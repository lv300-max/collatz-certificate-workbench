#!/usr/bin/env python3
"""
Exact depth <=18 closure report.

This is the exact-enumeration layer from deep_sibling_closure_law.py, isolated
so it does not launch any sampled or symbolic depth >18 work. It uses no random
seeds. Proof decisions use Python integer arithmetic only:

  gap = 2^c - 3^o
  B   = ceil(b / gap) = (b + gap - 1) // gap

The optional delta field is diagnostic only.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any


KMAX = 16
MAX_STEPS = 10_000
MAX_K_VALID = 500
EXACT_DEPTH_CAP = 18
PRE_REPORT_EXACT_DEPTH_CAP = 14
B_LIMIT = 200_001
REPORT = Path("exact_depth_closure_report.json")
LOG2_3 = math.log2(3)  # display/debug only


def ceil_div(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("ceil_div denominator must be positive")
    return (a + b - 1) // b


def compute_descent(r: int, k: int, max_steps: int = MAX_STEPS) -> tuple[int, int, int, int, int, bool, int] | None:
    a = 1
    b = 0
    c = 0
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
            a *= 3
            b = 3 * b + (1 << c)
            n = 3 * n + 1
            odd_count += 1
        gap = (1 << c) - a
        if gap > 0:
            return (m, a, b, c, ceil_div(b, gap), valid, odd_count)
    return None


def find_valid_k(r: int, k_min: int = KMAX, max_k: int = MAX_K_VALID) -> tuple[int | None, tuple[int, int, int, int, int, bool, int] | None]:
    for k in range(k_min, max_k + 1):
        rep = r % (1 << k)
        if rep % 2 == 0:
            continue
        res = compute_descent(rep, k)
        if res is not None and res[5]:
            return k, res
    return None, None


def build_exact_parent_list() -> list[dict[str, Any]]:
    parents: list[dict[str, Any]] = []
    for r0 in range(1, 1 << KMAX, 2):
        res0 = compute_descent(r0, KMAX)
        if res0 is None or res0[5]:
            continue
        kv, res = find_valid_k(r0, k_min=KMAX)
        if kv is None or res is None:
            continue
        depth = kv - KMAX
        if 15 <= depth <= EXACT_DEPTH_CAP:
            parents.append(
                {
                    "r0": r0,
                    "k_prime": kv,
                    "depth": depth,
                    "parent_o": res[6],
                    "parent_c": res[3],
                    "parent_B": res[4],
                }
            )
    parents.sort(key=lambda r: (r["depth"], r["r0"]))
    return parents


def build_pre_report_exact_parent_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r0 in range(1, 1 << KMAX, 2):
        res0 = compute_descent(r0, KMAX)
        if res0 is None or res0[5]:
            continue
        kv, res = find_valid_k(r0, k_min=KMAX)
        if kv is None or res is None:
            continue
        depth = kv - KMAX
        if 0 < depth <= PRE_REPORT_EXACT_DEPTH_CAP:
            m, _a, b, c, B, valid, o = res
            rows.append(
                {
                    "r0": r0,
                    "k_prime": kv,
                    "depth": depth,
                    "status": "CLOSED_BY_EXACT_VALID_K",
                    "m": m,
                    "o": o,
                    "c": c,
                    "b": b,
                    "B": B,
                    "sampled": False,
                    "exact": True,
                    "valid": valid,
                    "coverage_source": "pre_report_exact_depth_parent",
                }
            )
    rows.sort(key=lambda r: (r["depth"], r["r0"]))
    return rows


def load_reusable_parent_rows() -> list[dict[str, Any]] | None:
    if not REPORT.exists():
        return None
    try:
        with REPORT.open("r", encoding="utf-8") as f:
            existing = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    rows = existing.get("parent_rows")
    if not isinstance(rows, list):
        return None
    if not rows:
        return None
    if any(row.get("closed") is not True for row in rows):
        return None
    if any(int(row.get("depth", -1)) < 15 or int(row.get("depth", -1)) > EXACT_DEPTH_CAP for row in rows):
        return None
    return rows


def enumerate_parent(parent: dict[str, Any]) -> dict[str, Any]:
    r0 = int(parent["r0"])
    depth = int(parent["depth"])
    n_siblings = 1 << depth
    failures: list[dict[str, Any]] = []
    max_k = 0
    max_B = 0
    min_delta = math.inf
    b_over_limit: list[dict[str, Any]] = []
    exact_formula_checks = 0

    for j in range(n_siblings):
        sibling = r0 + j * (1 << KMAX)
        kf, res = find_valid_k(sibling, k_min=KMAX)
        if kf is None or res is None:
            failures.append({"j": j, "sibling": sibling, "reason": "no_valid_k"})
            continue
        _, a, b, c, B, valid, o = res
        gap = (1 << c) - (3 ** o)
        reasons: list[str] = []
        if a != 3 ** o:
            reasons.append("a != 3^o")
        if gap <= 0:
            reasons.append("gap <= 0")
        else:
            exact_B = ceil_div(b, gap)
            if exact_B != B:
                reasons.append("reported B disagrees with exact integer ceiling")
        if not valid:
            reasons.append("residue certificate invalid at k")
        if reasons:
            failures.append({"j": j, "sibling": sibling, "k": kf, "reasons": reasons})
            continue

        exact_formula_checks += 1
        max_k = max(max_k, kf)
        max_B = max(max_B, B)
        min_delta = min(min_delta, c - o * LOG2_3)
        if B > B_LIMIT and len(b_over_limit) < 20:
            b_over_limit.append({"j": j, "sibling": sibling, "k": kf, "B": B, "o": o, "c": c})

    return {
        "r0": r0,
        "k_prime": parent["k_prime"],
        "depth": depth,
        "siblings": n_siblings,
        "exact_formula_checks": exact_formula_checks,
        "failures": len(failures),
        "failure_examples": failures[:20],
        "closed": len(failures) == 0,
        "max_k": max_k,
        "max_B": max_B,
        "min_delta": None if min_delta == math.inf else min_delta,
        "b_over_limit_examples": b_over_limit,
    }


def main() -> None:
    started = time.time()
    print("EXACT DEPTH CLOSURE")
    print(f"  Depth cap          : {EXACT_DEPTH_CAP}")
    print(f"  Random seeds       : none")
    print(f"  Sampled rows used  : none")
    print()

    pre_report_rows = build_pre_report_exact_parent_rows()
    parents = build_exact_parent_list()
    depth_counts = Counter(p["depth"] for p in parents)
    pre_report_depth_counts = Counter(p["depth"] for p in pre_report_rows)
    print(f"Pre-report exact parents found : {len(pre_report_rows)}")
    for depth in sorted(pre_report_depth_counts):
        print(f"  depth {depth}: {pre_report_depth_counts[depth]} parents")
    print(f"Exact parents found : {len(parents)}")
    for depth in sorted(depth_counts):
        print(f"  depth {depth}: {depth_counts[depth]} parents, {1 << depth:,} siblings each")
    print()

    parent_rows: list[dict[str, Any]] = []
    total_siblings = 0
    exact_failures = 0
    exact_parents_closed = 0
    max_depth_closed = 0
    max_B = 0
    max_k = 0
    min_delta = math.inf
    b_over_limit_count = 0

    reusable_rows = load_reusable_parent_rows()
    if reusable_rows is not None:
        print()
        print(f"Reusing existing depth 15-{EXACT_DEPTH_CAP} parent_rows from {REPORT}")
        parent_rows = reusable_rows
        for row in parent_rows:
            total_siblings += row["siblings"]
            exact_failures += row["failures"]
            max_B = max(max_B, row["max_B"])
            max_k = max(max_k, row["max_k"])
            if row["min_delta"] is not None:
                min_delta = min(min_delta, row["min_delta"])
            b_over_limit_count += len(row["b_over_limit_examples"])
            if row["closed"]:
                exact_parents_closed += 1
                max_depth_closed = max(max_depth_closed, row["depth"])
    else:
        for i, parent in enumerate(parents, 1):
            t0 = time.time()
            row = enumerate_parent(parent)
            row["elapsed_seconds"] = round(time.time() - t0, 3)
            parent_rows.append(row)

            total_siblings += row["siblings"]
            exact_failures += row["failures"]
            max_B = max(max_B, row["max_B"])
            max_k = max(max_k, row["max_k"])
            if row["min_delta"] is not None:
                min_delta = min(min_delta, row["min_delta"])
            b_over_limit_count += len(row["b_over_limit_examples"])
            if row["closed"]:
                exact_parents_closed += 1
                max_depth_closed = max(max_depth_closed, row["depth"])

            if i % 10 == 0 or not row["closed"]:
                status = "CLOSED" if row["closed"] else f"FAIL({row['failures']})"
                print(
                    f"  [{i:3d}/{len(parents)}] r0={row['r0']:6d} depth={row['depth']:2d} "
                    f"siblings={row['siblings']:,} max_k={row['max_k']:3d} "
                    f"max_B={row['max_B']:6d} {status} ({row['elapsed_seconds']:.1f}s)",
                    flush=True,
                )

    sampled_rows_used = 0
    formula_checks = sum(r["exact_formula_checks"] for r in parent_rows)
    final_status = (
        "PASS_EXACT_DEPTH"
        if max_depth_closed >= EXACT_DEPTH_CAP
        and exact_parents_closed == len(parents)
        and exact_failures == 0
        and sampled_rows_used == 0
        and max_B <= B_LIMIT
        else "INCOMPLETE"
    )

    summary = {
        "max_exact_depth_closed": max_depth_closed,
        "exact_parents_closed": exact_parents_closed,
        "exact_parents_total": len(parents),
        "exact_siblings_verified": total_siblings,
        "exact_formula_checks": formula_checks,
        "exact_failures": exact_failures,
        "max_B": max_B,
        "max_k_needed": max_k,
        "min_delta": None if min_delta == math.inf else min_delta,
        "sampled_rows_used": sampled_rows_used,
        "b_over_limit_example_count": b_over_limit_count,
        "final_status": final_status,
    }
    report = {
        "method": {
            "source": "exact_depth_closure.py",
            "derived_from": "exact enumeration layer of deep_sibling_closure_law.py",
            "random_seeds": False,
            "global_caps_increased": False,
            "sampled_rows_used": False,
            "integer_checks_only_for_proof": True,
            "gap_formula": "gap = 2^c - 3^o",
            "B_formula": "B = (b + gap - 1) // gap",
            "delta_is_diagnostic_only": True,
            "MAX_STEPS": MAX_STEPS,
            "MAX_K_VALID": MAX_K_VALID,
            "KMAX": KMAX,
            "pre_report_exact_depth_cap": PRE_REPORT_EXACT_DEPTH_CAP,
            "exact_depth_cap": EXACT_DEPTH_CAP,
            "B_LIMIT": B_LIMIT,
        },
        "summary": summary,
        "pre_report_exact_depth_summary": {
            "pre_report_exact_depth_parent_rows": len(pre_report_rows),
            "depth_counts": dict(sorted(pre_report_depth_counts.items())),
            "sampled_rows_used": 0,
            "fields": ["r0", "k_prime", "depth", "status", "m", "o", "c", "b", "B", "sampled"],
        },
        "pre_report_exact_parent_rows": pre_report_rows,
        "depth_counts": dict(sorted(depth_counts.items())),
        "parent_rows": parent_rows,
        "plain_truth": (
            "This report certifies only the exact depth <=18 layer by exhaustive sibling enumeration. "
            "It uses no sampled evidence and does not claim the full theorem is proven."
        ),
        "runtime_seconds": round(time.time() - started, 3),
    }
    with REPORT.open("w") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print()
    print("EXACT DEPTH SUMMARY")
    print(f"  Exact parents closed     : {exact_parents_closed} / {len(parents)}")
    print(f"  Exact siblings verified  : {total_siblings:,}")
    print(f"  Exact failures           : {exact_failures}")
    print(f"  Max depth exact closed   : {max_depth_closed}")
    print(f"  Max B                    : {max_B}")
    print(f"  Min delta                : {summary['min_delta']}")
    print(f"  Final status             : {final_status}")


if __name__ == "__main__":
    main()
