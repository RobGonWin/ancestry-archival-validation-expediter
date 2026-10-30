"""Synthetic checks for source-bound, conservative NEA research decisions."""

import hashlib
import json
from datetime import date

import pytest

from aave.nea_census import (
    census_age_excludes_reference, census_finder_plan, genealogist_search_plan,
    nara_catalog_adapter, nara_catalog_request, plan_closure_batch,
)
from aave.nea_classification import (
    birth_year_excludes_reference, classify_documented_sex, genealogy_crosswalk,
    identify_subject_birth, relationship_episode,
)
from aave.nea_dates import attained_age, compare_age, parse_date_interval
from aave.nea_discovery import SearchAdapter, discovery_queries, execute_batch, plan_cohorts
from aave.nea_evidence import (
    census_observation, dependency_groups, extract_page, inventory_local,
    reconcile_memorial, require_private_destination,
)
from aave.nea_research import adjudicate_person, ranking_closure, resolve_inventory, stable_id, verify_review
from aave.nea_verification import reusable_slice, save_slice, slice_fingerprint


@pytest.mark.parametrize("value,first,last", [
    ("1919", "1919-01-01", "1919-12-31"),
    ("2000-02", "2000-02-01", "2000-02-29"),
    ("1900/1902", "1900-01-01", "1902-12-31"),
    ("2001-02-03", "2001-02-03", "2001-02-03"),
])
def test_date_intervals(value, first, last):
    interval = parse_date_interval(value)
    assert interval.earliest.isoformat() == first
    assert interval.latest.isoformat() == last


@pytest.mark.parametrize("value", ["ca 1900", "1902/1900", "2001-02-29", "unknown"])
def test_unsupported_dates_fail_closed(value):
    with pytest.raises(ValueError):
        parse_date_interval(value)


def test_cutoff_screening_does_not_predict_lifespan():
    result = compare_age(parse_date_interval("1919"), None)
    assert result["upper_age"] == [107, 295]
    assert result["status"] == "bounded_below_roma_at_cutoff"
    assert result["future_lifespan"] == "not_inferred"
    assert not result["completed_lifespan_documented"]


def test_exact_and_partial_ages_have_different_labels():
    exact = compare_age(parse_date_interval("1900-01-01"), parse_date_interval("2008-01-01"))
    partial = compare_age(parse_date_interval("1900"), parse_date_interval("2008"))
    assert exact["status"] == "verified_above_roma"
    assert partial["status"] == "possible_competitor"
    future = compare_age(parse_date_interval("1920-01-01"), parse_date_interval("2030-01-01"))
    assert future["endpoint"] == "2026-10-23"
    assert not future["completed_lifespan_documented"]


def test_leap_birthday_and_negative_age():
    assert attained_age(date(2000, 2, 29), date(2001, 2, 28)) == (1, 0)
    with pytest.raises(ValueError):
        attained_age(date(2000, 1, 1), date(1999, 1, 1))


def test_reference_and_comparator_reported_date_regression():
    reference = attained_age(date(1910, 12, 22), date(2018, 10, 25))
    comparator = attained_age(date(1907, 4, 21), date(2011, 9, 12))
    assert reference == (107, 307)
    assert comparator == (104, 144)
    assert reference > comparator


def test_private_all_destination_is_checked_before_any_write(tmp_path):
    from aave.cli import main
    with pytest.raises(SystemExit) as exit_info:
        main(["nea", "all", "--repo", str(tmp_path), "--local-root", str(tmp_path),
              "--out", str(tmp_path / "public")])
    assert exit_info.value.code == 2
    assert not (tmp_path / "public").exists()


def test_identity_conflict_cannot_remove_female_candidate():
    person = {"person_id": "p", "profile_url": "https://example.org/person"}
    decision = adjudicate_person(person, {"decision_id": "d", "sex": "female",
                                          "conflict": "source hash mismatch"}, date(2026, 10, 23))
    assert decision["sex"] == "unknown"
    assert decision["status"] == "identity_conflict"
    assert ranking_closure([decision], [], "reference")["unresolved_sex_unknown"]


