"""
excursion_quotient_analyzer.py
==============================
Exact quotient-state analyzer for below-line excursions.

The previous compressor grouped diagnostics by coarse keys. This script uses a
stronger exact quotient:

    q = ((3^o * residue + b) >> c) mod 2^(level-c)
    s = level - c
    u = o - 306
    v = c - 485

For c <= level, q is the known low-s-bit value of the current iterate after the
prefix. Future parity steps until the next branch are determined by q, s, and
the offset pair (u,v). This gives a finite quotient candidate for below-line
excursions near the 306/485 barrier.

This is proof-support code. It reports conflicts instead of pretending a
conflicted quotient is a theorem.
"""

import json
import math
import os
import time
from collections import Counter, defaultdict, deque

KMAX = 16
LOG2_3 = math.log2(3)
B_LIMIT = 200_001
BASE_O = 306
BASE_C = 485
ENTRY_MIN_O = int(os.environ.get("QUOTIENT_ENTRY_MIN_O", "307"))
MAX_STEPS = int(os.environ.get("QUOTIENT_MAX_STEPS", "10000"))
MAX_K_VALID = int(os.environ.get("QUOTIENT_MAX_K_VALID", "500"))
MAX_PARENTS = int(os.environ.get("QUOTIENT_MAX_PARENTS", "80"))
MAX_ENTRY_NODES = int(os.environ.get("QUOTIENT_MAX_ENTRY_NODES", "300000"))
MAX_ENTRIES = int(os.environ.get("QUOTIENT_MAX_ENTRIES", "2000"))
MAX_TRANSITIONS = int(os.environ.get("QUOTIENT_MAX_TRANSITIONS", "2000000"))
MAX_LEVEL = int(os.environ.get("QUOTIENT_MAX_LEVEL", "900"))
OUTFILE = os.environ.get("QUOTIENT_OUTFILE", "excursion_quotient_report.json")
MAX_EXPORTED_OPEN = int(os.environ.get("QUOTIENT_MAX_EXPORTED_OPEN", "0"))
MAX_EXPORTED_RETURNS = int(os.environ.get("QUOTIENT_MAX_EXPORTED_RETURNS", "200"))


def compute_descent(r, k, max_steps=MAX_STEPS):
    a, b, c = 1, 0, 0
    n = r
    valid = True
    odd_count = 0
    for m in range(1, max_steps + 1):
        if c >= k:
            valid = False
        if n & 1 == 0:
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


def state_delta(o, c):
    return c - o * LOG2_3


def state_successors(state):
    residue, level, a, b, c, o, steps = state
    if c >= level:
        return [
            (residue, level + 1, a, b, c, o, steps),
            (residue + (1 << level), level + 1, a, b, c, o, steps),
        ]
    parity = ((a * residue + b) >> c) & 1
    if parity == 0:
        return [(residue, level, a, b, c + 1, o, steps + 1)]
    return [(residue, level, 3 * a, 3 * b + (1 << c), c, o + 1, steps + 1)]


def quotient_key(state):
    residue, level, a, b, c, o, _steps = state
    if c > level:
        return ("needs-branch", level - c, o - BASE_O, c - BASE_C, residue & ((1 << KMAX) - 1))
    s = level - c
    q = ((a * residue + b) >> c) & ((1 << s) - 1) if s else 0
    return (s, q, o - BASE_O, c - BASE_C)


def is_boundary_key(key):
    return isinstance(key, tuple) and len(key) == 4 and key[0] == 0


def max_run(word, symbol):
    best = cur = 0
    for ch in word:
        if ch == symbol:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def v2_sequence_from_parity_word(word):
    seq = []
    pending_odd = False
    zeros = 0
    for ch in word:
        if ch == "1":
            if pending_odd:
                seq.append(zeros)
            pending_odd = True
            zeros = 0
        elif pending_odd:
            zeros += 1
    if pending_odd:
        seq.append(zeros)
    return seq


