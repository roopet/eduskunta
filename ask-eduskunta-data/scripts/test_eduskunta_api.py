from __future__ import annotations

import json
import unittest
from urllib.parse import parse_qs, urlparse

from eduskunta_api import (
    EduskuntaClient,
    HttpResponse,
    SearchLimitError,
    encode_path_identifier,
    extract_html_blocks,
    public_document_url,
    public_matter_url,
)


class FakeSearchTransport:
    def __init__(self, total: int, row_factory=None) -> None:
        self.total = total
        self.row_factory = row_factory or (lambda index: {"id": str(index)})
        self.calls: list[dict[str, object]] = []

    def __call__(self, method, url, body, headers, timeout):
        if method == "GET":
            payload = json.loads(parse_qs(urlparse(url).query)["q"][0])
        else:
            payload = json.loads(body.decode("utf-8"))
        start = int(payload.get("startFromIndex", 0))
        size = int(payload.get("maxResults", 100))
        end = min(start + size, self.total)
        results = [self.row_factory(index) for index in range(start, end)]
        response = {
            "results": results,
            "searchMetadata": {
                "totalResultCount": self.total,
                "actualResultCount": len(results),
                "requestedResultCount": size,
                "startFromIndex": start,
                "maxScore": 1.0,
            },
        }
        self.calls.append({"method": method, "payload": payload})
        return HttpResponse(
            status=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps(response).encode("utf-8"),
            final_url=url,
        )


