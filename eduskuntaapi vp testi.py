import json
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
import pandas as pd


# =========================
# ASETUKSET
# =========================

URL = "https://api.julkinen.beta.eduskunta.fi/api/v1/search/"

# siirtyvät
vuodet_siirtyvat = list(range(2013, 2026))
asiatyypit_siirtyvat = ["HE", "U", "E", "UTP", "EUN", "TS"]

# ei-siirtyvät
vuodet_ei_siirtyvat = list(range(2023, 2026))
asiatyypit_ei_siirtyvat = [
    "VNS", "VNT", "VN", "PI", "K", "LA", "TPA", "TAA", "LTA", "KA", "KK", "SKT", "VK",
    "PNE", "LJL", "VJL", "M", "KAA", "O", "VAP", "VAA", "ETJ"
]

# referenssitaulu
asiatyypit_kaikki = [
    "HE", "VNS", "VNT", "U", "VN", "E", "UTP", "PI", "K", "LA",
    "TPA", "TAA", "LTA", "KA", "KK", "SKT", "VK", "PNE", "LJL",
    "VJL", "M", "KAA", "O", "VAP", "VAA", "ETJ", "EUN", "TS"
]

asiatyyppien_selitteet = pd.DataFrame({
    "lyhenne": asiatyypit_kaikki,
    "asiatyyppi": [
        "Hallituksen esitys",
        "Valtioneuvoston selonteko",
        "Valtioneuvoston tiedonanto",
        "Valtioneuvoston U-kirjelmä",
        "Valtioneuvoston kirjelmä",
        "Valtioneuvoston E-selvitys",
        "Valtioneuvoston UTP-selvitys",
        "Pääministerin ilmoitus",
        "Kertomus",
        "Lakialoite",
        "Toimenpidealoite",
        "Talousarvioaloite",
        "Lisätalousarvioaloite",
        "Keskustelualoite",
        "Kirjallinen kysymys",
        "Suullinen kysymys",
        "Välikysymys",
        "Puhemiesneuvoston ehdotus",
        "Lepäämään jätetty lakiehdotus",
        "Vahvistamatta jäänyt laki",
        "Muu asia",
        "Kansalaisaloite",
        "Valiokunnan oma asia",
        "Vapautuspyyntö",
        "Vaali",
        "Eduskuntatyön järjestäminen",
        "Eurooppa-neuvoston ja EUn neuvostojen kokoukset",
        "Toissijaisuusasia",
    ]
})

# R-koodin throttle ~ 5 sek väli (60/300 = 0.2 req/s -> 1 req / 5 s)
SLEEP_SECONDS = 5

# sivun koko
MAX_RESULTS = 1000


# =========================
# APUTOIMINNOT
# =========================

def safe_get(obj: Any, *path: str, default: Any = None) -> Any:
    """Turvallinen nouto sisäkkäisistä dict-rakenteista."""
    cur = obj
    for key in path:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return default
    return cur if cur is not None else default


def build_query_json(vpvuosi: str, asiatyyppi: str, start_from_index: int, max_results: int) -> Dict[str, Any]:
    return {
        "category": "valtiopaivaasia",
        "maxResults": max_results,
        "startFromIndex": start_from_index,
        "expression": {
            "and": [
                {"property": "eduskuntatunnus", "match": vpvuosi},
                {"property": "asiakirjatyyppikoodi", "match": asiatyyppi},
            ]
        },
    }