def find_entries(parents):
    entries = []
    per_parent = Counter()
    for r0, kv, depth in parents:
        stack = [(r0, KMAX, 1, 0, 0, 0, 0)]
        nodes = 0
        while stack and len(entries) < MAX_ENTRIES:
            state = stack.pop()
            residue, level, _a, _b, c, o, steps = state
            nodes += 1
            if nodes > MAX_ENTRY_NODES:
                break
            if level >= MAX_LEVEL and c >= level:
                continue
            if steps >= MAX_STEPS:
                continue
            if o >= ENTRY_MIN_O and c <= math.floor(o * LOG2_3):
                entries.append((r0, kv, depth, state))
                per_parent[r0] += 1
                continue
            stack.extend(state_successors(state))
    return entries, per_parent


def classify_positive(state):
    residue, level, a, b, c, o, steps = state
    delta = state_delta(o, c)
    if delta <= 0:
        return None
    denom = (1 << c) - a
    B = (b + denom - 1) // denom
    return {
        "pair": (o, c),
        "delta": delta,
        "B": B,
        "B_ok": B <= B_LIMIT,
        "level": level,
        "m": steps,
        "lane16": residue & ((1 << KMAX) - 1),
    }


def frontier_summary(state):
    residue, level, a, b, c, o, steps = state
    delta = state_delta(o, c)
    item = {
        "key": quotient_key(state),
        "pair": (o, c),
        "delta": delta,
        "level": level,
        "m": steps,
        "lane16": residue & ((1 << KMAX) - 1),
    }
    denom = (1 << c) - a
    if denom > 0:
        item["B"] = (b + denom - 1) // denom
        item["B_ok"] = item["B"] <= B_LIMIT
    else:
        item["B"] = None
        item["B_ok"] = False
    return item


def boundary_successor_summary(state, limit=128):
    """Peek past a level boundary for diagnostics without using it as proof."""
    out = []
    for branched in state_successors(state):
        cur = branched
        path = ""
        for _ in range(limit):
            ret = classify_positive(cur)
            if ret is not None:
                out.append({"kind": "positive", "path": path, **ret})
                break
            key = quotient_key(cur)
            if isinstance(key, tuple) and len(key) == 4 and key[0] == 0:
                out.append({
                    "kind": "boundary",
                    "path": path,
                    "key": key,
                    "pair": (cur[5], cur[4]),
                    "delta": state_delta(cur[5], cur[4]),
                })
                break
            nxts = state_successors(cur)
            if len(nxts) != 1:
                out.append({"kind": "branch", "path": path, "key": key})
                break
            nxt = nxts[0]
            path += "1" if nxt[5] > cur[5] else "0"
            cur = nxt
        else:
            out.append({"kind": "limit", "path": path, "key": quotient_key(cur)})
    return out


def reconstruct_word(key, parents, edge_moves):
    parts = []
    cur = key
    while cur in parents and parents[cur] is not None:
        move = edge_moves.get(cur, "")
        if move:
            parts.append(move)
        cur = parents[cur]
    return "".join(reversed(parts))


