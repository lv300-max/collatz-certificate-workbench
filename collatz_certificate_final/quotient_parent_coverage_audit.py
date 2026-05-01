"""
quotient_parent_coverage_audit.py
=================================
Structural audit for parent-level coverage of the quotient frontier method.

Inputs:
    excursion_quotient_report.json
    frontier_coverage_audit_report.json

The audit recomputes the depth >18 parent list deterministically with the same
local descent routines used by the workbench.  It does not run random seeds,
raise quotient caps, or claim proof completion.
"""

import json
import os
from collections import Counter

KMAX = 16
MAX_STEPS = 10_000
MAX_K_VALID = 500

QREPORT = os.environ.get("QPARENT_QREPORT", "excursion_quotient_report.json")
FRONTIER_AUDIT = os.environ.get(
    "QPARENT_FRONTIER_AUDIT", "frontier_coverage_audit_report.json"
)
OUTFILE = os.environ.get(
    "QPARENT_OUT", "quotient_parent_coverage_audit_report.json"
)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def maybe_load_json(path):
    try:
        return load_json(path)
    except FileNotFoundError:
        return None


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


def depth_gt_18_parents():
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
            parents.append({
                "r0": r0,
                "k_prime": kv,
                "depth": depth,
                "a": str(res[1]),
                "b": str(res[2]),
                "c": res[3],
                "B": res[4],
            })
    parents.sort(key=lambda p: (p["depth"], p["r0"]))
    return parents


def parent_id(parent):
    return int(parent["r0"])


def parent_key_tuple(parent):
    return int(parent[0]), int(parent[1]), int(parent[2])


def compact_parent(parent):
    return {
        "r0": int(parent["r0"]),
        "k_prime": int(parent["k_prime"]),
        "depth": int(parent["depth"]),
    }


def artifact_status():
    candidates = [
        "deep_sibling_closure_law_report.json",
        "deep_parent_margin_certificate_report.json",
        "deep_margin_all_parents_report.json",
        "below_line_excursion_report.json",
        "below_line_excursion_report_10.json",
        "frontier_word_invariant_report.json",
        "frontier_affine_invariant_report.json",
        "frontier_coverage_audit_report.json",
    ]
    out = []
    for path in candidates:
        out.append({"path": path, "exists": os.path.exists(path)})
    return out


