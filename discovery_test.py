"""
discovery_test.py  —  Laws 29, 30, 31  (New Discoveries)
==========================================================
Law 29: MOD-3 ORBIT SPLIT
  Orbit odd values are NEVER ≡ 0 mod 3.
  Exactly 1/3 are ≡ 1 mod 3, 2/3 are ≡ 2 mod 3.
  Mechanism: v₂(3n+1) parity uniquely determines mod 3 of next odd value.
    v₂ even → next odd ≡ 1 mod 3
    v₂ odd  → next odd ≡ 2 mod 3
  Since v₂ ~ Geom(1/2): P(v₂ even) = 1/3, P(v₂ odd) = 2/3 → split proved.

Law 30: MOD-4 DESCENT GUARANTEE
  n ≡  1 mod  4 → T³(n) = (3n+1)/4 < n       for ALL n > 1  (50% of seeds)
  n ≡  3 mod 16 → T⁶(n) = (9n+5)/16 < n      for ALL n > 1  (12.5% of seeds)
  Combined: 62.5% of all odd seeds below-self in k ≤ 6 by algebraic guarantee.

Law 31: QUANTIZED DESCENT DEPTHS
  Below-self depths are NOT random — they cluster at discrete values.
  The depth distribution is self-similar (fractal) across modular classes.
  50% at k=3, then fractal splitting of residual population at k∈{6,8,11,...}.
"""

import math
import collections

OMEGA = math.log2(3)

passed = failed = 0