class ApiHelperTests(unittest.TestCase):
    def test_path_encoding_encodes_space_and_slash(self):
        self.assertEqual(encode_path_identifier("HE 60/2018 vp"), "HE%2060%2F2018%20vp")

    def test_public_urls_are_encoded(self):
        self.assertEqual(
            public_matter_url("HE 60/2018 vp"),
            "https://www.eduskunta.fi/asiat-ja-aanestykset/valtiopaivaasiat/HE%2060%2F2018%20vp",
        )
        self.assertTrue(public_document_url("EDK-2025-AK-8709").endswith("/pdf"))

    def test_search_all_pages_until_total(self):
        transport = FakeSearchTransport(total=5)
        sleeps: list[float] = []
        client = EduskuntaClient(transport=transport, sleeper=sleeps.append)
        result = client.search_all(
            {"category": "valtiopaivaasia"},
            method="get",
            page_size=2,
            get_delay=0,
        )

        self.assertEqual([row["id"] for row in result["data"]["results"]], ["0", "1", "2", "3", "4"])
        self.assertEqual(len(transport.calls), 3)
        self.assertTrue(result["trace"]["complete"])

    def test_search_all_refuses_more_than_api_limit(self):
        transport = FakeSearchTransport(total=10_001)
        client = EduskuntaClient(transport=transport, sleeper=lambda _: None)

        with self.assertRaises(SearchLimitError):
            client.search_all({"category": "puheenvuoro"}, method="get")

    def test_mps_uses_paginated_search_and_preserves_list_shape(self):
        transport = FakeSearchTransport(
            total=2001,
            row_factory=lambda index: {
                "id": str(index),
                "kansanedustaja": {
                    "henkilonro": str(index),
                    "sukunimi": f"Nimi {index}",
                },
            },
        )
        client = EduskuntaClient(transport=transport, sleeper=lambda _: None)

        result = client.mps()

        self.assertEqual(len(transport.calls), 3)
        self.assertTrue(
            all(call["payload"]["category"] == "kansanedustaja" for call in transport.calls)
        )
        self.assertEqual(len(result["data"]["kansanedustajat"]), 2001)
        self.assertEqual(result["data"]["searchMetadata"]["uniquePersonCount"], 2001)

    def test_hearings_keeps_all_phase_codes_sections_and_separate_attachments(self):
        def event(code, identifier, date="2026-02-13"):
            return {
                "tapahtumapvm": date,
                "kasittelytunnus": identifier,
                "yleinenkasittelyvaihe": "Asiantuntijakuuleminen",
                "yleinenkasittelyvaihetunnus": code,
                "valiokunta": {
                    "nimi": "Talousvaliokunta",
                    "tunnus": "TaV",
                    "jaosto": {"nimi": "Työjaosto", "tunnus": "TYJ"},
                },
                "jarjestys": 1,
                "fraasi": {
                    "fraasisisalto": None,
                    "fraasiryhmat": [
                        {
                            "fraasiKappaleKooste": "Valiokunnassa olivat kuultavina:",
                            "fraasiToimijat": [
                                {
                                    "fraasiyhteistoteksti": "Esimerkkivirasto",
                                    "fraasihenkilo": None,
                                }
                            ],
                        }
                    ],
                },
            }

        events = [
            event("ATKUUL", "TP-1"),
            event("ATKUULA", "TP-2"),
            event("ATKUULJT", "TP-3"),
            event("ATKUJTA", "TP-4"),
            event("ATKUUL", "TP-1"),
            event("MUU", "TP-5"),
            event("ATKUUL", "TP-6", date="2025-12-31"),
        ]
        statements = [
            {
                "edktunnus": "EDK-2026-AK-1",
                "asiakirjatyyppikoodi": "AL",
                "asiakirjatyyppinimi": "Asiantuntijalausunto",
                "nimeketeksti": "Sama asiantuntija ja otsikko",
                "laadintapvm": "2026-02-13",
                "lausuntoJarjestys": 2,
            },
            {
                "edktunnus": "EDK-2026-AK-2",
                "asiakirjatyyppikoodi": "ALL",
                "asiakirjatyyppinimi": "Asiantuntijalausunnon liite",
                "nimeketeksti": "Sama asiantuntija ja otsikko",
                "laadintapvm": "2026-02-13",
                "lausuntoJarjestys": 1,
            },
            {
                "edktunnus": "EDK-2025-AK-9",
                "asiakirjatyyppikoodi": "AL",
                "laadintapvm": "2025-12-31",
            },
        ]
        matter = {
            "eduskuntatunnus": {"fi": "U 4/2026 vp"},
            "nimeke": {"fi": "Esimerkkiasia"},
            "kasittelyt": {"fi": events},
            "asiantuntijalausunnot": {"fi": statements},
        }
        false_positive_matter = {
            "eduskuntatunnus": {"fi": "U 5/2026 vp"},
            "nimeke": {"fi": "Ei hyväksyttyä kuulemistapahtumaa"},
            "kasittelyt": {"fi": [event("MUU", "TP-7")]},
            "asiantuntijalausunnot": {
                "fi": [
                    {
                        "edktunnus": "EDK-2026-AK-3",
                        "asiakirjatyyppikoodi": "AL",
                        "laadintapvm": "2026-02-13",
                    }
                ]
            },
        }
        transport = FakeSearchTransport(
            total=2,
            row_factory=lambda index: {
                "id": f"matter-{index + 1}",
                "valtiopaivaasia": matter if index == 0 else false_positive_matter,
            },
        )
        client = EduskuntaClient(transport=transport, sleeper=lambda _: None)

        result = client.hearings(2026)

        self.assertEqual(result["data"]["counts"]["hearingEvents"], 4)
        self.assertEqual(result["data"]["counts"]["actorParticipations"], 4)
        self.assertEqual(result["data"]["counts"]["statementDocuments"], 2)
        self.assertEqual(
            {row["yleinenKasittelyvaihetunnus"] for row in result["data"]["events"]},
            {"ATKUUL", "ATKUULA", "ATKUULJT", "ATKUJTA"},
        )
        self.assertEqual(result["data"]["events"][0]["valiokunta"]["jaosto"]["tunnus"], "TYJ")
        self.assertEqual(
            {row["edktunnus"] for row in result["data"]["statementDocuments"]},
            {"EDK-2026-AK-1", "EDK-2026-AK-2"},
        )
        nested = transport.calls[0]["payload"]["expression"]
        self.assertEqual(nested["property"], "kasittelyt.fi")
        self.assertEqual(nested["with"]["and"][1]["fromDate"], "2026-01-01")

    def test_hearings_uses_requested_language_for_search_and_parsing(self):
        event = {
            "tapahtumapvm": "2026-03-04",
            "kasittelytunnus": "TP-SV-1",
            "yleinenkasittelyvaihe": "Utfrågning av sakkunniga",
            "yleinenkasittelyvaihetunnus": "ATKUUL",
            "valiokunta": None,
            "fraasi": None,
        }
        matter = {
            "eduskuntatunnus": {"sv": "E 4/2026 rd"},
            "nimeke": {"sv": "Exempelärende"},
            "kasittelyt": {"sv": [event]},
            "asiantuntijalausunnot": {
                "sv": [],
                "fi": [
                    {
                        "edktunnus": "EDK-2026-AK-SV-1",
                        "asiakirjatyyppikoodi": "AL",
                        "laadintapvm": "2026-03-04",
                    }
                ],
            },
        }
        transport = FakeSearchTransport(
            total=1,
            row_factory=lambda _: {"id": "matter-sv", "valtiopaivaasia": matter},
        )
        client = EduskuntaClient(transport=transport, sleeper=lambda _: None)

        result = client.hearings(2026, language="sv")

        nested = transport.calls[0]["payload"]["expression"]
        self.assertEqual(nested["property"], "kasittelyt.sv")
        self.assertEqual(
            nested["with"]["and"][0]["match"], "Utfrågning av sakkunniga"
        )
        self.assertEqual(result["data"]["counts"]["hearingEvents"], 1)
        self.assertEqual(result["data"]["events"][0]["eduskuntatunnus"], "E 4/2026 rd")
        self.assertEqual(result["data"]["counts"]["statementDocuments"], 1)
        self.assertEqual(
            result["data"]["statementDocuments"][0]["metadataLanguage"], "fi"
        )

    def test_hearings_tolerates_non_object_nested_values(self):
        events = [
            {
                "tapahtumapvm": "2026-04-01",
                "kasittelytunnus": "TP-BAD-1",
                "yleinenkasittelyvaihetunnus": "ATKUUL",
                "valiokunta": "unexpected",
                "fraasi": "unexpected",
            },
            {
                "tapahtumapvm": "2026-04-02",
                "kasittelytunnus": "TP-BAD-2",
                "yleinenkasittelyvaihetunnus": "ATKUULJT",
                "valiokunta": {
                    "nimi": "Talousvaliokunta",
                    "jaosto": "unexpected",
                },
                "fraasi": {
                    "fraasiryhmat": [
                        {
                            "fraasiKappaleKooste": "Valiokunnassa oli kuultavana:",
                            "fraasiToimijat": [
                                {
                                    "fraasiyhteistoteksti": "Esimerkkivirasto",
                                    "fraasihenkilo": "unexpected",
                                }
                            ],
                        }
                    ]
                },
            },
        ]
        matter = {
            "eduskuntatunnus": {"fi": "O 1/2026 vp"},
            "nimeke": {"fi": "Poikkeava testiaineisto"},
            "kasittelyt": {"fi": events},
            "asiantuntijalausunnot": {"fi": "unexpected"},
        }
        transport = FakeSearchTransport(
            total=1,
            row_factory=lambda _: {"id": "matter-bad", "valtiopaivaasia": matter},
        )
        client = EduskuntaClient(transport=transport, sleeper=lambda _: None)

        result = client.hearings(2026)

        self.assertEqual(result["data"]["counts"]["hearingEvents"], 2)
        self.assertEqual(result["data"]["counts"]["actorParticipations"], 1)
        self.assertEqual(result["data"]["counts"]["statementDocuments"], 0)
        self.assertEqual(result["data"]["events"][0]["fraasiryhmat"], [])
        self.assertIsNone(result["data"]["events"][0]["valiokunta"]["nimi"])
        actor = result["data"]["events"][1]["fraasiryhmat"][0]["toimijat"][0]
        self.assertIsNone(actor["etunimi"])
        self.assertEqual(actor["yhteiso"], "Esimerkkivirasto")

    def test_transient_error_is_retried(self):
        calls = 0
        sleeps: list[float] = []

        def transport(method, url, body, headers, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                return HttpResponse(503, {"Retry-After": "0"}, b"busy", url)
            return HttpResponse(200, {"Content-Type": "application/json"}, b'{"count": 3}', url)

        client = EduskuntaClient(transport=transport, sleeper=sleeps.append)
        result = client.count({"category": "valtiopaivaasia"})

        self.assertEqual(result["data"]["count"], 3)
        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [0.0])

    def test_html_blocks_preserve_headings_and_paragraphs(self):
        html = """
        <html><head><style>hidden</style></head><body>
        <h2>Valiokunnan perustelut</h2>
        <p>Ensimmäinen <strong>kappale</strong>.</p>
        <script>ignore()</script><ul><li>Kohta yksi</li></ul>
        </body></html>
        """
        blocks = extract_html_blocks(html)

        self.assertEqual(
            [(block["tag"], block["text"]) for block in blocks],
            [
                ("h2", "Valiokunnan perustelut"),
                ("p", "Ensimmäinen kappale."),
                ("li", "Kohta yksi"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
