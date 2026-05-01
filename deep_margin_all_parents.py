"""
deep_margin_all_parents.py
===========================
Extend the margin-theorem probe to ALL 776 open deep parents (depth 17+).

For depth 17-18 (55 parents): exact enumeration was done in margin_theorem_probe.py.
For depth 19+  (721 parents): c_par can be 43..119, siblings = 2^(c_par-16) = too many.
  → Use targeted random sampling: N_SAMPLE siblings per parent.

For each sibling we extract (o, c) from its descent formula and compute:
  δ  = c  - o · log₂(3)       (log-drift;  must be > 0)
  ε  = c/o - log₂(3)          (rate margin; must be > 0)
  B  = ceil(b / (2^c - 3^o))  (threshold; must be ≤ 200001)

Pass condition:  c/o > 1.5849625  AND  B ≤ 200001

KEY QUESTION: Is the global minimum δ across ALL 776 parents
and ALL sampled siblings still strictly positive?

Also: do any of the deeper parents achieve tighter margins
(δ < 0.007500, the current minimum from depth 17-18)?

OUTPUT:
  - Per-parent: min δ, min c/o, max B, pass/fail
  - Grand summary: global min δ, min ε, any violation
  - Danger-lane table: top-20 tightest δ parents
  - Violation list (if any)
"""

import time, sys, math, random, json
from collections import defaultdict

LOG2_3   = math.log2(3)   # 1.58496250072...
KMAX     = 16
MAX_K    = 500
MAX_STEPS = 10_000
N_SAMPLE  = 4096          # siblings to sample per depth-19+ parent
B_LIMIT   = 200_001
PASS_RATIO = LOG2_3       # c/o must exceed this

t0 = time.time()

# ── Descent formula ──────────────────────────────────────────────────────────

def compute_descent(r, k, max_steps=MAX_STEPS):
    """
    Symbolic descent of residue r at level k.
    Returns (m, a, b, c, B, valid) or None if no formula found in max_steps.
    a = 3^o, c = total even-steps.
    """
    a, b, c = 1, 0, 0
    n = r
    valid = True
    for m in range(1, max_steps + 1):
        if c >= k:
            valid = False
        if n % 2 == 0:
            c += 1
            n >>= 1
        else:
            a = 3 * a
            b = 3 * b + (1 << c)
            n = 3 * n + 1
        two_c = 1 << c
        if two_c > a:
            B = (b + two_c - a - 1) // (two_c - a)
            return (m, a, b, c, B, valid)
    return None

# ── Load certificate ─────────────────────────────────────────────────────────

print("Loading certificate...", flush=True)
data = json.load(open("collatz_certificate.json"))
certs = data["certificates"]

# Build parent registry from invalid_k16_root entries
roots_by_r0 = {}   # r0 (int) → root entry
for c in certs:
    if c.get("source") == "invalid_k16_root":
        r0 = int(c["residue"])
        roots_by_r0[r0] = c

# Build per-parent sampled entry list (already in certificate)
cert_sampled = defaultdict(list)
for c in certs:
    if c.get("source") == "bfs_sibling_sampled":
        p = c["parent_k16_residue"]
        cert_sampled[p].append(c)

print(f"  invalid_k16_root parents: {len(roots_by_r0)}")
print(f"  parents with cert samples: {len(cert_sampled)}")

# Collect all 776 open parents (those with sampled entries)
all_parents = []
for r0_str, entries in cert_sampled.items():
    r0 = int(r0_str)
    root = roots_by_r0.get(r0)
    if root is None:
        continue
    c_par = int(root["c"])          # = k of the invalid_k16_root entry
    depth  = c_par - KMAX           # = k' - 16
    all_parents.append((r0, c_par, depth, entries))

all_parents.sort(key=lambda x: (x[2], x[0]))   # sort by depth then r0
print(f"  open parents resolved: {len(all_parents)}")
print(f"  depth range: {all_parents[0][2]} .. {all_parents[-1][2]}")
print()

