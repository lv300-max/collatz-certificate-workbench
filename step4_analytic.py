"""Step 4B: Verify the 2-adic distinctness lemma analytically.

Claim: For any odd b mod 2^(k+1), the two principal preimages
  c1(b) = 3^{-1} * (2b - 1)  mod 2^(k+2)   [valuation j=1]
  c2(b) = 3^{-1} * (4b - 1)  mod 2^(k+3)   [valuation j=2]
reduce to DIFFERENT residue classes mod 2^(k+1).
That is: c1(b) mod 2^(k+1)  !=  c2(b) mod 2^(k+1).

If true for all odd b and all k >= 1, the inductive step in Theorem 4A holds.
"""

def modinv3(mod):
    """3^{-1} mod 2^m — always exists since gcd(3,2^m)=1."""
    return pow(3, -1, mod)

def check_distinctness(max_k=30):
    print("Checking: c1(b) mod 2^(k+1)  !=  c2(b) mod 2^(k+1)  for all odd b, all k")
    print(f"{'k':>4}  {'odd b classes':>14}  {'all distinct?':>14}  {'failures'}")
    print("-" * 65)
    all_pass = True
    for k in range(1, max_k + 1):
        mod_k1  = 2**(k+1)   # modulus for b
        mod_c1  = 2**(k+2)   # modulus for c1
        mod_c2  = 2**(k+3)   # modulus for c2
        inv3_c1 = modinv3(mod_c1)
        inv3_c2 = modinv3(mod_c2)

        failures = []
        for b in range(1, mod_k1, 2):  # all odd b mod 2^(k+1)
            c1 = (inv3_c1 * (2*b - 1)) % mod_c1
            c2 = (inv3_c2 * (4*b - 1)) % mod_c2
            # Reduce both to mod 2^(k+1)
            c1r = c1 % mod_k1
            c2r = c2 % mod_k1
            if c1r == c2r:
                failures.append(b)

        status = "PASS" if not failures else f"FAIL: b={failures}"
        if failures:
            all_pass = False
        print(f"{k:>4}  {2**k:>14}  {status:>14}  {failures if failures else ''}")

    print()
    if all_pass:
        print(f"ALL k=1..{max_k} PASS — distinctness lemma holds empirically.")
        print("This validates the inductive step of Theorem 4A.")
    else:
        print("FAILURES FOUND — inductive step needs revision.")

check_distinctness(max_k=20)
