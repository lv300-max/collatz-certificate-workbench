"""
margin_theorem_probe.py
========================
Target: prove that for every deep sibling formula, a < 2^c.

Since a = 3^o (where o = number of odd steps in the orbit prefix),
the condition a < 2^c is equivalent to:

    3^o < 2^c
    ⟺  o · log₂(3) < c
    ⟺  c / o > log₂(3)  ≈ 1.58496...

We call  δ = c - o·log₂(3)  the "log-drift" (must be > 0).
We call  ε = c/o - log₂(3)  the "rate margin" (must be > 0).

For each sibling of each deep parent (depth 17–18), we extract
the parity word, compute (o, c, δ, ε, B, margin=2^c-3^o),
and look for:
  1. Is δ > 0 always? (is c/o > log2(3) always?)
  2. What is the minimum δ observed?
  3. Do near-zero δ (tight drift) correspond to high B?
  4. Is there a uniform lower bound ε₀ > 0?
  5. Does the parity word structure enforce δ > 0?

PARITY WORD STRUCTURE:
  A Collatz orbit prefix of m steps can be written as a binary word P
  where bit i = 1 if step i was odd, 0 if even.
  Given P, we have:
    o   = popcount(P)
    c   = m - o  (every even step increments c by 1, odd step increments c by 0
                  but does increment b; actually c is tracked directly)
  Wait — actually from the descent function: c = total right-shifts = total even
  steps. And a = 3^o. So we need:
    (total right-shifts) / (total odd steps) > log₂(3)
  i.e., (even steps) / (odd steps) > log₂(3) ≈ 1.585

  Since even_steps + odd_steps = m:
    c / o = (m - o) / o = m/o - 1 > log₂(3)
    ⟹ m/o > 1 + log₂(3) ≈ 2.585
    ⟹ o/m < 1 / (1 + log₂(3)) ≈ 0.3868

  So the fraction of odd steps must be below ~38.68%.
  If it ever reaches or exceeds that, descent fails.

EXTENDED ANALYSIS:
  - Extract parity word from orbit prefix
  - Track (o, c, δ, ε) for every distinct formula
  - Report minimum δ, minimum ε
  - Find which parity words produce the tightest margins
  - Check if tight-margin formulas correspond to high B
"""

import time, sys, math
from collections import defaultdict, Counter

LOG2_3 = math.log2(3)   # ≈ 1.58496250072...

KMAX     = 16
MAX_K    = 500
MAX_STEPS = 10_000
MAX_DEPTH = 18

t0 = time.time()

# ── Core descent with parity word extraction ──────────────────────────────────

def compute_descent_with_parity(r, k, max_steps=MAX_STEPS):
    """
    Returns (m, a, b, c, B, valid, o, parity_word) where:
      o = odd step count
      parity_word = integer encoding the parity sequence (bit i = step i parity)
    """
    a, b, c = 1, 0, 0
    n = r
    valid = True
    parity_word = 0
    o = 0
    for m in range(1, max_steps + 1):
        if c >= k:
            valid = False
        if n % 2 == 0:
            c += 1; n >>= 1
            # parity_word bit = 0 (already 0)
        else:
            a = 3 * a; b = 3 * b + (1 << c); n = 3 * n + 1
            o += 1
            parity_word |= (1 << (m - 1))
        two_c = 1 << c
        if two_c > a:
            B = (b + two_c - a - 1) // (two_c - a)
            return (m, a, b, c, B, valid, o, parity_word)
    return None

def find_valid_k_with_parity(r, k_min=KMAX, max_k=MAX_K):
    for k in range(k_min, max_k + 1):
        rep = r % (1 << k)
        if rep % 2 == 0:
            continue
        res = compute_descent_with_parity(rep, k)
        if res is not None and res[5]:
            return k, res
    return None, None

# ── Build parent list ─────────────────────────────────────────────────────────

print("=" * 72)
print("MARGIN THEOREM PROBE  —  Is c/o > log₂(3) always?")
print("=" * 72)
print(f"  log₂(3) = {LOG2_3:.10f}")
print(f"  Target:  c/o > {LOG2_3:.6f}  for every sibling formula")
print()