def test_reference_and_groups_gate_universal_closure():
    reference = {"person_id": "r", "status": "verified_equal_roma", "sex": "male"}
    assert ranking_closure([reference], [], "r")["status"] == "established_as_of_cutoff"
    assert ranking_closure([reference], [{"award_id": "g"}], "r")["status"] == "not_established"
    assert ranking_closure([], [], "r")["status"] == "not_established"
    assert stable_id("person", "a") != stable_id("award", "a")
    assert stable_id("person", "a") != stable_id("person", "b")


def test_review_requires_hash_and_subject_link(tmp_path):
    assert "no_hash_bound_source" in verify_review({}, {}, tmp_path)
    cache = tmp_path / "local-vault" / "page.html"
    cache.parent.mkdir()
    cache.write_bytes(b"<p>Artist born in 1950.</p>")
    digest = hashlib.sha256(cache.read_bytes()).hexdigest()
    profile = {"profile_sha256": digest, "local_ignored_cache": "local-vault/page.html"}
    review = {"source_sha256": digest, "subject_reviewed": True,
              "rationale": "Subject sentence reviewed", "excerpt": "Artist born in 1950."}
    assert verify_review(review, profile, tmp_path) == []
    cache.write_bytes(b"changed")
    assert "cached_source_hash_mismatch" in verify_review(review, profile, tmp_path)


def test_ledger_age_cannot_be_changed(tmp_path):
    ledger = tmp_path / "data" / "ledger.json"
    ledger.parent.mkdir()
    ledger.write_text(json.dumps({"records": [{"source_id": "s", "reported_completed_age_years": 90}]}))
    review = {"subject_reviewed": True, "rationale": "reported age",
              "evidence_file": "data/ledger.json", "evidence_source_id": "s",
              "evidence_sha256": hashlib.sha256(ledger.read_bytes()).hexdigest(), "completed_age_years": 80}
    assert "review_age_differs_from_evidence_record" in verify_review(review, {}, tmp_path)


def test_death_ceiling_is_bound_to_reviewed_evidence(tmp_path):
    ledger = tmp_path / "data" / "ledger.json"
    ledger.parent.mkdir()
    ledger.write_text(json.dumps({"records": [{"source_id": "s",
                                               "death_not_after": "2000-02-20"}]}))
    review = {"subject_reviewed": True, "rationale": "Institution reports death by publication",
              "evidence_file": "data/ledger.json", "evidence_source_id": "s",
              "evidence_sha256": hashlib.sha256(ledger.read_bytes()).hexdigest(),
              "death_not_after": "2000-02-20"}
    assert verify_review(review, {}, tmp_path) == []
    review["death_not_after"] = "2000-02-19"
    assert "review_dates_differ_from_evidence_record" in verify_review(review, {}, tmp_path)


def test_ledger_binding_survives_checkout_line_endings(tmp_path):
    from aave.nea_research import ledger_sha256
    source = tmp_path / "data" / "ledger.json"
    source.parent.mkdir()
    source.write_bytes(b'{"records": [{"source_id": "s", "birth_date": "1950"}]}\n')
    review = {"subject_reviewed": True, "rationale": "reviewed", "birth": "1950",
              "evidence_file": "data/ledger.json", "evidence_source_id": "s",
              "evidence_hash_normalization": "lf_text", "evidence_sha256": ledger_sha256(source)}
    source.write_bytes(source.read_bytes().replace(b"\n", b"\r\n"))
    assert verify_review(review, {}, tmp_path) == []


def test_search_checkpoint_moves_to_next_batch(tmp_path):
    queries = [{"query_id": str(i), "priority": 0, "provider": "api", "query": str(i)} for i in range(4)]
    calls = []
    adapter = SearchAdapter(lambda query: calls.append(query) or [], "https://example.org/terms", True, 0)
    path = tmp_path / "checkpoint.json"
    execute_batch(queries, {"api": adapter}, path, limit=2)
    execute_batch(queries, {"api": adapter}, path, limit=2)
    assert calls == ["0", "1", "2", "3"]
    assert all(row["status"] == "not_found" for row in json.loads(path.read_text()).values())
    assert all(not row["age_exclusion_authorized"] for row in json.loads(path.read_text()).values())


