#!/usr/bin/env python3
"""
quotient_key_validity_audit.py

Audit the exported quotient-key closure evidence for the 578 depth >18 parent
lanes.  This script uses no random seeds and does not use floats for proof
decisions.  It does not claim the full theorem is proven.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


QPARENT = Path("quotient_parent_batch_report.json")
FRONTIER_COVERAGE = Path("frontier_coverage_audit_report.json")
RETURN_MAP = Path("frontier_return_map_report.json")
B_CONTROL = Path("b_control_report.json")
QTRANSITION_AUDIT = Path("quotient_transition_table_audit_report.json")
QEXACT_FALLBACK = Path("quotient_exact_state_fallback_audit_report.json")
OUT = Path("quotient_key_validity_audit_report.json")

B_LIMIT = 200_001
EXPECTED_PARENTS = 578
CLOSED_STATUSES = {
    "CLOSED_BY_QUOTIENT",
    "CLOSED_WITH_LOCAL_KEYS",
    "OPEN_KEYS_COVERED_BY_EXISTING_FRONTIER",
    "COVERED_BUT_CAP_REACHED",
}
LOCAL_GOOD = {"CERTIFIED_RETURN", "HIGH_B_RETURN_THEN_CERTIFIED"}


def load_json(path: Path, required: bool = True) -> Any:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def key_id(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=False)


def bool_bad(value: Any) -> bool:
    return value not in (False, 0, None)


def audit_parent_rows(batch: dict[str, Any]) -> dict[str, Any]:
    rows = batch.get("parent_rows", [])
    ids = [row.get("r0") for row in rows]
    id_counts = Counter(ids)
    duplicate_ids = sorted(r0 for r0, count in id_counts.items() if r0 is not None and count > 1)

    missing_identity: list[dict[str, Any]] = []
    bad_status_rows: list[dict[str, Any]] = []
    conflict_rows: list[dict[str, Any]] = []
    sampled_rows: list[dict[str, Any]] = []
    cap_semantic_failures: list[dict[str, Any]] = []
    open_export_failures: list[dict[str, Any]] = []
    local_failures: list[dict[str, Any]] = []
    local_examples_seen = 0
    local_examples_expected = 0
    high_b_positive_diagnostic_count = 0

    for index, row in enumerate(rows):
        identity_missing = [
            field
            for field in ("r0", "k_prime", "depth", "status")
            if field not in row or row.get(field) is None
        ]
        if identity_missing:
            missing_identity.append(
                {"row_index": index, "r0": row.get("r0"), "missing_fields": identity_missing}
            )
        if row.get("status") not in CLOSED_STATUSES:
            bad_status_rows.append(
                {"row_index": index, "r0": row.get("r0"), "status": row.get("status")}
            )
        if as_int(row.get("conflict_count")) != 0:
            conflict_rows.append(
                {
                    "row_index": index,
                    "r0": row.get("r0"),
                    "conflict_count": row.get("conflict_count"),
                }
            )
        if bool_bad(row.get("sampled")) or bool_bad(row.get("sampled_as_proof")):
            sampled_rows.append(
                {"row_index": index, "r0": row.get("r0"), "sampled": row.get("sampled")}
            )
        if row.get("status") == "COVERED_BUT_CAP_REACHED":
            open_count = as_int(row.get("open_key_count"))
            covered = as_int(row.get("covered_open_key_count"))
            uncovered = as_int(row.get("uncovered_open_key_count"))
            if open_count == 0 or uncovered != 0 or covered != open_count:
                cap_semantic_failures.append(
                    {
                        "row_index": index,
                        "r0": row.get("r0"),
                        "open_key_count": open_count,
                        "covered_open_key_count": covered,
                        "uncovered_open_key_count": uncovered,
                    }
                )
        if row.get("open_keys_all_exported_in_parent_run") is not True:
            open_export_failures.append(
                {"row_index": index, "r0": row.get("r0"), "value": row.get("open_keys_all_exported_in_parent_run")}
            )

        high_b_positive_diagnostic_count += as_int(row.get("bad_B_positive_count"))
        local_examples = row.get("local_key_examples", [])
        local_examples_seen += len(local_examples)
        local_examples_expected += as_int(row.get("local_keys_attempted"))
        for local_index, item in enumerate(local_examples):
            reasons: list[str] = []
            classification = item.get("classification")
            if classification not in LOCAL_GOOD:
                reasons.append(f"bad local classification {classification}")
            if not item.get("key"):
                reasons.append("missing local key")
            if not item.get("return_pair"):
                reasons.append("missing return_pair")
            if classification == "CERTIFIED_RETURN":
                if as_int(item.get("B"), B_LIMIT + 1) > B_LIMIT:
                    reasons.append(f"B exceeds limit: {item.get('B')}")
            elif classification == "HIGH_B_RETURN_THEN_CERTIFIED":
                final_b = item.get("b_control_next", {}).get("B")
                if as_int(final_b, B_LIMIT + 1) > B_LIMIT:
                    reasons.append(f"b_control_next.B exceeds limit: {final_b}")
            if reasons:
                local_failures.append(
                    {
                        "row_index": index,
                        "local_index": local_index,
                        "r0": row.get("r0"),
                        "reasons": reasons,
                        "record": item,
                    }
                )

    summary = batch.get("summary", {})
    pass_ok = (
        len(rows) == EXPECTED_PARENTS
        and as_int(summary.get("total_depth_gt_18_parents")) == EXPECTED_PARENTS
        and as_int(summary.get("processed_parents")) == EXPECTED_PARENTS
        and as_int(summary.get("missing_or_unprocessed_parents")) == 0
        and not duplicate_ids
        and not missing_identity
        and not bad_status_rows
        and not conflict_rows
        and not sampled_rows
        and not cap_semantic_failures
        and not open_export_failures
        and not local_failures
        and local_examples_seen == local_examples_expected
    )

    return {
        "pass": pass_ok,
        "row_count": len(rows),
        "summary": summary,
        "status_counts": dict(Counter(row.get("status") for row in rows)),
        "duplicate_parent_ids": duplicate_ids,
        "missing_identity_rows": missing_identity[:50],
        "bad_status_rows": bad_status_rows[:50],
        "conflict_rows": conflict_rows[:50],
        "sampled_rows": sampled_rows[:50],
        "cap_semantic_failures": cap_semantic_failures[:50],
        "open_export_failures": open_export_failures[:50],
        "local_examples_expected": local_examples_expected,
        "local_examples_seen": local_examples_seen,
        "local_failures": local_failures[:50],
        "high_B_positive_diagnostic_count": high_b_positive_diagnostic_count,
        "high_B_positive_note": (
            "bad_B_positive_count is diagnostic in quotient exploration; high-B positive states "
            "are not accepted as closed returns unless later covered by return-map/B-control evidence."
        ),
    }


def audit_frontier_coverage(frontier: dict[str, Any]) -> dict[str, Any]:
    summary = frontier.get("summary", {})
    checks = frontier.get("checks", {})
    missing = frontier.get("missing_keys", {})
    failures = {
        key: value
        for key, value in missing.items()
        if value not in ([], {}, 0, None)
    }
    required_checks = [
        "every_open_key_exported",
        "every_open_key_return_mapped",
        "every_high_B_key_B_controlled",
        "every_high_B_eventually_certified",
        "no_still_debt_keys",
        "no_conflicts",
        "no_final_B_over_200001",
    ]
    bad_checks = [key for key in required_checks if checks.get(key) is not True]
    pass_ok = (
        summary.get("pass") is True
        and not bad_checks
        and not failures
        and as_int(summary.get("quotient_open_keys")) == as_int(summary.get("return_map_records"))
        and as_int(summary.get("high_B_returns")) == as_int(summary.get("b_control_records"))
        and as_int(summary.get("final_B_over_limit")) == 0
        and as_int(summary.get("max_final_B")) <= B_LIMIT
        and as_int(summary.get("conflicts")) == 0
        and as_int(summary.get("still_debt_keys")) == 0
    )
    return {
        "pass": pass_ok,
        "summary": summary,
        "checks": checks,
        "bad_checks": bad_checks,
        "nonempty_missing_key_sets": failures,
    }


def audit_return_map(return_map: dict[str, Any]) -> dict[str, Any]:
    records = return_map.get("return_records", [])
    bad_records: list[dict[str, Any]] = []
    high_b_keys = set()
    certified_keys = set()
    for index, rec in enumerate(records):
        classification = rec.get("classification")
        key = rec.get("key")
        reasons: list[str] = []
        if classification not in {"CERTIFIED_RETURN", "HIGH_B_RETURN"}:
            reasons.append(f"bad classification {classification}")
        if not key:
            reasons.append("missing key")
        if not rec.get("return_pair"):
            reasons.append("missing return_pair")
        b_value = rec.get("B")
        if classification == "CERTIFIED_RETURN" and as_int(b_value, B_LIMIT + 1) > B_LIMIT:
            reasons.append(f"CERTIFIED_RETURN B exceeds limit: {b_value}")
        if classification == "HIGH_B_RETURN":
            high_b_keys.add(key_id(key))
            if as_int(b_value, 0) <= B_LIMIT:
                reasons.append(f"HIGH_B_RETURN B is not above limit: {b_value}")
        if classification == "CERTIFIED_RETURN":
            certified_keys.add(key_id(key))
        if reasons:
            bad_records.append({"index": index, "key": key, "reasons": reasons, "record": rec})

    summary = return_map.get("summary", {})
    pass_ok = (
        not bad_records
        and len(records) == as_int(summary.get("open_states_analyzed"))
        and as_int(summary.get("conflicts")) == 0
        and as_int(summary.get("still_debt_at_cap")) == 0
        and as_int(summary.get("certified_returns")) + as_int(summary.get("high_B_returns")) == len(records)
    )
    return {
        "pass": pass_ok,
        "record_count": len(records),
        "summary": summary,
        "bad_records": bad_records[:50],
        "high_B_key_count": len(high_b_keys),
        "certified_key_count": len(certified_keys),
        "high_B_keys": sorted(high_b_keys),
    }


def audit_b_control(b_control: dict[str, Any], high_b_keys: set[str]) -> dict[str, Any]:
    chains = b_control.get("high_B_chains", [])
    bad_records: list[dict[str, Any]] = []
    controlled_keys = set()
    for index, rec in enumerate(chains):
        key = rec.get("key")
        controlled_keys.add(key_id(key))
        reasons: list[str] = []
        if rec.get("classification") != "B_EVENTUALLY_CERTIFIED":
            reasons.append(f"bad classification {rec.get('classification')}")
        for field in ("starting_B", "first_later_B", "max_later_B"):
            if field in rec and as_int(rec.get(field), B_LIMIT + 1) > B_LIMIT and field != "starting_B":
                reasons.append(f"{field} exceeds limit: {rec.get(field)}")
        zero_b = rec.get("zero_tail_certification", {}).get("B")
        if as_int(zero_b, B_LIMIT + 1) > B_LIMIT:
            reasons.append(f"zero_tail_certification.B exceeds limit: {zero_b}")
        if not key:
            reasons.append("missing key")
        if reasons:
            bad_records.append({"index": index, "key": key, "reasons": reasons, "record": rec})

    missing_high_b = sorted(high_b_keys - controlled_keys)
    extra_control = sorted(controlled_keys - high_b_keys)
    summary = b_control.get("summary", {})
    pass_ok = (
        not bad_records
        and not missing_high_b
        and not extra_control
        and as_int(summary.get("high_B_states_analyzed")) == len(chains)
        and as_int(summary.get("B_EVENTUALLY_CERTIFIED")) == len(chains)
        and as_int(summary.get("STILL_OPEN")) == 0
        and as_int(summary.get("B_GROWS")) == 0
        and as_int(summary.get("max_later_B")) <= B_LIMIT
    )
    return {
        "pass": pass_ok,
        "chain_count": len(chains),
        "summary": summary,
        "bad_records": bad_records[:50],
        "missing_high_B_keys": missing_high_b[:50],
        "extra_b_control_keys": extra_control[:50],
    }


def main() -> None:
    batch = load_json(QPARENT)
    frontier = load_json(FRONTIER_COVERAGE)
    return_map = load_json(RETURN_MAP)
    b_control = load_json(B_CONTROL)
    transition_audit = load_json(QTRANSITION_AUDIT, required=False) or {}
    exact_fallback = load_json(QEXACT_FALLBACK, required=False) or {}

    parent_audit = audit_parent_rows(batch)
    frontier_audit = audit_frontier_coverage(frontier)
    return_map_audit = audit_return_map(return_map)
    b_control_audit = audit_b_control(b_control, set(return_map_audit["high_B_keys"]))

    sampled_as_proof_count = (
        len(parent_audit["sampled_rows"])
        + (1 if batch.get("method", {}).get("random_seeds") else 0)
        + (1 if frontier.get("method", {}).get("random_seeds") else 0)
        + (1 if return_map.get("method", {}).get("random_seeds") else 0)
        + (1 if b_control.get("method", {}).get("random_seeds") else 0)
    )

    transition_table_exported = transition_audit.get("status") == "PASS_QUOTIENT_TRANSITION_TABLE"
    exact_state_fallback_exported = exact_fallback.get("status") == "PASS_EXACT_STATE_FALLBACK_FOR_TRACKED_KEYS"
    determinism_basis = (
        "Exported conflict counters are zero in parent rows, frontier coverage, and return-map reports. "
        "The tracked quotient transition table and exact-state fallback are exported for proof-critical keys. "
        "Full quotient equivalence classes still require an external lemma or exhaustive representative coverage."
        if transition_table_exported and exact_state_fallback_exported
        else (
            "Exported conflict counters are zero in parent rows, frontier coverage, and return-map reports. "
            "The full representative transition table is not exported, so this audit cannot independently replay "
            "every quotient merge."
        )
    )
    pass_exported = (
        parent_audit["pass"]
        and frontier_audit["pass"]
        and return_map_audit["pass"]
        and b_control_audit["pass"]
        and sampled_as_proof_count == 0
    )
    status = (
        "PASS_QUOTIENT_KEY_VALIDITY"
        if pass_exported
        else "FAIL_QUOTIENT_KEY_VALIDITY"
    )

    report = {
        "status": status,
        "plain_truth": (
            "This audits the exported quotient-key closure evidence. It does not claim the full proof is complete."
        ),
        "method": {
            "random_seeds": False,
            "integer_checks_only_for_proof_decisions": True,
            "B_limit": B_LIMIT,
            "expected_depth_gt_18_parents": EXPECTED_PARENTS,
            "transition_table_exported": transition_table_exported,
            "exact_state_fallback_exported": exact_state_fallback_exported,
            "determinism_basis": determinism_basis,
        },
        "sampled_as_proof_count": sampled_as_proof_count,
        "parent_batch_audit": parent_audit,
        "frontier_coverage_audit": frontier_audit,
        "return_map_audit": {
            key: value for key, value in return_map_audit.items() if key != "high_B_keys"
        },
        "b_control_audit": b_control_audit,
        "remaining_hardening_for_independent_replay": [
            "Prove compact quotient-key full equivalence classes, or export exhaustive representative coverage for them.",
            "Keep the tracked quotient transition table and exact-state fallback passing.",
            "Export full open-key lists per parent, not only samples, if independent parent-level replay is required.",
        ],
    }

    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("QUOTIENT KEY VALIDITY AUDIT")
    print(f"  Parent rows              : {parent_audit['row_count']} / {EXPECTED_PARENTS}")
    print(f"  Parent audit pass        : {parent_audit['pass']}")
    print(f"  Frontier coverage pass   : {frontier_audit['pass']}")
    print(f"  Return map pass          : {return_map_audit['pass']}")
    print(f"  B-control pass           : {b_control_audit['pass']}")
    print(f"  Sampled as proof count   : {sampled_as_proof_count}")
    print(f"  Transition table export  : {transition_table_exported}")
    print(f"  Exact fallback export    : {exact_state_fallback_exported}")
    print(f"  Status                   : {status}")
    print(f"  Report                   : {OUT}")


if __name__ == "__main__":
    main()
