# Copilot Studio -paketti

Tämä hakemisto sovittaa `ask-eduskunta-data`-taidon Copilot Studioon. Copilot Studiossa skill antaa semanttiset toimintaohjeet, mutta ulkoinen Eduskunta Public API pitää lisätä agentille erillisenä REST API -toolina.

## Sisältö

- `eduskunta-api.swagger.json`: suppea, vain lukemiseen tarkoitettu Swagger 2.0 -kuvaus Copilot Studioa varten
- `skill-package/`: Copilot Studioon ladattavan skill-paketin lähdetiedostot
- `ask-eduskunta-data-copilot-studio.zip`: suoraan ladattava skill-paketti, jossa `SKILL.md` on ZIP-tiedoston juuressa

## 1. Luo REST API -tool

1. Avaa Copilot Studion vasemman reunan **Tools**-sivu.
2. Valitse **New tool > REST API**. Jos vaihtoehto näkyy suoraan agentin Build-näkymässä, voit aloittaa myös sieltä.
3. Lataa `eduskunta-api.swagger.json`.
4. Anna kuvaukseksi esimerkiksi: `Hakee Suomen eduskunnan virallista avointa dataa. Käytä kaikkiin valtiopäiväasioita, asiakirjoja, kansanedustajia, puheenvuoroja ja äänestyksiä koskeviin tietohakuihin.`
5. Valitse autentikoinniksi **None**. Eduskunnan julkinen API ei määrittele autentikointia.
6. Valitse kaikki Swaggerin tarjoamat read-only-toiminnot ja julkaise tool.
7. Luo pyydetty yhteys, lisää toiminnot agentille ja varmista, että ne ovat **Enabled**.
8. Salli agentin päättää dynaamisesti, milloin toimintoa käytetään. Valitse completion-asetukseksi agentin oma kontekstuaalinen vastaus.

Copilot Studio luo REST API -toolille taustalla custom connectorin. Ympäristön DLP- ja Advanced Connector Policy -sääntöjen pitää sallia connector ja host `api.eduskunta.fi`.

Microsoftin ohjeet:

- [REST API -toolin lisääminen](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-rest-api)
- [Toolien lisääminen agentille](https://learn.microsoft.com/en-us/microsoft-copilot-studio/add-tools-custom-agent)
- [Custom connectorien DLP-hallinta](https://learn.microsoft.com/en-us/power-platform/admin/dlp-custom-connector-parity)

## 2. Lisää skill

Lataa agentin Build-näkymän Skills-osioon `ask-eduskunta-data-copilot-studio.zip`.

Jos rakennat paketin itse PowerShellillä, suorita tässä hakemistossa:

```powershell
Compress-Archive -Path '.\skill-package\*' -DestinationPath '.\ask-eduskunta-data-copilot-studio.zip' -Force
```

ZIP-tiedoston juuressa pitää olla `SKILL.md`; älä pakkaa itse `skill-package`-yläkansiota mukaan.

Jos agentissa on jo alkuperäinen skill-versio, korvaa se tällä versiolla. Copilot-versio kieltää Python-skriptin ja selaustyökalun käyttämisen API-kutsuihin ja ohjaa kutsut nimettyihin REST API -toimintoihin.

## 3. Tee yhteystesti

Testaa REST API -tool ensin erillään agentista:

1. Suorita `GetMatterTypes`. Toiminto ei tarvitse parametreja ja sen pitää palauttaa JSON sekä HTTP 200.
2. Suorita `CountParliamentData` tällä bodylla:

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

3. Suorita `GetParliamentaryMatter` tunnuksella `HE 60/2018 vp`.
4. Testaa vasta sitten Preview-chatissa esimerkiksi: `Miten HE 60/2018 vp eteni ja mikä oli lopputulos?`

## 4. Selvitä 403

Tarkista Preview-aktiviteetista epäonnistunut URL, vastausrunko ja toolin nimi.

| Havainto | Syy | Korjaus |
|---|---|---|
| URL alkaa `www.eduskunta.fi` | Agentti käytti selausta ja sivuston automaatiotorjunta esti kutsun | Korvaa skill Copilot-versiolla ja käytä vain REST API -toolia |
| `AppForbidden`, DLP tai policy mainitaan | Power Platform esti custom connectorin | Salli connector tai `api.eduskunta.fi` ympäristön DLP/ACP-säännöissä |
| Tool-yhteys pyytää tunnuksia | Autentikointi on määritelty väärin | Luo REST API -tool uudelleen autentikoinnilla **None** |
| `GetMatterTypes` palauttaa HTML-muotoisen 403:n | Kohdepalvelu torjuu Power Platformin ulospäin lähtevän kutsun | Käytä hallittua Azure Function- tai API Management -välityspalvelua |
| `GetMatterTypes` toimii, mutta tunnuksen sisältävä operaatio ei | Connectorin URL-koodaus ei sovi ympäristöön | Varmista ensin oletusarvo `single`; kokeile `double` vain, jos ympäristön välityskerros purkaa koodauksen ennen API:a |
| HTTP 429 | API:n kutsuraja ylittyi | Pienennä kutsutiheyttä, käytä count-operaatiota ja noudata `Retry-After`-aikaa |

Jos DLP-eston syy ei näy Previewssa, julkaise agentti testiympäristöön ja tarkista Monitor-näkymän epäonnistunut sessio sekä connectorin yhteystila.

## Välityspalvelin tarvittaessa

Jos suora REST API -tool saa jatkuvasti kohdepalvelun HTML-muotoisen 403-vastauksen, käytä Azure Functionia tai API Managementia välissä. Välityspalvelimen tulee:

- sallia vain tarvittavat read-only-operaatiot;
- lähettää `Accept: application/json` ja tunnistettava `User-Agent`;
- URL-koodata eduskuntatunnukset, istuntotunnukset ja äänestystunnukset;
- toteuttaa aikakatkaisu, rajatut uudelleenyritykset ja `Retry-After`;
- rajoittaa tuloskokoa ja välimuistittaa viitetietoja;
- lokittaa endpoint, status, kesto ja noutoaika ilman käyttäjän tarpeettomia henkilötietoja.
