#!/usr/bin/env python3
"""
quotient_transition_table_audit.py

Audit quotient_transition_table.json. This checks tracked proof-critical keys,
not the full mathematical quotient-equivalence lemma.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TABLE = Path("quotient_transition_table.json")
OUT = Path("quotient_transition_table_audit_report.json")
B_LIMIT = 200_001
TERMINAL = {"CERTIFIED_RETURN", "HIGH_B_RETURN_THEN_CERTIFIED", "COVERED", "CLOSED"}


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def key_id(key: Any) -> str:
    return json.dumps(key, separators=(",", ":"))


def main() -> None:
    table = load_json(TABLE)
    if not isinstance(table, dict):
        report = {
            "status": "INCOMPLETE_QUOTIENT_TRANSITION_TABLE",
            "reason": "quotient_transition_table.json missing or invalid",
        }
        with OUT.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print("QUOTIENT TRANSITION TABLE AUDIT")
        print("  Status: INCOMPLETE_QUOTIENT_TRANSITION_TABLE")
        return

    rows = table.get("rows", [])
    row_by_key = {key_id(row.get("key")): row for row in rows}
    missing_representatives = []
    missing_successors = []
    mixed_outcomes = []
    bad_successors = []
    sampled_as_proof = []
    conflicts = []
    still_open = []
    final_b_over = []

    for row in rows:
        key = row.get("key")
        kid = key_id(key)
        classification = row.get("classification")
        outcomes = set(row.get("outcome_classes", []))
        if row.get("representatives_seen", 0) < 1:
            missing_representatives.append({"key": key, "reason": "no exported representative"})
        if len(outcomes) > 1:
            mixed_outcomes.append({"key": key, "outcome_classes": sorted(outcomes)})
        if row.get("sampled") or row.get("sampled_as_proof"):
            sampled_as_proof.append(key)
        if row.get("conflict_count", 0):
            conflicts.append({"key": key, "conflict_count": row.get("conflict_count")})
        if classification == "STILL_OPEN":
            still_open.append(key)
        if row.get("final_B") is not None and int(row["final_B"]) > B_LIMIT:
            final_b_over.append({"key": key, "final_B": row["final_B"]})
        if classification not in TERMINAL:
            successors = row.get("successor_keys", [])
            if not successors:
                missing_successors.append({"key": key, "classification": classification})
            for succ in successors:
                if key_id(succ) not in row_by_key:
                    bad_successors.append({"key": key, "missing_successor": succ})
        if kid not in row_by_key:
            bad_successors.append({"key": key, "reason": "internal key map inconsistency"})

    incomplete = missing_representatives or missing_successors
    fail = mixed_outcomes or conflicts or sampled_as_proof or still_open or final_b_over or bad_successors
    if fail:
        status = "FAIL_QUOTIENT_TRANSITION_TABLE"
    elif incomplete:
        status = "INCOMPLETE_QUOTIENT_TRANSITION_TABLE"
    else:
        status = "PASS_QUOTIENT_TRANSITION_TABLE"

    report = {
        "status": status,
        "plain_truth": (
            "This audits tracked proof-critical quotient keys. Full quotient equivalence still depends on "
            "full_equivalence_proven in quotient_transition_table.json or an external lemma."
        ),
        "proof_critical_keys_checked": len(rows),
        "full_equivalence_proven": table.get("full_equivalence_proven") is True,
        "sampled_as_proof_count": len(sampled_as_proof),
        "conflicts": len(conflicts),
        "still_open": len(still_open),
        "final_B_over_200001": len(final_b_over),
        "mixed_outcome_keys": mixed_outcomes[:50],
        "missing_representative_keys": missing_representatives[:50],
        "missing_successor_keys": missing_successors[:50],
        "bad_successor_keys": bad_successors[:50],
        "sampled_as_proof_keys": sampled_as_proof[:50],
        "conflict_keys": conflicts[:50],
        "still_open_keys": still_open[:50],
        "final_B_over_200001_keys": final_b_over[:50],
        "source_table_summary": {
            "proof_critical_key_count": table.get("proof_critical_key_count"),
            "source_summaries": table.get("source_summaries"),
            "missing_local_representatives": table.get("missing_local_representatives"),
        },
    }
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("QUOTIENT TRANSITION TABLE AUDIT")
    print(f"  Status                    : {status}")
    print(f"  Proof-critical keys       : {len(rows)}")
    print(f"  Missing representatives   : {len(missing_representatives)}")
    print(f"  Missing successors        : {len(missing_successors)}")
    print(f"  Mixed outcomes            : {len(mixed_outcomes)}")
    print(f"  Conflicts                 : {len(conflicts)}")
    print(f"  Still open                : {len(still_open)}")
    print(f"  Final B over {B_LIMIT}    : {len(final_b_over)}")
    print(f"  Sampled as proof          : {len(sampled_as_proof)}")
    print(f"  Report                    : {OUT}")


if __name__ == "__main__":
    main()
