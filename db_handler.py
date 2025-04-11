# db_handler.py
import sqlite3
from config import (DB_NAME, CURRENT_TERM_START_DATE,
                    PREVIOUS_TERM_START_DATE, PREVIOUS_TERM_END_DATE,
                    ORPO_START_DATE, MARIN_START_DATE, MARIN_END_DATE,
                    RINNE_START_DATE, RINNE_END_DATE, SIPILA_START_DATE, SIPILA_END_DATE)


def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        print(f"SQLite DB connection successful to {DB_NAME}")
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn):
    sql_create_table = """ CREATE TABLE IF NOT EXISTS hallituksen_esitykset (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                vaski_id TEXT UNIQUE NOT NULL,
                                eduskunta_tunnus TEXT,
                                paivamaara TEXT,
                                nimeke_teksti TEXT,
                                asiakirjatyyppi_nimi TEXT,
                                pdf_url TEXT,
                                local_pdf_path TEXT,
                                kielikoodi TEXT,
                                lyhyt_kuvaus TEXT,
                                voimaantulo TEXT
                            ); """
    try:
        c = conn.cursor()
        c.execute(sql_create_table)
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def insert_he(conn, he_data):
    # he_data on sanakirja, jossa avaimet vastaavat sarakkeiden nimiä
    sql = ''' INSERT OR IGNORE INTO hallituksen_esitykset(vaski_id, eduskunta_tunnus, paivamaara, nimeke_teksti,
                                            asiakirjatyyppi_nimi, pdf_url, local_pdf_path, kielikoodi,
                                            lyhyt_kuvaus, voimaantulo)
              VALUES(?,?,?,?,?,?,?,?,?,?) '''
    cur = conn.cursor()
    try:
        cur.execute(sql, (
            he_data.get('vaski_id'), he_data.get('eduskunta_tunnus'), he_data.get('paivamaara'),
            he_data.get('nimeke_teksti'), he_data.get('asiakirjatyyppi_nimi'), he_data.get('pdf_url'),
            he_data.get('local_pdf_path'), he_data.get('kielikoodi'), he_data.get('lyhyt_kuvaus'),
            he_data.get('voimaantulo')
        ))
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        print(f"Data causing error: {he_data}")
        return None

# db_handler.py
import sqlite3
from config import (DB_NAME, CURRENT_TERM_START_DATE,
                    PREVIOUS_TERM_START_DATE, PREVIOUS_TERM_END_DATE,
                    ORPO_START_DATE, MARIN_START_DATE, MARIN_END_DATE,
                    RINNE_START_DATE, RINNE_END_DATE, SIPILA_START_DATE, SIPILA_END_DATE)

# ... (muut funktiot pysyvät samoina) ...

