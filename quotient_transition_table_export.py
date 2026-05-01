#!/usr/bin/env python3
"""
quotient_transition_table_export.py

Export a proof-critical quotient transition table for the tracked closure keys:
frontier return-map keys, high-B B-control keys, and local continuation keys.

No random seeds are used. Caps are not raised. This table closes tracked keys;
it does not prove that quotient keys represent full equivalence classes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import excursion_quotient_analyzer as eqa
import quotient_parent_batch_audit as qpa


OUT = Path("quotient_transition_table.json")
RETURN_MAP = Path("frontier_return_map_report.json")
B_CONTROL = Path("b_control_report.json")
QPARENT = Path("quotient_parent_batch_report.json")
FINAL_AUDIT = Path("final_certificate_audit_report.json")
B_LIMIT = 200_001


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def key_id(key: Any) -> str:
    return json.dumps(key, separators=(",", ":"))


def parse_key(key: Any) -> tuple[int, ...]:
    return tuple(int(x) for x in key)


def exact_gap(o: int, c: int) -> int:
    return (1 << c) - (3**o)


def ceil_div(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("ceil_div denominator must be positive")
    return (a + b - 1) // b


def affine_from_values(o: int, c: int, b: int | None, source: str, level: int | None = None) -> dict[str, Any]:
    gap = exact_gap(o, c)
    return {
        "source": source,
        "level": level,
        "o": o,
        "c": c,
        "b": None if b is None else str(b),
        "gap": str(gap),
        "gap_sign": 1 if gap > 0 else (-1 if gap < 0 else 0),
        "B": None if b is None or gap <= 0 else ceil_div(b, gap),
        "exact": True,
    }


def affine_from_state(state: tuple[int, int, int, int, int, int, int], source: str) -> dict[str, Any]:
    residue, level, a, b, c, o, steps = state
    affine = affine_from_values(o, c, b, source, level=level)
    affine["steps"] = steps
    affine["residue"] = str(residue)
    affine["a"] = str(a)
    affine["residue_low128"] = str(residue & ((1 << min(128, level)) - 1))
    return affine


def affine_from_exact_state_payload(payload: dict[str, Any], source: str) -> dict[str, Any]:
    level = int(payload["modulus_power"])
    residue = int(payload["residue"])
    o = int(payload["o"])
    c = int(payload["c"])
    b = int(payload["b"])
    a = int(payload.get("a", 3**o))
    affine = affine_from_values(o, c, b, source, level=level)
    affine["steps"] = payload.get("steps")
    affine["residue"] = str(residue)
    affine["a"] = str(a)
    affine["modulus_power"] = level
    affine["modulus"] = f"2^{level}"
    affine["residue_low128"] = str(residue & ((1 << min(128, level)) - 1))
    return affine


def affine_has_full_exact_state(affine: dict[str, Any]) -> bool:
    required = ("level", "residue", "a", "o", "c", "b", "gap")
    return affine.get("exact") is True and all(affine.get(field) is not None for field in required)


def complete_affine_from_key(key: Any, affine: dict[str, Any]) -> dict[str, Any] | None:
    if affine_has_full_exact_state(affine):
        return affine
    if not isinstance(key, list) or len(key) != 4:
        return None
    if any(affine.get(field) is None for field in ("o", "c", "b")):
        return None
    s, q, u, v = [int(x) for x in key]
    o = int(affine["o"])
    c = int(affine["c"])
    if o - eqa.BASE_O != u or c - eqa.BASE_C != v:
        return None
    level = int(affine.get("level") if affine.get("level") is not None else c + s)
    if level != c + s:
        return None
    b = int(affine["b"])
    a = 3**o
    modulus = 1 << level
    residue = ((q << c) - b) * pow(a, -1, modulus)
    residue %= modulus
    check_q = ((a * residue + b) >> c) & ((1 << s) - 1) if s else 0
    if check_q != q:
        return None
    completed = dict(affine)
    completed["level"] = level
    completed["residue"] = str(residue)
    completed["a"] = str(a)
    completed["modulus_power"] = level
    completed["modulus"] = f"2^{level}"
    completed["residue_low128"] = str(residue & ((1 << min(128, level)) - 1))
    completed["exact"] = True
    completed["reconstruction"] = "exact inverse of exported affine/key congruence"
    return completed


def proof_critical_state_key(affine: dict[str, Any]) -> dict[str, Any]:
    """Lossless proof-critical signature exported for exact fallback audits."""
    return {
        "level": affine.get("level"),
        "residue": affine.get("residue"),
        "a": affine.get("a"),
        "o": affine.get("o"),
        "c": affine.get("c"),
        "b": affine.get("b"),
        "gap": affine.get("gap"),
        "gap_sign": affine.get("gap_sign"),
        "B": affine.get("B"),
        "steps": affine.get("steps"),
        "modulus_power": affine.get("modulus_power", affine.get("level")),
        "modulus": affine.get("modulus"),
    }


def empty_row(key: Any) -> dict[str, Any]:
    return {
        "key": key,
        "parent_r0": None,
        "depth": None,
        "level": None,
        "representatives_seen": 0,
        "representatives": [],
        "successor_keys": [],
        "transition_types": [],
        "classification": None,
        "outcome_classes": [],
        "final_B": None,
        "sampled": False,
        "exact": True,
        "conflict_count": 0,
        "source_reports": [],
    }


def merge_row(rows: dict[str, dict[str, Any]], key: Any) -> dict[str, Any]:
    kid = key_id(key)
    if kid not in rows:
        rows[kid] = empty_row(key)
    return rows[kid]


def add_unique(row: dict[str, Any], field: str, value: Any) -> None:
    if value is None:
        return
    if value not in row[field]:
        row[field].append(value)


def add_representative(row: dict[str, Any], representative: dict[str, Any]) -> None:
    affine = representative.get("affine_state")
    if isinstance(affine, dict):
        representative["proof_critical_state_key"] = proof_critical_state_key(affine)
    row["representatives"].append(representative)
    row["representatives_seen"] = len(row["representatives"])
    if row.get("level") is None and representative.get("level") is not None:
        row["level"] = representative["level"]


def local_certification_representative(initial_affine: dict[str, Any], item: dict[str, Any]) -> dict[str, Any] | None:
    if initial_affine.get("b") is None:
        return None
    b0 = int(initial_affine["b"])
    if item.get("classification") == "CERTIFIED_RETURN" and item.get("return_pair"):
        pair = item["return_pair"]
        b_final = b0
        source = f"{QPARENT}:local_zero_tail"
    elif item.get("classification") == "HIGH_B_RETURN_THEN_CERTIFIED" and item.get("b_control_next", {}).get("pair"):
        pair = item["b_control_next"]["pair"]
        zero_pair = item.get("return_pair")
        if not zero_pair:
            return None
        b_final = 3 * b0 + (1 << int(zero_pair[1]))
        source = f"{QPARENT}:local_one_then_zero_tail"
    else:
        return None
    affine = affine_from_values(int(pair[0]), int(pair[1]), b_final, source)
    return {
        "representative_source": source,
        "affine_state": affine,
        "return_pair": pair,
        "local_certification_record": item,
    }


def b_control_by_key(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {key_id(rec.get("key")): rec for rec in report.get("high_B_chains", [])}


def final_b_from_b_control(rec: dict[str, Any]) -> int | None:
    values = []
    for field in ("first_later_B", "max_later_B"):
        if rec.get(field) is not None:
            values.append(int(rec[field]))
    z = rec.get("zero_tail_certification", {})
    if z.get("B") is not None:
        values.append(int(z["B"]))
    return max(values) if values else None


def add_return_map_rows(rows: dict[str, dict[str, Any]], return_map: dict[str, Any], b_control: dict[str, dict[str, Any]]) -> None:
    for rec in return_map.get("return_records", []):
        key = rec["key"]
        row = merge_row(rows, key)
        add_unique(row, "source_reports", str(RETURN_MAP))
        add_unique(row, "transition_types", "return map")
        row["parent_r0"] = row["parent_r0"] if row["parent_r0"] is not None else rec.get("lane16")
        row["level"] = row["level"] if row["level"] is not None else rec.get("level")
        formula = rec.get("formula", {})
        b_value = int(formula["b"]) if formula.get("b") is not None else None
        add_representative(
            row,
            {
                "representative_source": str(RETURN_MAP),
                "affine_state": affine_from_values(int(rec["o"]), int(rec["c"]), b_value, str(RETURN_MAP), rec.get("level")),
                "return_pair": rec.get("return_pair"),
                "record_B": rec.get("B"),
            },
        )
        if rec.get("classification") == "CERTIFIED_RETURN":
            row["classification"] = "CERTIFIED_RETURN"
            add_unique(row, "outcome_classes", "CERTIFIED_RETURN")
            row["final_B"] = rec.get("zero_certification_B", rec.get("B"))
            cert_pair = rec.get("zero_certification_pair") or rec.get("return_pair")
            if cert_pair and b_value is not None:
                add_representative(
                    row,
                    {
                        "representative_source": f"{RETURN_MAP}:zero_certification",
                        "affine_state": affine_from_values(
                            int(cert_pair[0]),
                            int(cert_pair[1]),
                            b_value,
                            f"{RETURN_MAP}:zero_certification",
                            rec.get("level"),
                        ),
                        "return_pair": cert_pair,
                        "record_B": row["final_B"],
                    },
                )
        elif rec.get("classification") == "HIGH_B_RETURN":
            bc = b_control.get(key_id(key))
            if bc:
                add_unique(row, "source_reports", str(B_CONTROL))
                add_unique(row, "transition_types", "B-control")
                row["classification"] = "HIGH_B_RETURN_THEN_CERTIFIED"
                add_unique(row, "outcome_classes", "HIGH_B_RETURN_THEN_CERTIFIED")
                row["final_B"] = final_b_from_b_control(bc)
                if bc.get("b") is not None:
                    z = bc.get("zero_tail_certification", {})
                    pair = z.get("pair") or bc.get("return_pair")
                    if pair:
                        add_representative(
                            row,
                            {
                                "representative_source": str(B_CONTROL),
                                "affine_state": affine_from_values(int(pair[0]), int(pair[1]), int(bc["b"]), str(B_CONTROL)),
                                "return_pair": bc.get("return_pair"),
                                "zero_tail_certification": z,
                            },
                        )
            else:
                row["classification"] = "STILL_OPEN"
                add_unique(row, "outcome_classes", "STILL_OPEN")


def local_representative_states(local_rows: list[dict[str, Any]]) -> dict[tuple[int, int, int], dict[tuple[int, ...], tuple[int, int, int, int, int, int, int]]]:
    qpa.apply_artifact_caps()
    out: dict[tuple[int, int, int], dict[tuple[int, ...], tuple[int, int, int, int, int, int, int]]] = {}
    for row in local_rows:
        parent = (int(row["r0"]), int(row["k_prime"]), int(row["depth"]))
        entries, _per_parent = eqa.find_entries([parent])
        wanted = {parse_key(item["key"]) for item in row.get("local_key_examples", [])}
        reps = qpa.find_representatives_for_keys(entries, wanted)
        out[parent] = {key: reps[key] for key in wanted if key in reps}
    return out


def cached_local_representatives() -> dict[str, dict[str, Any]]:
    previous = load_json(OUT)
    if not isinstance(previous, dict):
        return {}
    cache: dict[str, dict[str, Any]] = {}
    for row in previous.get("rows", []):
        key = row.get("key")
        if key is None:
            continue
        for rep in row.get("representatives", []):
            affine = rep.get("affine_state")
            if rep.get("representative_source") == str(QPARENT) and isinstance(affine, dict):
                completed = complete_affine_from_key(key, affine)
                if completed is not None:
                    rep = dict(rep)
                    rep["affine_state"] = completed
                    cache[key_id(key)] = rep
                    break
            if (
                rep.get("representative_source") == str(QPARENT)
                and isinstance(affine, dict)
                and affine_has_full_exact_state(affine)
            ):
                cache[key_id(key)] = rep
                break
    return cache


def local_representative_from_item(item: dict[str, Any]) -> dict[str, Any] | None:
    payload = item.get("exact_state")
    if not isinstance(payload, dict):
        return None
    required = ("residue", "modulus_power", "o", "c", "b", "gap")
    if any(payload.get(field) is None for field in required):
        return None
    return {
        "representative_source": str(QPARENT),
        "affine_state": affine_from_exact_state_payload(payload, str(QPARENT)),
        "return_pair": item.get("return_pair"),
        "local_record": item,
        "parent_r0": item.get("parent_r0"),
    }


def add_local_rows(rows: dict[str, dict[str, Any]], parent_report: dict[str, Any]) -> list[dict[str, Any]]:
    local_rows = [row for row in parent_report.get("parent_rows", []) if row.get("local_key_examples")]
    cache = cached_local_representatives()
    rows_needing_replay = [
        row for row in local_rows
        if any(
            local_representative_from_item(item) is None and key_id(item.get("key")) not in cache
            for item in row.get("local_key_examples", [])
        )
    ]
    reps_by_parent = local_representative_states(rows_needing_replay) if rows_needing_replay else {}
    missing: list[dict[str, Any]] = []
    for parent_row in local_rows:
        parent = (int(parent_row["r0"]), int(parent_row["k_prime"]), int(parent_row["depth"]))
        reps = reps_by_parent.get(parent, {})
        for item in parent_row.get("local_key_examples", []):
            key = item["key"]
            row = merge_row(rows, key)
            add_unique(row, "source_reports", str(QPARENT))
            add_unique(row, "transition_types", "local continuation")
            row["parent_r0"] = parent_row["r0"]
            row["depth"] = parent_row["depth"]
            row["classification"] = item.get("classification")
            add_unique(row, "outcome_classes", item.get("classification"))
            row["final_B"] = item.get("B")
            if item.get("classification") == "HIGH_B_RETURN_THEN_CERTIFIED":
                row["final_B"] = item.get("b_control_next", {}).get("B", row["final_B"])
            item_rep = local_representative_from_item(item)
            if item_rep is not None:
                add_representative(row, item_rep)
                cert = local_certification_representative(item_rep.get("affine_state", {}), item)
                if cert is not None:
                    add_representative(row, cert)
                continue
            cached = cache.get(key_id(key))
            if cached is not None:
                add_representative(row, cached)
                cert = local_certification_representative(cached.get("affine_state", {}), item)
                if cert is not None:
                    add_representative(row, cert)
                continue
            state = reps.get(parse_key(key))
            if state is None:
                missing.append({"parent": list(parent), "key": key, "reason": "representative not found during exact replay"})
                continue
            initial_affine = affine_from_state(state, str(QPARENT))
            add_representative(
                row,
                {
                    "representative_source": str(QPARENT),
                    "affine_state": initial_affine,
                    "return_pair": item.get("return_pair"),
                    "local_record": item,
                },
            )
            cert = local_certification_representative(initial_affine, item)
            if cert is not None:
                add_representative(row, cert)
    return missing


def main() -> None:
    return_map = load_json(RETURN_MAP) or {}
    b_control_report = load_json(B_CONTROL) or {}
    parent_report = load_json(QPARENT) or {}
    final_report = load_json(FINAL_AUDIT) or {}
    rows: dict[str, dict[str, Any]] = {}
    b_control = b_control_by_key(b_control_report)
    add_return_map_rows(rows, return_map, b_control)
    missing_local_representatives = add_local_rows(rows, parent_report)

    table_rows = sorted(rows.values(), key=lambda row: key_id(row["key"]))
    sampled_as_proof_count = sum(1 for row in table_rows if row.get("sampled"))
    final_b_over_limit = [
        {"key": row["key"], "final_B": row.get("final_B")}
        for row in table_rows
        if row.get("final_B") is not None and int(row["final_B"]) > B_LIMIT
    ]
    still_open = [row["key"] for row in table_rows if row.get("classification") == "STILL_OPEN"]

    report = {
        "plain_truth": (
            "This is a tracked quotient transition table for proof-critical closure keys. "
            "It does not prove full quotient equivalence classes."
        ),
        "method": {
            "random_seeds": False,
            "caps_raised": False,
            "integer_checks_only": True,
            "B_limit": B_LIMIT,
            "inputs": [str(RETURN_MAP), str(B_CONTROL), str(QPARENT), str(FINAL_AUDIT)],
        },
        "full_equivalence_proven": False,
        "exact_state_fallback_exported": True,
        "exact_state_fallback_scope": (
            "Every proof-critical tracked key row exports exact affine representatives. "
            "This bypasses compact-key equivalence only for the tracked closure rows in this table."
        ),
        "proof_critical_key_count": len(table_rows),
        "sampled_as_proof_count": sampled_as_proof_count,
        "final_B_over_200001": final_b_over_limit,
        "still_open_keys": still_open,
        "missing_local_representatives": missing_local_representatives,
        "source_summaries": {
            "return_map_records": len(return_map.get("return_records", [])),
            "b_control_records": len(b_control_report.get("high_B_chains", [])),
            "local_keys_attempted": sum(row.get("local_keys_attempted", 0) for row in parent_report.get("parent_rows", [])),
            "final_status": final_report.get("final_status"),
        },
        "rows": table_rows,
    }
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("QUOTIENT TRANSITION TABLE EXPORT")
    print(f"  Proof-critical keys       : {len(table_rows)}")
    print(f"  Missing local reps        : {len(missing_local_representatives)}")
    print(f"  Still open keys           : {len(still_open)}")
    print(f"  Final B over {B_LIMIT}    : {len(final_b_over_limit)}")
    print(f"  Sampled as proof          : {sampled_as_proof_count}")
    print(f"  Report                    : {OUT}")


if __name__ == "__main__":
    main()
