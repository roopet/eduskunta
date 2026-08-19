---
name: ask-eduskunta-data
description: Hae, tulkitse, laske ja varmista Suomen eduskuntaa koskevaa tietoa agentille lisätyillä Eduskunta Public API -työkaluilla. Käytä taitoa valtiopäiväasioihin, asiakirjoihin, asiantuntijalausuntoihin, kansanedustajiin ja heidän ajallisiin jäsenyyksiinsä, täysistuntojen puheenvuoroihin ja pöytäkirjoihin, äänestyksiin, valiokuntiin, käsittelyvaiheisiin, eduskuntatilastoihin, eduskuntatunnuksiin ja määrällisiin vertailuihin.
---

# Kysy eduskuntatiedosta Copilot Studiossa

## Käytä vain rekisteröityjä työkaluja

Käytä ulkoisiin tietohakuihin vain agentille lisättyjä Eduskunta Public API -toimintoja. Älä yritä suorittaa Pythonia, komentorivikomentoja tai skill-paketin ulkopuolista koodia. Älä käytä verkkoselausta `api.eduskunta.fi`- tai `www.eduskunta.fi`-osoitteiden lukemiseen.

Käytä `www.eduskunta.fi`-linkkejä vain käyttäjälle näytettävinä lähdelinkkeinä. Varmista sisältö API:n HTML-toiminnolla.

Odotetut työkalutoiminnot ovat:

- `GetMatterTypes`
- `SearchParliamentData`
- `CountParliamentData`
- `GetParliamentaryMatter`
- `GetMatterDocuments`
- `GetDocumentMetadata`
- `GetDocumentHtml`
- `GetMember`
- `GetMatterVotes`
- `GetVote`
- `GetSessionVotes`

Jos tarvittava toiminto ei ole käytettävissä, kerro, että Eduskunta Public API -tool puuttuu tai on estetty. Älä arvaa vastausta.

## Määrittele kysymys

Kirjaa ennen hakua:

- entiteetti: asia, asiakirja, henkilö, puheenvuoro, pöytäkirjan asiakohta, äänestys vai tapahtuma;
- laskentayksikkö;
- aikarajaus: kalenterivuosi, valtiopäivävuosi, vaalikausi, hallituskausi, toimikausi vai istunto;
- kieli, asia- tai asiakirjatyyppi, valiokunta, henkilö ja aihe;
- millä lähdetasolla väite voidaan todentaa.

Älä samaista hallituskautta ja vaalikautta. Jos tulkinta muuttaa tulosta olennaisesti, kysy täsmennys. Muussa tapauksessa valitse perusteltu tulkinta ja kerro se vastauksessa.

Lue aina [concepts-and-reliability.md](references/concepts-and-reliability.md). Lue lisäksi vain tarpeelliset viitteet:

- asiat ja asiakirjat: [matters-and-documents.md](references/matters-and-documents.md)
- kansanedustajat: [members.md](references/members.md)
- puheenvuorot ja äänestykset: [speeches-votes-and-sessions.md](references/speeches-votes-and-sessions.md)
- määrät ja visualisoinnit: [statistics-and-counting.md](references/statistics-and-counting.md)
- hakurakenne: [api-search.md](references/api-search.md)
- Copilot-työkalureseptit: [copilot-tool-recipes.md](references/copilot-tool-recipes.md)

## Laadi hakusuunnitelma

Muodosta erikseen:

- kovat rajaukset: kategoria, tunnus, vuosi, tyyppi, valiokunta ja henkilö;
- pehmeät hakutermit: tarkka fraasi, perus- ja taivutusmuodot, varovainen vartalo ja synonyymit;
- poissulkevat ehdot;
- lähde, jolla lopullinen väite varmennetaan.

Säilytä ääkköset. Älä stemmaa erisnimiä tai lyhyitä lyhenteitä. Tee henkilöhaku ensin nimellä, poimi `henkilonro` samasta osumasta ja varmista nimi `GetMember`-vastauksesta.

## Hae ja sivuta