def test_disabled_provider_and_dry_run(tmp_path):
    query = {"query_id": "q", "priority": 0, "provider": "api", "query": "public artist"}
    path = tmp_path / "checkpoint.json"
    execute_batch([query], {}, path, dry_run=True)
    assert not path.exists()
    execute_batch([query], {}, path)
    assert json.loads(path.read_text())["q"]["status"] == "manual_followup"
    person = {"status": "bounded_below_roma_at_cutoff", "privacy_label": "public_ok"}
    assert discovery_queries(person) == []
    assert discovery_queries({"status": "possible_competitor", "privacy_label": "do_not_share"}) == []


def test_layered_queries_skip_retrieved_biography_and_refresh_explicitly():
    person = {"person_id": "p", "name": "Example Artist", "award_year": 2000,
              "status": "possible_competitor", "privacy_label": "public_ok", "priority": 0,
              "official_profile_retrieved": True, "cutoff": "2026-10-23"}
    queries = discovery_queries(person)
    assert "nea" not in {row["provider"] for row in queries}
    assert {"nea_death_statement", "funeral_directory", "historical_archive", "gerontology"}.issubset(
        {row["provider"] for row in queries})
    assert queries == discovery_queries(person)
    changed = discovery_queries({**person, "search_revision": 2})
    assert changed[0]["query_id"] != queries[0]["query_id"]


def test_fifty_recipient_cohorts_cover_each_pending_person_once():
    people = [{"person_id": f"p-{index:03d}", "name": "Synthetic artist",
               "privacy_label": "public_ok", "status": "possible_competitor"}
              for index in range(123)]
    people += [{"person_id": "excluded", "privacy_label": "public_ok", "status": "verified_below_roma"},
               {"person_id": "private", "privacy_label": "do_not_share", "status": "possible_competitor"}]
    cohorts = plan_cohorts(people, reference_id="p-000")
    assert [row["recipient_count"] for row in cohorts] == [50, 50, 22]
    identifiers = [identifier for cohort in cohorts for identifier in cohort["person_ids"]]
    assert len(identifiers) == len(set(identifiers)) == 122
    assert cohorts == plan_cohorts(list(reversed(people)), reference_id="p-000")
    with pytest.raises(ValueError):
        plan_cohorts(people, cohort_size=0)


def test_search_retries_are_bounded(tmp_path):
    calls = []
    def fail(query):
        calls.append(query)
        raise OSError("unavailable")
    query = {"query_id": "q", "priority": 0, "provider": "api", "query": "artist"}
    adapter = SearchAdapter(fail, "https://example.org/terms", True, 0, 2)
    result = execute_batch([query], {"api": adapter}, tmp_path / "checkpoint.json")
    assert len(calls) == 2
    assert result["q"]["status"] == "failed"
    execute_batch([query], {"api": adapter}, tmp_path / "checkpoint.json")
    assert len(calls) == 2


def test_memorial_same_name_and_listing_are_not_headstone_proof():
    person = {"person_id": "p", "birth": "1900-01-01"}
    record = {"person_id": "other", "name": "Same Name"}
    assert reconcile_memorial(person, record)["match_status"] == "rejected_match"
    record.update(person_id="p", identity_reviewed=True, identity_evidence=["dates"],
                  source_url="https://example.org/memorial", evidence_role="cemetery_listing")
    result = reconcile_memorial(person, record)
    assert result["match_status"] == "verified_match"
    assert not result["headstone_verified"]
    record.update(evidence_role="photographed_headstone", image_reviewed=True,
                  image_source_url="https://example.org/photo")
    assert reconcile_memorial(person, record)["headstone_verified"]


def test_source_dependence_is_transitive():
    records = [{"evidence_id": "a", "content_sha256": "x"},
               {"evidence_id": "b", "origin_id": "o"},
               {"evidence_id": "c", "content_sha256": "x", "origin_id": "o"}]
    assert dependency_groups(records) == [["a", "b", "c"]]


