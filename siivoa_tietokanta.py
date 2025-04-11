# siivoa_tietokanta.py
import sqlite3
from datetime import datetime
import os
import shutil # Varmuuskopiointia varten
from config import DB_NAME # Tuo tietokannan nimi config.py:stä

def find_earliest_date(rows, date_index):
    """Etsii ja palauttaa varhaisimman validin päivämäärän merkkijonona annetuista riveistä."""
    earliest_obj = None
    earliest_str = None
    for row in rows:
        date_str = row[date_index]
        if not date_str: continue # Ohita tyhjät päivämäärät
        try:
            # Olettaa muodon YYYY-MM-DD HH:MM:SS
            date_obj = datetime.strptime(date_str.split('.')[0], '%Y-%m-%d %H:%M:%S') # Poista mahdolliset millisekunnit
            if earliest_obj is None or date_obj < earliest_obj:
                earliest_obj = date_obj
                earliest_str = date_str # Palauta alkuperäinen merkkijono
        except (ValueError, TypeError):
            print(f"    VAROITUS: Ohitetaan virheellinen päivämäärämuoto: {date_str}")
            continue # Ignoroidaan virheelliset päivämäärät
    return earliest_str

def find_best_row_id_to_keep(rows, id_idx, path_idx, desc_idx):
    """Etsii säilytettävän rivin ID:n prioriteettijärjestyksessä."""
    best_id_both = None
    best_id_path_only = None
    first_id = rows[0][id_idx] if rows else None # Fallback: ensimmäinen rivi

    for row in rows:
        row_id = row[id_idx]
        has_path = bool(row[path_idx] and row[path_idx].strip()) # Tarkista ettei ole tyhjä merkkijono
        has_desc = bool(row[desc_idx] and row[desc_idx].strip())

        if has_path and has_desc:
            best_id_both = row_id # Löytyi paras vaihtoehto
            break # Ei tarvitse etsiä enempää, jos löytyi rivi molemmilla tiedoilla
        elif has_path and best_id_path_only is None:
            best_id_path_only = row_id # Tallennetaan paras "vain polku"-vaihtoehto

    if best_id_both is not None:
        print(f"    Valitaan säilytettäväksi rivi (polku+kuvaus löytyy): ID={best_id_both}")
        return best_id_both
    elif best_id_path_only is not None:
        print(f"    Valitaan säilytettäväksi rivi (vain polku löytyy): ID={best_id_path_only}")
        return best_id_path_only
    else:
        print(f"    VAROITUS: Yhdelläkään duplikaatilla ei polkua/kuvausta. Säilytetään ensimmäinen rivi: ID={first_id}")
        return first_id