def word_metadata(key, state, reason, parents, frontier_moves, parity_moves, min_deltas, previous_keys, ret=None):
    frontier_word = reconstruct_word(key, parents, frontier_moves)
    parity_word = reconstruct_word(key, parents, parity_moves)
    residue, level, a, b, c_state, o_state, _steps = state
    h = frontier_word.count("1")
    z = frontier_word.count("0")
    t = len(frontier_word)
    o, c = o_state, c_state
    positive = ret is not None
    gap = (1 << c) - a
    gap_positive = gap > 0
    exact_B = (b + gap - 1) // gap if gap_positive else None
    item = {
        **frontier_summary(state),
        "reason": reason,
        "accumulated_frontier_word": frontier_word,
        "frontier_word_prefix": frontier_word[:200],
        "frontier_word_suffix": frontier_word[-200:],
        "parity_word_prefix": parity_word[:200],
        "parity_word_suffix": parity_word[-200:],
        "word_length": t,
        "h": h,
        "z": z,
        "t": t,
        "h_over_t": h / t if t else 0.0,
        "o": o,
        "c": c,
        "min_delta_seen": min_deltas.get(key, state_delta(o, c)),
        "longest_run_1": max_run(frontier_word, "1"),
        "longest_run_0": max_run(frontier_word, "0"),
        "v2_sequence": v2_sequence_from_parity_word(parity_word)[-200:],
        "parent_key": previous_keys.get(key),
        "previous_key": previous_keys.get(key),
        "returned_to_positive_margin": positive,
        "return_B": ret["B"] if ret else None,
        "return_delta": ret["delta"] if ret else None,
        "affine": {
            "residue": str(residue),
            "level": level,
            "free_bits": max(0, level - c),
            "a": str(a),
            "b": str(b),
            "c": c,
            "o": o,
            "a_bit_length": a.bit_length(),
            "b_bit_length": b.bit_length(),
            "gap_sign": 1 if gap > 0 else (-1 if gap < 0 else 0),
            "gap": str(gap),
            "gap_abs_bit_length": abs(gap).bit_length(),
            "exact_B": exact_B,
            "B_ok": exact_B is not None and exact_B <= B_LIMIT,
            "three_pow_mod_2c": str(a % (1 << c)),
            "b_mod_2c": str(b % (1 << c)),
            "residue_low128": str(residue & ((1 << min(128, level)) - 1)),
        },
    }
    return item


def explore_quotient(entries):
    queue = deque()
    representatives = {}
    origins = defaultdict(set)
    parents = {}
    frontier_moves = {}
    parity_moves = {}
    previous_keys = {}
    last_boundary = {}
    min_deltas = {}
    for r0, kv, depth, state in entries:
        key = quotient_key(state)
        representatives.setdefault(key, state)
        origins[key].add((r0, kv, depth))
        parents.setdefault(key, None)
        frontier_moves.setdefault(key, "")
        parity_moves.setdefault(key, "")
        previous_keys.setdefault(key, None)
        last_boundary.setdefault(key, key if is_boundary_key(key) else None)
        min_deltas.setdefault(key, state_delta(state[5], state[4]))
        queue.append(key)

    transitions = {}
    returns = defaultdict(list)
    bad_B_positive = []
    conflicts = []
    open_keys = {}
    visits = 0

    while queue:
        key = queue.popleft()
        state = representatives[key]
        visits += 1
        if visits > MAX_TRANSITIONS:
            open_keys[key] = "transition_cap"
            break

        ret = classify_positive(state)
        if ret is not None:
            if ret["B_ok"]:
                returns[key].append(ret)
                continue
            if len(bad_B_positive) < 50:
                bad_B_positive.append(ret)

        residue, level, _a, _b, _c, _o, steps = state
        if level >= MAX_LEVEL and _c >= level:
            open_keys[key] = "level_cap"
            continue
        if steps >= MAX_STEPS:
            open_keys[key] = "step_cap"
            continue

        succ_keys = []
        for nxt in state_successors(state):
            nk = quotient_key(nxt)
            succ_keys.append(nk)
            if nk not in representatives:
                representatives[nk] = nxt
                parents[nk] = key
                previous_keys[nk] = key
                if nxt[5] > state[5]:
                    parity_moves[nk] = "1"
                elif nxt[4] > state[4]:
                    parity_moves[nk] = "0"
                else:
                    parity_moves[nk] = ""
                lb = last_boundary.get(key)
                move = ""
                if is_boundary_key(nk):
                    if lb is not None and lb in representatives:
                        base_state = representatives[lb]
                        if nxt[5] > base_state[5]:
                            move = "1"
                        elif nxt[4] > base_state[4]:
                            move = "0"
                    last_boundary[nk] = nk
                else:
                    last_boundary[nk] = key if is_boundary_key(key) else lb
                frontier_moves[nk] = move
                min_deltas[nk] = min(
                    min_deltas.get(key, state_delta(state[5], state[4])),
                    state_delta(nxt[5], nxt[4]),
                )
                queue.append(nk)
            else:
                # Validate that exact representatives with the same quotient have
                # the same one-step quotient successors. If not, key is too coarse.
                old_succ = [quotient_key(x) for x in state_successors(representatives[nk])]
                new_succ = [quotient_key(x) for x in state_successors(nxt)]
                if old_succ != new_succ and len(conflicts) < 20:
                    conflicts.append({
                        "key": nk,
                        "old_successors": old_succ,
                        "new_successors": new_succ,
                    })
        transitions[key] = succ_keys

    open_items = list(open_keys.items())
    if MAX_EXPORTED_OPEN > 0:
        open_items = open_items[:MAX_EXPORTED_OPEN]

    return_items = []
    for k, vals in returns.items():
        if len(return_items) >= MAX_EXPORTED_RETURNS:
            break
        for ret in vals:
            return_items.append(word_metadata(
                k, representatives[k], "return", parents, frontier_moves,
                parity_moves, min_deltas, previous_keys, ret=ret,
            ))
            if len(return_items) >= MAX_EXPORTED_RETURNS:
                break

    return {
        "n_entries": len(entries),
        "n_keys": len(representatives),
        "n_transitions": len(transitions),
        "n_return_keys": len(returns),
        "n_open_keys": len(open_keys),
        "conflicts": conflicts,
        "open_keys": {str(k): v for k, v in open_items},
        "open_frontier": [
            {
                **word_metadata(
                    k, representatives[k], reason, parents, frontier_moves,
                    parity_moves, min_deltas, previous_keys,
                ),
                "reason": reason,
                "boundary_successors": boundary_successor_summary(representatives[k])
                if reason == "level_cap" else [],
            }
            for k, reason in open_items
        ],
        "returned_frontier": return_items,
        "return_pairs": Counter(tuple(r["pair"]) for vals in returns.values() for r in vals),
        "bad_B_positive": bad_B_positive,
        "origins_sample": {str(k): list(v)[:5] for k, v in list(origins.items())[:20]},
    }