def test_census_preserves_conflicting_vendor_reading():
    result = census_observation({"original_name": "Example", "vendor_name": "Exampel"})
    assert result["transcription_conflict"]
    assert result["identity_status"] == "needs_review"
    assert result["privacy_label"] == "do_not_share"


def test_private_inventory_and_visible_text(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "saved.html").write_text('<link rel="canonical" href="https://example.org"><script>secret</script><p>Visible</p>')
    (archive / "sequence.vcf").write_text("excluded")
    output = tmp_path / "local-vault" / "inventory.json"
    result = inventory_local([archive, tmp_path / "missing"], output, tmp_path)
    assert len(result["roots"][0]["artifacts"]) == 1
    artifact = result["roots"][0]["artifacts"][0]
    assert artifact["extracted_text"] == "Visible"
    assert not artifact["modified_time_is_capture_date"]
    assert result["roots"][1]["availability"] == "FileNotFoundError"
    with pytest.raises(ValueError):
        require_private_destination(tmp_path / "public", tmp_path)
    assert extract_page(b"<style>hidden</style>text")[0] == "text"


def test_verification_slice_invalidates_only_changed_inputs(tmp_path):
    fingerprint = slice_fingerprint({"source": "hash"}, cutoff="2026-10-23", rules_version="1")
    receipt = {"slice_id": "dates", "fingerprint": fingerprint, "status": "blocked",
               "source_roles": ["index"], "decision": "no original available", "blockers": ["manual"]}
    save_slice(tmp_path / "slice.json", receipt)
    assert reusable_slice(receipt, fingerprint)
    changed = slice_fingerprint({"source": "new hash"}, cutoff="2026-10-23", rules_version="1")
    assert not reusable_slice(receipt, changed)
    with pytest.raises(ValueError):
        save_slice(tmp_path / "bad.json", {})


@pytest.mark.parametrize("members,review", [([], {}), ([{"name": "A"}], {}),
    ([{"name": "A"}, {"name": "A"}], {"subject_reviewed": True, "rationale": "reviewed", "source_sha256": "hash"})])
def test_unreviewed_or_empty_group_cannot_disappear(tmp_path, members, review):
    folder = tmp_path / "data"
    folder.mkdir()
    url = "https://example.org/joint-award"
    documents = {
        "nea-recipient-age-audit.json": {"entries": [{"profile_url": url, "recipient_label": "Joint Award", "award_year": 2000, "art_form": "music"}]},
        "nea-person-age-bounds.json": {"adjudications": [], "coverage": {"award_entries_with_individual_age_exclusion": 0}},
        "nea-male-ranking-coverage.json": {"entries": [{"profile_url": url, "profile_sha256": "hash"}], "coverage": {"successfully_retrieved_profiles": 1}},
        "nea-research-reviews.json": {"reference_profile_url": "https://example.org/reference", "decisions": [],
            "collective_awards": [{"profile_url": url, "kind": "joint", "members": members, "membership_complete": True,
                                   "membership_review": review, "blockers": ["membership unverified"]}]},
    }
    for name, document in documents.items():
        (folder / name).write_text(json.dumps(document), encoding="utf-8")
    result = resolve_inventory(tmp_path)
    assert result["summary"]["unresolved_collective_awards"] == 1
    assert result["ranking"]["status"] == "not_established"


def test_birth_identification_skips_award_years_and_relatives():
    late = identify_subject_birth("Profile Bio Born in 1938 and raised nearby.", "Mike Auldridge", award_year=2012)
    assert late["disposition"] == "exclude_by_birth_year"
    assert late["birth_year"] == 1938
    relative = identify_subject_birth("Her son was born in 1977 after the apprenticeship.", "Clarissa Rizal")
    assert relative is None
    event = identify_subject_birth("In the Tradition was born, becoming an annual event. In 1984", "Linda Goss")
    assert event is None
    early = identify_subject_birth("Bio George Lopez was born on April 23, 1900, in Cordova.", "George López")
    assert early["disposition"] == "needs_death_or_census"
    approximate = identify_subject_birth("Bio Mary Holiday Black was born about 1934.", "Mary Holiday Black")
    assert approximate["disposition"] == "muted_approximate"


