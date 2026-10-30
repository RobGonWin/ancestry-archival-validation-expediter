"""Content-bound verification slices for resumable historical research."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def slice_fingerprint(inputs: dict, *, cutoff: str, rules_version: str) -> str:
    """Bind a slice to source hashes, predecessor decisions, cutoff and review rules."""
    payload = {"inputs": inputs, "cutoff": cutoff, "rules_version": rules_version}
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def reusable_slice(receipt: dict, fingerprint: str) -> bool:
    """Reuse completed decisions and bounded failures only while their inputs match.

    A blocked receipt preserves its lead without authorizing another identical
    retrieval. An explicit new input (including an access-state revision) reopens it.
    """
    can_reuse = (receipt.get("fingerprint") == fingerprint
                 and receipt.get("status") in {"completed", "blocked"})
    return can_reuse


def save_slice(path: Path, receipt: dict) -> None:
    """Atomically persist a reviewed slice with explicit limits and source roles."""
    required = {"slice_id", "fingerprint", "status", "source_roles", "decision", "blockers"}
    if not required.issubset(receipt):
        raise ValueError("Verification slice lacks required provenance fields")
    if receipt["status"] not in {"completed", "blocked", "needs_review"}:
        raise ValueError("Unknown verification slice status")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
