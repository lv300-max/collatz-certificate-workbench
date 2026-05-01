# Quotient Full-Equivalence Obstruction

Status: `FULL_EQUIVALENCE_NOT_PROVEN`

The compact quotient key used by `excursion_quotient_analyzer.py` is

```text
(s, q, u, v) = (level - c, ((3^o * residue + b) >> c) mod 2^s, o - 306, c - 485)
```

This key determines the local quotient successor rule:

```text
s > 0, q even: (s,q,u,v) -> (s-1, q/2, u, v+1)
s > 0, q odd : (s,q,u,v) -> (s, (3q+1) mod 2^s, u+1, v)
s = 0       : (0,0,u,v) -> {(1,0,u,v), (1,1,u,v)}
```

That is not enough for the requested full-equivalence lemma. Terminal
certification depends on the exact affine carry `b` through
`B = ceil(b / (2^c - 3^o))` when the gap is positive. The compact key stores
`o` and `c` via offsets, so the gap is recomputable, but it does not store exact
`b`, a declared sufficient modulus for `b`, exact residue `r`, exact modulus or
depth, or the frontier/parity history.

The exported transition table is a tracked closure table, not a full
representative-class export. It has 948 tracked rows, all terminal or closed, and the tracked transition
audit passes. However, every same-key representative row is missing at least
one of the exact representative fields needed for a full class comparison:
`a, residue, steps`.

Collision review result:

```json
{
  "INSUFFICIENT_DATA": 948
}
```

The obstruction is therefore structural and evidentiary:

1. The key omits proof-critical state (`b`, exact residue/modulus/depth, and
   terminal outcome).
2. The table exports tracked representatives and later certification witnesses,
   not all representatives in each quotient class.
3. No external algebraic lemma is present proving that the omitted fields are
   irrelevant for certification, B-control, or final bridge outcome.

Conclusion: the tracked quotient table remains valid as a tracked exact-state
fallback artifact, but the full quotient-class equivalence lemma is incomplete.
This does not prove Collatz.
