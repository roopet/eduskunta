# streamlit_app.py
import streamlit as st
import db_handler
import pdf_parser
import gemini_analyzer
from config import DB_NAME
import os
import pandas as pd
import re # Tarvitaan pisteiden parsimiseen
#from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode


# --- Alustukset ja funktiot (initialize_components, get_pdf_full_text, format_gemini_prompt, get_search_params_from_llm) ---
# Varmista, että nämä ovat määritelty tai tuotu oikein
try:
    from chat_interface import get_search_params_from_llm, get_pdf_full_text, format_gemini_prompt
except ImportError:
    st.error("Tarvittavia apufunktioita ei löytynyt. Varmista importit.")
    # Placeholderit
    def get_search_params_from_llm(model, q): return [], 'kaikki'
    def get_pdf_full_text(path): return None
    def format_gemini_prompt(q, text, id): return "Virhe: format_gemini_prompt puuttuu"

st.set_page_config(page_title="HE Haku & Analyysi", layout="wide")

@st.cache_resource
def initialize_components():
    # ... (kuten ennen) ...
    print("Initializing components...")
    conn = db_handler.create_connection()
    if conn: db_handler.create_table(conn)
    model = gemini_analyzer.configure_gemini()
    return conn, model

conn, gemini_model = initialize_components()

#st.set_page_config(page_title="HE Haku & Analyysi", layout="wide")
st.title("Eduskunnan hallituksen esitysten haku ja analyysi")

# Session state alustukset
if 'original_question' not in st.session_state: st.session_state.original_question = ""
if 'suggested_keywords' not in st.session_state: st.session_state.suggested_keywords = []
if 'selected_keywords' not in st.session_state: st.session_state.selected_keywords = []
if 'filter_identifier' not in st.session_state: st.session_state.filter_identifier = 'kaikki'
if 'search_results' not in st.session_state: st.session_state.search_results = None
if 'analysis_results' not in st.session_state: st.session_state.analysis_results = {}
if 'relevance_scores' not in st.session_state: st.session_state.relevance_scores = {} # Uusi state pisteille
if 'score_threshold' not in st.session_state: st.session_state.score_threshold = 50 # Oletusraja

# --- Vaihe 1: Kysymyksen syöttö ---
# ... (kuten ennen, nappi nollaa myös relevance_scores) ...
st.subheader("1. Esitä kysymyksesi")
question_input = st.text_area("Kirjoita kysymyksesi tähän", height=100, key="question_text_area", value=st.session_state.original_question)
if st.button("Lähetä kysymys ja hae hakuehdotukset"):
    if question_input:
        st.session_state.original_question = question_input
        # Nollaa kaikki
        st.session_state.suggested_keywords = []
        st.session_state.selected_keywords = []
        st.session_state.filter_identifier = 'kaikki'
        st.session_state.search_results = None
        st.session_state.analysis_results = {}
        st.session_state.relevance_scores = {} # Nollaa myös pisteet

        # ... (hae hakusanat ja filtteri get_search_params_from_llm avulla) ...
        if gemini_model:
            with st.spinner("Pyydetään hakusanoja ja tunnistetaan filtteriä..."):
                 keywords, filter_id = get_search_params_from_llm(gemini_model, st.session_state.original_question)
                 # ... (Generic filter & Deduplication kuten ennen) ...
                 GENERIC_FILTER_WORDS = set(['laki', 'lait', 'lainsäädäntö', 'säädös', 'säännös', 'oikeus', 'esitys','hallitus', 'eduskunta', 'muutos', 'muuttaminen', 'muuttamisesta','ehdotus', 'pykälä', 'momentti', 'kohta', 'liite', 'asetus', 'direktiivi','yleissopimus', 'sopimus', 'kansainvälinen', 'suomi', 'valtioneuvosto', 'ministeriö','tarkoitus', 'tavoite', 'soveltaminen', 'voimaantulo', 'määräys', 'käsittely', 'hyväksyminen'])
                 keywords_filtered = [kw for kw in keywords if kw.lower() not in GENERIC_FILTER_WORDS]
                 seen = set(); unique_keywords = [];
                 for kw in keywords_filtered:
                      kw_lower = kw.lower()
                      if kw_lower not in seen: unique_keywords.append(kw); seen.add(kw_lower)
                 st.session_state.suggested_keywords = unique_keywords
                 st.session_state.selected_keywords = unique_keywords
                 st.session_state.filter_identifier = filter_id
        else: st.error("Gemini ei alustettu.")
    else: st.warning("Kirjoita kysymys.")


