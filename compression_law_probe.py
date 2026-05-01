"""
compression_law_probe.py
=========================
For deep invalid lane parents at depth 17 and 18, fully enumerate all siblings
and analyze whether the huge space of (a,b,c) triples compresses into
proof-relevant invariant classes.

QUESTIONS:
  1. Does every formula satisfy a < 2^c?  (descent margin positive)
  2. Is B = ceil(b/(2^c-a)) always bounded by a small constant?
  3. Does max B depend structurally on: depth / popcount(j) / trailing_ones(j) /
     j mod small power of 2 / c-a margin?
  4. Are there patterns in residue j mod 2^m vs B?
  5. Can we find a compressed invariant: "for all j, B <= C" with C provable?

OUTPUT PER PARENT:
  - sibling count, unique formula count, unique parity word count
  - max B, min descent margin, worst sibling
  - histograms: B, k_needed, c values
  - correlations: trailing_ones(j)/popcount(j)/j%64 vs B
  - regression: what structural feature of j best predicts B?
"""

import time, sys, math
from collections import defaultdict, Counter

KMAX       = 16
MAX_K      = 500
MAX_STEPS  = 10_000
MAX_DEPTH  = 18   # fully enumerate depth <= this; depth-17 and depth-18

t0 = time.time()

# ── Core descent ─────────────────────────────────────────────────────────────