def fetch_once(session: requests.Session, query_json: Dict[str, Any]) -> Dict[str, Any]:
    """Yksi GET-kutsu; q-parametrissa JSON-stringinä (kuten R: toJSON + req_url_query)."""
    params = {"q": json.dumps(query_json, ensure_ascii=False)}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # Jos joskus tarvitaan token, se yleensä tulisi Authorization-headeriin.
        # R-koodissa ei kuitenkaan käytetty tokenia, joten jätetään pois.
        # "Authorization": f"Bearer {api_token}",
    }

    time.sleep(SLEEP_SECONDS)
    resp = session.get(URL, params=params, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def get_total_count(search_metadata: Dict[str, Any], fallback_len: int) -> int:
    """
    Yritetään päätellä kokonaisosumat. API:n kenttien nimet voivat vaihdella;
    R-koodi käytti actualResultCount:ia "osumina".
    """
    for key in ("actualResultCount", "totalResultCount", "resultCount", "totalHits"):
        val = search_metadata.get(key)
        if isinstance(val, int):
            return val
    return fallback_len


def extract_rows_from_results(results: List[Dict[str, Any]], vpvuosi: str, asiatyyppi_koodi: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for r in results:
        asia = r.get("valtiopaivaasia") or {}

        tunnus = safe_get(asia, "eduskuntatunnus", "fi")
        asiakirjatyyppi_nimi = safe_get(asia, "asiakirjatyyppinimi", "fi")
        anto_pvm = safe_get(asia, "laadintapvm", "fi")
        tilanne = safe_get(asia, "kokonaispaatosnimi", "fi")

        if tilanne is None:
            tilanne = safe_get(asia, "tila", "fi")
            kasittely_paattynyt: Optional[str] = None
        else:
            kasittelyt = safe_get(asia, "kasittelyt", "fi", default=[]) or []
            tapahtumapaivat = [
                k.get("tapahtumapvm")
                for k in kasittelyt
                if isinstance(k, dict) and k.get("tapahtumapvm") is not None
            ]
            kasittely_paattynyt = max(tapahtumapaivat) if tapahtumapaivat else None

        rows.append({
            "tunnus": tunnus,
            "asiakirjatyyppikoodi": asiatyyppi_koodi,     # lisätty joinia varten
            "asiakirjatyyppi": asiakirjatyyppi_nimi,      # API:n nimi
            "vireilletulovuosi": vpvuosi,
            "anto_pvm": anto_pvm,
            "tilanne": tilanne,
            "kasittely_paattynyt": kasittely_paattynyt,
        })

    return rows


def fetch_all_pages_for_type(
    session: requests.Session,
    vpvuosi: str,
    asiatyyppi: str,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Hakee kaikki sivut (maxResults=1000) kyseiselle vuodelle + asiatyypille.
    Palauttaa (rows, total_count).
    """
    all_rows: List[Dict[str, Any]] = []
    start = 0
    page = 1
    total_count_est: Optional[int] = None

    while True:
        query_json = build_query_json(vpvuosi, asiatyyppi, start_from_index=start, max_results=MAX_RESULTS)
    #    print(f"  - Haku: vuosi={vpvuosi}, tyyppi={asiatyyppi:=None}")  # placeholder to avoid accidental typo
        print(f"  - Haku: vuosi={vpvuosi}, tyyppi={asiatyyppi}")

        # (yllä oleva rivi oli tarkoitus tulostaa, mutta muuttujan nimi on asiatyyppi)
        # korjataan tulostus oikeaksi:
        print(f"  - GET sivu {page}: vuosi={vpvuosi}, tyyppi={asiatyyppi if False else asiatyyppi}, startFromIndex={start}, maxResults={MAX_RESULTS}")

        try:
            vastaus = fetch_once(session, query_json)
        except requests.HTTPError as e:
            print(f"    ! HTTP-virhe sivulla {page} (vuosi={vpvuosi}, tyyppi={asiatyyppi if False else asiatyyppi}): {e}")
            break
        except requests.RequestException as e:
            print(f"    ! Pyyntövirhe sivulla {page} (vuosi={vpvuosi}, tyyppi={asiatyyppi if False else asiatyyppi}): {e}")
            break

        search_metadata = vastaus.get("searchMetadata") or {}
        results = vastaus.get("results") or []
        returned = len(results)

        if total_count_est is None:
            total_count_est = get_total_count(search_metadata, fallback_len=returned)

        print(f"    -> Palautui {returned} riviä (kokonaisosumat-arvio: {total_count_est})")

        if returned == 0:
            break

        rows = extract_rows_from_results(results, vpvuosi=vpvuosi, asiatyyppi_koodi=asiatyyppi if False else asiatyyppi)
        all_rows.extend(rows)
        print(f"    -> Parsittu {len(rows)} riviä, kertynyt yhteensä {len(all_rows)}")

        # Lopetusehto: jos palautui alle maxResults tai ollaan jo haettu vähintään total_count_est
        start += returned
        page += 1

        if returned < MAX_RESULTS:
            print("    -> Viimeinen sivu (returned < maxResults).")
            break
        if total_count_est is not None and start >= total_count_est:
            print("    -> Kaikki osumat haettu (start >= kokonaisosumat-arvio).")
            break

    return all_rows, int(total_count_est or len(all_rows))


# =========================
# PÄÄOHJELMA
# =========================

def main() -> pd.DataFrame:
    session = requests.Session()
    all_rows: List[Dict[str, Any]] = []

    print("== Aloitetaan siirtyvien asioiden haku ==")
    for year in vuodet_siirtyvat:
        vpvuosi = str(year)
        print(f"\nVuosi {vpvuosi} (siirtyvät):")
        for asiatyyppi in asiatyypit_siirtyvat:
            print(f"* Asiatyyppi {asiatyyppi if False else asiatyyppi}")
            rows, total = fetch_all_pages_for_type(session, vpvuosi, asiatyyppi)
            if total == 0 or len(rows) == 0:
                print("  -> Ei osumia.")
                continue
            all_rows.extend(rows)
            print(f"  -> Lisätty {len(rows)} riviä, kokonaiskertymä {len(all_rows)}")

    print("\n== Aloitetaan ei-siirtyvien asioiden haku ==")
    for year in vuodet_ei_siirtyvat:
        vpvuosi = str(year)
        print(f"\nVuosi {vpvuosi} (ei-siirtyvät):")
        for asiatyyppi in asiatyypit_ei_siirtyvat:
            print(f"* Asiatyyppi {asiatyyppi if False else asiatyyppi}")
            rows, total = fetch_all_pages_for_type(session, vpvuosi, asiatyyppi)
            if total == 0 or len(rows) == 0:
                print("  -> Ei osumia.")
                continue
            all_rows.extend(rows)
            print(f"  -> Lisätty {len(rows)} riviä, kokonaiskertymä {len(all_rows)}")

    print("\n== Muodostetaan DataFrame ==")
    df = pd.DataFrame(all_rows)

    if df.empty:
        print("DataFrame jäi tyhjäksi (ei osumia).")
        return df

    # Datetime-muunnokset (robusti)
    print("== Muunnetaan päivämäärä-sarakkeet datetime-tyyppiin ==")
    df["anto_pvm"] = pd.to_datetime(df["anto_pvm"], errors="coerce", dayfirst=True)
    df["kasittely_paattynyt"] = pd.to_datetime(df["kasittely_paattynyt"], errors="coerce", dayfirst=True)

    # Join selitteisiin (asiakirjatyyppikoodi -> lyhenne)
    print("== Liitetään asiatyyppien selitteet (join) ==")
    df = df.merge(
        asiatyyppien_selitteet,
        how="left",
        left_on="asiakirjatyyppikoodi",
        right_on="lyhenne"
    ).drop(columns=["lyhenne"])

    print(f"== Valmis. Rivejä yhteensä: {len(df)} ==")
    return df


if __name__ == "__main__":
    df = main()

    print("\n== Esikatselu (20 ensimmäistä) ==")
    print(df.head(20).to_string(index=False))

#    Halutessasi tallennus:
    df.to_csv("valtiopaivaasiat.csv", index=False, encoding="utf-8")