# --- Vaihe 2: Hakusanojen vahvistus ---
# (Tämä osio pysyy ennallaan - näyttää multiselectin ja text_inputin,
# päivittää st.session_state.selected_keywords kun nappia painetaan
# ja laukaisee haun. Tärkeää: formin sisällä oleva logiikka ajetaan
# vasta kun nappia painetaan)
if st.session_state.suggested_keywords:
    st.subheader("2. Vahvista tai muokkaa hakusanoja")
    st.info(f"Tunnistettu aikafiltteri: **{st.session_state.filter_identifier}**")
    with st.form("keyword_form"):
        # ... (multiselect ja text_input kuten edellisessä versiossa) ...
        current_options = st.session_state.suggested_keywords
        valid_defaults = [kw for kw in st.session_state.selected_keywords if kw in current_options]
        selected_gemini = st.multiselect(
             "Geminin ehdotukset:", options=current_options, default=valid_defaults,
             label_visibility="collapsed", key="keyword_multiselect"
        )
        additional_keywords_input = st.text_input(
             "Omat hakusanat (pilkulla erotettuna):", label_visibility="collapsed", key="additional_keywords"
        )
        submitted = st.form_submit_button("Tee haku valituilla/lisätyillä sanoilla")

        if submitted:
            # Yhdistä, deduplikoi ja tallenna lopulliset hakusanat stateen
            final_keywords = list(selected_gemini)
            if additional_keywords_input:
                additional_keywords = [kw.strip() for kw in additional_keywords_input.split(',') if kw.strip()]
                final_keywords.extend(additional_keywords)
            seen = set()
            unique_final_keywords = []
            for kw in final_keywords:
                kw_lower = kw.lower()
                if kw_lower not in seen:
                    unique_final_keywords.append(kw)
                    seen.add(kw_lower)
            st.session_state.selected_keywords = unique_final_keywords # Lopulliset hakusanat

            # Nollaa hakutulokset ja analyysit ennen uutta hakua
            st.session_state.search_results = None
            st.session_state.analysis_results = {}
            st.session_state.prioritized_hes = []

            if not st.session_state.selected_keywords:
                 st.warning("Valitse tai anna vähintään yksi hakusana.")
            else:
                # Suorita haku
                with st.spinner("Etsitään tietokannasta..."):
                    if conn:
                        print(f"DEBUG UI: Haetaan sanoilla: {st.session_state.selected_keywords}, Filtteri: {st.session_state.filter_identifier}")
                        results = db_handler.search_hes(
                            conn,
                            st.session_state.selected_keywords,
                            filter_identifier=st.session_state.filter_identifier
                        )
                        st.session_state.search_results = results # Tallennetaan raakatulokset
                        st.success(f"Haku valmis, löytyi {len(results) if results else 0} osumaa.")
                        # Älä aja rerun tässä, jotta priorisointilogiikka ehtii suorittaa
                    else:
                        st.error("Tietokantayhteys puuttuu.")


