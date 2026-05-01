"""
deep_lane_unsampled_probe.py  —  Adversarial Sibling Hunter
============================================================
For each deep invalid parent lane r0 (depth > 14), probes adversarially
chosen sibling indices j rather than random samples.

The goal is to find a sibling that either:
  (a) has no valid k up to MAX_K  →  concrete gap in certificate
  (b) requires a much higher k than the parent  →  stress test
  (c) has B >= sibling value  →  threshold not useful for that sibling

Adversarial j values probed for each parent (depth d, 2^d siblings):
  - j = 0                    (the parent itself)
  - j = 1                    (smallest non-zero j)
  - j = 2                    
  - j = 2^d - 1              (last sibling)
  - j = 2^d - 2
  - j = 2^(d-1)              (midpoint)
  - j = 2^(d-1) - 1         (just before midpoint)
  - j = (2^d)//3             (1/3 point)
  - j = (2*2^d)//3           (2/3 point)
  - j with all lower bits=1  (j = 2^min(d,30)-1)
  - j with alternating bits  (j = 0b10101010... up to d bits)
  - j with single high bit   (j = 2^(d-1))  (already above)
  - j maximizing trailing ones in s = r0 + j*2^16
  - j maximizing popcount of s mod 2^k'

For each probed sibling:
  - Run find_valid_k(s, k_min=16, max_k=MAX_K_PROBE)
  - Report: closed yes/no, k', B, m, B<s?

Output:
  One row per (parent, j) probe.
  Summary: any failure found or all closed.

This is adversarial evidence, not a proof.
A proof requires the symbolic argument in deep_lane_symbolic.py.
"""

import time, sys

KMAX = 16
MAX_STEPS = 10_000
MAX_K_PROBE = 500  # raise to 1000 for harder search
VERIFY_LIMIT = 200_001
TOP_N = 30  # probe deepest N parents

t0 = time.time()

# ── Core functions ───────────────────────────────────────────────────────────

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

def find_valid_k(r, k_min=KMAX, max_k=MAX_K_PROBE):
    for k in range(k_min, max_k + 1):
        rep = r % (1 << k)
        if rep % 2 == 0:
            continue
        res = compute_descent(rep, k)
        if res is not None and res[5]:
            return k, res
    return None, None

# ── Build deep parent list ───────────────────────────────────────────────────

print("="*72)
print("DEEP LANE ADVERSARIAL SIBLING PROBE")
print("="*72)
print(f"MAX_K_PROBE={MAX_K_PROBE}  TOP_N={TOP_N}\n")

def get_deep_parents():
    results = []
    for r0 in range(1, 1 << KMAX, 2):
        res0 = compute_descent(r0, KMAX)
        if res0 is None or res0[5]:
            continue
        kv, res = find_valid_k(r0, k_min=KMAX)
        if kv is None:
            continue
        depth = kv - KMAX
        if depth > 14:
            results.append((r0, kv, depth, res[4]))
    results.sort(key=lambda x: -x[2])
    return results

print("Building deep parent list ...")
deep_parents = get_deep_parents()
print(f"  {len(deep_parents)} deep parents found  ({time.time()-t0:.1f}s)\n")

TARGET = deep_parents[:TOP_N]

# ── Adversarial j selector ───────────────────────────────────────────────────

