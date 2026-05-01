#!/usr/bin/env python3
"""
coverage_source_diagnosis.py

Diagnose what coverage data is actually exported by the current certificate
artifacts.  This script does not run random seeds and does not make proof
completion claims.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


FILES = [
    Path("exact_depth_closure_report.json"),
    Path("quotient_parent_batch_report.json"),
    Path("direct_bridge_report.json"),
    Path("final_certificate_audit_report.json"),
    Path("residue_partition_exhaustiveness_report.json"),
    Path("residue_density_partition_audit_report.json"),
]
OUT = Path("coverage_source_diagnosis_report.json")

RESIDUE_KEYS = {"r", "residue", "r0"}
MODULUS_KEYS = {"k", "k_prime", "modulus_power", "depth"}
STATUS_KEYS = {"status", "classification", "final_status", "closed"}
SAMPLED_KEYS = {"sampled", "sampled_rows_used", "sampled_as_proof", "random_seeds", "random_seed"}
B_KEYS = {"B", "parent_B", "max_B", "B_LIMIT", "first_later_B", "max_later_B", "max_starting_B"}
FINITE_RANGE_KEYS = {"odd_min", "odd_max", "verify_limit", "range"}
CLOSED_LEAF_KEYS = {"closed_leaves", "leaves", "closed_leaf_rows"}
OPEN_PARENT_KEYS = {"parent_rows", "open_parents", "deep_parents", "blocked_or_partial_parent_ids"}


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_dicts(value: Any, path: str = "$"):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from iter_dicts(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_dicts(child, f"{path}[{index}]")


def has_any_key(value: Any, keys: set[str]) -> bool:
    return any(bool(set(obj) & keys) for _path, obj in iter_dicts(value))


def paths_with_keys(value: Any, keys: set[str], limit: int = 20) -> list[str]:
    out: list[str] = []
    for path, obj in iter_dicts(value):
        if set(obj) & keys:
            out.append(path)
            if len(out) >= limit:
                break
    return out


def list_at(value: Any, key: str) -> list[Any]:
    if isinstance(value, dict) and isinstance(value.get(key), list):
        return value[key]
    return []


def row_key_counts(rows: list[Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        if isinstance(row, dict):
            counts.update(row.keys())
    return dict(sorted(counts.items()))


def rows_with_residue_and_modulus(rows: list[Any]) -> int:
    count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        has_residue = any(key in row for key in RESIDUE_KEYS)
        has_modulus = any(key in row for key in MODULUS_KEYS)
        if has_residue and has_modulus:
            count += 1
    return count


def file_diagnosis(path: Path, data: Any) -> dict[str, Any]:
    if data is None:
        return {
            "present": False,
            "contains_actual_residue_class_data": False,
            "contains_only_summary_counts": False,
        }

    parent_rows = list_at(data, "parent_rows")
    lanes = list_at(data, "lanes")
    assignments = list_at(data, "all_assignments")
    closed_leaf_lists = [
        path_name
        for path_name, obj in iter_dicts(data)
        if any(key in obj and isinstance(obj[key], list) for key in CLOSED_LEAF_KEYS)
    ]
    summary_like = isinstance(data, dict) and (
        "summary" in data or "audits" in data or "final_status" in data
    )
    residue_lane_count = rows_with_residue_and_modulus(parent_rows) + rows_with_residue_and_modulus(lanes)
    assignment_residue_count = sum(
        1
        for row in assignments
        if isinstance(row, dict) and "r0" in row and "buckets" in row
    )

    finite_range = None
    if isinstance(data, dict):
        summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
        if any(key in summary for key in FINITE_RANGE_KEYS):
            finite_range = {
                "odd_min": summary.get("odd_min"),
                "odd_max": summary.get("odd_max"),
                "verify_limit": summary.get("verify_limit"),
                "range": summary.get("range"),
            }

    return {
        "present": True,
        "top_level_keys": sorted(data.keys()) if isinstance(data, dict) else [],
        "contains_residue_r": has_any_key(data, RESIDUE_KEYS),
        "contains_modulus_or_depth_k": has_any_key(data, MODULUS_KEYS),
        "contains_parent_r0": has_any_key(data, {"r0"}),
        "contains_lane_status": has_any_key(data, STATUS_KEYS),
        "contains_exact_or_sampled_flag": has_any_key(data, SAMPLED_KEYS),
        "contains_B_threshold_or_B_values": has_any_key(data, B_KEYS),
        "contains_direct_finite_range": finite_range is not None,
        "direct_finite_range": finite_range,
        "contains_list_of_closed_leaves": bool(closed_leaf_lists),
        "closed_leaf_list_paths": closed_leaf_lists[:20],
        "contains_list_of_open_or_deep_parents": bool(parent_rows)
        or has_any_key(data, OPEN_PARENT_KEYS),
        "parent_row_count": len(parent_rows),
        "lane_row_count": len(lanes),
        "assignment_row_count": len(assignments),
        "rows_with_residue_and_modulus_or_depth": residue_lane_count,
        "assignment_rows_with_r0": assignment_residue_count,
        "parent_row_keys": row_key_counts(parent_rows),
        "lane_row_keys": row_key_counts(lanes),
        "contains_actual_residue_class_data": residue_lane_count > 0 or assignment_residue_count > 0,
        "contains_only_summary_counts": summary_like and residue_lane_count == 0 and not assignments,
        "example_paths": {
            "residue": paths_with_keys(data, RESIDUE_KEYS, 5),
            "modulus_or_depth": paths_with_keys(data, MODULUS_KEYS, 5),
            "status": paths_with_keys(data, STATUS_KEYS, 5),
            "sampled_or_random": paths_with_keys(data, SAMPLED_KEYS, 5),
            "B": paths_with_keys(data, B_KEYS, 5),
        },
    }


def status_counts(data: Any) -> dict[str, int]:
    rows = list_at(data, "parent_rows")
    counts = Counter()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "status" in row:
            counts[str(row["status"])] += 1
        elif row.get("closed") is True:
            counts["CLOSED"] += 1
    return dict(sorted(counts.items()))


def main() -> None:
    loaded = {path: load_json(path) for path in FILES}
    files = {str(path): file_diagnosis(path, data) for path, data in loaded.items()}

    exact = loaded[Path("exact_depth_closure_report.json")]
    parent = loaded[Path("quotient_parent_batch_report.json")]
    direct = loaded[Path("direct_bridge_report.json")]
    density = loaded[Path("residue_density_partition_audit_report.json")]
    partition = loaded[Path("residue_partition_exhaustiveness_report.json")]

    exact_rows = list_at(exact, "parent_rows")
    pre_report_exact_rows = list_at(exact, "pre_report_exact_parent_rows")
    parent_rows = list_at(parent, "parent_rows")
    direct_summary = (direct or {}).get("summary", {}) if isinstance(direct, dict) else {}
    first_missing = (
        density.get("first_20_missing_residue_slots", [])
        if isinstance(density, dict)
        else []
    )
    partition_gap = (
        partition.get("source_data_gaps", {})
        if isinstance(partition, dict)
        else {}
    )

    answers = {
        "which_files_have_actual_residue_class_data": [
            path for path, diag in files.items()
            if diag.get("contains_actual_residue_class_data")
        ],
        "which_files_only_have_summary_counts": [
            path for path, diag in files.items()
            if diag.get("contains_only_summary_counts")
        ],
        "exact_depth_closure_report_contains": (
            f"{len(exact_rows)} depth 15-18 parent_rows with r0, k_prime/depth, closed flag, "
            f"sibling counts, and aggregate exact checks; {len(pre_report_exact_rows)} "
            "pre-report low-depth exact parent rows with r0, k_prime, depth, m, o, c, b, B, and sampled=false. "
            "It still does not export every sibling leaf as its own r,k lane; parent-cylinder rows are the frontier partition units."
            if exact_rows else "no parent_rows found"
        ),
        "quotient_parent_batch_report_contains": (
            f"{len(parent_rows)} parent rows; "
            f"{rows_with_residue_and_modulus(parent_rows)} rows have r0 plus k_prime/depth. "
            f"Status counts: {status_counts(parent)}"
        ),
        "direct_bridge_report_role": (
            "finite-case coverage"
            if direct_summary else "direct bridge report missing or lacks summary"
        ),
        "direct_bridge_report_is_residue_density_coverage": False,
        "why_small_residues_were_missing": (
            "The first density audit only treated the depth 15-18 exact rows and the 578 deep-parent rows "
            "as residue classes, so shallow r0 mod 2^16 residues such as 1,3,5,7 were not in its lane source. "
            "The corrected density audit now uses residue_partition_exhaustiveness_report.json as the complete "
            "frontier partition source, so those small residues are covered by shallow_valid_at_k16 lanes."
        ),
        "frontier_partition_gap_found": partition_gap,
        "data_required_for_valid_exact_partition_audit": [
            "An explicit universe definition: all odd integers, odd residues modulo 2^K, or r0 frontier modulo 2^16.",
            "Every residue-density lane exported with r, modulus_power k, status/classification, and sampled=false.",
            "Every closed exact-depth leaf exported individually if leaves, not parents, are the density lanes.",
            "Every closed symbolic/pre-parent leaf exported with r and k.",
            "Every deep parent exported with r0, k_prime/depth, modulus, status, and coverage source.",
            "A separate finite-case section for direct_bridge_report.json, unless finite cases are converted into explicit residue lanes.",
            "A disjointness rule stating whether finite direct bridge cases can overlap residue lanes or are only representative checks.",
        ],
    }

    fix_plan = {
        "if_exact_depth_leaves_are_missing": [
            "Modify exact_depth_closure.py to emit a closed_leaves array if leaf-level lanes are required.",
            "Each closed leaf should include r, k, status, m, o, c, b or b summary, B, and sampled=false.",
            "Keep parent_rows as summary data, but do not use them as leaf-level density lanes unless that is the intended partition.",
        ],
        "if_deep_parents_need_full_residue_data": [
            "Modify quotient_parent_batch_audit.py so every parent row includes r0, k_prime, depth, modulus='2^k_prime', status, coverage_source, and sampled=false.",
            "Keep quotient/local key closure details separate from residue identity fields.",
        ],
        "then_rebuild_density_audit": [
            "Load only complete residue-density lane rows.",
            "Use the smallest common K justified by those rows and the declared universe.",
            "Fail as INCOMPLETE_DENSITY_PARTITION if any closure source only has summaries or finite ranges.",
            "Report missing=0, overlap=0, sampled_as_proof=0 only for the declared universe.",
        ],
    }

    report = {
        "status": "DIAGNOSIS_COMPLETE",
        "plain_truth": (
            "This diagnoses exported coverage data only. It does not claim proof failure or proof completion."
        ),
        "files": files,
        "answers": answers,
        "fix_plan": fix_plan,
        "density_audit_observed_failure": {
            "status": density.get("status") if isinstance(density, dict) else None,
            "common_modulus_power": density.get("common_modulus_power") if isinstance(density, dict) else None,
            "missing_slots": density.get("missing_slots") if isinstance(density, dict) else None,
            "first_missing_residue_slots": first_missing,
        },
    }

    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("COVERAGE SOURCE DIAGNOSIS")
    print("  Actual residue class data:")
    for path in answers["which_files_have_actual_residue_class_data"]:
        print(f"    - {path}")
    print("  Summary-only files:")
    for path in answers["which_files_only_have_summary_counts"]:
        print(f"    - {path}")
    print(f"  Exact-depth export       : {answers['exact_depth_closure_report_contains']}")
    print(f"  Quotient parent export   : {answers['quotient_parent_batch_report_contains']}")
    print("  Direct bridge role       : finite-case coverage, not residue-density coverage")
    print(f"  Small missing slots      : {first_missing[:20]}")
    print(f"  Report                  : {OUT}")


if __name__ == "__main__":
    main()
