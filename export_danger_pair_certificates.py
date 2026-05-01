"""
export_danger_pair_certificates.py
==================================
Export exact representative certificates for continued-fraction danger pairs.

The search is deterministic and starts from unresolved depth>18 parents. It
prints and writes one branch certificate per requested (o,c) pair.
"""

import json
import math
import time

KMAX = 16
MAX_STEPS = 10_000
MAX_K_VALID = 500
LOG2_3 = math.log2(3)
TARGET_PAIRS = [(29, 46), (147, 233), (200, 317), (253, 401), (306, 485)]
OUTFILE = "danger_pair_certificates.json"


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


def find_pair_certificate(pair, parents, max_nodes=5_000_000, max_level=520):
    target_o, target_c = pair
    for r0, kv, depth in parents:
        stack = [(r0, KMAX, 1, 0, 0, 0, 0, "")]
        nodes = 0
        while stack:
            residue, level, a, b, c, odd_count, steps, word = stack.pop()
            nodes += 1
            if nodes > max_nodes or steps >= MAX_STEPS or level >= max_level:
                continue

            if (odd_count, c) == pair and c - odd_count * LOG2_3 > 0:
                denom = (1 << c) - a
                B = (b + denom - 1) // denom
                j_mod_level = (residue - r0) >> KMAX
                return {
                    "pair": [target_o, target_c],
                    "parent_r0": r0,
                    "depth": depth,
                    "parent_k_prime": kv,
                    "branch_level": level,
                    "sibling_j_mod_2^(level-16)": str(j_mod_level),
                    "sibling_j_mod_2^depth": j_mod_level % (1 << depth),
                    "m": steps,
                    "o": odd_count,
                    "c": c,
                    "c_over_o": c / odd_count,
                    "delta": c - odd_count * LOG2_3,
                    "B": B,
                    "B_limit_margin": 200_001 - B,
                    "a": str(a),
                    "b": str(b),
                    "denominator": str(denom),
                    "formula": f"T^{steps}(n) = (3^{odd_count} * n + b) / 2^{c}",
                    "parity_word": word,
                    "first_200_parity_symbols": word[:200],
                    "nodes_in_parent_search": nodes,
                }

            delta = c - odd_count * LOG2_3
            if delta > 0:
                continue
            if c >= level:
                stack.append((residue + (1 << level), level + 1, a, b, c, odd_count, steps, word))
                stack.append((residue, level + 1, a, b, c, odd_count, steps, word))
                continue

            parity = ((a * residue + b) >> c) & 1
            if parity == 0:
                stack.append((residue, level, a, b, c + 1, odd_count, steps + 1, word + "0"))
            else:
                stack.append((residue, level, 3 * a, 3 * b + (1 << c), c, odd_count + 1, steps + 1, word + "1"))
    return None


def main():
    t0 = time.time()
    parents = deep_open_parents()
    certs = []
    print("=" * 72)
    print("DANGER PAIR CERTIFICATE EXPORT")
    print("=" * 72)
    print(f"Parents searched: {len(parents)}")
    print()
    for pair in TARGET_PAIRS:
        cert = find_pair_certificate(pair, parents)
        if cert is None:
            print(f"{pair}: NOT FOUND")
            continue
        certs.append(cert)
        print(f"{pair}: r0={cert['parent_r0']} d={cert['depth']} "
              f"k'={cert['parent_k_prime']} m={cert['m']} "
              f"B={cert['B']} delta={cert['delta']:.12f} "
              f"j_mod_depth={cert['sibling_j_mod_2^depth']}")

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(certs, f, indent=2)
    print()
    print(f"Wrote {OUTFILE}")
    print(f"Total time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
