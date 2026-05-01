#!/usr/bin/env python3
"""
full_framework_closure_audit.py

Framework-level coverage audit for the exact-state closure pipeline.

This script does not run random seeds, raise caps, or use sampled evidence.
It does not claim Collatz is proven. It checks whether the declared odd
r0 mod 2^16 frontier, exact-depth layer, 578 deep parents, cap-stopped rows,
local keys, return-map states, and high-B returns are covered by exact source
reports or full exact-state certificates, and it identifies any remaining
compact-quotient-only dependence.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


OUT = Path("full_framework_closure_audit_report.json")
B_LIMIT = 200_001
FINAL_PASS_WORDING = (
    "The declared r0 mod 2^16 frontier, exact-depth layer, 578 deep parents, "
    "cap-stopped rows, local keys, return-map states, high-B returns, and previously "
    "quotient-closed parents are now all covered by exact source reports or full "
    "exact-state certificates. No proof-critical row relies only on compact quotient "
    "abstraction. Independent mathematical review is still required before any public "
    "proof claim."
)
EXPECTED_BUCKETS = {
    "shallow_valid_at_k16": 30_654,
    "pre_report_exact_depth_parent": 1_338,
    "exact_depth_closed_parent": 198,
    "deep_parent": 578,
}
REQUIRED_INPUTS = [
    "residue_partition_exhaustiveness_report.json",
    "residue_density_partition_audit_report.json",
    "exact_depth_closure_report.json",
    "direct_bridge_report.json",
    "quotient_parent_batch_report.json",
    "frontier_coverage_audit_report.json",
    "frontier_return_map_report.json",
    "b_control_report.json",
    "quotient_transition_table.json",
    "quotient_transition_table_audit_report.json",
    "exact_state_closure_report.json",
    "final_certificate_audit_report.json",
]


def load_json(path: str) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def key_id(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=False)


def status(pass_ok: bool, fail: bool = False, incomplete: bool = False) -> str:
    if fail:
        return "FAIL"
    if incomplete:
        return "INCOMPLETE"
    return "PASS" if pass_ok else "FAIL"


def check_frontier_universe(residue: dict[str, Any], density: dict[str, Any]) -> dict[str, Any]:
    failures = []
    bucket_counts = residue.get("bucket_counts", {})
    if residue.get("universe_type") != "odd base residues r0 modulo 2^16":
        failures.append("universe_type mismatch")
    if residue.get("total_odd_base_residues") != 32768:
        failures.append("total_odd_base_residues != 32768")
    if residue.get("assigned_once") != 32768:
        failures.append("assigned_once != 32768")
    if residue.get("missing") != 0:
        failures.append("missing != 0")
    if residue.get("duplicates") != 0:
        failures.append("duplicates != 0")
    if residue.get("sampled_as_proof_count") != 0:
        failures.append("sampled_as_proof_count != 0")
    if bucket_counts != EXPECTED_BUCKETS:
        failures.append("bucket split mismatch")
    if sum(int(v) for v in bucket_counts.values()) != 32768:
        failures.append("bucket total != 32768")
    if density.get("covered_slots") != 32768:
        failures.append("density covered_slots != 32768")
    if density.get("missing_slots") != 0:
        failures.append("density missing_slots != 0")
    if density.get("duplicate_overlap_slots") != 0:
        failures.append("density duplicate_overlap_slots != 0")
    if density.get("sampled_as_proof_count") != 0:
        failures.append("density sampled_as_proof_count != 0")

    return {
        "status": "PASS" if not failures else "FAIL_FRONTIER_UNIVERSE",
        "universe": residue.get("universe_type"),
        "total_odd_r0": residue.get("total_odd_base_residues"),
        "bucket_total": sum(int(v) for v in bucket_counts.values()) if isinstance(bucket_counts, dict) else None,
        "bucket_counts": bucket_counts,
        "missing": residue.get("missing"),
        "duplicates": residue.get("duplicates"),
        "sampled_as_proof_count": residue.get("sampled_as_proof_count"),
        "density_summary": {
            "covered_slots": density.get("covered_slots"),
            "missing_slots": density.get("missing_slots"),
            "duplicate_overlap_slots": density.get("duplicate_overlap_slots"),
            "sampled_as_proof_count": density.get("sampled_as_proof_count"),
        },
        "failures": failures,
    }


def exact_state_key_set(exact_state: dict[str, Any]) -> set[str]:
    return {key_id(row.get("key")) for row in exact_state.get("results", []) if row.get("key") is not None}


def exact_state_parent_witness_ids(exact_state: dict[str, Any]) -> set[str]:
    return {
        str(row.get("parent_witness_id"))
        for row in exact_state.get("results", [])
        if row.get("source_kind") == "closed_by_quotient_parent_witness"
        and row.get("parent_witness_id") is not None
        and row.get("classification") in {"CERTIFIED_RETURN", "HIGH_B_THEN_CERTIFIED"}
        and row.get("final_B") is not None
        and int(row["final_B"]) <= B_LIMIT
    }


def local_item_has_exact_state(item: dict[str, Any]) -> bool:
    exact_state = item.get("exact_state")
    if not isinstance(exact_state, dict):
        return False
    required = ("residue", "modulus_power", "o", "c", "b", "gap")
    if any(exact_state.get(field) is None for field in required):
        return False
    if item.get("sampled") is True or item.get("exact") is not True:
        return False
    if item.get("classification") not in {"CERTIFIED_RETURN", "HIGH_B_RETURN_THEN_CERTIFIED"}:
        return False
    final_b = item.get("final_B", item.get("B"))
    return final_b is not None and int(final_b) <= B_LIMIT


def parent_witness_has_exact_state(item: dict[str, Any]) -> bool:
    exact_state = item.get("exact_state")
    if not isinstance(exact_state, dict):
        return False
    required = ("residue", "modulus_power", "o", "c", "b", "gap")
    if any(exact_state.get(field) is None for field in required):
        return False
    if item.get("coverage_source") != "FULL_EXACT_STATE_CERTIFICATE":
        return False
    if item.get("sampled") is True or item.get("exact") is not True:
        return False
    if item.get("classification") not in {"CERTIFIED_RETURN", "HIGH_B_RETURN_THEN_CERTIFIED"}:
        return False
    if item.get("witness_id") is None:
        return False
    final_b = item.get("final_B", item.get("B"))
    return final_b is not None and int(final_b) <= B_LIMIT


def check_deep_parents(parent_report: dict[str, Any], exact_state: dict[str, Any]) -> dict[str, Any]:
    rows = parent_report.get("parent_rows", [])
    exact_keys = exact_state_key_set(exact_state)
    parent_witness_ids = exact_state_parent_witness_ids(exact_state)
    missing = []
    uncovered = []
    sampled = []
    compact_only = []
    not_closed = []
    closed = 0
    status_counts = Counter()

    for row in rows:
        status_counts[row.get("status")] += 1
        row_id = {
            "r0": row.get("r0"),
            "k_prime": row.get("k_prime"),
            "depth": row.get("depth"),
            "status": row.get("status"),
        }
        if row.get("r0") is None or row.get("k_prime") is None or row.get("depth") is None or row.get("modulus") is None:
            missing.append({**row_id, "reason": "missing parent residue/depth/modulus data"})
            continue
        if row.get("sampled") is True:
            sampled.append(row_id)
        if row.get("exact") is not True:
            missing.append({**row_id, "reason": "row is not marked exact"})
            continue
        if row.get("conflict_count", 0):
            not_closed.append({**row_id, "reason": "conflict_count nonzero"})
            continue

        row_status = row.get("status")
        row_closed = False
        if row_status == "CLOSED_BY_QUOTIENT":
            quotient_closed = (
                row.get("open_key_count") == 0
                and row.get("uncovered_open_key_count") == 0
                and row.get("local_keys_still_open") == 0
                and not row.get("cap_or_truncation_reasons")
            )
            witnesses = row.get("exact_closure_witnesses", [])
            witness_ids = {str(item.get("witness_id")) for item in witnesses if item.get("witness_id") is not None}
            witness_ok = (
                bool(witnesses)
                and len(witnesses) == int(row.get("entry_count", -1))
                and len(witnesses) == int(row.get("return_keys", -1))
                and row.get("closed_by_quotient_full_state_export_complete") is True
                and row.get("coverage_source") == "FULL_EXACT_STATE_CERTIFICATE"
                and all(parent_witness_has_exact_state(item) for item in witnesses)
                and witness_ids.issubset(parent_witness_ids)
            )
            row_closed = quotient_closed and witness_ok
            if quotient_closed and not witness_ok:
                compact_only.append({
                    **row_id,
                    "reason": "closed internally by compact quotient exploration; exported full-state certificates missing or not certified",
                    "witness_count": len(witnesses),
                    "entry_count": row.get("entry_count"),
                    "return_keys": row.get("return_keys"),
                    "missing_from_exact_state_closure": sorted(witness_ids - parent_witness_ids)[:10],
                })
        elif row_status == "COVERED_BUT_CAP_REACHED":
            row_closed = (
                row.get("open_key_count") == row.get("covered_open_key_count")
                and row.get("uncovered_open_key_count") == 0
                and row.get("open_keys_all_exported_in_parent_run") is True
                and row.get("local_keys_still_open") == 0
            )
        elif row_status == "CLOSED_WITH_LOCAL_KEYS":
            local_examples = row.get("local_key_examples", [])
            local_ok = bool(local_examples) and all(local_item_has_exact_state(item) for item in local_examples)
            local_keys_in_exact_state = all(key_id(item.get("key")) in exact_keys for item in local_examples)
            row_closed = (
                row.get("local_keys_still_open") == 0
                and row.get("local_keys_attempted") == row.get("local_keys_certified", 0) + row.get("local_keys_high_b_certified", 0)
                and local_ok
                and local_keys_in_exact_state
            )
        else:
            row_closed = False

        if not row_closed:
            not_closed.append({**row_id, "reason": "row lacks accepted exact closure evidence"})
        else:
            closed += 1

        if row_status != "CLOSED_WITH_LOCAL_KEYS" and row.get("uncovered_open_key_count", 0):
            uncovered.append({**row_id, "uncovered_open_key_count": row.get("uncovered_open_key_count")})

    parents_checked = len(rows)
    hard_ok = (
        parents_checked == 578
        and closed == 578
        and not missing
        and not uncovered
        and not sampled
        and not not_closed
    )
    compact_dependency = len(compact_only)
    check_status = (
        "PASS"
        if hard_ok and compact_dependency == 0
        else ("PASS_WITH_QUOTIENT_DEPENDENCE" if hard_ok and compact_dependency else "FAIL_DEEP_PARENT_COMPLETENESS")
    )
    return {
        "status": check_status,
        "parents_checked": parents_checked,
        "parents_closed": closed,
        "parents_missing": len(missing),
        "parents_with_uncovered_keys": len(uncovered),
        "parents_relying_only_on_compact_quotient": compact_dependency,
        "parents_relying_on_sampled_rows": len(sampled),
        "status_counts": dict(status_counts),
        "missing_examples": missing[:30],
        "uncovered_examples": uncovered[:30],
        "not_closed_examples": not_closed[:30],
        "compact_quotient_only_examples": compact_only[:30],
        "sampled_examples": sampled[:30],
    }


def check_exact_state_coverage(exact_state: dict[str, Any], qtable: dict[str, Any]) -> dict[str, Any]:
    rows = exact_state.get("results", [])
    missing_fields = []
    final_b_over = []
    allowed = {"CERTIFIED_RETURN", "HIGH_B_THEN_CERTIFIED"}
    for row in rows:
        missing = [
            field
            for field in ("residue", "level", "modulus", "o", "c", "b", "initial_gap", "final_B")
            if row.get(field) is None
        ]
        if row.get("classification") not in allowed:
            missing.append("certified classification")
        if row.get("final_B") is not None and int(row["final_B"]) > B_LIMIT:
            final_b_over.append({"key": row.get("key"), "final_B": row.get("final_B")})
        if missing:
            missing_fields.append({"key": row.get("key"), "missing_or_bad": missing})

    qrows = qtable.get("rows", [])
    q_missing_exact = []
    for row in qrows:
        if "local continuation" not in row.get("transition_types", []):
            continue
        exact_rep = False
        for rep in row.get("representatives", []):
            affine = rep.get("affine_state") or {}
            if all(affine.get(field) is not None for field in ("residue", "level", "o", "c", "b", "gap")):
                exact_rep = True
                break
        if not exact_rep:
            q_missing_exact.append(row.get("key"))

    pass_ok = (
        exact_state.get("status") == "PASS_EXACT_STATE_CLOSURE"
        and exact_state.get("total_states") == exact_state.get("certified_states", 0) + exact_state.get("high_B_then_certified", 0)
        and exact_state.get("missing_exact_state_fields") == 0
        and exact_state.get("still_open") == 0
        and exact_state.get("conflicts") == 0
        and exact_state.get("final_B_over_200001") == 0
        and int(exact_state.get("max_final_B", 0)) <= B_LIMIT
        and not missing_fields
        and not final_b_over
        and not q_missing_exact
    )
    return {
        "status": "PASS" if pass_ok else "FAIL_EXACT_STATE_COVERAGE",
        "exact_states_checked": len(rows),
        "certified_states": exact_state.get("certified_states"),
        "high_B_then_certified": exact_state.get("high_B_then_certified"),
        "missing_exact_state_fields": exact_state.get("missing_exact_state_fields"),
        "still_open": exact_state.get("still_open"),
        "conflicts": exact_state.get("conflicts"),
        "final_B_over_200001": exact_state.get("final_B_over_200001"),
        "max_final_B": exact_state.get("max_final_B"),
        "rows_missing_required_fields": len(missing_fields),
        "transition_rows_missing_exact_representative": len(q_missing_exact),
        "missing_field_examples": missing_fields[:30],
        "transition_missing_examples": q_missing_exact[:30],
    }


def check_no_quotient_dependence(parent_check: dict[str, Any], direct: dict[str, Any], exact_depth: dict[str, Any], exact_state: dict[str, Any]) -> dict[str, Any]:
    exact_summary = exact_depth.get("summary", {})
    direct_summary = direct.get("summary", {})
    exact_depth_rows = int(exact_summary.get("exact_parents_closed", 0)) + int(exact_summary.get("pre_report_exact_depth_parent_count", 0) or 0)
    if not exact_summary.get("pre_report_exact_depth_parent_count"):
        exact_depth_rows = 198 + 1338 if exact_summary.get("exact_parents_closed") == 198 else exact_depth_rows
    compact = int(parent_check.get("parents_relying_only_on_compact_quotient", 0))
    return {
        "status": "PASS" if compact == 0 else "INCOMPLETE_QUOTIENT_DEPENDENCE",
        "full_exact_state_rows": exact_state.get("total_states"),
        "direct_bridge_rows": direct_summary.get("checked"),
        "exact_depth_rows": exact_depth_rows,
        "compact_quotient_only_rows": compact,
        "compact_quotient_only_examples": parent_check.get("compact_quotient_only_examples", []),
    }


def check_cap_stopped_rows(parent_report: dict[str, Any], frontier_cov: dict[str, Any], exact_state: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in parent_report.get("parent_rows", []) if row.get("status") == "COVERED_BUT_CAP_REACHED"]
    checks = frontier_cov.get("checks", {})
    global_exact_ok = (
        frontier_cov.get("summary", {}).get("pass") is True
        and checks.get("every_open_key_exported") is True
        and checks.get("every_open_key_return_mapped") is True
        and checks.get("every_high_B_key_B_controlled") is True
        and checks.get("every_high_B_eventually_certified") is True
        and checks.get("no_still_debt_keys") is True
        and checks.get("no_conflicts") is True
        and checks.get("no_final_B_over_200001") is True
        and exact_state.get("status") == "PASS_EXACT_STATE_CLOSURE"
    )
    bad = []
    for row in rows:
        row_ok = (
            row.get("sampled") is False
            and row.get("exact") is True
            and row.get("open_keys_all_exported_in_parent_run") is True
            and row.get("uncovered_open_key_count") == 0
            and row.get("open_key_count") == row.get("covered_open_key_count")
            and row.get("conflict_count") == 0
            and row.get("local_keys_still_open") == 0
            and global_exact_ok
        )
        if not row_ok:
            bad.append({
                "r0": row.get("r0"),
                "status": row.get("status"),
                "open_key_count": row.get("open_key_count"),
                "covered_open_key_count": row.get("covered_open_key_count"),
                "uncovered_open_key_count": row.get("uncovered_open_key_count"),
            })
    return {
        "status": "PASS" if len(rows) == 286 and not bad else "FAIL_CAP_STOPPED_ROWS",
        "cap_stopped_rows_checked": len(rows),
        "cap_stopped_rows_with_exact_coverage": len(rows) - len(bad),
        "bad_count": len(bad),
        "global_frontier_exact_coverage": global_exact_ok,
        "bad_examples": bad[:30],
    }


def check_local_keys(parent_report: dict[str, Any], exact_state: dict[str, Any]) -> dict[str, Any]:
    exact_keys = exact_state_key_set(exact_state)
    items = [item for row in parent_report.get("parent_rows", []) for item in row.get("local_key_examples", [])]
    bad = []
    for item in items:
        final_b = item.get("final_B", item.get("B"))
        ok = (
            local_item_has_exact_state(item)
            and key_id(item.get("key")) in exact_keys
            and final_b is not None
            and int(final_b) <= B_LIMIT
        )
        if not ok:
            bad.append({"key": item.get("key"), "classification": item.get("classification"), "final_B": final_b})
    return {
        "status": "PASS" if len(items) == 64 and not bad else "FAIL_LOCAL_KEYS",
        "local_keys_checked": len(items),
        "local_keys_exact_state_certified": len(items) - len(bad),
        "bad_count": len(bad),
        "bad_examples": bad[:30],
    }


def check_bridge_compatibility(direct: dict[str, Any], exact_depth: dict[str, Any], exact_state: dict[str, Any], frontier_cov: dict[str, Any]) -> dict[str, Any]:
    direct_summary = direct.get("summary", {})
    exact_summary = exact_depth.get("summary", {})
    max_values = [
        int(exact_state.get("max_final_B", 0) or 0),
        int(frontier_cov.get("summary", {}).get("max_final_B", 0) or 0),
        int(exact_summary.get("max_B", 0) or 0),
    ]
    failures = []
    if direct_summary.get("final_status") != "PASS_DIRECT_BRIDGE":
        failures.append("direct bridge status is not PASS_DIRECT_BRIDGE")
    if direct_summary.get("odd_min") != 3 or direct_summary.get("odd_max") != B_LIMIT or direct_summary.get("verify_limit") != B_LIMIT:
        failures.append("direct bridge range mismatch")
    if direct_summary.get("checked") != 100000:
        failures.append("direct bridge checked count mismatch")
    if direct_summary.get("failure_count") != 0 or direct_summary.get("meta_direct_failures") != 0:
        failures.append("direct bridge failures nonzero")
    if max(max_values) > B_LIMIT:
        failures.append("some final B exceeds bridge limit")
    return {
        "status": "PASS" if not failures else "FAIL_BRIDGE_COMPATIBILITY",
        "direct_bridge_checked": direct_summary.get("checked"),
        "direct_bridge_range": [direct_summary.get("odd_min"), direct_summary.get("odd_max")],
        "direct_bridge_failures": direct_summary.get("failure_count"),
        "max_final_B_all_layers": max(max_values),
        "failures": failures,
    }


def final_status(checks: dict[str, dict[str, Any]], missing_inputs: list[str]) -> str:
    if missing_inputs:
        return "INCOMPLETE_FULL_FRAMEWORK_CLOSURE"
    hard_fail = any(
        str(check.get("status", "")).startswith("FAIL")
        for name, check in checks.items()
        if name != "no_quotient_proof_dependence"
    )
    if hard_fail:
        return "FAIL_FULL_FRAMEWORK_CLOSURE"
    compact = checks["no_quotient_proof_dependence"].get("compact_quotient_only_rows", 0)
    if compact:
        return "PASS_PIPELINE_BUT_QUOTIENT_DEPENDENCE_REMAINS"
    if all(check.get("status") == "PASS" for check in checks.values()):
        return "PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE"
    return "INCOMPLETE_FULL_FRAMEWORK_CLOSURE"


def main() -> None:
    reports = {path: load_json(path) for path in REQUIRED_INPUTS}
    missing_inputs = [path for path, data in reports.items() if not isinstance(data, dict)]
    if missing_inputs:
        report = {
            "status": "INCOMPLETE_FULL_FRAMEWORK_CLOSURE",
            "missing_inputs": missing_inputs,
            "plain_truth": "Required source data is missing. No proof claim is made.",
        }
        write_json(OUT, report)
        print("FULL FRAMEWORK CLOSURE AUDIT")
        print("  Status: INCOMPLETE_FULL_FRAMEWORK_CLOSURE")
        print(f"  Missing inputs: {missing_inputs}")
        return

    residue = reports["residue_partition_exhaustiveness_report.json"]
    density = reports["residue_density_partition_audit_report.json"]
    exact_depth = reports["exact_depth_closure_report.json"]
    direct = reports["direct_bridge_report.json"]
    parent = reports["quotient_parent_batch_report.json"]
    frontier_cov = reports["frontier_coverage_audit_report.json"]
    qtable = reports["quotient_transition_table.json"]
    qtable_audit = reports["quotient_transition_table_audit_report.json"]
    exact_state = reports["exact_state_closure_report.json"]

    checks = {
        "frontier_universe": check_frontier_universe(residue, density),
        "deep_parent_completeness": check_deep_parents(parent, exact_state),
        "exact_state_coverage": check_exact_state_coverage(exact_state, qtable),
        "cap_stopped_rows": check_cap_stopped_rows(parent, frontier_cov, exact_state),
        "local_keys": check_local_keys(parent, exact_state),
        "bridge_compatibility": check_bridge_compatibility(direct, exact_depth, exact_state, frontier_cov),
    }
    checks["no_quotient_proof_dependence"] = check_no_quotient_dependence(
        checks["deep_parent_completeness"], direct, exact_depth, exact_state
    )

    qtable_ok = (
        qtable_audit.get("status") == "PASS_QUOTIENT_TRANSITION_TABLE"
        and qtable_audit.get("sampled_as_proof_count") == 0
        and qtable_audit.get("conflicts") == 0
        and qtable_audit.get("still_open") == 0
        and qtable_audit.get("final_B_over_200001") == 0
    )
    status_value = final_status(checks, missing_inputs)
    if status_value == "PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE" and not qtable_ok:
        status_value = "FAIL_FULL_FRAMEWORK_CLOSURE"

    pass_fail_table = {name: check.get("status") for name, check in checks.items()}
    report = {
        "status": status_value,
        "plain_truth": (
            "This framework audit checks generated exact reports and compact-quotient dependence. "
            "It does not claim Collatz is proven."
        ),
        "method": {
            "random_seeds": False,
            "caps_raised": False,
            "sampled_evidence_used_as_proof": False,
            "compact_quotient_keys_used_as_proof": False,
            "B_limit": B_LIMIT,
            "inputs": REQUIRED_INPUTS,
        },
        "checks": checks,
        "pass_fail_table": pass_fail_table,
        "compact_quotient_only_rows": checks["no_quotient_proof_dependence"].get("compact_quotient_only_rows"),
        "parents_checked": checks["deep_parent_completeness"].get("parents_checked"),
        "parents_closed": checks["deep_parent_completeness"].get("parents_closed"),
        "exact_states_checked": checks["exact_state_coverage"].get("exact_states_checked"),
        "qtable_audit_ok": qtable_ok,
        "final_message": (
            f"PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE: {FINAL_PASS_WORDING}"
            if status_value == "PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE"
            else (
                "PASS_PIPELINE_BUT_QUOTIENT_DEPENDENCE_REMAINS: all non-quotient framework checks passed, but some parent "
                "rows are still justified only by compact quotient exploration rather than exported full-state certificates."
                if status_value == "PASS_PIPELINE_BUT_QUOTIENT_DEPENDENCE_REMAINS"
                else status_value
            )
        ),
        "collatz_proven": False,
    }
    write_json(OUT, report)

    print("FULL FRAMEWORK CLOSURE AUDIT")
    print(f"  Status                     : {status_value}")
    print(f"  Compact quotient-only rows : {report['compact_quotient_only_rows']}")
    print(f"  Parents checked/closed     : {report['parents_checked']} / {report['parents_closed']}")
    print(f"  Exact states checked       : {report['exact_states_checked']}")
    print(f"  Report                     : {OUT}")


if __name__ == "__main__":
    main()
