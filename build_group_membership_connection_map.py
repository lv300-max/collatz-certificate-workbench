#!/usr/bin/env python3
"""Build the strongest defensible connection map from the exported artifacts.

The map connects each odd base residue mod 2^16 to the closure evidence that is
actually present. It does not invent 84-group IDs where the source artifacts do
not export a foreign key into the 84 symbolic packet.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
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


def terminal_kind(bucket: dict[str, Any]) -> str:
    b = bucket.get("bucket")
    status = bucket.get("status")
    if b == "shallow_valid_at_k16":
        return "DIRECT_BASE_DESCENT"
    if b == "pre_report_exact_depth_parent":
        return "PRE_REPORT_EXACT_DEPTH_CERTIFICATE"
    if b == "exact_depth_closed_parent":
        return "EXACT_DEPTH_CLOSED_PARENT"
    if b == "deep_parent":
        if status == "CLOSED_BY_QUOTIENT":
            return "DEEP_PARENT_FULL_EXACT_STATE_CERTIFICATE"
        if status == "CLOSED_WITH_LOCAL_KEYS":
            return "DEEP_PARENT_LOCAL_KEY_CERTIFICATE"
        if status == "COVERED_BUT_CAP_REACHED":
            return "DEEP_PARENT_EXPORTED_OPEN_KEYS_COVERED"
    return "UNKNOWN"


def main() -> None:
    generated_utc = datetime.now(timezone.utc).isoformat()

    residue = load_json("residue_partition_exhaustiveness_report.json")
    density = load_json("residue_density_partition_audit_report.json")
    exact = load_json("exact_state_closure_report.json")
    qparent = load_json("quotient_parent_batch_report.json")
    packet = load_json("reviewer_packet_84_symbolic_class_groups.json")

    exact_by_parent: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in exact["results"]:
        parent = row.get("parent_r0")
        if parent is not None:
            exact_by_parent[int(parent)].append(row)

    qparent_by_r0 = {int(row["r0"]): row for row in qparent["parent_rows"]}
    lane_by_r = {int(row["residue"]): row for row in density["lanes"]}

    connection_rows = []
    symbolic_84_link_count = 0

    for assignment in residue["all_assignments"]:
        r0 = int(assignment["r0"])
        bucket = assignment["buckets"][0] if assignment.get("buckets") else {}
        lane = lane_by_r.get(r0, {})
        qrow = qparent_by_r0.get(r0) if bucket.get("bucket") == "deep_parent" else None
        exact_rows = exact_by_parent.get(r0, [])
        exact_terminal_counts = Counter(row.get("terminal_outcome") for row in exact_rows)

        # No current artifact exports a class_id/group_id foreign key into the
        # 84 symbolic packet. Keep these explicit instead of guessing.
        symbolic_group_id = None
        symbolic_group_label = None
        symbolic_link_status = "NO_EXPORTED_84_GROUP_LINK"

        connection_rows.append(
            {
                "base_residue": r0,
                "base_modulus": "2^16",
                "assignment_status": assignment.get("assignment_status"),
                "bucket": bucket.get("bucket"),
                "bucket_status": bucket.get("status"),
                "terminal_kind": terminal_kind(bucket),
                "sampled": bucket.get("sampled"),
                "source": bucket.get("source"),
                "lane_type": lane.get("lane_type"),
                "lane_status": lane.get("status_or_classification"),
                "proof_fields": {
                    "B": bucket.get("B"),
                    "c": bucket.get("c"),
                    "m": bucket.get("m"),
                    "o": bucket.get("o"),
                    "k_prime": bucket.get("k_prime"),
                    "depth": bucket.get("depth"),
                },
                "deep_parent_evidence": None if qrow is None else {
                    "status": qrow.get("status"),
                    "coverage_source": qrow.get("coverage_source"),
                    "exact": qrow.get("exact"),
                    "open_keys_all_exported_in_parent_run": qrow.get(
                        "open_keys_all_exported_in_parent_run"
                    ),
                    "open_key_count": qrow.get("open_key_count"),
                    "covered_open_key_count": qrow.get("covered_open_key_count"),
                    "uncovered_open_key_count": qrow.get("uncovered_open_key_count"),
                    "local_keys_certified": qrow.get("local_keys_certified"),
                    "local_keys_high_b_certified": qrow.get("local_keys_high_b_certified"),
                    "local_keys_still_open": qrow.get("local_keys_still_open"),
                    "exact_closure_witness_count": qrow.get("exact_closure_witness_count"),
                },
                "exact_state_terminal_counts": dict(exact_terminal_counts),
                "exact_state_row_count": len(exact_rows),
                "symbolic_84_group_id": symbolic_group_id,
                "symbolic_84_group_label": symbolic_group_label,
                "symbolic_84_link_status": symbolic_link_status,
            }
        )

    terminal_counts = Counter(row["terminal_kind"] for row in connection_rows)
    bucket_counts = Counter(row["bucket"] for row in connection_rows)
    status_counts = Counter(row["bucket_status"] for row in connection_rows)
    sampled_rows = [row for row in connection_rows if row["sampled"]]
    unknown_rows = [row for row in connection_rows if row["terminal_kind"] == "UNKNOWN"]
    residual_local_key_deep = [
        row for row in connection_rows
        if row["deep_parent_evidence"]
        and row["deep_parent_evidence"].get("uncovered_open_key_count") not in (None, 0)
        and row["terminal_kind"] == "DEEP_PARENT_LOCAL_KEY_CERTIFICATE"
    ]
    unresolved_deep = [
        row for row in connection_rows
        if row["deep_parent_evidence"]
        and row["deep_parent_evidence"].get("uncovered_open_key_count") not in (None, 0)
        and row["terminal_kind"] != "DEEP_PARENT_LOCAL_KEY_CERTIFICATE"
    ]

    report = {
        "title": "Group Membership Connection Map",
        "generated_utc": generated_utc,
        "status": "BASE_TO_CLOSURE_CONNECTED__84_GROUP_LINK_NOT_EXPORTED",
        "collatz_proven_by_this_file": False,
        "summary": {
            "base_residues": len(connection_rows),
            "base_missing": residue.get("missing"),
            "base_duplicates": residue.get("duplicates"),
            "sampled_rows": len(sampled_rows),
            "unknown_terminal_rows": len(unknown_rows),
            "deep_rows_with_residual_keys_closed_by_local_certificate": len(
                residual_local_key_deep
            ),
            "deep_rows_with_unresolved_open_keys": len(unresolved_deep),
            "symbolic_84_groups": packet.get("group_count"),
            "symbolic_84_group_member_sum": sum(
                row["group_member_count"] for row in packet["records"]
            ),
            "base_rows_with_exported_84_group_id": symbolic_84_link_count,
            "base_rows_missing_exported_84_group_id": len(connection_rows)
            - symbolic_84_link_count,
        },
        "terminal_counts": dict(terminal_counts),
        "bucket_counts": dict(bucket_counts),
        "bucket_status_counts": dict(status_counts),
        "connection_rows": connection_rows,
        "reviewer_boundary": (
            "This connects every odd base residue mod 2^16 to exported closure "
            "evidence. It does not connect those routes to the 84 symbolic group "
            "IDs because no current artifact exports that foreign key or a formal "
            "membership rule."
        ),
    }

    write_json("group_membership_connection_map.json", report)

    md = f"""# Group Membership Connection Map