def main():
    t0 = time.time()
    parents = deep_open_parents()
    print("=" * 78)
    print("EXCURSION QUOTIENT ANALYZER")
    print("=" * 78)
    print(f"Parents              : {len(parents)}")
    print(f"Entry max nodes      : {MAX_ENTRY_NODES:,}")
    print(f"Max entries          : {MAX_ENTRIES:,}")
    print(f"Transition cap       : {MAX_TRANSITIONS:,}")
    print(f"Level cap            : {MAX_LEVEL}")
    print()

    entries, per_parent = find_entries(parents)
    print(f"Entries collected    : {len(entries)}")
    print(f"Parents with entries : {len(per_parent)}")
    print(f"Entry count sample   : {dict(per_parent.most_common(12))}")

    result = explore_quotient(entries)
    result["return_pairs"] = {str(k): v for k, v in result["return_pairs"].items()}
    result["parents"] = parents
    result["entry_count_by_parent"] = dict(per_parent)
    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print()
    print("SUMMARY")
    print(f"  Quotient keys       : {result['n_keys']:,}")
    print(f"  Transition keys     : {result['n_transitions']:,}")
    print(f"  Return keys         : {result['n_return_keys']:,}")
    print(f"  Open keys           : {result['n_open_keys']:,}")
    print(f"  Conflicts           : {len(result['conflicts'])}")
    print(f"  Bad-B positives     : {len(result['bad_B_positive'])}")
    print(f"  Return pairs        : {len(result['return_pairs'])} distinct")
    print(f"  Report              : {OUTFILE}")
    print(f"  Total time          : {time.time() - t0:.1f}s")

    if result["conflicts"]:
        print("\nQUOTIENT TOO COARSE: conflicts found.")
    elif result["n_open_keys"]:
        print("\nQUOTIENT INCOMPLETE: open keys remain under caps.")
    else:
        print("\nQUOTIENT CLOSED for collected entries.")


if __name__ == "__main__":
    main()