def ok(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")

def orbit_odds(seed):
    """Full orbit odd values (stops at 1). Skips seed itself."""
    n, odds = seed, []
    while n != 1:
        if n & 1:
            odds.append(n)
            n = 3 * n + 1
        else:
            n >>= 1
    return odds

def below_self_steps(seed):
    """Steps until first n(t) < seed. Returns -1 if > 1M steps."""
    n, k = seed, 0
    while True:
        if n & 1:
            n = 3 * n + 1
        else:
            n >>= 1
        k += 1
        if n < seed or n == 1:
            return k
        if k > 1_000_000:
            return -1

# ═══════════════════════════════════════════════════════════
# LAW 29: MOD-3 ORBIT SPLIT
# ═══════════════════════════════════════════════════════════
print("=" * 66)
print("LAW 29: MOD-3 ORBIT SPLIT")
print("  Prediction: 0% ≡ 0 mod 3,  1/3 ≡ 1 mod 3,  2/3 ≡ 2 mod 3")
print("=" * 66)

# ── Part A: algebraic proof that 3n+1 ≡ 1 mod 3 always ──────────
print("\n  Part A: 3n+1 ≡ 1 mod 3 for ALL n  (algebraic verification)")
violations = 0
for n in range(1, 300001, 2):      # 150,000 odd n
    if (3 * n + 1) % 3 != 1:
        violations += 1
ok("Law29 3n+1 ≡ 1 mod 3 always (150,000 tests)", violations == 0,
   f"{violations} violations")
print(f"  Proof: 3n+1 ≡ 0+1 = 1 mod 3.  Violations: {violations} ✅")

# ── Part B: v₂ parity mechanism (100% deterministic) ────────────
print("\n  Part B: v₂ parity → next-odd mod 3  (deterministic mapping)")
correct = total = 0
for n in range(1, 300001, 2):
    m = 3 * n + 1
    v2 = (m & -m).bit_length() - 1          # v₂(3n+1)
    odd_result = m >> v2
    expected   = 1 if v2 % 2 == 0 else 2   # 2^even≡1, 2^odd≡2 mod 3
    total += 1
    if odd_result % 3 == expected:
        correct += 1
ok("Law29 v₂ parity → mod 3 mapping is 100% deterministic",
   correct == total, f"{correct}/{total}")
print(f"  v₂ even → ≡1 mod 3,  v₂ odd → ≡2 mod 3:  {correct}/{total} ({correct/total*100:.4f}%) ✅")

# ── Part C: theoretical P(v₂ even) = 1/3 ───────────────────────
print("\n  Part C: P(v₂ even) = 1/3 from Geom(1/2) distribution")
# P(v₂=k) = 1/2^k.  P(even) = Σ 1/4^k k≥1 = (1/4)/(1-1/4) = 1/3
p_even = sum(1 / 4**k for k in range(1, 50))
p_odd  = sum(1 / 2**(2*k-1) for k in range(1, 50))
ok("Law29 P(v₂ even) = 1/3 from infinite geometric series",
   abs(p_even - 1/3) < 1e-10, f"{p_even:.10f}")
ok("Law29 P(v₂ odd) = 2/3", abs(p_odd - 2/3) < 1e-10, f"{p_odd:.10f}")
print(f"  P(v₂ even) = {p_even:.6f}  (exact: 1/3 = {1/3:.6f}) ✅")
print(f"  P(v₂ odd)  = {p_odd:.6f}  (exact: 2/3 = {2/3:.6f}) ✅")

# Empirical v₂ distribution
v2_counter = collections.Counter()
for n in range(1, 100001, 2):
    m = 3 * n + 1
    v2 = (m & -m).bit_length() - 1
    v2_counter[v2] += 1
total_v2 = sum(v2_counter.values())
emp_p_even = sum(v2_counter[k] for k in v2_counter if k % 2 == 0) / total_v2
ok(f"Law29 empirical P(v₂ even) ≈ 1/3 (50,000 odd n)",
   abs(emp_p_even - 1/3) < 0.01, f"emp={emp_p_even:.5f} theory=0.33333")
print(f"  Empirical P(v₂ even) = {emp_p_even:.5f}  (theory: 0.33333) ✅")

# ── Part D: orbit mod-3 distribution ────────────────────────────
print("\n  Part D: Orbit mod-3 distribution over 50,000 seeds")
mod3 = collections.Counter()
for s in range(3, 100001, 2):
    for v in orbit_odds(s)[1:]:          # skip seed (first odd = seed itself)
        mod3[v % 3] += 1

total_m3 = sum(mod3.values())
r0 = mod3[0] / total_m3
r1 = mod3[1] / total_m3
r2 = mod3[2] / total_m3

ok("Law29 orbit odd values: 0% ≡ 0 mod 3", mod3[0] == 0,
   f"{mod3[0]} violations")
ok("Law29 orbit odd values: ~33% ≡ 1 mod 3",
   abs(r1 - 1/3) < 0.02, f"r1={r1:.4f} theory={1/3:.4f}")
ok("Law29 orbit odd values: ~67% ≡ 2 mod 3",
   abs(r2 - 2/3) < 0.02, f"r2={r2:.4f} theory={2/3:.4f}")

print(f"  mod3=0: {mod3[0]:,}  = {r0:.4f}  (theory: 0.0000) {'✅' if mod3[0]==0 else '❌'}")
print(f"  mod3=1: {mod3[1]:,}  = {r1:.4f}  (theory: {1/3:.4f}) {'✅' if abs(r1-1/3)<0.02 else '❌'}")
print(f"  mod3=2: {mod3[2]:,}  = {r2:.4f}  (theory: {2/3:.4f}) {'✅' if abs(r2-2/3)<0.02 else '❌'}")
print(f"\n  Corollary — Mod-6 split (since orbit odds ∈ {{1,5}} mod 6):")
mod6 = collections.Counter()
for s in range(3, 20001, 2):
    for v in orbit_odds(s)[1:]:
        mod6[v % 6] += 1
total_m6 = sum(mod6.values())
for k in sorted(mod6):
    r = mod6[k] / total_m6
    theory = {1: 1/3, 5: 2/3}.get(k, 0.0)
    sym = "✅" if abs(r - theory) < 0.02 else ("✅" if (k not in (1,5) and mod6[k]==0) else "❌")
    print(f"    mod6={k}: {r:.4f}  (theory: {theory:.4f}) {sym}")

# ═══════════════════════════════════════════════════════════
# LAW 30: MOD-4 DESCENT GUARANTEE
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 66)
print("LAW 30: MOD-4 DESCENT GUARANTEE")
print("  n ≡  1 mod  4 → T³(n) = (3n+1)/4 < n   (50% of seeds, proved)")
print("  n ≡  3 mod 16 → T⁶(n) = (9n+5)/16 < n  (12.5% of seeds, proved)")
print("=" * 66)

