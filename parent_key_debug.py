"""
parent_key_debug.py
===================
Focused debug for parent r0=5759 and uncovered quotient key [1, 1, 2124, 1979].

The script reruns only this parent with the artifact caps used by the current
frontier report, finds the target key, and then continues locally from the exact
representative state.

No random seeds.  No global cap increases.  No proof-complete claim.
"""

import json
import math
import os
import time
from collections import Counter, deque

import excursion_quotient_analyzer as eqa

TARGET_PARENT = (5759, 35, 19)
TARGET_KEY = (1, 1, 2124, 1979)
OUTFILE = "parent_key_debug_5759.json"
B_LIMIT = 200_001

ARTIFACT_MAX_LEVEL = 2500
ARTIFACT_MAX_TRANSITIONS = 3_161_208
ARTIFACT_MAX_ENTRIES = 100
LOCAL_MAX_TRANSITIONS = int(os.environ.get("PARENT_KEY_LOCAL_MAX_TRANSITIONS", "500000"))
LOCAL_MAX_DEPTH = int(os.environ.get("PARENT_KEY_LOCAL_MAX_DEPTH", "128"))


def key_list(key):
    return [int(x) for x in key]


def ceil_div(a, b):
    if b <= 0:
        raise ValueError("ceil_div denominator must be positive")
    return (a + b - 1) // b


def exact_delta_sign(o, c):
    g = (1 << c) - (3 ** o)
    return 1 if g > 0 else (-1 if g < 0 else 0)


def bounded_int(value, max_digits=160):
    text = str(value)
    if len(text) <= max_digits:
        return text
    return {"digits": len(text), "prefix": text[:80], "suffix": text[-80:]}


def apply_artifact_caps():
    before = {
        "MAX_LEVEL": eqa.MAX_LEVEL,
        "MAX_TRANSITIONS": eqa.MAX_TRANSITIONS,
        "MAX_ENTRIES": eqa.MAX_ENTRIES,
    }
    eqa.MAX_LEVEL = ARTIFACT_MAX_LEVEL
    eqa.MAX_TRANSITIONS = ARTIFACT_MAX_TRANSITIONS
    eqa.MAX_ENTRIES = ARTIFACT_MAX_ENTRIES
    after = {
        "MAX_LEVEL": eqa.MAX_LEVEL,
        "MAX_TRANSITIONS": eqa.MAX_TRANSITIONS,
        "MAX_ENTRIES": eqa.MAX_ENTRIES,
    }
    return {"before": before, "after": after}


def max_run(word, symbol):
    best = cur = 0
    for ch in word:
        if ch == symbol:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def reconstruct_word(key, parents, edge_moves):
    parts = []
    cur = key
    while cur in parents and parents[cur] is not None:
        move = edge_moves.get(cur, "")
        if move:
            parts.append(move)
        cur = parents[cur]
    return "".join(reversed(parts))


def classify_positive_state(state):
    residue, level, a, b, c, o, steps = state
    g = (1 << c) - a
    if g <= 0:
        return None
    B = ceil_div(b, g)
    return {
        "pair": [o, c],
        "level": level,
        "steps": steps,
        "gap": str(g),
        "gap_bit_length": g.bit_length(),
        "B": B,
        "B_ok": B <= B_LIMIT,
    }