# --- LISÄTTY VAIHE: GEMINI-PISTEITYS HAKUTULOKSILLE ---
# Ajetaan tämä vain jos haku on tehty, tuloksia löytyi, JA pisteitä ei ole vielä laskettu
if st.session_state.search_results and not st.session_state.relevance_scores and gemini_model:
    with st.spinner("Pyydetään Geminiä arvioimaan tulosten relevanssia..."):
        results_for_scoring = st.session_state.search_results
        MAX_RESULTS_TO_SCORE = 250 # Raja kuinka monelle lasketaan pisteet
        if len(results_for_scoring) > MAX_RESULTS_TO_SCORE:
            st.info(f"Rajataan relevanssiarviointi {MAX_RESULTS_TO_SCORE} ensimmäiseen hakutulokseen.")
            results_for_scoring = results_for_scoring[:MAX_RESULTS_TO_SCORE]

        # Muodosta teksti Geminille
        scoring_input_text = ""
        for row in results_for_scoring:
            he_tunnus_score = row[0]
            lyhyt_kuvaus_score = row[2] if row[2] else "(Kuvaus puuttuu)"
            # Lyhennetään kuvausta tarvittaessa tokenien säästämiseksi
            max_desc_len = 1000
            if len(lyhyt_kuvaus_score) > max_desc_len:
                 lyhyt_kuvaus_score = lyhyt_kuvaus_score[:max_desc_len] + "..."
            scoring_input_text += f"HE Tunnus: {he_tunnus_score}\nKuvaus: {lyhyt_kuvaus_score}\n---\n"

        if scoring_input_text:
            scoring_prompt = f"""Käyttäjän alkuperäinen kysymys oli: "{st.session_state.original_question}"

Arvioi kunkin alla olevan hallituksen esityksen (HE) lyhyen kuvauksen relevanssi käyttäjän alkuperäiseen kysymykseen nähden asteikolla 0-100%. Korkeampi prosentti tarkoittaa suurempaa relevanssia.

Palauta vastauksesi muodossa:
HE Tunnus: Pisteet%
HE Tunnus: Pisteet%
...

ÄLÄ laita mitään muuta tekstiä vastaukseen. Jos et voi antaa arviota jollekin, älä sisällytä sitä vastaukseen.

Arvioitavat kuvaukset:
{scoring_input_text}
Arviot:"""

            try:
                scoring_response = gemini_analyzer.analyze_text_with_gemini(gemini_model, "", scoring_prompt)
                scores = {}
                # Parsi vastaus (yksinkertainen regex)
                for line in scoring_response.splitlines():
                    match = re.match(r"^\s*(HE\s*\d+/\d{4}\s*vp)\s*:\s*(\d{1,3})\s*%?\s*$", line.strip(), re.IGNORECASE)
                    if match:
                        he_id = match.group(1).replace(" ", "").upper() # Normalisoi HE-tunnus
                        score = int(match.group(2))
                        # Varmista että HE ID on niissä, joita pyydettiin arvioimaan
                        found_in_request = any(inp_row[0].replace(" ", "").upper() == he_id for inp_row in results_for_scoring)
                        if 0 <= score <= 100 and found_in_request:
                             # Normalisoi myös tallennettava avain
                             orig_he_id = next((inp_row[0] for inp_row in results_for_scoring if inp_row[0].replace(" ", "").upper() == he_id), None)
                             if orig_he_id:
                                  scores[orig_he_id] = score
                st.session_state.relevance_scores = scores
                print(f"DEBUG UI: Gemini relevanssipisteet: {scores}")
            except Exception as e:
                st.error(f"Virhe relevanssipisteiden käsittelyssä Geminillä: {e}")
                st.session_state.relevance_scores = {} # Tyhjennä virheen sattuessa
        else:
             st.session_state.relevance_scores = {} # Ei mitään arvioitavaa


