# How To Verify

Run these commands from the repository root's parent directory or after opening this folder directly:

```bash
cd collatz_certificate_final
python3 final_certificate_audit.py
python3 -m json.tool final_certificate_audit_report.json
python3 -m py_compile final_certificate_audit.py
```

Expected output from the audit command:

```text
PASS_CERTIFICATE_PIPELINE:
All tracked parent obstructions were covered by the certificate pipeline under exact integer arithmetic. Independent mathematical review is still required to verify that the certificate framework is logically exhaustive.
```

Other scripts included for deeper reproduction, in dependency order:

```bash
python3 exact_depth_closure.py
python3 frontier_return_map.py
python3 b_control_test.py
python3 frontier_coverage_audit.py
python3 quotient_parent_batch_audit.py
```

Those deeper runs can be substantially slower than the final report audit.
