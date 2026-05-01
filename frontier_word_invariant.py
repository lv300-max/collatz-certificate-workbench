"""
frontier_word_invariant.py
==========================
Proof-support analyzer for the missing frontier word invariant.

This does not sample random Collatz seeds and does not increase search caps.
It rebuilds the quotient exploration with the same frontier state machine, but
adds a second layer of bookkeeping: the boundary word.  A boundary word records
which frontier cycles used the debt-increasing branch:

    0 : F(o,c)   -> F(o,c+1)
    1 : F(o,c)   -> F(o+1,c+1)

For a word of length t with h ones:

    Delta(o+h,c+t) = Delta(o,c) + t - h*log2(3)

The point of this file is to discover candidate restrictions on h/t that are
imposed by residue constraints.  It is not a proof unless every open frontier
key gets a certified return rule.
"""

import json
import math
import os
import time
from collections import Counter, defaultdict, deque

from excursion_quotient_analyzer import (
    BASE_C,
    BASE_O,
    B_LIMIT,
    ENTRY_MIN_O,
    KMAX,
    LOG2_3,
    MAX_ENTRY_NODES,
    MAX_ENTRIES,
    MAX_LEVEL,
    MAX_PARENTS,
    MAX_STEPS,
    MAX_TRANSITIONS,
    classify_positive,
    deep_open_parents,
    find_entries,
    quotient_key,
    state_delta,
    state_successors,
)

OUTFILE = os.environ.get("FRONTIER_WORD_OUTFILE", "frontier_word_invariant_report.json")
MOTIF_MAX = int(os.environ.get("FRONTIER_MOTIF_MAX", "16"))
REBUILD = os.environ.get("FRONTIER_WORD_REBUILD", "0") == "1"


def state_pair(state):
    return state[5], state[4]


def is_boundary_key(key):
    return isinstance(key, tuple) and len(key) == 4 and key[0] == 0


def normalize_to_boundary_or_return(state):
    """Continue deterministic parity steps until a boundary or valid return."""
    path = ""
    cur = state
    v2_run = 0
    while True:
        ret = classify_positive(cur)
        if ret is not None and ret["B_ok"]:
            return "return", cur, path, v2_run, ret

        key = quotient_key(cur)
        if is_boundary_key(key):
            return "boundary", cur, path, v2_run, None

        if cur[1] >= MAX_LEVEL and cur[4] >= cur[1]:
            return "open", cur, path, v2_run, {"reason": "level_cap"}
        if cur[6] >= MAX_STEPS:
            return "open", cur, path, v2_run, {"reason": "step_cap"}

        nxts = state_successors(cur)
        if len(nxts) != 1:
            return "open", cur, path, v2_run, {"reason": "unexpected_branch"}
        nxt = nxts[0]
        if nxt[5] > cur[5]:
            path += "1"
            v2_run = 0
        elif nxt[4] > cur[4]:
            path += "0"
            v2_run += 1
        cur = nxt


def branch_boundary(state):
    """Return normalized children of an s=0 boundary state."""
    children = []
    for child in state_successors(state):
        kind, terminal, suffix, v2_run, ret = normalize_to_boundary_or_return(child)
        branch_bit = "1" if terminal[5] > state[5] else "0"
        children.append({
            "kind": kind,
            "state": terminal,
            "boundary_bit": branch_bit,
            "parity_suffix": suffix,
            "v2_run": v2_run,
            "return": ret,
        })
    return children