# --- KORJATTU search_hes FUNKTIO ---
def search_hes(conn, keywords, filter_identifier='kaikki'):
    """Etsii HE:itä yhdellä kyselyllä, vaatien lyhyt_kuvaus -kentän olemassaolon."""
    cur = conn.cursor()
 #   base_query = "SELECT eduskunta_tunnus, nimeke_teksti, lyhyt_kuvaus FROM hallituksen_esitykset"
    base_query = "SELECT eduskunta_tunnus, nimeke_teksti, lyhyt_kuvaus, pdf_url FROM hallituksen_esitykset"  # Lisätty pdf_url
    where_clauses = [] # Lista kaikille WHERE-ehdoille
    params = []      # Lista kaikille parametreille

    # 0. **LISÄTTY**: Vaatimus, että lyhyt_kuvaus ei ole NULL eikä tyhjä
    # Tämä ehto lisätään aina osaksi WHERE-lausetta
    where_clauses.append("lyhyt_kuvaus IS NOT NULL AND lyhyt_kuvaus != ''")
    # Tähän ehtoon ei liity parametreja

    # 1. Rakenna avainsanaehto (OR-lohko)
    if keywords:
        keyword_conditions = []
        keyword_params = []
        for keyword in keywords:
            keyword_conditions.append("(LOWER(nimeke_teksti) LIKE ? OR LOWER(lyhyt_kuvaus) LIKE ?)")
            keyword_params.extend([f"%{keyword.lower()}%", f"%{keyword.lower()}%"])
        if keyword_conditions:
            # Lisätään sulkeissa oleva OR-lohko
            where_clauses.append("(" + " OR ".join(keyword_conditions) + ")")
            params.extend(keyword_params) # Lisätään avainsanaparametrit
        else:
             # Jos jostain syystä avainsanoja ei saada (vaikka lista ei ollut tyhjä), ei välttämättä haluta hakea
             print("DEBUG DB: Avainsanaehtoja ei muodostunut.")
             # Voitaisiin palauttaa tyhjä tai jatkaa ilman avainsanaehtoa riippuen halutusta toiminnasta
             # Tässä jatketaan ilman avainsanaehtoa, jolloin pelkkä pvm ja lyhytkuvaus-ehto jäävät
             pass # Jatketaan silti, jos vaikka pelkkä pvm-suodatus halutaan tehdä (vaatii lyhytkuvauksen)
    else:
        print("DEBUG DB: Ei avainsanoja, palautetaan tyhjä.")
        return [] # Vaaditaan avainsanoja ainakin tässä logiikassa

    # 2. Rakenna päivämääräehto
    date_condition_sql = ""
    date_params = []
    date_filter_applied = False

    # (if/elif -lohko päivämäärien asettamiseksi kuten edellisessä versiossa)
    if filter_identifier == 'nykyinen_kausi':
        date_condition_sql = "substr(paivamaara, 1, 10) >= ?"
        date_params.append(CURRENT_TERM_START_DATE)
        date_filter_applied = True
    elif filter_identifier == 'edellinen_kausi':
        date_condition_sql = "substr(paivamaara, 1, 10) >= ? AND substr(paivamaara, 1, 10) <= ?"
        date_params.extend([PREVIOUS_TERM_START_DATE, PREVIOUS_TERM_END_DATE])
        date_filter_applied = True
    elif filter_identifier == 'orpo':
        date_condition_sql = "substr(paivamaara, 1, 10) >= ?"
        date_params.append(ORPO_START_DATE)
        date_filter_applied = True
    elif filter_identifier == 'marin':
        date_condition_sql = "substr(paivamaara, 1, 10) >= ? AND substr(paivamaara, 1, 10) <= ?"
        date_params.extend([MARIN_START_DATE, MARIN_END_DATE])
        date_filter_applied = True
    elif filter_identifier == 'rinne':
        date_condition_sql = "substr(paivamaara, 1, 10) >= ? AND substr(paivamaara, 1, 10) <= ?"
        date_params.extend([RINNE_START_DATE, RINNE_END_DATE])
        date_filter_applied = True
    elif filter_identifier == 'sipilä' or filter_identifier == 'sipila':
        date_condition_sql = "substr(paivamaara, 1, 10) >= ? AND substr(paivamaara, 1, 10) <= ?"
        date_params.extend([SIPILA_START_DATE, SIPILA_END_DATE])
        date_filter_applied = True

    # Lisää päivämääräehto JA SEN PARAMETRIT, jos se on määritelty
    if date_condition_sql:
        where_clauses.append(date_condition_sql)
        params.extend(date_params) # Varmistetaan että tämä on mukana!
        print(f"DEBUG DB: Lisätty aikafiltteri ehto: {date_condition_sql} parametrilla/parametreilla {date_params}")

    # 3. Rakenna lopullinen kysely
    full_query = base_query
    if where_clauses:
        # Yhdistetään kaikki ehdot (lyhytkuvaus-ehto, avainsana-OR-lohko, pvm-ehto) ANDilla
        full_query += " WHERE " + " AND ".join(where_clauses)
    else:
         # Ei pitäisi tapahtua, koska lyhytkuvaus-ehto lisätään aina
         print("DEBUG DB: Ei ehtoja kyselyyn muodostunut (epätodennäköinen tilanne).")
         return []


    print(f"DEBUG DB: Suoritetaan SQL-kysely: {full_query}")
    print(f"DEBUG DB: Kyselyn parametrit ({len(params)} kpl): {params[:20]}...")

    try:
        cur.execute(full_query, params)
        rows = cur.fetchall()
        print(f"DEBUG DB: Kysely palautti {len(rows)} riviä.")
        return rows
    except sqlite3.Error as e:
        print(f"DEBUG DB: Virhe SQL-kyselyssä: {e}")
        return []
# --- FUNKTIO LOPPUU ---

def get_pdf_path(conn, he_tunnus):
     cur = conn.cursor()
     cur.execute("SELECT local_pdf_path FROM hallituksen_esitykset WHERE eduskunta_tunnus = ?", (he_tunnus,))
     result = cur.fetchone()
     return result[0] if result else None

# Muista luoda yhteys ja taulu pääskriptissä:
# conn = create_connection()
# if conn:
#    create_table(conn)
#    ... (muu logiikka)
#    conn.close()