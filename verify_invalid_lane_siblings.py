"""
verify_invalid_lane_siblings.py  v2  — per-sibling valid-k search
"""
import random, time
from collections import Counter

K_START=16; MAX_STEPS=10_000; MAX_K=500
VERIFY_LIMIT=200_001; EXHAUSTIVE_BITS=14
SAMPLE_COUNT=1_000; SAMPLE_N_MIN=200_003
SAMPLE_N_MAX=SAMPLE_N_MIN+(1<<22); SAMPLE_SEED=42
random.seed(SAMPLE_SEED)

def find_valid_k(r, k_min=K_START):
    for k in range(k_min, MAX_K+1):
        rep = r % (1<<k)
        if rep%2==0: continue
        a,b,c=1,0,0; n=rep; valid=True; found=None
        for m in range(1,MAX_STEPS+1):
            if n<=0: break
            if n==1:
                found={'m':m-1,'a':0,'b':0,'c':1,'threshold':1,'valid':True}; break
            if c>=k: valid=False
            if n%2==0: c+=1; n>>=1
            else: a=3*a; b=3*b+(1<<c); n=3*n+1
            if (1<<c)>a:
                d=(1<<c)-a; thr=b//d+1
                found={'m':m,'a':a,'b':b,'c':c,'threshold':thr,'valid':valid}; break
        if found and found['valid']: return k,found
    return None,None

t0=time.time()
print("="*68)
print("INVALID LANE SIBLING AUDIT  v2")
print("="*68)
print(f"\nPhase 1: collecting invalid k={K_START} lanes...")

invalid_lanes=[]
for r0 in range(1,1<<K_START,2):
    a,b,c=1,0,0; n=r0; valid16=True; closed=False
    for _ in range(MAX_STEPS):
        if n<=0 or n==1: closed=True; break
        if c>=K_START: valid16=False
        if n%2==0: c+=1; n>>=1
        else: a=3*a; b=3*b+(1<<c); n=3*n+1
        if (1<<c)>a: closed=True; break
    if not closed or valid16: continue
    k2,_=find_valid_k(r0,k_min=K_START)
    invalid_lanes.append((r0, k2 if k2 else -1))

print(f"  {len(invalid_lanes):,} invalid lanes  ({time.time()-t0:.2f}s)")
k2d=Counter(k2 for _,k2 in invalid_lanes)
for k2 in sorted(k2d):
    ns=(1<<(k2-K_START)) if k2>0 else 0
    tag="EXACT" if (k2-K_START)<=EXHAUSTIVE_BITS else "SAMPLED"
    print(f"  k2={k2:>3}  n={k2d[k2]:>5}  sib={ns:>14,}  [{tag}]")

print(f"\nPhase 2: sibling verification...")
print(f"  EXACT when depth<={EXHAUSTIVE_BITS}, SAMPLED otherwise ({SAMPLE_COUNT}/lane)")
print()

el=es=sl=sc=0
mt_e=mt_s=0; we=ws=None
fe=[]; fs=[]; unc=[]

for idx,(r0,k2) in enumerate(invalid_lanes):
    if idx%200==0:
        print(f"  {idx:,}/{len(invalid_lanes):,} | {time.time()-t0:.1f}s | e_sib={es:,} s_chk={sc:,} | fe={len(fe)} fs={len(fs)}",flush=True)
    if k2<0: unc.append(r0); continue
    depth=k2-K_START; n_sib=1<<depth
    if depth<=EXHAUSTIVE_BITS:
        el+=1
        for j in range(n_sib):
            s=r0+j*(1<<K_START); es+=1
            kv,res=find_valid_k(s,k_min=K_START)
            if kv is None: fe.append((s,'no_valid_k')); continue
            thr=res['threshold']
            if thr>VERIFY_LIMIT: fe.append((s,f'thr={thr}')); continue
            if thr>mt_e: mt_e=thr; we=(s,kv,res)
    else:
        sl+=1; mod=1<<K_START
        base=SAMPLE_N_MIN+((r0-SAMPLE_N_MIN%mod+mod)%mod)
        if base%2==0: base+=mod
        step=mod; max_j=max(1,(SAMPLE_N_MAX-base)//step)
        seen=set(); cnt=0
        while cnt<min(SAMPLE_COUNT,max_j+1):
            j=random.randint(0,max_j)
            if j in seen: continue
            seen.add(j); cnt+=1; n=base+j*step; sc+=1
            kv,res=find_valid_k(n,k_min=K_START)
            if kv is None: fs.append((n,'no_valid_k')); continue
            thr=res['threshold']
            if thr>=n: fs.append((n,f'thr={thr}>=n')); continue
            if thr>mt_s: mt_s=thr; ws=(n,kv,res)

print(f"\n{'='*68}\nRESULTS\n{'='*68}")
print(f"  Invalid k={K_START} lanes : {len(invalid_lanes):,}")
print(f"  Unclosed              : {len(unc):,}")
print(f"\n  EXACT: {el:,} lanes, {es:,} siblings, {len(fe)} failures, max_thr={mt_e:,}")
if we: print(f"    worst: s={we[0]}  k'={we[1]}  thr={we[2]['threshold']}")
print(f"\n  SAMPLED: {sl:,} lanes, {sc:,} checks, {len(fs)} failures, max_thr={mt_s:,}")
if ws: print(f"    worst: n={ws[0]}  k'={ws[1]}  thr={ws[2]['threshold']}")
if fe: print(f"\n  Exact failures:"); [print(f"    {x}") for x in fe[:5]]
if fs: print(f"\n  Sampled failures:"); [print(f"    {x}") for x in fs[:5]]

pe=len(fe)==0 and len(unc)==0 and mt_e<=VERIFY_LIMIT
ps=len(fs)==0 and mt_s<=VERIFY_LIMIT

print(f"\n{'='*68}\nVERDICT\n{'='*68}")
for desc,ok,det in [
    ("Exact: 0 failures",pe,f"{len(fe)} failures"),
    ("Exact: max_thr<=VERIFY_LIMIT",mt_e<=VERIFY_LIMIT,f"max={mt_e:,}"),
    ("Sampled: 0 failures",ps,f"{len(fs)} failures"),
    ("Sampled: max_thr<=VERIFY_LIMIT",mt_s<=VERIFY_LIMIT,f"max={mt_s:,}"),
]:
    print(f"  [{'PASS' if ok else 'FAIL'}] {desc:<46} ({det})")
print(f"\n  Total time: {time.time()-t0:.2f}s")
print()
if pe and ps:
    print(f"  EXACT: PROVEN — {es:,} siblings, all thr<={mt_e}")
    if sl: print(f"  SAMPLED: EMPIRICAL — {sc:,} checks, all thr<={mt_s}<<n")
else:
    print("  FAIL — see above.")
