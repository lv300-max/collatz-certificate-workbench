"""
deep_parent_margin_certificate.py
BFS parity tree — universal margin certificate for all depth-19+ open parents.
No sampling. 100% sibling coverage per node (verified at runtime).

STATE: (n_val, o, c, b, bits_free)
  stride_power = KMAX + (depth - bits_free) - c
  Branch when stride_power == 0 and bits_free > 0:
    bit=0: n_val unchanged;  bit=1: n_val += 3^o
  Terminate when 2^c > 3^o  ->  formula (o,c,b,B) covers 2^bits_free siblings.
"""
import time, sys, math, json
from collections import defaultdict, deque

LOG2_3        = math.log2(3)
KMAX          = 16
MAX_STEPS     = 30_000
MAX_BFS_NODES = 5_000_000
B_LIMIT       = 200_001
t0            = time.time()

def bfs_parity_tree(r0, depth, max_nodes=MAX_BFS_NODES):
    queue = deque()
    queue.append((r0, 0, 0, 0, depth))
    formula_map      = {}
    siblings_covered = 0
    siblings_open    = 0
    total_nodes      = 0
    min_delta        = float('inf')
    max_B            = 0
    violations       = []
    while queue:
        n_val, o, c, b, bits_free = queue.popleft()
        total_nodes += 1
        if total_nodes > max_nodes:
            siblings_open += 1 << bits_free
            continue
        resolved = False
        for _ in range(MAX_STEPS):
            # termination
            if c > o * LOG2_3 + 0.5:
                a_int = pow(3, o); two_c = 1 << c
                if two_c > a_int:
                    B     = (b + two_c - a_int - 1) // (two_c - a_int)
                    count = 1 << bits_free
                    delta = c - o * LOG2_3
                    key   = (o, c, b)
                    if key not in formula_map:
                        formula_map[key] = {'B_max': B, 'count': count}
                    else:
                        fs = formula_map[key]
                        fs['count'] += count
                        if B > fs['B_max']: fs['B_max'] = B
                    siblings_covered += count
                    if delta < min_delta: min_delta = delta
                    if B > max_B:        max_B = B
                    if delta <= 0 or B > B_LIMIT:
                        violations.append({'r0':r0,'o':o,'c':c,'B':B,'delta':delta})
                    resolved = True
                    break
            # branch check
            stride_power = KMAX + (depth - bits_free) - c
            if stride_power == 0 and bits_free > 0:
                a_int = pow(3, o)
                queue.append((n_val,         o, c, b, bits_free - 1))
                queue.append((n_val + a_int, o, c, b, bits_free - 1))
                resolved = True; break
            # collatz step
            if n_val & 1 == 0: n_val >>= 1; c += 1
            else: b = 3*b + (1 << c); n_val = 3*n_val + 1; o += 1
        if not resolved:
            siblings_open += 1 << bits_free
    return {'formula_map':formula_map,'siblings_covered':siblings_covered,
            'siblings_open':siblings_open,'total_nodes':total_nodes,
            'min_delta':min_delta,'max_B':max_B,'violations':violations}

# Load parents
print("="*76)
print("DEEP PARENT MARGIN CERTIFICATE  —  BFS Parity Tree, No Sampling")
print("="*76)
print(f"  log2(3)={LOG2_3:.10f}  B_LIMIT={B_LIMIT}  MAX_BFS_NODES={MAX_BFS_NODES:,}\n")
print("Loading certificate ...", flush=True)
data  = json.load(open("collatz_certificate.json"))
certs = data["certificates"]
roots_by_r0 = {}
for entry in certs:
    if entry.get("source") == "invalid_k16_root":
        r0 = int(entry["residue"])
        if r0 not in roots_by_r0: roots_by_r0[r0] = entry

open_parents = []
for r0, root in roots_by_r0.items():
    c_par = int(root["c"]); depth = c_par - KMAX
    if depth >= 19: open_parents.append((r0, c_par, depth))
open_parents.sort(key=lambda x: (x[2], x[0]))

