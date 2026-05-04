#!/usr/bin/env python3
"""Export the membership data that is actually present in this repo.

This intentionally does not synthesize the missing 7,364,628 pre-aggregation
members behind the 84 symbolic certificate groups. The reviewer packet stores
only grouped counts plus each group's canonical certificate.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_json(name: str):
    with (ROOT / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(name: str, data) -> None:
    with (ROOT / name).open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def main() -> None:
    generated_utc = datetime.now(timezone.utc).isoformat()

    residue_density = load_json("residue_density_partition_audit_report.json")
    residue_exhaustive = load_json("residue_partition_exhaustiveness_report.json")
    packet = load_json("reviewer_packet_84_symbolic_class_groups.json")

    exhaustive_by_residue = {
        row["r0"]: row for row in residue_exhaustive["all_assignments"]
    }

    base_members = []
    for lane in residue_density["lanes"]:
        r = lane["residue"]
        assignment = exhaustive_by_residue.get(r, {})
        base_members.append(
            {
                "residue": r,
                "modulus": lane["proof_modulus"],
                "modulus_power": lane["proof_modulus_power"],
                "lane_type": lane["lane_type"],
                "source": lane["source"],
                "status_or_classification": lane.get("status_or_classification"),
                "sampled_as_proof": lane["sampled_as_proof"],
                "sampled_or_exact": lane["sampled_or_exact"],
                "assignment_status": assignment.get("assignment_status"),
                "assignment_buckets": assignment.get("buckets", []),
                "assignment_bucket_count": assignment.get("bucket_count"),
            }
        )

    base_export = {
        "title": "Base Partition Full Member List",
        "generated_utc": generated_utc,
        "scope": "Odd residues modulo 2^16 from the audited base partition.",
        "status": "BASE_PARTITION_FULL_MEMBER_LIST_EXPORTED",
        "modulus": "2^16",
        "odd_residue_count": len(base_members),
        "expected_odd_residue_count": residue_density["total_odd_residue_slots"],
        "missing": residue_density["missing_slots"],
        "duplicates": residue_density["duplicate_overlap_slots"],
        "sampled_as_proof_count": residue_density["sampled_as_proof_count"],
        "members": base_members,
    }

    group_summaries = []
    for row in packet["records"]:
        cert = row["canonical_certificate"]
        group_summaries.append(
            {
                "class_id": row["class_id"],
                "label": row["label"],
                "group_member_count": row["group_member_count"],
                "full_member_rows_available": False,
                "canonical_certificate": {
                    "r": cert["r"],
                    "A": cert["A"],
                    "m": cert["m"],
                    "b": cert["b"],
                    "gap": cert["gap"],
                    "B": cert["B"],
                    "min_n": cert["min_n"],
                    "valuation_hash": cert.get("valuation_hash")
                    or cert.get("valuation_word_hash"),
                    "status": cert["status"],
                },
                "group_bounds": row.get("group_bounds", {}),
                "note": row.get("note"),
            }
        )

    group_summary_export = {
        "title": "84 Symbolic Group Member Count Summary",
        "generated_utc": generated_utc,
        "scope": "Grouped 84-row symbolic packet. Full pre-aggregation member rows are not stored in this repo.",
        "status": "GROUP_MEMBER_COUNTS_ONLY_FULL_MEMBER_ROWS_MISSING",
        "group_count": packet["group_count"],
        "classes_audited": packet["classes_audited"],
        "group_member_sum": sum(row["group_member_count"] for row in packet["records"]),
        "full_member_rows_available": False,
        "groups": group_summaries,
    }

    blocker = {
        "title": "Group Member List Export Status",
        "generated_utc": generated_utc,
        "base_partition_member_list": {
            "file": "base_partition_full_member_list.json",
            "status": "exported",
            "members": len(base_members),
            "missing": residue_density["missing_slots"],
            "duplicates": residue_density["duplicate_overlap_slots"],
        },
        "symbolic_84_group_member_list": {
            "status": "blocked",
            "reason": "The current 84-row packet stores group_member_count and a canonical certificate per group, but not the individual pre-aggregation member lanes.",
            "groups": packet["group_count"],
            "expected_member_rows": packet["classes_audited"],
            "available_member_rows": 0,
            "available_summary_file": "certificate_group_member_counts.json",
        },
        "reviewer_impact": "The base partition is exportable and complete. The 84-group full membership theorem still needs either a full member export or a formal rule proving exactly which lanes belong to each group.",
        "needed_next_artifact": {
            "file": "group_membership_full.json",
            "required_rows": packet["classes_audited"],
            "minimum_schema": [
                "member_id",
                "group_class_id",
                "group_label",
                "residue_r",
                "forcing_A",
                "forcing_modulus_2_to_A_plus_1",
                "m",
                "b",
                "gap",
                "B",
                "min_n",
                "valuation_hash",
                "source_branch",
                "status",
            ],
        },
    }

    write_json("base_partition_full_member_list.json", base_export)
    write_json("certificate_group_member_counts.json", group_summary_export)
    write_json("GROUP_MEMBER_LIST_EXPORT_STATUS.json", blocker)

    md = f"""# Group Member List Export Status

Generated: {generated_utc}

## Exported

- `base_partition_full_member_list.json`
- Odd residues modulo `2^16`: `{len(base_members)} / {residue_density["total_odd_residue_slots"]}`
- Missing: `{residue_density["missing_slots"]}`
- Duplicates: `{residue_density["duplicate_overlap_slots"]}`
- Sampled-as-proof rows: `{residue_density["sampled_as_proof_count"]}`

## Not Exportable From Current Files

The full pre-aggregation member list behind the 84 symbolic certificate groups is not present in this repo.

The packet files contain:

- 84 grouped records
- `group_member_count` per record
- canonical certificate per group
- total grouped members: `{packet["classes_audited"]}`

They do not contain the individual `{packet["classes_audited"]}` member rows.

## Reviewer Impact

The base partition member list is complete and exportable.

The 84-group membership theorem still needs one of these:

1. `group_membership_full.json` with all `{packet["classes_audited"]}` member rows, or
2. a formal membership rule proving exactly which lanes belong to each of the 84 groups.

Without that artifact, the honest status remains:

```text
certificate algebra verified
base partition exported
84 group counts verified
full 84-group member list missing
grouping theorem still requires independent review
```
"""
    (ROOT / "GROUP_MEMBER_LIST_EXPORT_STATUS.md").write_text(md, encoding="utf-8")

    print("BASE_PARTITION_FULL_MEMBER_LIST_EXPORTED")
    print(f"members: {len(base_members)}")
    print("missing:", residue_density["missing_slots"])
    print("duplicates:", residue_density["duplicate_overlap_slots"])
    print()
    print("84_GROUP_FULL_MEMBER_LIST_STATUS")
    print("status: BLOCKED_FULL_MEMBER_ROWS_NOT_PRESENT")
    print("groups:", packet["group_count"])
    print("expected member rows:", packet["classes_audited"])
    print("available member rows: 0")
    print()
    print("wrote base_partition_full_member_list.json")
    print("wrote certificate_group_member_counts.json")
    print("wrote GROUP_MEMBER_LIST_EXPORT_STATUS.json")
    print("wrote GROUP_MEMBER_LIST_EXPORT_STATUS.md")


if __name__ == "__main__":
    main()