def adversarial_js(d):
    """Return adversarial j values for depth d (2^d siblings)."""
    two_d = 1 << d
    js = set()
    # boundary
    js.update([0, 1, 2, max(0, two_d-1), max(0, two_d-2)])
    # midpoints
    js.update([two_d//2, max(0, two_d//2 - 1), two_d//3, 2*two_d//3])
    # all-ones lower bits (up to 30 to stay manageable)
    js.add((1 << min(d, 30)) - 1)
    # alternating bits up to d
    alt = 0
    for i in range(0, min(d, 60), 2):
        alt |= (1 << i)
    js.add(alt % two_d)
    alt2 = 0
    for i in range(1, min(d, 60), 2):
        alt2 |= (1 << i)
    js.add(alt2 % two_d)
    # sparse single bits
    for bit in range(min(d, 20)):
        js.add(1 << bit)
    # quarter/eighth points
    js.update([two_d//4, 3*two_d//4, two_d//8, 7*two_d//8])
    return sorted(js)

# ── Probe ────────────────────────────────────────────────────────────────────

total_probes = 0
total_failures = 0
total_high_k = 0
hard_failures = []

print(f"{'r0':>8}  {'kp':>4}  {'d':>4}  j_label                 "
      f"  {'k_found':>7}  {'B':>8}  {'B<s':>5}  result")
print("-"*80)

for r0, kv, depth, B_par in TARGET:
    js = adversarial_js(depth)
    parent_failures = 0

    for j in js:
        s = r0 + j * (1 << KMAX)
        total_probes += 1

        kf, res = find_valid_k(s, k_min=KMAX, max_k=MAX_K_PROBE)

        if kf is None:
            total_failures += 1
            parent_failures += 1
            hard_failures.append({"r0": r0, "k_prime": kv, "depth": depth, "j": j, "s": s})
            j_lbl = f"j={j}"[:22]
            print(f"{r0:>8}  {kv:>4}  {depth:>4}  {j_lbl:<24}  {'NONE':>7}  {'?':>8}  {'?':>5}  *** NO VALID K ***")
            sys.stdout.flush()
            continue

        m_f, a_f, b_f, c_f, B_f, _ = res
        B_below_s = (B_f < s)
        if not B_below_s and s > VERIFY_LIMIT:
            total_high_k += 1

        if kf > kv + 50:
            total_high_k += 1

        # Only print failures and notable high-k
        if not B_below_s or kf > kv + 30:
            j_lbl = f"j={j}"[:22]
            note = "B>=s" if not B_below_s else f"k_jump+{kf-kv}"
            print(f"{r0:>8}  {kv:>4}  {depth:>4}  {j_lbl:<24}  {kf:>7}  {B_f:>8}  {'YES' if B_below_s else 'NO':>5}  {note}")
            sys.stdout.flush()

    if parent_failures == 0:
        # Brief per-parent summary (pass line)
        js_count = len(js)
        print(f"{r0:>8}  {kv:>4}  {depth:>4}  [{js_count} adv siblings]         "
              f"  {'all':>7}  {'':>8}  {'':>5}  PASS ({js_count} probes)")
        sys.stdout.flush()

# ── Summary ──────────────────────────────────────────────────────────────────

elapsed = time.time() - t0
print("\n" + "="*72)
print("ADVERSARIAL PROBE SUMMARY")
print("="*72)
print(f"  Parents probed  : {len(TARGET)}")
print(f"  Total probes    : {total_probes}")
print(f"  Hard failures   : {total_failures}  (no valid k up to {MAX_K_PROBE})")
print(f"  High-k notable  : {total_high_k}")
print(f"  Time            : {elapsed:.1f}s")
print()

if hard_failures:
    print("HARD FAILURE DETAILS:")
    for f in hard_failures:
        print(f"  r0={f['r0']}  k'={f['k_prime']}  depth={f['depth']}  j={f['j']}  s={f['s']}")
    print()
    print("STATUS: COUNTEREXAMPLE CANDIDATES FOUND — review above.")
else:
    print("No hard failures in adversarial probes.")
    print()
    print("NOTE: This is adversarial evidence, not a proof.")
    print("  The adversarial j values were chosen to stress-test boundary and")
    print("  structured siblings. Passing does not certify all 2^depth siblings.")
    print("  See deep_lane_symbolic.py for the structural closure argument.")
    print()
    print("STATUS: NO COUNTEREXAMPLES FOUND in adversarial probe of top",
          len(TARGET), "deepest lanes.")