def max_run(word, ch):
    best = cur = 0
    for x in word:
        if x == ch:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def motifs(word):
    found = Counter()
    for n in range(2, min(MOTIF_MAX, len(word) // 2) + 1):
        for i in range(0, len(word) - 2 * n + 1):
            block = word[i:i + n]
            if word[i + n:i + 2 * n] == block:
                found[block] += 1
    return found


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


def residue_constraint(state):
    residue, level, _a, _b, c, o, _steps = state
    return {
        "modulus_bits": level,
        "known_parity_bits": c,
        "free_bits": max(0, level - c),
        "residue_low64": residue & ((1 << min(64, level)) - 1),
        "o": o,
        "c": c,
    }


def explore_frontier_words(entries):
    queue = deque()
    reps = {}
    words = {}
    metadata = {}
    returns = []
    bad_positive = []
    open_records = []
    conflicts = []
    visits = 0

    for r0, kv, depth, entry in entries:
        kind, boundary, suffix, v2_run, ret = normalize_to_boundary_or_return(entry)
        if kind == "return":
            returns.append({"origin": (r0, kv, depth), "word": "", "return": ret})
            continue
        key = quotient_key(boundary)
        reps.setdefault(key, boundary)
        words.setdefault(key, "")
        metadata.setdefault(key, {
            "origins": set(),
            "entry_suffixes": Counter(),
            "max_v2_run": 0,
        })
        metadata[key]["origins"].add((r0, kv, depth))
        metadata[key]["entry_suffixes"][suffix] += 1
        metadata[key]["max_v2_run"] = max(metadata[key]["max_v2_run"], v2_run)
        queue.append(key)

    while queue:
        key = queue.popleft()
        state = reps[key]
        word = words[key]
        visits += 1
        if visits > MAX_TRANSITIONS:
            open_records.append((key, state, word, "transition_cap"))
            break

        ret = classify_positive(state)
        if ret is not None:
            if ret["B_ok"]:
                returns.append({"key": key, "word": word, "return": ret})
                continue
            if len(bad_positive) < 100:
                bad_positive.append({"key": key, "word": word, "positive": ret})

        if state[1] >= MAX_LEVEL and state[4] >= state[1]:
            open_records.append((key, state, word, "level_cap"))
            continue
        if state[6] >= MAX_STEPS:
            open_records.append((key, state, word, "step_cap"))
            continue

        children = branch_boundary(state) if is_boundary_key(key) else []
        if not children:
            for nxt in state_successors(state):
                nk = quotient_key(nxt)
                if nk not in reps:
                    reps[nk] = nxt
                    words[nk] = word
                    metadata[nk] = metadata.get(nk, {"origins": set(), "entry_suffixes": Counter(), "max_v2_run": 0})
                    queue.append(nk)
            continue

        for child in children:
            if child["kind"] == "return":
                returns.append({
                    "key": key,
                    "word": word + child["boundary_bit"],
                    "return": child["return"],
                    "parity_suffix": child["parity_suffix"],
                })
                continue
            if child["kind"] == "open":
                open_records.append((key, child["state"], word + child["boundary_bit"], child["return"]["reason"]))
                continue

            nk = quotient_key(child["state"])
            nw = word + child["boundary_bit"]
            if nk not in reps:
                reps[nk] = child["state"]
                words[nk] = nw
                metadata[nk] = {"origins": set(), "entry_suffixes": Counter(), "max_v2_run": child["v2_run"]}
                queue.append(nk)
            else:
                old_children = [
                    (c["kind"], quotient_key(c["state"]), c["boundary_bit"])
                    for c in branch_boundary(reps[nk])
                ] if is_boundary_key(nk) else []
                new_children = [
                    (c["kind"], quotient_key(c["state"]), c["boundary_bit"])
                    for c in branch_boundary(child["state"])
                ] if is_boundary_key(nk) else []
                if old_children != new_children and len(conflicts) < 20:
                    conflicts.append({
                        "key": nk,
                        "old_children": old_children,
                        "new_children": new_children,
                    })
                if len(nw) < len(words[nk]):
                    words[nk] = nw
            metadata[nk]["max_v2_run"] = max(metadata[nk]["max_v2_run"], child["v2_run"])

    return {
        "representatives": reps,
        "words": words,
        "metadata": metadata,
        "returns": returns,
        "bad_positive": bad_positive,
        "open_records": open_records,
        "conflicts": conflicts,
        "visits": visits,
    }


def summarize_open(records):
    rows = []
    for key, state, word, reason in records:
        h = word.count("1")
        t = len(word)
        o, c = state_pair(state)
        rows.append({
            "key": key,
            "pair": (o, c),
            "reason": reason,
            "word_length": t,
            "odd_count_h": h,
            "halving_count_t": t,
            "h_over_t": h / t if t else 0.0,
            "max_consecutive_ones": max_run(word, "1"),
            "max_consecutive_zeros": max_run(word, "0"),
            "delta": state_delta(o, c),
            "debt_depth": max(0.0, -state_delta(o, c)),
            "residue_constraint": residue_constraint(state),
            "word_prefix": word[:128],
            "word_suffix": word[-128:],
        })
    return rows


def forced_repayment_examples(returns):
    examples = []
    for rec in returns:
        word = rec.get("word", "")
        ret = rec["return"]
        if not word:
            continue
        h = word.count("1")
        t = len(word)
        examples.append({
            "word_length": t,
            "odd_count_h": h,
            "h_over_t": h / t,
            "max_consecutive_ones": max_run(word, "1"),
            "return_pair": tuple(ret["pair"]),
            "return_delta": ret["delta"],
            "B": ret["B"],
            "word_suffix": word[-96:],
        })
    examples.sort(key=lambda x: (-x["word_length"], -x["h_over_t"], x["B"]))
    return examples[:20]


def candidate_recurrence(open_rows, return_examples):
    if not open_rows:
        return {"status": "closed_under_caps"}
    max_ratio = max(r["h_over_t"] for r in open_rows)
    concrete_one_runs = [r["max_consecutive_ones"] for r in open_rows if r["max_consecutive_ones"] is not None]
    max_ones = max(concrete_one_runs) if concrete_one_runs else "not exported"
    max_debt = max(r["debt_depth"] for r in open_rows)
    longest = max(r["word_length"] for r in open_rows)
    return {
        "status": "candidate_only",
        "frontier_rule": "F(o,c,w) -> F(o,c+1,w0) or F(o+1,c+1,w1)",
        "delta_rule": "Delta' = Delta + 1 for 0, Delta' = Delta + 1 - log2(3) for 1",
        "observed_open_max_h_over_t": max_ratio,
        "observed_open_max_consecutive_ones": max_ones,
        "observed_max_debt_depth": max_debt,
        "observed_longest_debt_duration": longest,
        "candidate_invariant": (
            "Long one-heavy frontier words must create residue constraints that "
            "force a zero-rich repayment block. This is not yet certified; the "
            "next proof must derive the repayment block from congruences, not "
            "from caps."
        ),
        "repayment_examples_available": len(return_examples),
    }


def main():
    t0 = time.time()
    if not REBUILD:
        with open("excursion_quotient_report.json", "r", encoding="utf-8") as f:
            qreport = json.load(f)
        frontier = qreport.get("open_frontier", [])
        rows = []
        local_motifs = Counter()
        repayment = qreport.get("returned_frontier", [])
        words = []
        for item in frontier:
            key = item["key"]
            if len(key) != 4:
                continue
            word = item.get("accumulated_frontier_word", "")
            words.append(word)
            o, c = item["pair"]
            h = item.get("h", word.count("1"))
            z = item.get("z", word.count("0"))
            t = item.get("t", len(word))
            suffixes = [x.get("path", "") for x in item.get("boundary_successors", [])]
            local_motifs.update(motifs(word))
            local_motifs.update(x for x in suffixes if x)
            rows.append({
                "key": key,
                "pair": item["pair"],
                "reason": item["reason"],
                "word_length": t,
                "odd_count_h": h,
                "zero_count_z": z,
                "halving_count_t": t,
                "h_over_t": h / t if t else 0.0,
                "max_consecutive_ones": item.get("longest_run_1", max_run(word, "1")),
                "max_consecutive_zeros": item.get("longest_run_0", max_run(word, "0")),
                "delta": item["delta"],
                "min_delta_seen": item.get("min_delta_seen", item["delta"]),
                "debt_depth": max(0.0, -item.get("min_delta_seen", item["delta"])),
                "residue_constraint": {
                    "modulus_bits": item["level"],
                    "known_parity_bits": item["pair"][1],
                    "free_bits": max(0, item["level"] - item["pair"][1]),
                    "lane16": item["lane16"],
                },
                "local_boundary_successors": item.get("boundary_successors", []),
                "word_prefix": word[:200],
                "word_suffix": word[-200:],
                "v2_sequence_tail": item.get("v2_sequence", []),
                "parent_key": item.get("parent_key"),
                "previous_key": item.get("previous_key"),
                "returned_to_positive_margin": item.get("returned_to_positive_margin", False),
                "return_B": item.get("return_B"),
            })

        unique_words = set(words)
        longest_debt = max(rows, key=lambda r: r["word_length"], default=None)
        max_one_run = max(rows, key=lambda r: r["max_consecutive_ones"], default=None)
        debt_to_cap = [r for r in rows if r["reason"] in {"level_cap", "transition_cap", "step_cap"} and r["delta"] <= 0]
        prefixes = Counter(w[:64] for w in words)
        suffixes = Counter(w[-64:] for w in words)

        report = {
            "mode": "report_only",
            "summary": {
                "open_keys_analyzed": len(rows),
                "open_keys_total_reported_by_quotient": qreport.get("n_open_keys"),
                "unique_frontier_words": len(unique_words),
                "returns": qreport.get("n_return_keys"),
                "bad_positive_observed": len(qreport.get("bad_B_positive", [])),
                "conflicts": len(qreport.get("conflicts", [])),
                "max_debt_depth": max((r["debt_depth"] for r in rows), default=0.0),
                "longest_debt_duration": max((r["word_length"] for r in rows), default=0),
                "max_one_heavy_run": max((r["max_consecutive_ones"] for r in rows), default=0),
            },
            "common_prefix": common_prefix(words),
            "common_suffix": common_suffix(words),
            "common_prefixes": [
                {"prefix": k, "count": v}
                for k, v in prefixes.most_common(12)
            ],
            "common_suffixes": [
                {"suffix": k, "count": v}
                for k, v in suffixes.most_common(12)
            ],
            "longest_debt_word": longest_debt,
            "max_one_heavy_run_word": max_one_run,
            "debt_forever_to_cap": debt_to_cap[:50],
            "forbidden_word_findings": {
                "all_one_debt_words_to_cap": sum(
                    1 for r in rows
                    if r["word_length"] > 0
                    and r["max_consecutive_ones"] == r["word_length"]
                    and r["delta"] <= 0
                    and r["reason"] in {"level_cap", "transition_cap", "step_cap"}
                ),
                "simple_one_heavy_forbidden_lemma_false": True,
                "reason": (
                    "The exported frontier contains finite all-1 debt words "
                    "that survive to the quotient cap. A valid lemma must use "
                    "additional congruence/formula data beyond the 0/1 "
                    "frontier word and h/t ratio."
                ),
            },
            "open_frontier_examples": rows[:50],
            "repeated_motifs": [
                {"motif": k, "count": v, "length": len(k), "ones": k.count("1")}
                for k, v in local_motifs.most_common(30)
            ],
            "forced_repayment_examples": repayment[:20],
            "candidate_recurrence": candidate_recurrence(rows, repayment),
            "candidate_integer_invariant": {
                "frontier_offsets": "h=count(1), z=count(0), t=h+z in accumulated_frontier_word",
                "debt_condition": "2^(485+t) <= 3^(306+h)",
                "return_condition": "2^(485+t+r) > 3^(306+h+g) and B <= 200001",
                "needed_bound": "prove h <= floor((t + Delta0 - epsilon)/log2(3)) after a bounded repayment block",
                "structural_target": "derive a congruence-forced zero-rich block from long one-heavy words",
            },
            "candidate_congruence_lemma": {
                "status": "not_found",
                "failed_candidate": "There is a universal max h or max consecutive 1s before repayment.",
                "counter_observation": "Finite all-1 frontier debt words occur up to the current cap.",
                "next_viable_form": (
                    "Track the affine numerator b and denominator gap "
                    "2^c-3^o, or an exact residue interval, in addition to "
                    "the frontier word. The word alone does not force repayment."
                ),
            },
            "what_remains_open": [
                "Report-only mode analyzes the open keys exported by the quotient report.",
                "Need a congruence lemma forcing repayment after long one-heavy prefixes.",
                "Need exact B certification for every resulting positive return.",
            ],
        }

        with open(OUTFILE, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=list)

        print("=" * 78)
        print("FRONTIER WORD INVARIANT")
        print("=" * 78)
        print(f"Open keys analyzed       : {report['summary']['open_keys_analyzed']:,}")
        print(f"Open keys in quotient    : {report['summary']['open_keys_total_reported_by_quotient']:,}")
        print(f"Unique frontier words    : {report['summary']['unique_frontier_words']}")
        print(f"Repeated motifs          : {len(report['repeated_motifs']):,}")
        print(f"Max debt depth           : {report['summary']['max_debt_depth']:.12f}")
        print(f"Longest debt duration    : {report['summary']['longest_debt_duration']:,}")
        print(f"Max one-heavy run        : {report['summary']['max_one_heavy_run']:,}")
        print(f"Forced repayment examples: {len(repayment):,}")
        print(f"Conflicts                : {report['summary']['conflicts']}")
        print(f"Debt words to cap        : {len(debt_to_cap):,}")
        print(f"All-1 debt words to cap  : {report['forbidden_word_findings']['all_one_debt_words_to_cap']:,}")
        print(f"Common prefix length     : {len(report['common_prefix'])}")
        print(f"Common suffix length     : {len(report['common_suffix'])}")
        if longest_debt:
            print(f"Longest debt word pair   : {tuple(longest_debt['pair'])} len={longest_debt['word_length']} h/t={longest_debt['h_over_t']:.6f}")
        print()
        print("Top repeated motifs:")
        for item in report["repeated_motifs"][:10]:
            print(f"  {item['motif']}  count={item['count']} ones={item['ones']}/{item['length']}")
        print()
        print("Common prefixes:")
        for item in report["common_prefixes"][:5]:
            print(f"  count={item['count']} prefix={item['prefix']}")
        print()
        print("Common suffixes:")
        for item in report["common_suffixes"][:5]:
            print(f"  count={item['count']} suffix={item['suffix']}")
        print()
        print("Candidate recurrence:")
        for k, v in report["candidate_recurrence"].items():
            print(f"  {k}: {v}")
        print()
        print("Candidate integer invariant:")
        for k, v in report["candidate_integer_invariant"].items():
            print(f"  {k}: {v}")
        print()
        print("Candidate congruence lemma:")
        for k, v in report["candidate_congruence_lemma"].items():
            print(f"  {k}: {v}")
        print()
        print("What remains open:")
        for item in report["what_remains_open"]:
            print(f"  - {item}")
        print(f"\nReport: {OUTFILE}")
        print(f"Total time: {time.time() - t0:.1f}s")
        return

    parents = deep_open_parents()
    entries, per_parent = find_entries(parents)
    result = explore_frontier_words(entries)
    open_rows = summarize_open(result["open_records"])
    return_examples = forced_repayment_examples(result["returns"])

    all_words = list(result["words"].values()) + [r["word"] for r in result["returns"] if "word" in r]
    unique_words = set(all_words)
    motif_counter = Counter()
    for word in all_words:
        motif_counter.update(motifs(word))

    report = {
        "config": {
            "parents": len(parents),
            "max_parents": MAX_PARENTS,
            "entries": len(entries),
            "entry_min_o": ENTRY_MIN_O,
            "max_entries": MAX_ENTRIES,
            "max_entry_nodes": MAX_ENTRY_NODES,
            "max_transitions": MAX_TRANSITIONS,
            "max_level": MAX_LEVEL,
        },
        "summary": {
            "open_keys_analyzed": len(open_rows),
            "unique_frontier_words": len(unique_words),
            "returns": len(result["returns"]),
            "bad_positive_observed": len(result["bad_positive"]),
            "conflicts": len(result["conflicts"]),
            "max_debt_depth": max((r["debt_depth"] for r in open_rows), default=0.0),
            "longest_debt_duration": max((r["word_length"] for r in open_rows), default=0),
        },
        "open_frontier_examples": open_rows[:50],
        "repeated_motifs": [
            {"motif": k, "count": v, "length": len(k), "ones": k.count("1")}
            for k, v in motif_counter.most_common(30)
        ],
        "forced_repayment_examples": return_examples,
        "candidate_recurrence": candidate_recurrence(open_rows, return_examples),
        "what_remains_open": [
            "The current run records frontier words under the existing quotient caps; it does not prove every possible frontier word.",
            "Need an exact congruence lemma showing long one-heavy words force a zero-rich repayment block.",
            "Need to attach each repayment block to an exact positive-margin state with B <= 200001.",
            "No proof may be claimed until every open frontier key has a certified return rule.",
        ],
        "conflicts": result["conflicts"],
    }

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=list)

    print("=" * 78)
    print("FRONTIER WORD INVARIANT")
    print("=" * 78)
    print(f"Open keys analyzed       : {report['summary']['open_keys_analyzed']:,}")
    print(f"Unique frontier words    : {report['summary']['unique_frontier_words']:,}")
    print(f"Repeated motifs          : {len(report['repeated_motifs']):,}")
    print(f"Max debt depth           : {report['summary']['max_debt_depth']:.12f}")
    print(f"Longest debt duration    : {report['summary']['longest_debt_duration']:,}")
    print(f"Forced repayment examples: {len(return_examples):,}")
    print(f"Conflicts                : {report['summary']['conflicts']}")
    print()
    print("Top repeated motifs:")
    for item in report["repeated_motifs"][:10]:
        print(f"  {item['motif']}  count={item['count']} ones={item['ones']}/{item['length']}")
    print()
    print("Candidate recurrence:")
    for k, v in report["candidate_recurrence"].items():
        print(f"  {k}: {v}")
    print()
    print("What remains open:")
    for item in report["what_remains_open"]:
        print(f"  - {item}")
    print(f"\nReport: {OUTFILE}")
    print(f"Total time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
