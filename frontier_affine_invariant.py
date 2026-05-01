"""
frontier_affine_invariant.py
============================
Analyze the exact affine data behind the open quotient frontier.

The word-only invariant is false: finite all-1 debt words survive to the cap.
This script checks whether the exact affine state gives a stronger obstruction:

    T^m(n) = (3^o n + b) / 2^c
    gap    = 2^c - 3^o
    B      = ceil(b / gap)  when gap > 0

It does not sample random seeds, does not increase caps, and does not claim a
proof.  It classifies the exported open frontier states from
excursion_quotient_report.json.
"""

import json
import math
from collections import Counter

B_LIMIT = 200_001
LOG2_3 = math.log2(3)
REPORT_IN = "excursion_quotient_report.json"
REPORT_OUT = "frontier_affine_invariant_report.json"


def load_report():
    with open(REPORT_IN, "r", encoding="utf-8") as f:
        return json.load(f)


def int_field(obj, name, default=0):
    val = obj.get(name, default)
    return int(val) if isinstance(val, str) else val


def classify_open(item):
    affine = item["affine"]
    gap = int_field(affine, "gap")
    b = int_field(affine, "b")
    level = affine["level"]
    c = affine["c"]
    word = item.get("accumulated_frontier_word", "")
    free_bits = affine.get("free_bits", max(0, level - c))

    if gap > 0:
        B = (b + gap - 1) // gap
        status = "certified" if B <= B_LIMIT else "positive_bad_B"
    elif gap < 0:
        B = None
        status = "debt"
    else:
        B = None
        status = "zero_gap"

    impossible = free_bits < 0
    if impossible:
        status = "impossible_bad_free_bits"

    return {
        "key": item["key"],
        "pair": item["pair"],
        "status": status,
        "reason": item.get("reason"),
        "word_length": item.get("word_length", len(word)),
        "h": item.get("h", word.count("1")),
        "z": item.get("z", word.count("0")),
        "h_over_t": item.get("h_over_t", word.count("1") / len(word) if word else 0.0),
        "longest_run_1": item.get("longest_run_1"),
        "longest_run_0": item.get("longest_run_0"),
        "is_all_one": bool(word) and word.count("1") == len(word),
        "delta": item["delta"],
        "min_delta_seen": item.get("min_delta_seen", item["delta"]),
        "gap_sign": affine["gap_sign"],
        "gap_abs_bit_length": affine["gap_abs_bit_length"],
        "a_bit_length": affine["a_bit_length"],
        "b_bit_length": affine["b_bit_length"],
        "B": B,
        "B_ok": B is not None and B <= B_LIMIT,
        "free_bits": free_bits,
        "level": level,
        "c": c,
        "o": affine["o"],
        "residue_low128": affine.get("residue_low128"),
        "three_pow_mod_2c_tail": str(affine.get("three_pow_mod_2c", ""))[-80:],
        "b_mod_2c_tail": str(affine.get("b_mod_2c", ""))[-80:],
        "word_prefix": item.get("frontier_word_prefix", word[:160]),
        "word_suffix": item.get("frontier_word_suffix", word[-160:]),
    }