def local_continue_from_state(start_state):
    """
    Continue from one exact representative.  This is not a global cap increase:
    the search starts at the target key only and records if it needs more local
    budget.
    """
    queue = deque([(start_state, "")])
    seen = {eqa.quotient_key(start_state)}
    visits = 0
    positives = []
    conflicts = []
    open_local = []
    first_boundary = None

    while queue:
        state, suffix = queue.popleft()
        visits += 1
        ret = classify_positive_state(state)
        if ret:
            positives.append({**ret, "suffix": suffix})
            if ret["B_ok"]:
                return {
                    "classification": "CERTIFIED_RETURN",
                    "visits": visits,
                    "first_positive": positives[0],
                    "certified_positive": {**ret, "suffix": suffix},
                    "positives_seen": positives[:20],
                    "conflicts": conflicts,
                    "open_local": open_local,
                }

        if visits >= LOCAL_MAX_TRANSITIONS:
            open_local.append({
                "reason": "local_transition_cap",
                "key": key_list(eqa.quotient_key(state)),
                "suffix": suffix,
            })
            break
        if len(suffix) >= LOCAL_MAX_DEPTH:
            open_local.append({
                "reason": "local_depth_cap",
                "key": key_list(eqa.quotient_key(state)),
                "suffix": suffix,
            })
            continue

        successors = eqa.state_successors(state)
        for nxt in successors:
            move = ""
            if nxt[5] > state[5]:
                move = "1"
            elif nxt[4] > state[4]:
                move = "0"
            nk = eqa.quotient_key(nxt)
            if isinstance(nk, tuple) and len(nk) == 4 and nk[0] == 0 and first_boundary is None:
                first_boundary = {
                    "key": key_list(nk),
                    "pair": [nxt[5], nxt[4]],
                    "suffix": suffix + move,
                }
            if nk in seen:
                continue
            seen.add(nk)
            queue.append((nxt, suffix + move))

    first_positive = positives[0] if positives else None
    if first_positive and first_positive["B"] > B_LIMIT:
        # Apply the same exact B-control one-return diagnostic used elsewhere.
        o, c = first_positive["pair"]
        _residue, _level, _a, b, _c0, _o0, _steps = start_state
        # The positive reached by normal state transitions already has its own b
        # in the queued state, so recover it by replaying the suffix.
        cur = start_state
        for ch in first_positive["suffix"]:
            nxts = eqa.state_successors(cur)
            if len(nxts) == 1:
                cur = nxts[0]
            else:
                idx = 1 if ch == "1" else 0
                # state_successors at a branch returns residue then residue+bit;
                # the odd/even move label is safer than list order.
                matching = []
                for nxt in nxts:
                    label = "1" if nxt[5] > cur[5] else ("0" if nxt[4] > cur[4] else "")
                    if label == ch:
                        matching.append(nxt)
                cur = matching[0] if matching else nxts[idx]
        _r, _lvl, _a, b, c, o, _st = cur
        bctrl = one_then_zero_return(o, c, b)
        if bctrl["B"] <= B_LIMIT:
            return {
                "classification": "HIGH_B_RETURN_THEN_CERTIFIED",
                "visits": visits,
                "first_positive": first_positive,
                "b_control_next": bctrl,
                "positives_seen": positives[:20],
                "first_boundary": first_boundary,
                "conflicts": conflicts,
                "open_local": open_local,
            }
    return {
        "classification": "NEEDS_HIGHER_LOCAL_CAP" if open_local else "STILL_DEBT",
        "visits": visits,
        "first_positive": first_positive,
        "positives_seen": positives[:20],
        "first_boundary": first_boundary,
        "conflicts": conflicts,
        "open_local": open_local,
    }


def one_then_zero_return(o, c, b):
    old_c = c
    o += 1
    c += 1
    b = 3 * b + (1 << old_c)
    g = (1 << c) - (3 ** o)
    zeros = 0
    while g <= 0:
        c += 1
        zeros += 1
        g = (1 << c) - (3 ** o)
    B = ceil_div(b, g)
    return {
        "suffix": "1" + ("0" * min(zeros, 256)),
        "suffix_truncated": zeros > 256,
        "zeros_after_one": zeros,
        "pair": [o, c],
        "gap": str(g),
        "gap_bit_length": g.bit_length(),
        "B": B,
        "B_ok": B <= B_LIMIT,
    }


def zero_return_from_state(state):
    _residue, _level, a, b, c, o, _steps = state
    g = (1 << c) - a
    zeros = 0
    while g <= 0:
        c += 1
        zeros += 1
        g = (1 << c) - a
    B = ceil_div(b, g)
    return {
        "suffix": "0" * min(zeros, 256),
        "suffix_truncated": zeros > 256,
        "zeros": zeros,
        "pair": [o, c],
        "gap": str(g),
        "gap_bit_length": g.bit_length(),
        "B": B,
        "B_ok": B <= B_LIMIT,
    }


def exact_frontier_return_from_key(state):
    """
    The target key has s=1 and q=1, so its immediate deterministic successor is
    an odd step.  After that, compute the first all-zero frontier return exactly.
    """
    successors = eqa.state_successors(state)
    if len(successors) != 1:
        return {"ok": False, "reason": "target key branches immediately"}
    odd_state = successors[0]
    if odd_state[5] <= state[5]:
        return {"ok": False, "reason": "target key did not take the expected odd successor"}
    direct_zero = zero_return_from_state(state)
    after_one_zero = zero_return_from_state(odd_state)
    b_control = None
    if after_one_zero["B"] > B_LIMIT:
        _residue, _level, _a, b, c, o, _steps = odd_state
        # Move to the returned positive state first.
        c = after_one_zero["pair"][1]
        b_control = one_then_zero_return(o, c, b)
    if after_one_zero["B_ok"]:
        classification = "CERTIFIED_RETURN"
    elif b_control and b_control["B_ok"]:
        classification = "HIGH_B_RETURN_THEN_CERTIFIED"
    else:
        classification = "STILL_DEBT" if after_one_zero["B"] is None else "NEEDS_HIGHER_LOCAL_CAP"
    return {
        "ok": True,
        "immediate_successor": {
            "move": "1",
            "key": key_list(eqa.quotient_key(odd_state)),
            "pair": [odd_state[5], odd_state[4]],
            "gap_sign": exact_delta_sign(odd_state[5], odd_state[4]),
        },
        "direct_zero_return_from_target": direct_zero,
        "one_then_zero_return": after_one_zero,
        "b_control_next": b_control,
        "classification": classification,
    }