def test_sex_label_is_explicit_and_1919_cannot_reach_roma():
    assert classify_documented_sex("male") == "male"
    assert classify_documented_sex("Henry") == "unknown"
    assert birth_year_excludes_reference(1919)
    assert not birth_year_excludes_reference(1910)


def test_census_crosswalk_and_relationship_chronology_stay_unmerged():
    crosswalk = genealogy_crosswalk({"aave_person_id": "person-a", "public_tree_person_id": "I1",
                                     "identity_match_confidence": "possible_match"})
    assert crosswalk["silent_identity_merge"] is False
    assert crosswalk["identifiers_may_be_cited_together"] is False
    episode_a = relationship_episode({"subject": "Example Subject", "counterpart": "Example Counterpart A",
                                   "role": "parent_of_synthetic_subject_as_stated", "observed_context": "synthetic obituary",
                                   "source_role": "synthetic_obituary"})
    episode_b = relationship_episode({"subject": "Example Subject", "counterpart": "Example Counterpart B",
                                 "role": "spouse_in_caption", "observed_context": "synthetic performance, 1994",
                                 "source_role": "photograph_caption"})
    assert episode_a["counterpart"] != episode_b["counterpart"]
    assert episode_a["end_established"] is False and episode_b["divorce_or_death_inferred"] is False


def test_closure_batch_uses_discovery_pipeline_and_caps_queries():
    people = [{"person_id": f"person-{index:03d}", "name": f"Person {index}", "award_year": 1982,
               "status": "insufficient_age_evidence", "priority": 0, "privacy_label": "public_ok",
               "sex": "unknown", "art_form": "music"} for index in range(35)]
    people[0]["name"] = "Henry Townsend"
    plan = plan_closure_batch(people, person_limit=30, query_limit=40, preferred_names=["Henry Townsend"])
    assert plan["people_selected"] == 30
    assert plan["query_count"] <= 40
    assert plan["queries"][0]["provider"] in {"nara_catalog", "census_index_lead", "familysearch_public",
                                               "ancestry_public_lead", "findagrave", "funeral"}
    assert plan["known_male_selected"] == 0
    request = nara_catalog_request("Example Person", 1940)
    assert request["returns_named_person"] is False and request["api_key_required"] is True
    assert request["url"].startswith("https://catalog.archives.gov/api/v2/records/search?")
    assert request["api_key_header"] == "x-api-key"
    assert request["automated_access"] is False
    assert request["terms_review_required"] is True
    assert nara_catalog_adapter().enabled is False
    assert plan["census_finder_count"] == 30 * 2 * 5
    assert len(plan["genealogist_finders"]) == 30 * 5
    leads = genealogist_search_plan("Sample Fellow", birth_year=1910)
    assert {row["provider"] for row in leads} == {
        "chronicling_america", "stevemorse_census", "familysearch_wiki",
        "masters_traditional_arts", "findagrave_memorial"}
    assert all(row["automated_access"] is False for row in leads)
    assert "format=json" in leads[0]["url"]
    finders = {row["provider"] for row in census_finder_plan("Example Person", 1950, state="ZZ")}
    assert {"nara_1950_name_search", "nara_catalog", "steve_morse_ed_finder", "ancestry_census_index"} <= finders
    ancestry = next(row for row in census_finder_plan("Example Person", 1940) if row["provider"] == "ancestry_census_index")
    assert ancestry["automated_access"] is False and ancestry["url"] is None
    assert census_age_excludes_reference(1940, 20)
    assert census_age_excludes_reference(1950, 30)
    assert not census_age_excludes_reference(1940, 29)
    assert not census_age_excludes_reference(1950, 39)


def test_nea_cli_help_is_registered(capsys):
    from aave.cli import main
    with pytest.raises(SystemExit) as exit_info:
        main(["nea", "--help"])
    assert exit_info.value.code == 0
    assert "ingest-local" in capsys.readouterr().out