def motifs(words, max_len=24):
    counts = Counter()
    for word in words:
        nmax = min(max_len, len(word) // 2)
        for n in range(2, nmax + 1):
            for i in range(0, len(word) - 2 * n + 1):
                block = word[i:i + n]
                if word[i + n:i + 2 * n] == block:
                    counts[block] += 1
    return counts


def common_prefix(words):
    if not words:
        return ""
    prefix = words[0]
    for word in words[1:]:
        i = 0
        n = min(len(prefix), len(word))
        while i < n and prefix[i] == word[i]:
            i += 1
        prefix = prefix[:i]
        if not prefix:
            break
    return prefix


def common_suffix(words):
    return common_prefix([w[::-1] for w in words])[::-1]


def all_one_affine_formula(rows):
    all_one = [r for r in rows if r["is_all_one"]]
    if not all_one:
        return {"status": "none"}
    all_one.sort(key=lambda r: r["word_length"])
    first = all_one[0]
    last = all_one[-1]
    return {
        "status": "observed_finite_family",
        "count": len(all_one),
        "min_length": first["word_length"],
        "max_length": last["word_length"],
        "min_pair": first["pair"],
        "max_pair": last["pair"],
        "max_debt_delta": min(r["delta"] for r in all_one),
        "gap": (
            "For all-1 frontier words from base (306,485), "
            "(o,c)=(306+L,485+L), so Delta(L)=Delta0+L*(1-log2(3)). "
            "This remains debt increasingly fast; word data alone cannot force return."
        ),
    }


def candidate_congruence_lemma(rows):
    impossible = [r for r in rows if r["status"].startswith("impossible")]
    certified = [r for r in rows if r["status"] == "certified"]
    debt = [r for r in rows if r["status"] == "debt"]
    all_one_debt = [r for r in debt if r["is_all_one"]]

    if impossible:
        status = "some_impossible"
    elif certified and not debt:
        status = "all_certified"
    elif all_one_debt:
        status = "word_and_affine_gap_insufficient"
    else:
        status = "open"

    return {
        "status": status,
        "impossible_count": len(impossible),
        "certified_open_count": len(certified),
        "debt_count": len(debt),
        "all_one_debt_count": len(all_one_debt),
        "failed_candidate": "long one-heavy frontier words are impossible or forced to repay by gap alone",
        "counter_observation": (
            "The exported exact affine states include valid residue representatives "
            "with gap < 0 and all-1 frontier words. They are not impossible at the "
            "current exact level."
        ),
        "next_candidate": (
            "Track a future affine return map for the all-1 family, or prove an "
            "external descent/coverage lemma for the residue interval. The local "
            "state (word,a,b,c,gap) at the cap does not itself provide B."
        ),
    }


def main():
    q = load_report()
    open_items = q.get("open_frontier", [])
    rows = [classify_open(item) for item in open_items if "affine" in item]
    words = [item.get("accumulated_frontier_word", "") for item in open_items]

    status_counts = Counter(r["status"] for r in rows)
    all_one_rows = [r for r in rows if r["is_all_one"]]
    debt_rows = [r for r in rows if r["status"] == "debt"]
    positive_bad = [r for r in rows if r["status"] == "positive_bad_B"]
    certified = [r for r in rows if r["status"] == "certified"]

    longest_debt = max(debt_rows, key=lambda r: r["word_length"], default=None)
    max_one_run = max(rows, key=lambda r: r["longest_run_1"] or 0, default=None)
    worst_gap = max(rows, key=lambda r: r["gap_abs_bit_length"], default=None)
    motif_counts = motifs(words)

    report = {
        "source": REPORT_IN,
        "summary": {
            "total_open_keys": len(rows),
            "status_counts": dict(status_counts),
            "unique_frontier_words": len(set(words)),
            "repeated_motifs": len(motif_counts),
            "longest_debt_duration": longest_debt["word_length"] if longest_debt else 0,
            "max_one_heavy_run": max_one_run["longest_run_1"] if max_one_run else 0,
            "all_one_debt_words": len(all_one_rows),
            "positive_bad_B": len(positive_bad),
            "certified_at_open": len(certified),
        },
        "longest_debt_word": longest_debt,
        "max_one_heavy_run_word": max_one_run,
        "worst_gap_word": worst_gap,
        "all_one_affine_family": all_one_affine_formula(rows),
        "common_prefix": common_prefix(words),
        "common_suffix": common_suffix(words),
        "common_prefixes": [
            {"prefix": k, "count": v}
            for k, v in Counter(w[:96] for w in words).most_common(12)
        ],
        "common_suffixes": [
            {"suffix": k, "count": v}
            for k, v in Counter(w[-96:] for w in words).most_common(12)
        ],
        "repeated_motifs": [
            {"motif": k, "count": v, "length": len(k), "ones": k.count("1")}
            for k, v in motif_counts.most_common(30)
        ],
        "any_word_stays_debt_to_cap": debt_rows[:50],
        "candidate_congruence_lemma": candidate_congruence_lemma(rows),
        "what_is_proven": [
            "The exported open states are exact affine states, not random seeds.",
            "No exported open state is certified by B <= 200001 at the cap.",
            "All exported open states remain gap-negative debt states.",
            "Finite all-1 debt branches are exact states at the current cap, so word/gap alone does not forbid them.",
        ],
        "what_remains_open": [
            "Need a return map beyond the cap for the all-1 affine family, or a proof that those residue intervals are covered elsewhere.",
            "Need exact B <= 200001 for every positive return, not just gap positivity.",
            "Need to prove the rule for all open frontier keys, not just exported representatives, before claiming closure.",
        ],
    }

    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 78)
    print("FRONTIER AFFINE INVARIANT")
    print("=" * 78)
    print(f"Total open keys       : {report['summary']['total_open_keys']:,}")
    print(f"Status counts         : {report['summary']['status_counts']}")
    print(f"Unique frontier words : {report['summary']['unique_frontier_words']:,}")
    print(f"Repeated motifs       : {report['summary']['repeated_motifs']:,}")
    print(f"Longest debt duration : {report['summary']['longest_debt_duration']:,}")
    print(f"Max one-heavy run     : {report['summary']['max_one_heavy_run']:,}")
    print(f"All-1 debt words      : {report['summary']['all_one_debt_words']:,}")
    if longest_debt:
        print(f"Longest debt pair     : {tuple(longest_debt['pair'])} delta={longest_debt['delta']:.12f}")
    print()
    print("Top repeated motifs:")
    for item in report["repeated_motifs"][:10]:
        print(f"  {item['motif']} count={item['count']} ones={item['ones']}/{item['length']}")
    print()
    print("Candidate congruence lemma:")
    for k, v in report["candidate_congruence_lemma"].items():
        print(f"  {k}: {v}")
    print()
    print("What remains open:")
    for item in report["what_remains_open"]:
        print(f"  - {item}")
    print(f"\nReport: {REPORT_OUT}")


if __name__ == "__main__":
    main()
