# Kansanedustajat

## Identiteetti ja lähde

Käytä perustietoon kategoriaa `kansanedustaja`, `GET /kansanedustajat` -listausta tai `GET /kansanedustajat/{id}` -detail-endpointia. Listaus sisältää myös entisiä edustajia, joten se ei sellaisenaan tarkoita nykyisiä kansanedustajia. Poimi `henkilonro` saman henkilön varmennetusta hakutuloksesta ja tarkista, että detail-vastauksen nimi täsmää. Älä koskaan arvaa henkilönumeroa tai liitä henkilöitä pelkän nimen perusteella.

Perusobjektissa voi olla:

- nimi, kutsumanimi ja `henkilonro`
- syntymä- ja kuolinvuosi
- `edustajantoimenTila`
- `viimeisinEduskuntaryhma` ja historialliset `eduskuntaryhmat`
- `edustajatoimet`
- `viimeisinVaalipiiri` ja historialliset `vaalipiirit`
- `valiokuntajasenyydet` ja `toimielinjasenyydet`
- `eduskuntaryhmaTehtavat`
- `valtioneuvostonJasenyydet` ja `nykyinenMinisteriys`
- `sidonnaisuudet`, `koulutukset`, `tyoura`
- keskeytykset ja sijaisuudet

## Nykyisyys ja historia

“Nykyinen kansanedustaja” rajataan yleensä `edustajantoimenTila = Nykyinen`. Tarkista lisäksi avoin `edustajatoimi`, jos tulos on yllättävä. Ilmoita noutopäivä.

Historiallisessa kysymyksessä älä käytä `viimeisinEduskuntaryhma`- tai `viimeisinVaalipiiri`-kenttää kysytyn vuoden tietona. Valitse jäsenyydet aikavälien perusteella.

Kaksi jaksoa ovat päällekkäin, kun:

```text
jäsenyys.alku <= kysymys.loppu
ja
(jäsenyys.loppu puuttuu tai jäsenyys.loppu >= kysymys.alku)
```

Jos ryhmäjäsenyys ja toimielinjäsenyys vaaditaan samanaikaisesti, varmista, että molemmat leikkaavat käyttäjän aikavälin. Kerro, jos niiden keskinäistä samanaikaisuutta ei ole laskettu tarkemmin.

## Nimihaku

Hae ensin kutsumanimi + sukunimi tai koko nimi. Suomen taivutusmuoto pitää palauttaa perusmuotoon: `Arhinmäen` -> `Arhinmäki`. Älä muuta erisnimeä aggressiivisella stemmauksella. Jos samannimisiä henkilöitä on useita, erittele vaihtoehdot tai pyydä täsmennys.

## Ryhmät, vaalipiirit ja tehtävät

- Käytä nykyiseen ryhmään `viimeisinEduskuntaryhma`-objektia vain nykyhetken vastauksessa.
- Käytä historiallisiin ryhmiin `eduskuntaryhmat`-listaa ja päivämääriä.
- Käytä vaalipiirihistoriaan `vaalipiirit`-listaa.
- Käytä ministeritehtäviin `valtioneuvostonJasenyydet`-tietoja. Huomioi nimivariaatiot, kuten `sisäministeri` ja `sisäasiainministeri`.
- Käytä valiokunta- ja muihin toimielintehtäviin oikeaa jäsenyyslistaa sekä roolia ja aikaväliä.
- Erottele jäsenyys, puheenjohtajuus, varapuheenjohtajuus ja varajäsenyys.

## Sidonnaisuudet ja taustatiedot

Sidonnaisuudet, tulot ja lahjat voivat olla kieli- ja vuosikohtaisia. Ryhmittele `ryhmaotsikko`-kentän mukaan ja näytä ilmoitusvuosi tai ajankohta. Älä väitä historiallista aineistoa täydelliseksi, jos API:ssa näkyy vain nykyinen tai rajallinen historia.

Ammatti, koulutus ja työura ovat vapaita tekstikenttiä. Jos käyttäjä kysyy esimerkiksi “sosiaalialan” tai “lääkärin” määrää, määrittele täsmälliset hyväksyttävät nimikkeet, näytä ne ja tee tarvittaessa herkkyystarkistus laajemmalla ja suppeammalla luokituksella.

## Ikä ja kokemus

`syntymavuosi` ei riitä tarkkaan ikään päivinä tai kuukausina. Käytä ilmaisua “täyttää/täytti kuluvana vuonna” tai “syntymävuoden perusteella”. Ikäryhmien tulee olla aukottomia ja päällekkäisyydettömiä: alle 30, 30–34, …, 65–69, 70+.

Laske edustajakokemus `edustajatoimet`-jaksoista. Yhdistä päällekkäiset tai suoraan jatkuvat jaksot ennen kokonaiskeston laskua. Raportoi erikseen pisin yhtäjaksoinen kausi ja kaikkien jaksojen yhteiskesto, jos käyttäjän kysymys voi tarkoittaa kumpaa tahansa.

## Vastauslista

Kun listaat henkilöitä, anna vähintään:

- nimi
- kysytyn ajankohdan ryhmä/puolue
- kysytyn ajankohdan vaalipiiri
- kysymykseen kuuluva rooli ja aikajakso
- `henkilonro` tai linkki henkilön API-detailiin

Älä näytä nykyistä ryhmää historiallisena ryhmänä vain siksi, että se on helpommin saatavilla.
