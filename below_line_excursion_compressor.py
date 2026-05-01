"""
below_line_excursion_compressor.py
==================================
Deterministic proof-support scan for below-line excursions after the certified
continued-fraction danger pair (306,485).

For each unresolved depth>18 parent, this searches exact symbolic branches for
the first state with:

    o >= ENTRY_MIN_O and c <= floor(o * log2(3))

From that entry, it continues the exact branch tree until each excursion branch
returns to positive margin (c - o*log2(3) > 0), then records whether the return
pair is in the certified safe set and whether the return certificate has
B <= 200001. A non-safe-set positive return is still a valid local certificate
when B <= 200001; it is reported separately because it is not one of the tight
continued-fraction danger records.

This script is intentionally conservative: if a cap is reached, the excursion
is marked open, not proved.
"""

import json
import math
import os
import time
from collections import Counter, deque

KMAX = 16
MAX_STEPS = 10_000
MAX_K_VALID = 500
LOG2_3 = math.log2(3)
B_LIMIT = 200_001

SAFE_PAIRS = {
    (17, 27),
    (29, 46),
    (41, 65),
    (94, 149),
    (147, 233),
    (200, 317),
    (253, 401),
    (306, 485),
}

ENTRY_MIN_O = int(os.environ.get("EXCURSION_ENTRY_MIN_O", "307"))
MAX_ENTRY_NODES = int(os.environ.get("EXCURSION_MAX_ENTRY_NODES", "2000000"))
MAX_EXCURSION_NODES = int(os.environ.get("EXCURSION_MAX_NODES", "500000"))
MAX_LEVEL = int(os.environ.get("EXCURSION_MAX_LEVEL", "900"))
MAX_ENTRIES_PER_PARENT = int(os.environ.get("EXCURSION_MAX_ENTRIES_PER_PARENT", "4"))
MAX_PARENTS = int(os.environ.get("EXCURSION_MAX_PARENTS", "0"))
OUTFILE = os.environ.get("EXCURSION_OUTFILE", "below_line_excursion_report.json")
CHECKPOINT_EVERY = int(os.environ.get("EXCURSION_CHECKPOINT_EVERY", "1"))


def compute_descent(r, k, max_steps=MAX_STEPS):
    a, b, c = 1, 0, 0
    n = r
    valid = True
    odd_count = 0
    for m in range(1, max_steps + 1):
        if c >= k:
            valid = False
        if n % 2 == 0:
            c += 1
            n >>= 1
        else:
            a = 3 * a
            b = 3 * b + (1 << c)
            n = 3 * n + 1
            odd_count += 1
        two_c = 1 << c
        if two_c > a:
            B = (b + two_c - a - 1) // (two_c - a)
            return m, a, b, c, B, valid, odd_count
    return None


def find_valid_k(r, k_min=KMAX, max_k=MAX_K_VALID):
    for k in range(k_min, max_k + 1):
        rep = r % (1 << k)
        if rep % 2 == 0:
            continue
        res = compute_descent(rep, k)
        if res is not None and res[5]:
            return k, res
    return None, None


def deep_open_parents():
    parents = []
    for r0 in range(1, 1 << KMAX, 2):
        res0 = compute_descent(r0, KMAX)
        if res0 is None or res0[5]:
            continue
        kv, res = find_valid_k(r0, k_min=KMAX)
        if kv is None:
            continue
        depth = kv - KMAX
        if depth > 18:
            parents.append((r0, kv, depth))
    parents.sort(key=lambda x: x[2])
    if MAX_PARENTS > 0:
        parents = parents[:MAX_PARENTS]
    return parents


def step_state(state, parity):
    residue, level, a, b, c, o, steps, word = state
    if parity == 0:
        return residue, level, a, b, c + 1, o, steps + 1, word + "0"
    return residue, level, 3 * a, 3 * b + (1 << c), c, o + 1, steps + 1, word + "1"


def successors(state):
    residue, level, a, b, c, o, steps, word = state
    if c >= level:
        return [
            (residue, level + 1, a, b, c, o, steps, word),
            (residue + (1 << level), level + 1, a, b, c, o, steps, word),
        ]
    parity = ((a * residue + b) >> c) & 1
    return [step_state(state, parity)]


def find_below_entries(r0):
    stack = [(r0, KMAX, 1, 0, 0, 0, 0, "")]
    entries = []
    nodes = 0
    seen_entry_keys = set()

    while stack and len(entries) < MAX_ENTRIES_PER_PARENT:
        state = stack.pop()
        residue, level, a, b, c, o, steps, word = state
        nodes += 1
        if nodes > MAX_ENTRY_NODES:
            return entries, nodes, "entry_node_cap"
        if level >= MAX_LEVEL:
            continue
        if steps >= MAX_STEPS:
            continue

        if o >= ENTRY_MIN_O and c <= math.floor(o * LOG2_3):
            key = (residue % (1 << min(level, KMAX + 32)), level, o, c)
            if key not in seen_entry_keys:
                seen_entry_keys.add(key)
                entries.append(state)
            continue

        stack.extend(successors(state))

    reason = "entry_limit" if len(entries) >= MAX_ENTRIES_PER_PARENT else "exhausted"
    return entries, nodes, reason


def compress_key(state):
    residue, level, _a, _b, c, o, _steps, _word = state
    # Proof-support compression key. Exact state still drives transitions; this
    # groups diagnostics by low lane and offset from the certified barrier.
    return {
        "lane16": residue & ((1 << KMAX) - 1),
        "level_minus_c": level - c,
        "o_minus_306": o - 306,
        "c_minus_485": c - 485,
        "delta_band_milli": math.floor((c - o * LOG2_3) * 1000),
    }


