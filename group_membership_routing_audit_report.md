# Group Membership Routing Audit

Generated: 2026-05-04T16:45:48.771507+00:00

## Status

```text
GROUP_MEMBERSHIP_ROUTING_AUDIT_BLOCKED_MISSING_84_LINKS
```

This audit checks the route evidence that is currently present in the repo. It
does not claim a completed proof.

## Base Partition

```text
pass: True
total odd residues: 32768
assignment rows: 32768
assigned once: 32768
missing: 0
duplicates: 0
bad assignment rows: 0
sampled-as-proof rows: 0
```

Bucket counts:

```text
{'shallow_valid_at_k16': 30654, 'deep_parent': 578, 'exact_depth_closed_parent': 198, 'pre_report_exact_depth_parent': 1338}
```

## Exact-State Closure

```text
pass: True
parents closed: 578 / 578
exact states checked: 1235
compact quotient-only rows: 0
```

Terminal outcomes:

```text
{'CERTIFIED_RETURN': 862, 'HIGH_B_THEN_CERTIFIED': 373}
```

## 84 Symbolic Packet

```text
pass: True
groups: 84
group member sum: 7364628
failures: 0
status: 84-LABEL SYMBOLIC CERTIFICATE PACKET STABLE THROUGH k41
```

## End-To-End 84-Group Membership

```text
pass: False
base routes checked: 32768
routes with explicit 84-group link: 0
routes missing explicit 84-group link: 32768
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