def compute_descent(r, k, max_steps=MAX_STEPS):
    a, b, c = 1, 0, 0; n = r; valid = True
    for m in range(1, max_steps + 1):
        if c >= k: valid = False
        if n % 2 == 0: c += 1; n >>= 1
        else: a = 3*a; b = 3*b + (1 << c); n = 3*n + 1
        two_c = 1 << c
        if two_c > a:
            return (m, a, b, c, (b + two_c - a - 1) // (two_c - a), valid)
    return None

def find_valid_k(r, k_min=KMAX, max_k=MAX_K):
    for k in range(k_min, max_k + 1):
        rep = r % (1 << k)
        if rep % 2 == 0: continue
        res = compute_descent(rep, k)
        if res is not None and res[5]:
            return k, res
    return None, None

def trailing_ones(j):
    if j == 0: return 0
    count = 0
    while j & 1:
        count += 1; j >>= 1
    return count

def trailing_zeros(j):
    if j == 0: return 64
    count = 0
    while not (j & 1):
        count += 1; j >>= 1
    return count

# ── Build deep parent list ────────────────────────────────────────────────────

print("=" * 72)
print("COMPRESSION LAW PROBE — Deep Sibling Formula Analysis")
print("=" * 72)
print()
print("Scanning for deep parents (depth 17–18) ...")

parents_by_depth = defaultdict(list)
for r0 in range(1, 1 << KMAX, 2):
    res0 = compute_descent(r0, KMAX)
    if res0 is None or res0[5]: continue
    kv, res = find_valid_k(r0)
    if kv is None: continue
    d = kv - KMAX
    if 17 <= d <= MAX_DEPTH:
        parents_by_depth[d].append((r0, kv, res[1], res[2], res[3], res[4]))

for d in sorted(parents_by_depth):
    print(f"  depth={d}: {len(parents_by_depth[d])} parents")

total_parents = sum(len(v) for v in parents_by_depth.values())
print(f"  Total: {total_parents} parents")
print(f"  Scan time: {time.time()-t0:.1f}s")
print()

# ── Per-parent analysis ───────────────────────────────────────────────────────

def analyze_parent(r0, kv, depth, idx, total):
    """Fully enumerate all 2^depth siblings and collect statistics."""
    n_sib = 1 << depth
    t_par = time.time()

    # Accumulators
    all_B       = []
    all_k       = []
    all_c       = []
    all_margin  = []   # 2^c - a
    formulas    = Counter()  # (a,b,c) -> count
    fails       = 0
    worst_B     = 0
    worst_j     = -1
    worst_abc   = None
    min_margin  = float('inf')
    min_margin_j = -1

    # Correlation tables: attribute -> list of (attr_val, B)
    corr_trailing_ones = []
    corr_trailing_zeros= []
    corr_popcount      = []
    corr_jmod64        = []
    corr_jmod32        = []
    corr_jmod8         = []
    corr_c             = []

    for j in range(n_sib):
        s  = r0 + j * (1 << KMAX)
        kf, res = find_valid_k(s, k_min=KMAX, max_k=MAX_K)
        if kf is None:
            fails += 1
            continue
        m, a, b, c, B, valid = res
        margin = (1 << c) - a

        all_B.append(B)
        all_k.append(kf)
        all_c.append(c)
        all_margin.append(margin)
        formulas[(a, b, c)] += 1

        if B > worst_B:
            worst_B   = B
            worst_j   = j
            worst_abc = (a, b, c, B, kf)

        if margin < min_margin:
            min_margin   = margin
            min_margin_j = j

        to = trailing_ones(j)
        tz = trailing_zeros(j) if j > 0 else depth
        pc = bin(j).count('1')

        corr_trailing_ones.append((to, B))
        corr_trailing_zeros.append((tz, B))
        corr_popcount.append((pc, B))
        corr_jmod64.append((j % 64, B))
        corr_jmod32.append((j % 32, B))
        corr_jmod8.append((j  %  8, B))
        corr_c.append((c, B))

    elapsed = time.time() - t_par

    # Histograms
    def histogram(vals, nbins=10):
        if not vals: return {}
        lo, hi = min(vals), max(vals)
        if lo == hi: return {lo: len(vals)}
        step = max(1, (hi - lo + nbins - 1) // nbins)
        h = defaultdict(int)
        for v in vals:
            bucket = lo + ((v - lo) // step) * step
            h[bucket] += 1
        return dict(sorted(h.items()))

    def correlation_by_key(pairs):
        """Group by key, compute mean and max B per key."""
        by_key = defaultdict(list)
        for k, v in pairs:
            by_key[k].append(v)
        return {k: (sum(vs)/len(vs), max(vs), len(vs)) for k, vs in sorted(by_key.items())}

    # Print results
    print(f"\n{'='*72}")
    print(f"PARENT [{idx}/{total}]  r0={r0}  depth={depth}  k'={kv}")
    print(f"  Siblings: {n_sib:,}  |  Fails: {fails}  |  Time: {elapsed:.1f}s")
    print(f"  Unique formulas (a,b,c): {len(formulas):,} / {n_sib:,} siblings")
    print(f"  Max B: {worst_B}  |  Worst j: {worst_j}  |  Worst (a,b,c,B,k): {worst_abc}")
    print(f"  Min descent margin (2^c-a): {min_margin}  |  At j={min_margin_j}")
    print(f"  All margins > 0: {'YES ✅' if min_margin > 0 else 'NO ❌'}")
    print(f"  All B <= 200001: {'YES ✅' if worst_B <= 200001 else 'NO ❌  MAX=' + str(worst_B)}")

    # k histogram
    k_hist = Counter(all_k)
    print(f"\n  k_needed histogram (top 10 values):")
    for kval, cnt in sorted(k_hist.items())[:20]:
        bar = '#' * min(40, cnt * 40 // max(k_hist.values()))
        print(f"    k={kval:4d}: {cnt:7,}  {bar}")

    # B histogram
    B_hist = histogram(all_B, nbins=12)
    print(f"\n  B histogram:")
    max_cnt = max(B_hist.values()) if B_hist else 1
    for blo, cnt in sorted(B_hist.items()):
        bar = '#' * min(40, cnt * 40 // max_cnt)
        print(f"    B>={blo:6d}: {cnt:7,}  {bar}")

    # c histogram
    c_hist = Counter(all_c)
    print(f"\n  c (orbit depth) histogram (top 15):")
    for cval, cnt in sorted(c_hist.items())[:20]:
        bar = '#' * min(40, cnt * 40 // max(c_hist.values()))
        print(f"    c={cval:4d}: {cnt:7,}  {bar}")

    # Correlation: trailing_ones(j) vs max B
    to_corr = correlation_by_key(corr_trailing_ones)
    print(f"\n  trailing_ones(j) → mean_B / max_B:")
    for to_val, (mean_B, max_B_v, cnt) in sorted(to_corr.items()):
        print(f"    trailing_ones={to_val:3d}: mean_B={mean_B:7.1f}  max_B={max_B_v:6d}  n={cnt:7,}")

    # Correlation: popcount(j) vs max B
    pc_corr = correlation_by_key(corr_popcount)
    print(f"\n  popcount(j) → mean_B / max_B:")
    for pc_val, (mean_B, max_B_v, cnt) in sorted(pc_corr.items()):
        print(f"    popcount={pc_val:3d}: mean_B={mean_B:7.1f}  max_B={max_B_v:6d}  n={cnt:7,}")

    # Correlation: j mod 8 vs max B
    j8_corr = correlation_by_key(corr_jmod8)
    print(f"\n  j mod 8 → mean_B / max_B:")
    for jmod, (mean_B, max_B_v, cnt) in sorted(j8_corr.items()):
        print(f"    j%8={jmod}: mean_B={mean_B:7.1f}  max_B={max_B_v:6d}  n={cnt:7,}")

    # Correlation: c vs max B
    c_corr = correlation_by_key(corr_c)
    print(f"\n  c (orbit depth) → mean_B / max_B (top by max_B):")
    top_c = sorted(c_corr.items(), key=lambda x: -x[1][1])[:10]
    for cval, (mean_B, max_B_v, cnt) in top_c:
        print(f"    c={cval:4d}: mean_B={mean_B:7.1f}  max_B={max_B_v:6d}  n={cnt:7,}")

    # Margin statistics
    margin_sorted = sorted(all_margin)
    print(f"\n  Descent margin (2^c-a) stats:")
    print(f"    min={min(all_margin)}  median={margin_sorted[len(margin_sorted)//2]}  max={max(all_margin)}")
    print(f"    margins==1: {sum(1 for m in all_margin if m==1):,}  margins<=10: {sum(1 for m in all_margin if m<=10):,}")

    # Top-10 worst B siblings
    combined = list(zip(all_B, all_k, all_c, [t for t,_ in corr_trailing_ones],
                        [p for p,_ in corr_popcount]))
    combined_sorted = sorted(combined, key=lambda x: -x[0])[:10]
    print(f"\n  Top-10 worst-B siblings:")
    print(f"    {'B':>8}  {'k':>5}  {'c':>5}  {'trail_1s':>8}  {'popcount':>8}")
    for B_v, k_v, c_v, to_v, pc_v in combined_sorted:
        print(f"    {B_v:8d}  {k_v:5d}  {c_v:5d}  {to_v:8d}  {pc_v:8d}")

    return {
        'r0': r0, 'depth': depth, 'n_sib': n_sib,
        'fails': fails, 'max_B': worst_B, 'min_margin': min_margin,
        'n_formulas': len(formulas), 'all_B': all_B,
        'a_lt_2c_all': min_margin > 0,
        'B_bounded': worst_B <= 200001,
    }


# ── Main loop ────────────────────────────────────────────────────────────────

all_results = []
idx = 0
total = total_parents

for depth in sorted(parents_by_depth):
    for (r0, kv, a_par, b_par, c_par, B_par) in parents_by_depth[depth]:
        idx += 1
        result = analyze_parent(r0, kv, depth, idx, total)
        all_results.append(result)
        sys.stdout.flush()

# ── Grand summary ─────────────────────────────────────────────────────────────

print()
print("=" * 72)
print("GRAND SUMMARY — COMPRESSION LAW PROBE")
print("=" * 72)
print()
total_sib = sum(r['n_sib'] for r in all_results)
total_fails = sum(r['fails'] for r in all_results)
all_max_B = [r['max_B'] for r in all_results]
all_margins_ok = all(r['a_lt_2c_all'] for r in all_results)
all_B_bounded = all(r['B_bounded'] for r in all_results)

print(f"  Parents analyzed     : {len(all_results)}")
print(f"  Total siblings       : {total_sib:,}")
print(f"  Total failures       : {total_fails}")
print(f"  All margins > 0      : {'YES ✅' if all_margins_ok else 'NO ❌'}")
print(f"  All B <= 200001      : {'YES ✅' if all_B_bounded else 'NO ❌'}")
print(f"  Global max B         : {max(all_max_B) if all_max_B else 'N/A'}")
print(f"  Max B by parent:")
for r in sorted(all_results, key=lambda x: -x['max_B'])[:10]:
    print(f"    r0={r['r0']:8d} d={r['depth']} max_B={r['max_B']:6d} "
          f"formulas={r['n_formulas']:,}/{r['n_sib']:,}")

print()
if total_fails == 0 and all_margins_ok and all_B_bounded:
    print("✅  COMPRESSION LAW HOLDS for all analyzed parents:")
    print("    Every sibling has a < 2^c (descent guaranteed) and B <= 200001.")
    print("    The 633 open parents may close by the same compressed invariant.")
    print("    KEY CONJECTURE: for all deep parents, max B <= C_d for a depth-dependent C_d.")
else:
    print("❌  Compression law does NOT hold universally — see failures above.")

print(f"\n  Total time: {time.time()-t0:.1f}s")