def main():
    qreport = load_json(QREPORT)
    frontier_audit = maybe_load_json(FRONTIER_AUDIT)
    all_parents = depth_gt_18_parents()
    all_parent_ids = {parent_id(p) for p in all_parents}
    all_by_id = {parent_id(p): p for p in all_parents}

    q_parents_raw = qreport.get("parents", [])
    q_parent_tuples = {parent_key_tuple(p) for p in q_parents_raw}
    q_parent_ids = {p[0] for p in q_parent_tuples}
    represented_ids = all_parent_ids & q_parent_ids
    missing_ids = all_parent_ids - q_parent_ids
    extra_q_ids = q_parent_ids - all_parent_ids

    entry_count_by_parent = {
        int(k): int(v) for k, v in qreport.get("entry_count_by_parent", {}).items()
    }
    parents_with_entries = set(entry_count_by_parent)
    represented_without_entries = represented_ids - parents_with_entries

    open_reasons = Counter(qreport.get("open_keys", {}).values())
    capped_reason_names = {
        reason for reason in open_reasons
        if any(token in str(reason).lower() for token in ["cap", "trunc", "sample", "partial"])
    }
    has_capped_states = bool(capped_reason_names)

    # The current quotient artifact does not retain a complete parent-origin set
    # for each open key.  origins_sample is explicitly sampled diagnostic data.
    origins_sample = qreport.get("origins_sample", {})
    per_parent_open_key_coverage_auditable = False
    exported_all_open_keys_globally = (
        len(qreport.get("open_keys", {})) == len(qreport.get("open_frontier", []))
    )

    parent_rows = []
    for parent in all_parents:
        r0 = parent_id(parent)
        represented = r0 in represented_ids
        has_entries = r0 in parents_with_entries
        row = {
            **compact_parent(parent),
            "represented_in_quotient_parent_list": represented,
            "entry_count": entry_count_by_parent.get(r0, 0),
            "has_collected_entries": has_entries,
            "all_open_quotient_keys_exported_for_parent": (
                "UNKNOWN: report does not retain complete open-key origins by parent"
                if represented else False
            ),
            "sibling_space_coverage": (
                "PARTIAL_OR_EMPIRICAL: quotient report is capped/sampled and gives no full sibling-space certificate"
                if represented else "MISSING"
            ),
            "coverage_status": (
                "PARTIAL" if represented else "MISSING"
            ),
            "capped_or_truncated": bool(represented and has_capped_states),
        }
        parent_rows.append(row)

    fully_covered_ids = {
        row["r0"] for row in parent_rows if row["coverage_status"] == "FULL"
    }
    partial_ids = {
        row["r0"] for row in parent_rows if row["coverage_status"] == "PARTIAL"
    }
    capped_ids = {
        row["r0"] for row in parent_rows if row["capped_or_truncated"]
    }

    frontier_key_audit_pass = (
        bool(frontier_audit)
        and frontier_audit.get("summary", {}).get("pass") is True
    )
    abstraction_status = (
        "sampled_or_capped_exploration"
        if (
            missing_ids
            or partial_ids
            or represented_without_entries
            or has_capped_states
            or origins_sample
            or not per_parent_open_key_coverage_auditable
        )
        else "exact_quotient_equivalence_coverage"
    )

    final_status = "PASS" if (
        len(all_parents) == 578
        and len(fully_covered_ids) == len(all_parents)
        and not missing_ids
        and not partial_ids
        and not capped_ids
        and abstraction_status == "exact_quotient_equivalence_coverage"
    ) else "INCOMPLETE"

    depth_counts = Counter(p["depth"] for p in all_parents)
    report = {
        "source_reports": {
            "quotient": QREPORT,
            "frontier_key_coverage_audit": FRONTIER_AUDIT if frontier_audit else None,
        },
        "available_parent_or_exact_depth_artifacts": artifact_status(),
        "method": {
            "random_seeds": False,
            "global_caps_increased": False,
            "parent_enumeration": (
                "Deterministic recomputation of depth >18 k=16 parents using "
                f"MAX_STEPS={MAX_STEPS} and MAX_K_VALID={MAX_K_VALID}."
            ),
            "structural_distinction": (
                "Exact key coverage of exported frontier states is separate from "
                "universal parent/sibling-space coverage."
            ),
        },
        "summary": {
            "total_depth_gt_18_parents": len(all_parents),
            "represented_parents": len(represented_ids),
            "parents_with_collected_entries": len(parents_with_entries & all_parent_ids),
            "fully_covered_parents": len(fully_covered_ids),
            "partially_covered_parents": len(partial_ids),
            "missing_parents": len(missing_ids),
            "capped_or_truncated_parents": len(capped_ids),
            "extra_quotient_parent_ids_not_in_depth_gt_18_set": len(extra_q_ids),
            "quotient_parent_list_count": len(q_parents_raw),
            "quotient_entries": qreport.get("n_entries"),
            "quotient_open_keys": qreport.get("n_open_keys"),
            "quotient_open_frontier_exported": len(qreport.get("open_frontier", [])),
            "exported_all_open_keys_globally": exported_all_open_keys_globally,
            "per_parent_open_key_coverage_auditable": per_parent_open_key_coverage_auditable,
            "frontier_key_audit_pass": frontier_key_audit_pass,
            "quotient_abstraction_status": abstraction_status,
            "final_status": final_status,
        },
        "depth_distribution": {
            str(depth): depth_counts[depth] for depth in sorted(depth_counts)
        },
        "quotient_state_markers": {
            "open_reason_counts": dict(open_reasons),
            "capped_or_truncated_reasons": sorted(capped_reason_names),
            "has_origins_sample": bool(origins_sample),
            "origins_sample_count": len(origins_sample),
            "represented_without_entries": [
                compact_parent(all_by_id[r0]) for r0 in sorted(represented_without_entries)
            ],
        },
        "represented_parent_ids": [
            compact_parent(all_by_id[r0]) for r0 in sorted(represented_ids)
        ],
        "parents_with_entries": [
            {
                **compact_parent(all_by_id[r0]),
                "entry_count": entry_count_by_parent.get(r0, 0),
            }
            for r0 in sorted(parents_with_entries & all_parent_ids)
        ],
        "missing_parent_ids": [
            compact_parent(all_by_id[r0]) for r0 in sorted(missing_ids)
        ],
        "partial_parent_ids": [
            compact_parent(all_by_id[r0]) for r0 in sorted(partial_ids)
        ],
        "capped_or_truncated_parent_ids": [
            compact_parent(all_by_id[r0]) for r0 in sorted(capped_ids)
        ],
        "parent_rows": parent_rows,
        "answers": {
            "1_how_many_depth_gt_18_parents_exist": len(all_parents),
            "2_how_many_are_represented_in_quotient_frontier": len(represented_ids),
            "3_are_all_open_quotient_keys_exported_per_parent": (
                "Not provable from this artifact. All open keys are exported globally, "
                "but open keys do not carry complete parent-origin coverage."
            ),
            "4_do_exported_keys_cover_full_sibling_space": (
                "No full sibling-space coverage certificate is present. The report "
                "contains capped/sampled exploration entries."
            ),
            "5_parent_residues_with_no_quotient_frontier_representation": len(missing_ids),
            "6_quotient_states_marked_sampled_truncated_capped_partial": bool(
                has_capped_states or origins_sample
            ),
            "7_abstraction_proves_equivalence_or_samples_paths": abstraction_status,
            "10_final_status": final_status,
        },
        "plain_truth": (
            "INCOMPLETE: the current quotient artifact covers exported frontier keys, "
            "but it does not universally cover all 578 depth >18 parents."
            if final_status == "INCOMPLETE" else
            "PASS: all depth >18 parents are covered by exact quotient equivalence classes."
        ),
        "what_this_does_not_claim": [
            "No complete Collatz proof is claimed.",
            "No universal quotient-parent theorem is inferred from sampled/capped data.",
        ],
    }

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    s = report["summary"]
    print("=" * 78)
    print("QUOTIENT PARENT COVERAGE AUDIT")
    print("=" * 78)
    print(f"Total depth >18 parents          : {s['total_depth_gt_18_parents']:,}")
    print(f"Represented parents              : {s['represented_parents']:,}")
    print(f"Fully covered parents            : {s['fully_covered_parents']:,}")
    print(f"Partially covered parents        : {s['partially_covered_parents']:,}")
    print(f"Missing parents                  : {s['missing_parents']:,}")
    print(f"Capped/truncated parents         : {s['capped_or_truncated_parents']:,}")
    print(f"Quotient parent list count       : {s['quotient_parent_list_count']:,}")
    print(f"Quotient entries                 : {s['quotient_entries']:,}")
    print(f"Quotient open keys               : {s['quotient_open_keys']:,}")
    print(f"Frontier key audit pass          : {s['frontier_key_audit_pass']}")
    print(f"Abstraction status               : {s['quotient_abstraction_status']}")
    print(f"FINAL STATUS                     : {s['final_status']}")
    print()
    print("Missing parent IDs:")
    print(json.dumps(report["missing_parent_ids"], separators=(",", ":")))
    print("Partial parent IDs:")
    print(json.dumps(report["partial_parent_ids"], separators=(",", ":")))
    print("Capped/truncated parent IDs:")
    print(json.dumps(report["capped_or_truncated_parent_ids"], separators=(",", ":")))
    print()
    print(report["plain_truth"])
    print(f"Report                           : {OUTFILE}")


if __name__ == "__main__":
    main()
