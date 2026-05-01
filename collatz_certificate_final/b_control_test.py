"""
b_control_test.py
=================
Diagnostic B-control analysis for HIGH_B_RETURN frontier states.

Input:
    frontier_return_map_report.json

For each HIGH_B_RETURN record, this script starts at the returned positive-gap
state and follows the exact symbolic danger continuation:

    one-frontier move, then the minimal number of zero-frontier moves needed
    to return to positive gap.

It tracks B = ceil(b / (2^c - 3^o)) using Python integers only.  This is a
diagnostic report, not a proof of global closure.
"""

import json
import os
from collections import Counter

B_LIMIT = 200_001
REPORT_IN = os.environ.get("B_CONTROL_INPUT", "frontier_return_map_report.json")
REPORT_OUT = os.environ.get("B_CONTROL_OUT", "b_control_report.json")
MAX_CHAIN = int(os.environ.get("B_CONTROL_MAX_CHAIN", "64"))
GROW_RUN_THRESHOLD = int(os.environ.get("B_CONTROL_GROW_RUN", "3"))
STABLE_RUN_THRESHOLD = int(os.environ.get("B_CONTROL_STABLE_RUN", "6"))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ceil_div(a, b):
    if b <= 0:
        raise ValueError("ceil_div denominator must be positive")
    return (a + b - 1) // b


def gap(o, c):
    return (1 << c) - (3 ** o)


def B_value(o, c, b):
    g = gap(o, c)
    if g <= 0:
        return None
    return ceil_div(b, g)


def bounded_int(value, max_digits=120):
    text = str(value)
    if len(text) <= max_digits:
        return text
    return {
        "digits": len(text),
        "prefix": text[:60],
        "suffix": text[-60:],
    }


def order_stable(a, b):
    """Same decimal order of magnitude without floating point."""
    return len(str(a)) == len(str(b))


def minimal_positive_zero_return(o, c, b):
    zeros = 0
    g = gap(o, c)
    while g <= 0:
        c += 1
        zeros += 1
        g = gap(o, c)
    return o, c, b, zeros, g, ceil_div(b, g)


def one_then_return(o, c, b):
    old_c = c
    o += 1
    c += 1
    b = 3 * b + (1 << old_c)
    return minimal_positive_zero_return(o, c, b)


def zero_tail_to_limit(o, c, b):
    zeros = 0
    g = gap(o, c)
    B = ceil_div(b, g)
    while B > B_LIMIT:
        c += 1
        zeros += 1
        g = gap(o, c)
        B = ceil_div(b, g)
    return {
        "extra_zeros": zeros,
        "pair": [o, c],
        "gap_bit_length": g.bit_length(),
        "B": B,
    }


def extract_record(rec):
    b = int(rec["formula"]["b"])
    start_o = rec["o"]
    start_c = rec["c"]
    return_o, return_c = rec["return_pair"]
    start_gap = gap(start_o, start_c)
    return_gap = gap(return_o, return_c)
    reported_B = rec["B"]
    exact_B = ceil_div(b, return_gap)
    conflict = None if exact_B == reported_B else "reported B disagrees with exact return gap"
    return {
        "key": rec["key"],
        "parent_key": rec.get("parent_key"),
        "previous_key": rec.get("previous_key"),
        "o": start_o,
        "c": start_c,
        "b": str(b),
        "gap": str(start_gap),
        "B": reported_B,
        "return_time": rec["return_time"],
        "return_pair": rec["return_pair"],
        "return_gap": str(return_gap),
        "frontier_word": rec.get("frontier_word", ""),
        "word_length": rec.get("word_length"),
        "is_all_one": rec.get("is_all_one"),
        "conflict": conflict,
    }


def classify_chain(rec):
    base = extract_record(rec)
    if base["conflict"]:
        return {**base, "classification": "STILL_OPEN", "reason": base["conflict"], "chain": []}

    b = int(base["b"])
    o, c = base["return_pair"]
    current_B = base["B"]
    max_later_B = 0
    saw_drop = False
    saw_stable = False
    grow_run = 0
    stable_run = 0
    chain = []

    zero_tail = zero_tail_to_limit(o, c, b)

    classification = None
    reason = None
    for step in range(1, MAX_CHAIN + 1):
        prev_B = current_B
        o, c, b, zeros, g, current_B = one_then_return(o, c, b)
        max_later_B = max(max_later_B, current_B)
        relation = "drop" if current_B < prev_B else ("grow" if current_B > prev_B else "equal")
        if relation == "drop":
            saw_drop = True
            grow_run = 0
        elif relation == "grow":
            grow_run += 1
        else:
            grow_run = 0

        stable = order_stable(prev_B, current_B)
        if stable:
            saw_stable = True
            stable_run += 1
        else:
            stable_run = 0

        chain.append({
            "step": step,
            "move": "1" + ("0" * min(zeros, 80)),
            "move_truncated": zeros > 80,
            "one_then_zero_count": zeros,
            "pair": [o, c],
            "gap_bit_length": g.bit_length(),
            "B": current_B,
            "relation_to_previous_B": relation,
            "same_decimal_order_as_previous": stable,
        })

        if current_B <= B_LIMIT:
            classification = "B_EVENTUALLY_CERTIFIED"
            reason = "danger one-return chain reaches B <= 200001"
            break
        if grow_run >= GROW_RUN_THRESHOLD:
            classification = "B_GROWS"
            reason = f"B increased for {GROW_RUN_THRESHOLD} consecutive one-return steps"
            break
        if stable_run >= STABLE_RUN_THRESHOLD:
            classification = "B_STABLE"
            reason = f"B stayed in the same decimal order for {STABLE_RUN_THRESHOLD} consecutive one-return steps"
            break

    if classification is None:
        if saw_drop:
            classification = "B_DROPS"
            reason = "B dropped on the tracked chain but did not certify before the local chain cap"
        elif saw_stable:
            classification = "B_STABLE"
            reason = "B stayed within the same decimal order before the local chain cap"
        else:
            classification = "STILL_OPEN"
            reason = "local chain cap reached before classification"

    return {
        **base,
        "classification": classification,
        "reason": reason,
        "start_return_state": {
            "pair": base["return_pair"],
            "gap_bit_length": int(base["return_gap"]).bit_length(),
            "B": base["B"],
        },
        "zero_tail_certification": zero_tail,
        "immediate_zero_drops_B": zero_tail["B"] < base["B"],
        "maps_to_lower_B_family": bool(chain and chain[0]["B"] < base["B"]),
        "first_later_B": chain[0]["B"] if chain else None,
        "max_later_B": max_later_B,
        "chain_length": len(chain),
        "chain": chain,
        "exact_formula": {
            "start_gap": "2^c - 3^o",
            "B": "ceil(b / gap)",
            "zero_move": "(o,c,b) -> (o,c+1,b)",
            "one_move": "(o,c,b) -> (o+1,c+1,3*b+2^c)",
        },
    }


