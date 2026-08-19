---
name: ask-eduskunta-data
description: Hae, tulkitse, laske ja varmista Suomen eduskuntaa koskevaa tietoa Eduskunta Public API -rajapinnasta. Käytä taitoa, kun kysymys koskee valtiopäiväasioita, niihin liittyviä asiakirjoja tai asiantuntijalausuntoja, kansanedustajia ja heidän ajallisia jäsenyyksiään, täysistuntojen puheenvuoroja tai pöytäkirjoja, äänestyksiä, valiokuntia, asian käsittelyvaiheita, eduskuntatilastoja tai näiden lähteistettyä visualisointia. Käytä myös silloin, kun käyttäjä mainitsee eduskuntatunnuksen, EDK-tunnuksen, istuntotunnuksen tai äänestystunnuksen taikka pyytää määrällistä vertailua eduskuntadatasta.
---

# Kysy eduskuntatiedosta

## Tavoite

Muodosta Eduskunnan avoimesta datasta luotettava, jäljitettävä vastaus. Erottele käsitteet ennen hakua, varmista sisältö väitteen edellyttämältä lähdetasolta ja kerro rajaukset sekä epävarmuus käyttäjän kielellä.

## Toimi tässä järjestyksessä

### 1. Määrittele kysymys

Kirjaa ennen hakua:

- mitä entiteettiä kysytään: asia, asiakirja, henkilö, puheenvuoro, pöytäkirjan asiakohta, äänestys vai tapahtuma;
- mikä on laskentayksikkö;
- aikarajaus ja tarkoittaako se kalenterivuotta, valtiopäivävuotta, vaalikautta, hallituskautta, toimikautta vai istuntoa;
- kieli, asiatyyppi, asiakirjatyyppi, valiokunta, henkilö tai aihe;
- millä lähteellä väite voidaan todentaa.

Älä samaista hallituskautta ja vaalikautta. Jos käyttäjän käyttämä ilmaus muuttaa tulosta olennaisesti, kysy täsmennys. Muussa tapauksessa valitse perusteltu tulkinta ja kerro se vastauksessa.

Lue aina [concepts-and-reliability.md](references/concepts-and-reliability.md). Lue lisäksi vain kysymystä vastaavat viitteet:

- vp-asiat, asiakirjat ja käsittely: [matters-and-documents.md](references/matters-and-documents.md)
- kansanedustajat: [members.md](references/members.md)
- puheenvuorot, pöytäkirjat, istunnot ja äänestykset: [speeches-votes-and-sessions.md](references/speeches-votes-and-sessions.md)
- määrät, trendit ja visualisoinnit: [statistics-and-counting.md](references/statistics-and-counting.md)
- hakurakenne ja operaattorit: [api-search.md](references/api-search.md)
- valmiit kyselymallit: [query-recipes.md](references/query-recipes.md)

### 2. Laadi hakusuunnitelma

Muodosta erikseen:

- kovat rajaukset: kategoria, tunnus, vuosi/aikaväli, asia- tai asiakirjatyyppi, valiokunta, henkilö;
- pehmeät hakutermit: tarkka fraasi, perusmuodot, taivutusmuodot, varovaiset vartalot, synonyymit ja viralliset asiasanat;
- poissulkevat ehdot;
- tarkistuslähteet ja vaihtoehtoinen haku, jos ensimmäinen haku jää epävarmaksi.

Säilytä ääkköset. Älä stemmaa erisnimiä tai lyhyitä lyhenteitä. Tee henkilöhaku ensin täsmällisellä nimellä ja varmista henkilö `henkilonro`-tunnuksella.

### 3. Hae ja tallenna auditointitiedot

Käytä `scripts/eduskunta_api.py`-apuohjelmaa, jos Python on käytettävissä. Se hoitaa tunnusten URL-koodauksen, GET/POST-valinnan, sivutuksen, uudelleenyritykset ja noutoajan kirjaamisen.

```powershell
python scripts/eduskunta_api.py matter "HE 60/2018 vp"
python scripts/eduskunta_api.py documents "HE 60/2018 vp"
python scripts/eduskunta_api.py search --payload query.json --all
python scripts/eduskunta_api.py count --payload query.json
```

Jos apuohjelmaa ei voi ajaa, tee samat kutsut HTTP-työkalulla. Säilytä vähintään:

