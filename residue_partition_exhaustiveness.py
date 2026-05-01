#!/usr/bin/env python3
"""
residue_partition_exhaustiveness.py

Exact bookkeeping audit for the frontier split over odd residues r0 mod 2^16.

This does not run random seeds and does not claim the proof is complete.  It
checks whether every odd base residue is assigned by the available framework
data to exactly one residue-frontier bucket:

  - shallow/base valid at k=16, recomputed by integer descent
  - pre-report exact-depth parent with depth <15, exported by exact_depth_closure_report.json
  - exact-depth closed parent from exact_depth_closure_report.json
  - depth >18 parent from quotient_parent_batch_report.json

The direct bridge finite range is recorded as an annotation only.  It is finite
numeric coverage, not a residue-density lane.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import exact_depth_closure as edc


KMAX = 16
EXACT_REPORT = Path("exact_depth_closure_report.json")
PARENT_REPORT = Path("quotient_parent_batch_report.json")
DIRECT_BRIDGE_REPORT = Path("direct_bridge_report.json")
OUT = Path("residue_partition_exhaustiveness_report.json")


def load_json(path: Path, required: bool = False) -> Any:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 10)
        except ValueError:
            return None
    return None


def report_r0_map(
    report: dict[str, Any] | None,
    source: str,
    rows_key: str = "parent_rows",
) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    rows_by_r0: dict[int, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    if not report:
        return rows_by_r0, duplicates
    for index, row in enumerate(report.get(rows_key, [])):
        r0 = as_int(row.get("r0"))
        if r0 is None:
            continue
        record = {
            "source": source,
            "rows_key": rows_key,
            "row_index": index,
            "r0": r0,
            "k_prime": row.get("k_prime"),
            "depth": row.get("depth"),
            "status": row.get("status", "CLOSED" if row.get("closed") is True else "UNKNOWN"),
            "m": row.get("m"),
            "o": row.get("o"),
            "c": row.get("c"),
            "b": row.get("b"),
            "B": row.get("B", row.get("max_B")),
        }
        if r0 in rows_by_r0:
            duplicates.append({"r0": r0, "first": rows_by_r0[r0], "second": record})
        rows_by_r0[r0] = record
    return rows_by_r0, duplicates


def direct_bridge_info(report: dict[str, Any] | None, r0: int) -> dict[str, Any]:
    summary = (report or {}).get("summary", {})
    odd_min = as_int(summary.get("odd_min"))
    odd_max = as_int(summary.get("odd_max"))
    if odd_min is None or odd_max is None:
        return {"finite_representative_covered": False, "reason": "direct_bridge_range_missing"}
    return {
        "finite_representative_covered": odd_min <= r0 <= odd_max and r0 % 2 == 1,
        "range": [odd_min, odd_max],
        "note": "finite representative coverage only; not a residue-density lane",
    }


def classify_r0(
    r0: int,
    pre_report_rows: dict[int, dict[str, Any]],
    exact_rows: dict[int, dict[str, Any]],
    deep_rows: dict[int, dict[str, Any]],
    direct_report: dict[str, Any] | None,
) -> dict[str, Any]:
    buckets: list[dict[str, Any]] = []
    res0 = edc.compute_descent(r0, KMAX)
    if res0 is not None and res0[5]:
        steps, _a, _b, c, B, _valid, o = res0
        buckets.append(
            {
                "bucket": "shallow_valid_at_k16",
                "r0": r0,
                "modulus_power": KMAX,
                "status": "CLOSED_BY_BASE_DESCENT",
                "m": steps,
                "o": o,
                "c": c,
                "B": B,
                "sampled": False,
            }
        )
    if r0 in exact_rows:
        buckets.append({"bucket": "exact_depth_closed_parent", **exact_rows[r0], "sampled": False})
    if r0 in deep_rows:
        buckets.append({"bucket": "deep_parent", **deep_rows[r0], "sampled": False})
    if r0 in pre_report_rows:
        buckets.append({"bucket": "pre_report_exact_depth_parent", **pre_report_rows[r0], "sampled": False})
    if not buckets:
        k_valid, valid_res = edc.find_valid_k(r0, k_min=KMAX)
        if k_valid is not None and valid_res is not None:
            depth = k_valid - KMAX
            if depth < 15:
                steps, _a, _b, c, B, _valid, o = valid_res
                buckets.append(
                    {
                        "bucket": "pre_report_exact_depth_parent_recomputed",
                        "source": "recomputed_by_residue_partition_exhaustiveness.py",
                        "source_data_gap": (
                            "not exported by exact_depth_closure_report.json; that report starts at depth 15"
                        ),
                        "r0": r0,
                        "k_prime": k_valid,
                        "depth": depth,
                        "status": "CLOSED_BY_EXACT_RECOMPUTED_VALID_K",
                        "m": steps,
                        "o": o,
                        "c": c,
                        "B": B,
                        "sampled": False,
                    }
                )

    if len(buckets) == 1:
        assignment_status = "ASSIGNED_ONCE"
    elif len(buckets) == 0:
        assignment_status = "MISSING"
    else:
        assignment_status = "DUPLICATE"

    return {
        "r0": r0,
        "assignment_status": assignment_status,
        "bucket_count": len(buckets),
        "buckets": buckets,
        "direct_bridge_annotation": direct_bridge_info(direct_report, r0),
    }


def main() -> None:
    exact_report = load_json(EXACT_REPORT)
    parent_report = load_json(PARENT_REPORT)
    direct_report = load_json(DIRECT_BRIDGE_REPORT)
    exact_rows, exact_internal_duplicates = report_r0_map(exact_report, str(EXACT_REPORT))
    pre_report_rows, pre_report_internal_duplicates = report_r0_map(
        exact_report,
        str(EXACT_REPORT),
        rows_key="pre_report_exact_parent_rows",
    )
    deep_rows, deep_internal_duplicates = report_r0_map(parent_report, str(PARENT_REPORT))

    records = [
        classify_r0(r0, pre_report_rows, exact_rows, deep_rows, direct_report)
        for r0 in range(1, 1 << KMAX, 2)
    ]
    counts = Counter(record["assignment_status"] for record in records)
    bucket_counts = Counter(
        bucket["bucket"]
        for record in records
        for bucket in record["buckets"]
    )
    sampled_as_proof_count = sum(
        1
        for record in records
        for bucket in record["buckets"]
        if bucket.get("sampled")
    )
    direct_finite_count = sum(
        1
        for record in records
        if record["direct_bridge_annotation"].get("finite_representative_covered")
    )
    status = (
        "PASS_RESIDUE_PARTITION_EXHAUSTIVENESS"
        if counts.get("MISSING", 0) == 0
        and counts.get("DUPLICATE", 0) == 0
        and sampled_as_proof_count == 0
        else "FAIL_RESIDUE_PARTITION_EXHAUSTIVENESS"
    )

    report = {
        "status": status,
        "plain_truth": (
            "This is exact bookkeeping for the r0 mod 2^16 frontier split. "
            "It does not prove the Collatz theorem."
        ),
        "universe_type": "odd base residues r0 modulo 2^16",
        "modulus_power": KMAX,
        "total_odd_base_residues": 1 << (KMAX - 1),
        "assigned_once": counts.get("ASSIGNED_ONCE", 0),
        "missing": counts.get("MISSING", 0),
        "duplicates": counts.get("DUPLICATE", 0),
        "sampled_as_proof_count": sampled_as_proof_count,
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "source_data_gaps": {
            "pre_report_exact_depth_parent_recomputed": bucket_counts.get(
                "pre_report_exact_depth_parent_recomputed", 0
            ),
            "pre_report_exact_depth_parent_exported": bucket_counts.get(
                "pre_report_exact_depth_parent", 0
            ),
            "note": (
                "pre_report_exact_depth_parent_exported counts low-depth parent residues read "
                "directly from exact_depth_closure_report.json. A nonzero recomputed count would "
                "mean this audit had to reconstruct missing low-depth rows."
            ),
        },
        "direct_bridge_finite_representative_count": direct_finite_count,
        "direct_bridge_note": (
            "direct_bridge_report.json covers finite odd n representatives, "
            "not complete residue classes for density accounting."
        ),
        "input_presence": {
            str(EXACT_REPORT): exact_report is not None,
            str(PARENT_REPORT): parent_report is not None,
            str(DIRECT_BRIDGE_REPORT): direct_report is not None,
        },
        "source_row_counts": {
            "exact_depth_closure_parent_rows": len(exact_rows),
            "exact_depth_closure_pre_report_parent_rows": len(pre_report_rows),
            "quotient_parent_batch_parent_rows": len(deep_rows),
            "exact_report_duplicate_r0_rows": len(exact_internal_duplicates),
            "pre_report_exact_duplicate_r0_rows": len(pre_report_internal_duplicates),
            "deep_parent_report_duplicate_r0_rows": len(deep_internal_duplicates),
        },
        "first_20_missing": [
            record for record in records if record["assignment_status"] == "MISSING"
        ][:20],
        "first_20_duplicates": [
            record for record in records if record["assignment_status"] == "DUPLICATE"
        ][:20],
        "all_assignments": records,
    }
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("RESIDUE PARTITION EXHAUSTIVENESS")
    print(f"  Universe            : {report['universe_type']}")
    print(f"  Total odd r0         : {report['total_odd_base_residues']}")
    print(f"  Assigned once        : {report['assigned_once']}")
    print(f"  Missing              : {report['missing']}")
    print(f"  Duplicates           : {report['duplicates']}")
    print(f"  Bucket counts        : {report['bucket_counts']}")
    print(f"  Direct finite reps   : {direct_finite_count}")
    print(f"  Status               : {status}")


if __name__ == "__main__":
    main()
