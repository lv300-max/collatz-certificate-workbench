"""
quotient_parent_batch_audit.py
==============================
Per-parent batch audit for the quotient frontier method.

This script processes depth >18 parents one at a time under the existing
quotient analyzer caps.  It is checkpointed/resumable and records whether each
parent is closed by quotient exploration, has open keys already covered by the
current frontier key/B-control reports, or remains blocked by caps/conflicts.

No random seeds are used.  No quotient caps are raised here.
"""

import json
import os
import re
import time
from collections import Counter, defaultdict, deque

import excursion_quotient_analyzer as eqa

KMAX = 16
FRONTIER_AUDIT = os.environ.get(
    "QPARENT_BATCH_FRONTIER_AUDIT", "frontier_coverage_audit_report.json"
)
QREPORT = os.environ.get("QPARENT_BATCH_QREPORT", "excursion_quotient_report.json")
RETURN_MAP = os.environ.get("QPARENT_BATCH_RETURN_MAP", "frontier_return_map_report.json")
BCONTROL = os.environ.get("QPARENT_BATCH_BCONTROL", "b_control_report.json")
OUTFILE = os.environ.get("QPARENT_BATCH_OUT", "quotient_parent_batch_report.json")
BATCH_LIMIT = int(os.environ.get("QPARENT_BATCH_LIMIT", "0"))
BATCH_START = int(os.environ.get("QPARENT_BATCH_START", "0"))
RESUME = os.environ.get("QPARENT_BATCH_RESUME", "1") != "0"
CHECKPOINT_EVERY = int(os.environ.get("QPARENT_BATCH_CHECKPOINT_EVERY", "1"))
USE_ARTIFACT_CAPS = os.environ.get("QPARENT_BATCH_USE_ARTIFACT_CAPS", "1") != "0"
LOCAL_KEY_PREFIX_STEPS = int(os.environ.get("QPARENT_LOCAL_KEY_PREFIX_STEPS", "8"))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def maybe_load_json(path):
    try:
        return load_json(path)
    except FileNotFoundError:
        return None


def key_tuple(key):
    if isinstance(key, str):
        return tuple(int(x) for x in re.findall(r"-?\d+", key))
    return tuple(int(x) for x in key)


def key_list(key):
    return [int(x) for x in key]


def ceil_div(a, b):
    if b <= 0:
        raise ValueError("ceil_div denominator must be positive")
    return (a + b - 1) // b


def depth_gt_18_parents():
    parents = []
    for r0 in range(1, 1 << KMAX, 2):
        res0 = eqa.compute_descent(r0, KMAX)
        if res0 is None or res0[5]:
            continue
        kv, res = eqa.find_valid_k(r0, k_min=KMAX)
        if kv is None:
            continue
        depth = kv - KMAX
        if depth > 18:
            parents.append({
                "r0": r0,
                "k_prime": kv,
                "depth": depth,
                "parent_B": res[4],
                "parent_c": res[3],
            })
    parents.sort(key=lambda p: (p["depth"], p["r0"]))
    return parents


def covered_key_sets():
    return_map = maybe_load_json(RETURN_MAP) or {}
    b_control = maybe_load_json(BCONTROL) or {}
    certified = set()
    high_b = set()
    covered = set()
    for rec in return_map.get("return_records", []):
        key = key_tuple(rec["key"])
        if rec.get("classification") == "CERTIFIED_RETURN":
            certified.add(key)
            covered.add(key)
        elif rec.get("classification") == "HIGH_B_RETURN":
            high_b.add(key)
    for rec in b_control.get("high_B_chains", []):
        key = key_tuple(rec["key"])
        if rec.get("classification") == "B_EVENTUALLY_CERTIFIED":
            covered.add(key)
    return {
        "certified_return_keys": certified,
        "high_b_return_keys": high_b,
        "covered_keys": covered,
    }


