# Käsitteet ja luotettavuus

## Ydinkäsitteet

- **Valtiopäiväasia:** eduskunnan käsiteltävä kokonaisuus, esimerkiksi `HE 60/2018 vp`, `KK 123/2020 vp` tai `KAA 5/2022 vp`. Hakukategoria on `valtiopaivaasia`.
- **Asiakirja:** asiaan tai eduskuntatyöhön liittyvä yksittäinen julkaisu, jolla on yleensä oma `edktunnus`, esimerkiksi `EDK-2025-AK-8709`. Hakukategoria on `asiakirja`.
- **Asiatyyppi:** vp-asian laji, esimerkiksi HE, LA, KAA tai KK. `valtiopaivaasia`-kategoriassa `asiakirjatyyppikoodi.fi` tarkoittaa käytännössä asiatyyppiä.
- **Asiakirjatyyppi:** yksittäisen dokumentin laji, esimerkiksi valiokunnan mietintö, valiokunnan lausunto, asiantuntijalausunto, eduskunnan vastaus tai pöytäkirja.
- **Käsittely:** asian etenemiseen liittyvä tapahtuma, jolla voi olla päivä, vaihe, valiokunta, fraasi ja toimijoita.
- **Pöytäkirjan asiakohta:** täysistunnon pöytäkirjan yhden asian käsittelyä kuvaava kokonaisuus. Se kokoaa keskustelua ja voi liittyä useaan asiakirjaan.
- **Puheenvuoro:** yhden puhujan puheenvuoro tietyssä täysistunnossa ja asiakohdassa.
- **Äänestys:** yksi äänestystapahtuma, jolla on oma tunnus, kysymyksenasettelu, tulos ja edustajakohtaiset äänet.

## Älä sekoita näitä

| Kysymys | Oikea taso | Tyypillinen tunnus |
|---|---|---|
| Miten asia eteni? | valtiopäiväasia + käsittelyt | `HE 60/2018 vp` |
| Mitä valiokunta kirjoitti? | valiokunta-asiakirjan sisältö | `EDK-...` |
| Kuka antoi asiantuntijalausunnon? | asiantuntijalausunnon metadata | `EDK-...` |
| Mitä asiantuntija väitti? | asiantuntijalausunnon HTML/XML/PDF | `EDK-...` |
| Mitä edustaja sanoi? | puheenvuoro + pöytäkirjan asiakohta | puheenvuoron `id` / PTK |
| Miten edustaja äänesti? | äänestyksen detail-vastaus | äänestyksen `id` |

“Lausunto” voi tarkoittaa joko valiokunnan lausuntoa toiselle valiokunnalle tai henkilön/organisaation asiantuntijalausuntoa valiokunnalle. Henkilö, organisaatio, titteli, liite, vastine tai lisäselvitys viittaa yleensä asiantuntija-aineistoon. Valiokuntatunnus kuten PeVL tai LiVL viittaa valiokunnan omaan lausuntoon.

## Todistustaso

Käytä väitteen vahvuutta vastaavaa lähdettä:

1. Hakutulos osoittaa löydettävyyden ja perustiedot.
2. Detail-vastaus osoittaa rakenteiset suhteet, vaiheet ja tilat.
3. HTML/XML/PDF osoittaa varsinaisen sisällön.
4. Äänestyksen detail-vastaus osoittaa äänestystuloksen ja edustajakohtaiset äänet.
5. Pöytäkirjan asiakohta osoittaa täysistuntokontekstin.

Älä lainaa tai referoi sisältöä, jota et ole lukenut. Otsikko, `nimeketeksti` ja hakusnippet voivat auttaa löytämisessä, mutta eivät yksin vahvista kannanottoa.

## Ajallinen luotettavuus

- Tulkitse puuttuva loppupäivä avoimeksi jaksoksi, ei ikuiseksi varmuudeksi.
- Sisällytä henkilö tai jäsenyys aikaväliin, jos `alku <= kyselyn loppu` ja (`loppu` puuttuu tai `loppu >= kyselyn alku`).
- Erota nykyinen ryhmä/vaalipiiri historiallisista jäsenyyksistä.
- Käytä nykytilaa koskevassa vastauksessa noutopäivää.
- Älä päättele tarkkaa ikää pelkästä syntymävuodesta. Ilmaise “ikä kuluvana vuonna”, jos päivää ei ole.
- Ennen vuotta 2015 kieli- ja asiakirjasisällön kattavuus voi olla heikompi. Kerro tämä historiallisissa hauissa.

## Hakukattavuus

Yhdistä aihehaussa vähintään kaksi tasoa:

- vp-asian nimeke ja viralliset asiasanat;
- asiakirjojen otsikot ja metatiedot;
- tarvittaessa asiakirjan koko teksti, puheenvuoro tai pöytäkirjan asiakohta.

Käytä suomessa perusmuotoja, taivutusmuotoja, varovaisia vartaloita ja synonyymejä. Esimerkiksi `tietojärjestelmä`, `tietojärjestelmät`, `tietojärjestelmien`, `tietojärjestelmiä` sekä pitkän sanan vartalo `tietojärjestelm`. Käytä myös fraaseja kuten `sähköinen asiointi` ja sen taivutusmuotoja.

## Epävarmuuden raportointi

Erota seuraavat tilanteet:

- **Todennettu:** väitettä suoraan tukeva lähde löytyi.
- **Todennäköinen osuma:** metadata vastaa hakua, mutta sisältö puuttuu tai sitä ei voitu lukea.
- **Ei löytynyt tällä haulla:** kysely ei palauttanut osumaa.
- **Ei voitu varmentaa:** API, asiakirja tai olennainen kenttä oli puutteellinen.

Älä muunna “ei löytynyt” -tulosta muotoon “ei ole olemassa”.

## Lähteet

- OpenAPI: https://api.eduskunta.fi/openapi.json
- API-käyttöliittymä: https://api.eduskunta.fi/
- Eduskunnan tilastot: https://www.eduskunta.fi/FI/naineduskuntatoimii/tilastot/Sivut/default.aspx
- Lainvalmistelun eduskuntakäsittely: https://lainvalmistelu.finlex.fi/6-eduskuntakasittely/
- Keskeiset lyhenteet: https://avoindata.eduskunta.fi/digitoidut/lyhenteet