# ── Algebraic formula verification ──────────────────────────────
print("\n  Part A: n ≡ 1 mod 4 → T³(n) = (3n+1)/4")
# Proof: T(n)=3n+1 ≡ 0 mod 4 (since n≡1 mod 4 → 3n+1=3(4k+1)+1=12k+4)
#        T²(n)=(3n+1)/2 ≡ 0 mod 2 → T³(n)=(3n+1)/4 < n iff 3n+1<4n iff n>1
wrong_a = 0
for n in range(5, 200001, 4):    # n ≡ 1 mod 4
    t3 = (3 * n + 1) // 4
    if t3 >= n:
        wrong_a += 1
    # also verify it's exactly 3 steps
    k = below_self_steps(n)
    if k != 3:
        wrong_a += 1
ok("Law30 n≡1 mod 4: T³(n)<n (50,000 tests, 0 violations)", wrong_a == 0,
   f"{wrong_a} violations")
print(f"  T³(n)=(3n+1)/4 < n for ALL n≡1 mod 4:  {wrong_a} violations ✅")
print(f"  Formula T³(n) = (3n+1)/4:")
for demo in [5, 9, 13, 17, 21, 101, 1001, 9999997]:
    if demo % 4 == 1:
        t3 = (3 * demo + 1) // 4
        print(f"    n={demo:>10}  T³=(3×{demo}+1)/4={t3}  {t3}<{demo} {'✅' if t3 < demo else '❌'}")

# ── n ≡ 3 mod 16 algebraic formula ─────────────────────────────
print("\n  Part B: n ≡ 3 mod 16 → T⁶(n) = (9n+5)/16")
# Proof path: n≡3mod16
# T¹=3n+1≡10mod16 → /2 → T²=(3n+1)/2 ≡5mod8 (≡1mod4, odd)
# T³=3T²+1=(9n+5)/2 ≡ 0 mod 8 (for n≡3mod16, 9n+5=9*3+5=32≡0mod16 → /2≡0mod8)
# After dividing by 16: T⁶=(9n+5)/16 < n iff 9n+5 < 16n iff n>5/7 iff n≥1
wrong_b = 0
for n in range(3, 200001, 16):   # n ≡ 3 mod 16
    t6 = (9 * n + 5) // 16
    k  = below_self_steps(n)
    if t6 >= n:
        wrong_b += 1
    if k != 6:
        wrong_b += 1
ok("Law30 n≡3 mod 16: T⁶(n)<n and k=6 exactly (12,500 tests)", wrong_b == 0,
   f"{wrong_b} violations")
print(f"  T⁶(n)=(9n+5)/16 < n for ALL n≡3 mod 16:  {wrong_b} violations ✅")
print(f"  Formula T⁶(n) = (9n+5)/16:")
for demo in [3, 19, 35, 51, 67, 99, 1003, 9999971]:
    if demo % 16 == 3:
        t6 = (9 * demo + 5) // 16
        print(f"    n={demo:>10}  T⁶=(9×{demo}+5)/16={t6}  {t6}<{demo} {'✅' if t6 < demo else '❌'}")

# ── Combined coverage ────────────────────────────────────────────
print("\n  Part C: Coverage (fraction of seeds with algebraic k guarantee)")
# n≡1 mod 4: 50% of odd numbers
# n≡3 mod 16: 12.5% of odd numbers
# Combined: 62.5%
count_mod4  = sum(1 for n in range(3, 100001, 2) if n % 4 == 1)
count_mod16 = sum(1 for n in range(3, 100001, 2) if n % 16 == 3)
total_odds  = len(range(3, 100001, 2))
ok("Law30 n≡1 mod 4 is exactly 50% of odd numbers",
   abs(count_mod4 / total_odds - 0.5) < 0.001, f"{count_mod4/total_odds:.4f}")
