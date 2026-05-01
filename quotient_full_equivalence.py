#!/usr/bin/env python3
"""
quotient_full_equivalence.py

Final quotient full-equivalence audit.

This is a proof-boundary checker. It does not run random seeds, raise caps, or
use sampled evidence as proof. Its job is to decide whether the exported
quotient artifacts prove that every compact quotient key represents a full
proof-critical equivalence class.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


OUT = Path("quotient_full_equivalence_report.json")
LEMMA = Path("QUOTIENT_FULL_EQUIVALENCE_LEMMA.md")
OBSTRUCTION = Path("QUOTIENT_FULL_EQUIVALENCE_OBSTRUCTION.md")
EQA = Path("excursion_quotient_analyzer.py")
TABLE = Path("quotient_transition_table.json")
TRANSITION_AUDIT = Path("quotient_transition_table_audit_report.json")
SCHEMA_REVIEW = Path("quotient_key_schema_review_report.json")
ABSTRACTION = Path("quotient_abstraction_validity_report.json")
EXACT_FALLBACK = Path("quotient_exact_state_fallback_audit_report.json")

BASE_O = 306
BASE_C = 485
B_LIMIT = 200_001

TERMINAL_CERTIFIED = {"CERTIFIED_RETURN"}
B_CONTROLLED = {"HIGH_B_RETURN_THEN_CERTIFIED"}
TERMINAL_OR_CLOSED = TERMINAL_CERTIFIED | B_CONTROLLED | {"COVERED", "CLOSED"}


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def key_id(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=False)


def extract_quotient_key_source() -> str | None:
    if not EQA.exists():
        return None
    text = EQA.read_text(encoding="utf-8")
    match = re.search(r"def quotient_key\(state\):(?P<body>.*?)(?:\n\ndef |\Z)", text, re.S)
    return ("def quotient_key(state):" + match.group("body")).rstrip() if match else None


def is_normal_key(key: Any) -> bool:
    return (
        isinstance(key, list)
        and len(key) == 4
        and all(isinstance(x, int) for x in key)
    )


def affine_matches_row_key(row_key: Any, affine: dict[str, Any]) -> bool:
    if not is_normal_key(row_key):
        return False
    if affine.get("o") is None or affine.get("c") is None:
        return False
    return [
        int(row_key[0]),
        int(row_key[1]),
        int(affine["o"]) - BASE_O,
        int(affine["c"]) - BASE_C,
    ] == row_key


def proof_signature(proof_key: dict[str, Any]) -> dict[str, Any]:
    return {
        "level": proof_key.get("level"),
        "residue": proof_key.get("residue"),
        "a": proof_key.get("a"),
        "o": proof_key.get("o"),
        "c": proof_key.get("c"),
        "b": proof_key.get("b"),
        "gap": proof_key.get("gap"),
        "gap_sign": proof_key.get("gap_sign"),
        "B": proof_key.get("B"),
        "steps": proof_key.get("steps"),
    }


def unique_count(values: list[Any]) -> int:
    return len({key_id(v) for v in values})


def classify_representatives(rows: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts = Counter()
    examples: dict[str, list[dict[str, Any]]] = {
        "equivalent_representatives": [],
        "collapsed_different_states": [],
        "mixed_outcome": [],
        "insufficient_data": [],
    }
    same_key_rep_counts = Counter()
    missing_same_key_fields = Counter()
    exported_same_key_rep_total = 0
    witness_rep_total = 0

    for row in rows:
        key = row.get("key")
        outcomes = sorted(set(row.get("outcome_classes", [])))
        same_key_reps = []
        witness_reps = []

        for rep in row.get("representatives", []):
            affine = rep.get("affine_state") or {}
            if affine_matches_row_key(key, affine):
                same_key_reps.append(rep)
            else:
                witness_reps.append(rep)

        exported_same_key_rep_total += len(same_key_reps)
        witness_rep_total += len(witness_reps)
        same_key_rep_counts[len(same_key_reps)] += 1

        if len(outcomes) > 1:
            class_counts["MIXED_OUTCOME"] += 1
            if len(examples["mixed_outcome"]) < 20:
                examples["mixed_outcome"].append({"key": key, "outcome_classes": outcomes})
            continue

        if not same_key_reps:
            class_counts["INSUFFICIENT_DATA"] += 1
            if len(examples["insufficient_data"]) < 20:
                examples["insufficient_data"].append(
                    {"key": key, "reason": "no exported representative whose (o,c) matches the quotient key"}
                )
            continue

        signatures = []
        missing_fields = set()
        for rep in same_key_reps:
            proof_key = rep.get("proof_critical_state_key")
            if not isinstance(proof_key, dict):
                missing_fields.add("proof_critical_state_key")
                signatures.append({})
                continue
            sig = proof_signature(proof_key)
            signatures.append(sig)
            for field in ("level", "residue", "a", "o", "c", "b", "gap", "gap_sign", "steps"):
                if sig.get(field) is None:
                    missing_fields.add(field)

        for field in missing_fields:
            missing_same_key_fields[field] += 1

        if missing_fields:
            class_counts["INSUFFICIENT_DATA"] += 1
            if len(examples["insufficient_data"]) < 20:
                examples["insufficient_data"].append(
                    {
                        "key": key,
                        "reason": "same-key representatives are not fully exported",
                        "missing_fields": sorted(missing_fields),
                        "same_key_representatives": len(same_key_reps),
                    }
                )
            continue

        if len(same_key_reps) == 1:
            class_counts["EXACT_SINGLETON"] += 1
            continue

        differing_fields = []
        for field in ("level", "residue", "a", "o", "c", "b", "gap", "gap_sign", "B", "steps"):
            if unique_count([sig.get(field) for sig in signatures]) > 1:
                differing_fields.append(field)

        if differing_fields:
            class_counts["COLLAPSED_DIFFERENT_STATES"] += 1
            if len(examples["collapsed_different_states"]) < 20:
                examples["collapsed_different_states"].append(
                    {
                        "key": key,
                        "differing_fields": differing_fields,
                        "same_key_representatives": len(same_key_reps),
                    }
                )
        else:
            class_counts["EQUIVALENT_REPRESENTATIVES"] += 1
            if len(examples["equivalent_representatives"]) < 20:
                examples["equivalent_representatives"].append(
                    {"key": key, "same_key_representatives": len(same_key_reps)}
                )

    return {
        "classification_counts": dict(class_counts),
        "same_key_representative_count_distribution": {
            str(k): v for k, v in sorted(same_key_rep_counts.items())
        },
        "exported_same_key_representatives": exported_same_key_rep_total,
        "certification_or_future_witness_representatives": witness_rep_total,
        "missing_same_key_representative_fields": dict(missing_same_key_fields),
        "examples": examples,
    }


def successor_key_from_compact_key(key: list[int]) -> list[list[int]]:
    """One-step quotient successor formula for normal compact keys."""
    s, q, u, v = [int(x) for x in key]
    if s == 0:
        return [[1, 0, u, v], [1, 1, u, v]]
    if q & 1:
        return [[s, (3 * q + 1) & ((1 << s) - 1), u + 1, v]]
    return [[s - 1, q >> 1, u, v + 1]]


def audit_successors(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_by_key = {key_id(row.get("key")): row for row in rows}
    successor_sets: dict[str, set[str]] = {}
    nondeterministic = []
    missing = []
    terminal_certified = []
    local_continued = []
    b_controlled = []

    for row in rows:
        key = row.get("key")
        kid = key_id(key)
        successors = row.get("successor_keys", [])
        succ_ids = {key_id(s) for s in successors}
        if kid in successor_sets and successor_sets[kid] != succ_ids:
            nondeterministic.append({"key": key, "successor_keys": successors})
        successor_sets[kid] = succ_ids

        classification = row.get("classification")
        transition_types = set(row.get("transition_types", []))
        if classification in TERMINAL_CERTIFIED:
            terminal_certified.append(key)
        if classification in B_CONTROLLED or "B-control" in transition_types:
            b_controlled.append(key)
        if "local continuation" in transition_types:
            local_continued.append(key)

        if classification not in TERMINAL_OR_CLOSED:
            for succ in successors:
                if key_id(succ) not in row_by_key:
                    missing.append({"key": key, "missing_successor": succ})
            if not successors:
                missing.append({"key": key, "reason": "nonterminal row has no successors"})

    theoretical_examples = []
    for row in rows[:20]:
        key = row.get("key")
        if is_normal_key(key):
            theoretical_examples.append({"key": key, "one_step_successor_formula": successor_key_from_compact_key(key)})

    return {
        "keys_checked": len(rows),
        "nondeterministic_successor_keys": nondeterministic[:50],
        "missing_successor_keys": missing[:50],
        "terminal_certified_keys": len(terminal_certified),
        "local_continued_keys": len(local_continued),
        "b_controlled_keys": len(b_controlled),
        "all_exported_rows_are_terminal_or_closed": all(
            row.get("classification") in TERMINAL_OR_CLOSED for row in rows
        ),
        "exported_successor_edges": sum(len(row.get("successor_keys", [])) for row in rows),
        "compact_key_one_step_successor_rule": {
            "determined_by_key": True,
            "even_case": "(s,q,u,v) with s>0 and q even -> (s-1, q/2, u, v+1)",
            "odd_case": "(s,q,u,v) with s>0 and q odd -> (s, (3q+1) mod 2^s, u+1, v)",
            "branch_case": "(0,0,u,v) -> {(1,0,u,v), (1,1,u,v)}",
            "scope": "local quotient stepping only; not terminal certification or B-control outcome",
        },
        "theoretical_successor_examples": theoretical_examples,
    }


def key_definition_report(key_source: str | None) -> dict[str, Any]:
    return {
        "source_file": str(EQA),
        "source": key_source,
        "quotient_key_fields": [
            {
                "field": "s",
                "definition": "s = level - c",
                "meaning": "number of known low bits of the current iterate after division by 2^c",
                "included": True,
            },
            {
                "field": "q",
                "definition": "q = ((a * residue + b) >> c) mod 2^s",
                "meaning": "low-s-bit residue of the current symbolic iterate",
                "included": True,
            },
            {
                "field": "u",
                "definition": "u = o - BASE_O",
                "meaning": "odd-count offset; exact o is recoverable with BASE_O=306",
                "included": True,
            },
            {
                "field": "v",
                "definition": "v = c - BASE_C",
                "meaning": "halving-count offset; exact c is recoverable with BASE_C=485",
                "included": True,
            },
            {
                "field": "needs-branch diagnostic residue",
                "definition": "('needs-branch', level-c, u, v, residue mod 2^KMAX) when c > level",
                "meaning": "diagnostic only; normal tracked keys do not use this shape",
                "included": "diagnostic_only",
            },
        ],
        "proof_critical_variables_included": [
            "known current-iterate low bits q",
            "known low-bit window length s",
            "odd count o via u + BASE_O",
            "halving count c via v + BASE_C",
            "gap sign/magnitude is recomputable from o,c as 2^c - 3^o",
            "one-step local quotient successor rule",
        ],
        "proof_critical_variables_omitted": [
            "exact seed residue r",
            "residue modulus/depth k or level as an independent field",
            "exact affine carry b",
            "b modulo a proof-critical modulus beyond what is compressed into q",
            "coefficient a as an exported exact field in the compact key",
            "frontier word/parity history",
            "return/certification class",
            "final_B / B-control outcome",
        ],
        "b_storage": {
            "in_quotient_key": "not stored exactly and not stored modulo a declared proof-critical modulus",
            "in_exported_representatives": "exact b is exported for tracked representative/witness rows, but that is not part of the quotient key",
        },
        "residue_modulus_storage": {
            "normal_key": "not stored; q is current-iterate residue modulo 2^s, not seed residue/modulus",
            "diagnostic_key": "residue mod 2^KMAX only when c > level",
        },
        "o_c_storage": "stored as offsets u=o-306 and v=c-485",
        "frontier_word_or_parity_state_storage": "not stored in the quotient key",
        "successor_rule_determined_by_key": {
            "local_one_step_quotient_rule": True,
            "certification_or_final_bridge_outcome": False,
        },
    }


def required_state_report() -> dict[str, Any]:
    required = [
        {
            "field": "residue r",
            "reason": "identifies the symbolic residue class and representative branch",
            "in_quotient_key": False,
        },
        {
            "field": "modulus/depth 2^k or exact level",
            "reason": "bounds known parity information and branch frontier",
            "in_quotient_key": "partially: s=level-c is present, exact level is omitted",
        },
        {
            "field": "affine form T^m(n) = (3^o n + b) / 2^c",
            "reason": "determines exact continuation and certification thresholds",
            "in_quotient_key": "partially: o,c are present; exact b and full n/residue are omitted",
        },
        {
            "field": "o",
            "reason": "determines 3^o and gap",
            "in_quotient_key": True,
        },
        {
            "field": "c",
            "reason": "determines 2^c and gap",
            "in_quotient_key": True,
        },
        {
            "field": "b modulo enough power of 2",
            "reason": "needed for future parity beyond the stored q window and for affine carry",
            "in_quotient_key": "only compressed through q for the current low s bits",
        },
        {
            "field": "exact b",
            "reason": "needed for B = ceil(b / (2^c - 3^o)) and final bridge outcome",
            "in_quotient_key": False,
        },
        {
            "field": "gap sign 2^c - 3^o",
            "reason": "decides debt/positive-margin certification cases",
            "in_quotient_key": "recomputable from o,c",
        },
        {
            "field": "current symbolic/parity position",
            "reason": "distinguishes branch frontier/history when certification depends on more than low bits",
            "in_quotient_key": "partially: q,s give the current low-bit window; full history omitted",
        },
        {
            "field": "successor transition rule",
            "reason": "needed for closure",
            "in_quotient_key": "local one-step quotient rule is determined",
        },
        {
            "field": "return/B-control classification",
            "reason": "terminal proof outcome must be identical across representatives",
            "in_quotient_key": False,
        },
    ]
    omitted = [item["field"] for item in required if item["in_quotient_key"] is False]
    partial = [
        item["field"]
        for item in required
        if isinstance(item["in_quotient_key"], str) and item["in_quotient_key"].startswith("partially")
    ]
    return {
        "required_state": required,
        "required_state_vs_quotient_key": {
            "omitted_proof_critical_fields": omitted,
            "partially_represented_fields": partial,
            "comparison_status": "FULL_EQUIVALENCE_NOT_PROVEN",
        },
    }


def write_obstruction(report: dict[str, Any]) -> None:
    text = f"""# Quotient Full-Equivalence Obstruction

