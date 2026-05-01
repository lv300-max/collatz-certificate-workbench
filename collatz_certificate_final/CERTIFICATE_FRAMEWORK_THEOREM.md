**Do not believe it. Audit it.**

# Collatz Symbolic Certificate Framework — Theorem and Audit Map

## 1. Claim Boundary

This document does not claim independent acceptance of a Collatz proof.
It states the certificate framework that passed the internal audit.
The purpose is to identify the exact structural lemmas that require outside review.

If the residue partition is exhaustive and the quotient abstraction is valid, the arithmetic audit is already closed.

## 2. Core Map

Let the Collatz map be

```text
T(n) = n/2     if n is even
T(n) = 3n + 1 if n is odd
```

A symbolic lane iterate has the affine form

```text
T^m(n) = (3^o n + b) / 2^c
```

where:

- `m` is the total number of raw Collatz steps.
- `o` is the number of odd-growth steps.
- `c` is the total halving count.
- `b` is the accumulated affine carry.

Define

```text
gap = 2^c - 3^o
```

If `gap > 0`, then

```text
T^m(n) < n
```

for all `n > B`, where

```text
B = ceil(b / gap)
```

The exact integer implementation is

```text
B = (b + gap - 1) // gap
```

No floating-point comparison is used for proof-critical gap or threshold checks.

## 3. Main Certificate Theorem

Internal theorem:

If every odd `n > 1` belongs to one certified residue lane, and each certified lane has either:

A. direct bridge coverage,
B. exact symbolic descent with `B <= 200001`,
C. quotient return coverage plus B-control with final `B <= 200001`,

then every positive integer reaches `1` by strong induction.

The packet verifies the certificate chain. Independent review must verify that the residue coverage and quotient abstraction are logically exhaustive.

## 4. Lemma 1 — Exhaustiveness of Residue Partition

Exact depth `<=18` plus the 578 depth `>18` parents must cover every odd `n > 1` in the intended framework.

Reviewer questions:

- Are all odd residue classes included?
- Are there missing or duplicate residue parents?
- Does every odd `n > 1` map into exactly one covered bucket?
- Does the transition from exact depth `<=18` to 578 deep parents lose any residue classes?

Report links:

- `exact_depth_closure_report.json`
- `quotient_parent_batch_report.json`
- `final_certificate_audit_report.json`

Status:

- Computational audit: PASS
- Independent structural review: REQUIRED

## 5. Lemma 2 — Validity of Quotient Abstraction

A quotient key must represent a full equivalence class, not merely one explored representative.

Reviewer questions:

- Does a quotient key preserve all proof-relevant state?
- Do two members of the same quotient key have identical return/certification behavior?
- Are quotient conflicts impossible or merely unobserved?
- Does the `conflicts = 0` audit prove consistency only for explored states, or for the full class?

Report links:

- `excursion_quotient_report.json`
- `frontier_coverage_audit_report.json`
- `quotient_parent_coverage_audit_report.json`

Status:

- Computational audit: PASS on tracked frontier
- Independent structural review: REQUIRED

## 6. Lemma 3 — Covered-But-Cap-Reached Rows

Rows marked `COVERED_BUT_CAP_REACHED` are accepted only if every open/cap-stopped key is already mapped to a certified return path or covered by row-level frontier/B-control evidence.

Reviewer questions:

- Does each row have explicit coverage source?
- Are any rows accepted merely because the cap was reached?
- Are all open keys accounted for?

Report links:

- `quotient_parent_batch_report.json`
- `final_certificate_audit_report.json`

Status:

- Internal audit: PASS

## 7. Lemma 4 — Local-Key Continuation

Cap-stopped local keys are continued independently from their exact affine state. This is valid only if the local key contains enough exact state data to continue without relying on global context.

Reviewer questions:

- Does each local key store exact `o`, `c`, `b`, word/residue data?
- Is continuation from that state equivalent to continuing the original parent branch?
- Are final `B` values inside the bridge?

Report links:

- `quotient_parent_batch_report.json`
- `parent_key_debug_5759.json` if present
- `final_certificate_audit_report.json`

Status:

- Internal audit: PASS

## 8. Lemma 5 — B-Control

High-B returns are not accepted immediately. They must map to a later certified state with final `B <= 200001`.

Reviewer questions:

- Are all high-B states included?
- Does every high-B chain eventually certify?
- Is `B` computed exactly?
- Is there any hidden float decision?

Report links:

- `b_control_report.json`
- `frontier_return_map_report.json`
- `frontier_coverage_audit_report.json`

Status:

- Internal audit: PASS

## 9. Lemma 6 — Direct Bridge Compatibility

Every final threshold `B` is `<= 200001`. The direct bridge verifies every odd `n` in `[3, 200001]`. Therefore any lane with `B <= 200001` is absorbed by the verified bridge.

Reviewer questions:

- Does the direct bridge include all odd `n` from `3` to `200001`?
- Are there zero failures?
- Are all final `B` values within this range?

Report links:

- `direct_bridge_report.json`
- `final_certificate_audit_report.json`

Status:

- Internal audit: PASS

## 10. Lemma 7 — No Sampled Evidence in Proof Path

Sampled evidence may guide exploration but must not be used in proof-critical closure.

Reviewer questions:

- Are any sampled rows used as proof?
- Does exact depth closure exclude sampled rows?
- Are parent/frontier/B-control closures exact for tracked states?

Report links:

- `exact_depth_closure_report.json`
- `final_certificate_audit_report.json`
- `MANIFEST.json`

Status:

- Internal audit: PASS if exact-depth report has `sampled_rows_used = 0`

## 11. Strong Induction Closure

Once every odd `n > 1` has a finite iterate `T^m(n) < n`, strong induction gives termination:

- Base case: `1` terminates.
- If all positive integers below `n` terminate, and `T^m(n) = q < n`, then `q` terminates, so `n` terminates.
- Even `n` descends immediately by `n/2 < n`.
- Therefore all positive integers terminate, provided the descent certificate coverage is exhaustive.

## 12. Final Audit Result

```text
PASS_CERTIFICATE_PIPELINE:
All tracked parent obstructions were covered by the certificate pipeline under exact integer arithmetic. Independent mathematical review is still required to verify that the certificate framework is logically exhaustive.
```

## 13. Reviewer Attack List

Please attack these first:

1. Exhaustiveness of residue partition.
2. Validity of quotient abstraction.
3. Whether `COVERED_BUT_CAP_REACHED` rows are logically closed, not just cap-stopped.
4. Whether local-key continuation is state-complete.
5. Whether any sampled evidence enters proof-critical paths.

## 14. Appendix — Commands

Run the final audit:

```bash
cd collatz_certificate_final
python3 final_certificate_audit.py
python3 -m json.tool final_certificate_audit_report.json
python3 -m py_compile final_certificate_audit.py
```

Regenerate the exact-depth closure report:

```bash
cd collatz_certificate_final
python3 exact_depth_closure.py
python3 -m json.tool exact_depth_closure_report.json
python3 -m py_compile exact_depth_closure.py
```
