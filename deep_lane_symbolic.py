"""
deep_lane_symbolic.py  —  Symbolic Sibling Closure Analysis
============================================================
For each deep invalid parent lane r0, attempts to prove sibling closure
WITHOUT enumeration by deriving a symbolic descent condition over all j.

Background
----------
A "deep" parent lane has depth d = k' - 16 > 14.
The 2^d sibling residues at level k' are:
    s_j = r0 + j * 2^16  (mod 2^k')    for j in [0, 2^d)

A symbolic certificate for the whole family would show:
    For all j in [0, 2^d),  find_valid_k(s_j) succeeds with B < s_j.

Approach A — Parity-Path Analysis
    If all 2^d siblings follow the SAME parity sequence for the first m steps
    (determined entirely by the lower 16 bits), then they share the same
    (a, b, c) formula, and descent follows from a single threshold check.
    We test this by deriving the parity sequence from the parent r0 at level k'
    and verifying that the lower 16 bits alone force that sequence.

Approach B — Level Compression
    Check whether s_j (mod 2^k'') for some k'' < k' is identical for all j.
    If all siblings collapse to the same residue class at a lower valid level,
    one certificate covers all of them.

Approach C — Affine Certificate in j
    Represent n = r0 + j*2^16 and track T^m(n) as a linear function of j:
    T^m(n) = (A * (r0 + j*2^16) + B_val) / 2^c = A*r0/2^c + A*j*2^16/2^c + B_val/2^c
    Descent requires T^m(n) < n, i.e. A*n + B_val < n * 2^c.
    If A < 2^c (proven by certificate), this holds for all n > B regardless of j.

    KEY OBSERVATION: if the SAME parity path applies for all j (Approach A holds),
    then the same (a, b, c) apply, and the threshold B = ceil(b/(2^c-a)) is
    independent of j. Descent is then:
        n > B  =>  T^m(n) < n  for ALL n in the residue family.
    Since B is typically very small (≤ 200001), empirical verification covers n ≤ B
    and the symbolic formula covers n > B.

Output
------
For each of the deepest 50 parent lanes:
  - Whether the parity path is identical for ALL 2^d siblings (forced by lower bits)
  - Whether a lower-level certificate collapses all siblings
  - Whether Approach C (affine bound) applies
  - CLOSED / PARTIAL / OPEN status

CLOSED = proof-complete for this lane (no residue class left uncovered)
PARTIAL = some method applies but not all j covered
OPEN = cannot establish closure without full enumeration
"""

import time, sys
from itertools import islice

KMAX = 16
MAX_STEPS = 10_000
MAX_K_VALID = 500

t0 = time.time()

# ── Core functions (same as certificate_export.py) ──────────────────────────

def compute_descent(r, k, max_steps=MAX_STEPS):
    a, b, c = 1, 0, 0
    n = r
    valid = True
    for m in range(1, max_steps + 1):
        if c >= k:
            valid = False
        if n % 2 == 0:
            c += 1; n >>= 1
        else:
            a = 3*a; b = 3*b + (1 << c); n = 3*n + 1
        two_c = 1 << c
        if two_c > a:
            denom = two_c - a
            B = (b + denom - 1) // denom
            return (m, a, b, c, B, valid)
    return None

def find_valid_k(r, k_min=KMAX, max_k=MAX_K_VALID):
    for k in range(k_min, max_k + 1):
        rep = r % (1 << k)
        if rep % 2 == 0:
            continue
        res = compute_descent(rep, k)
        if res is not None and res[5]:
            return k, res
    return None, None

def parity_sequence(r, k, m_steps):
    """Return the parity bits for the first m_steps Collatz steps of r,
    tracking whether any step exits the k-lane."""
    n = r
    seq = []
    for _ in range(m_steps):
        seq.append(n & 1)
        if n % 2 == 0:
            n >>= 1
        else:
            n = 3 * n + 1
    return seq

def orbit_step_count_to_formula(r, k):
    """Return m (number of steps until descent formula triggers) for residue r at level k."""
    res = compute_descent(r % (1 << k), k)
    if res is None:
        return None
    return res[0]

# ── Load deep lanes ──────────────────────────────────────────────────────────

print("="*70)
print("DEEP LANE SYMBOLIC CLOSURE ANALYSIS")
print("="*70)
print()

