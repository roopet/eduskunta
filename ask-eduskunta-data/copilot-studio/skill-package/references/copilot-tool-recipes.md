# Copilot Studio -työkalureseptit

## Sisällysluettelo

- [Yhteystesti](#yhteystesti)
- [Haku ja määrä](#haku-ja-määrä)
- [Valtiopäiväasia](#valtiopäiväasia)
- [Asiakirja](#asiakirja)
- [Asiantuntijakuulemiset](#asiantuntijakuulemiset)
- [Kansanedustaja](#kansanedustaja)
- [Sisältösivut ja tiedostot](#sisältösivut-ja-tiedostot)
- [Äänestykset](#äänestykset)

## Yhteystesti

Kutsu ensin `GetMatterTypes`. Se ei tarvitse parametreja. Onnistunut JSON-vastaus osoittaa, että connector saavuttaa `api.eduskunta.fi`-palvelun.

Jos tämä antaa `403`-virheen, älä tee muita hakuja ennen connectorin, DLP-sääntöjen tai välityspalvelimen korjaamista.

## Haku ja määrä

Käytä `SearchParliamentData`-toimintoa löytämiseen ja `CountParliamentData`-toimintoa määrään. Anna pyynnön body yhtenä objektina.

Esimerkki vuoden 2025 kansalaisaloitteiden määrästä:

```json
{
  "category": "valtiopaivaasia",
  "expression": {
    "and": [
      {"property": "valtiopaivavuosi.fi", "match": "2025"},
      {"property": "asiakirjatyyppikoodi.fi", "match": "KAA"}
    ]
  }
}
```

Esimerkki hallituksen esitysten hakemisesta:

```json
{
  "category": "valtiopaivaasia",
  "langCode": "fi",
  "maxResults": 100,
  "startFromIndex": 0,
  "expression": {
    "and": [
      {"property": "valtiopaivavuosi.fi", "match": "2025"},
      {"property": "asiakirjatyyppikoodi.fi", "match": "HE"}
    ]
  },
  "sort": [{"property": "laadintapvm", "ascending": false}]
}
```

## Valtiopäiväasia

Kun tunnus tunnetaan, käytä `GetParliamentaryMatter`-toimintoa ja anna tunnus normaalissa muodossa:

```text
HE 60/2018 vp
```

Käytä `GetMatterDocuments`-toimintoa saman asian asiakirjojen inventointiin. Valitse tarvittava `edktunnus` asiakirjatyypin, kielen ja päivämäärän perusteella. Säilytä samalla henkilöllä tai organisaatiolla olevat `AL`, `ALL`, `V` ja `LS` erillisinä, jos niiden `edktunnus` eroaa.

## Asiakirja

Käytä ensin `GetDocumentMetadata`-toimintoa. Kun vastaus edellyttää asiakirjan sisältöä, kutsu `GetDocumentHtml` samalla EDK-tunnuksella.

Anna tunnus normaalissa muodossa:

```text
EDK-2019-AK-243347
```

Vanha tunnus voi olla esimerkiksi `EDK_HE_1_2010`. Anna aina API:n palauttama arvo sellaisenaan; älä oleta nykyistä väliviivamuotoa.

HTML-vastaus voi olla pitkä. Poimi vain väitteen kannalta olennaiset otsikot ja kappaleet. Älä tulkitse navigaatiotekstiä asiakirjan sisällöksi.

## Asiantuntijakuulemiset

Hae kalenterivuoden kuulemiset `SearchParliamentData`-toiminnolla. Päivämäärän pitää olla samassa sisäkkäisessä käsittelytapahtumassa kuin kuulemisvaiheen:

```json
{
  "category": "valtiopaivaasia",
  "maxResults": 1000,
  "startFromIndex": 0,
  "expression": {
    "property": "kasittelyt.fi",
    "with": {
      "and": [
        {"property": "yleinenkasittelyvaihe", "match": "Asiantuntijakuuleminen"},
        {"property": "tapahtumapvm", "fromDate": "2026-01-01", "toDate": "2027-01-01"}
      ]
    }
  }
}
```

Sivuta kaikki vp-asiat. Suodata niiden `kasittelyt.fi`-listasta päivämääräväli ja koodit `ATKUUL`, `ATKUULA`, `ATKUULJT` ja `ATKUJTA`; pelkkä `ATKUUL*` ei riitä. Deduplikoi `kasittelytunnus`-arvolla. Poimi valiokunta, `valiokunta.jaosto` sekä kaikkien fraasiryhmien kuvaus ja toimijat. Inventoi saman vuoden `asiantuntijalausunnot.fi` erikseen ja säilytä kaikki eri `edktunnus`-arvot.

## Kansanedustaja

Kun tarvitset kaikki nykyiset ja entiset edustajat, sivuta `SearchParliamentData`-haku kategoriassa `kansanedustaja` kasvattamalla `startFromIndex`-arvoa, kunnes haettu määrä saavuttaa `totalResultCount`-arvon. Deduplikoi `henkilonro`-arvolla. Älä lopeta ensimmäiseen 1 000 osumaan.

Hae henkilö ensin `SearchParliamentData`-toiminnolla:

```json
{
  "category": "kansanedustaja",
  "maxResults": 20,
  "startFromIndex": 0,
  "expression": {
    "and": [
      {"property": "kutsumanimi", "match": "ETUNIMI"},
      {"property": "sukunimi", "match": "SUKUNIMI"}
    ]
  }
}
```

Poimi `henkilonro` osumasta. Kutsu vasta sitten `GetMember`. Tarkista detail-vastauksesta, että nimi täsmää. Älä arvaa henkilönumeroa.

## Sisältösivut ja tiedostot

Sisältösivun löytöhaku:

```json
{
  "category": "sisaltosivu",
  "query": "Euroopan unionin rahoituskehys vuosille 2028 2034",
  "maxResults": 20,
  "startFromIndex": 0
}
```

Voit linkittää `absoluteUrl`-osoitteen käyttäjälle, jos otsikko ja lyhyt kuvaus osoittavat sivun mahdollisesti hyödylliseksi. Älä esitä metatietoa sivun koko sisältönä.

Tiedoston kevyt löytöhaku:

```json
{
  "category": "tiedosto",
  "query": "eduskunta ja EU",
  "maxResults": 20,
  "startFromIndex": 0,
  "fields": {"operation": "exclude", "list": ["fullText"]}
}
```

Toista tarkka haku ilman poissulkua ja varmista sisältö `tiedosto.fullText`-kentästä. Säilytä nimi, tiedostopääte, `id`, URL ja noutopäivä.

## Äänestykset

Käytä `GetMatterVotes`-toimintoa asian kaikkien äänestysten inventointiin. Anna esimerkiksi:

```text
KAA 1/2019 vp
```

Kutsu jokaiselle olennaiselle tunnukselle `GetVote`. Lue kysymyksenasettelu ennen jaa/ei-tuloksen tulkintaa.

Käytä `GetSessionVotes`-toimintoa, kun rajaus on täysistunto. Poimi äänestys-API:n käyttämä `istunnonTunniste` toisesta äänestysvastauksesta tai hakutuloksesta. Anna esimerkiksi `2020-141`. Älä anna tähän PTK-asiakirjatunnusta.
