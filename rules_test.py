"""
rules_test.py  —  Collatz 20-Law Rule Verification Suite
=========================================================
Tests all 20 discovered laws against specific examples.
Each test prints PASS or FAIL with evidence.

Laws tested:
  1.  EVEN DROP LAW
  2.  ODD DANGER LAW
  3.  POWER DROP LAW
  4.  PARITY-INJECTION LAW
  5.  SATURATION RIDGE LAW
  6.  SIZE IS NOT DANGER LAW
  7.  MONSTER DELAY SIGNATURE
  8.  Ω SPEED LIMIT LAW
  9.  BELOW-SELF INDUCTION LAW
  10. PROOF TARGET (descent check)
  11. EVEN SHELL LAW
  12. ANCHOR / COLLECTOR LAW
  13. MERGE LAW
  14. DOUBLE CAPTURE LAW
  15. ODD CORE LAW
  16. AMP LAW
  17. DELAY DENSITY LAW
  18. NORMALIZED DELAY LAW
  19. PEAK RESIDUE LAW
  20. ODD ISOLATION LAW
"""

import math, sys

OMEGA = math.log2(3)   # ≈ 1.58496

ANCHORS = {1, 2, 4, 8, 16, 40, 80, 184, 3077, 9232, 6909950,
           459624658, 171640888, 112627739}

# ─────────────────────────────────────────────
# CORE COLLATZ TRACER
# ─────────────────────────────────────────────

def trace(seed, max_steps=2_000_000):
    """Full trace returning all statistics."""
    n = seed
    steps = 0
    odd_steps = even_steps = 0
    peak = seed
    peak_step = 0
    max_odd_run = max_even_run = 0
    odd_run = even_run = 0
    door = "UNKNOWN"

    while n != 1 and steps < max_steps:
        if n in ANCHORS and steps > 0:
            door = "ANCHOR/COLLECTOR"
            break
        if steps > 0 and n < seed:
            door = "BELOW-SELF"
            break

        if n > peak:
            peak = n
            peak_step = steps

        if n % 2 == 0:
            n >>= 1
            even_steps += 1
            even_run += 1
            if odd_run > max_odd_run:
                max_odd_run = odd_run
            odd_run = 0
        else:
            n = 3 * n + 1
            odd_steps += 1
            odd_run += 1
            if even_run > max_even_run:
                max_even_run = even_run
            even_run = 0
        steps += 1

    if door == "UNKNOWN":
        if n == 1 or n in ANCHORS:
            door = "ANCHOR/COLLECTOR"
        elif n < seed:
            door = "BELOW-SELF"

    if even_run > max_even_run:
        max_even_run = even_run
    if odd_run > max_odd_run:
        max_odd_run = odd_run

    omega_ratio = even_steps / odd_steps if odd_steps > 0 else float('inf')
    amp = peak / seed if seed > 0 else 1
    digit_count = len(str(seed))
    log2n = math.log2(seed) if seed > 1 else 1
    peak_mod6  = peak % 6
    peak_mod12 = peak % 12
    delay_density  = steps / digit_count
    normalized_delay = steps / log2n

    return {
        'seed': seed, 'final': n, 'steps': steps,
        'odd': odd_steps, 'even': even_steps,
        'door': door,
        'peak': peak, 'peak_step': peak_step,
        'peak_mod6': peak_mod6, 'peak_mod12': peak_mod12,
        'max_odd_run': max_odd_run, 'max_even_run': max_even_run,
        'omega_ratio': omega_ratio,
        'amp': amp,
        'delay_density': delay_density,
        'normalized_delay': normalized_delay,
        'digit_count': digit_count,
    }

def odd_core(n):
    """Return (core, shell_depth) where n = 2^shells * core, core odd."""
    shells = 0
    while n % 2 == 0:
        n >>= 1
        shells += 1
    return n, shells

# ─────────────────────────────────────────────
# TEST HARNESS
# ─────────────────────────────────────────────

passed = failed = 0

def check(name, condition, evidence=""):
    global passed, failed
    sym = "✅ PASS" if condition else "❌ FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
    print(f"  {sym}  {name}")
    if evidence:
        print(f"         {evidence}")
    if not condition:
        print(f"         ^^^ FAILED ^^^")

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

# ─────────────────────────────────────────────
print("=" * 60)
print("  COLLATZ 20-LAW RULE VERIFICATION SUITE")
print("=" * 60)

# ─────────────────────────────────────────────
section("LAW 1 — EVEN DROP LAW")
# Even numbers immediately go below themselves
for n in [62, 126, 254, 510, 1024, 131072]:
    nxt = n // 2
    check(f"{n} → {nxt} (below self in 1 step)", nxt < n,
          f"n={n}, n/2={nxt}")

