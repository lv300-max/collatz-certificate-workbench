"""
frontier_recurrence_certificate.py
==================================
Exact recurrence check for the open quotient frontier.

The quotient analyzer exposed open states with s = level - c = 0, i.e. the
known parity prefix has consumed every known residue bit and another sibling
bit is needed.  At that boundary the next transition is symbolic and exact:

    F(u,v) -> F(u,   v+1)   via branch bit 0 then an even step
    F(u,v) -> F(u+1, v+1)   via branch bit 1 then an odd step followed by even

where u = o - 306 and v = c - 485.

This file verifies the recurrence against the concrete transition function and
then asks whether margin-only induction can close it.  It cannot: the all-1
branch drives delta by 1 - log2(3) < 0 forever.  Therefore the current quotient
state is a proof-support abstraction, not a parent-level certificate.
"""

import json
import math
import os

from excursion_quotient_analyzer import (
    BASE_C,
    BASE_O,
    KMAX,
    LOG2_3,
    quotient_key,
    state_successors,
)

REPORT = os.environ.get("FRONTIER_REPORT", "frontier_recurrence_report.json")
SAMPLE_STEPS = int(os.environ.get("FRONTIER_SAMPLE_STEPS", "64"))


def concrete_boundary_state(u, v):
    """Build a representative s=0 boundary state with c=level."""
    o = BASE_O + u
    c = BASE_C + v
    level = c
    residue = 1
    a = 3 ** o
    b = 0
    steps = o + c
    return residue, level, a, b, c, o, steps


def normalize_boundary_successors(state):
    """Follow each immediate branch until it returns to s=0."""
    out = []
    for branched in state_successors(state):
        cur = branched
        path = []
        while True:
            key = quotient_key(cur)
            if isinstance(key, tuple) and len(key) == 4 and key[0] == 0:
                _s, _q, u, v = key
                out.append((u, v, "".join(path), cur[5], cur[4]))
                break
            nxts = state_successors(cur)
            if len(nxts) != 1:
                raise RuntimeError(f"unexpected secondary branch at key={key}")
            nxt = nxts[0]
            path.append("1" if nxt[5] > cur[5] else "0")
            cur = nxt
    return sorted(out)


def verify_recurrence(samples):
    checks = []
    for u, v in samples:
        observed = normalize_boundary_successors(concrete_boundary_state(u, v))
        expected = sorted([
            (u, v + 1, "0", BASE_O + u, BASE_C + v + 1),
            (u + 1, v + 1, "10", BASE_O + u + 1, BASE_C + v + 1),
        ])
        checks.append({
            "u": u,
            "v": v,
            "observed": observed,
            "expected": expected,
            "ok": observed == expected,
        })
    return checks


def verify_reachable_frontier(report):
    checks = []
    for item in report.get("open_frontier", []):
        key = item["key"]
        if len(key) != 4 or key[0] != 0:
            continue
        _s, _q, u, v = key
        observed = sorted(
            (x["key"][2], x["key"][3], x["path"])
            for x in item.get("boundary_successors", [])
            if x.get("kind") == "boundary"
        )
        expected = sorted([(u, v + 1, "0"), (u + 1, v + 1, "10")])
        checks.append({
            "key": key,
            "pair": item["pair"],
            "observed": observed,
            "expected": expected,
            "ok": observed == expected,
        })
    return checks


def all_one_path(start_u, start_v, steps):
    path = []
    u, v = start_u, start_v
    for t in range(steps + 1):
        o = BASE_O + u
        c = BASE_C + v
        path.append({
            "t": t,
            "u": u,
            "v": v,
            "o": o,
            "c": c,
            "delta": c - o * LOG2_3,
            "c_over_o": c / o,
        })
        u += 1
        v += 1
    return path


def first_upper_candidates_after(o_min, limit):
    hits = []
    for o in range(o_min, limit + 1):
        c = math.ceil(o * LOG2_3)
        delta = c - o * LOG2_3
        if delta < 0.01:
            hits.append((delta, o, c, c / o))
    return sorted(hits)[:20]


def main():
    artificial_samples = [(0, 0), (1, 1), (1272, 2015), (1860, 3314)]
    artificial_checks = verify_recurrence(artificial_samples)

    # Use a real frontier sample from the latest quotient report if present.
    start = {"u": 1272, "v": 2015, "source": "default"}
    try:
        with open("excursion_quotient_report.json", "r", encoding="utf-8") as f:
            q = json.load(f)
        if q.get("open_frontier"):
            key = q["open_frontier"][0]["key"]
            start = {"u": key[2], "v": key[3], "source": "excursion_quotient_report.json"}
    except FileNotFoundError:
        pass

    one_path = all_one_path(start["u"], start["v"], SAMPLE_STEPS)
    result = {
        "reachable_recurrence": "F(u,v) -> F(u,v+1) and F(u+1,v+1)",
        "reachable_checks": verify_reachable_frontier(q) if "q" in locals() else [],
        "artificial_key_checks": artificial_checks,
        "quotient_key_alone_is_sufficient": False,
        "start": start,
        "all_one_branch_first": one_path[:12],
        "all_one_branch_last": one_path[-1],
        "all_one_delta_change_per_cycle": 1 - LOG2_3,
        "margin_only_closes": False,
        "reason": (
            "The all-1 branch has delta_{t+1}-delta_t = 1-log2(3) < 0, "
            "so a margin-only induction cannot force c/o above log2(3)."
        ),
        "next_upper_candidates": [
            {
                "delta": d,
                "o": o,
                "c": c,
                "c_over_o": ratio,
            }
            for d, o, c, ratio in first_upper_candidates_after(307, 4000)
        ],
    }

    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("=" * 78)
    print("FRONTIER RECURRENCE CERTIFICATE")
    print("=" * 78)
    reachable_ok = bool(result["reachable_checks"]) and all(x["ok"] for x in result["reachable_checks"])
    artificial_ok = all(x["ok"] for x in artificial_checks)
    print(f"Reachable recurrence: {reachable_ok} ({len(result['reachable_checks'])} frontier samples)")
    print(f"Key-alone recurrence: {artificial_ok}")
    print("Transition          : F(u,v) -> F(u,v+1), F(u+1,v+1) on reachable frontier")
    print(f"Start source        : {start['source']}")
    print(f"Start u,v           : ({start['u']}, {start['v']})")
    print(f"All-1 delta change  : {1 - LOG2_3:.12f}")
    print(f"All-1 last delta    : {one_path[-1]['delta']:.12f} at pair {(one_path[-1]['o'], one_path[-1]['c'])}")
    print("Margin-only closes  : False")
    print("Next tight upper candidates:")
    for item in result["next_upper_candidates"][:8]:
        print(f"  ({item['o']}, {item['c']}) delta={item['delta']:.12f}")
    print(f"Report              : {REPORT}")


if __name__ == "__main__":
    main()