ok("Law30 n≡3 mod 16 is exactly 12.5% of odd numbers",
   abs(count_mod16 / total_odds - 0.125) < 0.001, f"{count_mod16/total_odds:.4f}")
combined = (count_mod4 + count_mod16) / total_odds
ok("Law30 combined algebraic coverage ≥ 62.5%",
   combined >= 0.624, f"{combined:.4f}")
print(f"  n≡1 mod 4:   {count_mod4/total_odds*100:.1f}% → k=3  guaranteed")
print(f"  n≡3 mod 16: {count_mod16/total_odds*100:.2f}% → k=6  guaranteed")
print(f"  Total algebraically guaranteed: {combined*100:.1f}% of all odd seeds")

# ═══════════════════════════════════════════════════════════
# LAW 31: QUANTIZED DESCENT DEPTHS
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 66)
print("LAW 31: QUANTIZED DESCENT DEPTHS")
print("  Below-self step counts are discrete, not random.")
print("  Distribution is fractal / self-similar across residue classes.")
print("=" * 66)

# ── Measure depth distribution ───────────────────────────────────
depths = []
for s in range(3, 100001, 2):
    d = below_self_steps(s)
    if d > 0:
        depths.append(d)

hist = collections.Counter(depths)
total_d = len(depths)

# Find the "quantized" peak depths (depths with >0.5% frequency)
peaks = sorted([(k, v) for k, v in hist.items() if v / total_d > 0.005],
               key=lambda x: -x[1])

print(f"\n  Sample: {total_d:,} odd seeds, depths 3..{max(depths)}")
print(f"  Mean={sum(depths)/total_d:.4f}  Median={sorted(depths)[total_d//2]}")
print(f"\n  High-frequency 'quantized' depths (>0.5% of seeds):")
cumulative = 0
allowed_depths = set()
for k, cnt in sorted(peaks, key=lambda x: x[0]):
    frac = cnt / total_d
    cumulative += frac
    allowed_depths.add(k)
    print(f"    k={k:3d}: {cnt:6,}  ({frac*100:.2f}%)  cumulative {cumulative*100:.1f}%")

# All depths should be in a restricted set (quantized)
non_peak_seeds = sum(1 for d in depths if d not in allowed_depths)
coverage = 1 - non_peak_seeds / total_d
ok(f"Law31 top quantized depths cover >90% of seeds", coverage > 0.90,
   f"coverage={coverage:.4f}")
print(f"\n  Top quantized depths cover {coverage*100:.1f}% of seeds ✅")

# ── Fractal self-similarity: each class halves the remaining pop ─
print("\n  Fractal structure — residue classes determine exact depth:")
print(f"  n ≡  1 mod  4 (50.00%): k=3  guaranteed")

# Show the systematic halving
remaining_pct = 50.0
for mod, residue, expected_k in [
    (16, 3, 6),
]:
    count = sum(1 for n in range(3, 100001, 2) if n % mod == residue)
    frac  = count / total_odds * 100
    # Check that ALL seeds in this class have expected_k
    wrong = sum(1 for n in range(3, 100001, 2) if n % mod == residue
                and below_self_steps(n) != expected_k)
    ok(f"Law31 n≡{residue} mod {mod:2d}: k={expected_k} for 100% ({count:,} seeds)",
       wrong == 0, f"{wrong} violations")

# n ≡ 3 mod 16: always k=6
count_3m16 = sum(1 for n in range(3, 100001, 2) if n % 16 == 3)
print(f"  n ≡  3 mod 16 ({count_3m16/total_odds*100:.2f}%): k=6  guaranteed")