# --- MUOKATTU VAIHE 3: HAKUTULOSTEN NÄYTTÖ PISTEILLÄ JA ESIVALINNOILLA ---
if st.session_state.search_results is not None:
    st.subheader("3. Hakutulokset ja analysoitavien valinta")
    results = st.session_state.search_results
    scores = st.session_state.relevance_scores
    score_threshold = st.session_state.get('score_threshold', 50) # Hae raja statesta

    # --- LISÄTTY: Liukusäädin edelleen tässä ---
    new_threshold = st.slider(
        "Esivalinnan relevanssiraja (%)", 0, 100, score_threshold, 5, key="threshold_slider",
        help="Valitse raja-arvo, jonka ylittävät tulokset esivalitaan."
    )
    # Päivitä vain jos arvo muuttui
    if new_threshold != score_threshold:
        st.session_state.score_threshold = new_threshold
        # Voit halutessasi ajaa rerun, jotta esivalinnat päivittyvät heti,
        # tai antaa käyttäjän jatkaa ja valinnat päivittyvät seuraavassa vaiheessa
        # st.rerun()

    if not results:
        st.info("Haulla ei löytynyt tuloksia.")
    else:
        if scores: st.markdown(f"Alla hakutulokset. Gemini arvioi relevanssin. Yli {st.session_state.score_threshold}% arviot esivalittu:")
        else: st.markdown("Alla hakutulokset.")

        try:
            df_results = pd.DataFrame(results, columns=['HE Tunnus', 'Otsikko', 'lyhyt_kuvaus_hidden', 'PDF URL'])
            df_results['Relevanssi (%)'] = df_results['HE Tunnus'].map(scores).fillna(0).astype(int)
            df_results['Valitse'] = df_results['Relevanssi (%)'] >= st.session_state.score_threshold # Käytä päivitettyä rajaa
            df_results = df_results[['Valitse', 'HE Tunnus', 'Relevanssi (%)', 'Otsikko', 'PDF URL', 'lyhyt_kuvaus_hidden']] # Otetaan PDF URL mukaan

            # --- LISÄTTY: Järjestys relevanssin mukaan ---
            df_results = df_results.sort_values(by='Relevanssi (%)', ascending=False)
            # -----------------------------------------

            # --- Leveyden laskenta (ennallaan) ---
            checkbox_width_val = 10; he_tunnus_width_val = 10; relevanssi_width_val = 10
            if not df_results.empty and 'HE Tunnus' in df_results.columns:
                 try:
                     max_len = df_results['HE Tunnus'].astype(str).map(len).max()
                     if pd.notna(max_len): he_tunnus_width_val = max(120, (int(max_len) * 8) + 30)
                 except Exception: pass
            final_checkbox_width = int(checkbox_width_val)
            final_he_tunnus_width = int(he_tunnus_width_val)
            final_relevanssi_width = int(relevanssi_width_val)
            # ------------------------------------

            # --- MUOKATTU: st.data_editor column_config ---
            edited_df = st.data_editor(
                df_results,
                key="data_editor_" + str(st.session_state.original_question) + str(st.session_state.score_threshold),
                column_config={
                    "Valitse": st.column_config.CheckboxColumn("Analysoi?", width=final_checkbox_width, required=True),
                #    "Valitse": st.column_config.CheckboxColumn("Analysoi?", width="small", required=True),
                    # Yritetään LinkColumnia uudelleen HE Tunnukselle
                    "HE Tunnus": st.column_config.LinkColumn(
                        "HE Tunnus",
                        help="Linkki alkuperäiseen PDF-dokumenttiin (jos saatavilla)",
                        width=final_he_tunnus_width,
                    #    width="small",
                        display_text="^(.+)$", # Näytä koko tunnus
                        # Asetetaan URL tulemaan 'PDF URL' -sarakkeesta
                        # Streamlitin dokumentaatio viittaa siihen, että tämä voisi toimia DataFramen kanssa
                        # Tässä täytyy olla tarkkana sarakkeen nimen kanssa
                         validate=None # Poistetaan validaatio, jos se aiheutti ongelmia
                    ),
                    "Relevanssi (%)": st.column_config.NumberColumn("Relevanssi", format="%d %%", width=final_relevanssi_width),
                #    "Relevanssi (%)": st.column_config.NumberColumn("Relevanssi", format="%d %%", width="small"),
                    "Otsikko": st.column_config.TextColumn("Otsikko"),
                    "lyhyt_kuvaus_hidden": None, # Piilotetaan
                    "PDF URL": None # Piilotetaan
                },
                hide_index=True, use_container_width=True,
                # Muokataan vain Valitse-saraketta
                disabled=['HE Tunnus', 'Relevanssi (%)', 'Otsikko', 'PDF URL', 'lyhyt_kuvaus_hidden']
            )
            # -------------------------------------------

            # --- Analysoi-nappi ja logiikka (kuten ennen, mutta hakee URL:n) ---
            if st.button("Analysoi valitut Geminillä", key="analyze_button"):
                selected_rows = edited_df[edited_df["Valitse"] == True]
                selected_for_analysis = selected_rows['HE Tunnus'].tolist()

                if not selected_for_analysis: st.warning("Et valinnut...")
                elif not gemini_model: st.error("Gemini API ei...")
                else:
                    st.session_state.analysis_results = {}
                    with st.spinner(f"Analysoidaan {len(selected_for_analysis)} valittua esitystä..."):
                        # Haetaan KAIKKI tulosdata (mukaanlukien URL) DataFramesta tehokkaammin
                        all_results_df = df_results.set_index('HE Tunnus')

                        for he_tunnus in selected_for_analysis:
                            st.write(f"Analysoidaan {he_tunnus}...")
                            analysis_result_text = f"Virheellinen tila ({he_tunnus})"
                            pdf_url_for_analysis = all_results_df.loc[he_tunnus, 'PDF URL'] # Hae URL dataframe indeksistä
                            pdf_path = db_handler.get_pdf_path(conn, he_tunnus) # Hae paikallinen polku

                            # --- LISÄTTY: Linkin lisäys stateen tallennettavaan tulokseen ---
                            link_markdown = f" ([PDF]({pdf_url_for_analysis}))" if pdf_url_for_analysis else ""
                            # -----------------------------------------------------------

                            if pdf_url_for_analysis:
                                # Kutsu uutta funktiota URL:lla
                                # Varmista, että funktio on tuotu oikein (esim. pdf_parser.get_pdf_text_from_url)
                                pdf_text = pdf_parser.get_pdf_text_from_url(pdf_url_for_analysis,
                                                                            max_pages=None)  # Lue koko dokkari

                                if pdf_text is not None:  # Tarkista None, "" on ok jos PDF on tyhjä
                                    st.write(
                                        f"DEBUG: PDF Text obtained for {he_tunnus} from URL (Length: {len(pdf_text)})")
                                    # Olettaen format_gemini_prompt importattu
                                    analysis_prompt = format_gemini_prompt(st.session_state.original_question, pdf_text,
                                                                           he_tunnus)
                                    analysis_result_raw = gemini_analyzer.analyze_text_with_gemini(gemini_model, "",
                                                                                                   analysis_prompt)
                                    analysis_result_text = analysis_result_raw + link_markdown

                           # if pdf_path and os.path.exists(pdf_path):
                           #     pdf_text = get_pdf_full_text(pdf_path)
                           #     if pdf_text is not None and pdf_text != "":
                           #         analysis_prompt = format_gemini_prompt(st.session_state.original_question, pdf_text, he_tunnus)
                           #         analysis_result_raw = gemini_analyzer.analyze_text_with_gemini(gemini_model, "", analysis_prompt)
                          #          # Lisää linkki analyysin loppuun (tai alkuun)
                         #           analysis_result_text = analysis_result_raw + link_markdown
                        #        else:
                       #             analysis_result_text = f"Virhe: PDF-tekstin lukeminen epäonnistui ({he_tunnus})." + link_markdown
                            else:
                                 analysis_result_text = f"Virhe: PDF-polkua ei löytynyt tai se on virheellinen ({he_tunnus})." + link_markdown

                            st.session_state.analysis_results[he_tunnus] = analysis_result_text

                    st.success("Analyysit valmiina!")
                    st.rerun() # Päivitä näyttämään analyysit

        except Exception as e:
            st.error(f"Virhe tulosten näyttämisessä/käsittelyssä: {e}")
            import traceback
            traceback.print_exc()

