# Tilastot ja laskenta

## Sisällysluettelo

- [Laskentasopimus](#laskentasopimus)
- [Yksiköt ja tunnukset](#yksiköt-ja-tunnukset)
- [Virallisten notebookien periaatteet](#virallisten-notebookien-periaatteet)
- [Aikajaksot](#aikajaksot)
- [Ryhmittely ja osuudet](#ryhmittely-ja-osuudet)
- [Laadunvarmistus](#laadunvarmistus)
- [Visualisointi](#visualisointi)

## Laskentasopimus

Kirjoita ennen laskentaa yksi lause:

> Lasken [yksikön] [aikavälillä] käyttäen [kategoriaa ja tunnusta], rajattuna [tyypit/kieli/status], noutopäivänä [aika].

Kerro, lasketaanko vireille tulleita, käsiteltyjä, päätettyjä, hyväksyttyjä, voimassa olevia, julkaistuja vai kaikkia löydettyjä kohteita. Nämä eivät ole sama mittari.

Käytä `/search/count`-endpointia, jos yksi API-kysely vastaa määritelmää täsmällisesti. Jos tulos vaatii useita rivejä, kieliversioita, liitosta tai statuslogiikkaa, hae kaikki osat, deduplikoi tunnuksella ja dokumentoi laskenta.

## Yksiköt ja tunnukset

| Yksikkö | Kategoria/lähde | Deduplikointitunnus |
|---|---|---|
| valtiopäiväasia | `valtiopaivaasia` | `eduskuntatunnus.fi` |
| asiakirja | `asiakirja` / inventaario | `edktunnus` |
| kansanedustaja | `kansanedustaja` | `henkilonro` |
| puheenvuoro | `puheenvuoro` | `id` |
| äänestys | `aanestys` | `id` |
| edustajan ääni | äänestyksen detail | äänestys-id + `henkilonro` |
| käsittelytapahtuma | vp-asian detail | asian tunnus + vaihe/tunnus + päivä + järjestys |

Älä laske asiasana-, asiakirja-, käsittely- tai lausuntorivejä vp-asioiden määräksi.

## Virallisten notebookien periaatteet

Käyttäjän toimittamat eduskunnan virallisia tilastoja tuottavat R-notebookit osoittavat seuraavat hyödylliset määrittelyt. Toteuta laskenta Pythonilla tai API:n `count`-endpointilla, mutta säilytä määritelmä.

### Vireille tulleet asiat vuosittain ja asiatyypeittäin

Käytä `valtiopaivaasia`-kategoriaa ja rajaa:

- `valtiopaivavuosi.fi = vuosi`
- `asiakirjatyyppikoodi.fi = asiatyyppi`

Kutsu `/search/count` jokaiselle ei-päällekkäiselle vuosi–tyyppi-yhdistelmälle. Nouda asiatyyppien ajantasaiset nimet `/reference-data/asiatyypit`-endpointista. Vuosittaisten solujen summa muodostaa kokonaismäärän vain, jos jokainen asia kuuluu täsmälleen yhteen soluun.

### Nykyisten edustajien ryhmäjakauma

Hae `kansanedustaja`-kategoriasta `edustajantoimenTila = Nykyinen`, deduplikoi `henkilonro`-tunnuksella ja ryhmittele `viimeisinEduskuntaryhma.nimi.fi`-arvolla. Ilmoita noutopäivä. Tarkista, että kokonaismäärä vastaa nykyisten yksilöllisten edustajien määrää.

### Nykyisten edustajien ikäjakauma

Jos käytössä on vain `syntymavuosi`, laske `kuluvan vuoden vuosiluku - syntymävuosi` ja nimeä mittari “ikä kuluvana vuonna”, ei tarkaksi iäksi. Käytä aukottomia luokkia:

- alle 30
- 30–34
- 35–39
- 40–44
- 45–49
- 50–54
- 55–59
- 60–64
- 65–69
- 70 tai yli

Älä toista lähdenotebookin ehtovirhettä, jossa viimeinen ehto alkoi 65 vuodesta; 70+ alkaa 70 vuodesta.

### Valtiopäiväasiat päätöksittäin

Päätöstilasto vaatii enemmän kuin yhden vuoden vireilletulot. Osa asiatyypeistä voi siirtyä aiemmilta valtiopäiviltä tai vaalikausilta. Hae relevantit aiemmat asiat, käytä `kokonaispaatosnimi.fi`-arvoa ja sen puuttuessa `tila.fi`-arvoa, ja rajaa käsittelyn päättymispäivä tarkasteltavaan valtiopäiväjaksoon. Selvitä valtiopäivien alku `/reference-data/valtiopaivat`-endpointista; älä kovakoodaa vanhan notebookin päivää.

Yhdessä vp-asiassa voi olla useita ehdotuksia eri lopputuloksin. Jos käyttäjä kysyy “lakeja” tai “lakiehdotuksia”, laske tarvittaessa `ehdotukset`-tasolla ja selitä ero asioiden määrään.

### Toimielinjäsenyydet ja johtohenkilöt

Hae nykyiset edustajat, litistä `toimielinjasenyydet.fi`, rajaa jäsenyys noutopäivään tai kysyttyyn aikaväliin ja ryhmittele henkilö + toimielin + rooli. Älä käytä nykyistä ryhmää historiallisena ryhmänä.

## Aikajaksot

Erota:

- kalenterivuosi;
- valtiopäivävuosi;
- vaalikausi;
- hallituskausi;
- yksittäinen täysistunto;
- jäsenyyden tai tehtävän aikajakso.

Hae vaalikausien ja valtiopäivien rajat viitetiedoista. Hallituskauden päivät eivät ole sama tietue kuin vaalikausi; pyydä tai lähteistä hallituksen tarkat päivät, jos mittari koskee hallituskautta.

Ajanjaksojen päällekkäisyys:

```python
def overlaps(start, end, query_start, query_end):
    return start <= query_end and (end is None or end >= query_start)
```

Käytä suljettua päällekkäisyyslogiikkaa henkilö- ja jäsenyystiedoissa. API:n `fromDate`/`toDate`-hakuvälin `toDate` on sen sijaan dokumentaation mukaan poissulkeva.

## Ryhmittely ja osuudet

Varmista aina:

- ryhmien summa = deduplikoitu kokonaismäärä;
- puuttuvat arvot ovat oma “ei tietoa” -ryhmä, eivät automaattisesti nolla;
- prosenttien nimittäjä on näkyvissä;
- kieliversiot eivät kaksinkertaista havaintoja;
- historiallinen ryhmä tai vaalipiiri valitaan tapahtuma-ajankohdan mukaan;
- mitätöidyt äänestykset käsitellään määritelmän mukaisesti.

Luokittelukysymyksissä, joissa lähde on vapaata tekstiä (esim. ammattiala tai aihe), näytä luokittelusanasto ja tarvittaessa suppea sekä laaja tulos.

## Laadunvarmistus

1. Vertaa haettujen sivujen rivimäärää `totalResultCount`-arvoon.
2. Vertaa deduplikoitua määrää `/search/count`-tulokseen, jos määritelmä on sama.
3. Tarkista vähintään kolme riviä alkuperäisistä detail-vastauksista.
4. Tarkista ryhmäsummat ja nollat.
5. Tarkista aikavälin ensimmäinen ja viimeinen päivä sekä avoimet loppupäivät.
6. Tallenna pyyntö, noutoaika ja mahdolliset epäonnistuneet osat.
7. Jos virallinen eduskuntatilasto vastaa samaa määritelmää, vertaa siihen ja selvitä erot ennen vastausta.

## Visualisointi

Käytä:

- pylväskaaviota kategorioiden vertailuun;
- viivaa vain aidosti vertailukelpoiseen aikasarjaan;
- taulukkoa, jos tarkat tunnukset tai pienet määrät ovat olennaisia;
- pinottua kaaviota vain, jos ryhmät muodostavat saman kokonaisuuden jokaisessa pisteessä.

Lisää kuvaan tai alaviitteeseen:

- mittarin täsmällinen nimi;
- ajanjakso ja aikakäsite;
- kieli-, tyyppi- ja statusrajaukset;
- puuttuvien arvojen käsittely;
- noutopäivä;
- “Lähde: Eduskunta Public API” ja suora URL tai kyselykuvaus.

Viralliset eduskuntatilastot: https://www.eduskunta.fi/FI/naineduskuntatoimii/tilastot/Sivut/default.aspx