def compact_chain(record):
    return {
        "classification": record["classification"],
        "key": record["key"],
        "return_pair": record["return_pair"],
        "starting_B": record["B"],
        "first_later_B": record.get("first_later_B"),
        "max_later_B": record.get("max_later_B"),
        "chain_length": record.get("chain_length"),
        "zero_tail_certification": record.get("zero_tail_certification"),
        "first_steps": record.get("chain", [])[:4],
        "b": bounded_int(record["b"]),
        "return_gap": bounded_int(record["return_gap"]),
    }


def summarize(records):
    counts = Counter(r["classification"] for r in records)
    examples = {}
    for label in ["B_EVENTUALLY_CERTIFIED", "B_DROPS", "B_STABLE", "B_GROWS", "STILL_OPEN"]:
        item = next((r for r in records if r["classification"] == label), None)
        examples[label] = compact_chain(item) if item else None
    worst = max(records, key=lambda r: r.get("max_later_B", 0), default=None)
    longest = max(records, key=lambda r: r.get("chain_length", 0), default=None)
    return {
        "high_B_states_analyzed": len(records),
        "B_EVENTUALLY_CERTIFIED": counts.get("B_EVENTUALLY_CERTIFIED", 0),
        "B_DROPS": counts.get("B_DROPS", 0),
        "B_STABLE": counts.get("B_STABLE", 0),
        "B_GROWS": counts.get("B_GROWS", 0),
        "STILL_OPEN": counts.get("STILL_OPEN", 0),
        "classification_counts": dict(counts),
        "max_starting_B": max((r["B"] for r in records), default=0),
        "max_later_B": max((r.get("max_later_B", 0) for r in records), default=0),
        "immediate_zero_B_drops": sum(1 for r in records if r.get("immediate_zero_drops_B")),
        "maps_to_lower_B_family": sum(1 for r in records if r.get("maps_to_lower_B_family")),
        "worst_chain": compact_chain(worst) if worst else None,
        "longest_chain": compact_chain(longest) if longest else None,
        "examples": examples,
    }


def main():
    report = load_json(REPORT_IN)
    high_b = [
        rec for rec in report.get("return_records", [])
        if rec.get("classification") == "HIGH_B_RETURN"
    ]
    records = [classify_chain(rec) for rec in high_b]
    summary = summarize(records)
    out = {
        "source": REPORT_IN,
        "method": {
            "diagnostic_not_proof": True,
            "integer_checks_only": True,
            "random_seeds": False,
            "global_caps_increased": False,
            "max_chain": MAX_CHAIN,
            "tracked_chain": "from returned positive-gap state: one-frontier move, then minimal zero-return to positive gap",
        },
        "summary": summary,
        "high_B_chains": records,
        "what_remains_open": [
            "This only diagnoses exported HIGH_B_RETURN states from the current report.",
            "It does not prove that arbitrary continuations must follow the tracked lower-B return chain.",
            "No global Collatz proof is claimed.",
        ],
    }
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("=" * 78)
    print("B CONTROL TEST")
    print("=" * 78)
    print(f"High-B states analyzed       : {summary['high_B_states_analyzed']:,}")
    print(f"B_EVENTUALLY_CERTIFIED count : {summary['B_EVENTUALLY_CERTIFIED']:,}")
    print(f"B_DROPS count                : {summary['B_DROPS']:,}")
    print(f"B_STABLE count               : {summary['B_STABLE']:,}")
    print(f"B_GROWS count                : {summary['B_GROWS']:,}")
    print(f"STILL_OPEN count             : {summary['STILL_OPEN']:,}")
    print(f"Max starting B               : {summary['max_starting_B']:,}")
    print(f"Max later B                  : {summary['max_later_B']:,}")
    if summary["worst_chain"]:
        w = summary["worst_chain"]
        print(f"Worst chain                  : key={w['key']} start_B={w['starting_B']:,} max_later_B={w['max_later_B']:,}")
    if summary["longest_chain"]:
        l = summary["longest_chain"]
        print(f"Longest chain                : key={l['key']} length={l['chain_length']}")
    print("Examples:")
    for label, example in summary["examples"].items():
        if example:
            print(f"  {label}: key={example['key']} start_B={example['starting_B']} first_later_B={example['first_later_B']}")
        else:
            print(f"  {label}: none")
    print(f"Report                       : {REPORT_OUT}")


if __name__ == "__main__":
    main()
