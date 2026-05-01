# What if Collatz does not need every number counted?

A finite certificate pipeline for residue-lane descent.

This packet does not ask you to believe a proof claim.
It asks you to attack two structural questions:

1. Is the residue partition exhaustive?
2. Do quotient classes preserve the proof-critical state?

If both are yes, the remaining packet is mostly exact arithmetic verification.

The core certificate form is:

```text
T^m(n) = (3^o · n + b) / 2^c
```

Define:

```text
gap = 2^c - 3^o
B = ceil(b / gap)
```

If `gap > 0` and `n > B`, then `T^m(n) < n`.

Audit result:

```text
PASS_CERTIFICATE_PIPELINE:
All tracked parent obstructions were covered by the certificate pipeline under exact integer arithmetic. Independent mathematical review is still required to verify that the certificate framework is logically exhaustive.
```

**Do not believe it. Audit it.**