# ─────────────────────────────────────────────
section("LAW 2 — ODD DANGER LAW")
# Odd seeds near powers-of-2 are dramatically slower than even neighbors
triples = [(131071, 131072, 131073),
           (262143, 262144, 262145),
           (9007199254740991, 9007199254740992, 9007199254740993)]
for lo, mid, hi in triples:
    r_lo  = trace(lo)
    r_mid = trace(mid)
    r_hi  = trace(hi)
    check(f"2^k-1={lo} steps > 2^k+1={hi} steps",
          r_lo['steps'] > r_hi['steps'],
          f"steps: {lo}→{r_lo['steps']}, {mid}→{r_mid['steps']}, {hi}→{r_hi['steps']}")
    check(f"2^k={mid} steps is minimal (even shell)",
          r_mid['steps'] <= r_hi['steps'],
          f"2^k steps={r_mid['steps']}")

# ─────────────────────────────────────────────
section("LAW 3 — POWER DROP LAW")
for k in [10, 17, 23, 30, 53]:
    n = 2**k
    r = trace(n)
    check(f"2^{k} captured in 1 step", r['steps'] == 1,
          f"2^{k}={n}, steps={r['steps']}, door={r['door']}")

# ─────────────────────────────────────────────
section("LAW 4 — PARITY-INJECTION LAW")
for k in [17, 18, 19, 20, 53]:
    n = 2**k + 1
    r = trace(n)
    check(f"2^{k}+1 captured fast (≤ 5 steps)", r['steps'] <= 5,
          f"n={n}, steps={r['steps']}, door={r['door']}")

# ─────────────────────────────────────────────
section("LAW 5 — SATURATION RIDGE LAW")
known = [
    (255,      21),
    (2047,     94),
    (131071,   163),
    (8388607,  223),
    (8796093022207, 331),
    (9007199254740991, 344),
]
for n, expected_steps in known:
    r = trace(n)
    check(f"2^k-1={n} steps == {expected_steps}",
          r['steps'] == expected_steps,
          f"actual steps={r['steps']}")
# Saturation always has high step counts vs neighbors
for k in [8, 11, 17, 23]:
    sat  = trace(2**k - 1)
    inj  = trace(2**k + 1)
    check(f"2^{k}-1 steps ({sat['steps']}) > 2^{k}+1 steps ({inj['steps']})",
          sat['steps'] > inj['steps'])

# ─────────────────────────────────────────────
section("LAW 6 — SIZE IS NOT DANGER LAW")
fast_giants = [
    (75387266222633775, 16),
    (131072, 1),
    (9007199254740992, 1),
]
for n, max_s in fast_giants:
    r = trace(n)
    check(f"{n} (large) captured fast ≤ {max_s} steps",
          r['steps'] <= max_s,
          f"steps={r['steps']}, door={r['door']}")

# ─────────────────────────────────────────────
section("LAW 7 — MONSTER DELAY SIGNATURE")
monsters = [9007199254740991, 8796093022207, 63728127, 8400511]
for n in monsters:
    r = trace(n)
    is_monster = (r['steps'] >= 100 and
                  r['odd'] > 0 and
                  r['max_odd_run'] <= 1 and
                  r['amp'] >= 100)
    check(f"{n} has monster signature",
          is_monster,
          f"steps={r['steps']}, amp={r['amp']:.1f}x, maxOddRun={r['max_odd_run']}, ωphase from ratio={r['omega_ratio']:.4f}")

# ─────────────────────────────────────────────
section("LAW 8 — Ω SPEED LIMIT LAW")
# Fast decay seeds should have omega_ratio >> OMEGA
for n in [62, 126, 254]:
    r = trace(n)
    check(f"{n} (fast decay) ωRatio > Ω",
          r['omega_ratio'] > OMEGA or r['odd'] == 0,
          f"ωRatio={r['omega_ratio']:.4f}, Ω={OMEGA:.5f}")
# Monster delays hover near Ω
for n in [9007199254740991, 63728127]:
    r = trace(n)
    check(f"{n} (monster) ωRatio near Ω (within 0.5)",
          abs(r['omega_ratio'] - OMEGA) < 0.5,
          f"ωRatio={r['omega_ratio']:.5f}, gap={r['omega_ratio']-OMEGA:.5f}")

# ─────────────────────────────────────────────
section("LAW 9 — BELOW-SELF INDUCTION LAW")
for n in [131071, 27, 9007199254740991, 63728127]:
    r = trace(n)
    check(f"{n} door is BELOW-SELF or ANCHOR",
          r['door'] in ("BELOW-SELF", "ANCHOR/COLLECTOR"),
          f"door={r['door']}, steps={r['steps']}")

