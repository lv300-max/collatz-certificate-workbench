"""
cf_danger_search.py
===================
Focused continued-fraction danger-pair scan for unresolved deep parents.

This does not run random seeds and does not redo exact sibling enumeration.
It rebuilds the depth>18 parent list, then symbolically scans each parent for
first positive-margin branch certificates and unresolved branches that can stay
at or below c/o = log2(3).
"""

import math
import os
import time

KMAX = 16
MAX_STEPS = 10_000
MAX_K_VALID = 500
LOG2_3 = math.log2(3)
KNOWN_SAFE = {
    (17, 27),
    (29, 46),
    (41, 65),
    (94, 149),
    (147, 233),
    (200, 317),
    (253, 401),
    (306, 485),
}
MAX_NODES = int(os.environ.get("CF_DANGER_MAX_NODES", "2000000"))
MAX_LEVEL = int(os.environ.get("CF_DANGER_MAX_LEVEL", "500"))
MAX_REPORT = int(os.environ.get("CF_DANGER_MAX_REPORT", "12"))
DANGER_MIN_O = int(os.environ.get("CF_DANGER_MIN_O", "307"))


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
    return parents


def continued_fraction_upper_candidates(limit_o):
    """Return upper semiconvergents c/o above log2(3), including intermediates."""
    cf = []
    x = LOG2_3
    while len(cf) < 32:
        a = math.floor(x)
        cf.append(a)
        x = 1 / (x - a)

    conv = []
    n2, n1 = 0, 1
    d2, d1 = 1, 0
    for a in cf:
        n = a * n1 + n2
        d = a * d1 + d2
        conv.append((d, n))
        n2, n1 = n1, n
        d2, d1 = d1, d

    candidates = set()
    for i in range(len(conv) - 1):
        o0, c0 = conv[i]
        o1, c1 = conv[i + 1]
        if c0 - o0 * LOG2_3 <= 0:
            continue
        if c1 - o1 * LOG2_3 >= 0:
            continue
        max_t = cf[i + 2] if i + 2 < len(cf) else 1
        for t in range(1, max_t + 1):
            o = o0 + t * o1
            c = c0 + t * c1
            if o > limit_o:
                break
            if c - o * LOG2_3 > 0:
                candidates.add((o, c))
    return sorted(candidates)


def scan_parent(r0, candidate_pairs):
    stack = [(r0, KMAX, 1, 0, 0, 0, 0)]
    nodes = 0
    candidate_hits = {}
    best_delta = math.inf
    best_pair = None
    first_below = None
    cap_blockers = []

    while stack:
        residue, level, a, b, c, odd_count, steps = stack.pop()
        nodes += 1

        delta = c - odd_count * LOG2_3
        if odd_count >= DANGER_MIN_O and c <= math.floor(odd_count * LOG2_3):
            if first_below is None:
                first_below = (residue, level, steps, odd_count, c, delta)

        if nodes > MAX_NODES:
            cap_blockers.append((residue, level, steps, odd_count, c, delta, "node_cap"))
            break
        if steps >= MAX_STEPS:
            cap_blockers.append((residue, level, steps, odd_count, c, delta, "step_cap"))
            continue
        if level >= MAX_LEVEL:
            cap_blockers.append((residue, level, steps, odd_count, c, delta, "level_cap"))
            continue

        if delta > 0:
            pair = (odd_count, c)
            if pair in candidate_pairs:
                candidate_hits[pair] = candidate_hits.get(pair, 0) + 1
            if delta < best_delta:
                best_delta = delta
                best_pair = pair
            continue

        if c >= level:
            stack.append((residue + (1 << level), level + 1, a, b, c, odd_count, steps))
            stack.append((residue, level + 1, a, b, c, odd_count, steps))
            continue

        parity = ((a * residue + b) >> c) & 1
        if parity == 0:
            stack.append((residue, level, a, b, c + 1, odd_count, steps + 1))
        else:
            stack.append((residue, level, 3 * a, 3 * b + (1 << c), c, odd_count + 1, steps + 1))

    unknown_pairs = sorted(pair for pair in candidate_hits if pair not in KNOWN_SAFE)
    return {
        "nodes": nodes,
        "candidate_hits": candidate_hits,
        "unknown_pairs": unknown_pairs,
        "best_pair": best_pair,
        "best_delta": best_delta,
        "first_below": first_below,
        "cap_blockers": cap_blockers,
        "complete": not stack and not cap_blockers,
    }