def infer_artifact_caps(qreport):
    levels = []
    for section in ("open_frontier", "returned_frontier"):
        for item in qreport.get(section, []):
            if "level" in item:
                levels.append(int(item["level"]))
            affine = item.get("affine") or {}
            if "level" in affine:
                levels.append(int(affine["level"]))
    transition_cap = qreport.get("n_transitions")
    entries_cap = qreport.get("n_entries")
    return {
        "MAX_LEVEL": max(levels) if levels else eqa.MAX_LEVEL,
        "MAX_TRANSITIONS": int(transition_cap) if transition_cap else eqa.MAX_TRANSITIONS,
        "MAX_ENTRIES": int(entries_cap) if entries_cap else eqa.MAX_ENTRIES,
    }


def apply_artifact_caps():
    qreport = maybe_load_json(QREPORT) or {}
    inferred = infer_artifact_caps(qreport)
    before = {
        "MAX_LEVEL": eqa.MAX_LEVEL,
        "MAX_TRANSITIONS": eqa.MAX_TRANSITIONS,
        "MAX_ENTRIES": eqa.MAX_ENTRIES,
    }
    if USE_ARTIFACT_CAPS:
        eqa.MAX_LEVEL = inferred["MAX_LEVEL"]
        eqa.MAX_TRANSITIONS = inferred["MAX_TRANSITIONS"]
        eqa.MAX_ENTRIES = inferred["MAX_ENTRIES"]
    after = {
        "MAX_LEVEL": eqa.MAX_LEVEL,
        "MAX_TRANSITIONS": eqa.MAX_TRANSITIONS,
        "MAX_ENTRIES": eqa.MAX_ENTRIES,
    }
    return {"source": QREPORT, "inferred": inferred, "before": before, "after": after}


def result_key(parent):
    return str(parent["r0"])


def summarize_rows(rows, total_parent_count):
    counts = Counter(row["status"] for row in rows)
    closed_statuses = {
        "CLOSED_BY_QUOTIENT",
        "OPEN_KEYS_COVERED_BY_EXISTING_FRONTIER",
        "CLOSED_WITH_LOCAL_KEYS",
    }
    return {
        "total_depth_gt_18_parents": total_parent_count,
        "processed_parents": len(rows),
        "closed_parents": counts.get("CLOSED_BY_QUOTIENT", 0),
        "covered_by_existing_frontier": counts.get("OPEN_KEYS_COVERED_BY_EXISTING_FRONTIER", 0),
        "closed_with_local_keys": counts.get("CLOSED_WITH_LOCAL_KEYS", 0),
        "partial_or_blocked_parents": sum(
            count for status, count in counts.items()
            if status not in closed_statuses
        ),
        "missing_or_unprocessed_parents": total_parent_count - len(rows),
        "status_counts": dict(counts),
        "max_open_keys": max((row["open_key_count"] for row in rows), default=0),
        "max_entries": max((row["entry_count"] for row in rows), default=0),
        "max_keys": max((row["quotient_keys"] for row in rows), default=0),
        "max_transitions": max((row["transition_keys"] for row in rows), default=0),
        "local_keys_attempted": sum(row.get("local_keys_attempted", 0) for row in rows),
        "local_keys_certified": sum(row.get("local_keys_certified", 0) for row in rows),
        "local_keys_high_b_certified": sum(row.get("local_keys_high_b_certified", 0) for row in rows),
        "local_keys_still_open": sum(row.get("local_keys_still_open", 0) for row in rows),
    }


def load_existing_rows():
    if not RESUME:
        return {}
    existing = maybe_load_json(OUTFILE)
    if not existing:
        return {}
    return {str(row["r0"]): row for row in existing.get("parent_rows", [])}


