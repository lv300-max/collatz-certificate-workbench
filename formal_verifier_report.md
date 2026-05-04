# Formal Verifier Report

Status: `FORMAL_VERIFIER_PASS_WITH_GROUP_COVERAGE_CAVEAT`

- Packet rows checked: `84`
- Packet rows passed: `84`
- Packet rows failed: `0`
- Group member sum: `7364628`
- Classes audited: `7364628`
- Collatz proven by this file: `False`

## Source Statuses

- zero_new_cases_d_gold: `D_GOLD_ZERO_NEW_CASES_AUDIT_PASS`
- residue_partition: `PASS_RESIDUE_PARTITION_EXHAUSTIVENESS`
- residue_partition_assigned_once: `32768`
- residue_partition_missing: `0`
- residue_partition_duplicates: `0`
- residue_partition_sampled_as_proof: `0`
- residue_density: `PASS_DENSITY_PARTITION`
- density_covered_slots: `32768`
- density_missing_slots: `0`
- density_duplicate_overlap_slots: `0`
- full_framework: `PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE`
- parents_checked: `578`
- parents_closed: `578`
- exact_states_checked: `1235`
- compact_quotient_only_rows: `0`
- master_source: `PASS`

## Caveat

The verifier checks all displayed packet rows and source audit statuses. The 84 packet rows are cost-table groups, so a final proof still needs independent review of the grouping/partition theorem that maps every odd n to a displayed certified group or exact-state closure branch.

## Checked Result

All displayed 84 packet rows passed raw integer verification: valuation hash, forced word modulo `2^(A+1)`, affine tuple, positive gap, `min_n > B`, and representative descent.
