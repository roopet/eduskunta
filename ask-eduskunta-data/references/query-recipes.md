# Kyselymallit

## Sisällysluettelo

- [Apuohjelman käyttö](#apuohjelman-käyttö)
- [Vp-asian haku](#vp-asian-haku)
- [Asiakirjahaku](#asiakirjahaku)
- [Kansanedustajat](#kansanedustajat)
- [Puheenvuorot](#puheenvuorot)
- [Äänestykset](#äänestykset)
- [Määrät](#määrät)
- [Aihehaku](#aihehaku)

## Apuohjelman käyttö

Suorita komennot taitokansion juuresta. Käytä ympäristön Pythonia.

```powershell
python scripts/eduskunta_api.py --help
```

Komennot tulostavat JSON-objektin, jossa on noutoaika, endpoint, pyyntö ja data. Ohjaa tulos tiedostoon vain, jos tarvitset auditointijäljen.

```powershell
python scripts/eduskunta_api.py matter "HE 60/2018 vp" --output he-60.json
python scripts/eduskunta_api.py documents "HE 60/2018 vp"
python scripts/eduskunta_api.py public-url matter "HE 60/2018 vp"
python scripts/eduskunta_api.py public-url document "EDK-2025-AK-8709"
```

## Vp-asian haku

Hallituksen esitykset vuodelta 2025:

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

```powershell
python scripts/eduskunta_api.py search --payload he-2025.json --all
```

Kun tunnus tunnetaan, siirry suoraan detailiin:

```powershell
python scripts/eduskunta_api.py matter "KAA 5/2022 vp"
```

## Asiakirjahaku

Liikenne- ja viestintävaliokunnan asiakirjat vuodelta 2023, joissa otsikko liittyy ajoneuvolakiin:

```json
{
  "query": "ajoneuvolaki",
  "category": "asiakirja",
  "maxResults": 100,
  "startFromIndex": 0,
  "expression": {
    "and": [
      {"property": "valtiopaivavuosi", "match": "2023"},
      {"property": "valiokuntanimi", "match": "Liikenne- ja viestintävaliokunta"},
      {"property": "kielikoodi", "match": "fi"}
    ]
  },
  "sort": [{"property": "laadintapvm", "ascending": false}]
}
```

Tarkista osuman metadata ja nouda sisältö:

```powershell
python scripts/eduskunta_api.py document "EDK-2023-AK-9899"
python scripts/eduskunta_api.py document-text "EDK-2023-AK-9899"
```

Jos etsit asiantuntijan lausuntoa tietystä asiasta, hae ensin vp-asia ja inventoi `asiantuntijalausunnot.fi`. Hae avoimesta `nimeketeksti`-kentästä henkilön koko nimeä, sukunimeä, organisaatiota ja aihetermien taivutusmuotoja. Vahvista väite dokumentin tekstistä.

## Kansanedustajat

Nykyiset kansanedustajat:

```json
{
  "category": "kansanedustaja",
  "maxResults": 300,
  "startFromIndex": 0,
  "expression": {
    "and": [
      {"property": "edustajantoimenTila", "match": "Nykyinen"}
    ]
  },
  "sort": [{"property": "henkilonro", "ascending": true}]
}
```

Nimihaku:

```json
{
  "category": "kansanedustaja",
  "maxResults": 20,
  "startFromIndex": 0,
  "expression": {
    "and": [
      {"property": "kutsumanimi", "match": "Ben"},
      {"property": "sukunimi", "match": "Zyskowicz"}
    ]
  }
}
```

Hae osuman `id` tai `henkilonro`, varmista nimi samasta osumasta ja nouda detail korvaamalla paikkamerkki saadulla numerolla. Älä arvaa numeroa:

```powershell
python scripts/eduskunta_api.py mp HENKILONRO
```

Historiallinen ryhmä + toimielin -kysymys edellyttää molempien listojen aikavälien tarkistamista detail-vastauksesta. Älä yritä ratkaista sitä vain sumealla `query`-haulla.

## Puheenvuorot

Yhden edustajan puheenvuorot tietyssä istunnossa:

```json
{
  "category": "puheenvuoro",
  "maxResults": 1000,
  "startFromIndex": 0,
  "expression": {
    "and": [
      {"property": "valtiopaivavuosi", "match": "2011"},
      {"property": "taysistuntonumero", "match": "20"},
      {"termWithIds": {"term": "puhuja.henkilonro", "ids": ["HENKILONRO"]}}
    ]
  }
}
```

Jos `termWithIds` ei toimi valitussa indeksissä, käytä dokumentaation mukaista sisäkkäistä `with`-ehtoa tai hae istunnon puheenvuorot ja suodata `puhuja.henkilonro` paikallisesti. Kerro paikallisesta suodatuksesta.

Varmista puheen yhteys asiaan `asia.fi.eduskuntatunnus`- tai `poytakirjanasiankohta.fi`-kentästä. Pelkkä päivämäärä ei riitä.

## Äänestykset

Asian äänestykset:

```powershell
python scripts/eduskunta_api.py matter-votes "KAA 1/2019 vp"
```

Istunnon äänestykset:

```powershell
python scripts/eduskunta_api.py session-votes "PTK 175/2014 vp"
```

Yksi äänestys:

```powershell
python scripts/eduskunta_api.py vote "AANESTYSTUNNUS"
```

Hakukategorian esimerkki tietyn kuukauden äänestyksille:

```json
{
  "category": "aanestys",
  "langCode": "fi",
  "maxResults": 1000,
  "startFromIndex": 0,
  "expression": {
    "and": [
      {"property": "istuntopvm", "match_phrase": "2026-06"}
    ]
  },
  "sort": [{"property": "aanestysalkuaika", "ascending": true}]
}
```

Lue kysymyksenasettelu ennen kuin tulkitset jaa/ei-tulosta.

## Määrät

Laske kansalaisaloitteet vuonna 2025:

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

```powershell
python scripts/eduskunta_api.py count --payload kaa-2025.json
```

Jos kysymys koskee hyväksyttyjä kansalaisaloitteita, määrittele ensin tarkoittaako “hyväksytty” aloitetta sellaisenaan, aloitteen pohjalta muutettuna hyväksyttyä lakia vai eduskunnan päätöstä ryhtyä valmisteluun. Nouda asioiden detailit ja tarkista päätökset; pelkkä vireilletulolaskenta ei vastaa kysymykseen.

## Aihehaku

Muodosta 3–10 termiä kolmessa ryhmässä:

1. tarkat fraasit;
2. perusmuodot ja taivutusmuodot;
3. läheiset käsitteet ja varovaiset vartalot.

Esimerkki “turvallisuusalan lainsäädäntö”:

- fraasit: `yksityinen turvallisuusala`, `järjestyksenvalvonta`
- perusmuodot: `vartiointi`, `järjestyksenvalvoja`, `pelastustoimi`, `poliisitoimi`
- vartalot: `vartioin`, `järjestyksenvalv`, `pelastustoim`, `poliisitoim`

Aja termiryhmät erillisinä kyselyinä, yhdistä `eduskuntatunnus.fi`-arvolla ja tallenna jokaiselle osumalle, mikä termi toi sen mukaan. Tarkista lopullinen relevanssi asiakirjan tekstistä.