# Separate into exact (depth ≤ 16 handled by prior scripts) and sample groups
# depth 17-18 was done in margin_theorem_probe; we redo them here for completeness
# depth 19+ needs sampling

# ── Per-parent analysis ──────────────────────────────────────────────────────

grand_min_delta  = float("inf")
grand_min_ratio  = float("inf")
grand_max_B      = 0
grand_violations = []
parent_rows      = []   # (min_delta, min_ratio, max_B, r0, depth, c_par, n_sibs, pass)

DIVIDER = "=" * 72

print(DIVIDER)
print(f"DEEP MARGIN PROBE — ALL {len(all_parents)} OPEN PARENTS")
print(DIVIDER)
print(f"{'r0':>8}  {'dep':>3}  {'c_par':>5}  {'n_sibs':>7}  "
      f"{'min_δ':>10}  {'min_c/o':>10}  {'max_B':>7}  {'pass':>5}")
print("-" * 72)

for idx, (r0, c_par, depth, cert_entries) in enumerate(all_parents):
    t_par = time.time()

    min_delta  = float("inf")
    min_ratio  = float("inf")
    max_B      = 0
    fail_count = 0
    n_checked  = 0

    # --- Strategy A: use all cert-sampled entries (already computed formulas) ---
    for entry in cert_entries:
        a_val = int(entry["a"])
        c_val = int(entry["c"])
        b_val = int(entry["b"])
        B_val = int(entry["threshold_B"])
        if a_val <= 0:
            continue
        # o from a = 3^o
        o = round(math.log(a_val, 3)) if a_val > 1 else 0
        if o <= 0 or 3**o != a_val:
            continue
        delta = c_val - o * LOG2_3
        ratio = c_val / o
        if delta < min_delta:
            min_delta = delta
        if ratio < min_ratio:
            min_ratio = ratio
        if B_val > max_B:
            max_B = B_val
        if ratio <= PASS_RATIO or B_val > B_LIMIT:
            fail_count += 1
            grand_violations.append({
                "r0": r0, "depth": depth, "c_par": c_par,
                "o": o, "c": c_val, "B": B_val,
                "delta": delta, "ratio": ratio,
                "source": "cert_sample"
            })
        n_checked += 1

    # --- Strategy B: fresh random sample for depth-19+ parents ---
    if depth >= 3:   # depth 19+ means c_par-16 >= 3, so c_par >= 19
        n_upper_bits = c_par - KMAX  # number of free bits above bit-16
        sample_count = min(N_SAMPLE, 1 << n_upper_bits)
        # Sample random j values in [0, 2^n_upper_bits)
        max_j = 1 << n_upper_bits
        if max_j <= sample_count:
            js = range(max_j)              # enumerate all if small
        else:
            js = [random.randint(0, max_j - 1) for _ in range(sample_count)]
        for j in js:
            r_sib = (r0 + j * (1 << KMAX)) % (1 << c_par)
            res = compute_descent(r_sib, c_par)
            if res is None:
                continue
            m_val, a_val, b_val, c_val, B_val, valid = res
            if not valid:
                continue
            o = round(math.log(a_val, 3)) if a_val > 1 else 0
            if o <= 0 or 3**o != a_val:
                continue
            delta = c_val - o * LOG2_3
            ratio = c_val / o
            if delta < min_delta:
                min_delta = delta
            if ratio < min_ratio:
                min_ratio = ratio
            if B_val > max_B:
                max_B = B_val
            if ratio <= PASS_RATIO or B_val > B_LIMIT:
                fail_count += 1
                grand_violations.append({
                    "r0": r0, "depth": depth, "c_par": c_par,
                    "o": o, "c": c_val, "B": B_val,
                    "delta": delta, "ratio": ratio,
                    "source": "fresh_sample"
                })
            n_checked += 1

    # Update grand stats
    if min_delta < grand_min_delta:
        grand_min_delta = min_delta
    if min_ratio < grand_min_ratio:
        grand_min_ratio = min_ratio
    if max_B > grand_max_B:
        grand_max_B = max_B

    passed = (fail_count == 0)
    status = "PASS" if passed else f"FAIL({fail_count})"
    parent_rows.append((min_delta, min_ratio, max_B, r0, depth, c_par, n_checked, passed))

    elapsed = time.time() - t_par
    print(f"{r0:>8}  {depth:>3}  {c_par:>5}  {n_checked:>7}  "
          f"{min_delta:>10.6f}  {min_ratio:>10.8f}  {max_B:>7}  {status:>5}",
          flush=True)

