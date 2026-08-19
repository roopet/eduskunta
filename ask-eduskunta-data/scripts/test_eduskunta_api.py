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
    def __init__(self, total: int) -> None:
        self.total = total
        self.calls: list[dict[str, object]] = []

    def __call__(self, method, url, body, headers, timeout):
        if method == "GET":
            payload = json.loads(parse_qs(urlparse(url).query)["q"][0])
        else:
            payload = json.loads(body.decode("utf-8"))
        start = int(payload.get("startFromIndex", 0))
        size = int(payload.get("maxResults", 100))
        end = min(start + size, self.total)
        results = [{"id": str(index)} for index in range(start, end)]
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

