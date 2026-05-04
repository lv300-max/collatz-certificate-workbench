# Group Membership Connection Map

Generated: 2026-05-04T16:48:47.045560+00:00

## Status

```text
BASE_TO_CLOSURE_CONNECTED__84_GROUP_LINK_NOT_EXPORTED
```

## What Is Connected

Every odd base residue modulo `2^16` is connected to the closure evidence
exported by the current repo.

```text
base residues: 32768
base missing: 0
base duplicates: 0
sampled rows: 0
unknown terminal rows: 0
deep rows with residual keys closed by local certificate: 64
deep rows with unresolved open keys: 0
```

Terminal counts:

```text
{'DIRECT_BASE_DESCENT': 30654, 'DEEP_PARENT_FULL_EXACT_STATE_CERTIFICATE': 228, 'DEEP_PARENT_EXPORTED_OPEN_KEYS_COVERED': 286, 'DEEP_PARENT_LOCAL_KEY_CERTIFICATE': 64, 'EXACT_DEPTH_CLOSED_PARENT': 198, 'PRE_REPORT_EXACT_DEPTH_CERTIFICATE': 1338}
```

Bucket status counts:

```text
{'CLOSED_BY_BASE_DESCENT': 30654, 'CLOSED_BY_QUOTIENT': 228, 'COVERED_BUT_CAP_REACHED': 286, 'CLOSED_WITH_LOCAL_KEYS': 64, 'CLOSED': 198, 'CLOSED_BY_EXACT_VALID_K': 1338}
```

## What Is Still Not Connected

The 84 symbolic packet is verified separately:

```text
84 groups: 84
84 group member sum: 7364628
```

But the current base/exact route artifacts do not export a field like
`symbolic_group_id`, `class_id`, or `packet_class_id` that maps each route/member
into one of those 84 groups.

```text
base rows with exported 84 group id: 0
base rows missing exported 84 group id: 32768
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
