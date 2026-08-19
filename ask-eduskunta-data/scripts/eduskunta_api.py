#!/usr/bin/env python3
"""Deterministic helper for the Parliament of Finland Open Data API.

Uses only the Python standard library. Every command emits an audit envelope
containing the retrieval time, request, endpoint, and returned data.
"""

from __future__ import annotations

import argparse
import email.utils
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://api.eduskunta.fi/api/v1"
DEFAULT_TIMEOUT = 45.0
TRANSIENT_STATUS = {429, 500, 502, 503, 504}
MAX_SEARCH_RESULTS = 10_000
USER_AGENT = "ask-eduskunta-data/1.0 (+https://api.eduskunta.fi/)"


class ApiError(RuntimeError):
    """Raised when an API request or response cannot be handled reliably."""


class SearchLimitError(ApiError):
    """Raised when a search must be split into non-overlapping partitions."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes
    final_url: str


@dataclass(frozen=True)
class RequestTrace:
    method: str
    url: str
    final_url: str
    status: int
    retrieved_at: str
    attempt: int


Transport = Callable[[str, str, bytes | None, Mapping[str, str], float], HttpResponse]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def encode_path_identifier(value: str) -> str:
    """Encode every path-special character, including spaces and slashes."""

    if not value or not value.strip():
        raise ValueError("Identifier must not be empty")
    return quote(value.strip(), safe="")


def public_matter_url(eduskuntatunnus: str) -> str:
    encoded = encode_path_identifier(eduskuntatunnus)
    return (
        "https://www.eduskunta.fi/asiat-ja-aanestykset/"
        f"valtiopaivaasiat/{encoded}"
    )


def public_document_url(edktunnus: str) -> str:
    encoded = encode_path_identifier(edktunnus)
    return (
        "https://www.eduskunta.fi/asiat-ja-aanestykset/"
        f"valtiopaivaasiat/asiakirjat/edktunnus/{encoded}/pdf"
    )


def _default_transport(
    method: str,
    url: str,
    body: bytes | None,
    headers: Mapping[str, str],
    timeout: float,
) -> HttpResponse:
    request = Request(url, data=body, headers=dict(headers), method=method)
    with urlopen(request, timeout=timeout) as response:
        return HttpResponse(
            status=int(response.status),
            headers={key: value for key, value in response.headers.items()},
            body=response.read(),
            final_url=response.geturl(),
        )


def _retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    raw = next(
        (value for key, value in headers.items() if key.lower() == "retry-after"),
        None,
    )
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        try:
            retry_at = email.utils.parsedate_to_datetime(raw)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            return None


def _decode_json(body: bytes, url: str) -> Any:
    try:
        return json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        preview = body[:240].decode("utf-8", errors="replace")
        raise ApiError(f"Expected JSON from {url}, received: {preview!r}") from exc


class EduskuntaClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = 4,
        backoff: float = 1.0,
        transport: Transport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.transport = transport or _default_transport
        self.sleeper = sleeper

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        accept: str = "application/json",
    ) -> tuple[HttpResponse, RequestTrace]:
        url = f"{self.base_url}{path}"
        body = None
        headers = {"Accept": accept, "User-Agent": USER_AGENT}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
            headers["Content-Type"] = "application/json"

        last_error: Exception | None = None
        for attempt in range(1, self.retries + 2):
            try:
                response = self.transport(method, url, body, headers, self.timeout)
                if response.status in TRANSIENT_STATUS:
                    delay = _retry_after_seconds(response.headers)
                    if delay is None:
                        delay = self.backoff * (2 ** (attempt - 1))
                    if attempt <= self.retries:
                        self.sleeper(delay)
                        continue
                    raise ApiError(
                        f"Transient HTTP {response.status} persisted for {url}"
                    )
                if response.status < 200 or response.status >= 300:
                    preview = response.body[:240].decode("utf-8", errors="replace")
                    raise ApiError(
                        f"HTTP {response.status} for {url}: {preview!r}"
                    )
                trace = RequestTrace(
                    method=method,
                    url=url,
                    final_url=response.final_url,
                    status=response.status,
                    retrieved_at=utc_now(),
                    attempt=attempt,
                )
                return response, trace
            except HTTPError as exc:
                response_body = exc.read() if exc.fp is not None else b""
                if exc.code in TRANSIENT_STATUS and attempt <= self.retries:
                    delay = _retry_after_seconds(dict(exc.headers.items()))
                    if delay is None:
                        delay = self.backoff * (2 ** (attempt - 1))
                    self.sleeper(delay)
                    continue
                preview = response_body[:240].decode("utf-8", errors="replace")
                raise ApiError(f"HTTP {exc.code} for {url}: {preview!r}") from exc
            except (URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt <= self.retries:
                    self.sleeper(self.backoff * (2 ** (attempt - 1)))
                    continue
                break

        raise ApiError(f"Request failed after retries for {url}: {last_error}")

    def _json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        response, trace = self._request(method, path, payload=payload)
        return {
            "trace": asdict(trace),
            "request": payload,
            "data": _decode_json(response.body, trace.final_url),
        }

    def _text(self, path: str, *, accept: str) -> dict[str, Any]:
        response, trace = self._request("GET", path, accept=accept)
        encoding = "utf-8"
        content_type = next(
            (
                value
                for key, value in response.headers.items()
                if key.lower() == "content-type"
            ),
            "",
        )
        if "charset=" in content_type.lower():
            encoding = content_type.lower().split("charset=", 1)[1].split(";", 1)[0]
        return {
            "trace": asdict(trace),
            "request": None,
            "data": response.body.decode(encoding, errors="replace"),
        }

    @staticmethod
    def _search_method(payload: Mapping[str, Any], requested: str) -> str:
        if requested in {"get", "post"}:
            return requested.upper()
        compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        query_length = len(urlencode({"q": compact}, safe=""))
        return "GET" if query_length <= 900 else "POST"

    def search(
        self, payload: Mapping[str, Any], *, method: str = "auto"
    ) -> dict[str, Any]:
        chosen = self._search_method(payload, method)
        if chosen == "GET":
            compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            path = "/search?" + urlencode({"q": compact})
            return self._json("GET", path)
        return self._json("POST", "/search", payload=payload)

    def count(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._json("POST", "/search/count", payload=payload)

    def search_all(
        self,
        payload: Mapping[str, Any],
        *,
        method: str = "auto",
        page_size: int = 1000,
        max_records: int = MAX_SEARCH_RESULTS,
        get_delay: float = 1.1,
        post_delay: float = 7.0,
    ) -> dict[str, Any]:
        if page_size < 1 or page_size > MAX_SEARCH_RESULTS:
            raise ValueError("page_size must be between 1 and 10000")
        if max_records < 1 or max_records > MAX_SEARCH_RESULTS:
            raise ValueError("max_records must be between 1 and 10000")

        base_payload = dict(payload)
        base_payload.pop("startFromIndex", None)
        base_payload["maxResults"] = min(page_size, max_records)
        results: list[Any] = []
        traces: list[dict[str, Any]] = []
        total: int | None = None
        start = 0

        while True:
            page_payload = dict(base_payload)
            page_payload["startFromIndex"] = start
            page = self.search(page_payload, method=method)
            traces.append(page["trace"])
            data = page["data"]
            if not isinstance(data, dict):
                raise ApiError("Search response was not a JSON object")
            page_results = data.get("results")
            metadata = data.get("searchMetadata") or {}
            if not isinstance(page_results, list):
                raise ApiError("Search response did not contain a results list")
            if total is None:
                raw_total = metadata.get("totalResultCount")
                total = int(raw_total) if raw_total is not None else len(page_results)
                if total > MAX_SEARCH_RESULTS:
                    raise SearchLimitError(
                        f"Query matches {total} results; split it into non-overlapping "
                        "partitions such as years or sessions"
                    )
                if total > max_records:
                    raise SearchLimitError(
                        f"Query matches {total} results, above max_records={max_records}"
                    )
            results.extend(page_results)
            actual = len(page_results)
            start += actual
            if actual == 0 or start >= total:
                break
            selected_method = traces[-1]["method"]
            self.sleeper(post_delay if selected_method == "POST" else get_delay)

        return {
            "trace": {
                "retrieved_at": traces[-1]["retrieved_at"] if traces else utc_now(),
                "pages": traces,
                "complete": total is not None and len(results) >= total,
            },
            "request": base_payload,
            "data": {
                "results": results,
                "searchMetadata": {
                    "totalResultCount": total or 0,
                    "actualResultCount": len(results),
                    "startFromIndex": 0,
                },
            },
        }

    def matter(self, identifier: str) -> dict[str, Any]:
        return self._json(
            "GET", f"/valtiopaivaasiat/{encode_path_identifier(identifier)}"
        )

    def documents(self, identifier: str) -> dict[str, Any]:
        return self._json(
            "GET", f"/asiakirjat/eduskuntatunnus/{encode_path_identifier(identifier)}"
        )

    def document(self, edktunnus: str) -> dict[str, Any]:
        return self._json(
            "GET", f"/asiakirjat/edktunnus/{encode_path_identifier(edktunnus)}"
        )

    def document_html(self, edktunnus: str) -> dict[str, Any]:
        return self._text(
            f"/asiakirjat/edktunnus/{encode_path_identifier(edktunnus)}/html",
            accept="text/html,application/xhtml+xml",
        )

    def document_xml(self, edktunnus: str) -> dict[str, Any]:
        return self._text(
            f"/asiakirjat/edktunnus/{encode_path_identifier(edktunnus)}/xml",
            accept="application/xml,text/xml",
        )

    def mp(self, identifier: str) -> dict[str, Any]:
        return self._json("GET", f"/kansanedustajat/{encode_path_identifier(identifier)}")

    def mps(self) -> dict[str, Any]:
        return self._json("GET", "/kansanedustajat")

    def vote(self, identifier: str) -> dict[str, Any]:
        return self._json(
            "GET", f"/taysistunnot/aanestykset/{encode_path_identifier(identifier)}"
        )

    def session_votes(self, identifier: str) -> dict[str, Any]:
        return self._json(
            "GET",
            f"/taysistunnot/istunnon-aanestykset/{encode_path_identifier(identifier)}",
        )

    def matter_votes(self, identifier: str) -> dict[str, Any]:
        return self._json(
            "GET",
            f"/taysistunnot/asian-aanestykset/{encode_path_identifier(identifier)}",
        )

    def latest_votes(self) -> dict[str, Any]:
        return self._json("GET", "/taysistunnot/uusimmat-aanestykset")

    def record_html(self, identifier: str) -> dict[str, Any]:
        return self._text(
            "/taysistunnot/poytakirja-asiakohdat/"
            f"{encode_path_identifier(identifier)}/html",
            accept="text/html,application/xhtml+xml",
        )

    def reference(self, name: str) -> dict[str, Any]:
        allowed = {
            "asiakirjatyypit",
            "asiatyypit",
            "eduskuntaryhmat",
            "kansanedustajat",
            "puheenvuorotyypit",
            "sukupuolet",
            "vaalikaudet",
            "vaalipiirit",
            "valiokunnat",
            "valtiopaivat",
        }
        if name not in allowed:
            raise ValueError(f"Unknown reference-data name: {name}")
        return self._json("GET", f"/reference-data/{name}")

    def aggregate(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._json("POST", "/aggregations/unique-by", payload=payload)


class BlockHTMLParser(HTMLParser):
    BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th"}
    SKIP_TAGS = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict[str, Any]] = []
        self._active_tag: str | None = None
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth == 0 and tag in self.BLOCK_TAGS and self._active_tag is None:
            self._active_tag = tag
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth == 0 and tag == self._active_tag:
            text = " ".join("".join(self._parts).split())
            if text:
                self.blocks.append(
                    {"index": len(self.blocks), "tag": self._active_tag, "text": text}
                )
            self._active_tag = None
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and self._active_tag is not None:
            self._parts.append(data)


def extract_html_blocks(html: str) -> list[dict[str, Any]]:
    parser = BlockHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.blocks


def _read_payload(path: str) -> dict[str, Any]:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("Payload must be a JSON object")
    return value


def _write_result(result: Any, output: str | None) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _client_from_args(args: argparse.Namespace) -> EduskuntaClient:
    return EduskuntaClient(
        args.base_url,
        timeout=args.timeout,
        retries=args.retries,
        backoff=args.backoff,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--backoff", type=float, default=1.0)
    parser.add_argument("--output", help="Write UTF-8 JSON to this path")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Run a search request")
    search.add_argument("--payload", required=True, help="JSON file or - for stdin")
    search.add_argument("--method", choices=("auto", "get", "post"), default="auto")
    search.add_argument("--all", action="store_true", help="Fetch every result page")
    search.add_argument("--page-size", type=int, default=1000)
    search.add_argument("--max-records", type=int, default=MAX_SEARCH_RESULTS)

    count = sub.add_parser("count", help="Count results without fetching them")
    count.add_argument("--payload", required=True, help="JSON file or - for stdin")

    aggregate = sub.add_parser("aggregate", help="Run a unique-by aggregation")
    aggregate.add_argument("--payload", required=True, help="JSON file or - for stdin")

    for command, help_text in (
        ("matter", "Fetch a parliamentary matter"),
        ("documents", "Fetch document metadata for a matter"),
        ("document", "Fetch document metadata by EDK identifier"),
        ("document-html", "Fetch document HTML"),
        ("document-xml", "Fetch document XML"),
        ("document-text", "Fetch document HTML and extract traceable blocks"),
        ("mp", "Fetch one MP by ID"),
        ("vote", "Fetch one vote by ID"),
        ("session-votes", "Fetch all votes in a plenary session"),
        ("matter-votes", "Fetch all votes for a parliamentary matter"),
        ("record-html", "Fetch a plenary record article as HTML"),
    ):
        item = sub.add_parser(command, help=help_text)
        item.add_argument("identifier")

    sub.add_parser("mps", help="Fetch all MPs")
    sub.add_parser("latest-votes", help="Fetch the latest votes")

    reference = sub.add_parser("reference", help="Fetch reference data")
    reference.add_argument("name")

    public_url = sub.add_parser("public-url", help="Build an encoded public URL")
    public_url.add_argument("kind", choices=("matter", "document"))
    public_url.add_argument("identifier")

    return parser


def run_command(args: argparse.Namespace) -> Any:
    if args.command == "public-url":
        url = (
            public_matter_url(args.identifier)
            if args.kind == "matter"
            else public_document_url(args.identifier)
        )
        return {"kind": args.kind, "identifier": args.identifier, "url": url}

    client = _client_from_args(args)
    if args.command == "search":
        payload = _read_payload(args.payload)
        if args.all:
            return client.search_all(
                payload,
                method=args.method,
                page_size=args.page_size,
                max_records=args.max_records,
            )
        return client.search(payload, method=args.method)
    if args.command == "count":
        return client.count(_read_payload(args.payload))
    if args.command == "aggregate":
        return client.aggregate(_read_payload(args.payload))
    if args.command == "matter":
        return client.matter(args.identifier)
    if args.command == "documents":
        return client.documents(args.identifier)
    if args.command == "document":
        return client.document(args.identifier)
    if args.command == "document-html":
        return client.document_html(args.identifier)
    if args.command == "document-xml":
        return client.document_xml(args.identifier)
    if args.command == "document-text":
        result = client.document_html(args.identifier)
        html = result["data"]
        result["data"] = {
            "edktunnus": args.identifier,
            "source_url": result["trace"]["final_url"],
            "blocks": extract_html_blocks(html),
        }
        return result
    if args.command == "mp":
        return client.mp(args.identifier)
    if args.command == "mps":
        return client.mps()
    if args.command == "vote":
        return client.vote(args.identifier)
    if args.command == "session-votes":
        return client.session_votes(args.identifier)
    if args.command == "matter-votes":
        return client.matter_votes(args.identifier)
    if args.command == "latest-votes":
        return client.latest_votes()
    if args.command == "record-html":
        return client.record_html(args.identifier)
    if args.command == "reference":
        return client.reference(args.name)
    raise ValueError(f"Unknown command: {args.command}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = run_command(args)
        _write_result(result, args.output)
        return 0
    except (ApiError, ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