Generated: {generated_utc}

## Status

```text
BASE_TO_CLOSURE_CONNECTED__84_GROUP_LINK_NOT_EXPORTED
```

## What Is Connected

Every odd base residue modulo `2^16` is connected to the closure evidence
exported by the current repo.

```text
base residues: {len(connection_rows)}
base missing: {residue.get("missing")}
base duplicates: {residue.get("duplicates")}
sampled rows: {len(sampled_rows)}
unknown terminal rows: {len(unknown_rows)}
deep rows with residual keys closed by local certificate: {len(residual_local_key_deep)}
deep rows with unresolved open keys: {len(unresolved_deep)}
```

Terminal counts:

```text
{dict(terminal_counts)}
```

Bucket status counts:

```text
{dict(status_counts)}
```

## What Is Still Not Connected

The 84 symbolic packet is verified separately:

```text
84 groups: {packet.get("group_count")}
84 group member sum: {sum(row["group_member_count"] for row in packet["records"])}
```

But the current base/exact route artifacts do not export a field like
`symbolic_group_id`, `class_id`, or `packet_class_id` that maps each route/member
into one of those 84 groups.

```text
base rows with exported 84 group id: {symbolic_84_link_count}
base rows missing exported 84 group id: {len(connection_rows) - symbolic_84_link_count}
```

## Honest Reviewer Boundary

This file connects:

```text
base residue -> closure evidence
```

It does not yet connect:

```text
base residue/member -> 84 symbolic group id
```

The missing artifact remains:

```text
group_membership_full.json
```

or a formal group-membership rule.
"""
    (ROOT / "group_membership_connection_map.md").write_text(md, encoding="utf-8")

    print("BASE_TO_CLOSURE_CONNECTED__84_GROUP_LINK_NOT_EXPORTED")
    print("base residues:", len(connection_rows))
    print("base missing:", residue.get("missing"))
    print("base duplicates:", residue.get("duplicates"))
    print("sampled rows:", len(sampled_rows))
    print("unknown terminal rows:", len(unknown_rows))
    print(
        "deep rows with residual keys closed by local certificate:",
        len(residual_local_key_deep),
    )
    print("deep rows with unresolved open keys:", len(unresolved_deep))
    print("terminal counts:", dict(terminal_counts))
    print("base rows with exported 84 group id:", symbolic_84_link_count)
    print("base rows missing exported 84 group id:", len(connection_rows) - symbolic_84_link_count)
    print("wrote group_membership_connection_map.json")
    print("wrote group_membership_connection_map.md")


if __name__ == "__main__":
    main()