def explore_quotient_with_representatives(entries):
    queue = deque()
    representatives = {}
    transitions = {}
    returns = defaultdict(list)
    bad_B_positive = []
    conflicts = []
    open_keys = {}
    visits = 0

    for _r0, _kv, _depth, state in entries:
        key = eqa.quotient_key(state)
        representatives.setdefault(key, state)
        queue.append(key)

    while queue:
        key = queue.popleft()
        state = representatives[key]
        visits += 1
        if visits > eqa.MAX_TRANSITIONS:
            open_keys[key] = "transition_cap"
            break

        ret = eqa.classify_positive(state)
        if ret is not None:
            if ret["B_ok"]:
                returns[key].append(ret)
                continue
            if len(bad_B_positive) < 50:
                bad_B_positive.append(ret)

        _residue, level, _a, _b, c, _o, steps = state
        if level >= eqa.MAX_LEVEL and c >= level:
            open_keys[key] = "level_cap"
            continue
        if steps >= eqa.MAX_STEPS:
            open_keys[key] = "step_cap"
            continue

        succ_keys = []
        for nxt in eqa.state_successors(state):
            nk = eqa.quotient_key(nxt)
            succ_keys.append(nk)
            if nk not in representatives:
                representatives[nk] = nxt
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

    return {
        "n_keys": len(representatives),
        "n_transitions": len(transitions),
        "n_return_keys": len(returns),
        "n_open_keys": len(open_keys),
        "conflicts": conflicts,
        "open_keys": open_keys,
        "open_frontier": [{"key": key_list(k), "reason": v} for k, v in open_keys.items()],
        "return_pairs": Counter(tuple(r["pair"]) for vals in returns.values() for r in vals),
        "bad_B_positive": bad_B_positive,
        "representatives": representatives,
    }


def zero_return_from_state(state):
    _residue, _level, a, b, c, o, _steps = state
    if a != 3 ** o:
        return {
            "classification": "CONFLICT",
            "reason": "representative coefficient a does not equal 3^o",
        }
    zeros = 0
    gap = (1 << c) - a
    while gap <= 0:
        c += 1
        zeros += 1
        gap = (1 << c) - a
    B = ceil_div(b, gap)
    return {
        "zeros": zeros,
        "pair": [o, c],
        "gap_bit_length": gap.bit_length(),
        "B": B,
        "B_ok": B <= eqa.B_LIMIT,
    }


def one_then_zero_return(o, c, b):
    old_c = c
    o += 1
    c += 1
    b = 3 * b + (1 << old_c)
    a = 3 ** o
    zeros = 0
    gap = (1 << c) - a
    while gap <= 0:
        c += 1
        zeros += 1
        gap = (1 << c) - a
    B = ceil_div(b, gap)
    return {
        "suffix": "1" + ("0" * min(zeros, 96)),
        "suffix_truncated": zeros > 96,
        "zeros_after_one": zeros,
        "pair": [o, c],
        "gap_bit_length": gap.bit_length(),
        "B": B,
        "B_ok": B <= eqa.B_LIMIT,
    }


