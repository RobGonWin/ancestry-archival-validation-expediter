"""Synthetic, offline checks for explicitly authorized Exa discovery."""

import json
import os

import pytest

from aave.nea_discovery import execute_batch
from aave.nea_exa import exa_search_adapter
from aave.nea_discovery import SearchProviderError


def test_disabled_adapter_does_not_read_or_use_key(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    adapter = exa_search_adapter()
    assert not adapter.enabled
    with pytest.raises(ValueError, match="disabled"):
        adapter.search("Synthetic public artist")


def test_enabled_adapter_requires_key(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="EXA_API_KEY is required"):
        exa_search_adapter(enabled=True)


def test_explicit_key_takes_precedence_without_environment_mutation(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "synthetic-environment-token")
    headers_seen = []

    def transport(endpoint, payload, headers):
        headers_seen.append(headers)
        return {"results": []}

    adapter = exa_search_adapter(enabled=True, api_key=" synthetic-explicit-token ",
                                 transport=transport)
    assert adapter.search("Synthetic public archive") == []
    assert headers_seen[0]["x-api-key"] == "synthetic-explicit-token"
    assert os.environ["EXA_API_KEY"] == "synthetic-environment-token"


def test_explicit_key_works_without_environment(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    adapter = exa_search_adapter(enabled=True, api_key="synthetic-explicit-token",
                                 transport=lambda *_: {"results": []})
    assert adapter.search("Synthetic public archive") == []


def test_blank_explicit_key_does_not_fall_back(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "synthetic-environment-token")
    with pytest.raises(ValueError, match="EXA_API_KEY is required"):
        exa_search_adapter(enabled=True, api_key=" ")


def test_disabled_adapter_ignores_explicit_key():
    adapter = exa_search_adapter(api_key="synthetic-explicit-token")
    with pytest.raises(ValueError, match="disabled"):
        adapter.search("Synthetic public archive")


@pytest.mark.parametrize("credential_source", ["environment", "explicit"])
def test_checkpoint_has_provenance_without_secret_and_resumes(monkeypatch, tmp_path,
                                                            credential_source):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    options = {}
    if credential_source == "environment":
        monkeypatch.setenv("EXA_API_KEY", "synthetic-test-token")
    else:
        options["api_key"] = "synthetic-test-token"
    calls = []

    def transport(endpoint, payload, headers):
        assert headers["x-api-key"] == "synthetic-test-token"
        assert payload["numResults"] == 5
        calls.append(endpoint)
        return {"results": [{"url": "https://example.org/artist", "title": "Synthetic artist",
                              "text": "An unreviewed source lead.", "headers": headers}]}

    adapter = exa_search_adapter(enabled=True, transport=transport, **options)
    query = {"query_id": "synthetic-query", "provider": "exa", "priority": 0,
             "query": "Synthetic public artist", "query_is_external_emission": True}
    checkpoint = tmp_path / "checkpoint.json"
    results = execute_batch([query], {"exa": adapter}, checkpoint, limit=1)
    execute_batch([query], {"exa": adapter}, checkpoint, limit=1)
    assert len(calls) == 1
    row = results["synthetic-query"]
    assert row["status"] == "searched"
    assert row["response_sha256"]
    assert row["hits"][0]["retrieved_at"]
    assert not row["age_exclusion_authorized"]
    assert "synthetic-test-token" not in checkpoint.read_text()
    assert "headers" not in row["hits"][0]


@pytest.mark.parametrize("payload", [{}, {"results": [{}]},
                                    {"results": [{"url": "file:///private.txt"}]}])
def test_invalid_results_cannot_become_source_leads(monkeypatch, payload):
    monkeypatch.setenv("EXA_API_KEY", "synthetic-test-token")
    adapter = exa_search_adapter(enabled=True, transport=lambda *_: payload)
    with pytest.raises(ValueError):
        adapter.search("Synthetic public artist")


def test_failed_transport_is_checkpointed_without_exception_text(monkeypatch, tmp_path):
    monkeypatch.setenv("EXA_API_KEY", "synthetic-test-token")

    def transport(*_):
        raise OSError("synthetic-test-token must not enter the checkpoint")

    adapter = exa_search_adapter(enabled=True, transport=transport)
    query = {"query_id": "failed", "provider": "exa", "priority": 0, "query": "Synthetic artist"}
    checkpoint = tmp_path / "checkpoint.json"
    execute_batch([query], {"exa": adapter}, checkpoint, limit=1)
    row = json.loads(checkpoint.read_text())["failed"]
    assert row["status"] == "failed"
    assert row["attempts"] == 1
    assert "synthetic-test-token" not in checkpoint.read_text()


@pytest.mark.parametrize("status,kind", [(401, "access_block"), (403, "access_block"),
                                        (402, "billing_block"), (429, "rate_limit"),
                                        (503, "http_error")])
def test_http_diagnostics_are_safe_and_access_blocks_halt(monkeypatch, status, kind):
    from urllib.error import HTTPError

    def blocked(*args, **kwargs):
        raise HTTPError("https://example.org/synthetic-secret", status, "synthetic-secret", {}, None)

    monkeypatch.setattr("aave.nea_exa.urlopen", blocked)
    adapter = exa_search_adapter(enabled=True, api_key="synthetic-secret")
    with pytest.raises(SearchProviderError) as caught:
        adapter.search("Synthetic public archive")
    assert caught.value.failure_kind == kind
    assert caught.value.http_status == status
    assert caught.value.halt_batch == (status < 500)
    assert "synthetic-secret" not in str(caught.value)


def test_certificate_error_is_distinguished_without_disabling_tls(monkeypatch):
    import ssl
    from urllib.error import URLError

    def failed_tls(*args, **kwargs):
        raise URLError(ssl.SSLCertVerificationError("synthetic-secret"))

    monkeypatch.setattr("aave.nea_exa.urlopen", failed_tls)
    adapter = exa_search_adapter(enabled=True, api_key="synthetic-secret")
    with pytest.raises(SearchProviderError) as caught:
        adapter.search("Synthetic public archive")
    assert caught.value.failure_kind == "tls_certificate"
    assert "synthetic-secret" not in str(caught.value)
