#!/usr/bin/env python3
"""
formal_verifier.py

Machine-checkable audit for the current Collatz certificate packet.

This verifier intentionally separates what is checked from what is only
supported by upstream grouping reports:

  - It checks every displayed 84 packet row by raw integer arithmetic.
  - It recomputes valuation words from representatives.
  - It verifies valuation-word forcing modulo 2^(A+1).
  - It verifies the affine tuple and descent inequality exactly.
  - It verifies the source partition/closure reports have PASS statuses.

It does not by itself prove Collatz. The remaining mathematical bridge is that
the 84 cost-table groups are aggregates; group coverage depends on the recorded
partition/grouping audits and should be independently reviewed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKET = Path("reviewer_packet_84_symbolic_class_groups.json")
ZERO_GOLD = Path("zero_new_cases_d_gold_audit_report.json")
RESIDUE_PARTITION = Path("residue_partition_exhaustiveness_report.json")
RESIDUE_DENSITY = Path("residue_density_partition_audit_report.json")
FULL_FRAMEWORK = Path("full_framework_closure_audit_report.json")
MASTER_SOURCE = Path("master_source_coverage_audit_report.json")
OUT_JSON = Path("formal_verifier_report.json")
OUT_MD = Path("formal_verifier_report.md")

PACKET_STATUS = "84-LABEL SYMBOLIC CERTIFICATE PACKET STABLE THROUGH k41"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def v2(n: int) -> int:
    if n <= 0:
        raise ValueError("v2 expects positive integer")
    return (n & -n).bit_length() - 1


def valuation_word(n: int, m: int) -> tuple[list[int], int]:
    vals: list[int] = []
    x = n
    for _ in range(m):
        y = 3 * x + 1
        a = v2(y)
        vals.append(a)
        x = y >> a
    return vals, x


def word_hash(vals: list[int]) -> str:
    return hashlib.sha256(",".join(map(str, vals)).encode("ascii")).hexdigest()


def affine_from_word(vals: list[int]) -> tuple[int, int, int]:
    total_a = 0
    b = 0
    for a in vals:
        b = 3 * b + (1 << total_a)
        total_a += a
    return len(vals), total_a, b


def forced_word_mod_check(r: int, vals: list[int], A: int) -> tuple[bool, str]:
    """
    Verify that every n == r mod 2^(A+1) has the displayed valuation word.

    After a prefix with total division exponent s, the current odd iterate is
    determined modulo 2^(A+1-s). The next valuation a is forced if 3x+1 is
    divisible by 2^a and not by 2^(a+1) modulo that remaining power.
    """
    remaining = A + 1
    residue = r % (1 << remaining)
    used = 0
    for idx, a in enumerate(vals, start=1):
        if remaining < a + 1:
            return False, f"step {idx}: remaining bits {remaining} < a+1 {a+1}"
        y = 3 * residue + 1
        if y % (1 << a) != 0:
            return False, f"step {idx}: not divisible by 2^{a}"
        if y % (1 << (a + 1)) == 0:
            return False, f"step {idx}: divisible by 2^{a+1}; valuation not exact"
        remaining -= a
        used += a
        residue = (y >> a) % (1 << remaining)
    if used != A:
        return False, f"total valuation {used} != A {A}"
    return True, "forced modulo 2^(A+1)"


def ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def verify_packet_row(row: dict[str, Any]) -> dict[str, Any]:
    cert = row["canonical_certificate"]
    class_id = int(row["class_id"])
    r = int(cert["r"])
    representative = int(cert["representative_n"])
    A = int(cert["A"])
    m = int(cert["m"])
    b = int(cert["b"])
    gap = int(cert["gap"])
    B = int(cert["B"])
    min_n = int(cert["min_n"])
    below_value = int(cert["below_value"])

    failures: list[str] = []
    vals, computed_below = valuation_word(representative, m)
    computed_m, computed_A, computed_b = affine_from_word(vals)
    computed_gap = (1 << A) - pow(3, m)
    computed_B = ceil_div(b, gap) if gap > 0 else None
    h = word_hash(vals)
    forced_ok, forced_reason = forced_word_mod_check(r, vals, A)

    if representative % 2 != 1:
        failures.append("representative is not odd")
    if r % 2 != 1:
        failures.append("r is not odd")
    if computed_m != m:
        failures.append(f"computed m {computed_m} != packet m {m}")
    if computed_A != A:
        failures.append(f"computed A {computed_A} != packet A {A}")
    if computed_b != b:
        failures.append("computed b does not match packet b")
    if computed_gap != gap:
        failures.append("computed gap does not match packet gap")
    if computed_B != B:
        failures.append(f"computed B {computed_B} != packet B {B}")
    if below_value != computed_below:
        failures.append("computed below_value does not match packet below_value")
    if h != cert["valuation_word_hash"]:
        failures.append("valuation hash mismatch")
    if not forced_ok:
        failures.append(f"valuation forcing failed: {forced_reason}")
    if gap <= 0:
        failures.append("gap <= 0")
    if min_n <= B:
        failures.append("min_n <= B")
    if cert.get("forcing_modulus") != f"2^{A + 1}":
        failures.append("forcing_modulus field is not 2^(A+1)")
    if cert.get("affine_denominator") != f"2^{A}":
        failures.append("affine_denominator field is not 2^A")
    if cert.get("status") != PACKET_STATUS:
        failures.append("row status does not match packet stability status")

    # Exact representative descent identity.
    lhs = (pow(3, m) * representative + b) // (1 << A)
    if lhs != computed_below:
        failures.append("affine formula does not reproduce representative descent")
    if computed_below >= representative:
        failures.append("representative does not descend below itself")

    return {
        "class_id": class_id,
        "r": str(r),
        "A": A,
        "m": m,
        "B": str(B),
        "min_n": str(min_n),
        "forcing_modulus": f"2^{A + 1}",
        "valuation_hash": h,
        "forced_word": forced_ok,
        "gap_positive": gap > 0,
        "min_n_gt_B": min_n > B,
        "representative_descends": computed_below < representative,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def source_statuses() -> dict[str, Any]:
    residue = load_json(RESIDUE_PARTITION)
    density = load_json(RESIDUE_DENSITY)
    full = load_json(FULL_FRAMEWORK)
    master = load_json(MASTER_SOURCE)
    zero = load_json(ZERO_GOLD) if ZERO_GOLD.exists() else None

    return {
        "zero_new_cases_d_gold": None if zero is None else zero.get("status"),
        "residue_partition": residue.get("status"),
        "residue_partition_assigned_once": residue.get("assigned_once"),
        "residue_partition_missing": residue.get("missing"),
        "residue_partition_duplicates": residue.get("duplicates"),
        "residue_partition_sampled_as_proof": residue.get("sampled_as_proof_count"),
        "residue_density": density.get("status"),
        "density_covered_slots": density.get("covered_slots"),
        "density_missing_slots": density.get("missing_slots"),
        "density_duplicate_overlap_slots": density.get("duplicate_overlap_slots"),
        "full_framework": full.get("status"),
        "parents_checked": full.get("parents_checked"),
        "parents_closed": full.get("parents_closed"),
        "exact_states_checked": full.get("exact_states_checked"),
        "compact_quotient_only_rows": full.get("compact_quotient_only_rows"),
        "master_source": master.get("status"),
    }


def main() -> None:
    packet = load_json(PACKET)
    failures: list[str] = []

    if packet.get("status") != PACKET_STATUS:
        failures.append("packet status mismatch")
    if packet.get("group_count") != 84:
        failures.append("packet group_count != 84")
    if packet.get("forcing_convention", {}).get("valuation_word_forcing_modulus") != "2^(A+1)":
        failures.append("packet forcing convention mismatch")
    if packet.get("forcing_convention", {}).get("affine_descent_denominator") != "2^A":
        failures.append("packet affine denominator convention mismatch")

    rows = [verify_packet_row(row) for row in packet.get("records", [])]
    row_failures = [row for row in rows if row["failures"]]
    failures.extend(
        f"class {row['class_id']}: " + "; ".join(row["failures"])
        for row in row_failures
    )

    group_member_sum = sum(int(row.get("group_member_count", 0)) for row in packet["records"])
    if group_member_sum != int(packet.get("classes_audited", -1)):
        failures.append("group member sum does not match classes_audited")

    statuses = source_statuses()
    expected = {
        "zero_new_cases_d_gold": "D_GOLD_ZERO_NEW_CASES_AUDIT_PASS",
        "residue_partition": "PASS_RESIDUE_PARTITION_EXHAUSTIVENESS",
        "residue_density": "PASS_DENSITY_PARTITION",
        "full_framework": "PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE",
        "master_source": "PASS",
    }
    for key, value in expected.items():
        if statuses.get(key) != value:
            failures.append(f"{key} status {statuses.get(key)!r} != {value!r}")
    if statuses.get("residue_partition_missing") != 0:
        failures.append("residue partition has missing rows")
    if statuses.get("residue_partition_duplicates") != 0:
        failures.append("residue partition has duplicates")
    if statuses.get("residue_partition_sampled_as_proof") != 0:
        failures.append("residue partition uses sampled proof rows")
    if statuses.get("density_missing_slots") != 0:
        failures.append("density partition has missing slots")
    if statuses.get("density_duplicate_overlap_slots") != 0:
        failures.append("density partition has duplicate/overlap slots")
    if statuses.get("parents_checked") != statuses.get("parents_closed"):
        failures.append("not all full-framework parents are closed")
    if statuses.get("compact_quotient_only_rows") != 0:
        failures.append("compact quotient-only rows remain")

    status = "FORMAL_VERIFIER_PASS_WITH_GROUP_COVERAGE_CAVEAT" if not failures else "FORMAL_VERIFIER_FAIL"
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "collatz_proven_by_this_file": False,
        "why_not_final_proof": (
            "The verifier checks all displayed packet rows and source audit statuses. "
            "The 84 packet rows are cost-table groups, so a final proof still needs "
            "independent review of the grouping/partition theorem that maps every odd n "
            "to a displayed certified group or exact-state closure branch."
        ),
        "packet_rows_checked": len(rows),
        "packet_rows_passed": sum(1 for row in rows if row["status"] == "PASS"),
        "packet_rows_failed": len(row_failures),
        "group_member_sum": group_member_sum,
        "classes_audited": packet.get("classes_audited"),
        "source_statuses": statuses,
        "failures": failures,
        "row_results": rows,
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    md = [
        "# Formal Verifier Report",
        "",
        f"Status: `{status}`",
        "",
        f"- Packet rows checked: `{len(rows)}`",
        f"- Packet rows passed: `{report['packet_rows_passed']}`",
        f"- Packet rows failed: `{report['packet_rows_failed']}`",
        f"- Group member sum: `{group_member_sum}`",
        f"- Classes audited: `{packet.get('classes_audited')}`",
        f"- Collatz proven by this file: `{report['collatz_proven_by_this_file']}`",
        "",
        "## Source Statuses",
        "",
    ]
    for key, value in statuses.items():
        md.append(f"- {key}: `{value}`")
    md.extend(["", "## Caveat", "", report["why_not_final_proof"], ""])
    if failures:
        md.extend(["## Failures", ""])
        md.extend(f"- {failure}" for failure in failures)
    else:
        md.extend(
            [
                "## Checked Result",
                "",
                "All displayed 84 packet rows passed raw integer verification: valuation hash, forced word modulo `2^(A+1)`, affine tuple, positive gap, `min_n > B`, and representative descent.",
            ]
        )
    OUT_MD.write_text("\n".join(md) + "\n")

    print(status)
    print(f"packet rows checked: {len(rows)}")
    print(f"packet rows passed: {report['packet_rows_passed']}")
    print(f"packet rows failed: {report['packet_rows_failed']}")
    print(f"group member sum: {group_member_sum}")
    print(f"classes audited: {packet.get('classes_audited')}")
    print(f"failures: {len(failures)}")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