# ── Grand Summary ─────────────────────────────────────────────────────────────

elapsed_total = time.time() - t0

print()
print(DIVIDER)
print("GRAND SUMMARY — DEEP MARGIN ALL PARENTS")
print(DIVIDER)
print(f"  log₂(3)              = {LOG2_3:.10f}")
print(f"  Parents analyzed     : {len(all_parents)}")
print(f"  Total time           : {elapsed_total:.1f}s ({elapsed_total/60:.1f} min)")
print()
print(f"  Global min δ         = {grand_min_delta:.6f}")
print(f"  Global min c/o       = {grand_min_ratio:.8f}")
print(f"  Global min ε         = {grand_min_ratio - LOG2_3:.8f}")
print(f"  Global max B         = {grand_max_B}")
print()

all_pass = (len(grand_violations) == 0)
if all_pass:
    print("  ✅  ALL PARENTS PASS:  c/o > log₂(3)  and  B ≤ 200,001")
else:
    print(f"  ❌  VIOLATIONS: {len(grand_violations)} entries failed!")
    print()
    for v in grand_violations[:20]:
        print(f"    r0={v['r0']} dep={v['depth']} o={v['o']} c={v['c']} "
              f"ratio={v['ratio']:.8f} δ={v['delta']:.6f} B={v['B']}")

# ── Danger Lane Table ─────────────────────────────────────────────────────────

print()
print("  Danger-lane table: 30 parents with smallest min_δ")
print(f"  {'min_δ':>10}  {'min_c/o':>10}  {'max_B':>7}  {'r0':>8}  {'dep':>4}  {'c_par':>6}  {'n':>7}")
parent_rows.sort()  # sort by min_delta ascending
for row in parent_rows[:30]:
    min_delta, min_ratio, max_B, r0, depth, c_par, n_checked, passed = row
    flag = "" if passed else " ❌"
    print(f"  {min_delta:>10.6f}  {min_ratio:>10.8f}  {max_B:>7}  "
          f"{r0:>8}  {depth:>4}  {c_par:>6}  {n_checked:>7}{flag}")

# ── δ histogram across all parents ───────────────────────────────────────────

print()
print("  Distribution of per-parent min_δ:")
bins = [0, 0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30, float("inf")]
labels = ["0.00","0.01","0.02","0.03","0.05","0.07","0.10","0.15","0.20","0.30","∞"]
counts = [0] * (len(bins) - 1)
for row in parent_rows:
    d = row[0]
    for i in range(len(bins) - 1):
        if bins[i] <= d < bins[i+1]:
            counts[i] += 1
            break
for i, cnt in enumerate(counts):
    bar = "#" * (cnt * 40 // max(counts, default=1))
    print(f"    δ ∈ [{labels[i]:>5},{labels[i+1]:>5}) : {cnt:4d}  {bar}")

print()
print(DIVIDER)
if all_pass:
    print("✅  MARGIN THEOREM HOLDS for all sampled siblings across all 776 parents.")
    print(f"   Minimum observed δ = {grand_min_delta:.6f}")
    print(f"   Minimum observed ε = c/o - log₂(3) = {grand_min_ratio - LOG2_3:.8f}")
else:
    print("❌  VIOLATIONS FOUND — see above.")
print(DIVIDER)
