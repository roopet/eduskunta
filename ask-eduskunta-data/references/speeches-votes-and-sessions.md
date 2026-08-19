# Puheenvuorot, pöytäkirjat, istunnot ja äänestykset

## Puheenvuorot

Hae kategoriasta `puheenvuoro`. Keskeisiä kenttiä ovat:

- `id`, `tunnus`, `valtiopaivavuosi`, `taysistuntonumero`
- `asia.fi.eduskuntatunnus` ja asian nimeke
- `poytakirjanasiankohta.fi.eduskuntatunnus`, kohtanumero ja nimeke
- `puhuja` ja puhujan `henkilonro`
- `puheenvuorotyyppikoodi` ja `puheenvuorotyyppinimi`
- `aloitushetki`, `lopetushetki`, `kellonaika`
- `puheenvuoro` ja `puheenvuoroXml`

Rajaa suuret haut istunnon tai valtiopäivävuoden ja `taysistuntonumero`-kentän mukaan. Yhden vuoden puheenvuoroja voi olla yli 10 000, joten älä yritä hakea koko vuotta yhtenä kyselynä.

Henkilön puheenvuorohaku:

1. tunnista henkilö `kansanedustaja`-kategoriasta ja varmista `henkilonro`;
2. suodata puheenvuorot puhujan tunnuksella, ei vain nimitekstillä;
3. rajaa istunto, päivä tai asia;
4. tarkista puheenvuoron `asia` ja pöytäkirjan asiakohta;
5. lue puheenvuoron teksti ennen sisältöväitettä.

Läsnäolo täysistunnossa ei osoita puheenvuoroa tietyssä asiassa. Samana päivänä pidetty puheenvuoro ei osoita yhteyttä kysyttyyn asiaan, ellei asiakohta tai asiakirjaviite tue sitä.

Nouda puheenvuorotyyppien ajantasaiset nimet `/reference-data/puheenvuorotyypit`-endpointista. Tyypillisiä koodeja ovat E (esittely), N (nopeatahtinen), R (ryhmä), T (varsinainen) ja V (vastaus), mutta älä oleta listaa pysyväksi.

## Pöytäkirjan asiakohta

Käytä:

- `GET /taysistunnot/poytakirja-asiakohdat/{eduskuntatunnus+}/html`
- `GET /taysistunnot/poytakirja-asiakohdat/{eduskuntatunnus+}/nav/html`

Pöytäkirjan asiakohdan tunnus voi olla eri kuin asian varsinainen `HE ... vp` -tunnus. Säilytä molemmat. Asiakohta antaa keskustelu- ja päätöskontekstin, kun puheenvuorohaku antaa yksittäiset puheet.

## Äänestykset

Hakukategoria `aanestys` soveltuu äänestysten löytämiseen ja määrällisiin hakuihin. Käytä detail-endpointteja varmennukseen:

- `GET /taysistunnot/aanestykset/{aanestystunnus+}`: yksi äänestys
- `GET /taysistunnot/istunnon-aanestykset/{istuntotunnus+}`: istunnon kaikki äänestykset
- `GET /taysistunnot/asian-aanestykset/{eduskuntatunnus+}`: asian kaikki äänestykset
- `GET /taysistunnot/uusimmat-aanestykset`: viimeisimmät äänestykset

Äänestysobjektissa voi olla:

- `id`, `istunnonTunniste`, `istuntopvm`, `istuntonumero`
- `aanestysnumero`, alku- ja loppuaika
- `aanestysotsikko` ja päiväjärjestysotsikko
- `kohta`
- `aanestysmitatoity`
- `aanestystulos`
- `aanestystapahtumat` eli edustajakohtaiset äänet
- ryhmä-, vaalipiiri- ja hallitus/oppositiojakaumat

Erota:

- äänestysten lukumäärä;
- annettujen edustajaäänten lukumäärä;
- jaa/ei/tyhjä/poissa-jakauma;
- enemmistön marginaali;
- asian lopullinen päätös.

Ohita mitätöity äänestys oletuksena vain, jos käyttäjä kysyy päteviä tuloksia. Jos käyttäjä kysyy, mitä äänestyksiä “oli”, näytä myös mitätöidyt erikseen.

Älä päättele asian hyväksymistä yhden äänestyksen jaa-enemmistöstä ilman äänestyksen kysymyksenasettelua ja asian käsittelyvaihetta. Jaa voi tarkoittaa esimerkiksi valiokunnan ehdotusta, vastaehdotusta tai äänestysjärjestystä.

## Määrähaut

- Puheenvuorot: deduplikoi puheenvuoron `id`-arvolla.
- Pöytäkirjan asiakohdat: deduplikoi asiakohdan tunnuksella.
- Äänestykset: deduplikoi äänestyksen `id`-arvolla ja käsittele `aanestysmitatoity` erikseen.
- Edustajakohtaiset äänet: deduplikoi yhdistelmällä äänestys-id + `henkilonro`.

Jaa yli 10 000 osuman puheenvuorohaku valtiopäivävuoden sisällä istunnoittain. Selvitä istunnot viitetiedoista tai pöytäkirja-asiakirjoista, älä oleta istuntonumeroiden aukotonta sarjaa ilman tarkistusta.

## Lähteet

Käytä vastauksessa äänestyksen tai pöytäkirjan API-URL:ia sekä mahdollisuuksien mukaan asian julkista sivua. Eduskunnan verkkolähetyssivu voi täydentää videokontekstia, mutta API:n pöytäkirja ja äänestysdata ovat tekstiväitteen ensisijaiset lähteet.

