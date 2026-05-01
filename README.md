# Collatz Certificate Workbench

This repository contains the Collatz certificate workbench scripts, generated
audit reports, and browser UI.

Current honest status:

The declared r0 mod 2^16 frontier, exact-depth layer, 578 deep parents,
cap-stopped rows, local keys, return-map states, high-B returns, and previously
quotient-closed parents are now all covered by exact source reports or full
exact-state certificates. No proof-critical row relies only on compact quotient
abstraction. Independent mathematical review is still required before any
public proof claim.

## Large Artifact Notice

`collatz_certificate.json` is approximately 390 MB and is not stored directly in
this repository.

It can be regenerated with:

```bash
python3 certificate_export.py
```

A SHA-256 checksum is provided in `collatz_certificate.sha256` for verification.
See `ARTIFACTS.md` for download, regeneration, and verification details.
