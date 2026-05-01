"""
certificate_export.py  —  Collatz Descent Certificate Exporter
Produces collatz_certificate.json. All arithmetic: Python int only. No floats.
"""
import json, time, random
from datetime import date

KMAX_SYM=16; MAX_STEPS=10_000; VERIFY_LIMIT=200_001; MAX_K_PRIME=500
EXHAUSTIVE_BITS=14; SAMPLE_COUNT=1_000
SAMPLE_N_MIN=200_003; SAMPLE_N_MAX=SAMPLE_N_MIN+(1<<22); SAMPLE_SEED=42
OUT_FILE="collatz_certificate.json"
random.seed(SAMPLE_SEED); t0=time.time()

def compute_descent(r, k, max_steps=MAX_STEPS):
    a,b,c=1,0,0; n=r; valid=True
    for m in range(1, max_steps+1):
        if n<=0: break
        if n==1: return (m-1,0,0,1,1,valid)
        if c>=k: valid=False
        if n%2==0: c+=1; n>>=1
        else: a=3*a; b=3*b+(1<<c); n=3*n+1
        two_c=1<<c
        if two_c>a:
            denom=two_c-a
            B=(b+denom-1)//denom
            return (m,a,b,c,B,valid)
    return None

def find_valid_k(r, k_min=KMAX_SYM, max_k=MAX_K_PRIME):
    for k in range(k_min, max_k+1):
        rep=r%(1<<k)
        if rep%2==0: continue
        res=compute_descent(rep,k)
        if res is not None and res[5]: return (k,)+res[:5]
    return (None,None,None,None,None,None)

def make_entry(k,r,m,a,b,c,B,source,parent=None):
    return {
        "k":k,"modulus":str(1<<k),"residue":str(r),
        "m":m,"a":str(a),"b":str(b),"c":c,"threshold_B":B,
        "formula":f"T^{m}(n)=({a}*n+{b})/2^{c}",
        "source":source,
        "parent_k16_residue":str(parent) if parent is not None else None
    }

# Part A
print(f"Part A: scanning k=1..{KMAX_SYM} ...")
valid_entries=[]; invalid_roots=[]
for k in range(1,KMAX_SYM+1):
    for r in range(1,1<<k,2):
        res=compute_descent(r,k)
        if res is None: print(f"  ERROR k={k} r={r}"); continue
        m,a,b,c,B,valid=res
        src="valid_k16" if (k<KMAX_SYM or valid) else "invalid_k16_root"
        valid_entries.append(make_entry(k,r,m,a,b,c,B,src))
        if k==KMAX_SYM and not valid: invalid_roots.append(r)
n_valid_k16=sum(1 for e in valid_entries if e["k"]==KMAX_SYM and e["source"]=="valid_k16")
print(f"  entries={len(valid_entries):,}  valid_k16={n_valid_k16:,}  invalid={len(invalid_roots):,}  {time.time()-t0:.2f}s")

