#!/usr/bin/env python3
"""Audit the available group-membership routing evidence.

This checks the route data that exists in the repository. It deliberately does
not pretend the missing 84-group pre-aggregation membership map exists.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def load_json(name: str) -> Any:
    with (ROOT / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(name: str, data: Any) -> None:
    with (ROOT / name).open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def has_symbolic_group_link(row: dict[str, Any]) -> bool:
    keys = {
        "symbolic_group_id",
        "certificate_group_id",
        "group_class_id",
        "class_id",
        "packet_class_id",
    }
    if keys.intersection(row):
        return True
    for value in row.values():
        if isinstance(value, dict) and keys.intersection(value):
            return True
    return False


def main() -> None:
    generated_utc = datetime.now(timezone.utc).isoformat()

    residue = load_json("residue_partition_exhaustiveness_report.json")
    density = load_json("residue_density_partition_audit_report.json")
    exact = load_json("exact_state_closure_report.json")
    framework = load_json("full_framework_closure_audit_report.json")
    packet = load_json("reviewer_packet_84_symbolic_class_groups.json")

    assignments = residue["all_assignments"]
    lanes = density["lanes"]
    exact_results = exact["results"]

    assignment_by_r = {row["r0"]: row for row in assignments}
    lane_by_r = {row["residue"]: row for row in lanes}

    missing = [r for r in range(1, 2**16, 2) if r not in assignment_by_r]
    duplicate_count = residue.get("duplicates")
    bad_assignment_rows = [
        row for row in assignments
        if row.get("assignment_status") != "ASSIGNED_ONCE"
        or row.get("bucket_count") != 1
    ]

    routes = []
    symbolic_link_rows = 0
    for r in range(1, 2**16, 2):
        assignment = assignment_by_r.get(r)
        lane = lane_by_r.get(r)
        bucket = assignment["buckets"][0] if assignment and assignment.get("buckets") else {}
        has_group = has_symbolic_group_link(bucket) or has_symbolic_group_link(lane or {})
        symbolic_link_rows += int(has_group)
        routes.append(
            {
                "base_residue": r,
                "base_modulus": "2^16",
                "assignment_status": assignment.get("assignment_status") if assignment else "MISSING",
                "bucket": bucket.get("bucket"),
                "status": bucket.get("status"),
                "source": bucket.get("source"),
                "sampled": bucket.get("sampled"),
                "has_explicit_84_group_link": has_group,
                "lane_type": lane.get("lane_type") if lane else None,
                "lane_status": lane.get("status_or_classification") if lane else None,
            }
        )

    bucket_counts = Counter(route["bucket"] for route in routes)
    status_counts = Counter(route["status"] for route in routes)
    exact_terminal_counts = Counter(row.get("terminal_outcome") for row in exact_results)
    exact_classification_counts = Counter(row.get("classification") for row in exact_results)
    exact_source_counts = Counter(row.get("source_kind") for row in exact_results)

    base_partition_pass = (
        len(assignments) == 32768
        and len(missing) == 0
        and duplicate_count == 0
        and len(bad_assignment_rows) == 0
        and density.get("missing_slots") == 0
        and density.get("duplicate_overlap_slots") == 0
    )

    exact_state_pass = (
        framework.get("parents_closed") == framework.get("parents_checked") == 578
        and framework.get("exact_states_checked") == 1235
        and framework.get("compact_quotient_only_rows") == 0
        and exact.get("still_open") == 0
        and exact.get("conflicts") == 0
    )

    packet_pass = (
        packet.get("group_count") == 84
        and packet.get("failures") == []
        and sum(row["group_member_count"] for row in packet["records"])
        == packet.get("classes_audited")
    )

    full_84_membership_route_pass = symbolic_link_rows == len(routes)
    status = (
        "GROUP_MEMBERSHIP_ROUTING_AUDIT_BLOCKED_MISSING_84_LINKS"
        if base_partition_pass and exact_state_pass and packet_pass
        else "GROUP_MEMBERSHIP_ROUTING_AUDIT_FAILED_AVAILABLE_CHECKS"
    )

    report = {
        "title": "Group Membership Routing Audit",
        "generated_utc": generated_utc,
        "status": status,
        "collatz_proven_by_this_file": False,
        "base_partition": {
            "pass": base_partition_pass,
            "total_odd_residues": 32768,
            "assignment_rows": len(assignments),
            "assigned_once": residue.get("assigned_once"),
            "missing": len(missing),
            "duplicates": duplicate_count,
            "bad_assignment_rows": len(bad_assignment_rows),
            "density_missing_slots": density.get("missing_slots"),
            "density_duplicate_overlap_slots": density.get("duplicate_overlap_slots"),
            "sampled_as_proof_count": density.get("sampled_as_proof_count"),
            "bucket_counts": dict(bucket_counts),
            "status_counts": dict(status_counts),
        },
        "exact_state_closure": {
            "pass": exact_state_pass,
            "parents_closed": framework.get("parents_closed"),
            "parents_checked": framework.get("parents_checked"),
            "exact_states_checked": framework.get("exact_states_checked"),
            "compact_quotient_only_rows": framework.get("compact_quotient_only_rows"),
            "terminal_counts": dict(exact_terminal_counts),
            "classification_counts": dict(exact_classification_counts),
            "source_counts": dict(exact_source_counts),
        },
        "symbolic_84_packet": {
            "pass": packet_pass,
            "group_count": packet.get("group_count"),
            "classes_audited": packet.get("classes_audited"),
            "group_member_sum": sum(row["group_member_count"] for row in packet["records"]),
            "failures": len(packet.get("failures", [])),
            "status": packet.get("status"),
        },
        "end_to_end_group_membership": {
            "pass": full_84_membership_route_pass,
            "base_routes_checked": len(routes),
            "routes_with_explicit_84_group_link": symbolic_link_rows,
            "routes_missing_explicit_84_group_link": len(routes) - symbolic_link_rows,
            "reason_if_blocked": (
                "The available base-partition rows route to closure buckets "
                "and exact-state evidence, but they do not export a field that "
                "maps each route/member to one of the 84 symbolic class IDs."
            ),
        },
        "route_rows": routes,
        "needed_next_artifact": {
            "name": "group_membership_full.json or formal group-membership rule",
            "must_prove": [
                "total: every odd n gets assigned",
                "unique: no conflicting assignment",
                "terminating: route reaches exact closure or an 84 group",
                "sound: assigned 84 certificate applies to that n",
            ],
        },
    }

    write_json("group_membership_routing_audit_report.json", report)

    md = f"""# Group Membership Routing Audit

