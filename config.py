# config.py
import os # Lisätty os-importti PDF_FOLDER luontiin

BASE_URL = "https://avoindata.eduskunta.fi/api/v1/vaski/asiakirjatyyppinimi"
DB_NAME = "he_data.db"
PDF_FOLDER = "he_pdfs" # Kansio, johon PDF:t ladataan paikallisesti

# --- LISÄTTY PUUTTUVA PARAMS ---
PARAMS = {
    "languageCode": "fi",
    "filter": "Hallituksen esitys",
    "perPage": 100,  # Haetaan 100 kerrallaan
    "page": 0        # Aloitussivu (päivitetään silmukassa)
}
# ----------------------------------

# Oletetut avaimet API-vastauksessa (Tarkistettu JSON-vastauksesta!)
DOCUMENTS_KEY = 'rowData'
HAS_MORE_KEY = 'hasMore'

# Indeksit rowData-listassa (tarkistettu JSON-datasta)
DOC_ID_INDEX = 0
HE_NUM_INDEX = 1
DATE_INDEX = 2
TITLE_XML_INDEX = 3
DOC_TYPE_XML_INDEX = 4
PDF_URL_INDEX = 5
# API_LINK_INDEX = 6 # Ei käytössä tässä versiossa
LANG_CODE_INDEX = 7

# Regex PDF-parserointiin (nämä ovat *esimerkkejä*, vaativat testausta ja säätöä!)
DESC_START_HEADING = r"ESITYKSEN PÄÄASIALLINEN SISÄLTÖ"
# Päivitetty regex voimaantulolle kattamaan useampia tapauksia
EFFECTIVE_DATE_PHRASES_REGEX = [
    # Fraasi + spesifi pvm pp.kk.vvvv
    r"((?:Ehdotetut? l[ae]i[dt]? ovat tarkoitus tulla voimaan|Laki on tarkoitettu tulemaan voimaan)\s*.*?(\d{1,2}\.\s*\d{1,2}\.\s*\d{4}).*)",
    # Fraasi + spesifi pvm pp päivänä kuukautta vvvv
     r"((?:Laki|Tämä laki) tulee voimaan\s+\d{1,2}\.\s*päivänä\s*\w+kuuta\s*\d{4})",
    # Säädetään asetuksella
    r"(Tämän lain voimaantulosta\s*säädetään\s*(?:valtioneuvoston)?\s*asetuksella)",
    # Säädettävänä ajankohtana
    r"((?:Laki|Tämä laki) tulee voimaan(?:\s*myöhemmin)?\s*säädettävänä\s*ajankohtana)"
]

# --- VAALIKAUSIEN JA HALLITUSTEN PÄIVÄMÄÄRÄT ---
# Vaalikaudet (arviot eduskunnan kokoontumisesta)
CURRENT_TERM_START_DATE = '2023-04-12'
PREVIOUS_TERM_START_DATE = '2019-04-24'
PREVIOUS_TERM_END_DATE = '2023-04-11'

# Hallitukset (nimityspäivämäärät)
ORPO_START_DATE = '2023-06-20'
# Orpon kausi jatkuu, ei päättymispäivää haussa

MARIN_START_DATE = '2019-12-10'
MARIN_END_DATE = '2023-06-19' # Päivä ennen Orpon nimitystä

RINNE_START_DATE = '2019-06-06'
RINNE_END_DATE = '2019-12-09' # Päivä ennen Marinin nimitystä

SIPILA_START_DATE = '2015-05-29'
SIPILA_END_DATE = '2019-06-05' # Päivä ennen Rinteen nimitystä

SINCE_2015_START_DATE = '2015-05-29' # Käytetään Sipilän alkua rajana

# Varmistetaan, että PDF-kansio on olemassa skriptiä importattaessa
os.makedirs(PDF_FOLDER, exist_ok=True)