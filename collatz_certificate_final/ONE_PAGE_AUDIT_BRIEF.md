# One-Page Audit Brief

## A. What this is

A Collatz symbolic certificate framework using exact integer arithmetic.

## B. What it checks

It turns residue lanes into affine iterate certificates:

```text
T^m(n) = (3^o · n + b) / 2^c
```

## C. What certifies descent

A lane descends when:

```text
2^c > 3^o
```

and:

```text
B = ceil(b / (2^c - 3^o))
```

falls inside a directly verified bridge.

## D. Final internal audit

```text
Parent coverage: PASS
Local keys: PASS
Covered-but-cap-reached: PASS
Frontier coverage: PASS
B-control: PASS
Return map: PASS
Direct bridge: PASS
Exact depth: PASS
Exact arithmetic: PASS
```

Final status:

```text
PASS_CERTIFICATE_PIPELINE
```

## E. Key counts

- processed parents: 578 / 578
- unprocessed: 0
- closed_by_quotient: 228
- closed_with_local_keys: 64
- COVERED_BUT_CAP_REACHED: 286
- local_keys_still_open: 0
- NEEDS_HIGHER_LOCAL_CAP: 0
- conflicts: 0

## F. Main review target

The two high-value places to attack are:

1. residue partition exhaustiveness
2. quotient abstraction validity