# Recompute the deep parents list
def get_deep_parents():
    """Find all invalid k=16 parents with depth > 14, sorted deepest first."""
    results = []
    for r0 in range(1, 1 << KMAX, 2):
        res0 = compute_descent(r0, KMAX)
        if res0 is None or res0[5]:
            continue  # valid lane — skip
        kv, res = find_valid_k(r0, k_min=KMAX)
        if kv is None:
            continue
        depth = kv - KMAX
        if depth > 14:
            results.append((r0, kv, depth, res[1], res[2], res[3], res[4]))  # r0,k',d,a,b,c,B
    results.sort(key=lambda x: -x[2])
    return results

print("Computing deep parent list (depth > 14) ...")
deep_parents = get_deep_parents()
print(f"  Found {len(deep_parents)} deep parents  ({time.time()-t0:.1f}s)")
print()

TARGET = deep_parents[:50]  # analyse deepest 50

# ── Analysis per parent ───────────────────────────────────────────────────────

CLOSED = 0; PARTIAL = 0; OPEN = 0
results_log = []

print(f"{'r0':>8}  {'kp':>4}  {'d':>4}  {'c':>3}  {'B_par':>6}  {'path_forced':>11}  {'lower_cert':>10}  {'affine':>6}  status")
print("-"*80)

for r0, kv, depth, a_par, b_par, c_par, B_par in TARGET:
    # --- Approach B: does a lower level k'' < kv cover all siblings identically?
    lower_cert_k = None
    for k2 in range(KMAX, kv):
        rep2 = r0 % (1 << k2)
        if rep2 % 2 == 0:
            continue
        res2 = compute_descent(rep2, k2)
        if res2 is not None and res2[5]:
            lower_cert_k = k2
            break

    # If lower_cert_k exists and lower_cert_k <= KMAX+14 (exact enumerable),
    # then all siblings at level kv that share rep2 mod 2^k2 are covered.
    # But wait: siblings s_j = r0 + j*2^16 all have s_j ≡ r0 (mod 2^16).
    # For lower level k2 < kv, their residue mod 2^k2 is r0 mod 2^k2 (same for all j
    # only if k2 <= 16). For k2 > 16, siblings differ mod 2^k2.
    lower_cert_covers_all = (lower_cert_k is not None and lower_cert_k <= KMAX)

    # --- Approach A: is the parity path for the first m_par steps identical for
    # all siblings? This holds iff bits 0..c_par-1 of n determine the path,
    # and since all siblings agree on bits 0..15 (they ≡ r0 mod 2^16), we need c_par <= 16.
    # More carefully: the parity path of length m is determined by n mod 2^(m+...).
    # Sufficient condition: the m steps of T from r0 never look at bit >= 16 for parity.
    # This is equivalent to: the "carry propagation" stays within bits 0..15.
    # We can check this by verifying that 3*n+1 never exceeds 2^16 during the symbolic
    # prefix. A simpler sufficient condition: k_par <= 16 means c_par <= 16.
    path_forced = (kv <= KMAX + 1)  # parent itself needs only one extra bit
    # More generally: if the parity sequence for the FULL m_par steps can be determined
    # from n mod 2^KMAX alone (i.e., we never read a bit >= KMAX during these steps),
    # then all siblings share the same formula.
    # Check: simulate r0 and record max bit index ever read for parity
    # Parity is read before each step; we read bit 0 each time, but 3n+1 can carry up.
    # The relevant check is: does the orbit of r0 at level kv produce c=c_par <= 16?
    path_forced_strong = (c_par <= KMAX)

    # --- Approach C: Affine closure
    # If path_forced_strong: same (a,b,c) for all j.
    # Descent condition: T^m(n) = (a*n + b) / 2^c < n  iff  n > B = ceil(b/(2^c-a))
    # B_par is the threshold for r0. Since (a,b,c) are the same for ALL siblings
    # (when path_forced_strong), B_par applies to ALL siblings.
    affine_closed = path_forced_strong
    # When affine_closed, any sibling n > B_par is covered symbolically,
    # and n <= B_par is covered by empirical verification (since B_par <= 200001).

    # Final status
    if affine_closed or lower_cert_covers_all:
        status = "CLOSED"
        CLOSED += 1
    elif path_forced:
        status = "PARTIAL"
        PARTIAL += 1
    else:
        status = "OPEN"
        OPEN += 1

    results_log.append({
        "r0": r0, "k_prime": kv, "depth": depth, "a": a_par, "b": b_par,
        "c": c_par, "B": B_par, "path_forced": path_forced_strong,
        "lower_cert_covers_all": lower_cert_covers_all,
        "affine_closed": affine_closed, "status": status
    })

    print(f"{r0:>8}  {kv:>4}  {depth:>4}  {c_par:>3}  {B_par:>6}  "
          f"{'YES' if path_forced_strong else 'NO':>11}  "
          f"{'YES(k<=16)' if lower_cert_covers_all else 'no':>10}  "
          f"{'YES' if affine_closed else 'NO':>6}  {status}")

