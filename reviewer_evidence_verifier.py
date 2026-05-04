#!/usr/bin/env python3
"""Verify the reviewer evidence index against exported packet files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def load(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    index = load("REVIEWER_EVIDENCE_INDEX.json")
    cert = load("collatz_certificate.json")
    packet = load("certificate_packet_84.json")
    coverage = load("group_coverage_map.json")
    formal = load("formal_verifier_report.json")

    failures: list[str] = []

    sha = hashlib.sha256(Path("collatz_certificate.json").read_bytes()).hexdigest()
    if sha != index["legacy_full_certificate_layer"]["sha256"]:
        failures.append("collatz_certificate.json sha256 mismatch")

    entries = cert["certificates"]
    source_counts: dict[str, int] = {}
    for entry in entries:
        source_counts[entry["source"]] = source_counts.get(entry["source"], 0) + 1

    k16 = {int(entry["residue"]) for entry in entries if entry["k"] == 16}
    expected_k16 = set(range(1, 1 << 16, 2))

    checks = {
        "legacy_total_certificates": len(entries) == 1_210_087,
        "legacy_k16_complete": len(k16) == 32_768 and not (expected_k16 - k16),
        "legacy_source_counts_match": source_counts == index["legacy_full_certificate_layer"]["source_counts"],
        "legacy_no_direct_failures": len(cert["direct_verification"]["failures"]) == 0,
        "legacy_no_unclosed_lanes": cert["meta"]["unclosed_lanes"] == 0,
        "legacy_no_sibling_failures": cert["meta"]["sibling_failures"] == 0,
        "legacy_sampled_marked": source_counts.get("bfs_sibling_sampled", 0) == 49_664,
        "packet_84_rows": packet["group_count"] == 84 and formal["packet_rows_passed"] == 84,
        "packet_zero_failures": formal["packet_rows_failed"] == 0 and not formal["failures"],
        "packet_forcing_rule": packet["forcing_convention"]["valuation_word_forcing_modulus"] == "2^(A+1)",
        "packet_stable_k41": packet["recurrence_stability"]["compressed_recurrence_checked_through_k"] == 41,
        "coverage_base_complete": coverage["base_partition"]["assigned_once"] == coverage["base_partition"]["total_odd_base_residues"] == 32_768,
        "coverage_no_missing_duplicates": coverage["base_partition"]["missing"] == 0 and coverage["base_partition"]["duplicates"] == 0,
        "coverage_exact_state_closed": coverage["exact_state_closure"]["parents_closed"] == coverage["exact_state_closure"]["parents_checked"] == 578,
        "coverage_no_quotient_only": coverage["exact_state_closure"]["compact_quotient_only_rows"] == 0,
    }

    for name, ok in checks.items():
        if not ok:
            failures.append(name)

    print("REVIEWER_EVIDENCE_VERIFIER")
    for name, ok in checks.items():
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
    print()
    if failures:
        print("FINAL STATUS: REVIEWER_EVIDENCE_FAILED")
        print("failures:", len(failures))
        for failure in failures:
            print("-", failure)
        return 1
    print("FINAL STATUS: REVIEWER_EVIDENCE_INDEX_VERIFIED")
    print("legacy full certificate layer: verified counts and hash")
    print("84 symbolic packet layer: verified rows and forcing rule")
    print("coverage layer: verified base partition and exact-state closure counts")
    print("remaining review target: grouping theorem / arbitrary-n membership")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
