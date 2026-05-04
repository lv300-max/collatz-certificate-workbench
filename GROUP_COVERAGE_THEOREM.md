# Group Coverage Theorem Packet

Status line:

`Certificate algebra verified. Coverage theorem still needs review.`

## Claim Under Review

Every odd residue class in the workbench frontier enters exactly one certified branch:

1. a shallow/base descent branch,
2. a pre-report exact-depth parent branch,
3. an exact-depth closed parent branch,
4. a deep parent branch closed by exact-state evidence,
5. or one of the verified 84 symbolic certificate rows after grouping.

If the grouping/partition theorem is independently accepted, then every odd `n > 1` has a certified finite descent below itself. The usual minimal-counterexample argument would then force every Collatz trajectory to reach `1`.

## Source Audit Table

| audit | status | key counts |
|---|---|---|
| Residue partition exhaustiveness | `PASS_RESIDUE_PARTITION_EXHAUSTIVENESS` | total odd base residues `32768`; assigned once `32768`; missing `0`; duplicates `0`; sampled-as-proof `0` |
| Density partition | `PASS_DENSITY_PARTITION` | covered slots `32768`; missing slots `0`; duplicate/overlap slots `0` |
| Full framework exact-state closure | `PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE` | parents checked/closed `578 / 578`; exact states checked `1235`; compact quotient-only rows `0` |
| Master source coverage | `PASS` | proof-critical files missing `0`; source export status `PASS` |
| Zero-new-cases D-gold audit | `D_GOLD_ZERO_NEW_CASES_AUDIT_PASS` | failures `0`; 84-label packet stable through `k41` |
| Formal verifier | `FORMAL_VERIFIER_PASS_WITH_GROUP_COVERAGE_CAVEAT` | packet rows checked `84`; passed `84`; failed `0` |

## Frontier Partition

The audited base universe is odd residues `r0 mod 2^16`.

| bucket | count |
|---|---:|
| shallow_valid_at_k16 | 30654 |
| pre_report_exact_depth_parent | 1338 |
| exact_depth_closed_parent | 198 |
| deep_parent | 578 |
| total | 32768 |

Partition facts:

- assigned once: `32768`
- missing: `0`
- duplicates: `0`
- sampled-as-proof rows: `0`

## Symbolic Certificate Group Table

The 84 symbolic rows are cost-table groups. The row algebra has been verified by `formal_verifier.py`.

| item | value |
|---|---:|
| packet records | 84 |
| packet rows passed | 84 |
| packet rows failed | 0 |
| group member sum | 7364628 |
| classes audited | 7364628 |
| forcing modulus | `2^(A+1)` |
| affine denominator | `2^A` |
| stable through | `k41` |
| max A | 395 |
| max full step | 644 |

For each displayed row the verifier recomputed:

- valuation word hash,
- valuation-word forcing modulo `2^(A+1)`,
- affine tuple `T^m(n) = (3^m n + b) / 2^A`,
- `gap = 2^A - 3^m > 0`,
- `B = ceil(b / gap)`,
- `min_n > B`,
- representative descent below itself.

## Exact-State Branch Closure

The full framework audit reports:

- parents checked: `578`
- parents closed: `578`
- exact states checked: `1235`
- compact quotient-only rows: `0`

This is the key non-symbolic branch check: no proof-critical row is left relying only on compact quotient abstraction.

## What This Establishes

The engine has passed the current finite evidence stack:

1. no missing base residue class,
2. no duplicate residue assignment,
3. all exact-state branches close,
4. all displayed 84 symbolic certificate rows pass raw integer verification,
5. no new packet labels appeared in the checked compressed recurrence through `k41`.

## What Still Needs Review

This document is not a public proof by itself.

The remaining theorem to review is:

`Every odd n enters one of the audited branches or one of the 84 verified symbolic cost-table groups.`

Equivalently:

`The grouping/partition map from arbitrary odd n to the finite certificate system is exhaustive and conflict-free.`

That is the final bridge between the verified certificate algebra and a proof of the Collatz conjecture.
