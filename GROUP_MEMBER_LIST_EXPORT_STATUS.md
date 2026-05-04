# Group Member List Export Status

Generated: 2026-05-04T16:33:07.102100+00:00

## Exported

- `base_partition_full_member_list.json`
- Odd residues modulo `2^16`: `32768 / 32768`
- Missing: `0`
- Duplicates: `0`
- Sampled-as-proof rows: `0`

## Not Exportable From Current Files

The full pre-aggregation member list behind the 84 symbolic certificate groups is not present in this repo.

The packet files contain:

- 84 grouped records
- `group_member_count` per record
- canonical certificate per group
- total grouped members: `7364628`

They do not contain the individual `7364628` member rows.

## Reviewer Impact

The base partition member list is complete and exportable.

The 84-group membership theorem still needs one of these:

1. `group_membership_full.json` with all `7364628` member rows, or
2. a formal membership rule proving exactly which lanes belong to each of the 84 groups.

Without that artifact, the honest status remains:

```text
certificate algebra verified
base partition exported
84 group counts verified
full 84-group member list missing
grouping theorem still requires independent review
```
