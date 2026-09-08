# Eduskunta.fi-sisältösivut ja tiedostot

## Sisältösivut

Käytä `SearchParliamentData`-toimintoa ja `sisaltosivu`-kategoriaa, kun kysymys koskee eduskunta.fi-verkkosivun sisältöä tai kun sivu voisi täydentää vastausta taustatiedolla. Hakutuloksessa voi olla esimerkiksi `name`, `teaserTitle`, `teaserText`, `friendlyUrl`, `absoluteUrl`, `masterLanguage`, `languages`, `publishStart`, `contentId`, `snippet` ja `fullTextSnippet`.

Rajapinta ei välttämättä palauta sisältösivun leipätekstiä. Käsittele otsikkoa ja lyhyttä kuvausta metatietona: niiden perusteella voi arvioida sivun mahdollisesti hyödylliseksi ja linkittää sen käyttäjälle, mutta niiden perusteella ei saa esittää sivun yksityiskohtaista sisältöä varmennettuna. Älä yritä avata sivua selaimella Copilot Studion puolesta.

Käytännössä testattu hakukategoria on `sisaltosivu`. Älä korvaa sitä arvolla `sivu`, vaikka vanha esimerkki tai puutteellinen kuvaus käyttäisi sitä. Jos `category` jätetään pois löytöhaussa, sama sivu voi esiintyä useana hakutulostyyppinä; deduplikoi tällöin ensisijaisesti `id`- tai `contentId`-arvolla ja varmista lopullinen osuma `sisaltosivu`-haulla.

```json
{
  "category": "sisaltosivu",
  "query": "Euroopan unionin rahoituskehys vuosille 2028 2034",
  "maxResults": 20,
  "startFromIndex": 0
}
```

Näytä ensisijaisesti API:n palauttama `absoluteUrl`. Jos se puuttuu, käytä `friendlyUrl`-arvoa vain, kun siitä muodostuu yksiselitteinen eduskunta.fi-linkki.

## Tiedostot ja kokoteksti

Käytä `tiedosto`-kategoriaa sivustolla julkaistujen tiedostojen, kuten PDF-esitteiden, raporttien ja muun julkaisemateriaalin löytämiseen. Tiedosto-objekti voi sisältää `name`, `title`, `extension`, `language`, URL:n, julkaisutiedot, sivumäärän, tunnuksia sekä indeksoidun kokotekstin `fullText`.

`fullText` voi olla pitkä ja sisältää PDF:stä irrotetun tekstin rivinvaihtoja, tavutusta, sivunumeroita tai muuta muunnoskohinaa. Varmista ennen sisältöväitettä tiedoston nimi, tunnus, tiedostopääte ja URL. Etsi väitettä tukeva kohta kokotekstistä ja tarkista ympäröivä teksti. Älä samaista `tiedosto`-hakutulosta `asiakirja`-kategorian parlamentaariseen asiakirjaan ilman rakenteista yhteyttä.

Tee ensin kevyt löytöhaku, jossa kokoteksti jätetään noutamatta:

```json
{
  "category": "tiedosto",
  "query": "eduskunta ja EU",
  "maxResults": 20,
  "startFromIndex": 0,
  "fields": {
    "operation": "exclude",
    "list": ["fullText"]
  }
}
```

Poissuljettu `fullText` voi näkyä vastauksessa `null`-arvona. Tee sen jälkeen tarkempi `SearchParliamentData`-haku ilman `fullText`-poissulkua, jotta voit lukea valitun tiedoston tekstin. Jos kokoteksti puuttuu tai näyttää katkenneelta, kerro rajoitus ja tarjoa tiedoston URL käyttäjälle.

## Lähteen käyttö vastauksessa

Erottele nämä ilmaisut:

- “Sivun otsikon ja lyhyen kuvauksen perusteella tämä voi olla hyödyllinen taustalähde…”
- “Tiedoston API:ssa indeksoidusta kokotekstistä ilmenee…”
- “Kokotekstiä ei ollut saatavilla, joten tiedoston sisältöä ei voitu varmentaa.”

Anna linkille kuvaava nimi. Mainitse noutopäivä, jos sisältö tai julkaisutieto voi muuttua.