- API-perusosoite ja endpoint;
- JSON-pyyntö;
- noutoaika aikavyöhykkeineen;
- `totalResultCount`, `actualResultCount`, sivut ja mahdolliset virheet;
- tunnukset ja lähde-URL:t.

Nouda ajantasaiset koodit `reference-data`-endpointeista, kun rajaus riippuu koodista. Tarkista tarvittaessa myös `https://api.eduskunta.fi/openapi.json`, koska skeema ja käyttörajat voivat muuttua.

### 4. Varmista oikealla lähdetasolla

Noudata vähimmäistasoa:

- olemassaolo, otsikko ja perustiedot: hakutulos;
- asian tila, vaiheet, asiakirjasuhteet ja ehdotukset: vp-asian detail-vastaus;
- asiakirjan sisältö: asiakirjan HTML/XML tai tarvittaessa PDF;
- puheenvuoron sisältö ja puhuja: `puheenvuoro`-hakutulos sekä pöytäkirjan asiakohta;
- äänestyksen tulos ja edustajakohtaiset äänet: äänestyksen detail-endpoint;
- henkilön historia: henkilön detail-vastaus ja aikavälilliset jäsenyydet;
- määrät: `/search/count` tai kokonaan sivutettu ja tunnuksella deduplikoitu aineisto.

Älä päättele asiakirjan tai lausunnon kantaa pelkästä otsikosta. Älä tulkitse hakutuloksen puuttumista todisteeksi siitä, ettei tietoa tai tapahtumaa ole olemassa.

### 5. Tarkista ristiriidat

Tee vähintään yksi ristikkäistarkistus, kun vastaus koskee:

- lopputulosta tai lain hyväksymistä;
- eri käsittelyvaiheiden ajankohtaa;
- asiantuntijan väitteen sisältöä;
- yksittäisen edustajan äänestyskäyttäytymistä;
- historiallista puolue-, vaalipiiri-, ministeri- tai valiokuntatietoa;
- määrää, joka on koottu useasta kyselystä.

Jos metadata ja asiakirjan teksti poikkeavat, kerro ristiriita. Suosi väitettä suoraan osoittavaa alkuperäisasiakirjaa ja säilytä metadata kontekstina.

### 6. Vastaa jäljitettävästi

Aloita suoralla vastauksella. Lisää tarpeen mukaan:

1. rajaus ja laskentayksikkö;
2. tunnukset, nimet, päivämäärät ja status;
3. lähdelinkit Markdown-linkkeinä;
4. lyhyt kuvaus hakutermeistä ja suodattimista;
5. kattavuus, epävarmuus ja se, mitä ei voitu varmentaa.

Kerro suurissa tulosjoukoissa kokonaismäärä ja montako osumaa näytät. Merkitse noutopäivä ajantasaisiin tietoihin, kuten nykyisiin kansanedustajiin, tehtäviin ja keskeneräisiin asioihin.

Käytä varovaista ilmaisua:

- “API:n nykyisestä aineistosta löytyi…”
- “Tällä rajauksella osumia oli…”
- “Sisältöä ei voitu varmentaa pelkistä metatiedoista.”
- “Hakutulos ei osoita, ettei tällaista asiakirjaa ole; se voi puuttua tai olla eri tavalla indeksoitu.”

## Visualisointi

Tee kuvio vasta, kun määritelmä ja data on tarkistettu. Sisällytä otsikkoon tai alaviitteeseen ajanjakso, laskentayksikkö, kieli- ja tyyppirajaukset, noutopäivä sekä Eduskunta Public API lähteenä. Älä piirrä kumulatiivista tai prosenttikuvaa, jos nimittäjä tai ajallinen kattavuus on epäselvä.

## Lopputarkistus

- Ovatko asia ja asiakirja erillään?
- Onko “lausunto” tulkittu oikein?
- Onko aikarajaus päällekkäisyyssäännön mukainen?
- Onko jokainen määrä laskettu oikealla tunnuksella?
- Onko kaikki sivut haettu tai käytetty `count`-endpointia?
- Onko yli 10 000 osuman haku jaettu ei-päällekkäisiin osiin?
- Onko sisältöväite tarkistettu tekstistä?
- Onko mukana suora julkinen lähdelinkki ja noutopäivä?
- Onko epävarmuus erotettu faktasta?

