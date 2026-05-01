**Do not believe it. Audit it.**

# Reviewer Questions

- Are the residue parent classes exhaustive?
- Does exact depth <=18 plus the 578 depth >18 parents cover all odd n > 1?
- Are any sampled-only results used as proof?
- Are all B thresholds computed exactly?
- Does every final B fall inside the direct bridge?
- Are all cap-stopped keys locally continued?
- Is COVERED_BUT_CAP_REACHED logically justified row by row?
- Are there any missing parents, duplicate parents, or uncovered keys?
- Is there any hidden float-based proof decision?
- Can the final audit be independently reproduced?
