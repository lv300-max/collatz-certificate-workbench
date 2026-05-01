#!/usr/bin/env python3
"""
quotient_abstraction_validity.py

Audit whether the quotient abstraction is fully proven from exported data.

This report is deliberately strict. If the current artifacts only verify
tracked representatives and exported conflict counters, the status remains
INCOMPLETE_QUOTIENT_ABSTRACTION.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUT = Path("quotient_abstraction_validity_report.json")
QREPORT = Path("excursion_quotient_report.json")
QPARENT = Path("quotient_parent_batch_report.json")
QKEY = Path("quotient_key_validity_audit_report.json")
QTRANSITION = Path("quotient_transition_table.json")
QTRANSITION_AUDIT = Path("quotient_transition_table_audit_report.json")
QEXACT_FALLBACK = Path("quotient_exact_state_fallback_audit_report.json")


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def main() -> None:
    qreport = load_json(QREPORT) or {}
    qparent = load_json(QPARENT) or {}
    qkey = load_json(QKEY) or {}
    qtransition = load_json(QTRANSITION) or {}
    qtransition_audit = load_json(QTRANSITION_AUDIT) or {}
    qexact_fallback = load_json(QEXACT_FALLBACK) or {}

    q_summary = qreport.get("summary", {})
    p_rows = qparent.get("parent_rows", [])
    qkey_method = qkey.get("method", {})
    conflicts = (
        as_int(q_summary.get("conflicts"))
        + sum(as_int(row.get("conflict_count")) for row in p_rows)
        + as_int(qkey.get("parent_batch_audit", {}).get("summary", {}).get("conflicts"))
    )
    sampled_as_proof_keys = []
    for row in p_rows:
        if row.get("sampled") or row.get("sampled_as_proof"):
            sampled_as_proof_keys.append(row.get("r0"))

    quotient_key_definition = {
        "source": "excursion_quotient_analyzer.py",
        "key_formula": (
            "if c <= level: (s, q, o-BASE_O, c-BASE_C), where s=level-c and "
            "q=((a*residue+b)>>c) mod 2^s; otherwise needs-branch diagnostic key"
        ),
        "proof_critical_state_needed": [
            "low known iterate bits q",
            "remaining level distance s",
            "offset odd/even counts o-BASE_O and c-BASE_C",
            "exact affine coefficients or representative state for B certification",
            "successor key set for deterministic quotient merging",
        ],
    }

    transition_table_exported = qtransition_audit.get("status") == "PASS_QUOTIENT_TRANSITION_TABLE"
    exact_state_fallback_pass = qexact_fallback.get("status") == "PASS_EXACT_STATE_FALLBACK_FOR_TRACKED_KEYS"
    full_equivalence_proven = qtransition.get("full_equivalence_proven") is True
    representative_only_keys = as_int(q_summary.get("n_keys")) or max(
        (as_int(row.get("quotient_keys")) for row in p_rows),
        default=0,
    )
    proof_critical_keys_checked = qkey.get("frontier_coverage_audit", {}).get("summary", {}).get(
        "quotient_open_keys",
        q_summary.get("summary", {}).get("quotient_open_keys"),
    )
    exact_state_continuations = {
        "local_keys_attempted": sum(as_int(row.get("local_keys_attempted")) for row in p_rows),
        "local_keys_certified": sum(as_int(row.get("local_keys_certified")) for row in p_rows),
        "local_keys_high_b_certified": sum(as_int(row.get("local_keys_high_b_certified")) for row in p_rows),
        "return_map_records": qkey.get("frontier_coverage_audit", {}).get("summary", {}).get("return_map_records"),
        "b_control_records": qkey.get("frontier_coverage_audit", {}).get("summary", {}).get("b_control_records"),
    }

    missing_state_keys: list[dict[str, Any]] = []
    mixed_outcome_keys: list[dict[str, Any]] = []
    requires_external_lemma = not full_equivalence_proven
    if requires_external_lemma:
        if not transition_table_exported:
            missing_state_keys.append(
                {
                    "kind": "transition_table_not_exported_or_not_passing",
                    "reason": "No passing quotient_transition_table_audit_report.json is available for tracked keys.",
                }
            )
        if transition_table_exported and not full_equivalence_proven:
            missing_state_keys.append(
                {
                    "kind": "full_equivalence_not_proven",
                    "reason": (
                        "The tracked quotient transition table passes"
                        + (" with exact-state fallback" if exact_state_fallback_pass else "")
                        + ", but it does not prove that tracked keys represent full quotient equivalence classes."
                    ),
                }
            )

    if conflicts:
        status = "FAIL_QUOTIENT_ABSTRACTION"
    elif sampled_as_proof_keys:
        status = "FAIL_QUOTIENT_ABSTRACTION"
    elif transition_table_exported and exact_state_fallback_pass and requires_external_lemma:
        status = "PASS_TRACKED_QUOTIENT_TABLE_WITH_EXACT_STATE_FALLBACK"
    elif transition_table_exported and requires_external_lemma:
        status = "PASS_TRACKED_QUOTIENT_TRANSITION_TABLE"
    elif requires_external_lemma:
        status = "INCOMPLETE_QUOTIENT_ABSTRACTION"
    else:
        status = "PASS_QUOTIENT_ABSTRACTION"

    report = {
        "status": status,
        "plain_truth": (
            "This is the quotient abstraction validity gate. It does not claim the full proof is complete."
        ),
        "quotient_key_definition": quotient_key_definition,
        "quotient_keys_checked": representative_only_keys,
        "proof_critical_keys_checked": proof_critical_keys_checked,
        "conflicts": conflicts,
        "mixed_outcome_keys": mixed_outcome_keys,
        "missing_state_keys": missing_state_keys,
        "sampled_as_proof_keys": sampled_as_proof_keys,
        "exact_state_continuations": exact_state_continuations,
        "representative_only_keys": representative_only_keys,
        "requires_external_lemma": requires_external_lemma,
        "transition_table_exported": transition_table_exported,
        "exact_state_fallback_pass": exact_state_fallback_pass,
        "full_equivalence_proven": full_equivalence_proven,
        "transition_table_report": {
            "table_path": str(QTRANSITION),
            "audit_path": str(QTRANSITION_AUDIT),
            "audit_status": qtransition_audit.get("status"),
            "proof_critical_keys_checked": qtransition_audit.get("proof_critical_keys_checked"),
            "sampled_as_proof_count": qtransition_audit.get("sampled_as_proof_count"),
            "conflicts": qtransition_audit.get("conflicts"),
            "still_open": qtransition_audit.get("still_open"),
            "final_B_over_200001": qtransition_audit.get("final_B_over_200001"),
            "full_equivalence_proven": full_equivalence_proven,
        },
        "exact_state_fallback_report": {
            "path": str(QEXACT_FALLBACK),
            "status": qexact_fallback.get("status"),
            "tracked_keys_checked": qexact_fallback.get("tracked_keys_checked"),
            "sampled_as_proof_count": qexact_fallback.get("sampled_as_proof_count"),
            "arithmetic_failure_count": qexact_fallback.get("arithmetic_failure_count"),
            "final_B_over_200001_count": qexact_fallback.get("final_B_over_200001_count"),
            "relies_on_compact_quotient_equivalence": qexact_fallback.get("relies_on_compact_quotient_equivalence"),
        },
        "audit_answers": {
            "what_fields_define_a_quotient_key": quotient_key_definition["key_formula"],
            "does_each_key_store_enough_state_to_determine_future_behavior": (
                "tracked keys have passing exported transition rows and exact-state fallback; full equivalence is not proven"
                if transition_table_exported and exact_state_fallback_pass and requires_external_lemma
                else "tracked keys have passing exported transition rows; full equivalence is not proven"
                if transition_table_exported and requires_external_lemma else ("not proven from exported data" if requires_external_lemma else "yes")
            ),
            "are_collapsed_affine_states_fully_audited": (
                "tracked proof-critical rows have exact-state fallback; full quotient equivalence classes are not proven"
                if exact_state_fallback_pass
                else "no; tracked table passes but full quotient equivalence classes are not proven"
                if requires_external_lemma
                else "yes"
            ),
            "are_conflicts_impossible_by_definition_or_unobserved": (
                "no conflicts in tracked transition table; impossibility for full equivalence requires external lemma"
                if requires_external_lemma
                else "audited by exported transition table"
            ),
            "are_cap_stopped_keys_continued_from_exact_state": (
                qkey.get("frontier_coverage_audit", {}).get("pass") is True
            ),
        },
        "required_for_pass": [
            "Export per-key representative_count, successor_key_set, and conflict_count for every quotient key.",
            "Keep quotient_exact_state_fallback_audit_report.json passing for every tracked proof-critical key.",
            "Or provide a formal lemma proving the quotient key determines all proof-critical successors.",
            "Keep sampled_as_proof_keys empty and conflicts zero.",
        ],
    }

    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("QUOTIENT ABSTRACTION VALIDITY")
    print(f"  Status                  : {status}")
    print(f"  Conflicts               : {conflicts}")
    print(f"  Sampled proof keys       : {len(sampled_as_proof_keys)}")
    print(f"  Exact fallback pass      : {exact_state_fallback_pass}")
    print(f"  Requires external lemma  : {requires_external_lemma}")
    print(f"  Report                  : {OUT}")


if __name__ == "__main__":
    main()
