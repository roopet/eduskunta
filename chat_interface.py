# chat_interface.py
import db_handler
import pdf_parser
import gemini_analyzer
import os
import re
from config import DB_NAME

# POISTETTU: STOP_WORDS ja extract_keywords -funktio

def get_pdf_full_text(pdf_path):
    # ... (koodi pysyy samana kuin edellisessä versiossa) ...
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"PDF-polkua ei löytynyt tai se on virheellinen: {pdf_path}")
        return None
    try:
        doc = pdf_parser.fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()
        return full_text
    except Exception as e:
        print(f"Virhe PDF:n lukemisessa ({pdf_path}): {e}")
        return None


def format_gemini_prompt(original_question, pdf_text, he_tunnus):
    # ... (koodi pysyy samana kuin edellisessä versiossa) ...
    prompt = f"""Käyttäjä kysyi: "{original_question}"

Analysoi seuraava hallituksen esityksen (HE {he_tunnus}) teksti tämän kysymyksen näkökulmasta.
Kerro tiivistetysti ja perustellusti, miten tämä esitys liittyy kysymykseen.
Jos kysymys koskee esimerkiksi vaikutuksia tai muutoksia, kuvaa ne selkeästi.

Analysoitava teksti (HE {he_tunnus}):
--- START TEXT ---
{pdf_text}
--- END TEXT ---

Analyysisi:"""
    return prompt

# --- UUDELLEENNIMETTY JA MUOKATTU FUNKTIO ---
def get_search_params_from_llm(model, original_question):
    """Pyytää LLM:ää generoimaan hakusanat JA tunnistamaan aika/hallitusfiltterin."""
    if not model:
        print("Varoitus: Gemini-mallia ei alustettu.")
        return [], 'kaikki' # Oletus: ei sanoja, ei filtteriä

    # Esimerkki TODELLA TIIUKASTA kehotteesta get_search_params_from_llm -funktiossa:
    prompt = f"""Käyttäjä haluaa löytää Suomen eduskunnan hallituksen esityksiä (HE) liittyen tähän aiheeseen: "{original_question}"

    Tehtävät:
    1. Generoi  LYHYT lista (max 10-15 kpl) kaikkein keskeisimmistä, YLEISIMMISTÄ ja TOISISTAAN EROAVISTA suomenkielisistä HAKUSANOISTA (ensisijaisesti substantiivit perusmuodossa), jotka kattavat aiheen ytimen.
    2. VARMISTA, ETTÄ LISTALLA EI OLE SEMANTTISESTI PÄÄLLEKKÄISIÄ TERMEJÄ. Jos esimerkiksi 'metsä' on listalla ja kattaa aiheen, ÄLÄ lisää myös sanoja 'metsätalous' tai 'metsänhoito'. Valitse vain se kattavin tai olennaisin termi kustakin merkitysalueesta.
    3. VÄLTÄ TÄYSIN yleisiä lakitermejä ('laki', 'säädös', 'pykälä' jne.).
    4. Tunnista aikafiltteri ('orpo', 'marin', ..., 'kaikki') kuten aiemmin.

    Vastausmuoto: hakusana1,hakusana2;filtteri
    Esimerkki: metsä,hakkuu,suojelu;orpo

    Vastaus:"""

    print("\nPyydetään Geminiltä hakusanoja ja aikafiltteriä (matala lämpötila)...")
    try:
        # --- KUTSU MUUTETTU KÄYTTÄMÄÄN UUTTA FUNKTIOTA ---
        response_text = gemini_analyzer.generate_keywords_via_llm(model, prompt)
        # -------------------------------------------------
        if "virhe" in response_text.lower() or ';' not in response_text:
             print(f"Virhe tai odottamaton vastausmuoto Geminiltä: {response_text}")
             return [], 'kaikki'

        parts = response_text.split(';')
        keywords_raw = parts[0].strip()
        filter_identifier_raw = parts[1].strip().lower() if len(parts) > 1 else 'kaikki'

        keywords = [kw.strip() for kw in keywords_raw.split(',') if kw.strip() and len(kw) > 1]

        # Sallitut tunnisteet
        allowed_filters = ['orpo', 'marin', 'rinne', 'sipilä', 'nykyinen_kausi', 'edellinen_kausi', 'kaikki', 'nykyhallitus']
        if filter_identifier_raw not in allowed_filters:
            filter_identifier = 'kaikki' # Oletus, jos tunnistus epäonnistuu
        else:
            filter_identifier = filter_identifier_raw

        print(f"Geminin generoimat hakusanat: {keywords}")
        print(f"Tunnistettu filtteri: {filter_identifier}")
        return keywords, filter_identifier

    except Exception as e:
        print(f"Odottamaton virhe hakuparametrien generoinnissa: {e}")
        return [], 'kaikki'


