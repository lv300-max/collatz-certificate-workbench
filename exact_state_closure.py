#!/usr/bin/env python3
"""
exact_state_closure.py

Full-state closure audit for proof-critical tracked states.

This deliberately does not use compact quotient keys as proof.  Each tracked
state must carry its own exact proof-critical data and certify from that data:
residue, modulus/level, o, c, exact b, exact gap, B when applicable,
successor/certification state, terminal outcome, and final_B.

No random seeds are used.  No caps are raised.  Similar-looking states are not
merged unless their full proof-critical state is identical.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


B_LIMIT = 200_001
BASE_O = 306
BASE_C = 485

OUT = Path("exact_state_closure_report.json")
QUOTIENT_TABLE = Path("quotient_transition_table.json")
FRONTIER_RETURN = Path("frontier_return_map_report.json")
EXCURSION_QUOTIENT = Path("excursion_quotient_report.json")
QPARENT = Path("quotient_parent_batch_report.json")


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


def int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def ceil_div(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("ceil_div denominator must be positive")
    return (a + b - 1) // b


def gap(o: int, c: int) -> int:
    return (1 << c) - (3**o)


def sign(value: int) -> int:
    return 1 if value > 0 else (-1 if value < 0 else 0)


def compact_int(value: int | str | None, max_digits: int = 120) -> Any:
    if value is None:
        return None
    text = str(value)
    if len(text) <= max_digits:
        return text
    return {"digits": len(text), "prefix": text[:60], "suffix": text[-60:]}


def full_state_signature(state: dict[str, Any]) -> str | None:
    required = ("residue", "level", "o", "c", "b")
    if any(state.get(name) is None for name in required):
        return None
    return key_id(
        {
            "residue": str(state["residue"]),
            "level": int(state["level"]),
            "o": int(state["o"]),
            "c": int(state["c"]),
            "b": str(state["b"]),
        }
    )


def normal_key_matches_affine(key: Any, affine: dict[str, Any]) -> bool:
    if not isinstance(key, list) or len(key) != 4:
        return False
    if affine.get("o") is None or affine.get("c") is None:
        return False
    return [key[0], key[1], int(affine["o"]) - BASE_O, int(affine["c"]) - BASE_C] == key


def state_from_frontier_return_record(rec: dict[str, Any]) -> dict[str, Any]:
    formula = rec.get("formula") or {}
    residue = rec.get("residue", formula.get("residue"))
    level = rec.get("level")
    o = rec.get("o", formula.get("o"))
    c = rec.get("c", formula.get("c"))
    b = formula.get("b")
    a = formula.get("a")
    return {
        "state_source": str(FRONTIER_RETURN),
        "source_kind": "frontier_return_record",
        "key": rec.get("key"),
        "residue": None if residue is None else str(residue),
        "level": level,
        "modulus": None if level is None else f"2^{int(level)}",
        "o": o,
        "c": c,
        "a": None if a is None else str(a),
        "b": None if b is None else str(b),
        "reported_gap": formula.get("initial_gap"),
        "reported_B": rec.get("B"),
        "reported_classification": rec.get("classification"),
        "reported_final_B": rec.get("zero_certification_B", rec.get("B")),
        "return_pair": rec.get("return_pair"),
        "m": rec.get("m"),
        "terminal_hint": rec.get("classification"),
    }


def state_from_excursion_item(item: dict[str, Any]) -> dict[str, Any]:
    affine = item.get("affine") or {}
    level = affine.get("level", item.get("level"))
    return {
        "state_source": str(EXCURSION_QUOTIENT),
        "source_kind": "excursion_frontier_state",
        "key": item.get("key"),
        "residue": None if affine.get("residue") is None else str(affine.get("residue")),
        "level": level,
        "modulus": None if level is None else f"2^{int(level)}",
        "o": affine.get("o", item.get("o")),
        "c": affine.get("c", item.get("c")),
        "a": None if affine.get("a") is None else str(affine.get("a")),
        "b": None if affine.get("b") is None else str(affine.get("b")),
        "reported_gap": affine.get("gap"),
        "reported_B": affine.get("exact_B", item.get("B")),
        "reported_classification": None,
        "reported_final_B": None,
        "return_pair": None,
        "m": item.get("m"),
        "terminal_hint": item.get("reason"),
    }


def state_from_transition_row(row: dict[str, Any]) -> dict[str, Any]:
    same_key_reps = []
    for rep in row.get("representatives", []):
        affine = rep.get("affine_state") or {}
        if normal_key_matches_affine(row.get("key"), affine):
            same_key_reps.append(rep)

    rep = same_key_reps[0] if same_key_reps else {}
    affine = rep.get("affine_state") or {}
    local_record = rep.get("local_record") if isinstance(rep.get("local_record"), dict) else None
    level = affine.get("level", row.get("level"))
    return {
        "state_source": str(QUOTIENT_TABLE),
        "source_kind": "quotient_transition_row",
        "key": row.get("key"),
        "residue": None if affine.get("residue") is None else str(affine.get("residue")),
        "level": level,
        "modulus": None if level is None else f"2^{int(level)}",
        "o": affine.get("o"),
        "c": affine.get("c"),
        "a": None if affine.get("a") is None else str(affine.get("a")),
        "b": None if affine.get("b") is None else str(affine.get("b")),
        "reported_gap": affine.get("gap"),
        "reported_B": affine.get("B", row.get("final_B")),
        "reported_classification": row.get("classification"),
        "reported_final_B": row.get("final_B"),
        "return_pair": rep.get("return_pair"),
        "m": affine.get("steps"),
        "terminal_hint": row.get("classification"),
        "same_key_representatives_seen": len(same_key_reps),
        "local_record": local_record,
    }


def state_from_parent_witness(parent_row: dict[str, Any], witness: dict[str, Any]) -> dict[str, Any]:
    exact_state = witness.get("exact_state") if isinstance(witness.get("exact_state"), dict) else {}
    level = exact_state.get("modulus_power", exact_state.get("k"))
    return {
        "state_source": str(QPARENT),
        "source_kind": "closed_by_quotient_parent_witness",
        "coverage_source": witness.get("coverage_source"),
        "parent_r0": witness.get("parent_r0", parent_row.get("r0")),
        "parent_k_prime": witness.get("parent_k_prime", parent_row.get("k_prime")),
        "parent_depth": witness.get("parent_depth", parent_row.get("depth")),
        "parent_witness_id": witness.get("witness_id"),
        "key": witness.get("key"),
        "residue": None if exact_state.get("residue") is None else str(exact_state.get("residue")),
        "level": level,
        "modulus": None if level is None else f"2^{int(level)}",
        "o": exact_state.get("o"),
        "c": exact_state.get("c"),
        "a": None if exact_state.get("a") is None else str(exact_state.get("a")),
        "b": None if exact_state.get("b") is None else str(exact_state.get("b")),
        "reported_gap": exact_state.get("gap"),
        "reported_B": exact_state.get("B"),
        "reported_classification": witness.get("classification"),
        "reported_final_B": witness.get("final_B"),
        "return_pair": witness.get("return_pair"),
        "m": exact_state.get("steps"),
        "terminal_hint": witness.get("classification"),
        "local_record": witness,
    }


def build_full_state_indexes() -> dict[str, dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}

    return_map = load_json(FRONTIER_RETURN) or {}
    for rec in return_map.get("return_records", []):
        state = state_from_frontier_return_record(rec)
        if state.get("key") is not None:
            by_key[key_id(state["key"])] = state

    # Fallback only. The return-map records are preferred because they include
    # the terminal return classification and final B fields.
    qreport = load_json(EXCURSION_QUOTIENT) or {}
    for section in ("open_frontier", "returned_frontier"):
        for item in qreport.get(section, []):
            state = state_from_excursion_item(item)
            if state.get("key") is not None:
                by_key.setdefault(key_id(state["key"]), state)

    return by_key


def tracked_states() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    table = load_json(QUOTIENT_TABLE)
    if not isinstance(table, dict):
        return [], {"missing": str(QUOTIENT_TABLE)}

    full_by_key = build_full_state_indexes()
    states = []
    source_counts = Counter()
    full_state_seen: set[str] = set()

    for row in table.get("rows", []):
        key = row.get("key")
        source = full_by_key.get(key_id(key))
        if source is None:
            source = state_from_transition_row(row)
        else:
            source = {**source, "quotient_table_classification": row.get("classification")}

        signature = full_state_signature(source)
        if signature is not None:
            if signature in full_state_seen:
                continue
            full_state_seen.add(signature)

        states.append(source)
        source_counts[source.get("source_kind", "unknown")] += 1

    parent_report = load_json(QPARENT) or {}
    parent_witness_count = 0
    for parent_row in parent_report.get("parent_rows", []):
        for witness in parent_row.get("exact_closure_witnesses", []):
            source = state_from_parent_witness(parent_row, witness)
            signature = full_state_signature(source)
            if signature is not None:
                if signature in full_state_seen:
                    continue
                full_state_seen.add(signature)
            states.append(source)
            parent_witness_count += 1
            source_counts[source.get("source_kind", "unknown")] += 1

    return states, {
        "quotient_table_rows": len(table.get("rows", [])),
        "full_state_indexed_keys": len(full_by_key),
        "parent_exact_closure_witnesses": parent_witness_count,
        "states_after_identical_full_state_dedup": len(states),
        "state_source_counts": dict(source_counts),
    }


def validate_state(state: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    missing = [
        name
        for name in ("residue", "level", "modulus", "o", "c", "b")
        if state.get(name) is None
    ]
    conflicts = []
    if missing:
        return missing, conflicts

    o = int(state["o"])
    c = int(state["c"])
    b = int(state["b"])
    g = gap(o, c)

    reported_gap = state.get("reported_gap")
    if reported_gap is not None and int(reported_gap) != g:
        conflicts.append(
            {
                "kind": "gap_mismatch",
                "reported_gap": compact_int(reported_gap),
                "computed_gap": compact_int(g),
            }
        )

    reported_a = state.get("a")
    if reported_a is not None and int(reported_a) != 3**o:
        conflicts.append(
            {
                "kind": "a_mismatch",
                "reported_a": compact_int(reported_a),
                "computed_a": compact_int(3**o),
            }
        )

    if g > 0:
        computed_B = ceil_div(b, g)
        reported_B = state.get("reported_B")
        if reported_B is not None and int(reported_B) != computed_B:
            # A transition-table row may store final_B after extra zero tail,
            # so only mark a mismatch when the source is a direct exact state.
            if state.get("source_kind") != "quotient_transition_row":
                conflicts.append(
                    {
                        "kind": "B_mismatch",
                        "reported_B": reported_B,
                        "computed_B": computed_B,
                    }
                )

    return missing, conflicts


def zero_tail_to_limit(o: int, c: int, b: int) -> dict[str, Any]:
    zeros_to_positive = 0
    g = gap(o, c)
    while g <= 0:
        c += 1
        zeros_to_positive += 1
        g = gap(o, c)

    first_positive_c = c
    first_positive_gap = g
    first_positive_B = ceil_div(b, g)

    extra_zeros_to_limit = 0
    final_B = first_positive_B
    while final_B > B_LIMIT:
        c += 1
        extra_zeros_to_limit += 1
        g = gap(o, c)
        final_B = ceil_div(b, g)

    return {
        "successor_rule": "exact zero-tail continuation from full affine state",
        "zeros_to_positive_gap": zeros_to_positive,
        "first_positive_state": {
            "o": o,
            "c": first_positive_c,
            "gap": compact_int(first_positive_gap),
            "B": first_positive_B,
        },
        "extra_zeros_to_B_limit": extra_zeros_to_limit,
        "terminal_state": {
            "o": o,
            "c": c,
            "gap": compact_int(g),
            "B": final_B,
        },
        "terminal_outcome": (
            "CERTIFIED_RETURN" if first_positive_B <= B_LIMIT else "HIGH_B_THEN_CERTIFIED"
        ),
        "final_B": final_B,
    }


def zero_tail_lifted_residue(state: dict[str, Any], zeros: int) -> dict[str, Any]:
    """Lift residue bits for an exact all-zero local continuation."""
    residue = int(state["residue"])
    level = int(state["level"])
    o = int(state["o"])
    c = int(state["c"])
    b = int(state["b"])
    a = 3**o
    chosen_bits = []

    for _ in range(zeros):
        if c > level:
            return {
                "available": False,
                "reason": "cannot choose a zero successor when c > level without more exported residue bits",
                "residue": compact_int(residue),
                "level": level,
                "c": c,
            }
        if c == level:
            parity_without_new_bit = ((a * residue + b) >> c) & 1
            chosen_bit = parity_without_new_bit
            residue += chosen_bit << level
            level += 1
            chosen_bits.append(chosen_bit)
        else:
            parity = ((a * residue + b) >> c) & 1
            if parity != 0:
                return {
                    "available": False,
                    "reason": "requested zero-tail continuation conflicts with known odd parity",
                    "residue": compact_int(residue),
                    "level": level,
                    "c": c,
                }
        c += 1

    g = gap(o, c)
    return {
        "available": True,
        "residue": compact_int(residue),
        "level": level,
        "modulus": f"2^{level}",
        "o": o,
        "c": c,
        "b": compact_int(b),
        "gap": compact_int(g),
        "gap_sign": sign(g),
        "B": ceil_div(b, g) if g > 0 else None,
        "chosen_zero_tail_bits_prefix": "".join(str(x) for x in chosen_bits[:120]),
        "chosen_zero_tail_bits_suffix": "".join(str(x) for x in chosen_bits[-120:]),
        "chosen_zero_tail_bits_length": len(chosen_bits),
    }


def exact_state_numbers(state: dict[str, Any]) -> dict[str, int]:
    o = int(state["o"])
    return {
        "residue": int(state["residue"]),
        "level": int(state["level"]),
        "a": int(state.get("a") or 3**o),
        "b": int(state["b"]),
        "c": int(state["c"]),
        "o": o,
    }


def apply_exact_move(cur: dict[str, int], move: str) -> tuple[dict[str, int] | None, dict[str, Any] | None]:
    if move not in {"0", "1"}:
        return None, {"kind": "invalid_move", "move": move}

    residue = cur["residue"]
    level = cur["level"]
    a = cur["a"]
    b = cur["b"]
    c = cur["c"]

    if c > level:
        return None, {
            "kind": "insufficient_residue_depth",
            "level": level,
            "c": c,
            "move": move,
        }
    if c == level:
        base_parity = ((a * residue + b) >> c) & 1
        chosen_bit = base_parity ^ int(move)
        residue += chosen_bit << level
        level += 1
    else:
        parity = ((a * residue + b) >> c) & 1
        if parity != int(move):
            return None, {
                "kind": "known_parity_conflict",
                "expected_move": move,
                "actual_parity": parity,
                "level": level,
                "c": c,
            }

    if move == "0":
        c += 1
        return {**cur, "residue": residue, "level": level, "c": c}, None

    old_c = c
    return {
        **cur,
        "residue": residue,
        "level": level,
        "a": 3 * a,
        "b": 3 * b + (1 << old_c),
        "o": cur["o"] + 1,
    }, None


def apply_exact_moves(state: dict[str, Any], moves: str) -> tuple[dict[str, int] | None, dict[str, Any] | None]:
    cur = exact_state_numbers(state)
    for index, move in enumerate(moves):
        cur, conflict = apply_exact_move(cur, move)
        if conflict is not None:
            conflict["move_index"] = index
            return None, conflict
    return cur, None


def compact_state(cur: dict[str, int]) -> dict[str, Any]:
    g = gap(cur["o"], cur["c"])
    return {
        "residue": compact_int(cur["residue"]),
        "level": cur["level"],
        "modulus": f"2^{cur['level']}",
        "o": cur["o"],
        "c": cur["c"],
        "a": compact_int(cur["a"]),
        "b": compact_int(cur["b"]),
        "gap": compact_int(g),
        "gap_sign": sign(g),
        "B": ceil_div(cur["b"], g) if g > 0 else None,
    }


def local_first_return_moves(local_record: dict[str, Any]) -> str:
    prefix = local_record.get("prefix", "")
    zeros = int(local_record.get("zeros", 0) or 0)
    if local_record.get("prefix_truncated") and zeros > 0:
        shown_zero_tail = min(zeros, 96)
        deterministic_prefix = prefix[:-shown_zero_tail] if shown_zero_tail else prefix
        return deterministic_prefix + ("0" * zeros)
    return prefix


def certify_local_record_state(base: dict[str, Any], state: dict[str, Any], local_record: dict[str, Any]) -> dict[str, Any]:
    moves = local_first_return_moves(local_record)
    first_return, conflict = apply_exact_moves(state, moves)
    if conflict is not None:
        return {
            **base,
            "classification": "CONFLICT",
            "conflicts": [{"kind": "local_prefix_conflict", "detail": conflict}],
            "terminal_outcome": None,
            "final_B": None,
        }

    return_pair = local_record.get("return_pair")
    if return_pair and [first_return["o"], first_return["c"]] != [int(return_pair[0]), int(return_pair[1])]:
        return {
            **base,
            "classification": "CONFLICT",
            "conflicts": [
                {
                    "kind": "local_return_pair_mismatch",
                    "computed_pair": [first_return["o"], first_return["c"]],
                    "reported_pair": return_pair,
                }
            ],
            "terminal_outcome": None,
            "final_B": None,
        }

    first_gap = gap(first_return["o"], first_return["c"])
    if first_gap <= 0:
        return {
            **base,
            "classification": "CONFLICT",
            "conflicts": [{"kind": "local_return_gap_not_positive", "gap": compact_int(first_gap)}],
            "terminal_outcome": None,
            "final_B": None,
        }
    first_B = ceil_div(first_return["b"], first_gap)

    if local_record.get("classification") == "CERTIFIED_RETURN":
        if first_B > B_LIMIT:
            return {
                **base,
                "classification": "STILL_OPEN",
                "terminal_outcome": None,
                "final_B": first_B,
            }
        return {
            **base,
            "classification": "CERTIFIED_RETURN",
            "initial_gap": compact_int(gap(int(state["o"]), int(state["c"]))),
            "initial_gap_sign": sign(gap(int(state["o"]), int(state["c"]))),
            "successor_state": compact_state(first_return),
            "local_continuation": {
                "successor_rule": "exact exported local prefix from full affine state",
                "moves_prefix": moves[:160],
                "moves_truncated": len(moves) > 160,
                "moves_length": len(moves),
                "first_positive_state": compact_state(first_return),
                "terminal_state": compact_state(first_return),
                "terminal_outcome": "CERTIFIED_RETURN",
                "final_B": first_B,
            },
            "terminal_outcome": "CERTIFIED_RETURN",
            "terminal_state": compact_state(first_return),
            "final_B": first_B,
        }

    next_ret = local_record.get("b_control_next") or {}
    zeros_after_one = int(next_ret.get("zeros_after_one", 0) or 0)
    b_control_moves = "10" + ("0" * zeros_after_one)
    b_control_state, conflict = apply_exact_moves(
        {
            "residue": str(first_return["residue"]),
            "level": first_return["level"],
            "o": first_return["o"],
            "c": first_return["c"],
            "b": str(first_return["b"]),
            "a": str(first_return["a"]),
        },
        b_control_moves,
    )
    if conflict is not None:
        return {
            **base,
            "classification": "CONFLICT",
            "conflicts": [{"kind": "local_b_control_conflict", "detail": conflict}],
            "terminal_outcome": None,
            "final_B": None,
        }
    final_gap = gap(b_control_state["o"], b_control_state["c"])
    final_B = ceil_div(b_control_state["b"], final_gap) if final_gap > 0 else None
    if next_ret.get("pair") and [b_control_state["o"], b_control_state["c"]] != [
        int(next_ret["pair"][0]),
        int(next_ret["pair"][1]),
    ]:
        return {
            **base,
            "classification": "CONFLICT",
            "conflicts": [
                {
                    "kind": "local_b_control_pair_mismatch",
                    "computed_pair": [b_control_state["o"], b_control_state["c"]],
                    "reported_pair": next_ret.get("pair"),
                }
            ],
            "terminal_outcome": None,
            "final_B": None,
        }
    if final_B is None or final_B > B_LIMIT:
        return {
            **base,
            "classification": "STILL_OPEN",
            "terminal_outcome": None,
            "final_B": final_B,
        }
    return {
        **base,
        "classification": "HIGH_B_THEN_CERTIFIED",
        "initial_gap": compact_int(gap(int(state["o"]), int(state["c"]))),
        "initial_gap_sign": sign(gap(int(state["o"]), int(state["c"]))),
        "successor_state": compact_state(first_return),
        "local_continuation": {
            "successor_rule": "exact exported local prefix plus exact one-then-zero B-control",
            "first_return_moves_prefix": moves[:160],
            "first_return_moves_truncated": len(moves) > 160,
            "first_return_moves_length": len(moves),
            "first_positive_state": compact_state(first_return),
            "b_control_moves_prefix": b_control_moves[:160],
            "b_control_moves_truncated": len(b_control_moves) > 160,
            "b_control_moves_length": len(b_control_moves),
            "terminal_state": compact_state(b_control_state),
            "terminal_outcome": "HIGH_B_THEN_CERTIFIED",
            "final_B": final_B,
        },
        "terminal_outcome": "HIGH_B_THEN_CERTIFIED",
        "terminal_state": compact_state(b_control_state),
        "final_B": final_B,
    }


def certify_state(state: dict[str, Any]) -> dict[str, Any]:
    missing, conflicts = validate_state(state)
    base = {
        "key": state.get("key"),
        "state_source": state.get("state_source"),
        "source_kind": state.get("source_kind"),
        "coverage_source": state.get("coverage_source"),
        "parent_r0": state.get("parent_r0"),
        "parent_k_prime": state.get("parent_k_prime"),
        "parent_depth": state.get("parent_depth"),
        "parent_witness_id": state.get("parent_witness_id"),
        "residue": compact_int(state.get("residue")),
        "level": state.get("level"),
        "modulus": state.get("modulus"),
        "o": state.get("o"),
        "c": state.get("c"),
        "b": compact_int(state.get("b")),
        "reported_classification": state.get("reported_classification"),
        "reported_final_B": state.get("reported_final_B"),
    }
    if missing:
        return {
            **base,
            "classification": "MISSING_EXACT_STATE_FIELDS",
            "missing_fields": missing,
            "terminal_outcome": None,
            "final_B": None,
        }
    if conflicts:
        return {
            **base,
            "classification": "CONFLICT",
            "conflicts": conflicts,
            "terminal_outcome": None,
            "final_B": None,
        }

    local_record = state.get("local_record")
    if isinstance(local_record, dict):
        return certify_local_record_state(base, state, local_record)

    o = int(state["o"])
    c = int(state["c"])
    b = int(state["b"])
    g = gap(o, c)
    initial_B = ceil_div(b, g) if g > 0 else None
    closure = zero_tail_to_limit(o, c, b)
    terminal = closure["terminal_state"]
    total_zero_tail = (
        int(closure["zeros_to_positive_gap"]) + int(closure["extra_zeros_to_B_limit"])
    )
    lifted_successor = zero_tail_lifted_residue(state, total_zero_tail)
    if not lifted_successor.get("available"):
        return {
            **base,
            "classification": "CONFLICT",
            "conflicts": [
                {
                    "kind": "successor_state_unavailable",
                    "detail": lifted_successor,
                }
            ],
            "terminal_outcome": None,
            "final_B": None,
        }

    return {
        **base,
        "classification": closure["terminal_outcome"],
        "initial_gap": compact_int(g),
        "initial_gap_sign": sign(g),
        "initial_B": initial_B,
        "B_when_gap_positive": initial_B,
        "successor_state": lifted_successor,
        "local_continuation": closure,
        "terminal_outcome": closure["terminal_outcome"],
        "terminal_state": terminal,
        "final_B": closure["final_B"],
    }


def main() -> None:
    states, input_summary = tracked_states()
    results = [certify_state(state) for state in states]

    counts = Counter(row["classification"] for row in results)
    missing_rows = [row for row in results if row["classification"] == "MISSING_EXACT_STATE_FIELDS"]
    conflict_rows = [row for row in results if row["classification"] == "CONFLICT"]
    still_open_rows = [row for row in results if row["classification"] == "STILL_OPEN"]
    final_b_values = [int(row["final_B"]) for row in results if row.get("final_B") is not None]
    final_b_over = [row for row in results if row.get("final_B") is not None and int(row["final_B"]) > B_LIMIT]
    missing_field_counts = Counter(field for row in missing_rows for field in row.get("missing_fields", []))

    pass_ok = (
        len(still_open_rows) == 0
        and len(conflict_rows) == 0
        and len(missing_rows) == 0
        and len(final_b_over) == 0
        and len(results) > 0
    )

    report = {
        "status": "PASS_EXACT_STATE_CLOSURE" if pass_ok else "INCOMPLETE_EXACT_STATE_CLOSURE",
        "plain_truth": (
            "This audit does not use quotient keys as proof. It certifies each tracked state only "
            "from exported exact affine data. It is a framework artifact audit and must not be "
            "read as a Collatz proof."
        ),
        "method": {
            "random_seeds": False,
            "caps_raised": False,
            "uses_quotient_key_as_proof": False,
            "merge_rule": "states are deduplicated only by identical full proof-critical state",
            "B_limit": B_LIMIT,
            "inputs": [str(QUOTIENT_TABLE), str(FRONTIER_RETURN), str(EXCURSION_QUOTIENT), str(QPARENT)],
        },
        "input_summary": input_summary,
        "total_states": len(results),
        "certified_states": counts.get("CERTIFIED_RETURN", 0),
        "high_B_then_certified": counts.get("HIGH_B_THEN_CERTIFIED", 0),
        "still_open": len(still_open_rows),
        "conflicts": len(conflict_rows),
        "missing_exact_state_fields": len(missing_rows),
        "missing_exact_state_field_counts": dict(missing_field_counts),
        "max_final_B": max(final_b_values) if final_b_values else None,
        "final_B_over_200001": len(final_b_over),
        "pass_conditions": {
            "still_open_eq_0": len(still_open_rows) == 0,
            "conflicts_eq_0": len(conflict_rows) == 0,
            "missing_exact_state_fields_eq_0": len(missing_rows) == 0,
            "all_final_B_le_200001": len(final_b_over) == 0,
        },
        "full_equivalence_proven": False,
        "collatz_proven": False,
        "missing_exact_state_examples": missing_rows[:30],
        "conflict_examples": conflict_rows[:30],
        "still_open_examples": still_open_rows[:30],
        "final_B_over_200001_examples": final_b_over[:30],
        "result_examples": results[:30],
        "results": results,
    }
    write_json(OUT, report)

    print("EXACT STATE CLOSURE")
    print(f"  Status                    : {report['status']}")
    print(f"  Total states              : {len(results)}")
    print(f"  Certified states          : {report['certified_states']}")
    print(f"  High-B then certified     : {report['high_B_then_certified']}")
    print(f"  Still open                : {report['still_open']}")
    print(f"  Conflicts                 : {report['conflicts']}")
    print(f"  Missing exact state fields: {report['missing_exact_state_fields']}")
    print(f"  Max final_B               : {report['max_final_B']}")
    print(f"  Final B over {B_LIMIT}    : {report['final_B_over_200001']}")
    print(f"  Report                    : {OUT}")


if __name__ == "__main__":
    main()
