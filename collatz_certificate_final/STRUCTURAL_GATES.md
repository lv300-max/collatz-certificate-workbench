# The Two Gates That Matter

## Gate 1 - Residue Partition Exhaustiveness

Claim to check:
Every odd n > 1 belongs to either:

- an exact-depth closed lane, or
- one of the 578 deep parent lanes.

Reviewer attack questions:

- Are any odd residue classes missing?
- Are any duplicated?
- Is the split exact?
- Is any sampled evidence used?
- Does every odd n map to one bucket?

## Gate 2 - Quotient Abstraction Validity

Claim to check:
A quotient key preserves all proof-critical information needed for return/B-control certification.

Reviewer attack questions:

- Can two different branches share a quotient key but later diverge?
- Does the key store enough affine/residue state?
- Are quotient conflicts ruled out by theorem or only unobserved?
- Is "conflicts = 0" a theorem or just an audit result?
- Are all cap-stopped keys continued from exact state?

If Gate 1 and Gate 2 survive review, the remaining certificate packet is mostly exact arithmetic verification.
