#!/usr/bin/env python3
"""
quotient_exact_state_fallback_audit.py

Audit the exact affine representatives exported in quotient_transition_table.json.

This is not a full quotient-equivalence proof. It checks that the proof-critical
tracked keys used by the transition table have exact affine state, exact gap/B
arithmetic, terminal certification, no sampled proof rows, and no final B over
the direct bridge limit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TABLE = Path("quotient_transition_table.json")
OUT = Path("quotient_exact_state_fallback_audit_report.json")
B_LIMIT = 200_001
TERMINAL = {"CERTIFIED_RETURN", "HIGH_B_RETURN_THEN_CERTIFIED", "COVERED", "CLOSED"}


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def exact_gap(o: int, c: int) -> int:
    return (1 << c) - (3**o)


def ceil_div(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("ceil_div denominator must be positive")
    return (a + b - 1) // b


def key_id(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def audit_representative(row: dict[str, Any], rep: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    affine = rep.get("affine_state")
    if not isinstance(affine, dict):
        return [{"key": row.get("key"), "reason": "missing affine_state", "representative": rep}]
    if affine.get("exact") is not True:
        failures.append({"key": row.get("key"), "reason": "affine_state not exact"})

    missing = [name for name in ("o", "c", "b", "gap", "gap_sign") if affine.get(name) is None]
    if missing:
        failures.append({"key": row.get("key"), "reason": "missing affine fields", "fields": missing})
        return failures

    o = int(affine["o"])
    c = int(affine["c"])
    b = int(affine["b"])
    gap = exact_gap(o, c)
    if str(gap) != str(affine["gap"]):
        failures.append(
            {
                "key": row.get("key"),
                "reason": "gap mismatch",
                "reported_gap": affine.get("gap"),
                "computed_gap": str(gap),
            }
        )
    sign = 1 if gap > 0 else (-1 if gap < 0 else 0)
    if sign != int(affine["gap_sign"]):
        failures.append(
            {
                "key": row.get("key"),
                "reason": "gap sign mismatch",
                "reported_gap_sign": affine.get("gap_sign"),
                "computed_gap_sign": sign,
            }
        )
    if gap > 0:
        B = ceil_div(b, gap)
        if affine.get("B") is None:
            failures.append({"key": row.get("key"), "reason": "positive gap missing exact B"})
        elif int(affine["B"]) != B:
            failures.append(
                {
                    "key": row.get("key"),
                    "reason": "B mismatch",
                    "reported_B": affine.get("B"),
                    "computed_B": B,
                }
            )

    proof_key = rep.get("proof_critical_state_key")
    if not isinstance(proof_key, dict):
        failures.append({"key": row.get("key"), "reason": "missing proof_critical_state_key"})
    elif str(proof_key.get("gap")) != str(affine.get("gap")) or str(proof_key.get("b")) != str(affine.get("b")):
        failures.append({"key": row.get("key"), "reason": "proof_critical_state_key disagrees with affine_state"})
    return failures


def main() -> None:
    table = load_json(TABLE)
    if not isinstance(table, dict):
        report = {
            "status": "INCOMPLETE_EXACT_STATE_FALLBACK",
            "reason": "quotient_transition_table.json missing or invalid",
        }
        with OUT.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print("QUOTIENT EXACT STATE FALLBACK AUDIT")
        print("  Status: INCOMPLETE_EXACT_STATE_FALLBACK")
        return

    rows = table.get("rows", [])
    missing_exact_representatives = []
    arithmetic_failures = []
    uncertified_terminal_failures = []
    sampled_as_proof = []
    final_b_over = []
    compact_key_state_counts: dict[str, int] = {}

    for row in rows:
        key = row.get("key")
        reps = row.get("representatives", [])
        classification = row.get("classification")
        if row.get("sampled") or row.get("sampled_as_proof"):
            sampled_as_proof.append(key)
        if not reps:
            missing_exact_representatives.append({"key": key, "reason": "no representatives"})
            continue

        exact_positive_certificates = 0
        state_ids = set()
        for rep in reps:
            arithmetic_failures.extend(audit_representative(row, rep))
            affine = rep.get("affine_state", {})
            proof_key = rep.get("proof_critical_state_key")
            if isinstance(proof_key, dict):
                state_ids.add(key_id(proof_key))
            if affine.get("B") is not None and int(affine["B"]) <= B_LIMIT and int(affine.get("gap_sign", 0)) > 0:
                exact_positive_certificates += 1
        compact_key_state_counts[key_id(key)] = len(state_ids)

        if classification in TERMINAL and exact_positive_certificates == 0:
            uncertified_terminal_failures.append(
                {"key": key, "classification": classification, "reason": "terminal row lacks exact positive B certificate"}
            )
        if row.get("final_B") is not None and int(row["final_B"]) > B_LIMIT:
            final_b_over.append({"key": key, "final_B": row["final_B"]})

    failures = (
        missing_exact_representatives
        or arithmetic_failures
        or uncertified_terminal_failures
        or sampled_as_proof
        or final_b_over
    )
    status = "PASS_EXACT_STATE_FALLBACK_FOR_TRACKED_KEYS" if not failures else "FAIL_EXACT_STATE_FALLBACK"
    report = {
        "status": status,
        "plain_truth": (
            "This exact-state fallback audit covers exported proof-critical tracked keys only. "
            "It does not prove that compact quotient keys represent full equivalence classes."
        ),
        "input": str(TABLE),
        "tracked_keys_checked": len(rows),
        "full_equivalence_proven": False,
        "relies_on_compact_quotient_equivalence": False,
        "sampled_as_proof_count": len(sampled_as_proof),
        "missing_exact_representative_count": len(missing_exact_representatives),
        "arithmetic_failure_count": len(arithmetic_failures),
        "uncertified_terminal_failure_count": len(uncertified_terminal_failures),
        "final_B_over_200001_count": len(final_b_over),
        "compact_keys_with_multiple_exact_state_signatures": sum(
            1 for count in compact_key_state_counts.values() if count > 1
        ),
        "missing_exact_representatives": missing_exact_representatives[:50],
        "arithmetic_failures": arithmetic_failures[:50],
        "uncertified_terminal_failures": uncertified_terminal_failures[:50],
        "sampled_as_proof_keys": sampled_as_proof[:50],
        "final_B_over_200001": final_b_over[:50],
    }
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("QUOTIENT EXACT STATE FALLBACK AUDIT")
    print(f"  Status                         : {status}")
    print(f"  Tracked keys checked           : {len(rows)}")
    print(f"  Missing exact representatives  : {len(missing_exact_representatives)}")
    print(f"  Arithmetic failures            : {len(arithmetic_failures)}")
    print(f"  Uncertified terminal failures  : {len(uncertified_terminal_failures)}")
    print(f"  Final B over {B_LIMIT}         : {len(final_b_over)}")
    print(f"  Sampled as proof               : {len(sampled_as_proof)}")
    print(f"  Report                         : {OUT}")


if __name__ == "__main__":
    main()