def main():
    t0 = time.time()
    parents = deep_open_parents()
    candidates = continued_fraction_upper_candidates(2000)
    candidate_pairs = set(candidates)
    next_after_306 = next(pair for pair in candidates if pair[0] > 306)

    print("=" * 72)
    print("CONTINUED-FRACTION DANGER SEARCH")
    print("=" * 72)
    print(f"Open depth>18 parents     : {len(parents)}")
    print(f"Known safe danger pairs   : {sorted(KNOWN_SAFE)}")
    print(f"Next candidate after 306/485: {next_after_306}  "
          f"delta={next_after_306[1] - next_after_306[0] * LOG2_3:.12f}")
    print(f"Below-line reporting starts at o >= {DANGER_MIN_O}")
    print(f"Node cap / parent         : {MAX_NODES:,}")
    print(f"Level cap / branch        : {MAX_LEVEL}")
    print()

    complete = 0
    with_below = []
    with_unknown = []
    best_global = None
    next_candidate_hits = []

    for idx, (r0, kv, depth) in enumerate(parents, 1):
        res = scan_parent(r0, candidate_pairs)
        if res["complete"] and not res["first_below"] and not res["unknown_pairs"]:
            complete += 1
        if res["first_below"] and len(with_below) < MAX_REPORT:
            with_below.append((r0, kv, depth, res["first_below"]))
        if res["unknown_pairs"] and len(with_unknown) < MAX_REPORT:
            with_unknown.append((r0, kv, depth, res["unknown_pairs"][:8]))
        if next_after_306 in res["candidate_hits"] and len(next_candidate_hits) < MAX_REPORT:
            next_candidate_hits.append((r0, kv, depth, res["candidate_hits"][next_after_306]))
        if res["best_pair"] is not None:
            rec = (res["best_delta"], r0, kv, depth, res["best_pair"])
            if best_global is None or rec < best_global:
                best_global = rec

        if idx % 25 == 0 or res["unknown_pairs"] or res["first_below"]:
            best = "none" if res["best_pair"] is None else f"{res['best_pair']} d={res['best_delta']:.12f}"
            print(f"[{idx:3d}/{len(parents)}] r0={r0:6d} d={depth:3d} "
                  f"nodes={res['nodes']:9,} complete={res['complete']} "
                  f"best={best} below={res['first_below'] is not None} "
                  f"unknown_pairs={len(res['unknown_pairs'])}", flush=True)

    print()
    print("SUMMARY")
    print(f"  Parent-level margin certificates exported : {complete}")
    print(f"  Parents with a below-line branch           : {len(with_below)} shown")
    print(f"  Parents with unknown positive danger pairs : {len(with_unknown)} shown")
    print(f"  Hits of next candidate {next_after_306}      : {len(next_candidate_hits)} shown")
    if best_global:
        delta, r0, kv, depth, pair = best_global
        print(f"  Tightest positive pair seen                : r0={r0} d={depth} k'={kv} pair={pair} delta={delta:.12f}")
    print()
    print("Below-line examples:")
    for item in with_below:
        print(f"  {item}")
    print()
    print("Unknown positive-pair examples:")
    for item in with_unknown:
        print(f"  {item}")
    print()
    print(f"Next-candidate hits for {next_after_306}:")
    for item in next_candidate_hits:
        print(f"  {item}")
    print(f"\nTotal time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