Status: `FULL_EQUIVALENCE_NOT_PROVEN`

The compact quotient key used by `excursion_quotient_analyzer.py` is

```text
(s, q, u, v) = (level - c, ((3^o * residue + b) >> c) mod 2^s, o - 306, c - 485)
```

This key determines the local quotient successor rule:

```text
s > 0, q even: (s,q,u,v) -> (s-1, q/2, u, v+1)
s > 0, q odd : (s,q,u,v) -> (s, (3q+1) mod 2^s, u+1, v)
s = 0       : (0,0,u,v) -> {{(1,0,u,v), (1,1,u,v)}}
```

That is not enough for the requested full-equivalence lemma. Terminal
certification depends on the exact affine carry `b` through
`B = ceil(b / (2^c - 3^o))` when the gap is positive. The compact key stores
`o` and `c` via offsets, so the gap is recomputable, but it does not store exact
`b`, a declared sufficient modulus for `b`, exact residue `r`, exact modulus or
depth, or the frontier/parity history.

The exported transition table is a tracked closure table, not a full
representative-class export. It has {report['successor_determinism_test']['keys_checked']} tracked rows, all terminal or closed, and the tracked transition
audit passes. However, every same-key representative row is missing at least
one of the exact representative fields needed for a full class comparison:
`{', '.join(sorted(report['representative_collision_test']['missing_same_key_representative_fields']))}`.

