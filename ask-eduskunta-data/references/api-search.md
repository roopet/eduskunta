# API-haku

## Sisällysluettelo

- [Perusosoite ja kategoriat](#perusosoite-ja-kategoriat)
- [Hakupyyntö](#hakupyyntö)
- [Lausekeoperaattorit](#lausekeoperaattorit)
- [Sivutus ja rajat](#sivutus-ja-rajat)
- [GET ja POST](#get-ja-post)
- [Aggregaatiot ja viitetiedot](#aggregaatiot-ja-viitetiedot)
- [Virheenkäsittely](#virheenkäsittely)

## Perusosoite ja kategoriat

Perusosoite on `https://api.eduskunta.fi/api/v1`.

`/search` tukee OpenAPI-kuvauksen mukaan kategorioita:

- `kansanedustaja`
- `valtiopaivaasia`
- `asiakirja`
- `tapahtuma`
- `puheenvuoro`
- `aanestys`
- `yhteystieto`
- `sivu`
- `tiedosto`

Jätä `category` pois vain aidosti poikkikategoriaisessa löytöhaussa. Tee varmennus aina oikeassa kategoriassa.

## Hakupyyntö

```json
{
  "query": "sähköinen asiointi",
  "langCode": "fi",
  "category": "valtiopaivaasia",
  "maxResults": 100,
  "startFromIndex": 0,
  "expression": {
    "and": [
      {"property": "valtiopaivavuosi.fi", "match": "2025"},
      {"property": "asiakirjatyyppikoodi.fi", "match": "HE"}
    ]
  },
  "sort": [
    {"property": "laadintapvm", "ascending": false}
  ]
}
```

`query` on sumea tekstihaku. `expression` on rakenteinen rajaus. Kun molemmat annetaan, tekstiosumat rajataan lausekkeella. Eksplisiittinen `sort` ohittaa tekstirelevanssin ensisijaisena järjestyksenä.

`langCode` on OpenAPI-kuvauksen mukaan tuettu ainakin kategorioissa `kansanedustaja`, `valtiopaivaasia` ja `aanestys`. Asiakirjoissa käytä tarvittaessa `kielikoodi`-kenttää.

## Lausekeoperaattorit

**Osittainen tekstiosuma:**

```json
{"property": "nimeketeksti", "match": "tietojärjestelm"}
```

**Fraasiosuma:**

```json
{"property": "istuntopvm", "match_phrase": "2026-06"}
```

**AND / OR / NOT:**

```json
{
  "and": [
    {"property": "edustajantoimenTila", "match": "Nykyinen"},
    {"not": {"property": "sukunimi", "match": "Esimerkki"}}
  ]
}
```

**Sisäkkäinen objekti tai lista:**

```json
{
  "property": "eduskuntaryhmat",
  "with": {"property": "nimi", "match": "kokoomuksen"}
}
```

`with` on olennainen, jotta usea ehto kohdistuu saman sisäkkäisen tietueen sisälle.

**Kokonaislukuväli:** `from` sisältyy, `to` ei sisälly.

```json
{"property": "syntymavuosi", "from": 1970, "to": 1980}
```

**Päivämääräväli:** `fromDate` sisältyy, `toDate` ei sisälly.

```json
{"property": "laadintapvm", "fromDate": "2024-01-01", "toDate": "2025-01-01"}
```

**Olemassaolo:**

```json
{"exists": "loppupvm"}
```

**Täsmällinen boolean tai kokonaisluku:**

```json
{"property": "aktiivinen", "boolValue": true}
```

```json
{"property": "aanestysnumero", "intValue": 3}
```

**Tunnuslista:**

```json
{"ids": ["123", "456"]}
```

## Sivutus ja rajat

Yhden haun dokumentoitu enimmäistulosmäärä on 10 000. `SearchResponse.searchMetadata` sisältää:

- `totalResultCount`
- `actualResultCount`
- `requestedResultCount`
- `startFromIndex`
- `maxScore`

Kasvata `startFromIndex`-arvoa todellisella sivukoolla. Lopeta, kun tuloksia ei enää ole tai indeksi saavuttaa `totalResultCount`-arvon. Jos kokonaismäärä ylittää 10 000, jaa haku ei-päällekkäisiin vuosi-, istunto-, asiatyyppi- tai muuhun luotettavaan osaan. Tarkista osien summa `/search/count`-kutsuilla.

Älä käytä yhden sivun `actualResultCount`-arvoa kokonaismääränä.

## GET ja POST

GET välittää saman JSON-pyynnön `q`-parametrissa. POST lähettää JSON-rungon. Käytä GET:iä lyhyisiin pyyntöihin ja POST:ia pitkiin tai selkeyttä vaativiin pyyntöihin. OpenAPI-kuvaus varoittaa suurten vastausten 302-uudelleenohjauksesta; salli redirectit.

OpenAPI-kuvauksen 19.8.2026 teksti ilmoitti POST-rajaksi 450 pyyntöä / 3000 sekuntia / IP. Tarkista nykyinen kuvaus ennen laajaa ajoa. Noudata lisäksi `429`-vastauksen `Retry-After`-otsaketta. Älä päättele vanhan esimerkkidokumentin rajoja pysyviksi.

## Aggregaatiot ja viitetiedot

`POST /aggregations/unique-by` palauttaa kenttien yksilölliset arvot ja määrät. Esimerkiksi:

```json
{
  "category": "asiakirja",
  "agg": {"unique": {"terms": ["asiakirjatyyppinimi"]}}
}
```

Käytä viitetietoja ennen kovakoodattuja nimiä:

- `/reference-data/asiatyypit`
- `/reference-data/asiakirjatyypit`
- `/reference-data/valiokunnat`
- `/reference-data/eduskuntaryhmat`
- `/reference-data/vaalipiirit`
- `/reference-data/valtiopaivat`
- `/reference-data/vaalikaudet`
- `/reference-data/puheenvuorotyypit`

Viitetiedoissa voi olla aktiivisia ja historiallisia tunnuksia. Valitse ajanjaksoon sopiva tietue, älä vain ensimmäistä samannimistä.

## Virheenkäsittely

- Uudelleenyrityä vain tilapäiset `429`, `500`, `502`, `503` ja `504` sekä verkkovirheet.
- Käytä kasvavaa viivettä ja `Retry-After`-arvoa.
- Tallenna onnistuneet sivut ennen seuraavaa kutsua.
- Säilytä epäonnistuneiden endpointien, tunnusten ja sivujen lista.
- Älä korvaa aikaisempaa onnistunutta aineistoa tyhjällä korjausajolla.
- Raportoi käyttäjälle, jos kokonaisuutta ei saatu sivutettua loppuun.

Virallinen skeema: https://api.eduskunta.fi/openapi.json

