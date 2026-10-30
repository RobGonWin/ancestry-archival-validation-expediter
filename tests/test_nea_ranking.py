"""Synthetic rank tests: unresolved identities, caps and ties must remain visible."""

from aave.nea_ranking import build_individual_ranking


def person(identifier, age=None, *, exact=False, status=None):
    row = {"person_id": identifier, "name": identifier, "award_year": 2000,
           "profile_url": "https://example.test/" + identifier,
           "status": status or ("verified_equal_roma" if exact else "bounded_below_roma_at_cutoff"),
           "completed_lifespan_documented": exact}
    if age is not None:
        row["upper_age"] = age
    return row


def report(people, decisions=None):
    return build_individual_ranking({"people": people, "decisions": decisions or [],
                                     "cutoff": "2026-10-23",
                                     "summary": {"unresolved_collective_awards": 36}})


def indexed(result):
    return {row["person_id"]: row for row in result["people"]}


def test_unknown_person_can_intervene_above_reference():
    result = report([person("reference", [107, 307], exact=True),
                     person("unknown", status="muted_edge_case"), person("cap", [90, 0])])
    reference = indexed(result)["reference"]
    assert (reference["possible_rank_best"], reference["possible_rank_worst"]) == (1, 2)
    assert result["status"] == "not_established"
    assert result["excluded_collective_awards"] == 36
    assert result["named_people"] == 3


def test_screening_cap_is_not_lifespan_or_lower_endpoint():
    result = indexed(report([person("exact", [100, 0], exact=True), person("cap", [106, 0])]))
    assert result["cap"]["age_envelope"]["lower"] == [0, 0]
    assert result["cap"]["exact_date_subset_rank"] is None
    assert result["exact"]["exact_date_subset_rank"] == 1
    assert result["exact"]["possible_rank_worst"] == 2


def test_known_exact_ties_share_rank_and_do_not_intervene():
    result = indexed(report([person("a", [99, 1], exact=True),
                             person("b", [99, 1], exact=True), person("c", [98, 0], exact=True)]))
    assert result["a"]["possible_rank_worst"] == result["b"]["possible_rank_worst"] == 1
    assert result["c"]["possible_rank_best"] == result["c"]["possible_rank_worst"] == 3


def test_reported_age_has_exclusive_next_birthday_bound():
    result = indexed(report([person("exact", [104, 0], exact=True), person("reported")],
                             [{"person_id": "reported", "completed_age_years": 103,
                               "death_by_cutoff": True}]))
    assert result["reported"]["age_envelope"]["upper_exclusive"]
    assert result["reported"]["possible_rank_best"] == 2
    assert result["exact"]["possible_rank_worst"] == 1


def test_muted_or_conflicted_dates_never_supply_an_age_cap():
    for status in ["muted_edge_case", "identity_conflict", "insufficient_age_evidence"]:
        row = indexed(report([person("unreviewed", [50, 0], exact=True, status=status)]))["unreviewed"]
        assert row["age_envelope"]["upper"] is None
        assert row["exact_date_subset_rank"] is None
