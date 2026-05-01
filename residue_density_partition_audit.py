#!/usr/bin/env python3
"""
residue_density_partition_audit.py

Audit whether exact-depth closed lanes plus depth >18 parent lanes form an
exhaustive disjoint partition of odd residue classes.

This script does not run random seeds and does not use floating point values
for proof decisions.  It audits residue-class coverage exactly at a common
modulus 2^K, where K is the largest available lane modulus exponent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any


EXACT_REPORT = Path("exact_depth_closure_report.json")
PARENT_REPORT = Path("quotient_parent_batch_report.json")
PARTITION_REPORT = Path("residue_partition_exhaustiveness_report.json")
FINAL_AUDIT_REPORT = Path("final_certificate_audit_report.json")
OUT = Path("residue_density_partition_audit_report.json")

KMAX_BASE = 16
FIRST_EXAMPLE_LIMIT = 20


@dataclass(frozen=True)
class Lane:
    lane_id: str
    source: str
    lane_type: str
    row_index: int
    residue: int
    modulus_power: int
    depth: int | None
    classification: str
    sampled_or_exact: str
    sampled_as_proof: bool
    proof_modulus_power: int | None = None
    expanded_leaf_count: int = 1


@dataclass
class TrieNode:
    terminal_count: int = 0
    children: dict[int, "TrieNode"] = field(default_factory=dict)


def load_json(path: Path, required: bool = True) -> Any:
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


def is_sampled_row(row: dict[str, Any], report: dict[str, Any]) -> bool:
    row_flags = (
        row.get("sampled"),
        row.get("sampled_row"),
        row.get("sampled_rows_used"),
        row.get("sampled_as_proof"),
        row.get("random_seed"),
        row.get("random_seeds"),
    )
    if any(flag not in (None, False, 0, [], {}) for flag in row_flags):
        return True

    method = report.get("method") or {}
    method_flags = (
        method.get("sampled_rows_used"),
        method.get("random_seeds"),
        method.get("sampled_as_proof"),
    )
    return any(flag not in (None, False, 0, [], {}) for flag in method_flags)


def lane_evidence(row: dict[str, Any], report: dict[str, Any], exact_source: bool) -> tuple[str, bool]:
    sampled = is_sampled_row(row, report)
    if sampled:
        return "sampled", True
    if exact_source:
        return "exact", False
    return "exact_integer_or_symbolic_reported", False


def extract_lanes(
    exact_report: dict[str, Any] | None,
    parent_report: dict[str, Any] | None,
) -> tuple[list[Lane], list[dict[str, Any]]]:
    lanes: list[Lane] = []
    missing: list[dict[str, Any]] = []

    if exact_report is not None:
        for i, row in enumerate(exact_report.get("parent_rows", [])):
            closed = row.get("closed") is True
            if not closed:
                continue
            residue = as_int(row.get("r0", row.get("residue")))
            modulus_power = as_int(row.get("k_prime", row.get("modulus_power", row.get("k"))))
            depth = as_int(row.get("depth"))
            if residue is None or modulus_power is None:
                missing.append(
                    {
                        "source": str(EXACT_REPORT),
                        "row_index": i,
                        "reason": "closed exact-depth row missing residue or modulus power",
                    }
                )
                continue
            sampled_or_exact, sampled_as_proof = lane_evidence(row, exact_report, exact_source=True)
            lanes.append(
                Lane(
                    lane_id=f"exact:{i}:r{residue}:k{modulus_power}",
                    source=str(EXACT_REPORT),
                    lane_type="exact_depth_closed",
                    row_index=i,
                    residue=residue,
                    modulus_power=modulus_power,
                    depth=depth,
                    classification="CLOSED" if closed else str(row.get("status", "UNKNOWN")),
                    sampled_or_exact=sampled_or_exact,
                    sampled_as_proof=sampled_as_proof,
                )
            )

    if parent_report is not None:
        for i, row in enumerate(parent_report.get("parent_rows", [])):
            residue = as_int(row.get("r0", row.get("residue")))
            modulus_power = as_int(row.get("k_prime", row.get("modulus_power", row.get("k"))))
            depth = as_int(row.get("depth"))
            if residue is None or modulus_power is None:
                missing.append(
                    {
                        "source": str(PARENT_REPORT),
                        "row_index": i,
                        "reason": "deep parent row missing residue or modulus power",
                    }
                )
                continue
            sampled_or_exact, sampled_as_proof = lane_evidence(row, parent_report, exact_source=False)
            lanes.append(
                Lane(
                    lane_id=f"deep_parent:{i}:r{residue}:k{modulus_power}",
                    source=str(PARENT_REPORT),
                    lane_type="deep_parent",
                    row_index=i,
                    residue=residue,
                    modulus_power=modulus_power,
                    depth=depth,
                    classification=str(row.get("status", row.get("classification", "UNKNOWN"))),
                    sampled_or_exact=sampled_or_exact,
                    sampled_as_proof=sampled_as_proof,
                )
            )

    return lanes, missing


def extract_lanes_from_partition(partition_report: dict[str, Any]) -> tuple[list[Lane], list[dict[str, Any]]]:
    lanes: list[Lane] = []
    missing: list[dict[str, Any]] = []
    assignments = partition_report.get("all_assignments", [])
    for i, assignment in enumerate(assignments):
        if assignment.get("assignment_status") != "ASSIGNED_ONCE":
            missing.append(
                {
                    "source": str(PARTITION_REPORT),
                    "row_index": i,
                    "r0": assignment.get("r0"),
                    "reason": f"assignment status is {assignment.get('assignment_status')}",
                }
            )
            continue
        buckets = assignment.get("buckets", [])
        if len(buckets) != 1:
            missing.append(
                {
                    "source": str(PARTITION_REPORT),
                    "row_index": i,
                    "r0": assignment.get("r0"),
                    "reason": "assignment does not contain exactly one bucket",
                }
            )
            continue
        bucket = buckets[0]
        residue = as_int(bucket.get("r0", assignment.get("r0")))
        proof_k = as_int(bucket.get("k_prime", bucket.get("modulus_power", KMAX_BASE)))
        depth = as_int(bucket.get("depth"))
        if residue is None or proof_k is None:
            missing.append(
                {
                    "source": str(PARTITION_REPORT),
                    "row_index": i,
                    "r0": assignment.get("r0"),
                    "reason": "partition bucket missing r0 or proof modulus/depth",
                }
            )
            continue
        sampled = bucket.get("sampled") not in (None, False, 0)
        # The frontier partition universe is r0 modulo 2^16.  Parent rows with
        # proof depth k_prime certify all sibling leaves under that r0 prefix.
        lanes.append(
            Lane(
                lane_id=f"partition:{bucket.get('bucket')}:{residue}",
                source=str(bucket.get("source", PARTITION_REPORT)),
                lane_type=str(bucket.get("bucket", "unknown")),
                row_index=i,
                residue=residue,
                modulus_power=KMAX_BASE,
                depth=depth,
                classification=str(bucket.get("status", "UNKNOWN")),
                sampled_or_exact="sampled" if sampled else "exact",
                sampled_as_proof=sampled,
                proof_modulus_power=proof_k,
                expanded_leaf_count=1 << max(proof_k - KMAX_BASE, 0),
            )
        )
    return lanes, missing


def insert_lane(root: TrieNode, lane: Lane) -> None:
    node = root
    # Oddness fixes bit 0.  The trie indexes bits 1..k-1, low bit first.
    for bit_index in range(1, lane.modulus_power):
        bit = (lane.residue >> bit_index) & 1
        node = node.children.setdefault(bit, TrieNode())
    node.terminal_count += 1


def trie_slot_counts(root: TrieNode, common_k: int) -> tuple[int, int, int]:
    total_odd_slots = 1 << (common_k - 1)

    def walk(node: TrieNode, depth: int, inherited: int) -> tuple[int, int]:
        active = inherited + node.terminal_count
        span = 1 << (common_k - 1 - depth)
        if not node.children:
            covered = span if active > 0 else 0
            overlap = span if active > 1 else 0
            return covered, overlap

        covered = 0
        overlap = 0
        child_span = span >> 1
        for bit in (0, 1):
            child = node.children.get(bit)
            if child is None:
                if active > 0:
                    covered += child_span
                if active > 1:
                    overlap += child_span
            else:
                child_covered, child_overlap = walk(child, depth + 1, active)
                covered += child_covered
                overlap += child_overlap
        return covered, overlap

    covered_slots, overlap_slots = walk(root, 0, 0)
    return total_odd_slots, covered_slots, overlap_slots


def residue_is_covered(residue: int, lanes: list[Lane]) -> list[Lane]:
    return [
        lane
        for lane in lanes
        if residue % (1 << lane.modulus_power) == lane.residue % (1 << lane.modulus_power)
    ]


def first_missing_slots(lanes: list[Lane], common_k: int, limit: int) -> list[int]:
    missing: list[int] = []
    # Missing slots are expected near the bottom if the partition is incomplete.
    # The loop is exact for every slot it inspects; it stops after enough witnesses.
    for residue in range(1, 1 << common_k, 2):
        if not residue_is_covered(residue, lanes):
            missing.append(residue)
            if len(missing) >= limit:
                break
    return missing


def compatible(a: Lane, b: Lane) -> bool:
    modulus = 1 << min(a.modulus_power, b.modulus_power)
    return a.residue % modulus == b.residue % modulus


def first_overlap_slots(lanes: list[Lane], common_k: int, limit: int) -> list[dict[str, Any]]:
    candidates: dict[int, set[str]] = {}
    for i, a in enumerate(lanes):
        for b in lanes[i + 1 :]:
            if not compatible(a, b):
                continue
            if a.modulus_power >= b.modulus_power:
                residue = a.residue % (1 << common_k)
            else:
                residue = b.residue % (1 << common_k)
            candidates.setdefault(residue, set()).update({a.lane_id, b.lane_id})

    out: list[dict[str, Any]] = []
    for residue in sorted(candidates)[:limit]:
        covering = residue_is_covered(residue, lanes)
        out.append(
            {
                "residue_slot": residue,
                "covering_lane_ids": [lane.lane_id for lane in covering],
                "parent_ids": [
                    {
                        "lane_id": lane.lane_id,
                        "lane_type": lane.lane_type,
                        "row_index": lane.row_index,
                        "r": lane.residue,
                        "modulus_power": lane.modulus_power,
                        "depth": lane.depth,
                        "classification": lane.classification,
                    }
                    for lane in covering
                ],
            }
        )
    return out


def fraction_string(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def decimal_display(value: Fraction, digits: int = 18) -> str:
    scale = 10**digits
    scaled = value.numerator * scale // value.denominator
    whole, frac = divmod(scaled, scale)
    return f"{whole}.{frac:0{digits}d}".rstrip("0").rstrip(".")


def lane_to_json(lane: Lane) -> dict[str, Any]:
    return {
        "lane_id": lane.lane_id,
        "source": lane.source,
        "lane_type": lane.lane_type,
        "row_index": lane.row_index,
        "residue": lane.residue,
        "coverage_modulus": f"2^{lane.modulus_power}",
        "coverage_modulus_power": lane.modulus_power,
        "proof_modulus": f"2^{lane.proof_modulus_power}" if lane.proof_modulus_power else f"2^{lane.modulus_power}",
        "proof_modulus_power": lane.proof_modulus_power or lane.modulus_power,
        "expanded_leaf_count_at_proof_modulus": lane.expanded_leaf_count,
        "depth": lane.depth,
        "status_or_classification": lane.classification,
        "sampled_or_exact": lane.sampled_or_exact,
        "sampled_as_proof": lane.sampled_as_proof,
        "density_all_integers": fraction_string(Fraction(1, 1 << lane.modulus_power)),
        "density_within_odd_universe": fraction_string(Fraction(1, 1 << (lane.modulus_power - 1))),
    }


def main() -> None:
    exact_report = load_json(EXACT_REPORT, required=False)
    parent_report = load_json(PARENT_REPORT, required=False)
    partition_report = load_json(PARTITION_REPORT, required=False)
    final_report = load_json(FINAL_AUDIT_REPORT, required=False)

    missing_inputs = [
        str(path)
        for path, loaded, required in (
            (EXACT_REPORT, exact_report, True),
            (PARENT_REPORT, parent_report, True),
            (FINAL_AUDIT_REPORT, final_report, True),
            (PARTITION_REPORT, partition_report, False),
        )
        if required and loaded is None
    ]

    partition_status = partition_report.get("status") if isinstance(partition_report, dict) else None
    if partition_status == "PASS_RESIDUE_PARTITION_EXHAUSTIVENESS":
        lanes, missing_lane_data = extract_lanes_from_partition(partition_report)
        lane_source_mode = "residue_partition_exhaustiveness_report"
    else:
        lanes, missing_lane_data = extract_lanes(exact_report, parent_report)
        lane_source_mode = "exact_depth_and_deep_parent_reports_only"
    invalid_lanes = [
        lane_to_json(lane)
        for lane in lanes
        if lane.modulus_power < 1 or lane.residue % 2 == 0
    ]

    complete_lane_data = not missing_inputs and not missing_lane_data and not invalid_lanes and bool(lanes)
    common_k = max((lane.modulus_power for lane in lanes), default=0)

    root = TrieNode()
    if complete_lane_data:
        for lane in lanes:
            insert_lane(root, lane)
        total_odd_slots, covered_slots, overlap_slots = trie_slot_counts(root, common_k)
        missing_slots = total_odd_slots - covered_slots
    else:
        total_odd_slots = 0
        covered_slots = 0
        overlap_slots = 0
        missing_slots = 0

    sampled_as_proof_count = sum(1 for lane in lanes if lane.sampled_as_proof)
    exact_depth_lanes = [
        lane
        for lane in lanes
        if lane.lane_type in {"exact_depth_closed", "exact_depth_closed_parent"}
    ]
    pre_report_exact_depth_lanes = [
        lane for lane in lanes if lane.lane_type == "pre_report_exact_depth_parent_recomputed"
    ]
    deep_parent_lanes = [lane for lane in lanes if lane.lane_type == "deep_parent"]
    exact_depth_closed_slots = sum(
        1 << (common_k - lane.modulus_power)
        for lane in exact_depth_lanes
        if complete_lane_data
    )
    deep_parent_slots = sum(
        1 << (common_k - lane.modulus_power)
        for lane in deep_parent_lanes
        if complete_lane_data
    )
    pre_report_exact_depth_slots = sum(
        1 << (common_k - lane.modulus_power)
        for lane in pre_report_exact_depth_lanes
        if complete_lane_data
    )
    lane_density_sum_all_integers = sum(
        (Fraction(1, 1 << lane.modulus_power) for lane in lanes),
        Fraction(0, 1),
    )
    lane_density_sum_odd_universe = sum(
        (Fraction(1, 1 << (lane.modulus_power - 1)) for lane in lanes),
        Fraction(0, 1),
    )
    covered_density_odd_universe = (
        Fraction(covered_slots, total_odd_slots) if total_odd_slots else Fraction(0, 1)
    )

    if not complete_lane_data:
        status = "INCOMPLETE_DENSITY_PARTITION"
    elif missing_slots or overlap_slots:
        status = "FAIL_DENSITY_PARTITION"
    elif sampled_as_proof_count:
        status = "INCOMPLETE_DENSITY_PARTITION"
    else:
        status = "PASS_DENSITY_PARTITION"

    first_missing = (
        first_missing_slots(lanes, common_k, FIRST_EXAMPLE_LIMIT)
        if complete_lane_data and missing_slots
        else []
    )
    first_overlaps = (
        first_overlap_slots(lanes, common_k, FIRST_EXAMPLE_LIMIT)
        if complete_lane_data and overlap_slots
        else []
    )

    report = {
        "status": status,
        "plain_truth": (
            "This is an exact residue-slot density audit only. It does not claim the proof is complete."
        ),
        "lane_source_mode": lane_source_mode,
        "universe_type": "C) odd residues modulo 2^K",
        "universe_notes": {
            "A_all_integers": "A lane r mod 2^k has density 1/2^k among all integers.",
            "B_all_odd_integers": "The same odd lane has density 1/2^(k-1) relative to odd integers.",
            "C_odd_residues_mod_2^K": "This audit uses slots among odd residues modulo 2^K.",
            "common_denominator": "2^(K-1) odd slots for universe C.",
            "coverage_lane_note": (
                "When residue_partition_exhaustiveness_report.json is present and passing, "
                "coverage lanes are the r0 mod 2^16 frontier cylinders. proof_modulus_power "
                "records the exact/deep proof depth for parent cylinders."
            ),
        },
        "common_modulus_power": common_k,
        "common_modulus": f"2^{common_k}" if common_k else None,
        "max_proof_modulus_power": max(
            (lane.proof_modulus_power or lane.modulus_power for lane in lanes),
            default=0,
        ),
        "total_odd_residue_slots": total_odd_slots,
        "covered_slots": covered_slots,
        "missing_slots": missing_slots,
        "duplicate_overlap_slots": overlap_slots,
        "sampled_as_proof_count": sampled_as_proof_count,
        "exact_depth_closed_slots": exact_depth_closed_slots,
        "pre_report_exact_depth_slots": pre_report_exact_depth_slots,
        "deep_parent_slots": deep_parent_slots,
        "density_sum_as_fraction": fraction_string(lane_density_sum_all_integers),
        "density_sum_decimal_display": decimal_display(lane_density_sum_all_integers),
        "density_sum_basis": "sum of per-lane 1/2^k densities among all integers",
        "density_sum_within_odd_universe_as_fraction": fraction_string(lane_density_sum_odd_universe),
        "covered_density_within_odd_universe_as_fraction": fraction_string(covered_density_odd_universe),
        "covered_density_decimal_display": decimal_display(covered_density_odd_universe),
        "lane_counts": {
            "total_lanes": len(lanes),
            "exact_depth_closed_lanes": len(exact_depth_lanes),
            "pre_report_exact_depth_lanes": len(pre_report_exact_depth_lanes),
            "deep_parent_lanes": len(deep_parent_lanes),
        },
        "classification_counts": {
            classification: sum(1 for lane in lanes if lane.classification == classification)
            for classification in sorted({lane.classification for lane in lanes})
        },
        "input_presence": {
            str(EXACT_REPORT): exact_report is not None,
            str(PARENT_REPORT): parent_report is not None,
            str(PARTITION_REPORT): partition_report is not None,
            str(FINAL_AUDIT_REPORT): final_report is not None,
        },
        "missing_required_inputs": missing_inputs,
        "missing_lane_data": missing_lane_data,
        "invalid_lanes": invalid_lanes,
        "first_20_missing_residue_slots": first_missing,
        "first_20_overlap_residue_slots": first_overlaps,
        "parent_ids_causing_overlap": first_overlaps,
        "lanes": [lane_to_json(lane) for lane in lanes],
    }

    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("RESIDUE DENSITY PARTITION AUDIT")
    print(f"  Universe                  : {report['universe_type']}")
    print(f"  Common modulus power K    : {common_k}")
    print(f"  Total odd slots           : {total_odd_slots}")
    print(f"  Covered slots             : {covered_slots}")
    print(f"  Missing slots             : {missing_slots}")
    print(f"  Duplicate/overlap slots   : {overlap_slots}")
    print(f"  Sampled as proof count    : {sampled_as_proof_count}")
    print(f"  Density sum               : {report['density_sum_as_fraction']}")
    print(f"  Status                    : {status}")
    if first_missing:
        print(f"  First missing slots       : {first_missing}")
    if first_overlaps:
        print("  First overlap slots       :")
        for item in first_overlaps:
            print(f"    {item['residue_slot']}: {item['covering_lane_ids']}")


if __name__ == "__main__":
    main()