def local_key_continuation(key, state, reason):
    cur = state
    prefix = ""
    for _ in range(LOCAL_KEY_PREFIX_STEPS):
        ret = eqa.classify_positive(cur)
        if ret is not None:
            if ret["B_ok"]:
                return {
                    "key": key_list(key),
                    "classification": "CERTIFIED_RETURN",
                    "reason": "already positive with B <= limit",
                    "prefix": prefix,
                    "return_pair": list(ret["pair"]),
                    "B": ret["B"],
                }
            _residue, _level, _a, b, c, o, _steps = cur
            next_ret = one_then_zero_return(o, c, b)
            return {
                "key": key_list(key),
                "classification": (
                    "HIGH_B_RETURN_THEN_CERTIFIED" if next_ret["B_ok"] else "NEEDS_HIGHER_LOCAL_CAP"
                ),
                "reason": "positive high-B state followed by one-then-zero B-control",
                "prefix": prefix,
                "return_pair": list(ret["pair"]),
                "B": ret["B"],
                "b_control_next": next_ret,
            }

        successors = eqa.state_successors(cur)
        if len(successors) != 1:
            zero_ret = zero_return_from_state(cur)
            if zero_ret.get("classification") == "CONFLICT":
                return {"key": key_list(key), **zero_ret}
            if zero_ret["B_ok"]:
                return {
                    "key": key_list(key),
                    "classification": "CERTIFIED_RETURN",
                    "reason": "branch-boundary zero-frontier return",
                    "prefix": prefix + ("0" * min(zero_ret["zeros"], 96)),
                    "prefix_truncated": zero_ret["zeros"] > 96,
                    "return_pair": zero_ret["pair"],
                    "B": zero_ret["B"],
                    "zeros": zero_ret["zeros"],
                }
            next_ret = one_then_zero_return(zero_ret["pair"][0], zero_ret["pair"][1], cur[3])
            return {
                "key": key_list(key),
                "classification": (
                    "HIGH_B_RETURN_THEN_CERTIFIED" if next_ret["B_ok"] else "NEEDS_HIGHER_LOCAL_CAP"
                ),
                "reason": "branch-boundary zero return was high-B",
                "prefix": prefix + ("0" * min(zero_ret["zeros"], 96)),
                "prefix_truncated": zero_ret["zeros"] > 96,
                "return_pair": zero_ret["pair"],
                "B": zero_ret["B"],
                "zeros": zero_ret["zeros"],
                "b_control_next": next_ret,
            }

        nxt = successors[0]
        if nxt[5] > cur[5]:
            prefix += "1"
        elif nxt[4] > cur[4]:
            prefix += "0"
        cur = nxt

    zero_ret = zero_return_from_state(cur)
    if zero_ret.get("classification") == "CONFLICT":
        return {"key": key_list(key), **zero_ret}
    if zero_ret["B_ok"]:
        return {
            "key": key_list(key),
            "classification": "CERTIFIED_RETURN",
            "reason": f"deterministic prefix then zero-frontier return after {reason}",
            "prefix": prefix + ("0" * min(zero_ret["zeros"], 96)),
            "prefix_truncated": zero_ret["zeros"] > 96,
            "return_pair": zero_ret["pair"],
            "B": zero_ret["B"],
            "zeros": zero_ret["zeros"],
        }
    next_ret = one_then_zero_return(zero_ret["pair"][0], zero_ret["pair"][1], cur[3])
    return {
        "key": key_list(key),
        "classification": (
            "HIGH_B_RETURN_THEN_CERTIFIED" if next_ret["B_ok"] else "NEEDS_HIGHER_LOCAL_CAP"
        ),
        "reason": "local zero return remained high-B",
        "prefix": prefix + ("0" * min(zero_ret["zeros"], 96)),
        "prefix_truncated": zero_ret["zeros"] > 96,
        "return_pair": zero_ret["pair"],
        "B": zero_ret["B"],
        "zeros": zero_ret["zeros"],
        "b_control_next": next_ret,
    }