# ─────────────────────────────────────────────
section("LAW 10 — PROOF TARGET (sample odd descent)")
fail_count = 0
tested = 0
for n in range(3, 100_001, 2):
    r = trace(n)
    if r['door'] not in ("BELOW-SELF", "ANCHOR/COLLECTOR"):
        fail_count += 1
    tested += 1
check(f"All {tested:,} odd n in [3..100001] reach below-self or anchor",
      fail_count == 0,
      f"violations={fail_count}")

# ─────────────────────────────────────────────
section("LAW 11 — EVEN SHELL LAW")
shell_tests = [(62, 31), (126, 63), (254, 127), (510, 255),
               (1024, 512), (131072, 65536)]
for n, core_expected in shell_tests:
    core, shells = odd_core(n)
    # Even shell: first step goes to n/2
    nxt = n // 2
    check(f"{n} → {nxt} (1 even drop, shell depth {shells})",
          nxt == core_expected,
          f"odd_core({n})={core}, shells={shells}")
# Shells share odd core
for n in [31, 62, 124, 248, 496]:
    core, shells = odd_core(n)
    check(f"{n} odd core = 31", core == 31,
          f"core={core}, shells={shells}")

# ─────────────────────────────────────────────
section("LAW 12 — ANCHOR / COLLECTOR LAW")
# Known anchors that paths converge to
anchor_seeds = [(27, 3077), (31, 3077), (63, 3077), (7, 40)]
for seed, expected_anchor in anchor_seeds:
    # Trace manually looking for the anchor
    n = seed
    found_anchor = None
    for _ in range(10000):
        if n in ANCHORS:
            found_anchor = n
            break
        n = n // 2 if n % 2 == 0 else 3 * n + 1
    check(f"{seed} path hits anchor {expected_anchor}",
          found_anchor == expected_anchor,
          f"anchor_hit={found_anchor}")

# ─────────────────────────────────────────────
section("LAW 13 — MERGE LAW")
# If two paths share a value, they share the tail
def path_set(n, steps=500):
    seen = set()
    for _ in range(steps):
        seen.add(n)
        if n == 1: break
        n = n // 2 if n % 2 == 0 else 3 * n + 1
    return seen

# Seeds that are known to merge: 27 and 31 both hit 9232
s27 = path_set(27, 2000)
s31 = path_set(31, 2000)
merge_point = s27 & s31 - {1}
check("Path(27) and Path(31) share common values (Merge Law)",
      len(merge_point) > 0,
      f"shared values count={len(merge_point)}, sample={list(merge_point)[:3]}")

# ─────────────────────────────────────────────
section("LAW 14 — DOUBLE CAPTURE LAW")
# If n captured, 2n, 4n, 8n captured with 1,2,3 extra steps
# 2^j * n → captured in exactly 1 step always:
# 2^j*n → 2^(j-1)*n which is < 2^j*n → BELOW-SELF in step 1.
# The double-capture law means: if n is captured, ALL its shells are trivially captured.
for base in [31, 27, 63, 9007199254740991]:
    for j in (1, 2, 3, 4, 5):
        shell = base * (2 ** j)
        r_shell = trace(shell)
        check(f"2^{j}×{base} = {shell} captured in 1 step (even shell BELOW-SELF)",
              r_shell['steps'] == 1 and r_shell['door'] in ('BELOW-SELF','ANCHOR/COLLECTOR'),
              f"steps={r_shell['steps']}, door={r_shell['door']}")

# ─────────────────────────────────────────────
section("LAW 15 — ODD CORE LAW")
# Every number reduces to a unique odd core
tests = [(128, 1, 7), (96, 3, 5), (255, 255, 0), (256, 1, 8), (384, 3, 7)]
for n, expected_core, expected_shells in tests:
    core, shells = odd_core(n)
    check(f"oddCore({n}) = {expected_core}, shells={expected_shells}",
          core == expected_core and shells == expected_shells,
          f"got core={core}, shells={shells}")

# ─────────────────────────────────────────────
section("LAW 16 — AMP LAW")
known_amps = [
    (27, 269, 50),          # 27 → amp ≈ 269
    (8388607, 22445, 1000), # 8^M-1 → large amp
]
for n, expected_min, tolerance in known_amps:
    r = trace(n)
    check(f"{n} amp >= {expected_min} (explosion before capture)",
          r['amp'] >= expected_min,
          f"actual amp={r['amp']:.1f}x")