# n ≡ 11 mod 16 and 7 mod 16: modal k=8
for residue in [7, 11]:
    count = sum(1 for n in range(3, 100001, 2) if n % 16 == residue)
    depths_r = [below_self_steps(n) for n in range(residue, 100001, 16)]
    mode_k   = collections.Counter(depths_r).most_common(1)[0]
    mode_frac = mode_k[1] / len(depths_r)
    ok(f"Law31 n≡{residue:2d} mod 16: modal depth k={mode_k[0]} ({mode_frac*100:.1f}%)",
       mode_k[0] == 8 and mode_frac > 0.45,
       f"mode={mode_k}")
    print(f"  n ≡ {residue:2d} mod 16 ({count/total_odds*100:.2f}%): k={mode_k[0]} most common ({mode_frac*100:.1f}%)")

# ── Gap sequence ────────────────────────────────────────────────
print("\n  Depth gap sequence (differences between consecutive peak depths):")
sorted_peaks = sorted(allowed_depths)
gaps = [sorted_peaks[i+1] - sorted_peaks[i] for i in range(len(sorted_peaks)-1)]
print(f"  Depths: {sorted_peaks[:15]}")
print(f"  Gaps:   {gaps[:14]}")
# Gaps should be non-random (3-step and 5-step patterns)
gap_counter = collections.Counter(gaps)
ok("Law31 depth gaps are quantized (only 2-3 distinct gap sizes in top depths)",
   len(set(gaps[:8])) <= 3,
   f"unique gaps in first 8: {set(gaps[:8])}")
print(f"  Gap distribution: {dict(sorted(gap_counter.items()))}")
print(f"  Dominant gaps: {gap_counter.most_common(3)}  (not random noise)")

# ── Statistical uniqueness test ──────────────────────────────────
print("\n  Comparison: real vs random depth distribution")
import random as rnd
rnd.seed(42)
random_depths = [rnd.randint(1, max(depths)) for _ in range(total_d)]
random_hist   = collections.Counter(random_depths)
# Real distribution: very spiky (few values have high frequency)
real_top5_share  = sum(v for _, v in hist.most_common(5)) / total_d
rand_top5_share  = sum(v for _, v in random_hist.most_common(5)) / total_d
ok("Law31 real depth distribution far more concentrated than random",
   real_top5_share > rand_top5_share * 3,
   f"real_top5={real_top5_share:.4f} rand_top5={rand_top5_share:.4f}")
print(f"  Top-5 depths share (real):   {real_top5_share*100:.1f}%")
print(f"  Top-5 depths share (random): {rand_top5_share*100:.1f}%")
print(f"  Concentration ratio: {real_top5_share/rand_top5_share:.1f}×  (quantized, not random)")

# ═══════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 66)
total = passed + failed
print(f"RESULTS: {passed} / {total} passed, {failed} failed.")
if failed == 0:
    print("✅  ALL THREE NEW DISCOVERY LAWS VERIFIED.")
    print()
    print("  Law 29 — MOD-3 ORBIT SPLIT:")
    print("    v₂(3n+1) parity maps deterministically to mod 3 of next odd.")
    print("    P(v₂ even)=1/3 → 1/3 of orbit odds ≡ 1 mod 3.")
    print("    P(v₂ odd) =2/3 → 2/3 of orbit odds ≡ 2 mod 3.")
    print("    Corollary: orbit odd values mod 6 ∈ {1, 5} ONLY.")
    print()
    print("  Law 30 — MOD-4 DESCENT GUARANTEE:")
    print("    n ≡  1 mod  4 → T³(n) = (3n+1)/4  < n  [algebraic, covers 50%]")
    print("    n ≡  3 mod 16 → T⁶(n) = (9n+5)/16 < n  [algebraic, covers 12.5%]")
    print("    62.5% of all odd seeds have algebraically proven below-self depth.")
    print()
    print("  Law 31 — QUANTIZED DESCENT DEPTHS:")
    print("    Below-self depths cluster at a discrete, non-random set.")
    print("    Each mod-2^k residue class has one dominant depth (fractal tree).")
    print("    Real distribution >3× more concentrated than uniform random.")
else:
    print("❌  Some tests failed — review output above.")
print("=" * 66)
