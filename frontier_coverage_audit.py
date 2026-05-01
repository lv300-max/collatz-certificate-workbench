"""
frontier_coverage_audit.py
==========================
Key-level coverage audit for the current quotient frontier reports.

Inputs:
    excursion_quotient_report.json
    frontier_return_map_report.json
    b_control_report.json

This script checks whether every open quotient key exported by the quotient
analyzer is present in the return-map report, and whether every HIGH_B_RETURN
key is present and certified in the B-control report.  It does not run random
seeds, raise caps, or claim a complete Collatz proof.
"""

import json
import os
import re
from collections import Counter

B_LIMIT = 200_001
QREPORT = os.environ.get("FRONTIER_AUDIT_QREPORT", "excursion_quotient_report.json")
RREPORT = os.environ.get("FRONTIER_AUDIT_RREPORT", "frontier_return_map_report.json")
BCONTROL = os.environ.get("FRONTIER_AUDIT_BREPORT", "b_control_report.json")
OUTFILE = os.environ.get("FRONTIER_AUDIT_OUT", "frontier_coverage_audit_report.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_key(text):
    nums = re.findall(r"-?\d+", text)
    return tuple(int(x) for x in nums)


def key_tuple(key):
    if isinstance(key, str):
        return parse_key(key)
    return tuple(int(x) for x in key)


def key_list(key):
    return [int(x) for x in key]


def sorted_key_lists(keys):
    return [key_list(k) for k in sorted(keys)]


def final_B(record):
    classification = record.get("classification")
    if classification == "CERTIFIED_RETURN":
        return record.get("B")
    if classification == "HIGH_B_RETURN":
        zero_tail = record.get("zero_tail_certification") or {}
        return zero_tail.get("B")
    if classification == "B_EVENTUALLY_CERTIFIED":
        chain = record.get("chain") or []
        if chain:
            return chain[-1].get("B")
        zero_tail = record.get("zero_tail_certification") or {}
        return zero_tail.get("B")
    return record.get("B")


def main():
    qreport = load_json(QREPORT)
    rreport = load_json(RREPORT)
    breport = load_json(BCONTROL)

    quotient_open_key_reasons = {
        key_tuple(k): reason for k, reason in qreport.get("open_keys", {}).items()
    }
    quotient_open_items = {
        key_tuple(item["key"]): item for item in qreport.get("open_frontier", [])
    }
    quotient_open_keys = set(quotient_open_key_reasons) | set(quotient_open_items)

    return_records = rreport.get("return_records", [])
    return_by_key = {key_tuple(rec["key"]): rec for rec in return_records}
    return_keys = set(return_by_key)
    return_class_counts = Counter(rec.get("classification") for rec in return_records)

    b_records = breport.get("high_B_chains", [])
    b_by_key = {key_tuple(rec["key"]): rec for rec in b_records}
    b_keys = set(b_by_key)
    b_class_counts = Counter(rec.get("classification") for rec in b_records)

    high_b_keys = {
        key for key, rec in return_by_key.items()
        if rec.get("classification") == "HIGH_B_RETURN"
    }
    certified_keys = {
        key for key, rec in return_by_key.items()
        if rec.get("classification") == "CERTIFIED_RETURN"
    }
    still_debt_keys = {
        key for key, rec in return_by_key.items()
        if rec.get("classification") == "STILL_DEBT_AT_CAP"
    }
    conflict_keys = {
        key for key, rec in return_by_key.items()
        if rec.get("classification") == "CONFLICT"
    }

    missing_from_export = set(quotient_open_key_reasons) - set(quotient_open_items)
    missing_from_return_map = quotient_open_keys - return_keys
    extra_return_map_keys = return_keys - quotient_open_keys
    missing_from_b_control = high_b_keys - b_keys
    extra_b_control_keys = b_keys - high_b_keys
    not_eventually_certified_high_b = {
        key for key in high_b_keys & b_keys
        if b_by_key[key].get("classification") != "B_EVENTUALLY_CERTIFIED"
    }

    final_B_by_key = {}
    final_B_over_limit = {}
    for key, rec in return_by_key.items():
        cls = rec.get("classification")
        if cls == "CERTIFIED_RETURN":
            value = rec.get("B")
        elif cls == "HIGH_B_RETURN" and key in b_by_key:
            value = final_B(b_by_key[key])
        else:
            value = rec.get("B")
        final_B_by_key[key] = value
        if value is None or value > B_LIMIT:
            final_B_over_limit[key] = value

    pass_condition = (
        not missing_from_export
        and not missing_from_return_map
        and not extra_return_map_keys
        and not missing_from_b_control
        and not extra_b_control_keys
        and not not_eventually_certified_high_b
        and not still_debt_keys
        and not conflict_keys
        and not final_B_over_limit
    )

    report = {
        "source_reports": {
            "quotient": QREPORT,
            "return_map": RREPORT,
            "b_control": BCONTROL,
        },
        "summary": {
            "quotient_open_keys": len(quotient_open_key_reasons),
            "quotient_open_frontier_exported": len(quotient_open_items),
            "unique_quotient_open_keys": len(quotient_open_keys),
            "return_map_records": len(return_records),
            "return_map_unique_keys": len(return_keys),
            "return_map_classification_counts": dict(return_class_counts),
            "certified_returns": len(certified_keys),
            "high_B_returns": len(high_b_keys),
            "still_debt_keys": len(still_debt_keys),
            "conflicts": len(conflict_keys),
            "b_control_records": len(b_records),
            "b_control_unique_keys": len(b_keys),
            "b_control_classification_counts": dict(b_class_counts),
            "high_B_eventually_certified": b_class_counts.get("B_EVENTUALLY_CERTIFIED", 0),
            "final_B_over_limit": len(final_B_over_limit),
            "max_final_B": max((v for v in final_B_by_key.values() if v is not None), default=None),
            "pass": pass_condition,
        },
        "checks": {
            "every_open_key_exported": not missing_from_export,
            "every_open_key_return_mapped": not missing_from_return_map and not extra_return_map_keys,
            "every_high_B_key_B_controlled": not missing_from_b_control and not extra_b_control_keys,
            "every_high_B_eventually_certified": not not_eventually_certified_high_b,
            "no_still_debt_keys": not still_debt_keys,
            "no_conflicts": not conflict_keys,
            "no_final_B_over_200001": not final_B_over_limit,
        },
        "missing_keys": {
            "open_keys_not_exported_to_open_frontier": sorted_key_lists(missing_from_export),
            "open_keys_missing_from_return_map": sorted_key_lists(missing_from_return_map),
            "return_map_keys_not_in_open_quotient": sorted_key_lists(extra_return_map_keys),
            "high_B_keys_missing_from_b_control": sorted_key_lists(missing_from_b_control),
            "b_control_keys_not_high_B_in_return_map": sorted_key_lists(extra_b_control_keys),
            "high_B_keys_not_eventually_certified": sorted_key_lists(not_eventually_certified_high_b),
            "still_debt_keys": sorted_key_lists(still_debt_keys),
            "conflict_keys": sorted_key_lists(conflict_keys),
            "final_B_over_limit": [
                {"key": key_list(key), "final_B": value}
                for key, value in sorted(final_B_over_limit.items())
            ],
        },
        "pass_condition": [
            "every open key exported",
            "every open key return-mapped",
            "every high-B key B-controlled",
            "no still-debt keys",
            "no conflicts",
            "no final B > 200001",
        ],
        "plain_truth": (
            "PASS: current exported quotient frontier is key-covered by return map and B-control."
            if pass_condition else
            "FAIL: current exported quotient frontier has coverage gaps listed in missing_keys."
        ),
        "what_this_does_not_prove": [
            "This audit is over the current quotient analyzer report only.",
            "It does not prove the quotient frontier method covers all depth >18 parents universally.",
            "It does not claim a complete Collatz proof.",
        ],
    }

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    s = report["summary"]
    print("=" * 78)
    print("FRONTIER COVERAGE AUDIT")
    print("=" * 78)
    print(f"Open keys in quotient report          : {s['quotient_open_keys']:,}")
    print(f"Open states exported                  : {s['quotient_open_frontier_exported']:,}")
    print(f"Return-map states analyzed            : {s['return_map_records']:,}")
    print(f"Certified returns                     : {s['certified_returns']:,}")
    print(f"High-B returns                        : {s['high_B_returns']:,}")
    print(f"Still debt                            : {s['still_debt_keys']:,}")
    print(f"Conflicts                             : {s['conflicts']:,}")
    print(f"High-B states B-controlled            : {s['b_control_records']:,}")
    print(f"High-B eventually certified           : {s['high_B_eventually_certified']:,}")
    print(f"Final B over {B_LIMIT:,}                  : {s['final_B_over_limit']:,}")
    print(f"Max final B                           : {s['max_final_B']:,}")
    print(f"PASS                                  : {s['pass']}")
    print("Missing keys:")
    for label, values in report["missing_keys"].items():
        print(f"  {label}: {len(values)}")
        for item in values[:20]:
            print(f"    {item}")
    print()
    print(report["plain_truth"])
    print("Next structural audit: whether this quotient frontier method covers all depth >18 parents universally.")
    print(f"Report                                : {OUTFILE}")


if __name__ == "__main__":
    main()
