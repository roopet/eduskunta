# Copilot Studio -työkalureseptit

## Sisällysluettelo

- [Yhteystesti](#yhteystesti)
- [Haku ja määrä](#haku-ja-määrä)
- [Valtiopäiväasia](#valtiopäiväasia)
- [Asiakirja](#asiakirja)
- [Kansanedustaja](#kansanedustaja)
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

Käytä `GetMatterDocuments`-toimintoa saman asian asiakirjojen inventointiin. Valitse tarvittava `edktunnus` asiakirjatyypin, kielen ja päivämäärän perusteella.

## Asiakirja

Käytä ensin `GetDocumentMetadata`-toimintoa. Kun vastaus edellyttää asiakirjan sisältöä, kutsu `GetDocumentHtml` samalla EDK-tunnuksella.

Anna tunnus normaalissa muodossa:

```text
EDK-2019-AK-243347
```

HTML-vastaus voi olla pitkä. Poimi vain väitteen kannalta olennaiset otsikot ja kappaleet. Älä tulkitse navigaatiotekstiä asiakirjan sisällöksi.

## Kansanedustaja

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

## Äänestykset

Käytä `GetMatterVotes`-toimintoa asian kaikkien äänestysten inventointiin. Anna esimerkiksi:

```text
KAA 1/2019 vp
```

Kutsu jokaiselle olennaiselle tunnukselle `GetVote`. Lue kysymyksenasettelu ennen jaa/ei-tuloksen tulkintaa.

Käytä `GetSessionVotes`-toimintoa, kun rajaus on täysistunto. Poimi äänestys-API:n käyttämä `istunnonTunniste` toisesta äänestysvastauksesta tai hakutuloksesta. Anna esimerkiksi `2020-141`. Älä anna tähän PTK-asiakirjatunnusta.
