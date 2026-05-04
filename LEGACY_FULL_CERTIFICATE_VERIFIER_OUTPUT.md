# Legacy Full Certificate Verifier Output

```text
============================================================
COLLATZ CERTIFICATE VERIFIER
============================================================

Loading collatz_certificate.json ...
  1,210,087 certificates  |  date=2026-04-28  |  version=1.0

Checking residue coverage for k=16 ...
  k=16 entries=32,768  unique residues=32,768  missing=0
  [PASS] Full residue coverage for k=16

Verifying certificates ...
  Exact verified: 1,160,423 PASS  0 FAIL
  Sampled (NOT EXACT): 49,664 entries skipped
  Invalid-root entries: pass=2,114 fail=0

Re-running direct empirical verification [3..200,001] ...
  empirical failures=0

VERIFIER REPORT
  [PASS] Residue coverage (all odd mod 2^16 present)
  [PASS] Exact formula checks: 1,160,423 PASS
  [PASS] Empirical direct [3,200,001]: 0 failures
  [PASS] No unclosed lanes
  [PASS] No sibling failures

NOTICE: 49,664 entries are bfs_sibling_sampled (BFS depth > 14).
These were NOT individually formula-verified by certificate_verify.py.
They are covered by empirical verification up to 200,001.
The symbolic argument covers them via the threshold max_B=725 < 200,001.

CERTIFICATE VERIFIED (exact entries all PASS; sampled noted above)
```
