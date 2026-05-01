"""
frontier_return_map.py
======================
Exact future return map for exported open affine frontier states.

Input states come from excursion_quotient_report.json.  Each open state carries
an exact affine formula

    T^m(n) = (3^o * n + b) / 2^c

with a reported debt gap 2^c - 3^o <= 0.  From a boundary frontier state, the
symbolic zero successor keeps o and b fixed and increases c by one.  Therefore
the first zero-frontier future state with positive gap is found by exact integer
comparison, with no random seeds and no raised quotient caps.

This is a local return-map report for the exported frontier states.  It does
not prove global Collatz closure.
"""

import json
import os
import re
from collections import Counter

B_LIMIT = 200_001
REPORT_IN = os.environ.get("FRONTIER_RETURN_INPUT", "excursion_quotient_report.json")
AFFINE_REPORT_IN = os.environ.get(
    "FRONTIER_AFFINE_INPUT", "frontier_affine_invariant_report.json"
)
REPORT_OUT = os.environ.get("FRONTIER_RETURN_OUT", "frontier_return_map_report.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def int_field(obj, name, default=0):
    val = obj.get(name, default)
    return int(val) if isinstance(val, str) else val


def ceil_div(a, b):
    if b <= 0:
        raise ValueError("ceil_div denominator must be positive")
    return (a + b - 1) // b


def parse_pair(text):
    nums = re.findall(r"-?\d+", text)
    if len(nums) != 2:
        return None
    return int(nums[0]), int(nums[1])


def pair_key(pair):
    return [int(pair[0]), int(pair[1])]


def bounded_int(value, max_digits=160):
    text = str(value)
    if len(text) <= max_digits:
        return text
    return {
        "digits": len(text),
        "prefix": text[:80],
        "suffix": text[-80:],
    }


def known_closed_pairs(qreport):
    pairs = set()
    for key in qreport.get("return_pairs", {}):
        pair = parse_pair(key)
        if pair:
            pairs.add(pair)
    for item in qreport.get("returned_frontier", []):
        if item.get("B_ok"):
            pairs.add(tuple(item["pair"]))
    return pairs


def first_zero_positive(o, c, b):
    """First all-zero future frontier state with 2^(c+r) > 3^o."""
    three_o = 3 ** o
    r = 0
    two = 1 << c
    while two <= three_o:
        r += 1
        two <<= 1
    gap = two - three_o
    B = ceil_div(b, gap)
    return r, c + r, gap, B


def zero_certification_time(o, c, b, start_r):
    """First all-zero future state with both positive gap and B <= B_LIMIT."""
    three_o = 3 ** o
    r = start_r
    two = 1 << (c + r)
    gap = two - three_o
    B = ceil_div(b, gap)
    while B > B_LIMIT:
        r += 1
        two <<= 1
        gap = two - three_o
        B = ceil_div(b, gap)
    return r, c + r, gap, B


def all_one_future(o, c, b, sample_steps):
    """
    Exact all-1 frontier continuation summary.

    Under repeated one-frontier moves:
      o_t = o + t
      c_t = c + t
      gap_t = 2^t * 2^c - 3^t * 3^o
    so a debt state remains debt for every all-1 future t.
    """
    future_o = o + sample_steps
    future_c = c + sample_steps
    gap_at_sample = (1 << future_c) - (3 ** future_o)
    return {
        "sample_steps": sample_steps,
        "sample_pair": pair_key((future_o, future_c)),
        "sample_gap_sign": 1 if gap_at_sample > 0 else (-1 if gap_at_sample < 0 else 0),
        "sample_gap_abs_bit_length": abs(gap_at_sample).bit_length(),
        "stays_debt_for_all_future_all_ones": (1 << c) < (3 ** o),
        "formula": "gap_t = 2^t*2^c - 3^t*3^o; negative initial gap stays negative on the all-1 branch",
    }


def classify_item(item, closed_pairs):
    affine = item["affine"]
    o = int_field(affine, "o")
    c = int_field(affine, "c")
    a = int_field(affine, "a")
    b = int_field(affine, "b")
    residue = int_field(affine, "residue")
    reported_gap = int_field(affine, "gap")
    word = item.get("accumulated_frontier_word", "")
    key = item["key"]
    pair = tuple(item["pair"])

    conflicts = []
    expected_a = 3 ** o
    if a != expected_a:
        conflicts.append("a != 3^o")
    exact_gap = (1 << c) - expected_a
    if exact_gap != reported_gap:
        conflicts.append("reported gap != 2^c - 3^o")
    if tuple(pair) != (o, c):
        conflicts.append("item pair disagrees with affine (o,c)")
    if affine.get("gap_sign") not in (None, 1 if exact_gap > 0 else (-1 if exact_gap < 0 else 0)):
        conflicts.append("reported gap_sign disagrees with exact gap")

    base = {
        "key": key,
        "pair": pair_key(pair),
        "o": o,
        "c": c,
        "level": item.get("level", affine.get("level")),
        "m": item.get("m"),
        "lane16": item.get("lane16"),
        "parent_key": item.get("parent_key"),
        "previous_key": item.get("previous_key"),
        "word_length": item.get("word_length", len(word)),
        "h": item.get("h", word.count("1")),
        "z": item.get("z", word.count("0")),
        "frontier_word": word,
        "is_all_one": bool(word) and word.count("1") == len(word),
        "longest_run_1": item.get("longest_run_1"),
        "longest_run_0": item.get("longest_run_0"),
        "reason": item.get("reason"),
        "initial_gap_sign": 1 if exact_gap > 0 else (-1 if exact_gap < 0 else 0),
        "initial_gap_abs_bit_length": abs(exact_gap).bit_length(),
        "b_bit_length": b.bit_length(),
        "residue": str(residue),
        "residue_low128": affine.get("residue_low128"),
        "frontier_word_prefix": item.get("frontier_word_prefix", word[:120]),
        "frontier_word_suffix": item.get("frontier_word_suffix", word[-120:]),
    }

    if conflicts:
        return {
            **base,
            "classification": "CONFLICT",
            "conflicts": conflicts,
            "formula": {
                "a": str(a),
                "expected_a": str(expected_a),
                "b": str(b),
                "residue": str(residue),
                "c": c,
                "o": o,
                "reported_gap": str(reported_gap),
                "exact_gap": str(exact_gap),
            },
        }

    if exact_gap > 0:
        B = ceil_div(b, exact_gap)
        status = "CERTIFIED_RETURN" if B <= B_LIMIT else "HIGH_B_RETURN"
        return {
            **base,
            "classification": status,
            "future_word": "",
            "return_time": 0,
            "return_pair": pair_key((o, c)),
            "B": B,
            "gap_bit_length": exact_gap.bit_length(),
            "formula": {"a": str(a), "b": str(b), "c": c, "o": o, "gap": str(exact_gap)},
        }

    r_pos, c_pos, gap_pos, B_pos = first_zero_positive(o, c, b)
    r_cert, c_cert, gap_cert, B_cert = zero_certification_time(o, c, b, r_pos)
    return_pair = (o, c_pos)

    if return_pair in closed_pairs:
        status = "LOWER_FAMILY_MERGE"
    elif B_pos <= B_LIMIT:
        status = "CERTIFIED_RETURN"
    else:
        status = "HIGH_B_RETURN"

    all_one_steps = max(1, item.get("word_length", len(word)))
    return {
        **base,
        "classification": status,
        "future_word": "0" * min(r_pos, 256),
        "future_word_truncated": r_pos > 256,
        "return_time": r_pos,
        "return_pair": pair_key(return_pair),
        "gap_bit_length": gap_pos.bit_length(),
        "B": B_pos,
        "zero_certification_time": r_cert,
        "zero_certification_pair": pair_key((o, c_cert)),
        "zero_certification_B": B_cert,
        "zero_certification_gap_bit_length": gap_cert.bit_length(),
        "maps_to_known_closed_pair": return_pair in closed_pairs,
        "all_one_future": all_one_future(o, c, b, all_one_steps),
        "formula": {
            "T^m(n)": "(3^o*n + b) / 2^c",
            "a": str(a),
            "b": str(b),
            "residue": str(residue),
            "o": o,
            "c": c,
            "initial_gap": str(exact_gap),
            "first_return_gap": str(gap_pos),
            "first_return_B": B_pos,
            "first_return_condition": f"append {r_pos} zero-frontier moves",
        },
    }


def focus_records(records):
    near_1577_2499 = sorted(
        records,
        key=lambda r: abs(r["o"] - 1577) + abs(r["c"] - 2499),
    )[:12]
    near_971_1539 = [
        r for r in records if abs(r["o"] - 971) + abs(r["c"] - 1539) <= 32
    ]
    longest = sorted(records, key=lambda r: r.get("word_length", 0), reverse=True)[:12]
    all_one = [r for r in records if r.get("is_all_one")]
    return {
        "all_one_branch_outcomes": all_one,
        "longest_debt_duration_branches": longest,
        "near_1577_2499": near_1577_2499,
        "near_971_1539": near_971_1539,
        "near_971_1539_count": len(near_971_1539),
    }


def compact_example(record):
    formula = record.get("formula", {})
    return {
        "classification": record["classification"],
        "key": record["key"],
        "pair": record["pair"],
        "return_pair": record.get("return_pair"),
        "return_time": record.get("return_time"),
        "B": record.get("B"),
        "zero_certification_time": record.get("zero_certification_time"),
        "zero_certification_B": record.get("zero_certification_B"),
        "formula": {
            "a": bounded_int(formula.get("a", "")),
            "b": bounded_int(formula.get("b", "")),
            "o": formula.get("o"),
            "c": formula.get("c"),
            "initial_gap": bounded_int(formula.get("initial_gap", formula.get("gap", ""))),
            "first_return_gap": bounded_int(formula.get("first_return_gap", "")),
        },
    }


def summarize(records):
    counts = Counter(r["classification"] for r in records)
    conflicts = [r for r in records if r["classification"] == "CONFLICT"]
    non_conflicts = [r for r in records if r["classification"] != "CONFLICT"]
    all_one = [r for r in non_conflicts if r.get("is_all_one")]
    max_return = max(non_conflicts, key=lambda r: r.get("return_time", -1), default=None)
    max_B = max(non_conflicts, key=lambda r: r.get("B", -1), default=None)
    worst_debt = max(non_conflicts, key=lambda r: r.get("initial_gap_abs_bit_length", -1), default=None)
    certified = [r for r in records if r["classification"] == "CERTIFIED_RETURN"]
    high_b = [r for r in records if r["classification"] == "HIGH_B_RETURN"]
    merges = [r for r in records if r["classification"] == "LOWER_FAMILY_MERGE"]
    still_debt = [r for r in records if r["classification"] == "STILL_DEBT_AT_CAP"]

    examples = []
    for bucket in (certified, high_b, merges, conflicts):
        if bucket:
            examples.append(compact_example(bucket[0]))
    if max_return and max_return not in [e for e in examples]:
        examples.append(compact_example(max_return))
    if max_B:
        examples.append(compact_example(max_B))

    return {
        "open_states_analyzed": len(records),
        "classification_counts": dict(counts),
        "certified_returns": len(certified),
        "high_B_returns": len(high_b),
        "lower_family_merges": len(merges),
        "still_debt_at_cap": len(still_debt),
        "conflicts": len(conflicts),
        "max_return_time": max((r.get("return_time", 0) for r in non_conflicts), default=0),
        "max_B": max((r.get("B", 0) for r in non_conflicts), default=0),
        "worst_debt_start": compact_example(worst_debt) if worst_debt else None,
        "max_return_record": compact_example(max_return) if max_return else None,
        "max_B_record": compact_example(max_B) if max_B else None,
        "all_one_branch_count": len(all_one),
        "all_one_classification_counts": dict(Counter(r["classification"] for r in all_one)),
        "examples_with_exact_formulas": examples[:8],
    }


def main():
    qreport = load_json(REPORT_IN)
    affine_source_exists = os.path.exists(AFFINE_REPORT_IN)
    closed_pairs = known_closed_pairs(qreport)
    open_items = [item for item in qreport.get("open_frontier", []) if "affine" in item]
    records = [classify_item(item, closed_pairs) for item in open_items]
    summary = summarize(records)
    focus = focus_records(records)

    report = {
        "source": REPORT_IN,
        "affine_source_seen": AFFINE_REPORT_IN if affine_source_exists else None,
        "method": {
            "integer_checks_only": True,
            "random_seeds": False,
            "global_caps_increased": False,
            "classification_basis": (
                "The recorded classification uses the first all-zero symbolic future "
                "state with exact positive gap. all_one_future records the exact "
                "debt behavior of the all-1 continuation separately."
            ),
            "frontier_zero_rule": "(o,c,b) -> (o,c+1,b)",
            "frontier_one_rule": "(o,c,b) -> (o+1,c+1,3*b+2^c)",
        },
        "summary": summary,
        "focus": focus,
        "return_records": records,
        "what_is_proven": [
            "Each exported record was checked against a=3^o and gap=2^c-3^o with Python integers.",
            "For each non-conflicting exported debt state, the first all-zero symbolic future state with positive gap was computed exactly.",
            "The all-1 future branch of every exported debt state remains debt by the exact multiplicative gap formula.",
        ],
        "what_remains_open": [
            "This does not prove arbitrary symbolic continuations must choose a certified return branch.",
            "HIGH_B_RETURN records need an additional merge or extra-repayment argument before they become B-limit certificates.",
            "No global Collatz proof is claimed.",
        ],
    }

    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 78)
    print("FRONTIER RETURN MAP")
    print("=" * 78)
    print(f"Open states analyzed     : {summary['open_states_analyzed']:,}")
    print(f"Certified returns        : {summary['certified_returns']:,}")
    print(f"High-B returns           : {summary['high_B_returns']:,}")
    print(f"Lower-family merges      : {summary['lower_family_merges']:,}")
    print(f"Still debt at cap        : {summary['still_debt_at_cap']:,}")
    print(f"Conflicts                : {summary['conflicts']:,}")
    print(f"Max return time          : {summary['max_return_time']:,}")
    print(f"Max B                    : {summary['max_B']:,}")
    if summary["worst_debt_start"]:
        w = summary["worst_debt_start"]
        print(f"Worst debt start         : key={w['key']} pair={w['pair']}")
    print(f"All-1 branch outcomes    : {summary['all_one_classification_counts']}")
    print("Examples with exact formulas:")
    for ex in summary["examples_with_exact_formulas"][:5]:
        print(
            f"  {ex['classification']}: key={ex['key']} pair={ex['pair']} "
            f"return={ex.get('return_pair')} t={ex.get('return_time')} B={ex.get('B')}"
        )
    print(f"Report                   : {REPORT_OUT}")


if __name__ == "__main__":
    main()
