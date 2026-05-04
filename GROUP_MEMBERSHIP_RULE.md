# Group Membership Rule

## Status

This is the remaining theorem needed for review.

The certificate algebra is verified. The base partition is complete. The 84
certificate rows are verified.

The remaining question is:

```text
Why must every odd n enter one audited branch or one of the 84 symbolic certificate groups?
```

## Rule

### Input

Let `n` be any odd positive integer.

### Step 1 — Base Residue

Compute:

```text
r = n mod 2^16
```

Since `n` is odd, `r` is one of the `32,768` odd residues modulo `2^16`.

Verified data:

```text
odd residues assigned: 32768 / 32768
missing: 0
duplicates: 0
sampled-as-proof rows: 0
```

Therefore every odd `n` has exactly one base residue assignment.

### Step 2 — Base Partition Assignment

The base partition assigns each odd residue `r mod 2^16` to exactly one initial
state.

This gives a deterministic map:

```text
odd n -> base residue r -> assigned state
```

Required properties:

```text
total: every odd residue is assigned
unique: no odd residue has two conflicting assignments
```

Verified:

```text
total = yes
unique = yes
```

### Step 3 — Exact-State Routing

From the assigned state, the system follows the exact-state closure map.

Verified:

```text
parents closed: 578 / 578
exact states checked: 1235
compact quotient-only rows: 0
```

The important point:

```text
No closure depends only on a compact quotient abstraction.
Exact states are checked directly.
```

So the route is not merely sampled or guessed.

### Step 4 — Terminal Outcome

Every routed state must end in one of two outcomes:

1. a closed exact-state branch
2. a verified 84-row symbolic certificate group

This is the central membership claim.

Formally:

```text
For every odd n, the base residue route terminates in:

closed_branch(n)

or

certificate_group_i(n), where i is in {1, ..., 84}.
```

## Certificate Group Rule

If `n` lands in certificate group `i`, then that group provides:

```text
r_i
A_i
m_i
b_i
gap_i
B_i
min_n_i
valuation_word_i
```

The forcing condition is:

```text
n ≡ r_i mod 2^(A_i + 1)
```

This forces the valuation word.

The affine formula is:

```text
T^m_i(n) = (3^m_i * n + b_i) / 2^A_i
```

The descent condition is:

```text
gap_i = 2^A_i - 3^m_i > 0
B_i = ceil(b_i / gap_i)
min_n_i > B_i
```

Therefore every `n` in the group satisfies:

```text
T^m_i(n) < n
```

## Lift Closure

Every lift:

```text
n = r_i + k * 2^(A_i + 1)
```

keeps the same residue modulo `2^(A_i + 1)`.

Therefore it keeps:

```text
same valuation word
same m
same A
same b
same gap
same B
same descent certificate
```

So the certificate applies to all lifts, not just the representative.

## Minimal Counterexample Trap

Assume a smallest odd counterexample `N` exists.

By the membership rule, `N` enters either:

1. a closed exact-state branch
2. one of the 84 symbolic certificate groups

If it enters a closed exact-state branch, it is closed.

If it enters a symbolic certificate group, its certificate forces:

```text
T^m(N) < N
```

That contradicts `N` being the smallest counterexample.

Therefore, if the membership rule is valid, no smallest counterexample exists.

## What Must Be Reviewed

The certificate algebra is already verified.

The remaining review target is this statement:

```text
Every odd n maps from its base residue through exact-state routing into either:

1. a closed exact-state branch, or
2. one of the verified 84 symbolic certificate groups.
```

This theorem must be checked independently.

## Reviewer Checklist

A reviewer should verify:

- [ ] Every odd residue mod `2^16` appears exactly once.
- [ ] The base residue assignment is deterministic.
- [ ] Exact-state routing is total.
- [ ] Exact-state routing has no quotient-only shortcut.
- [ ] Every route terminates.
- [ ] Every terminal route is either closed or assigned to one of 84 groups.
- [ ] Every 84-group assignment satisfies `n ≡ r mod 2^(A+1)`.
- [ ] The forced valuation word is valid.
- [ ] The affine formula is valid.
- [ ] `gap > 0`.
- [ ] `min_n > B`.
- [ ] Therefore every lift descends below itself.

## Short Status

```text
certificate algebra: verified
base partition: complete
exact-state parents: closed
84 symbolic rows: verified
octave recurrence: stable through k41
remaining wall: prove group membership rule
```
