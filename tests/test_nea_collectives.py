"""Synthetic award-year scope, identity and conservative ranking regressions."""

from datetime import date

import pytest

from aave.nea_collectives import build_collective_comparisons, evidence_classification
from aave.nea_dates import attained_age
from aave.nea_discovery import SearchAdapter, execute_batch
from aave.nea_research import adjudicate_person


def inventory():
    subject = {"person_id": "reference", "name": "Synthetic Reference", "award_id": "award-ref",
               "award_year": 1990, "profile_url": "https://example.test/ref"}
    review = {"decision_id": "review-ref", "birth": "1910-12-22", "death": "2018-10-25", "sex": "male"}
    return {"cutoff": "2026-10-23", "people": [adjudicate_person(subject, review, date(2026, 10, 23))],
            "decisions": [{**review, "person_id": "reference"}], "summary": {"unresolved_collective_awards": 1}}


def member(identifier="member", *, status="award_year", name="Synthetic Member", birth="1950"):
    return {"person_id": identifier, "name": name, "membership_status": status,
            "membership_evidence": {"source_url": "https://example.test/group", "excerpt": "award-year roster"},
            "age_review": {"decision_id": "review-" + identifier, "birth": birth}}


def award(members, *, complete=True, url="https://example.test/group"):
    return {"name": "Synthetic Ensemble", "profile_url": url, "award_year": 2000,
            "membership_complete": complete, "members": members, "blockers": ["Unenumerated members"]}


def test_later_member_is_retained_but_not_ranked():
    report = build_collective_comparisons(inventory(), [award([member(), member("later", status="later")])])
    assert report["summary"]["new_deduplicated_people"] == 1
    assert report["deferred_members"][0]["person_id"] == "later"
    association = next(p for p in report["expanded"]["people"] if p["person_id"] == "member")["associations"][0]
    assert not association["individual_fellowship_asserted"]


def test_multiple_associations_deduplicate_only_with_explicit_identity_link():
    repeated = member()
    repeated["identity_evidence"] = "Same documented performer and birth year in two award-year rosters"
    report = build_collective_comparisons(inventory(), [award([member()]), award([repeated], url="https://example.test/other")])
    assert report["summary"]["new_deduplicated_people"] == 1
    assert report["summary"]["award_year_membership_associations"] == 2
    row = next(p for p in report["expanded"]["people"] if p["person_id"] == "member")
    assert len(row["associations"]) == 2
    repeated.pop("identity_evidence")
    with pytest.raises(ValueError, match="explicit linkage"):
        build_collective_comparisons(inventory(), [award([member()]), award([repeated], url="https://example.test/other")])


def test_names_do_not_merge_and_conflicting_linked_dates_fail_closed():
    report = build_collective_comparisons(inventory(), [award([member("one"), member("two")])])
    assert report["summary"]["new_deduplicated_people"] == 2
    linked = member(birth="1949")
    linked["identity_evidence"] = "Explicit identity assertion with conflicting dates"
    report = build_collective_comparisons(inventory(), [award([member()]), award([linked], url="https://example.test/other")])
    row = next(p for p in report["expanded"]["people"] if p["person_id"] == "member")
    assert row["evidence_classification"] == "conflicted"
    assert row["age_envelope"]["upper"] is None


def test_uncertain_or_missing_members_block_historical_closure():
    for group in [award([member()], complete=False), award([member(), member("unknown", status="uncertain")]), award([])]:
        report = build_collective_comparisons(inventory(), [group])
        assert not report["expanded"]["historical_population_complete"]
        assert not report["expanded"]["universal_maximum_established"]
        assert report["expanded"]["status"] == "conditional_comparison"
        assert report["summary"]["collective_awards_fully_age_screened"] == 0


def test_exact_comparators_cannot_rank_above_longer_lifespan():
    # Synthetic labels; the supplied public date pairs are arithmetic regressions.
    first = member("longer", birth="1918-05-09")
    first["age_review"]["death"] = "2023-02-22"
    second = member("shorter", birth="1907-04-21")
    second["age_review"]["death"] = "2011-09-12"
    assert attained_age(date(1918, 5, 9), date(2023, 2, 22)) == (104, 289)
    report = build_collective_comparisons(inventory(), [award([first, second])])
    rows = {row["person_id"]: row for row in report["expanded"]["people"]}
    assert rows["longer"]["age_envelope"]["upper"] == [104, 289]
    assert rows["shorter"]["possible_rank_best"] == 3
    assert rows["longer"]["possible_rank_worst"] == 2


