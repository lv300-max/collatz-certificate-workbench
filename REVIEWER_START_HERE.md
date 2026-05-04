# Collatz Certificate Workbench — Reviewer Start Here

## Status

This repository contains a finite symbolic certificate system candidate for Collatz.

It does **not** claim final accepted proof.

Current status:

```text
Certificate algebra verified.
Base partition complete.
84 packet rows verified.
Stable through k41.
Remaining review target: grouping/partition theorem.
```

## Main Verified Data

```text
odd base residues assigned once: 32768 / 32768
missing classes: 0
duplicate conflicts: 0

exact-state parents closed: 578 / 578
exact states checked: 1235
compact quotient-only rows: 0

84 packet rows verified: 84 / 84
packet failures: 0

stable through: k41
```

## Core Certificate

For a class with fixed valuation word:

```text
T^m(n) = (3^m n + b) / 2^A
```

Define:

```text
gap = 2^A - 3^m
B = ceil(b / gap)
```

If:

```text
gap > 0
n > B
```

then:

```text
T^m(n) < n
```

## Correct Forcing Rule

Important:

```text
valuation forcing modulus = 2^(A+1)
affine denominator = 2^A
```

So each class is checked as:

```text
n ≡ r mod 2^(A+1)
```

That residue forces the valuation word.

## Main Lemmas

- Finite Partition Lemma
- Valuation Forcing Lemma
- Affine Formula Lemma
- Descent Lemma
- Lift Closure Lemma
- Octave Recurrence Lemma
- Minimal Counterexample Trap Lemma

## What Passed

```text
FORMAL_VERIFIER_PASS_WITH_GROUP_COVERAGE_CAVEAT
packet rows checked: 84
packet rows passed: 84
packet rows failed: 0
failures: 0
```

## What Still Needs Review

The algebra passed.

The remaining wall is:

Every arbitrary odd `n` must be formally shown to enter:

1. an audited exact-state closure branch, or
2. one of the verified 84 symbolic certificate groups.

## Suggested Reviewer Question

Does the grouping/partition map from arbitrary odd `n` into the audited branches or verified 84 symbolic certificate groups hold universally?

If yes, the descent certificates rule out a smallest counterexample.

If no, the proof breaks there.
