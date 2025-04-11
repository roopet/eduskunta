# gemini_analyzer.py
import google.generativeai as genai
import os
import streamlit as st

def configure_gemini():
    try:
        # Yritä ensin lukea Streamlit secrets -tiedostosta
        api_key = st.secrets.get("GOOGLE_API_KEY")

        # Jos ei löydy secretseistä, yritä ympäristömuuttujaa (varalla paikalliselle kehitykselle)
        if not api_key:
            print("Ei löytynyt GOOGLE_API_KEY Streamlit secrets tiedostosta, yritetään ympäristömuuttujaa...")
            api_key = os.getenv("GOOGLE_API_KEY")

        # Jos ei löytynyt kummastakaan
        if not api_key:
            st.error("Virhe: GOOGLE_API_KEY ei löydy Streamlit secrets tiedostosta eikä ympäristömuuttujista. Määritä se jompaankumpaan.")
            print("Virhe: GOOGLE_API_KEY ei löydy Streamlit secrets tiedostosta eikä ympäristömuuttujista.")
            return None

        genai.configure(api_key=api_key)
        model_name = 'gemini-2.0-flash-lite' # Varmistetaan stabiili malli
        model = genai.GenerativeModel(model_name)
        print(f"Gemini model ({model_name}) configured successfully.")
        # Voit poistaa tämän tulosteen myöhemmin, kun kaikki toimii
        # st.success("Gemini API connection successful!") # Voit lisätä tämän palautteeksi käyttöliittymään
        return model

    except Exception as e:
        print(f"Virhe Gemini API:n konfiguroinnissa: {e}")
        st.error(f"Virhe Gemini API:n konfiguroinnissa: {e}") # Näytä virhe myös UI:ssa
        return None

# --- UUSI FUNKTIO HAKUSANOILLE (MATALA LÄMPÖTILA) ---
def generate_keywords_via_llm(model, keyword_prompt):
    """Generoi hakusanoja matalalla lämpötilalla konsistenssin parantamiseksi."""
    if not model:
        return "Gemini-mallia ei alustettu."

    try:
        # Aseta matala lämpötila (esim. 0.1 tai 0.2) deterministisempään tulokseen
        generation_config = genai.types.GenerationConfig(temperature=0.1) # TÄRKEÄ MUUTOS
        print(f"DEBUG Gemini: Lähetetään keyword prompt (temp={generation_config.temperature}): {keyword_prompt[:100]}...") # Lyhennetty tuloste

        response = model.generate_content(keyword_prompt, generation_config=generation_config)

        # Turvallisuus- ja virhetarkistukset + tekstin purku (kuten aiemmin)
        if not response.parts:
             feedback = getattr(response, 'prompt_feedback', None)
             block_reason = getattr(feedback, 'block_reason', 'Unknown') if feedback else 'Unknown'
             print(f"Varoitus: Avainsanojen generointivastaus estetty tai tyhjä. Syy: {block_reason}")
             # Yritetään saada lisätietoa estosta
             safety_ratings_str = str(getattr(feedback, 'safety_ratings', 'N/A')) if feedback else 'N/A'
             print(f"Safety Ratings: {safety_ratings_str}")
             return f"Avainsanojen generointi epäonnistui (Syy: {block_reason})."

        # Oletetaan, että onnistunut vastaus on tekstimuodossa
        # Tämä saattaa vaatia säätöä riippuen kirjaston versiosta
        if hasattr(response, 'text'):
             return response.text
        elif response.parts:
             return "".join(part.text for part in response.parts) # Yhdistä osat, jos niitä on
        else:
            print("Varoitus: Ei voitu purkaa tekstiä Geminin vastauksesta (keywords).")
            print(f"Koko vastausobjekti: {response}")
            return "Virhe: Ei voitu purkaa vastausta Geminiltä."

    except Exception as e:
        print(f"Virhe Gemini API -kutsussa (keywords): {e}")
        return f"Virhe Gemini-avainsanojen generoinnissa: {e}"
# --- UUSI FUNKTIO LOPPUU ---

def analyze_text_with_gemini(model, text_content, user_prompt):
    """
    Lähettää kehotteen ja valinnaisen tekstisisällön Gemini API:lle.

    Args:
        model: Alustettu Gemini GenerativeModel objekti.
        text_content (str): Analysoitava pääteksti (voi olla tyhjä).
        user_prompt (str): Varsinainen kehote tai kysymys Geminille.

    Returns:
        str: Geminin vastaus tai virheilmoitus.
    """
    if not model:
        return "Gemini-mallia ei alustettu."

    # Muodostetaan lopullinen kehote.
    # Lisätään tekstisisältö vain, jos sitä on annettu.
    if text_content:
        full_prompt = f"{user_prompt}\n\nAnalysoitava teksti:\n---\n{text_content}\n---"
    else:
        # Jos tekstisisältöä ei ole (esim. hakusanojen generointi), käytetään vain annettua kehotetta.
        full_prompt = user_prompt

    try:
        # Lisätään turvallisuusasetukset sallivammaksi joskus tarpeen mukaan
        # Huom: Tämä voi päästää läpi sisältöä, jonka Google normaalisti estäisi.
        # Käytä harkiten.
        # safety_settings = [
        #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        # ]
        # response = model.generate_content(full_prompt, safety_settings=safety_settings)

        response = model.generate_content(full_prompt)

        # Tarkista, onko vastaus estetty turvallisuussyistä
        if not response.parts:
             if response.prompt_feedback and response.prompt_feedback.block_reason:
                  print(f"Varoitus: Gemini esti vastauksen syystä: {response.prompt_feedback.block_reason}")
                  return f"Gemini esti vastauksen turvallisuussyistä ({response.prompt_feedback.block_reason}). Kokeile muotoilla kysymys/kehote uudelleen."
             else:
                  # Joskus vastaus voi olla tyhjä ilman selkeää estoa
                  print("Varoitus: Gemini palautti tyhjän vastauksen.")
                  return "Gemini palautti tyhjän vastauksen."


        # Tarkistetaan, onko kandidaatteja ja tekstiä (uudemmat API-versiot)
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content.parts:
                 return candidate.content.parts[0].text

        # Vanhempi API-tapa tai fallback
        if hasattr(response, 'text'):
            return response.text

        # Jos mikään ylläolevista ei toiminut
        print("Varoitus: Ei voitu purkaa tekstiä Geminin vastauksesta.")
        print(f"Koko vastausobjekti: {response}")
        return "Virhe: Ei voitu purkaa vastausta Geminiltä."


    except Exception as e:
        print(f"Virhe Gemini API -kutsussa: {e}")
        # Yritetään antaa lisätietoa virheestä, jos mahdollista
        error_details = getattr(e, 'message', str(e))
        return f"Virhe Gemini-analyysissä: {error_details}"

# Esimerkkikäyttö pääskriptissä:
# gemini_model = configure_gemini()
# if gemini_model:
#    analysis_result = analyze_text_with_gemini(gemini_model, pdf_text, "Heikentääkö tämä esitys eläinten oikeuksia?")
#    print(analysis_result)