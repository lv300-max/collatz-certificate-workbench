# Five-Minute Review Guide

## Step 1

Open `FINAL_AUDIT_SUMMARY.md`.
Confirm the final audit says `PASS_CERTIFICATE_PIPELINE`.

## Step 2

Open `CERTIFICATE_FRAMEWORK_THEOREM.md`.
Read the main theorem and the lemma chain.

## Step 3

Look at the two structural gates:

Gate 1:
Residue partition exhaustiveness.

Question:
Does exact depth <=18 plus the 578 depth >18 parents cover every odd n > 1?

Gate 2:
Quotient abstraction validity.

Question:
Does a quotient key preserve enough state to represent a full class?

## Step 4

If either gate fails, the framework fails.
If both gates hold, inspect the arithmetic reports.

## Step 5

Run:

```bash
python3 final_certificate_audit.py
```

Expected result:
`PASS_CERTIFICATE_PIPELINE`

The review goal is not to be impressed.
The review goal is to break the framework.