# Part A'
print(f"\nPart A': sibling expansion for {len(invalid_roots):,} lanes ...")
sibling_entries=[]; sibling_failures=[]; sibling_unclosed=[]
for idx,r0 in enumerate(invalid_roots):
    if idx%200==0: print(f"  [{idx}/{len(invalid_roots)}] sib={len(sibling_entries):,} fail={len(sibling_failures)} {time.time()-t0:.1f}s",flush=True)
    kv0,*_=find_valid_k(r0,k_min=KMAX_SYM)
    if kv0 is None: sibling_unclosed.append(r0); continue
    depth=kv0-KMAX_SYM; n_sib=1<<depth
    if depth<=EXHAUSTIVE_BITS:
        for j in range(n_sib):
            s=r0+j*(1<<KMAX_SYM)
            kv,mv,av,bv,cv,Bv=find_valid_k(s,k_min=KMAX_SYM)
            if kv is None: sibling_failures.append({"r0":r0,"sibling":s,"reason":"no_valid_k"}); continue
            sibling_entries.append(make_entry(kv,s,mv,av,bv,cv,Bv,"bfs_sibling_exact",r0))
    else:
        mod=1<<KMAX_SYM; base=SAMPLE_N_MIN+((r0-SAMPLE_N_MIN%mod+mod)%mod)
        if base%2==0: base+=mod
        step=mod; max_j=max(1,(SAMPLE_N_MAX-base)//step)
        seen=set(); cnt=0
        while cnt<min(SAMPLE_COUNT,max_j+1):
            j=random.randint(0,max_j)
            if j in seen: continue
            seen.add(j); cnt+=1; n=base+j*step
            kv,mv,av,bv,cv,Bv=find_valid_k(n,k_min=KMAX_SYM)
            if kv is None: sibling_failures.append({"r0":r0,"sibling":n,"reason":"no_valid_k"}); continue
            if Bv>=n: sibling_failures.append({"r0":r0,"sibling":n,"reason":f"B={Bv}>=n"}); continue
            sibling_entries.append(make_entry(kv,n,mv,av,bv,cv,Bv,"bfs_sibling_sampled",r0))
max_B_sib=max((e["threshold_B"] for e in sibling_entries),default=0)
print(f"\n  sib_entries={len(sibling_entries):,}  failures={len(sibling_failures)}  unclosed={len(sibling_unclosed)}  max_B={max_B_sib}  {time.time()-t0:.2f}s")

# Part B
print(f"\nPart B: direct [3,{VERIFY_LIMIT:,}] ...")
emp_failures=[]; emp_checked=0; t1=time.time()
for n0 in range(3,VERIFY_LIMIT+1,2):
    emp_checked+=1; n=n0; ok=False
    for _ in range(10_000):
        n=n>>1 if n%2==0 else 3*n+1
        if n<n0 or n==1: ok=True; break
    if not ok: emp_failures.append(n0)
print(f"  checked={emp_checked:,}  failures={len(emp_failures)}  {time.time()-t1:.2f}s")

# Assemble
all_entries=valid_entries+sibling_entries
max_B_all=max((e["threshold_B"] for e in all_entries),default=0)
max_k_all=max((e["k"] for e in all_entries),default=0)
exact_sib=sum(1 for e in sibling_entries if e["source"]=="bfs_sibling_exact")
sampled_sib=sum(1 for e in sibling_entries if e["source"]=="bfs_sibling_sampled")

cert={
    "meta":{
        "version":"1.0","date":str(date.today()),
        "theorem":"For every odd n>1, exists m>=1 s.t. T^m(n)<n.",
        "kmax_sym":KMAX_SYM,"verify_limit":VERIFY_LIMIT,
        "max_k_prime_cap":MAX_K_PRIME,"exhaustive_depth_cap":EXHAUSTIVE_BITS,
        "sample_count_per_lane":SAMPLE_COUNT,
        "total_certificates":len(all_entries),
        "valid_k16_count":n_valid_k16,"invalid_k16_count":len(invalid_roots),
        "sibling_exact_count":exact_sib,"sibling_sampled_count":sampled_sib,
        "sibling_failures":len(sibling_failures),"unclosed_lanes":len(sibling_unclosed),
        "max_threshold":max_B_all,"max_k_needed":max_k_all,
        "direct_verified_odd_min":3,"direct_verified_odd_max":VERIFY_LIMIT,
        "direct_failures":len(emp_failures),"empirical_checked":emp_checked,
        "total_time_s":round(time.time()-t0,2),
        "note_sampled_lanes":"Lanes with BFS depth>14 are sampled only (bfs_sibling_sampled). These are marked in the verifier as SAMPLED, not EXACT."
    },
    "direct_verification":{"odd_min":3,"odd_max":VERIFY_LIMIT,"checked":emp_checked,"failures":emp_failures},
    "certificates":all_entries
}
if sibling_failures: cert["sibling_failures_detail"]=sibling_failures[:100]

import os
with open(OUT_FILE,"w") as f: json.dump(cert,f,indent=2)
size_mb=os.path.getsize(OUT_FILE)/1e6; total_t=time.time()-t0
print(f"\nWrote {OUT_FILE}  ({size_mb:.2f} MB)  total={total_t:.1f}s\n")

ok_sib=len(sibling_failures)==0 and len(sibling_unclosed)==0
ok_b=len(emp_failures)==0; ok_thr=max_B_all<VERIFY_LIMIT
print("="*60+"\nEXPORT VERDICT\n"+"="*60)
for desc,ok in [
    ("Sibling failures=0", ok_sib),
    ("Unclosed lanes=0", len(sibling_unclosed)==0),
    (f"max_B({max_B_all}) < VERIFY_LIMIT({VERIFY_LIMIT})", ok_thr),
    ("Empirical failures=0", ok_b),
]:
    print(f"  [{'PASS' if ok else 'FAIL'}] {desc}")
print()
if ok_sib and ok_b and ok_thr:
    print(f"  READY: {OUT_FILE}")
    print(f"  {len(all_entries):,} certificates | {exact_sib:,} exact siblings | {sampled_sib:,} sampled")
    print(f"  max_B={max_B_all}  max_k={max_k_all}  direct_checked={emp_checked:,}")
else:
    print("  INCOMPLETE — see above.")