# Big but fast = low amp
r = trace(75387266222633775)
check("75387266222633775 amp < 100 (big but flat)",
      r['amp'] < 100,
      f"amp={r['amp']:.4f}x")

# ─────────────────────────────────────────────
section("LAW 17 — DELAY DENSITY LAW")
# delay density = steps / digit_count
champions = [(63728127, 50), (837799, 25), (9780657631, 20)]
for n, min_density in champions:
    r = trace(n)
    check(f"{n} delay density >= {min_density}",
          r['delay_density'] >= min_density,
          f"density={r['delay_density']:.2f} ({r['steps']} steps / {r['digit_count']} digits)")

# ─────────────────────────────────────────────
section("LAW 18 — NORMALIZED DELAY LAW")
# normalized delay = steps / log2(n)
# 9007199254740991 = 2^53-1 → 344 steps, log2 ≈ 53 → norm ≈ 6.49
n = 9007199254740991
r = trace(n)
norm = r['normalized_delay']
check(f"2^53-1 normalized delay ≈ 6.49",
      abs(norm - 6.49) < 0.5,
      f"norm={norm:.4f}")
# Fast n = low normalized delay
n2 = 131072
r2 = trace(n2)
check(f"131072 (2^17) normalized delay < 0.1",
      r2['normalized_delay'] < 0.1,
      f"norm={r2['normalized_delay']:.4f}")

# ─────────────────────────────────────────────
section("LAW 19 — PEAK RESIDUE LAW  (peakMod12 ∈ {4, 10})")
# NOTE: The invariant holds over the GLOBAL peak (full path to 1),
# not the local peak-before-below-self.
def global_peak_mod12(n):
    """Track peak over full path to 1."""
    x = n; peak = n
    for _ in range(5_000_000):
        if x == 1: break
        x = x >> 1 if x % 2 == 0 else 3 * x + 1
        if x > peak: peak = x
    return int(peak % 12)

violation_count = 0
sample_count = 0
for n in range(3, 20_001, 2):
    pm = global_peak_mod12(n)
    sample_count += 1
    if pm not in (4, 10):
        violation_count += 1
check(f"global peakMod12 ∈ {{4,10}} for all {sample_count:,} odd seeds [3..20001]",
      violation_count == 0,
      f"violations={violation_count}")

# Spot-check known values
known_peaks = [(131071, 4), (9007199254740991, 4), (27, 4)]
for n, expected_mod12 in known_peaks:
    pm = global_peak_mod12(n)
    check(f"{n} global peak mod12 == {expected_mod12}",
          pm == expected_mod12,
          f"peakMod12={pm}")

# ─────────────────────────────────────────────
section("LAW 20 — ODD ISOLATION LAW  (maxOddRun always = 1)")
# 3n+1 is always even when n is odd, so you can never have two consecutive
# odd steps.  maxOddRun must always be exactly 1 for odd seeds.
max_run_violations = 0
for n in range(3, 100_001, 2):
    r = trace(n)
    if r['max_odd_run'] > 1:
        max_run_violations += 1
        print(f"    VIOLATION: n={n} maxOddRun={r['max_odd_run']}")
check(f"maxOddRun = 1 for all odd seeds [3..100001]",
      max_run_violations == 0,
      f"violations={max_run_violations}")

# ─────────────────────────────────────────────
# TRIPLE SHELL TEST — all three together
section("TRIPLE SHELL TEST  (Laws 3+4+5 combined)")
triple_tests = [
    (2**17 - 1, 2**17,     2**17 + 1),
    (2**23 - 1, 2**23,     2**23 + 1),
    (2**53 - 1, 2**53,     2**53 + 1),
]
for lo, mid, hi in triple_tests:
    r_lo  = trace(lo)
    r_mid = trace(mid)
    r_hi  = trace(hi)
    k = round(math.log2(mid))
    check(f"2^{k}-1 steps ({r_lo['steps']}) >> 2^{k} steps ({r_mid['steps']}) == 1",
          r_mid['steps'] == 1)
    check(f"2^{k}+1 steps ({r_hi['steps']}) ≤ 5",
          r_hi['steps'] <= 5)
    check(f"2^{k}-1 steps >> 2^{k}+1 steps",
          r_lo['steps'] > r_hi['steps'])

# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("  RESULTS")
print("=" * 60)
total = passed + failed
print(f"  Passed : {passed} / {total}")
print(f"  Failed : {failed} / {total}")
if failed == 0:
    print("\n  ✅  ALL LAWS VERIFIED — every rule holds on tested examples.")
else:
    print(f"\n  ❌  {failed} law(s) failed — review output above.")
print()
