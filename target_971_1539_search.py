"""
target_971_1539_search.py
=========================
Targeted symbolic search for the next upper danger pair after 306/485:
(o,c) = (971,1539).

Unlike cf_danger_search.py, this does not stop at earlier positive-margin
certificates; it keeps extending branches until the target pair is found or a
cap is reached.
"""

import math
import os
import time

KMAX = 16
LOG2_3 = math.log2(3)
TARGET = (971, 1539)
MAX_NODES = int(os.environ.get("TARGET_971_MAX_NODES", "5000000"))
MAX_LEVEL = int(os.environ.get("TARGET_971_MAX_LEVEL", "1600"))
MAX_STEPS = int(os.environ.get("TARGET_971_MAX_STEPS", "2600"))
PARENTS = [871, 1743, 3567, 4207, 5147, 5567, 5759, 6655, 7167, 8415, 10235, 10599]


def search_parent(r0):
    stack = [(r0, KMAX, 1, 0, 0, 0, 0, "")]
    nodes = 0
    best_positive = (math.inf, None)
    first_below = None

    while stack:
        residue, level, a, b, c, o, steps, word = stack.pop()
        nodes += 1
        delta = c - o * LOG2_3

        if (o, c) == TARGET:
            denom = (1 << c) - a
            B = (b + denom - 1) // denom
            return {
                "hit": True,
                "r0": r0,
                "nodes": nodes,
                "residue": residue,
                "level": level,
                "m": steps,
                "o": o,
                "c": c,
                "delta": delta,
                "B": B,
                "a": a,
                "b": b,
                "word": word,
            }

        if o >= 307 and c <= math.floor(o * LOG2_3) and first_below is None:
            first_below = (residue, level, steps, o, c, delta)

        if delta > 0 and delta < best_positive[0]:
            best_positive = (delta, (o, c, steps, level))

        if nodes > MAX_NODES:
            return {
                "hit": False,
                "r0": r0,
                "nodes": nodes,
                "reason": "node_cap",
                "best_positive": best_positive,
                "first_below": first_below,
            }
        if level >= MAX_LEVEL:
            continue
        if steps >= MAX_STEPS:
            continue
        if o > TARGET[0] or c > TARGET[1]:
            continue

        if c >= level:
            stack.append((residue + (1 << level), level + 1, a, b, c, o, steps, word))
            stack.append((residue, level + 1, a, b, c, o, steps, word))
            continue

        parity = ((a * residue + b) >> c) & 1
        if parity == 0:
            stack.append((residue, level, a, b, c + 1, o, steps + 1, word + "0"))
        else:
            stack.append((residue, level, 3 * a, 3 * b + (1 << c), c, o + 1, steps + 1, word + "1"))

    return {
        "hit": False,
        "r0": r0,
        "nodes": nodes,
        "reason": "exhausted",
        "best_positive": best_positive,
        "first_below": first_below,
    }


def main():
    t0 = time.time()
    print("=" * 72)
    print("TARGETED (971,1539) SEARCH")
    print("=" * 72)
    print(f"Target delta      : {TARGET[1] - TARGET[0] * LOG2_3:.12f}")
    print(f"Node cap / parent : {MAX_NODES:,}")
    print(f"Level cap         : {MAX_LEVEL}")
    print()
    for r0 in PARENTS:
        res = search_parent(r0)
        if res["hit"]:
            print(f"HIT r0={r0} nodes={res['nodes']:,} level={res['level']} "
                  f"m={res['m']} B={res['B']} delta={res['delta']:.12f}")
            print(f"first200={res['word'][:200]}")
            break
        best = res["best_positive"]
        print(f"OPEN r0={r0} nodes={res['nodes']:,} reason={res['reason']} "
              f"best={best} first_below={res['first_below'] is not None}", flush=True)
    print(f"\nTotal time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