Generated: {generated_utc}

## Status

```text
{status}
```

This audit checks the route evidence that is currently present in the repo. It
does not claim a completed proof.

## Base Partition

```text
pass: {base_partition_pass}
total odd residues: 32768
assignment rows: {len(assignments)}
assigned once: {residue.get("assigned_once")}
missing: {len(missing)}
duplicates: {duplicate_count}
bad assignment rows: {len(bad_assignment_rows)}
sampled-as-proof rows: {density.get("sampled_as_proof_count")}
```

Bucket counts:

```text
{dict(bucket_counts)}
```

## Exact-State Closure

```text
pass: {exact_state_pass}
parents closed: {framework.get("parents_closed")} / {framework.get("parents_checked")}
exact states checked: {framework.get("exact_states_checked")}
compact quotient-only rows: {framework.get("compact_quotient_only_rows")}
```

Terminal outcomes:

```text
{dict(exact_terminal_counts)}
```

## 84 Symbolic Packet

```text
pass: {packet_pass}
groups: {packet.get("group_count")}
group member sum: {sum(row["group_member_count"] for row in packet["records"])}
failures: {len(packet.get("failures", []))}
status: {packet.get("status")}
```

## End-To-End 84-Group Membership

```text
pass: {full_84_membership_route_pass}
base routes checked: {len(routes)}
routes with explicit 84-group link: {symbolic_link_rows}
routes missing explicit 84-group link: {len(routes) - symbolic_link_rows}
```

The current files prove the base partition counts and exact-state closure
counts, but they do not export a field that maps each route/member to one of the
84 symbolic class IDs.

## Honest Conclusion

```text
certificate algebra: verified
base partition: complete
exact-state closure: verified
84 canonical group packet: verified
end-to-end 84 group membership map: not exported
remaining wall: group_membership_full.json or formal membership rule
```
"""
    (ROOT / "group_membership_routing_audit_report.md").write_text(md, encoding="utf-8")

    print(status)
    print("base partition pass:", base_partition_pass)
    print("total base routes:", len(routes))
    print("missing:", len(missing))
    print("duplicates:", duplicate_count)
    print("exact state pass:", exact_state_pass)
    print("84 packet pass:", packet_pass)
    print("routes with explicit 84-group link:", symbolic_link_rows)
    print("routes missing explicit 84-group link:", len(routes) - symbolic_link_rows)
    print("wrote group_membership_routing_audit_report.json")
    print("wrote group_membership_routing_audit_report.md")


if __name__ == "__main__":
    main()
