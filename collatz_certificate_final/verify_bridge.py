"""
verify_bridge.py  —  Honest Independent Audit of descent_bridge.py
====================================================================
SECTIONS:
  [1] ALGEBRAIC: Prove peakMod12 in {4,10} mod 12 for all odd n
  [2] FORMULA SPOT-CHECK: Verify (a,b,c) formula for valid+invalid lanes
  [3] VALIDITY AUDIT: Count valid vs invalid lanes at k=1..16
  [4] GAP ANALYSIS: Find n > bridge_limit with no valid symbolic coverage

DEFINITION: lane (r, k) is VALID iff c <= k when 2^c > a is first met.
  Valid   => T^m(n) = (a*n+b)/2^c holds for ALL n == r (mod 2^k)
  Invalid => formula only guaranteed for n == r (mod 2^c), c > k
"""

import math, random, time

def compute_descent_window(r, k, max_steps=3000):
    a, b, c = 1, 0, 0; n = r; c_valid = True
    for m in range(1, max_steps + 1):
        if n <= 0: break
        if n == 1:
            return {'m':m-1,'a':0,'b':0,'c':1,'threshold':1,'valid':c_valid,'terminal':True}
        if c >= k: c_valid = False
        if n % 2 == 0: c += 1; n >>= 1
        else: a = 3*a; b = 3*b + (1 << c); n = 3*n + 1
        two_c = 1 << c
        if two_c > a:
            return {'m':m,'a':a,'b':b,'c':c,'threshold':(b+two_c-a-1)//(two_c-a),'valid':c_valid,'terminal':False}
    return None

def collatz_steps(n0, steps):
    n = n0
    for _ in range(steps):
        n = n >> 1 if n % 2 == 0 else 3*n + 1
    return n

def has_valid_coverage(n, kmax=16):
    for k in range(1, kmax+1):
        r = n % (1 << k)
        if r % 2 == 0: continue
        res = compute_descent_window(r, k)
        if res and res['valid'] and not res.get('terminal') and res['threshold'] < n:
            return True, k, r, res
    return False, None, None, None

SEP = "=" * 68

# ── [1] ALGEBRAIC PROOF: peakMod12 ───────────────────────────────────────────
print(SEP)
print("[1]  ALGEBRAIC PROOF  -- peakMod12 in {4,10} (mod 12)")
print(SEP)
odd_res   = [r for r in range(12) if r % 2 == 1]
images    = {r: (3*r+1)%12 for r in odd_res}
img_set   = set(images.values())
ok1       = (img_set == {4, 10})
print("  Odd residues mod 12 :", odd_res)
print("  3r+1 mod 12 :", [(r, images[r]) for r in odd_res])
print("  Image set   :", sorted(img_set))
print("  MATCH {4,10}:", 'YES' if ok1 else 'NO')
print("  Status: PROVEN ALGEBRAICALLY" + (" ✓" if ok1 else " ✗"))
print()

# ── [2] FORMULA SPOT-CHECK ────────────────────────────────────────────────────
print(SEP)
print("[2]  FORMULA SPOT-CHECK  -- 200 lanes at k=16, 50 checks each")
print(SEP)
K16 = 16; MOD16 = 1 << K16
random.seed(42)
sample_lanes = random.sample(range(1, MOD16, 2), 200)
res2 = {'vp':0,'vf':0,'ip':0,'if_':0}
fails2 = []
for r in sample_lanes:
    res = compute_descent_window(r, K16)
    if res is None or res.get('terminal'): continue
    a,b,c,m = res['a'],res['b'],res['c'],res['m']
    two_c = 1<<c; ok = True
    for _ in range(50):
        n0 = r + random.randint(1,10000)*MOD16
        if n0%2==0: n0 += MOD16
        actual = collatz_steps(n0, m)
        numer  = a*n0+b
        if numer % two_c != 0 or numer//two_c != actual:
            ok = False
            if len(fails2)<3: fails2.append((r,n0,a,b,c,m,'mismatch' if numer%two_c==0 else 'not_div'))
            break
    k_ = 'vp' if (res['valid'] and ok) else 'vf' if (res['valid'] and not ok) else 'ip' if ok else 'if_'
    res2[k_] += 1

print(f"  VALID lanes  (c<=k):  matched {res2['vp']:3}  mismatched {res2['vf']:3}  <- should be 0")
print(f"  INVALID lanes (c>k):  matched {res2['ip']:3}  mismatched {res2['if_']:3}  <- expected nonzero")
sec2_ok = (res2['vf'] == 0)
print(f"  Section [2]: {'PASS' if sec2_ok else 'FAIL'}" + (" ✓" if sec2_ok else " ✗"))
if fails2:
    print("  Mismatch examples:")
    for f in fails2[:2]:
        print(f"    r={f[0]}, n'={f[1]}, c={f[4]}, m={f[5]}: {f[6]}")
print()

# ── [3] VALIDITY AUDIT k=1..16 ───────────────────────────────────────────────
print(SEP)
print("[3]  VALIDITY AUDIT  -- k=1..16")
print(SEP)
print("  Valid=c<=k  Invalid=c>k  Terminal=hits n=1 (not useful for large n)")
print()
KMAX=16
v_by_k={};i_by_k={};t_by_k={}
total_v=total_i=0
worst_v=worst_i=None
for k in range(1,KMAX+1):
    vc=ic=tc=0
    for r in range(1,1<<k,2):
        res=compute_descent_window(r,k)
        if res is None: ic+=1;total_i+=1
        elif res.get('terminal'): tc+=1
        elif res['valid']:
            vc+=1;total_v+=1
            if worst_v is None or res['threshold']>worst_v[2]['threshold']: worst_v=(k,r,res)
        else:
            ic+=1;total_i+=1
            if worst_i is None or res['threshold']>worst_i[2]['threshold']: worst_i=(k,r,res)
    v_by_k[k]=vc;i_by_k[k]=ic;t_by_k[k]=tc

print(f"  {'k':>3}  {'lanes':>7}  {'valid':>7}  {'invalid':>8}  {'terminal':>9}  {'%valid':>7}")
print("  " + "-"*50)
for k in range(1,KMAX+1):
    lanes = 1<<(k-1)
    pct   = 100.0*v_by_k[k]/lanes
    print(f"  {k:>3}  {lanes:>7,}  {v_by_k[k]:>7,}  {i_by_k[k]:>8,}  {t_by_k[k]:>9,}  {pct:>6.1f}%")

inv16=i_by_k[16]; val16=v_by_k[16]
max_valid_thr = worst_v[2]['threshold'] if worst_v else 0
print()
print(f"  Total valid: {total_v:,}   Total invalid: {total_i:,}")
if worst_v: print(f"  Worst valid  : r={worst_v[1]}, k={worst_v[0]}, c={worst_v[2]['c']}, threshold={worst_v[2]['threshold']}")
if worst_i: print(f"  Worst invalid: r={worst_i[1]}, k={worst_i[0]}, c={worst_i[2]['c']}, threshold={worst_i[2]['threshold']}")
print()
print(f"  k=16: {val16:,} valid  /  {inv16:,} invalid  ({100*val16/32768:.1f}% valid)")
print(f"  => {inv16:,} residue classes lack valid formulas at k=16.")
print(f"     Those formulas are only proven for n == r (mod 2^c) where c >> 16.")
print()

# ── [4] GAP ANALYSIS ─────────────────────────────────────────────────────────
print(SEP)
print("[4]  GAP ANALYSIS  -- n > bridge_limit with no valid symbolic coverage")
print(SEP)
BRIDGE_LIMIT = 200_001
print(f"  Empirical bridge limit : {BRIDGE_LIMIT:,}  (descent_bridge Part B)")
print(f"  Max threshold (valid)  : {max_valid_thr}")
print(f"  For the proof to be complete, every odd n > {BRIDGE_LIMIT:,} must")
print(f"  lie in at least one valid non-terminal lane with threshold < n.")
print()

gap_n = []; t0=time.time()
SCAN_END = BRIDGE_LIMIT + 200_000
for n in range(BRIDGE_LIMIT+2, SCAN_END, 2):
    covered,_,_,_ = has_valid_coverage(n)
    if not covered:
        gap_n.append(n)
        if len(gap_n)>=10: break
t_scan = time.time()-t0

if gap_n:
    print(f"  GAP CONFIRMED: uncovered n found within {SCAN_END-BRIDGE_LIMIT:,} values above bridge_limit")
    print(f"  First gap values: {gap_n[:5]}")
    print()
    n_ex = gap_n[0]
    print(f"  Coverage detail for n = {n_ex:,}:")
    for k2 in range(1, KMAX+1):
        r2 = n_ex % (1<<k2)
        if r2%2==0: continue
        res2b = compute_descent_window(r2, k2)
        if res2b is None: tag="MISSING"
        elif res2b.get('terminal'): tag="terminal (not useful for large n)"
        else: tag=f"c={res2b['c']}, threshold={res2b['threshold']}, valid={res2b['valid']}"
        print(f"    k={k2:>2}: r={r2:<8} {tag}")
    print()
    print(f"  WHY: orbits like 7,31,63,127,... climb far before descending.")
    print(f"  They need c >> k halvings before 2^c > a = 3^j (the descent condition).")
    print(f"  No k<=16 provides a valid formula for these orbit types.")
    print()
    print(f"  IMPACT: n = {n_ex:,} (and infinitely many similar n) are NOT")
    print(f"  covered by descent_bridge.py's certificate.  The 'CERTIFICATE")
    print(f"  COMPLETE' verdict in that script is PREMATURE.")
    print()
    print(f"  TO CLOSE THE GAP:")
    print(f"    A) Increase KMAX_SYM until ALL lanes are valid (may need k~64+)")
    print(f"    B) Increase VERIFY_LIMIT to cover all hard-orbit n up to valid")
    print(f"       symbolic coverage (requires knowing that cutoff)")
    print(f"    C) Separate proof that hard-orbit n must eventually descend")
    print(f"       (the actual Collatz conjecture for those residue classes)")
else:
    print(f"  No gaps found in scan window. (scan time {t_scan:.1f}s)")
print()

# ── SUMMARY ──────────────────────────────────────────────────────────────────
print(SEP)
print("AUDIT SUMMARY")
print(SEP)
print()
print(f"  [1] peakMod12 in {{4,10}}             : PROVEN ALGEBRAICALLY {'✓' if ok1 else '✗'}")
print(f"  [2] Formula correct for valid lanes  : {'CONFIRMED ✓' if sec2_ok else 'FAILED ✗'}")
print(f"  [3] Invalid lanes at k=16            : {inv16:,} / 32,768  ({100*inv16/32768:.1f}%)")
print(f"  [4] Gap above bridge_limit confirmed : {'YES ✗' if gap_n else 'NOT FOUND ✓'}")
print()
print("  PROOF STATUS:")
print("  ┌─ PROVEN (algebraic) ──────────────────────────────────────────┐")
print("  │  Even n descends: T(n)=n/2 < n  (trivial)                    │")
print("  │  peakMod12 in {4,10} for all odd n                           │")
print("  │  Lane 2 always closes to odd (Law 41)                        │")
print("  ├─ CERTIFICATE-BACKED (code-verified) ─────────────────────────┤")
print("  │  All odd n <= 200,001 descend  (empirical, Part B)           │")
print(f"  │  {val16:,}/32768 k=16 residue classes have valid formulas     │")
print(f"  │  Max valid-lane threshold = {max_valid_thr}  (low, good)              │")
print("  ├─ GAP (not closed by this workbench) ─────────────────────────┤")
print(f"  │  {inv16:,} hard residue classes at k=16 need c >> 16 halvings  │")
print("  │  Large n in these classes NOT proven to descend here         │")
print("  └───────────────────────────────────────────────────────────────┘")
print()
print("  CORRECT STATEMENT:")
print("  This workbench provides a PARTIAL certificate-backed termination")
print("  argument. Most residue classes are covered. A gap exists for hard-")
print("  orbit residue classes where c >> k. Formal peer review required.")
print("  DO NOT CLAIM 'Collatz solved.'")