def test_conditional_inference_does_not_become_verified_birth_or_lifespan():
    inferred = member(birth="1921/2019")
    inferred["age_review"].update(inference_basis="inferred_parent_chronology_screen",
        assumptions=["Identity bridge", "Reported parent older than subject"])
    report = build_collective_comparisons(inventory(), [award([inferred])])
    row = next(p for p in report["expanded"]["people"] if p["person_id"] == "member")
    assert row["evidence_classification"] == "inferred_probable"
    assert row["age_envelope"]["lower"] == [0, 0]
    assert row["inference_assumptions"] == inferred["age_review"]["assumptions"]
    assert evidence_classification({"status": "insufficient_age_evidence"}, {}) == "unresolved"


def test_unknown_sex_is_kept_out_of_male_only_population():
    report = build_collective_comparisons(inventory(), [award([member()])])
    assert report["male_only"]["population_size"] == 1
    assert report["male_only"]["sex_unknown_person_ids"] == ["member"]


def test_replay_uses_existing_batch_checkpoint_without_external_queries(tmp_path):
    calls = []
    adapter = SearchAdapter(lambda query: calls.append(query) or [], "https://example.test/terms", True, 0, 1)
    queries = [{"query_id": "fixed", "query": "synthetic ensemble roster", "provider": "public", "priority": 0}]
    path = tmp_path / "checkpoint.json"
    first = execute_batch(queries, {"public": adapter}, path)
    second = execute_batch(queries, {"public": adapter}, path)
    assert first == second
    assert calls == ["synthetic ensemble roster"]


def test_omitted_collectives_do_not_establish_complete_historical_population():
    report = build_collective_comparisons(inventory(), [])
    assert not report["expanded"]["historical_population_complete"]
    assert report["expanded"]["unresolved_collective_awards"]


def test_conflicted_later_review_cannot_be_hidden_by_an_earlier_screen():
    conflicted = member()
    conflicted["identity_evidence"] = "Claimed same performer; later source has identity conflict"
    conflicted["age_review"]["conflict"] = "Source attribution contradicted"
    report = build_collective_comparisons(inventory(), [award([member()]),
        award([conflicted], url="https://example.test/other")])
    row = next(p for p in report["expanded"]["people"] if p["person_id"] == "member")
    assert row["status"] == "identity_conflict"
    assert row["age_envelope"]["upper"] is None
    assert len(row["associated_reviews"]) == 2


def test_died_by_date_is_only_a_cap_even_with_an_exact_birth():
    bounded = member(birth="1900-01-01")
    bounded["age_review"]["death_not_after"] = "2000-01-01"
    report = build_collective_comparisons(inventory(), [award([bounded])])
    row = next(p for p in report["expanded"]["people"] if p["person_id"] == "member")
    assert row["age_envelope"]["upper"] == [100, 0]
    assert row["age_envelope"]["lower"] == [0, 0]
    assert row["death_evidence"] == "Died by 2000-01-01"
    assert row["exact_date_subset_rank"] is None