def rerun_parent_with_tracking():
    entries, per_parent = eqa.find_entries([TARGET_PARENT])
    queue = deque()
    representatives = {}
    parents = {}
    frontier_moves = {}
    parity_moves = {}
    min_deltas = {}
    open_keys = {}
    transitions = {}
    conflicts = []
    target_seen = False
    target_state = None
    target_reason = None
    visits = 0

    for _r0, _kv, _depth, state in entries:
        key = eqa.quotient_key(state)
        representatives.setdefault(key, state)
        parents.setdefault(key, None)
        frontier_moves.setdefault(key, "")
        parity_moves.setdefault(key, "")
        min_deltas.setdefault(key, eqa.state_delta(state[5], state[4]))
        queue.append(key)

    while queue:
        key = queue.popleft()
        state = representatives[key]
        visits += 1
        if key == TARGET_KEY and not target_seen:
            target_seen = True
            target_state = state

        if visits > eqa.MAX_TRANSITIONS:
            open_keys[key] = "transition_cap"
            if key == TARGET_KEY:
                target_reason = "transition_cap"
            break

        ret = eqa.classify_positive(state)
        if ret is not None and ret["B_ok"]:
            continue

        residue, level, _a, _b, c, _o, steps = state
        if level >= eqa.MAX_LEVEL and c >= level:
            open_keys[key] = "level_cap"
            if key == TARGET_KEY:
                target_reason = "level_cap"
            continue
        if steps >= eqa.MAX_STEPS:
            open_keys[key] = "step_cap"
            if key == TARGET_KEY:
                target_reason = "step_cap"
            continue

        succ_keys = []
        for nxt in eqa.state_successors(state):
            nk = eqa.quotient_key(nxt)
            succ_keys.append(nk)
            if nk not in representatives:
                representatives[nk] = nxt
                parents[nk] = key
                if nxt[5] > state[5]:
                    parity_moves[nk] = "1"
                elif nxt[4] > state[4]:
                    parity_moves[nk] = "0"
                else:
                    parity_moves[nk] = ""
                move = ""
                if isinstance(nk, tuple) and len(nk) == 4 and nk[0] == 0:
                    if nxt[5] > state[5]:
                        move = "1"
                    elif nxt[4] > state[4]:
                        move = "0"
                frontier_moves[nk] = move
                min_deltas[nk] = min(
                    min_deltas.get(key, eqa.state_delta(state[5], state[4])),
                    eqa.state_delta(nxt[5], nxt[4]),
                )
                queue.append(nk)
            else:
                old_succ = [eqa.quotient_key(x) for x in eqa.state_successors(representatives[nk])]
                new_succ = [eqa.quotient_key(x) for x in eqa.state_successors(nxt)]
                if old_succ != new_succ and len(conflicts) < 20:
                    conflicts.append({
                        "key": key_list(nk),
                        "old_successors": [key_list(x) for x in old_succ],
                        "new_successors": [key_list(x) for x in new_succ],
                    })
        transitions[key] = succ_keys

    if TARGET_KEY in open_keys and target_reason is None:
        target_reason = open_keys[TARGET_KEY]
    if target_state is None and TARGET_KEY in representatives:
        target_state = representatives[TARGET_KEY]

    word = reconstruct_word(TARGET_KEY, parents, frontier_moves) if TARGET_KEY in parents else ""
    parity_word = reconstruct_word(TARGET_KEY, parents, parity_moves) if TARGET_KEY in parents else ""
    return {
        "entries": entries,
        "per_parent": per_parent,
        "visits": visits,
        "representatives": representatives,
        "open_keys": open_keys,
        "transitions": transitions,
        "conflicts": conflicts,
        "target_seen": target_seen or TARGET_KEY in representatives,
        "target_state": target_state,
        "target_reason": target_reason,
        "frontier_word": word,
        "parity_word": parity_word,
        "open_reason_counts": Counter(open_keys.values()),
    }