Collision review result:

```json
{json.dumps(report['representative_collision_test']['classification_counts'], indent=2, sort_keys=True)}
```

The obstruction is therefore structural and evidentiary:

1. The key omits proof-critical state (`b`, exact residue/modulus/depth, and
   terminal outcome).
2. The table exports tracked representatives and later certification witnesses,
   not all representatives in each quotient class.
3. No external algebraic lemma is present proving that the omitted fields are
   irrelevant for certification, B-control, or final bridge outcome.

Conclusion: the tracked quotient table remains valid as a tracked exact-state
fallback artifact, but the full quotient-class equivalence lemma is incomplete.
This does not prove Collatz.
"""
    OBSTRUCTION.write_text(text, encoding="utf-8")
    if LEMMA.exists():
        LEMMA.unlink()


def write_lemma(report: dict[str, Any]) -> None:
    text = f"""# Quotient Full-Equivalence Lemma

Status: `PASS`

The current artifacts prove that each quotient key determines proof-critical
future behavior. Checked keys: {report['successor_determinism_test']['keys_checked']}.
"""
    LEMMA.write_text(text, encoding="utf-8")
    if OBSTRUCTION.exists():
        OBSTRUCTION.unlink()


def main() -> None:
    table = load_json(TABLE)
    rows = table.get("rows", []) if isinstance(table, dict) else []
    transition_audit = load_json(TRANSITION_AUDIT) or {}
    schema_review = load_json(SCHEMA_REVIEW) or {}
    abstraction = load_json(ABSTRACTION) or {}
    exact_fallback = load_json(EXACT_FALLBACK) or {}

    key_source = extract_quotient_key_source()
    key_def = key_definition_report(key_source)
    required = required_state_report()
    collision = classify_representatives(rows)
    successor = audit_successors(rows)

    mixed = collision["classification_counts"].get("MIXED_OUTCOME", 0)
    collapsed = collision["classification_counts"].get("COLLAPSED_DIFFERENT_STATES", 0)
    insufficient = collision["classification_counts"].get("INSUFFICIENT_DATA", 0)
    sampled_as_proof = (
        table.get("sampled_as_proof_count", 0)
        if isinstance(table, dict)
        else None
    )
    missing_successors = len(successor["missing_successor_keys"])
    nondeterministic = len(successor["nondeterministic_successor_keys"])

    omitted_fields = required["required_state_vs_quotient_key"]["omitted_proof_critical_fields"]
    full_equivalence_from_sources = (
        isinstance(table, dict)
        and table.get("full_equivalence_proven") is True
        and abstraction.get("full_equivalence_proven") is True
    )

    hard_fail = bool(mixed or nondeterministic or missing_successors or sampled_as_proof)
    incomplete = bool(
        insufficient
        or collapsed
        or omitted_fields
        or not rows
        or not full_equivalence_from_sources
    )

    if hard_fail:
        final_status = "FAIL_FULL_EQUIVALENCE"
    elif incomplete:
        final_status = "FULL_EQUIVALENCE_NOT_PROVEN"
    else:
        final_status = "PASS"

    report = {
        "final_status": final_status,
        "plain_truth": (
            "The tracked quotient transition table passes, but the compact key does not prove full "
            "quotient-class equivalence. The remaining gap is the external lemma that omitted fields "
            "cannot change certification or final bridge outcome."
        ),
        "method": {
            "random_seeds": False,
            "caps_raised": False,
            "sampled_evidence_used_as_proof": False,
            "integer_artifact_review_only": True,
            "inputs": [
                str(EQA),
                str(TABLE),
                str(TRANSITION_AUDIT),
                str(SCHEMA_REVIEW),
                str(ABSTRACTION),
                str(EXACT_FALLBACK),
            ],
        },
        "full_equivalence_proven": final_status == "PASS",
        "requires_external_lemma": final_status != "PASS",
        "tracked_transition_table_status": transition_audit.get("status"),
        "tracked_quotient_table_status": (
            "PASS_TRACKED_QUOTIENT_TRANSITION_TABLE"
            if transition_audit.get("status") == "PASS_QUOTIENT_TRANSITION_TABLE"
            else transition_audit.get("status")
        ),
        "source_full_equivalence_flags": {
            "quotient_transition_table": table.get("full_equivalence_proven") if isinstance(table, dict) else None,
            "quotient_abstraction_validity": abstraction.get("full_equivalence_proven"),
            "quotient_key_schema_review": schema_review.get("full_equivalence_proven"),
            "quotient_exact_state_fallback": exact_fallback.get("full_equivalence_proven"),
        },
        "task_1_quotient_key_definition": key_def,
        "task_2_required_state": required,
        "representative_collision_test": collision,
        "successor_determinism_test": successor,
        "decision": {
            "hard_fail_conditions": {
                "mixed_outcome_keys": mixed,
                "nondeterministic_successor_keys": nondeterministic,
                "missing_successor_keys": missing_successors,
                "sampled_as_proof_count": sampled_as_proof,
            },
            "incomplete_conditions": {
                "insufficient_data_keys": insufficient,
                "collapsed_different_state_keys_without_lemma": collapsed,
                "omitted_proof_critical_key_fields": omitted_fields,
                "source_artifacts_mark_full_equivalence_proven": full_equivalence_from_sources,
            },
            "status_rule_applied": (
                "PASS only if no hard failures, no insufficient/collapsed representative classes, "
                "no omitted proof-critical fields, and source artifacts mark full equivalence proven."
            ),
        },
    }

    write_json(OUT, report)
    if final_status == "PASS":
        write_lemma(report)
    else:
        write_obstruction(report)

    print("QUOTIENT FULL-EQUIVALENCE AUDIT")
    print(f"  Final status              : {final_status}")
    print(f"  Tracked rows checked      : {len(rows)}")
    print(f"  Tracked transition table  : {report['tracked_quotient_table_status']}")
    print(f"  Mixed outcomes            : {mixed}")
    print(f"  Collapsed different states: {collapsed}")
    print(f"  Insufficient data keys    : {insufficient}")
    print(f"  Missing successors        : {missing_successors}")
    print(f"  Report                    : {OUT}")
    print(f"  Obstruction               : {OBSTRUCTION if final_status != 'PASS' else 'not written'}")


if __name__ == "__main__":
    main()