def deduplicate_and_fix_dates_in_db():
    """Siivoaa duplikaatit ja korjaa päivämäärät olemassa olevassa tietokannassa."""
    conn = None
    try:
        print(f"Yhdistetään tietokantaan: {DB_NAME}")
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        # 1. Etsi HE Tunnukset, joilla on duplikaatteja
        cur.execute("""
            SELECT eduskunta_tunnus, COUNT(*) as count
            FROM hallituksen_esitykset
            GROUP BY eduskunta_tunnus
            HAVING COUNT(*) > 1
        """)
        duplicate_tunnukset = cur.fetchall()
        num_duplicates = len(duplicate_tunnukset)
        print(f"Löytyi {num_duplicates} HE Tunnusta, joilla on duplikaatteja.")

        if num_duplicates == 0:
            print("Duplikaatteja ei löytynyt. Tietokanta on jo siisti tältä osin.")
            return

        processed_count = 0
        # 2. Käy läpi duplikaatit
        for he_tunnus, count in duplicate_tunnukset:
            processed_count += 1
            print(f"\nKäsitellään {he_tunnus} ({count} kpl) ({processed_count}/{num_duplicates})...")

            # Hae kaikki duplikaattirivit tälle tunnukselle
            cur.execute("""
                SELECT id, vaski_id, paivamaara, nimeke_teksti, pdf_url, local_pdf_path, lyhyt_kuvaus, voimaantulo
                FROM hallituksen_esitykset
                WHERE eduskunta_tunnus = ?
                ORDER BY id -- Järjestys voi auttaa valinnassa, jos tarvitaan fallback
            """, (he_tunnus,))
            duplicate_rows = cur.fetchall()

            # Määritä indeksit selkeyden vuoksi (varmista että vastaa SELECT-lausetta)
            id_idx, vaski_idx, pvm_idx, title_idx, url_idx, path_idx, desc_idx, voim_idx = range(8)

            # Etsi varhaisin päivämäärä NÄISTÄ riveistä
            earliest_date = find_earliest_date(duplicate_rows, pvm_idx)

            # Etsi säilytettävän rivin ID NÄISTÄ riveistä
            id_to_keep = find_best_row_id_to_keep(duplicate_rows, id_idx, path_idx, desc_idx)

            if id_to_keep is None: # Ei pitäisi tapahtua, jos rivejä löytyi
                 print(f"  VIRHE: Säilytettävää riviä ei voitu määrittää tunnukselle {he_tunnus}. Ohitetaan.")
                 continue

            # Hae säilytettävän rivin nykyinen päivämäärä vertailua varten
            current_date_to_keep = None
            for row in duplicate_rows:
                 if row[id_idx] == id_to_keep:
                      current_date_to_keep = row[pvm_idx]
                      break

            # Aloita transaktio
            try:
                updated = False
                # Päivitä päivämäärä, jos se löytyi ja eroaa säilytettävän rivin nykyisestä
                if earliest_date and earliest_date != current_date_to_keep:
                    print(f"  Päivitetään rivin ID={id_to_keep} päivämääräksi: {earliest_date}")
                    cur.execute("UPDATE hallituksen_esitykset SET paivamaara = ? WHERE id = ?", (earliest_date, id_to_keep))
                    updated = True
                elif not earliest_date:
                    print(f"  VAROITUS: Varhaisinta päivämäärää ei voitu määrittää, ei päivitetä.")

                # Poista muut duplikaatit
                print(f"  Poistetaan muut duplikaatit (paitsi ID={id_to_keep})...")
                cur.execute("DELETE FROM hallituksen_esitykset WHERE eduskunta_tunnus = ? AND id != ?", (he_tunnus, id_to_keep))
                deleted_count = cur.rowcount
                print(f"  Poistettiin {deleted_count} duplikaattiriviä.")

                conn.commit() # Vahvista muutokset tälle ryhmälle
                if updated or deleted_count > 0:
                     print(f"  Muutokset tunnukselle {he_tunnus} vahvistettu.")
                else:
                     print(f"  Ei tarvittavia muutoksia tunnukselle {he_tunnus}.")

            except sqlite3.Error as e:
                 print(f"  VIRHE käsiteltäessä ryhmää {he_tunnus}: {e}. Perutaan muutokset tälle ryhmälle.")
                 conn.rollback() # Peru muutokset tämän ryhmän osalta

        print("\nTietokannan siivous valmis.")

    except sqlite3.Error as e:
        print(f"Tietokantavirhe: {e}")
    except Exception as e:
        print(f"Odottamaton virhe: {e}")
    finally:
        if conn:
            conn.close()
            print("Tietokantayhteys suljettu.")

if __name__ == "__main__":
    print("--- Aloitetaan tietokannan duplikaattien siivous ja päivämäärien korjaus ---")
    print(f"Kohdetietokanta: {DB_NAME}")

    # VARMUUSKOPIOINTI (erittäin suositeltavaa!)
    backup_db_name = DB_NAME + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        print(f"Otetaan varmuuskopio: {backup_db_name} ...")
        shutil.copyfile(DB_NAME, backup_db_name)
        print("Varmuuskopiointi onnistui.")
    except FileNotFoundError:
         print(f"VAROITUS: Tietokantaa {DB_NAME} ei löytynyt varmuuskopiointia varten. Jatketaan varovasti.")
    except Exception as e:
        print(f"VAROITUS: Varmuuskopiointi epäonnistui: {e}. Jatketaan varovasti.")

    # Varmistuskysymys käyttäjältä (valinnainen mutta turvallinen)
    confirm = input(f"Haluatko varmasti jatkaa tietokannan '{DB_NAME}' muokkaamista? (k/E): ")
    if confirm.lower() == 'k':
        deduplicate_and_fix_dates_in_db()
    else:
        print("Toiminto peruttu.")

    print("\n--- Skriptin suoritus päättyi ---")