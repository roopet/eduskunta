# Valtiopäiväasiat, asiakirjat ja käsittely

## Sisällysluettelo

- [Suositeltu hakujärjestys](#suositeltu-hakujärjestys)
- [Vp-asian detail-vastaus](#vp-asian-detail-vastaus)
- [Asiakirjainventaario](#asiakirjainventaario)
- [Käsittelyn tulkinta](#käsittelyn-tulkinta)
- [Kieli ja valiokunta](#kieli-ja-valiokunta)
- [Sisällön lukeminen](#sisällön-lukeminen)
- [Linkit](#linkit)

## Suositeltu hakujärjestys

1. Hae ehdokkaat kategoriasta `valtiopaivaasia` asiatason ehdoilla: vuosi, asiatyyppi, tunnus, nimeke, asiasanat ja aihe.
2. Rajaa ehdokasjoukko ja deduplikoi `eduskuntatunnus.fi`-arvolla.
3. Nouda valitun asian detail-vastaus: `GET /valtiopaivaasiat/{eduskuntatunnus+}`.
4. Inventoi asiaan liittyvät asiakirjat detail-vastauksesta ja tarvittaessa `GET /asiakirjat/eduskuntatunnus/{eduskuntatunnus+}` -endpointista.
5. Rajaa asiakirjat tyypin, kielen, valiokunnan, laatijan ja päivämäärän perusteella.
6. Nouda HTML/XML/PDF vasta, kun sisältöä tarvitaan.

Älä käytä yksittäisen asiakirjan tyyppiä ensimmäisen asiatason aihehaun korvikkeena. Huomaa kuitenkin, että `valtiopaivaasia`-kategoriassa kenttä `asiakirjatyyppikoodi.fi` on API:n asiatyyppikoodi, esimerkiksi HE tai KAA. Kentän nimi on historiallisesti harhaanjohtava.

## Vp-asian detail-vastaus

Tarkista ainakin:

- `eduskuntatunnus`, `asiakirjatyyppikoodi`, `asiakirjatyyppinimi`, `nimeke`
- `tila`, `kokonaispaatosnimi`, `laadintapvm`, `paattymispvm`
- `viimeisinKasittelyvaihe`
- `asiasanat`
- `ehdotukset`
- `kasittelyt`
- `keskeisetAsiakirjat`
- `kasittelynAsiakirjat`
- `asiantuntijalausunnot`
- `viittaavatAsiat`, `yhdistetytAsiat`, `euViittaukset`, `multiviitteet`

Useat kentät ovat kieliobjekteja (`fi`, `sv`). `kasittelynAsiakirjat` voi olla lista listoja. Käsittele puuttuvat ja tyhjät rakenteet normaalina vaihteluna, älä skeemavirheenä.

## Asiakirjainventaario

Kerää yhdestä asiakirjasta vähintään:

- `edktunnus`
- asiakirjan `eduskuntatunnus`
- asian `eduskuntatunnus`
- `asiakirjatyyppikoodi` ja `asiakirjatyyppinimi`
- `nimeketeksti`
- `valiokuntanimi`
- `laadintapvm`
- kieli
- `htmlSaatavilla` ja `liiteSaatavilla`
- lähderakenne: keskeinen asiakirja, käsittelyasiakirja tai asiantuntijalausunto
- API- ja julkinen URL

Litistä `kasittelynAsiakirjat` varovasti. Yhdistä rakenteet, mutta deduplikoi ensisijaisesti `edktunnus`-arvolla. Jos `edktunnus` puuttuu, käytä varatunnuksena yhdistelmää `eduskuntatunnus + asiakirjatyyppikoodi + kieli + laadintapvm`, ja kerro heikompi varmuus.

Asiantuntija-aineiston yleisiä koodeja:

- `AL`: asiantuntijalausunto
- `ALL`: asiantuntijalausunnon liite
- `V`: vastine
- `LS`: lisäselvitys

Nouda ajantasainen nimi ja aktiivisuustieto `/reference-data/asiakirjatyypit`-endpointista.

## Käsittelyn tulkinta

Järjestä `kasittelyt.fi` tapahtumapäivän ja tarvittaessa `jarjestys`-kentän mukaan. Älä päättele lopputulosta vain viimeisestä vapaamuotoisesta fraasista.

- `tila`: nykyinen yleinen tilanne.
- `viimeisinKasittelyvaihe`: viimeisin indeksoitu vaihe, ei välttämättä lopputulos.
- `kokonaispaatosnimi`: asian kokonaisratkaisun nimike, jos ratkaisu on syntynyt.
- `ehdotukset[].paatosnimi`: yksittäisen ehdotuksen päätös; yhdessä asiassa voi olla useita lakiehdotuksia eri lopputuloksin.
- `paattymispvm`: käsittelyn päättymispäivä, jos tallennettu.

Lakiehdotus käsitellään valiokunnan mietinnön pohjalta kahdessa täysistuntokäsittelyssä. Ensimmäisessä päätetään sisällöstä; toisessa hyväksymisestä tai hylkäämisestä ja mahdollisista lausumista. Älä merkitse ensimmäisessä käsittelyssä hyväksyttyä sisältöä lopullisesti hyväksytyksi laiksi.

Valiokunnan mietintö valmistelee asian täysistunnolle. Valiokunnan lausunto annetaan yleensä toiselle valiokunnalle. Asiantuntijalausunto on kuultavan henkilön tai organisaation toimittama aineisto.

## Kieli ja valiokunta

Sama asiakirja voi esiintyä suomeksi ja ruotsiksi. Rajaa kieli asiakirjatasolla `kielikoodi`-kentästä tai inventaarion kielirakenteesta. Jos kenttä puuttuu, käytä tunnistamiseen varovasti tyyppikoodia, tyyppinimeä ja otsikkoa; merkitse tämä päätelmäksi.

Valiokunta voi näkyä `valiokuntanimi`-kentässä, asiakirjatunnuksessa, tyyppikoodissa tai otsikossa. Nouda viralliset valiokunnat `/reference-data/valiokunnat`-endpointista. Tunnista lyhenteet sanareunoilla: esimerkiksi `LiV` ei saa osua sanan sisään. Historiallisissa aineistoissa sama nimi voi esiintyä usealla tunnuksella.

## Sisällön lukeminen

Ensisijainen järjestys:

1. `GET /asiakirjat/edktunnus/{edktunnus+}/html`
2. `GET /asiakirjat/edktunnus/{id+}/xml`
3. `GET /asiakirjat/edktunnus/{edktunnus+}/pdf`

HTML/XML säilyttää usein otsikot ja kappaleet PDF:ää paremmin. Tallenna jokaiselle poimitulle katkelmalle asiantunnus, `edktunnus`, lähde-URL, otsikko tai kappaleindeksi ja alkuperäinen teksti.

Valiokunta-asiakirjasta tarkista osumakohdan lisäksi ainakin mahdolliset osiot `Valiokunnan perustelut`, `Yleisperustelut`, `Johtopäätökset`, `Päätösehdotus` tai `Päätösesitys`, vastalauseet ja eriävät mielipiteet. Otsikot vaihtelevat.

## Linkit

Muodosta URL-koodatut linkit:

- asia: `https://www.eduskunta.fi/asiat-ja-aanestykset/valtiopaivaasiat/{eduskuntatunnus}`
- asiakirja: `https://www.eduskunta.fi/asiat-ja-aanestykset/valtiopaivaasiat/asiakirjat/edktunnus/{edktunnus}/pdf`

Koodaa myös kauttaviiva (`/` -> `%2F`) ja välilyönnit, kun muodostat käyttäjälle näytettävän lähdelinkin. Anna REST API -toolin tunnusparametri normaalissa muodossa; connector huolehtii työkalukutsun URL-koodauksesta.
