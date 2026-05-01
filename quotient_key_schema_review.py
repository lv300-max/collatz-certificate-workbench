#!/usr/bin/env python3
"""
quotient_key_schema_review.py

Review the current quotient key schema against the proof-critical state needed
for a full quotient-abstraction lemma.

This is a source/report audit. It does not run random seeds, raise caps, or
claim a proof.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


OUT = Path("quotient_key_schema_review_report.json")
EQA = Path("excursion_quotient_analyzer.py")
TRANSITION_AUDIT = Path("quotient_transition_table_audit_report.json")
ABSTRACTION = Path("quotient_abstraction_validity_report.json")
EXACT_FALLBACK = Path("quotient_exact_state_fallback_audit_report.json")


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_quotient_key_source() -> str | None:
    if not EQA.exists():
        return None
    text = EQA.read_text(encoding="utf-8")
    match = re.search(r"def quotient_key\(state\):(?P<body>.*?)(?:\n\ndef |\Z)", text, re.S)
    return match.group(0).strip() if match else None


def main() -> None:
    key_source = extract_quotient_key_source()
    transition_audit = load_json(TRANSITION_AUDIT) or {}
    abstraction = load_json(ABSTRACTION) or {}
    exact_fallback = load_json(EXACT_FALLBACK) or {}

    current_key_fields = [
        {
            "field": "s = level - c",
            "present": key_source is not None and "s = level - c" in key_source,
            "proof_role": "known low-bit window length",
        },
        {
            "field": "q = ((a * residue + b) >> c) mod 2^s",
            "present": key_source is not None and "q =" in key_source and "a * residue + b" in key_source,
            "proof_role": "known low bits of current iterate",
        },
        {
            "field": "o - BASE_O",
            "present": key_source is not None and "o - BASE_O" in key_source,
            "proof_role": "odd-count offset",
        },
        {
            "field": "c - BASE_C",
            "present": key_source is not None and "c - BASE_C" in key_source,
            "proof_role": "halving-count offset",
        },
        {
            "field": "r0 / lane residue in normal c<=level key",
            "present": False,
            "proof_role": "lane identity; only appears in needs-branch diagnostic key",
        },
        {
            "field": "full b or b modulo proof-critical modulus",
            "present": False,
            "proof_role": "B threshold and affine carry/certification",
        },
        {
            "field": "explicit carry / overflow",
            "present": False,
            "proof_role": "distinguishes affine states with same low iterate bits",
        },
        {
            "field": "frontier/parity word",
            "present": False,
            "proof_role": "history needed for a direct state-agreement lemma",
        },
        {
            "field": "gap sign/magnitude",
            "present": False,
            "proof_role": "descent threshold condition",
        },
    ]

    missing_for_direct_state_agreement = [
        item for item in current_key_fields
        if item["field"] in {
            "r0 / lane residue in normal c<=level key",
            "full b or b modulo proof-critical modulus",
            "explicit carry / overflow",
            "frontier/parity word",
            "gap sign/magnitude",
        }
        and not item["present"]
    ]

    tracked_transition_pass = transition_audit.get("status") == "PASS_QUOTIENT_TRANSITION_TABLE"
    exact_fallback_pass = exact_fallback.get("status") == "PASS_EXACT_STATE_FALLBACK_FOR_TRACKED_KEYS"
    full_equivalence_proven = abstraction.get("full_equivalence_proven") is True
    state_agreement_status = (
        "PASS_STATE_AGREEMENT_SCHEMA"
        if not missing_for_direct_state_agreement
        else "INCOMPLETE_STATE_AGREEMENT_SCHEMA"
    )
    transition_closure_status = (
        "PASS_TRACKED_TRANSITION_CLOSURE"
        if tracked_transition_pass
        else "INCOMPLETE_TRACKED_TRANSITION_CLOSURE"
    )
    status = (
        "PASS_QUOTIENT_KEY_SCHEMA"
        if state_agreement_status == "PASS_STATE_AGREEMENT_SCHEMA" and full_equivalence_proven
        else "INCOMPLETE_QUOTIENT_KEY_SCHEMA"
    )

    report = {
        "status": status,
        "plain_truth": (
            "The current key has a passing tracked transition table, but its schema does not by itself "
            "encode all proof-critical state listed in the state-agreement lemma."
        ),
        "current_quotient_key_source": key_source,
        "current_key_fields": current_key_fields,
        "proof_critical_state_required_for_direct_schema_pass": [
            "lane residue r0 and modulus/depth",
            "odd count o",
            "halving count c",
            "offset b or a proven sufficient residue/carry projection",
            "affine carry/overflow information",
            "gap sign/magnitude or exact recomputable gap",
            "parity/frontier word or a theorem proving q,s,o,c determine future parity",
            "successor key set closure",
        ],
        "state_agreement_status": state_agreement_status,
        "transition_closure_status": transition_closure_status,
        "missing_for_direct_state_agreement": missing_for_direct_state_agreement,
        "tracked_transition_table_status": transition_audit.get("status"),
        "tracked_transition_keys_checked": transition_audit.get("proof_critical_keys_checked"),
        "exact_state_fallback_status": exact_fallback.get("status"),
        "exact_state_fallback_keys_checked": exact_fallback.get("tracked_keys_checked"),
        "full_equivalence_proven": full_equivalence_proven,
        "requires_external_lemma": not full_equivalence_proven,
        "valid_fix_paths": [
            {
                "path": "formal_lemma",
                "requirement": (
                    "Prove algebraically that (s,q,o-BASE_O,c-BASE_C) determines every proof-critical "
                    "successor and certification quantity needed by the framework."
                ),
            },
            {
                "path": "augmented_key_schema",
                "requirement": (
                    "Change quotient_key to include a lossless proof-critical projection such as r0/depth, "
                    "o, c, b or sufficient b/carry projection, gap sign, and parity/frontier invariant; "
                    "then rerun parent batch and transition-table audits."
                ),
            },
            {
                "path": "exact_state_fallback",
                "requirement": (
                    "Bypass quotient equivalence for hard keys and export exact continuation for every "
                    "proof-critical state used by closure."
                ),
                "current_status": "PASS_FOR_TRACKED_KEYS" if exact_fallback_pass else "NOT_PASSING",
            },
        ],
    }
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("QUOTIENT KEY SCHEMA REVIEW")
    print(f"  Status                    : {status}")
    print(f"  State agreement schema    : {state_agreement_status}")
    print(f"  Tracked transition closure: {transition_closure_status}")
    print(f"  Exact-state fallback      : {exact_fallback.get('status')}")
    print(f"  Missing schema fields     : {len(missing_for_direct_state_agreement)}")
    print(f"  Report                    : {OUT}")


if __name__ == "__main__":
    main()