# --- Vaihe 4: Analyysien näyttö ---
if st.session_state.analysis_results:
     st.subheader("4. Gemini Analyysien Tulokset")
     # Järjestetään analyysit saman relevanssijärjestyksen mukaan kuin taulukko
     # Haetaan järjestys df_resultsista, jos se on vielä saatavilla (voi vaatia tallennusta stateen)
     # Yksinkertaisempi: käydään läpi siinä järjestyksessä kuin ne ovat dictissä
     for he_tunnus, analysis in st.session_state.analysis_results.items():
          # Otsikkoon ei enää tarvitse lisätä linkkiä, koska se lisättiin jo itse tekstiin
          with st.expander(f"Analyysi: {he_tunnus}"):
               # Käytä markdownia, jotta linkki toimii
               st.markdown(analysis, unsafe_allow_html=True)

# Sulje tietokantayhteys, kun sovellus suljetaan (tämä ei välttämättä toimi täydellisesti Streamlitissä)
# Parempi tapa voisi olla varmistaa yhteyden tila alussa ja sulkea vain tarvittaessa,
# mutta yksinkertaisessa sovelluksessa tämä voi riittää. Streamlit voi myös ajaa skriptin uudelleen.
# if conn:
#    conn.close() # Yhteyden sulkeminen Streamlitissä voi olla monimutkaista session state vuoksi