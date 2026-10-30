"""Opt-in Exa discovery adapter; search results remain unreviewed source leads."""

from __future__ import annotations

import json
import os
import socket
import ssl
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from aave.nea_discovery import SearchAdapter, SearchProviderError

EXA_ENDPOINT = "https://api.exa.ai/search"
EXA_TERMS = "https://exa.ai/terms-of-service"
ExaTransport = Callable[[str, dict, dict], dict]


def _request_search(endpoint: str, payload: dict, headers: dict) -> dict:
    """Post one bounded request without exposing credentials in errors."""
    request = Request(endpoint, data=json.dumps(payload).encode("utf-8"),
                      headers=headers, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as error:
        kind = {401: "access_block", 403: "access_block", 402: "billing_block",
                429: "rate_limit"}.get(error.code, "http_error")
        raise SearchProviderError(kind, http_status=error.code,
                                  halt_batch=400 <= error.code < 500) from None
    except URLError as error:
        reason = error.reason
        if isinstance(reason, ssl.SSLCertVerificationError):
            kind = "tls_certificate"
        elif isinstance(reason, ssl.SSLError):
            kind = "tls_error"
        elif isinstance(reason, socket.gaierror):
            kind = "dns_error"
        elif isinstance(reason, PermissionError):
            kind = "network_permission"
        elif isinstance(reason, TimeoutError):
            kind = "timeout"
        else:
            kind = "network_error"
        raise SearchProviderError(kind) from None
    except TimeoutError:
        raise SearchProviderError("timeout") from None
    except ValueError:
        raise SearchProviderError("invalid_response") from None
    return result


def exa_search_adapter(*, enabled: bool = False, num_results: int = 5,
                       api_key: str | None = None,
                       transport: ExaTransport | None = None) -> SearchAdapter:
    """Build an explicitly enabled public-source search provider.

    Use an explicit api_key or read EXA_API_KEY only when enabled; never write
    credentials to checkpoints. An explicit blank key fails rather than falling
    back to another credential. Disabled adapters ignore both key sources. The caller
    must supply public-only queries, review provider terms, and use execute_batch
    for query caps, serial requests, response hashes and resumable checkpoints.
    An injected transport supports host certificate stores and offline tests.
    """
    invalid_count = (isinstance(num_results, bool) or not isinstance(num_results, int)
                     or not 1 <= num_results <= 10)
    if invalid_count:
        raise ValueError("Exa num_results must be an integer from 1 to 10")
    credential = ""
    if enabled:
        credential = (os.environ.get("EXA_API_KEY", "") if api_key is None else api_key).strip()
    if enabled and not credential:
        raise ValueError("EXA_API_KEY is required when Exa is explicitly enabled")
    request_search = transport or _request_search

    def search(query: str) -> list[dict]:
        if not enabled:
            raise ValueError("Exa adapter is disabled")
        if not query.strip():
            raise ValueError("Exa search requires a nonempty public query")
        payload = {"query": query, "type": "auto", "numResults": num_results,
                   "contents": {"text": {"maxCharacters": 7000}}}
        result = request_search(EXA_ENDPOINT, payload,
                                {"x-api-key": credential, "Content-Type": "application/json"})
        if not isinstance(result, dict) or not isinstance(result.get("results"), list):
            raise ValueError("Exa returned an invalid result list")
        retrieved_at = datetime.now(UTC).isoformat()
        hits = []
        for hit in result["results"]:
            if not isinstance(hit, dict) or not isinstance(hit.get("url"), str):
                raise ValueError("Exa returned a result without a source URL")
            parsed_url = urlparse(hit["url"])
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                raise ValueError("Exa returned an invalid source URL")
            # Whitelist public result fields; never persist request headers.
            source = {key: hit[key] for key in
                      ("url", "title", "text", "publishedDate", "author", "id") if key in hit}
            source.update(provider="exa", endpoint=EXA_ENDPOINT, retrieved_at=retrieved_at,
                          result_role="discovery_lead_requires_source_review",
                          age_exclusion_authorized=False)
            hits.append(source)
        return hits

    adapter = SearchAdapter(search=search, terms_url=EXA_TERMS, enabled=enabled,
                            minimum_interval_seconds=1.0, maximum_attempts=1)
    return adapter