def test_collective_citation_validation_rejects_changed_bytes_and_missing_awards(tmp_path):
    import hashlib
    import json
    from aave.nea_collective_sources import load_reviewed_awards

    (tmp_path / "data").mkdir()
    cache = tmp_path / "local-vault/source.html"
    cache.parent.mkdir()
    cache.write_bytes(b"<p>Synthetic Member is in the award-year ensemble.</p>")
    url = "https://example.test/group"
    digest = hashlib.sha256(cache.read_bytes()).hexdigest()
    source = {"source_url": url, "source_sha256": digest, "local_ignored_cache": "local-vault/source.html"}
    group = award([member()])
    group.update(membership_rationale="The source enumerates the award-year roster", sources=[source])
    group["members"][0].update(age_review=None,
        membership_evidence={**source, "excerpt": "Synthetic Member is in the award-year ensemble.", "rationale": "Subject attributed"})
    documents = {
        "nea-research-reviews.json": {"collective_awards": [{"profile_url": url, "membership_complete": False}]},
        "nea-recipient-age-audit.json": {"entries": [{"profile_url": url, "award_year": 2000}]},
        "nea-male-ranking-coverage.json": {"entries": [{"profile_url": url, "profile_sha256": digest}]},
        "cohort.json": {"awards": [group]},
    }
    for filename, document in documents.items():
        (tmp_path / "data" / filename).write_text(json.dumps(document), encoding="utf-8")
    path = tmp_path / "data/cohort.json"
    groups, audit = load_reviewed_awards(tmp_path, [path])
    assert len(groups) == 1 and audit["citation_excerpts_verified"] == 1
    with pytest.raises(ValueError, match="exactly once"):
        load_reviewed_awards(tmp_path, [])
    cache.write_bytes(b"Changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_reviewed_awards(tmp_path, [path])


def screen(**changes):
    value = {"source_url": "https://example.test/group", "source_sha256": "0" * 64,
             "excerpt": "about 50 members between the ages of 16 and 70",
             "rationale": "Official group-wide age statement applies to every member",
             "as_of": "2025-06-01", "stated_max_age_years": 70, "tolerance_years": 25}
    value.update(changes)
    return value


def screened_award(**changes):
    group = award([member()], complete=False)
    group["collective_age_screen"] = screen(**changes)
    return group


def test_valid_group_age_screen_is_reported_separately_and_does_not_complete_the_roster():
    report = build_collective_comparisons(inventory(), [screened_award()])
    summary = report["summary"]
    assert summary["unresolved_membership_boundaries"] == 0
    assert summary["boundaries_age_screened_without_complete_roster"] == 1
    assert summary["collective_membership_boundaries_resolved"] == 0
    assert summary["collective_awards_fully_age_screened"] == 0
    expanded = report["expanded"]
    assert expanded["unresolved_collective_awards"] == []
    entry = expanded["age_screened_collective_awards"][0]
    assert entry["roster_complete"] is False and entry["oldest_possible_birth_year"] == 1929
    assert not expanded["historical_population_complete"]
    assert not expanded["universal_maximum_established"]
    assert expanded["status"] == "conditional_comparison"
    assert report["male_only"]["age_screened_collective_awards"] == expanded["age_screened_collective_awards"]


def test_weak_missing_or_future_group_age_screens_leave_the_boundary_open():
    weak = [screened_award(stated_max_age_years=95), screened_award(tolerance_years=0),
            screened_award(tolerance_years=4), screened_award(as_of="2030-01-01"),
            screened_award(as_of="not-a-date"), screened_award(stated_max_age_years=True),
            screened_award(excerpt=""), screened_award(source_sha256=None)]
    for group in weak:
        report = build_collective_comparisons(inventory(), [group])
        assert report["summary"]["unresolved_membership_boundaries"] == 1
        assert report["summary"]["boundaries_age_screened_without_complete_roster"] == 0
        assert report["expanded"]["age_screened_collective_awards"] == []


def test_unscreened_incomplete_roster_blocks_and_a_screen_covers_uncertain_members_without_completing_the_roster():
    report = build_collective_comparisons(inventory(), [award([member()], complete=False)])
    assert report["summary"]["unresolved_membership_boundaries"] == 1
    assert report["summary"]["boundaries_age_screened_without_complete_roster"] == 0
    group = screened_award()
    group["members"].append(member("unknown", status="uncertain"))
    report = build_collective_comparisons(inventory(), [group])
    assert report["summary"]["boundaries_age_screened_without_complete_roster"] == 1
    assert report["expanded"]["age_screened_collective_awards"][0]["roster_complete"] is False


def test_age_screen_citation_must_appear_in_the_registered_cached_source(tmp_path):
    import hashlib
    import json
    from aave.nea_collective_sources import load_reviewed_awards

    (tmp_path / "data").mkdir()
    cache = tmp_path / "local-vault/source.html"
    cache.parent.mkdir()
    cache.write_bytes(b"<p>The chorus has about 50 members between the ages of 16 and 70.</p>")
    url = "https://example.test/group"
    digest = hashlib.sha256(cache.read_bytes()).hexdigest()
    source = {"source_url": url, "source_sha256": digest, "local_ignored_cache": "local-vault/source.html"}
    group = award([], complete=False)
    group.update(membership_rationale="No roster is published", sources=[source],
                 collective_age_screen=screen(source_url=url, source_sha256=digest))
    documents = {
        "nea-research-reviews.json": {"collective_awards": [{"profile_url": url, "membership_complete": False}]},
        "nea-recipient-age-audit.json": {"entries": [{"profile_url": url, "award_year": 2000}]},
        "nea-male-ranking-coverage.json": {"entries": [{"profile_url": url, "profile_sha256": digest}]},
        "cohort.json": {"awards": [group]},
    }
    for filename, document in documents.items():
        (tmp_path / "data" / filename).write_text(json.dumps(document), encoding="utf-8")
    path = tmp_path / "data/cohort.json"
    _, audit = load_reviewed_awards(tmp_path, [path])
    assert audit["citation_excerpts_verified"] == 1
    group["collective_age_screen"]["excerpt"] = "members between the ages of 16 and 40"
    path.write_text(json.dumps({"awards": [group]}), encoding="utf-8")
    with pytest.raises(ValueError, match="[Ee]xcerpt"):
        load_reviewed_awards(tmp_path, [path])