print("Scanning deep parents (depth 17–18) ...")
parents_by_depth = defaultdict(list)
for r0 in range(1, 1 << KMAX, 2):
    res0 = compute_descent_with_parity(r0, KMAX)
    if res0 is None or res0[5]:
        continue
    kv_res = None
    for k in range(KMAX, MAX_K + 1):
        rep = r0 % (1 << k)
        if rep % 2 == 0:
            continue
        res = compute_descent_with_parity(rep, k)
        if res is not None and res[5]:
            kv_res = (k, res); break
    if kv_res is None:
        continue
    kv, res = kv_res
    d = kv - KMAX
    if 17 <= d <= MAX_DEPTH:
        parents_by_depth[d].append((r0, kv))

total_parents = sum(len(v) for v in parents_by_depth.values())
for d in sorted(parents_by_depth):
    print(f"  depth={d}: {len(parents_by_depth[d])} parents")
print(f"  Total: {total_parents}  ({time.time()-t0:.1f}s)")
print()

# ── Per-parent analysis ───────────────────────────────────────────────────────

def analyze_margin(r0, kv, depth, idx, total):
    n_sib = 1 << depth
    t_par = time.time()

    # Per-formula stats: keyed by (o, c) since a=3^o, and c determines margin
    formula_stats = {}   # (o,c) -> {count, B_max, B_list, delta, epsilon}
    all_delta  = []
    all_epsilon= []
    all_B      = []
    all_ratio  = []   # c/o
    fails      = 0

    min_delta   = float('inf')
    min_delta_o = min_delta_c = min_delta_B = min_delta_pw = None
    max_B       = 0
    max_B_delta = None

    # Track tight-margin (δ < 1) formulas
    tight_margin_formulas = []

    for j in range(n_sib):
        s   = r0 + j * (1 << KMAX)
        kf, res = find_valid_k_with_parity(s, k_min=KMAX, max_k=MAX_K)
        if kf is None:
            fails += 1
            continue

        m, a, b, c, B, valid, o, pw = res
        if o == 0:
            continue  # no odd steps → skip (shouldn't happen for odd n)

        delta   = c - o * LOG2_3          # must be > 0
        epsilon = c / o - LOG2_3          # must be > 0
        ratio   = c / o

        all_delta.append(delta)
        all_epsilon.append(epsilon)
        all_B.append(B)
        all_ratio.append(ratio)

        key = (o, c)
        if key not in formula_stats:
            formula_stats[key] = {'count': 0, 'B_max': 0, 'B_sum': 0,
                                   'delta': delta, 'epsilon': epsilon,
                                   'pw_example': pw, 'B_example': B}
        fs = formula_stats[key]
        fs['count'] += 1
        fs['B_sum'] += B
        if B > fs['B_max']:
            fs['B_max'] = B
            fs['pw_example'] = pw

        if delta < min_delta:
            min_delta   = delta
            min_delta_o = o
            min_delta_c = c
            min_delta_B = B
            min_delta_pw = pw

        if B > max_B:
            max_B       = B
            max_B_delta = delta

        if delta < 1.0:
            tight_margin_formulas.append((delta, o, c, B, pw))

    elapsed = time.time() - t_par

    # Sort tight margins
    tight_margin_formulas.sort()

    # Compute delta distribution
    if all_delta:
        delta_sorted = sorted(all_delta)
        n = len(delta_sorted)
        d10 = delta_sorted[n // 10]
        d50 = delta_sorted[n // 2]
        d90 = delta_sorted[9 * n // 10]

    # Bucket delta histogram
    def delta_histogram(vals, nbuckets=12):
        if not vals: return {}
        lo, hi = min(vals), max(vals)
        if lo == hi: return {lo: len(vals)}
        width = (hi - lo) / nbuckets
        h = defaultdict(int)
        for v in vals:
            bucket = int((v - lo) / width)
            bucket = min(bucket, nbuckets - 1)
            h[lo + bucket * width] += 1
        return dict(sorted(h.items()))

    print(f"\n{'='*72}")
    print(f"PARENT [{idx}/{total}]  r0={r0}  depth={depth}  k'={kv}  sibs={n_sib:,}")
    print(f"  Fails: {fails}  |  Time: {elapsed:.1f}s")
    print(f"  Unique (o,c) formulas: {len(formula_stats):,}")
    print(f"  All δ = c - o·log₂(3) > 0: {'YES ✅' if min_delta > 0 else 'NO ❌'}")
    print(f"  Min δ: {min_delta:.6f}  at o={min_delta_o}, c={min_delta_c}, B={min_delta_B}")
    print(f"  Max B: {max_B}  δ at max_B: {max_B_delta:.6f}")
    print(f"  Ratio c/o stats:")
    if all_ratio:
        ratio_sorted = sorted(all_ratio)
        nr = len(ratio_sorted)
        print(f"    min={ratio_sorted[0]:.6f}  p10={ratio_sorted[nr//10]:.6f}  "
              f"p50={ratio_sorted[nr//2]:.6f}  p90={ratio_sorted[9*nr//10]:.6f}  "
              f"max={ratio_sorted[-1]:.6f}")
        print(f"    log₂(3)={LOG2_3:.6f}  all ratios > log₂(3): "
              f"{'YES ✅' if ratio_sorted[0] > LOG2_3 else 'NO ❌'}")

    print(f"\n  δ distribution (c - o·log₂(3)):")
    dh = delta_histogram(all_delta)
    max_cnt = max(dh.values()) if dh else 1
    for bucket, cnt in list(dh.items())[:15]:
        bar = '#' * min(40, cnt * 40 // max_cnt)
        print(f"    δ>={bucket:8.3f}: {cnt:7,}  {bar}")

    print(f"\n  Tight-margin formulas (δ < 1.0): {len(tight_margin_formulas)}")
    if tight_margin_formulas:
        print(f"  {'δ':>10}  {'o':>6}  {'c':>6}  {'c/o':>8}  {'B':>6}  parity_word_bits")
        for delta, o, c, B, pw in tight_margin_formulas[:20]:
            pw_bits = bin(pw).count('1')
            pw_len  = pw.bit_length()
            print(f"  {delta:10.6f}  {o:6d}  {c:6d}  {c/o:8.6f}  {B:6d}  "
                  f"len={pw_len} ones={pw_bits} frac={pw_bits/pw_len:.4f}")

    print(f"\n  Correlation: δ vs B (tight δ < 2):")
    tight_pairs = [(d, B) for d, B in zip(all_delta, all_B) if d < 2.0]
    if tight_pairs:
        by_delta_bucket = defaultdict(list)
        for d_val, B_val in tight_pairs:
            bucket = round(d_val * 4) / 4  # 0.25 buckets
            by_delta_bucket[bucket].append(B_val)
        for bk in sorted(by_delta_bucket)[:12]:
            vs = by_delta_bucket[bk]
            print(f"    δ≈{bk:.2f}: n={len(vs):5,}  mean_B={sum(vs)/len(vs):6.1f}  max_B={max(vs)}")

    print(f"\n  Top-10 tightest δ formulas (lowest margin):")
    top_tight = sorted(formula_stats.items(), key=lambda x: x[1]['delta'])[:10]
    print(f"  {'(o,c)':>14}  {'δ':>10}  {'ε=c/o-log2(3)':>16}  {'B_max':>6}  count")
    for (o, c), fs in top_tight:
        print(f"  ({o:5d},{c:5d})  {fs['delta']:10.6f}  {fs['epsilon']:16.10f}  "
              f"{fs['B_max']:6d}  {fs['count']:,}")

    # Check: do tightest-δ formulas have highest B?
    top_B = sorted(formula_stats.items(), key=lambda x: -x[1]['B_max'])[:10]
    print(f"\n  Top-10 highest-B formulas:")
    print(f"  {'(o,c)':>14}  {'δ':>10}  {'B_max':>6}  count")
    for (o, c), fs in top_B:
        print(f"  ({o:5d},{c:5d})  {fs['delta']:10.6f}  {fs['B_max']:6d}  {fs['count']:,}")

    sys.stdout.flush()
    return {
        'r0': r0, 'depth': depth,
        'min_delta': min_delta, 'min_delta_o': min_delta_o, 'min_delta_c': min_delta_c,
        'max_B': max_B, 'max_B_delta': max_B_delta,
        'all_delta_gt_0': min_delta > 0,
        'min_ratio': min(all_ratio) if all_ratio else None,
        'tight_count': len(tight_margin_formulas),
        'n_formulas': len(formula_stats),
    }


# ── Main loop ─────────────────────────────────────────────────────────────────

all_results = []
idx = 0
total = total_parents

for depth in sorted(parents_by_depth):
    for (r0, kv) in parents_by_depth[depth]:
        idx += 1
        result = analyze_margin(r0, kv, depth, idx, total)
        all_results.append(result)
        sys.stdout.flush()

# ── Grand summary ─────────────────────────────────────────────────────────────

print()
print("=" * 72)
print("GRAND SUMMARY — MARGIN THEOREM PROBE")
print("=" * 72)
print(f"  log₂(3) = {LOG2_3:.10f}")
print(f"  Target:  c/o > log₂(3)  for every sibling formula")
print()

all_min_delta  = [r['min_delta'] for r in all_results]
all_min_ratio  = [r['min_ratio'] for r in all_results if r['min_ratio']]
all_tight      = [r['tight_count'] for r in all_results]
all_delta_ok   = all(r['all_delta_gt_0'] for r in all_results)

global_min_delta = min(all_min_delta) if all_min_delta else None
global_min_ratio = min(all_min_ratio) if all_min_ratio else None

print(f"  Parents analyzed      : {len(all_results)}")
print(f"  All δ > 0 (c > o·log₂(3)) : {'YES ✅' if all_delta_ok else 'NO ❌'}")
print(f"  Global min δ          : {global_min_delta:.6f}")
print(f"  Global min c/o        : {global_min_ratio:.6f}  (log₂(3)={LOG2_3:.6f})")
print(f"  Global min c/o - log₂(3)  : {global_min_ratio - LOG2_3:.6f}")
print(f"  Total tight-margin (δ<1) formulas: {sum(all_tight):,}")
print()

# Per parent minimum delta table
print("  Per-parent min δ (sorted ascending):")
sorted_results = sorted(all_results, key=lambda x: x['min_delta'])
print(f"  {'r0':>8}  {'depth':>5}  {'min_δ':>10}  {'min_ratio':>10}  {'max_B':>6}  "
      f"{'δ_at_maxB':>10}  formulas")
for r in sorted_results[:20]:
    print(f"  {r['r0']:8d}  {r['depth']:5d}  {r['min_delta']:10.6f}  "
          f"{r['min_ratio'] or 0:10.6f}  {r['max_B']:6d}  "
          f"{r['max_B_delta'] or 0:10.6f}  {r['n_formulas']:,}")

print()
if all_delta_ok and global_min_delta > 0:
    print(f"✅  MARGIN THEOREM HOLDS for all analyzed siblings:")
    print(f"    c / o > log₂(3) for every formula in every sibling family.")
    print(f"    Global minimum c/o = {global_min_ratio:.8f}")
    print(f"    Global minimum δ   = {global_min_delta:.8f}")
    print(f"    Global minimum ε   = c/o - log₂(3) = {global_min_ratio - LOG2_3:.8f}")
    print()
    print(f"  KEY QUESTION: Is ε bounded away from 0 uniformly?")
    print(f"  If ε ≥ ε₀ > 0 for ALL deep parents and ALL depths,")
    print(f"  then a < 2^c is structurally guaranteed, closing the proof gap.")
    print()
    print(f"  Observed global ε₀ (lower bound from data): {global_min_ratio - LOG2_3:.8f}")
    if global_min_ratio - LOG2_3 > 0.001:
        print(f"  ε > 0.001 ✅  — non-trivial uniform gap observed")
    else:
        print(f"  ε very small — need deeper analysis")
else:
    print(f"❌  Margin theorem FAILS — some formula has c/o <= log₂(3)")

print(f"\n  Total time: {time.time()-t0:.1f}s")
