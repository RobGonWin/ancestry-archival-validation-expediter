"""Privacy and source-confidence labels for conservative archive processing."""

PRIVACY_LABELS = {
    "public_ok",
    "public_summary_only",
    "private_family_only",
    "expert_review_only",
    "do_not_share",
    "living_person_redacted",
    "raw_dna_never_export",
}

SOURCE_CONFIDENCE_LABELS = {
    "confirmed",
    "probable",
    "family_identified",
    "personal_recollection",
    "needs_review",
    "public_secondary",
    "private_artifact",
}

DEFAULT_PRIVACY_LABEL = "private_family_only"
DEFAULT_SOURCE_CONFIDENCE = "needs_review"