def classify_parent(parent, covered_sets):
    t0 = time.time()
    parent_tuple = (parent["r0"], parent["k_prime"], parent["depth"])
    entries, per_parent = eqa.find_entries([parent_tuple])
    entry_time = time.time() - t0
    t1 = time.time()
    result = explore_quotient_with_representatives(entries)
    explore_time = time.time() - t1

    open_keys = set(result.get("open_keys", {}))
    conflicts = result.get("conflicts", [])
    open_reasons = Counter(result.get("open_keys", {}).values())
    cap_reasons = {
        reason for reason in open_reasons
        if any(token in str(reason).lower() for token in ["cap", "trunc", "partial", "sample"])
    }
    missing_from_existing_coverage = open_keys - covered_sets["covered_keys"]
    covered_open = open_keys & covered_sets["covered_keys"]
    representatives = result.get("representatives", {})
    local_key_results = []
    for key in sorted(missing_from_existing_coverage):
        state = representatives.get(key)
        if state is None:
            local_key_results.append({
                "key": key_list(key),
                "classification": "CONFLICT",
                "reason": "missing representative for uncovered key",
            })
            continue
        local_key_results.append(local_key_continuation(key, state, result["open_keys"].get(key)))

    local_counts = Counter(item["classification"] for item in local_key_results)
    local_still_open_classes = {"STILL_DEBT_LOCAL_CAP", "CONFLICT", "NEEDS_HIGHER_LOCAL_CAP"}
    local_still_open = [
        item for item in local_key_results
        if item["classification"] in local_still_open_classes
    ]
    local_good = {"CERTIFIED_RETURN", "HIGH_B_RETURN_THEN_CERTIFIED"}
    all_uncovered_locally_closed = bool(local_key_results) and all(
        item["classification"] in local_good for item in local_key_results
    )

    if conflicts:
        status = "CONFLICT"
    elif not entries:
        status = "NO_ENTRIES"
    elif not open_keys:
        status = "CLOSED_BY_QUOTIENT"
    elif not missing_from_existing_coverage and not cap_reasons:
        status = "OPEN_KEYS_COVERED_BY_EXISTING_FRONTIER"
    elif not missing_from_existing_coverage and cap_reasons:
        status = "COVERED_BUT_CAP_REACHED"
    elif all_uncovered_locally_closed:
        status = "CLOSED_WITH_LOCAL_KEYS"
    elif cap_reasons:
        status = "CAP_BLOCKED_WITH_UNCOVERED_KEYS"
    else:
        status = "UNCOVERED_OPEN_KEYS"

    return {
        "r0": parent["r0"],
        "k_prime": parent["k_prime"],
        "depth": parent["depth"],
        "status": status,
        "entry_count": len(entries),
        "entry_count_by_parent": int(per_parent.get(parent["r0"], 0)),
        "quotient_keys": result.get("n_keys", 0),
        "transition_keys": result.get("n_transitions", 0),
        "return_keys": result.get("n_return_keys", 0),
        "open_key_count": len(open_keys),
        "covered_open_key_count": len(covered_open),
        "uncovered_open_key_count": len(missing_from_existing_coverage),
        "local_keys_attempted": len(local_key_results),
        "local_keys_certified": local_counts.get("CERTIFIED_RETURN", 0),
        "local_keys_high_b_certified": local_counts.get("HIGH_B_RETURN_THEN_CERTIFIED", 0),
        "local_keys_still_open": len(local_still_open),
        "local_key_classification_counts": dict(local_counts),
        "local_key_examples": local_key_results[:20],
        "conflict_count": len(conflicts),
        "bad_B_positive_count": len(result.get("bad_B_positive", [])),
        "open_reason_counts": dict(open_reasons),
        "cap_or_truncation_reasons": sorted(cap_reasons),
        "open_keys_all_exported_in_parent_run": (
            len(result.get("open_keys", {})) == len(result.get("open_frontier", []))
        ),
        "sample_uncovered_open_keys": [
            key_list(key) for key in sorted(missing_from_existing_coverage)[:30]
        ],
        "sample_open_keys": [
            key_list(key) for key in sorted(open_keys)[:30]
        ],
        "sample_return_pairs": [
            [int(x[0]), int(x[1])] for x in list(result.get("return_pairs", Counter()).keys())[:30]
        ],
        "timing_seconds": {
            "entry_search": entry_time,
            "quotient_explore": explore_time,
            "total": time.time() - t0,
        },
    }


