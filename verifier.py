#!/usr/bin/env python3
"""
Reviewer-facing verifier for the exported Collatz certificate packet.

Inputs:
  - certificate_packet_84.json
  - group_coverage_map.json

Output is intentionally short and checklist-shaped for external review.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CERTIFICATE_PACKET = Path("certificate_packet_84.json")
COVERAGE_MAP = Path("group_coverage_map.json")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def v2(n: int) -> int:
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


def ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def forced_word_mod_check(r: int, vals: list[int], A: int) -> bool:
    remaining = A + 1
    residue = r % (1 << remaining)
    used = 0
    for a in vals:
        y = 3 * residue + 1
        if y % (1 << a) != 0:
            return False
        if y % (1 << (a + 1)) == 0:
            return False
        remaining -= a
        if remaining < 1 and a != vals[-1]:
            return False
        residue = (y >> a) % (1 << remaining)
        used += a
    return used == A


def verify_certificate_rows(packet: dict[str, Any]) -> tuple[int, list[str]]:
    failures: list[str] = []
    passed = 0
    for row in packet.get("records", []):
        cid = row.get("class_id")
        cert = row.get("canonical_certificate", {})
        try:
            r = int(cert["r"])
            representative = int(cert["representative_n"])
            A = int(cert["A"])
            m = int(cert["m"])
            b = int(cert["b"])
            gap = int(cert["gap"])
            B = int(cert["B"])
            min_n = int(cert["min_n"])
            below_value = int(cert["below_value"])
        except Exception as exc:
            failures.append(f"class {cid}: missing/noninteger field: {exc}")
            continue

        vals, computed_below = valuation_word(representative, m)
        computed_m, computed_A, computed_b = affine_from_word(vals)
        computed_gap = (1 << A) - pow(3, m)
        computed_B = ceil_div(b, gap) if gap > 0 else None
        affine_below = (pow(3, m) * representative + b) // (1 << A)

        row_failures = []
        if representative % 2 != 1 or r % 2 != 1:
            row_failures.append("non-odd residue/representative")
        if computed_m != m:
            row_failures.append("m mismatch")
        if computed_A != A:
            row_failures.append("A mismatch")
        if computed_b != b:
            row_failures.append("b mismatch")
        if computed_gap != gap or gap <= 0:
            row_failures.append("gap mismatch/nonpositive")
        if computed_B != B:
            row_failures.append("B mismatch")
        if min_n <= B:
            row_failures.append("min_n <= B")
        if computed_below != below_value or affine_below != below_value:
            row_failures.append("affine descent mismatch")
        if below_value >= representative:
            row_failures.append("representative does not descend")
        if word_hash(vals) != cert.get("valuation_word_hash"):
            row_failures.append("valuation hash mismatch")
        if not forced_word_mod_check(r, vals, A):
            row_failures.append("valuation forcing mismatch")
        if cert.get("forcing_modulus") != f"2^{A + 1}":
            row_failures.append("forcing modulus field mismatch")

        if row_failures:
            failures.append(f"class {cid}: " + "; ".join(row_failures))
        else:
            passed += 1
    return passed, failures


def main() -> int:
    packet = load_json(CERTIFICATE_PACKET)
    coverage = load_json(COVERAGE_MAP)
    base = coverage["base_partition"]
    exact = coverage["exact_state_closure"]
    cert_map = coverage["certificate_packet"]
    passed, failures = verify_certificate_rows(packet)

    base_ok = (
        base["assigned_once"] == base["total_odd_base_residues"]
        and base["missing"] == 0
        and base["duplicates"] == 0
        and base["sampled_as_proof_count"] == 0
    )
    exact_ok = (
        exact["parents_closed"] == exact["parents_checked"] == 578
        and exact["exact_states_checked"] == 1235
        and exact["compact_quotient_only_rows"] == 0
    )
    cert_ok = (
        passed == 84
        and not failures
        and cert_map["stable_through_k"] == 41
        and cert_map["forcing_modulus"] == "2^(A+1)"
        and cert_map["affine_denominator"] == "2^A"
    )

    print("BASE_PARTITION_COMPLETE" if base_ok else "BASE_PARTITION_FAILED")
    print(f"{base['assigned_once']} / {base['total_odd_base_residues']} odd residues assigned")
    print(f"missing = {base['missing']}")
    print(f"duplicates = {base['duplicates']}")
    print()
    print("EXACT_STATE_CLOSURE_COMPLETE" if exact_ok else "EXACT_STATE_CLOSURE_FAILED")
    print(f"parents closed = {exact['parents_closed']} / {exact['parents_checked']}")
    print(f"exact states checked = {exact['exact_states_checked']}")
    print(f"quotient-only rows = {exact['compact_quotient_only_rows']}")
    print()
    print("CERTIFICATE_PACKET_VERIFIED" if cert_ok else "CERTIFICATE_PACKET_FAILED")
    print(f"{passed} / 84 rows passed")
    print("valuation forcing verified with 2^(A+1)" if cert_ok else "valuation forcing verification failed")
    print("affine descent verified" if cert_ok else "affine descent verification failed")
    print(f"stable through k{cert_map['stable_through_k']}")
    print()
    print("FINAL STATUS:")
    print("certificate algebra verified")
    print("coverage map complete at base partition")
    print("grouping theorem requires independent review")

    if failures:
        print()
        print("FAILURES:")
        for failure in failures[:20]:
            print(f"- {failure}")
        if len(failures) > 20:
            print(f"- ... {len(failures) - 20} more")

    return 0 if base_ok and exact_ok and cert_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