depth_dist = defaultdict(int)
for _,_,d in open_parents: depth_dist[d] += 1
print(f"  {len(open_parents)} open parents  depth range {min(depth_dist)}..{max(depth_dist)}")
for d in sorted(depth_dist)[:25]:
    print(f"    depth={d:4d}: {depth_dist[d]:4d} parents  ({1<<d:,} sibs each)")
print()

# Per-parent loop
all_results=[]; total_closed=0; total_open=0; pclosed=0; ppartial=0
global_min_delta=float('inf'); global_max_B=0; any_viol=False

print("="*90)
print(f"{'#':>5} {'r0':>6} {'dep':>4} {'mode':>12} {'min_d':>10} {'maxB':>6} "
      f"{'forms':>8} {'nodes':>9} {'cov%':>6} {'t':>5}")
print("-"*90)

for idx,(r0,c_par,depth) in enumerate(open_parents,1):
    t_par = time.time()
    res   = bfs_parity_tree(r0, depth)
    ela   = time.time()-t_par
    sc=res['siblings_covered']; so=res['siblings_open']
    ns=1<<depth; tn=res['total_nodes']; md=res['min_delta']
    mB=res['max_B']; viols=res['violations']; nf=len(res['formula_map'])
    mode='EXACT_BFS' if so==0 else 'BFS_OFLOW'
    if viols: any_viol=True; status='VIOLATION'
    elif so==0: status='CLOSED'
    else: status='PARTIAL'
    if md<global_min_delta: global_min_delta=md
    if mB>global_max_B: global_max_B=mB
    total_closed+=sc; total_open+=so
    if so==0: pclosed+=1
    else: ppartial+=1
    all_results.append({'r0':r0,'depth':depth,'c_par':c_par,'mode':mode,
        'min_delta':md,'max_B':mB,'n_formulas':nf,'siblings_covered':sc,
        'siblings_open':so,'violations':viols,'elapsed':ela})
    print(f"{idx:5d} {r0:6d} {depth:4d} {mode:>12} {md:10.6f} {mB:6d} "
          f"{nf:8,} {tn:9,} {sc/ns*100:6.1f}% {ela:5.1f}  {status}", flush=True)
    if viols:
        for v in viols: print(f"      VIOLATION: {v}", flush=True)

# Summary
ela_total = time.time()-t0
print()
print("="*76)
print("GRAND SUMMARY")
print("="*76)
print(f"  Parents analyzed               : {len(open_parents)}")
print(f"  CLOSED (exact BFS)             : {pclosed}")
print(f"  PARTIAL (BFS overflow)         : {ppartial}")
print()
print(f"  Total siblings certified (BFS) : {total_closed:,}")
print(f"  Total siblings sampled only    : 0  (BFS is exact)")
print(f"  Total siblings UNCOVERED       : {total_open:,}")
print()
print(f"  Global min delta = c - o*log2(3): {global_min_delta:.8f}")
print(f"  Global max B                    : {global_max_B}")
print(f"  B < B_LIMIT={B_LIMIT}            : {'YES' if global_max_B < B_LIMIT else 'NO'}")
print()
tight=sorted(all_results,key=lambda x:x['min_delta'])[:20]
print("  Tightest-margin parents (top 20):")
print(f"  {'r0':>6} {'dep':>4} {'min_delta':>12} {'max_B':>7} {'mode':>12} {'forms':>9}")
for r in tight:
    print(f"  {r['r0']:6d} {r['depth']:4d} {r['min_delta']:12.8f} {r['max_B']:7d} "
          f"{r['mode']:>12} {r['n_formulas']:9,}")
print()
if any_viol:
    print("HARD VIOLATIONS FOUND.")
elif ppartial==0:
    print(f"ALL {pclosed} PARENTS FULLY CERTIFIED BY EXACT BFS.")
    print(f"  c/o > log2(3) for EVERY sibling of EVERY analyzed parent.")
    print(f"  B <= {global_max_B} for every formula.  Proof gap CLOSED.")
else:
    print(f"PARTIAL: {pclosed}/{len(open_parents)} parents closed.  {ppartial} still have open siblings.")
    for r in all_results:
        if r['siblings_open']>0:
            print(f"  r0={r['r0']} depth={r['depth']} open={r['siblings_open']:,}")
print(f"\nTotal time: {ela_total:.1f}s ({ela_total/60:.1f}min)")