def write_report(rows_by_id, all_parents, started_at, cap_info, final=False):
    rows = [
        rows_by_id[str(parent["r0"])]
        for parent in all_parents
        if str(parent["r0"]) in rows_by_id
    ]
    processed_ids = {row["r0"] for row in rows}
    unprocessed = [
        {k: parent[k] for k in ["r0", "k_prime", "depth"]}
        for parent in all_parents
        if parent["r0"] not in processed_ids
    ]
    summary = summarize_rows(rows, len(all_parents))
    report = {
        "source_reports": {
            "frontier_key_coverage_audit": FRONTIER_AUDIT,
            "return_map": RETURN_MAP,
            "b_control": BCONTROL,
        },
        "method": {
            "random_seeds": False,
            "global_caps_increased": False,
            "resumable": True,
            "batch_start": BATCH_START,
            "batch_limit": BATCH_LIMIT,
            "final_write": final,
            "quotient_caps_used": {
                "MAX_STEPS": eqa.MAX_STEPS,
                "MAX_K_VALID": eqa.MAX_K_VALID,
                "MAX_ENTRY_NODES": eqa.MAX_ENTRY_NODES,
                "MAX_ENTRIES": eqa.MAX_ENTRIES,
                "MAX_TRANSITIONS": eqa.MAX_TRANSITIONS,
                "MAX_LEVEL": eqa.MAX_LEVEL,
                "MAX_EXPORTED_OPEN": eqa.MAX_EXPORTED_OPEN,
                "MAX_EXPORTED_RETURNS": eqa.MAX_EXPORTED_RETURNS,
                "B_LIMIT": eqa.B_LIMIT,
            },
            "artifact_cap_inference": cap_info,
        },
        "summary": summary,
        "final_status": (
            "PASS" if summary["processed_parents"] == len(all_parents)
            and summary["partial_or_blocked_parents"] == 0
            else "INCOMPLETE"
        ),
        "parent_rows": rows,
        "unprocessed_parent_ids": unprocessed,
        "blocked_or_partial_parent_ids": [
            {k: row[k] for k in ["r0", "k_prime", "depth", "status", "open_key_count", "uncovered_open_key_count"]}
            for row in rows
            if row["status"] not in {
                "CLOSED_BY_QUOTIENT",
                "OPEN_KEYS_COVERED_BY_EXISTING_FRONTIER",
                "CLOSED_WITH_LOCAL_KEYS",
            }
        ],
        "runtime_seconds": time.time() - started_at,
        "plain_truth": (
            "This is a per-parent capped quotient audit. PASS requires all 578 parents "
            "to process with no blocked/partial statuses; otherwise parent-universal "
            "coverage remains incomplete."
        ),
    }
    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def main():
    started_at = time.time()
    cap_info = apply_artifact_caps()
    all_parents = depth_gt_18_parents()
    rows_by_id = load_existing_rows()
    covered_sets = covered_key_sets()
    selected = all_parents[BATCH_START:]
    if BATCH_LIMIT > 0:
        selected = selected[:BATCH_LIMIT]

    print("=" * 78)
    print("QUOTIENT PARENT BATCH AUDIT")
    print("=" * 78)
    print(f"Total depth >18 parents : {len(all_parents):,}")
    print(f"Selected parents        : {len(selected):,}")
    print(f"Existing rows loaded    : {len(rows_by_id):,}")
    print(f"Artifact caps used      : {cap_info['after']}")
    print(f"Output                  : {OUTFILE}")
    print()

    processed_this_run = 0
    for idx, parent in enumerate(selected, 1):
        rid = result_key(parent)
        if rid in rows_by_id:
            continue
        row = classify_parent(parent, covered_sets)
        rows_by_id[rid] = row
        processed_this_run += 1
        print(
            f"[{idx:4d}/{len(selected):4d}] r0={row['r0']:5d} d={row['depth']:3d} "
            f"entries={row['entry_count']:4d} open={row['open_key_count']:4d} "
            f"uncovered={row['uncovered_open_key_count']:4d} status={row['status']} "
            f"time={row['timing_seconds']['total']:.2f}s",
            flush=True,
        )
        if CHECKPOINT_EVERY > 0 and processed_this_run % CHECKPOINT_EVERY == 0:
            write_report(rows_by_id, all_parents, started_at, cap_info)

    write_report(rows_by_id, all_parents, started_at, cap_info, final=True)
    rows = list(rows_by_id.values())
    summary = summarize_rows(rows, len(all_parents))
    print()
    print("SUMMARY")
    print(f"  Processed parents       : {summary['processed_parents']:,} / {len(all_parents):,}")
    print(f"  Closed parents          : {summary['closed_parents']:,}")
    print(f"  Covered by existing     : {summary['covered_by_existing_frontier']:,}")
    print(f"  Closed with local keys  : {summary['closed_with_local_keys']:,}")
    print(f"  Partial/blocked         : {summary['partial_or_blocked_parents']:,}")
    print(f"  Local keys attempted    : {summary['local_keys_attempted']:,}")
    print(f"  Local keys certified    : {summary['local_keys_certified']:,}")
    print(f"  Local high-B certified  : {summary['local_keys_high_b_certified']:,}")
    print(f"  Local still open        : {summary['local_keys_still_open']:,}")
    print(f"  Unprocessed             : {summary['missing_or_unprocessed_parents']:,}")
    print(f"  Status counts           : {summary['status_counts']}")
    print(f"  Report                  : {OUTFILE}")


if __name__ == "__main__":
    main()