def main():
    t0 = time.time()
    cap_info = apply_artifact_caps()
    rerun = rerun_parent_with_tracking()
    state = rerun["target_state"]

    if state is None:
        local = None
        target_summary = None
        final_classification = "NEEDS_HIGHER_LOCAL_CAP"
        exact_reason = "target key was not reached in the parent-local rerun"
    else:
        residue, level, a, b, c, o, steps = state
        g = (1 << c) - a
        B = ceil_div(b, g) if g > 0 else None
        local = local_continue_from_state(state)
        exact_frontier_return = exact_frontier_return_from_key(state)
        if exact_frontier_return.get("ok"):
            final_classification = exact_frontier_return["classification"]
        else:
            final_classification = local["classification"]
        if rerun["target_reason"] == "transition_cap":
            exact_reason = (
                "The key is uncovered because the parent-local quotient exploration "
                "hit the transition cap before exporting/return-mapping this "
                "non-boundary open key."
            )
        elif rerun["target_reason"]:
            exact_reason = f"The key is open with reason {rerun['target_reason']}."
        else:
            exact_reason = (
                "The key was reached as an internal non-boundary quotient key; it "
                "is absent from the global return map, which only covered exported "
                "open frontier keys from the global artifact."
            )
        target_summary = {
            "key": key_list(TARGET_KEY),
            "residue": str(residue),
            "level": level,
            "o": o,
            "c": c,
            "steps": steps,
            "delta_float_diagnostic": c - o * math.log2(3),
            "gap_sign": 1 if g > 0 else (-1 if g < 0 else 0),
            "gap": bounded_int(g),
            "gap_abs_bit_length": abs(g).bit_length(),
            "B_if_gap_positive": B,
            "B_ok": B is not None and B <= B_LIMIT,
            "frontier_word": rerun["frontier_word"],
            "frontier_word_length": len(rerun["frontier_word"]),
            "frontier_word_prefix": rerun["frontier_word"][:200],
            "frontier_word_suffix": rerun["frontier_word"][-200:],
            "parity_word_prefix": rerun["parity_word"][:200],
            "parity_word_suffix": rerun["parity_word"][-200:],
            "longest_run_1": max_run(rerun["frontier_word"], "1"),
            "longest_run_0": max_run(rerun["frontier_word"], "0"),
            "open_reason": rerun["target_reason"],
        }

    report = {
        "target": {
            "parent": {
                "r0": TARGET_PARENT[0],
                "k_prime": TARGET_PARENT[1],
                "depth": TARGET_PARENT[2],
            },
            "key": key_list(TARGET_KEY),
        },
        "caps": {
            "artifact_caps": cap_info,
            "local_continuation_max_transitions": LOCAL_MAX_TRANSITIONS,
            "local_continuation_max_depth": LOCAL_MAX_DEPTH,
            "random_seeds": False,
            "global_caps_increased": False,
        },
        "parent_rerun": {
            "entries": len(rerun["entries"]),
            "entry_count_by_parent": dict(rerun["per_parent"]),
            "visits": rerun["visits"],
            "open_key_count": len(rerun["open_keys"]),
            "open_reason_counts": dict(rerun["open_reason_counts"]),
            "conflict_count": len(rerun["conflicts"]),
            "conflicts": rerun["conflicts"],
        },
        "key_found": bool(rerun["target_seen"]),
        "target_state": target_summary,
        "local_continuation": local,
        "exact_frontier_return": exact_frontier_return if state is not None else None,
        "final_classification": final_classification,
        "exact_reason_uncovered": exact_reason,
        "recommended_fix_to_batcher": (
            "Yes. The batcher should not treat coverage only by existing global "
            "frontier_return_map keys as final. For parent-local uncovered keys, "
            "it should invoke this same local-key continuation and B-control "
            "classification, then record the resulting certificate or local cap "
            "blocker per key."
        ),
        "diagnostic_not_proof": True,
        "runtime_seconds": time.time() - t0,
    }

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 78)
    print("PARENT KEY DEBUG r0=5759")
    print("=" * 78)
    print(f"Key found               : {report['key_found']}")
    if target_summary:
        print(f"Exact o,c               : ({target_summary['o']}, {target_summary['c']})")
        print(f"Delta diagnostic        : {target_summary['delta_float_diagnostic']:.12f}")
        print(f"Frontier word length    : {target_summary['frontier_word_length']}")
        print(f"Gap sign                : {target_summary['gap_sign']}")
        print(f"B if gap > 0            : {target_summary['B_if_gap_positive']}")
        print(f"B <= {B_LIMIT:,}           : {target_summary['B_ok']}")
        print(f"Open reason             : {target_summary['open_reason']}")
    if local:
        print(f"Return classification   : {local['classification']}")
        print(f"First positive          : {local.get('first_positive')}")
        print(f"B-control next          : {local.get('b_control_next')}")
    if report.get("exact_frontier_return"):
        exact_return = report["exact_frontier_return"]
        print(f"Exact frontier return   : {exact_return.get('classification')}")
        print(f"One-then-zero return    : {exact_return.get('one_then_zero_return')}")
        print(f"Exact B-control next    : {exact_return.get('b_control_next')}")
    print(f"Exact reason uncovered  : {exact_reason}")
    print("Recommended fix         : local-key continuation in batcher is the right next step")
    print(f"Report                  : {OUTFILE}")


if __name__ == "__main__":
    main()