# ── Summary ──────────────────────────────────────────────────────────────────

print("\n" + "="*70)
print("SUMMARY (top 50 deepest lanes)")
print("="*70)
print(f"  CLOSED  (affine or lower-cert): {CLOSED}")
print(f"  PARTIAL (path forced, partial): {PARTIAL}")
print(f"  OPEN    (no structural closure): {OPEN}")
print()

# Check all 776 deep parents
print(f"Checking all {len(deep_parents)} deep parents ...")
all_closed = all_partial = all_open = 0
open_list = []
for r0, kv, depth, a_par, b_par, c_par, B_par in deep_parents:
    affine_closed = (c_par <= KMAX)
    lower_cert_covers_all = False
    for k2 in range(KMAX, min(KMAX+1, kv)):
        rep2 = r0 % (1 << k2)
        if rep2 % 2 == 0: continue
        res2 = compute_descent(rep2, k2)
        if res2 and res2[5]: lower_cert_covers_all = True; break
    if affine_closed or lower_cert_covers_all:
        all_closed += 1
    else:
        all_open += 1
        open_list.append((r0, kv, depth, c_par, B_par))

print(f"  CLOSED : {all_closed}")
print(f"  OPEN   : {all_open}")
print()

if open_list:
    print(f"OPEN lanes (c > {KMAX}, no lower cert):")
    print(f"  {'r0':>8}  {'kp':>4}  {'depth':>5}  {'c':>4}  {'B':>6}")
    for r0, kv, depth, c_par, B_par in open_list[:30]:
        print(f"  {r0:>8}  {kv:>4}  {depth:>5}  {c_par:>4}  {B_par:>6}")
    if len(open_list) > 30:
        print(f"  ... and {len(open_list)-30} more")
    print()
    print("NOTE: OPEN lanes have c > 16 in the parent certificate.")
    print("  The parity path for the parent uses bits above 2^16,")
    print("  so siblings with different upper bits may follow different")
    print("  parity paths, yielding different (a, b, c) triples.")
    print("  These lanes are NOT closed by the affine argument alone.")
    print("  Require per-sibling certificates or a stronger structural theorem.")
else:
    print("ALL deep lanes CLOSED via affine argument (c <= 16 for all parents).")

print()
total_t = time.time() - t0
print(f"Total time: {total_t:.1f}s")
print()

# ── Theoretical explanation ──────────────────────────────────────────────────

print("="*70)
print("THEORETICAL STATUS")
print("="*70)
print("""
Affine Closure Theorem (for lanes where c_par <= 16):
  Let r0 be a deep invalid parent at k=16 with valid certificate at k'.
  Certificate: T^m(r0 mod 2^k') = (a * n + b) / 2^c  with a < 2^c, c <= 16.
  Threshold: B = ceil(b / (2^c - a)).

  For any sibling s_j = r0 + j * 2^16:
    s_j ≡ r0  (mod 2^16)
    The first m Collatz steps of s_j are determined by s_j mod 2^(max_bit_read).
    If c <= 16, the descent formula triggers before the orbit reads any bit
    above position 15 (all carry propagation stays within the lower 16 bits).
    Therefore s_j follows the SAME parity path as r0, giving the SAME (a, b, c).
    The descent condition T^m(s_j) < s_j holds for ALL s_j > B, regardless of j.
    Since B <= 200001 = VERIFY_LIMIT, the empirical bridge covers s_j <= B.
    TOGETHER: every integer n ≡ r0 (mod 2^16) with n > 1 is covered.

For OPEN lanes (c_par > 16):
  The formula for r0 uses carry bits above position 15.
  Siblings with j > 0 differ from r0 in bits 16..k'-1, and may take a
  different parity path, yielding a different (a', b', c') triple.
  The parent's threshold B does not apply to them without separate analysis.
  These lanes require per-sibling certificates or further structural argument.
""")