def continue_excursion(entry_state):
    queue = deque([entry_state])
    nodes = 0
    returns = []
    open_states = []
    max_B = 0
    min_return_delta = math.inf
    compressed = Counter()

    while queue:
        state = queue.popleft()
        residue, level, a, b, c, o, steps, word = state
        nodes += 1
        ck = compress_key(state)
        compressed[tuple(sorted(ck.items()))] += 1

        if nodes > MAX_EXCURSION_NODES:
            open_states.append((state, "excursion_node_cap"))
            break
        if level >= MAX_LEVEL:
            open_states.append((state, "level_cap"))
            continue
        if steps >= MAX_STEPS:
            open_states.append((state, "step_cap"))
            continue

        delta = c - o * LOG2_3
        if delta > 0:
            denom = (1 << c) - a
            B = (b + denom - 1) // denom
            pair = (o, c)
            max_B = max(max_B, B)
            min_return_delta = min(min_return_delta, delta)
            returns.append({
                "pair": pair,
                "safe_pair": pair in SAFE_PAIRS,
                "B": B,
                "B_ok": B <= B_LIMIT,
                "delta": delta,
                "m": steps,
                "level": level,
                "residue_mod_2^16": residue & ((1 << KMAX) - 1),
                "first_200_parity_symbols": word[:200],
            })
            continue

        queue.extend(successors(state))

    all_certified = bool(returns) and not open_states and all(r["B_ok"] for r in returns)
    all_safe_record = all_certified and all(r["safe_pair"] for r in returns)
    non_safe_return_pairs = sorted({tuple(r["pair"]) for r in returns if not r["safe_pair"]})
    return {
        "nodes": nodes,
        "returns": returns,
        "open_states": [
            {
                "reason": reason,
                "level": st[1],
                "m": st[6],
                "o": st[5],
                "c": st[4],
                "delta": st[4] - st[5] * LOG2_3,
                "compressed_key": compress_key(st),
            }
            for st, reason in open_states[:12]
        ],
        "max_B": max_B,
        "min_return_delta": min_return_delta,
        "all_certified": all_certified,
        "all_safe_record": all_safe_record,
        "non_safe_return_pairs": non_safe_return_pairs,
        "compressed_state_count": len(compressed),
        "top_compressed_states": [
            {**dict(k), "count": v}
            for k, v in compressed.most_common(8)
        ],
    }


def summarize_entry(entry_state):
    residue, level, _a, _b, c, o, steps, word = entry_state
    return {
        "level": level,
        "m": steps,
        "o": o,
        "c": c,
        "delta": c - o * LOG2_3,
        "residue_mod_2^16": residue & ((1 << KMAX) - 1),
        "compressed_key": compress_key(entry_state),
        "first_200_parity_symbols": word[:200],
    }


def main():
    t0 = time.time()
    parents = deep_open_parents()
    report = []
    certified_entries = 0
    safe_record_entries = 0
    open_entries = 0
    parent_all_certified = 0
    parent_all_safe_record = 0
    non_safe_return_counter = Counter()

    print("=" * 78)
    print("BELOW-LINE EXCURSION COMPRESSOR")
    print("=" * 78)
    print(f"Parents                  : {len(parents)}")
    print(f"Entry condition          : o >= {ENTRY_MIN_O}, c <= floor(o*log2(3))")
    print(f"Certified safe records   : {sorted(SAFE_PAIRS)}")
    print(f"Entry node cap / parent  : {MAX_ENTRY_NODES:,}")
    print(f"Excursion node cap       : {MAX_EXCURSION_NODES:,}")
    print(f"Level cap                : {MAX_LEVEL}")
    print()

    for idx, (r0, kv, depth) in enumerate(parents, 1):
        entries, entry_nodes, entry_reason = find_below_entries(r0)
        parent_result = {
            "r0": r0,
            "k_prime": kv,
            "depth": depth,
            "entry_nodes": entry_nodes,
            "entry_reason": entry_reason,
            "entries": [],
        }

        all_certified = bool(entries)
        all_safe_record = bool(entries)
        for entry in entries:
            exc = continue_excursion(entry)
            non_safe_return_counter.update(tuple(p) for p in exc["non_safe_return_pairs"])
            if exc["all_certified"]:
                certified_entries += 1
                if exc["all_safe_record"]:
                    safe_record_entries += 1
                else:
                    all_safe_record = False
            else:
                open_entries += 1
                all_certified = False
                all_safe_record = False
            parent_result["entries"].append({
                "entry": summarize_entry(entry),
                "excursion": exc,
            })

        if all_certified and entry_reason not in ("entry_node_cap", "entry_limit"):
            parent_all_certified += 1
            if all_safe_record:
                parent_all_safe_record += 1

        report.append(parent_result)
        if CHECKPOINT_EVERY and idx % CHECKPOINT_EVERY == 0:
            with open(OUTFILE, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
        print(f"[{idx:3d}/{len(parents)}] r0={r0:6d} d={depth:3d} "
              f"entries={len(entries):2d} entry_nodes={entry_nodes:9,} "
              f"entry_reason={entry_reason:14s} certified={all_certified} "
              f"safe_record={all_safe_record} cert_entries={certified_entries} "
              f"open_entries={open_entries}",
              flush=True)

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"  Parents analyzed          : {len(parents)}")
    print(f"  Parents all-certified     : {parent_all_certified}")
    print(f"  Parents all-safe-record   : {parent_all_safe_record}")
    print(f"  Certified excursions      : {certified_entries}")
    print(f"  Safe-record excursions    : {safe_record_entries}")
    print(f"  Open excursions           : {open_entries}")
    print(f"  Non-safe positive returns : {dict(non_safe_return_counter.most_common(20))}")
    print(f"  Report                    : {OUTFILE}")
    print(f"  Total time                : {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