def main():
    conn = db_handler.create_connection()
    if not conn:
        return

    gemini_model = gemini_analyzer.configure_gemini()
    if not gemini_model:
        print("KRIITTINEN VIRHE: Gemini API:a ei voitu alustaa. Ohjelma ei voi toimia ilman sitä.")
        if conn:
            conn.close()
        return

    # --- LISÄTTY TÄHÄN: YLEISTEN SANOJEN SUODATUSLISTA ---
    # Lista sanoista, jotka todennäköisesti esiintyvät lähes kaikissa HE:issä
    # ja ovat harvoin hyödyllisiä yksinään haussa. Voit laajentaa listaa tarvittaessa.
    GENERIC_FILTER_WORDS = set([
        'laki', 'lait', 'lainsäädäntö', 'säädös', 'säännös', 'oikeus', 'esitys',
        'hallitus', 'eduskunta', 'muutos', 'muuttaminen', 'muuttamisesta',
        'ehdotus', 'pykälä', 'momentti', 'kohta', 'liite', 'asetus', 'direktiivi',
        'yleissopimus', 'sopimus', 'kansainvälinen', 'suomi', 'valtioneuvosto', 'ministeriö',
        'tarkoitus', 'tavoite', 'soveltaminen', 'voimaantulo', 'määräys', 'käsittely', 'hyväksyminen'
        # Lisää tarvittaessa muita hyvin yleisiä termejä
    ])
    # ------------------------------------------------------

    print("\n--- Eduskunnan HE Kysely & Analyysi (AI-avusteinen haku) ---")
    print("Voit esittää kysymyksen HE-tietokannasta (esim. 'mitkä esitykset heikentävät eläinten oikeuksia?').")
    print("Kirjoita 'lopeta' poistuaksesi.")

    original_question = ""

    while True:
        try:
            user_input = input("\nKysymyksesi tai komento: ").strip()

            if user_input.lower() == "lopeta":
                break

            if not user_input:
                continue

            original_question = user_input
            print(f"\nKäsitellään kysymystä: '{original_question}'")

            # 1. Generoi avainsanat LLM:llä
        # vanha   keywords_llm = get_search_keywords_from_llm(gemini_model, original_question)
            keywords_llm, filter_identifier = get_search_params_from_llm(gemini_model, original_question)  # MUUTOS

            if not keywords_llm:
                print("Hakusanoja ei voitu generoida. Yritä muotoilla kysymys uudelleen tai tarkista API-avain.")
                continue

            # --- LISÄTTY TÄHÄN: SUODATUSVAIHE ---
            keywords_filtered = [kw for kw in keywords_llm if kw.lower() not in GENERIC_FILTER_WORDS]
            print(f"Suodatetut hakusanat hakuun: {keywords_filtered}")
            # ------------------------------------

            # Tarkistetaan jäikö suodatuksen jälkeen sanoja jäljelle
            if not keywords_filtered:
                 print("Suodatuksen jälkeen ei jäänyt jäljelle hakusanoja. Kokeile tarkentaa kysymystä.")
                 continue # Jos kaikki suodatettiin pois, ei haeta
                 # --- LISÄTTY: 3. POISTA TARKAT DUPLIKAATIT (CASE-INSENSITIVE) ---
            seen = set()
            unique_keywords = []
            for kw in keywords_filtered:
                     kw_lower = kw.lower()  # Verrataan pienellä kirjoitettuna
                     if kw_lower not in seen:
                         unique_keywords.append(kw)  # Säilytetään alkuperäinen kirjoitusasu listalla
                         seen.add(kw_lower)

            print(f"Uniikit suodatetut hakusanat hakuun: {unique_keywords}")
                 # -------------------------------------------------------------



            # 2. Tee tietokantahaku SUODATETUILLA avainsanoilla
            print(f"Etsitään tietokannasta hakusanoilla: {', '.join(keywords_filtered)}")
            print(
                f"DEBUG CHAT: Välitetään search_hes-funktiolle: keywords={keywords_filtered}, filter_identifier='{filter_identifier}'")

            # Käytetään db_handler.search_hes -funktiota suodatetuilla sanoilla
         #   results = db_handler.search_hes(conn, keywords_filtered) # <--- MUISTA KÄYTTÄÄ TÄSSÄ keywords_filtered
        #    results = db_handler.search_hes(conn, keywords_filtered, filter_identifier=filter_identifier)
            results = db_handler.search_hes(conn, unique_keywords, filter_identifier=filter_identifier)  # <-- Käytä unique_keywords

            # --- LOPUT KOODISTA (tulosten esitys, analysoitavien valinta jne.) PYSYY SAMANA ---
            if not results:
                print("Tietokannasta ei löytynyt osumia suodatetuilla avainsanoilla.")
                continue

            print("\nLöytyneet mahdollisesti relevantit esitykset:")
            results_dict = {}
            for i, row in enumerate(results):
                he_tunnus = row[0]
                title = row[1]
                results_dict[i + 1] = he_tunnus
                print(f"  {i+1}. {he_tunnus}: {title}")

            # 3. Kysy käyttäjältä, mitkä analysoidaan
            while True:
                analyze_input = input("\nMitkä näistä haluat analysoitavan tarkemmin Geminillä?\n"
                                      "Anna numerot pilkulla erotettuna (esim. 1,3), HE-tunnus, 'kaikki' tai 'ei': ").strip().lower()
                # ... (Valintojen käsittelylogiikka pysyy samana) ...
                selected_hes = []
                if analyze_input == 'ei' or analyze_input == '':
                    break
                elif analyze_input == 'kaikki':
                    selected_hes = list(results_dict.values())
                    break
                else:
                    try:
                        indices_or_ids = [item.strip() for item in analyze_input.split(',')]
                        valid_selection = True
                        for item in indices_or_ids:
                            if item.isdigit():
                                index = int(item)
                                if index in results_dict:
                                    selected_hes.append(results_dict[index])
                                else:
                                    print(f"Virheellinen numero: {index}")
                                    valid_selection = False
                                    break
                            else: # Oletetaan HE-tunnukseksi
                                found = False
                                for res_id in results_dict.values():
                                     if res_id.replace(" ","").lower() == item.replace(" ","").lower():
                                          selected_hes.append(res_id)
                                          found = True
                                          break
                                if not found:
                                     print(f"Antamaasi HE-tunnusta '{item}' ei löytynyt hakutuloksista.")
                                     valid_selection = False
                                     break
                        if valid_selection:
                             selected_hes = list(dict.fromkeys(selected_hes))
                             break
                        else:
                             selected_hes = []
                    except ValueError:
                        print("Virheellinen syöte. Anna numerot pilkulla erotettuna, HE-tunnus, 'kaikki' tai 'ei'.")


            # 4. Suorita analyysi valituille
            if selected_hes and not gemini_model:
                 print("Gemini API ei ole käytettävissä, joten analyysia ei voida suorittaa.")
            elif selected_hes:
                # ... (Analyysin suoritus pysyy samana) ...
                print(f"\n--- Aloitetaan {len(selected_hes)} HE:n analysointi Geminillä ---")
                for he_to_analyze in selected_hes:
                    print(f"\nAnalysoidaan: {he_to_analyze}")
                    pdf_path = db_handler.get_pdf_path(conn, he_to_analyze)
                    pdf_text = get_pdf_full_text(pdf_path) # Käytä aiemmin määriteltyä funktiota

                    if pdf_text:
                        gemini_prompt = format_gemini_prompt(original_question, pdf_text, he_to_analyze)
                        print("Lähetetään analyysipyyntö Gemini API:lle...")
                        analysis_result = gemini_analyzer.analyze_text_with_gemini(gemini_model, "", gemini_prompt)
                        print(f"\n--- Gemini Analyysi (HE {he_to_analyze}) ---")
                        print(analysis_result)
                        print("-----------------------------")
                    else:
                        print(f"Ei voitu lukea PDF-tekstiä esitykselle {he_to_analyze}. Analyysi ohitettu.")
                print("\n--- Analyysit valmiit ---")

        except Exception as e:
            print(f"\nTapahtui odottamaton virhe pääsilmukassa: {e}")
            import traceback
            traceback.print_exc()


    if conn:
        conn.close()
    print("\nYhteys tietokantaan suljettu. Ohjelma päättyi.")

if __name__ == "__main__":
    main()