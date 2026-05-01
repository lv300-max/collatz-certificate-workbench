#!/usr/bin/env python3
"""
master_source_coverage_audit.py

Source/export coverage audit for the Collatz certificate workbench.

This script inspects existing source and report artifacts. It does not run
random seeds, raise caps, or claim a proof.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUT = Path("master_source_coverage_audit_report.json")

FILES = [
    "final_certificate_audit.py",
    "final_certificate_audit_report.json",
    "exact_depth_closure.py",
    "exact_depth_closure_report.json",
    "quotient_parent_batch_audit.py",
    "quotient_parent_batch_report.json",
    "frontier_coverage_audit.py",
    "frontier_coverage_audit_report.json",
    "frontier_return_map.py",
    "frontier_return_map_report.json",
    "b_control_test.py",
    "b_control_report.json",
    "excursion_quotient_analyzer.py",
    "excursion_quotient_report.json",
    "quotient_parent_coverage_audit.py",
    "quotient_parent_coverage_audit_report.json",
    "residue_partition_exhaustiveness.py",
    "residue_partition_exhaustiveness_report.json",
    "residue_density_partition_audit.py",
    "residue_density_partition_audit_report.json",
    "coverage_source_diagnosis.py",
    "coverage_source_diagnosis_report.json",
    "direct_bridge_report.json",
    "quotient_abstraction_validity.py",
    "quotient_abstraction_validity_report.json",
    "quotient_transition_table_export.py",
    "quotient_transition_table_report.json",
    "quotient_transition_table.json",
    "quotient_transition_table_audit.py",
    "quotient_transition_table_audit_report.json",
    "quotient_exact_state_fallback_audit.py",
    "quotient_exact_state_fallback_audit_report.json",
    "quotient_key_schema_review.py",
    "quotient_key_schema_review_report.json",
    "quotient_key_validity_audit.py",
    "quotient_key_validity_audit_report.json",
    "exact_arithmetic_audit.py",
    "exact_arithmetic_audit_report.json",
    "collatz_certificate_final/MANIFEST.json",
    "collatz_certificate_final/CERTIFICATE_FRAMEWORK_THEOREM.md",
    "collatz_certificate_final/FINAL_AUDIT_SUMMARY.md",
]

PROOF_CRITICAL = {
    "final_certificate_audit.py",
    "exact_depth_closure.py",
    "exact_depth_closure_report.json",
    "quotient_parent_batch_audit.py",
    "quotient_parent_batch_report.json",
    "frontier_coverage_audit.py",
    "frontier_coverage_audit_report.json",
    "frontier_return_map.py",
    "frontier_return_map_report.json",
    "b_control_test.py",
    "b_control_report.json",
    "residue_partition_exhaustiveness.py",
    "residue_partition_exhaustiveness_report.json",
    "residue_density_partition_audit.py",
    "residue_density_partition_audit_report.json",
    "direct_bridge_report.json",
    "quotient_abstraction_validity.py",
    "quotient_abstraction_validity_report.json",
    "quotient_transition_table_export.py",
    "quotient_transition_table_report.json",
    "quotient_transition_table.json",
    "quotient_transition_table_audit.py",
    "quotient_transition_table_audit_report.json",
    "quotient_exact_state_fallback_audit.py",
    "quotient_exact_state_fallback_audit_report.json",
    "quotient_key_schema_review.py",
    "quotient_key_schema_review_report.json",
    "exact_arithmetic_audit.py",
    "exact_arithmetic_audit_report.json",
}

ROW_KEYS = (
    "parent_rows",
    "pre_report_exact_parent_rows",
    "return_records",
    "high_B_chains",
    "all_assignments",
    "lanes",
    "parent_records",
    "open_frontier",
    "returned_frontier",
    "transition_rows",
    "open_key_rows",
    "terminal_key_rows",
    "rows",
)
FIELD_GROUPS = {
    "residue_r_or_r0": {"r", "residue", "r0", "lane16", "parent_k16_residue"},
    "modulus_or_depth_k": {"k", "k_prime", "depth", "modulus", "modulus_power", "coverage_modulus_power"},
    "bucket_or_status": {"bucket", "status", "classification", "final_status", "closed"},
    "sampled_flag": {"sampled", "sampled_as_proof", "sampled_rows_used", "random_seeds"},
    "exact_flag": {"exact", "integer_checks_only", "integer_checks_only_for_proof"},
    "local_key_data": {"local_key_examples", "local_keys_attempted", "local_keys_certified", "key"},
    "return_pair": {"return_pair", "pair"},
    "B_or_final_B": {"B", "final_B", "max_B", "max_final_B", "threshold_B", "B_LIMIT"},
    "conflict_status": {"conflicts", "conflict_count", "conflict_keys"},
    "missing_or_uncovered_keys": {"missing_keys", "uncovered_open_key_count", "sample_uncovered_open_keys"},
}


def load_json(path: Path) -> tuple[Any, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except json.JSONDecodeError as exc:
        return None, f"json_decode_error: {exc}"
    except OSError as exc:
        return None, f"os_error: {exc}"


def iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def contains_any(value: Any, keys: set[str]) -> bool:
    return any(bool(set(obj) & keys) for obj in iter_dicts(value))


def list_rows(data: Any) -> dict[str, int]:
    if not isinstance(data, dict):
        return {}
    rows = {}
    for key in ROW_KEYS:
        if isinstance(data.get(key), list):
            rows[key] = len(data[key])
    return rows


def report_profile(path_name: str) -> dict[str, Any]:
    path = Path(path_name)
    profile: dict[str, Any] = {
        "exists": path.exists(),
        "proof_critical": path_name in PROOF_CRITICAL,
        "kind": path.suffix.lstrip(".") or "file",
    }
    if not path.exists():
        profile["read_status"] = "missing"
        return profile

    if path.suffix == ".json":
        data, error = load_json(path)
        if error:
            profile["read_status"] = error
            return profile
        rows = list_rows(data)
        profile.update(
            {
                "read_status": "ok",
                "top_level_keys": sorted(data.keys()) if isinstance(data, dict) else [],
                "row_level_sections": rows,
                "has_row_level_data": bool(rows),
                "summary_counts_only": isinstance(data, dict)
                and not rows
                and any(key in data for key in ("summary", "final_status", "audits")),
                "proof_critical_fields": {
                    label: contains_any(data, keys)
                    for label, keys in FIELD_GROUPS.items()
                },
            }
        )
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = ""
        profile.update(
            {
                "read_status": "ok",
                "line_count": len(text.splitlines()),
                "has_random_seed_marker": "random" in text.lower() or "seed" in text.lower(),
                "has_exact_integer_formula_marker": "(b + gap - 1) // gap" in text
                or "ceil_div" in text
                or "(1 << c) - a" in text,
            }
        )
    return profile


def main() -> None:
    profiles = {name: report_profile(name) for name in FILES}
    files_found = [name for name, p in profiles.items() if p["exists"]]
    files_missing = [name for name, p in profiles.items() if not p["exists"]]
    proof_critical_files_missing = [
        name for name in files_missing if name in PROOF_CRITICAL
    ]
    json_errors = [
        {"path": name, "read_status": p.get("read_status")}
        for name, p in profiles.items()
        if p["exists"] and str(p.get("read_status", "")).startswith("json_decode_error")
    ]
    files_with_only_summary = [
        name for name, p in profiles.items() if p.get("summary_counts_only")
    ]
    files_with_row_level_data = [
        name for name, p in profiles.items() if p.get("has_row_level_data")
    ]

    proof_critical_without_rows_or_regen: list[dict[str, str]] = []
    exact_regen_scripts = {
        "direct_bridge_report.json": "final_certificate_audit.py/collatz_certificate.json direct bridge verifier",
        "frontier_coverage_audit_report.json": "frontier_coverage_audit.py",
        "final_certificate_audit_report.json": "final_certificate_audit.py",
        "exact_arithmetic_audit_report.json": "exact_arithmetic_audit.py",
        "quotient_abstraction_validity_report.json": "quotient_abstraction_validity.py",
        "quotient_transition_table_audit_report.json": "quotient_transition_table_audit.py",
        "quotient_exact_state_fallback_audit_report.json": "quotient_exact_state_fallback_audit.py",
        "quotient_key_schema_review_report.json": "quotient_key_schema_review.py",
    }
    for name in PROOF_CRITICAL:
        p = profiles.get(name, {})
        if not name.endswith(".json") or not p.get("exists"):
            continue
        if p.get("has_row_level_data") or name in exact_regen_scripts:
            continue
        proof_critical_without_rows_or_regen.append(
            {
                "path": name,
                "reason": "proof-critical JSON has no row-level section and no explicit exact regeneration path in this audit",
            }
        )

    if proof_critical_files_missing or json_errors:
        status = "INCOMPLETE"
    elif proof_critical_without_rows_or_regen:
        status = "INCOMPLETE"
    else:
        status = "PASS"

    report = {
        "status": status,
        "source_export_status": status,
        "plain_truth": (
            "This is an export/source coverage audit. It does not claim the Collatz theorem is proven."
        ),
        "files_found": files_found,
        "files_missing": files_missing,
        "proof_critical_files_missing": proof_critical_files_missing,
        "json_errors": json_errors,
        "files_with_only_summary": files_with_only_summary,
        "files_with_row_level_data": files_with_row_level_data,
        "proof_critical_without_rows_or_regeneration_path": proof_critical_without_rows_or_regen,
        "exact_regeneration_paths": exact_regen_scripts,
        "files": profiles,
    }
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("MASTER SOURCE COVERAGE AUDIT")
    print(f"  Source export status       : {status}")
    print(f"  Files found                : {len(files_found)}")
    print(f"  Files missing              : {len(files_missing)}")
    print(f"  Proof-critical missing     : {len(proof_critical_files_missing)}")
    print(f"  Summary-only files         : {len(files_with_only_summary)}")
    print(f"  Row-level data files       : {len(files_with_row_level_data)}")
    print(f"  Report                     : {OUT}")


if __name__ == "__main__":
    main()
