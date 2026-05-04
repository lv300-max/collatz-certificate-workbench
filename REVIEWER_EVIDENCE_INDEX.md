# Reviewer Evidence Index

Status: `REVIEWER_EVIDENCE_INDEX_BUILT`

This file gathers the strongest outputs currently available. It does **not** claim final accepted proof. It makes the review target sharper.

## Legacy Full Certificate Layer

- file: `collatz_certificate.json`
- sha256: `479645e83e56cb2864d6a4340ee945ca00c2dbed466a3d1e575d3326de31cca7`
- total certificates: `1210087`
- source counts: `{'valid_k16': 63421, 'invalid_k16_root': 2114, 'bfs_sibling_sampled': 49664, 'bfs_sibling_exact': 1094888}`
- k=16 entries: `32768`
- k=16 unique odd residues: `32768`
- k=16 missing: `0`
- exact verified by `certificate_verify.py`: `1,160,423`
- exact failures: `0`
- sampled, not exact: `49664`
- direct verified odd range: `3..200001`
- direct failures: `0`
- unclosed lanes: `0`
- sibling failures: `0`
- max threshold: `725`

## 84 Symbolic Packet Layer

- file: `certificate_packet_84.json`
- status: `84-LABEL SYMBOLIC CERTIFICATE PACKET STABLE THROUGH k41`
- group count: `84`
- classes audited: `7364628`
- formal verifier status: `FORMAL_VERIFIER_PASS_WITH_GROUP_COVERAGE_CAVEAT`
- rows checked/passed/failed: `84 / 84 / 0`
- forcing modulus: `2^(A+1)`
- affine denominator: `2^A`
- stable through: `k41`

## Coverage Layer

- base partition assigned once: `32768 / 32768`
- base partition missing: `0`
- base partition duplicates: `0`
- exact-state parents closed: `578 / 578`
- exact states checked: `1235`
- compact quotient-only rows: `0`
- D-gold status: `D_GOLD_ZERO_NEW_CASES_AUDIT_PASS`
- full framework status: `PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE`

## Remaining Review Target

Export or prove the membership/grouping rule that maps arbitrary odd `n` into exact branches or verified 84-row symbolic certificate groups.
