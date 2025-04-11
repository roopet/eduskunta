# initial_load.py
import requests
import json
import time
import os
import re # Lisätty regex varten
from config import BASE_URL, PARAMS, DB_NAME, PDF_FOLDER, DOCUMENTS_KEY, HAS_MORE_KEY, PDF_URL_INDEX, TITLE_XML_INDEX, DOC_ID_INDEX, HE_NUM_INDEX, DATE_INDEX, DOC_TYPE_XML_INDEX, LANG_CODE_INDEX
import db_handler
import pdf_parser

def extract_first_text_from_xml_string(xml_string):
    # Yksinkertainen regex-pohjainen purku otsikolle/tyypille XML-fragmentista
    match = re.search(r'>([^<]+)<', xml_string)
    return match.group(1).strip() if match else xml_string # Palauta alkuperäinen, jos purku ei onnistu

def extract_pdf_url_from_html(html_string):
     match = re.search(r'href="([^"]+)"', html_string)
     # Poista lainausmerkit alusta ja lopusta, jos ne ovat mukana
     url = match.group(1).strip('"') if match else None
     # Varmista, että URL on validi (alkaa http)
     if url and url.startswith("http"):
         return url
     return None

def fetch_all_documents_and_populate_db(conn, max_pages_to_fetch=None):
    # Käytetään aiemmin kehitettyä hakulogiikkaa
    all_documents_raw = []
    current_page = 0
    print("Aloitetaan HE-metadatan haku rajapinnasta...")
    # ... (Tähän se while True -silmukka, joka hakee sivuja ja tarkistaa hasMore, kuten he-lataus.py:ssä)
    # ... Oletetaan, että silmukan tuloksena `all_documents_raw` sisältää kaikki rivit (listat listoista)
    # Esimerkki datasta, jos rajapinta palautti objektin:
    # page_obj = response.json()
    # page_docs = page_obj.get(DOCUMENTS_KEY, [])
    # has_more = page_obj.get(HAS_MORE_KEY, False)
    # if page_docs: all_documents_raw.extend(page_docs)
    # if not has_more: break
    # current_page += 1 ... jne.

    # Tässä vaiheessa oletetaan, että all_documents_raw on täytetty JSON-datasta haetuilla listoilla
    # Esimerkki: all_documents_raw = json.load(open('hallituksen_esitykset.json'))

    # ------ TÄHÄN TULEE DATAN LATAUS JA SILMUKKA ------
    # Tämä osa vaatii sen toimivan datan hakukoodin integrointia (fetch_all_documents he-lataus.py:stä)
    # Korvaa alla oleva kovakoodattu esimerkki oikealla datan haulla.
    # Tässä esimerkki siitä, miten dataa käsiteltäisiin kun se on haettu:

    # Ladataan data tiedostosta TÄSSÄ PoC:ssa, normaalisti tämä tulisi API-hausta
    try:
        with open('hallituksen_esitykset.json', 'r', encoding='utf-8') as f:
            all_documents_raw = json.load(f)
        print(f"Ladattu {len(all_documents_raw)} tietuetta JSON-tiedostosta.")
    except FileNotFoundError:
        print("Virhe: hallituksen_esitykset.json tiedostoa ei löytynyt. Aja ensin datan haku.")
        return
    except json.JSONDecodeError:
        print("Virhe: hallituksen_esitykset.json tiedoston sisältö ei ole validia JSONia.")
        return

    print("\nAloitetaan PDF-lataus, tekstinpoiminta ja tallennus tietokantaan...")
    processed_count = 0
    for row_data in all_documents_raw:
        try:
            vaski_id = row_data[DOC_ID_INDEX]
            he_tunnus_raw = row_data[HE_NUM_INDEX]
            # Puhdistetaan HE-tunnus (otetaan vain ensimmäinen, jos niitä on monta)
            he_tunnus = he_tunnus_raw.split(',')[0].strip()

            # Poimitaan ja puhdistetaan data
            nimeke_xml = row_data[TITLE_XML_INDEX]
            nimeke_teksti = extract_first_text_from_xml_string(nimeke_xml)

            tyyppi_xml = row_data[DOC_TYPE_XML_INDEX]
            tyyppi_teksti = extract_first_text_from_xml_string(tyyppi_xml)
            if tyyppi_teksti != "Hallituksen esitys":
                 continue # Käsitellään vain HE:t

            pdf_url_html = row_data[PDF_URL_INDEX]
            pdf_url = extract_pdf_url_from_html(pdf_url_html)

            # Lataa PDF paikallisesti
            local_path = pdf_parser.download_pdf(pdf_url, he_tunnus)

            lyhyt_kuvaus = None
            voimaantulo = None
            if local_path:
                # Poimi teksti useammalta sivulta
                # Adjust num_pages based on typical HE length, 5 seems reasonable start
                pdf_text = pdf_parser.extract_text_first_pages(local_path, num_pages=5)
                if pdf_text:
                    lyhyt_kuvaus = pdf_parser.find_short_description(pdf_text)
                    # Search for date text within the *same extracted text*
                    voimaantulo = pdf_parser.find_effective_date_text(pdf_text)

            # Koosta tietorivi tietokantaan tallennettavaksi
            he_entry = {
                'vaski_id': vaski_id,
                'eduskunta_tunnus': he_tunnus,
                'paivamaara': row_data[DATE_INDEX],
                'nimeke_teksti': nimeke_teksti,
                'asiakirjatyyppi_nimi': tyyppi_teksti,
                'pdf_url': pdf_url,
                'local_pdf_path': local_path,
                'kielikoodi': row_data[LANG_CODE_INDEX],
                'lyhyt_kuvaus': lyhyt_kuvaus,
                'voimaantulo': voimaantulo
            }

            # Tallenna tietokantaan
            db_handler.insert_he(conn, he_entry)
            processed_count += 1
            if processed_count % 10 == 0: # Tulosta edistymistä
                print(f"Käsitelty {processed_count}/{len(all_documents_raw)}...")

        except Exception as e:
            print(f"Virhe rivin käsittelyssä (Vaski ID: {row_data[DOC_ID_INDEX] if len(row_data)>0 else 'N/A'}): {e}")
            print(f"Rivin data: {row_data}") # Tulosta ongelmallinen rivi

    print(f"Valmis. {processed_count} hallituksen esitystä käsitelty ja tallennettu tietokantaan.")


# Pääohjelman suoritus
if __name__ == "__main__":
    conn = db_handler.create_connection()
    if conn is not None:
        db_handler.create_table(conn)
        # Tässä kutsutaan varsinaista datan hakua ja populointia
        # Tässä PoC:ssa data ladataan JSONista, mutta normaalisti haettaisiin API:sta ensin
        fetch_all_documents_and_populate_db(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")