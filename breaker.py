import random, time, sys

MAX_STEPS    = 2_000_000
WAVE_TIMEOUT = 120
PROGRESS_INT = 25_000
STEP_RECORD  = 344
AMP_RECORD   = 670_861_992_075

ANCHORS = {1,2,4,8,16,40,80,184,3077,9232,6909950,459624658,171640888,112627739}
BREAKS  = {k:0 for k in range(1,8)}
RECORDS = {'steps':STEP_RECORD,'amp':AMP_RECORD,'step_seed':0,'amp_seed':0}
tested  = 0
t0      = time.time()

def route(seed):
    n = seed; steps = 0; peak = seed
    odd = even = odd_run = max_odd_run = 0
    peak_mod12 = int(seed % 12)
    while n != 1 and steps < MAX_STEPS:
        if n & 1 == 0:
            n >>= 1; even += 1; odd_run = 0
        else:
            n = 3*n+1; odd += 1; odd_run += 1
            if odd_run > max_odd_run: max_odd_run = odd_run
        steps += 1
        if n > peak: peak = n; peak_mod12 = int(peak % 12)
    if n == 1 or n in ANCHORS: door = 'ANCHOR/COLLECTOR'
    elif n < seed: door = 'BELOW-SELF'
    else: door = 'UNKNOWN'
    return {'door':door,'steps':steps,'peak_mod12':peak_mod12,
            'max_odd_run':max_odd_run,'amp':peak//seed if seed>0 else 1}

def has_cycle(seed):
    if seed > 10_000_000: return False
    def s(x): return x>>1 if x&1==0 else 3*x+1
    slow = fast = seed
    for _ in range(200_000):
        slow = s(slow); fast = s(s(fast))
        # Reached terminal — no non-trivial cycle
        if fast <= 4 or slow <= 4: return False
        if slow == fast: return True
    return False

def check(seed, label=''):
    global tested
    if seed < 3 or seed % 2 == 0: return
    tested += 1
    if tested % PROGRESS_INT == 0:
        e = time.time()-t0
        print(f"  ... {tested:,} | {e:.0f}s | {tested/e:.0f}/s | steps_rec={RECORDS['steps']} | breaks={sum(BREAKS.values())}", flush=True)
    if has_cycle(seed):
        BREAKS[2] += 1
        print(f"\n{'!'*60}\n  CYCLE  seed={seed} ({label})\n{'!'*60}\n", flush=True)
        return
    r = route(seed)
    broken = []
    if r['door'] == 'UNKNOWN':
        broken.append(f"[1] UNKNOWN door steps={r['steps']}"); BREAKS[1]+=1
    if r['door'] not in ('BELOW-SELF','ANCHOR/COLLECTOR'):
        broken.append(f"[3] ESCAPE door={r['door']}"); BREAKS[3]+=1
    if r['steps'] > RECORDS['steps']:
        broken.append(f"[4] STEP RECORD {r['steps']} > {RECORDS['steps']}")
        RECORDS['steps']=r['steps']; RECORDS['step_seed']=seed; BREAKS[4]+=1
    if r['amp'] > RECORDS['amp']:
        broken.append(f"[5] AMP RECORD {r['amp']:.3e}")
        RECORDS['amp']=r['amp']; RECORDS['amp_seed']=seed; BREAKS[5]+=1
    if r['peak_mod12'] not in (4,10):
        broken.append(f"[6] MOD12={r['peak_mod12']} expected 4 or 10"); BREAKS[6]+=1
    if r['max_odd_run'] > 1:
        broken.append(f"[7] ODD RUN={r['max_odd_run']} > 1 !!!"); BREAKS[7]+=1
    if broken:
        print(f"\n{'!'*60}\n  ANOMALY seed={seed} ({label})", flush=True)
        for b in broken: print(f"    >> {b}")
        print(f"    steps={r['steps']} mod12={r['peak_mod12']} oddRun={r['max_odd_run']}\n{'!'*60}\n", flush=True)

def wave(name, seeds):
    w_start = time.time(); w = 0
    print(f"\nWave: {name}", flush=True)
    for seed, label in seeds:
        if time.time()-w_start > WAVE_TIMEOUT:
            print(f"  [timeout {WAVE_TIMEOUT}s — moving on]", flush=True); break
        check(seed, label); w += 1
    e = time.time()-w_start
    print(f"  done: {w} seeds | {e:.1f}s | hard={sum(BREAKS[k] for k in (1,2,3,6,7))} | steps_rec={RECORDS['steps']}", flush=True)

print("="*60+"\nCOLLATZ BREAKER — Adversarial Invariant Hunter\n"+"="*60)
print(f"MAX_STEPS={MAX_STEPS:,}  WAVE_TIMEOUT={WAVE_TIMEOUT}s\n")

# W1 — Mersenne
def gen_w1():
    for k in range(2,201): yield 2**k-1, f"M{k}"
wave("Mersenne 2^k-1 k=2..200", gen_w1())

# W2 — Near powers of 2
def gen_w2():
    for k in range(2,151):
        base = 2**k
        for d in (1,3,5,7,9,11,13,15):
            for n in (base-d, base+d):
                if n>2 and n%2==1: yield n, f"2^{k}+-{d}"
wave("Near-pow2 2^k+-1..15 k=2..150", gen_w2())

# W3 — Repunit decimals
def gen_w3():
    r = 1
    for _ in range(35):
        r = r*10+1
        if r%2==1 and r>2: yield r, f"rep{len(str(r))}"
wave("Repunit decimals", gen_w3())

# W4 — Dense-bit
def gen_w4():
    import functools
    for bits in range(20,81,5):
        for _ in range(300):
            n = (1<<bits)-1
            cuts = random.randint(0, bits//5)
            for _ in range(cuts):
                n &= ~(1 << random.randint(0, bits-2))
            yield n|1, f"{bits}b-dense"
wave("Dense-bit >=80% set 20-80bit", gen_w4())

# W5 — Sparse-bit
def gen_w5():
    for _ in range(2000):
        bits = random.randint(20,100)
        ns = random.randint(2,4)
        pos = sorted(random.sample(range(bits), min(ns,bits)))
        if pos: pos[0] = 0
        yield sum(1<<p for p in pos)|1, "sparse"
wave("Sparse-bit 2-4 bits 20-100bit", gen_w5())

# W6 — mod6=5 sweep (time-capped)
def gen_w6():
    for n in range(5, 10_000_006, 6): yield n, "mod6=5"
wave("mod6=5 sweep up to 10M (120s cap)", gen_w6())

# W7 — Random giants
def gen_w7():
    for _ in range(500):
        d = random.randint(25,60)
        n = random.randint(10**(d-1), 10**d-1) | 1
        yield n, f"{d}dig"
wave("Random giants 25-60 digits", gen_w7())

# W8 — Delay champions
def gen_w8():
    champs = [27,703,871,6171,77031,837799,8400511,63728127,3732423,
              100663295,1117065515,2880753225,4890328815,9780657631,
              2**46-1, 2**53-1, 2**61-1]
    for c in champs:
        if c % 2 == 0: c += 1
        if c > 2: yield c, "champ"
        for d in range(-100,101,2):
            n = c+d
            if n>2 and n%2==1: yield n, "near-champ"
wave("Delay champions + +-100 neighbors", gen_w8())

# W9 — Double-Mersenne
def gen_w9():
    for k in range(1,8): yield 2**(2**k)-1, f"DM{k}"
wave("Double-Mersenne 2^(2^k)-1 k=1..7", gen_w9())

# W10 — Near-Mersenne
def gen_w10():
    for k in range(10,81):
        base = 2**k-1
        for d in range(1,30,2):
            for n in (base-d, base+d):
                if n>2 and n%2==1: yield n, f"nM{k}+-{d}"
wave("Near-Mersenne 2^k-1 +-1..29 k=10..80", gen_w10())

# W11 — Factorial+1 / Primorial+1
def gen_w11():
    import math
    fac = 1
    for i in range(2,25):
        fac *= i
        if (fac+1)%2==1: yield fac+1, f"{i}!+1"
    pri = 1
    for p in [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47]:
        pri *= p
        if (pri+1)%2==1: yield pri+1, "prim+1"
wave("Factorial+1 / Primorial+1", gen_w11())

# W12 — 100-200 bit monsters
def gen_w12():
    for _ in range(500):
        bits = random.randint(100,200)
        n = random.getrandbits(bits) | 1 | (1<<(bits-1))
        yield n, f"{bits}b-mon"
wave("100-200 bit monsters (120s cap)", gen_w12())

# W13 — Alternating-bit
def gen_w13():
    for bits in range(10,121,2):
        n1 = sum(1<<i for i in range(0,bits,2))
        n2 = (~n1 & ((1<<bits)-1)) | 1
        for n in (n1, n2):
            if n>2 and n%2==1: yield n, f"alt_{bits}b"
wave("Alternating-bit 101010.../010101...", gen_w13())

# W14 — Arithmetic progressions
def gen_w14():
    for base in range(1,20):
        pw = 10
        for k in range(1,200):
            n = base*pw+1
            if n%2==1 and n>2: yield n, f"{base}x10^{k}+1"
            pw *= 10
wave("Arithmetic progressions base*10^k+1 (120s cap)", gen_w14())

# Final
elapsed = time.time()-t0
print("\n"+"="*60+"\nBREAKER COMPLETE\n"+"="*60)
print(f"Tested : {tested:,}  |  {elapsed:.1f}s ({elapsed/60:.1f}m)  |  {tested/elapsed:.0f}/s")
print(f"Step record : {RECORDS['steps']}  seed={RECORDS['step_seed']}")
print(f"Amp  record : {RECORDS['amp']:.6e}  seed={RECORDS['amp_seed']}\n")
labels = {1:"UNKNOWN door",2:"CYCLE",3:"ESCAPE",
          4:"Step record (soft)",5:"Amp record (soft)",
          6:"peakMod12 not in {4,10}",7:"maxOddRun > 1"}
hard = False
for k,lbl in labels.items():
    soft=k in(4,5); cnt=BREAKS[k]
    sym="0 ✅" if cnt==0 else (f"{cnt} ⚠️" if soft else f"{cnt} ❌")
    if not soft and cnt>0: hard=True
    print(f"  [{k}] {lbl:<40} {sym}")
print()
print("✅  NO HARD VIOLATIONS." if not hard else "❌  HARD VIOLATIONS — see above.")