Käytä löytöhakuun `SearchParliamentData`-toimintoa. Käytä määriin ensisijaisesti `CountParliamentData`-toimintoa.

Tallenna päättelyssä vähintään:

- käytetty toiminto ja JSON-pyyntö;
- noutopäivä;
- `totalResultCount`, `actualResultCount` ja `startFromIndex`;
- löydetty tunnus ja käyttäjälle näytettävä lähde-URL;
- epäonnistuneet toiminnot.

Nouda seuraava sivu kasvattamalla `startFromIndex`-arvoa palautettujen osumien määrällä. Älä käytä yhden sivun `actualResultCount`-arvoa kokonaismääränä. Jaa yli 10 000 osuman haku ei-päällekkäisiin osiin.

Anna tunnukset työkaluille normaalissa muodossa, kuten `HE 60/2018 vp`. Connector huolehtii URL-koodauksesta.

## Varmista oikealla lähdetasolla

- Hakutulos osoittaa löydettävyyden ja perustiedot.
- `GetParliamentaryMatter` osoittaa asian tilan, vaiheet ja asiakirjasuhteet.
- `GetMatterDocuments` inventoi asiaan liittyvät asiakirjat.
- `GetDocumentMetadata` osoittaa asiakirjan metatiedot.
- `GetDocumentHtml` osoittaa asiakirjan varsinaisen sisällön.
- `GetMember` osoittaa henkilöhistorian ja aikavälilliset jäsenyydet.
- `GetMatterVotes` inventoi asian äänestykset.
- `GetVote` osoittaa kysymyksenasettelun, tuloksen ja edustajakohtaiset äänet.
- `GetSessionVotes` inventoi yhden täysistunnon äänestykset.

Älä päättele asiakirjan kantaa pelkästä otsikosta. Älä tulkitse puuttuvaa hakutulosta todisteeksi siitä, ettei tietoa ole.

Tee vähintään yksi ristikkäistarkistus, kun vastaus koskee lopputulosta, hyväksyttyä lakia, käsittelyajankohtaa, asiantuntijan väitettä, edustajan ääntä, historiallista jäsenyyttä tai useasta kyselystä koottua määrää.

## Käsittele virheet

- `401`: tarkista tool-yhteys; Eduskunnan API ei vaadi kirjautumista.
- `403` ja `AppForbidden` tai policy-viittaus: ilmoita Power Platformin DLP- tai connector-estosta.
- HTML-muotoinen `403`: ilmoita, että kohdepalvelun automaatiotorjunta esti kutsun.
- `429`: noudata `Retry-After`-aikaa ja pienennä kutsutiheyttä.
- `5xx`: yritä uudelleen rajatusti kasvavalla viiveellä.

Älä korvaa aikaisempaa onnistunutta tietoa tyhjällä virhevastauksella.

## Vastaa jäljitettävästi

Aloita suoralla vastauksella. Lisää tarpeen mukaan:

1. rajaus ja laskentayksikkö;
2. tunnukset, nimet, päivämäärät ja tila;
3. käyttäjälle avattavat Markdown-lähdelinkit;
4. hakutermit ja rakenteiset suodattimet;
5. kattavuus, noutopäivä ja epävarmuus.

Kerro suurissa tulosjoukoissa kokonaismäärä ja montako osumaa näytät. Käytä muotoiluja “API:n nykyisestä aineistosta löytyi”, “tällä rajauksella osumia oli” ja “ei voitu varmentaa”, kun ne kuvaavat evidenssiä täsmällisesti.

## Lopputarkistus

- Ovatko asia ja asiakirja erillään?
- Onko aikarajaus määritelty?
- Onko henkilönumero poimittu varmennetusta osumasta?
- Onko kaikki sivut haettu tai käytetty count-toimintoa?
- Onko sisältöväite tarkistettu HTML-sisällöstä?
- Onko äänestyksen jaa/ei tulkittu kysymyksenasettelusta?
- Onko mukana lähdelinkki, noutopäivä ja epävarmuus?
