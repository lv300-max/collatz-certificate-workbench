"""
deep_sibling_closure_law.py
============================
Structural analysis and systematic exact closure of deep sibling families.

GOAL: For each invalid k=16 parent r0 with depth d = k' - 16 > 14, prove or
      disprove that ALL 2^d sibling residue classes at level k' have valid
      descent certificates.

METHODS (in order of rigor):
  1. EXACT ENUMERATION  — depth 15-17 first, then depth 18 when enabled
  2. SYMBOLIC TREE       — branch-and-bound parity proof for depth 19+
                           targeting c/o > log2(3)
  3. REDUCTION THEOREM   — closure of any deep sibling is equivalent to
                           the Collatz descent property for an arithmetic progression

STRUCTURE OF ARGUMENT (symbolic):
  Let r0 be an invalid parent at k=16 with certificate at level k'=16+d.
  Siblings: s_j = r0 + j * 2^16  for j in [0, 2^d)

  Initial symbolic state: n = 2^16 * j + r0
  After m Collatz steps where the formula fires for r0:
      T^m(r0) = (a * r0 + b) / 2^c   with a < 2^c, c = c_par

  For any sibling n = 2^16 * j + r0 (j >= 0):
      T^m(n) = (a * (2^16*j + r0) + b) / 2^c    IF same parity sequence
             = (a*2^16*j + a*r0 + b) / 2^c

  Descent condition: T^m(n) < n
      a*2^16*j + a*r0 + b < 2^c * (2^16*j + r0)
      j * 2^16 * (a - 2^c) < r0*(2^c - a) - b
  Since a < 2^c → (a - 2^c) < 0 → inequality flips:
      j > (b - r0*(2^c - a)) / (2^16*(2^c - a))  [negative RHS when b < r0*(2^c-a)]
  Since r0 > B = ceil(b/(2^c-a)) by the parent certificate, b < r0*(2^c-a), so
  the right side is negative, meaning j >= 0 suffices.

  THEREFORE: if the same parity sequence applies to ALL j in [0, 2^d), the parent's
  certificate covers ALL siblings at once, threshold B = ceil(b/(2^c-a)).

  BLOCKING CONDITION: c_par <= 16 → same path for all j → CLOSED.
  BRANCHING CONDITION: c_par > 16 → orbit reads bit c_par-1 > bit 15 →
      j's bit (c_par-16-1) determines the parity at step "first reading of bit c_par-1"
      → siblings with different j values can take DIFFERENT parity paths.

  For all 776 deep parents: c_par > 16.
  Therefore the direct affine argument fails.
  Siblings diverge from the parent's path and need individual analysis.

EQUIVALENCE THEOREM:
  Deep sibling closure at level k' is equivalent to:
    "Every odd n ≡ r0 (mod 2^16) has a valid Collatz descent certificate
     at some level k <= MAX_K_PRIME."
  
  This is a special case of the Collatz conjecture restricted to the arithmetic
  progression {r0 + t * 2^16 : t >= 0}.

  No random sampling is used here. A parent is closed only by exact sibling
  enumeration or by a symbolic branch certificate.
"""

import math
import os
import time

KMAX = 16
MAX_STEPS = 10_000
MAX_K_VALID = 500
EXACT_DEPTH_REQUIRED = int(os.environ.get("DEEP_CLOSER_EXACT_REQUIRED", "17"))
EXACT_DEPTH_OPTIONAL = int(os.environ.get("DEEP_CLOSER_EXACT_OPTIONAL", "18"))
RUN_DEPTH18_EXACT = os.environ.get("DEEP_CLOSER_SKIP_DEPTH18", "0") != "1"
B_LIMIT = 200_001
LOG2_3 = math.log2(3)
SYMBOLIC_MAX_STEPS = 10_000
SYMBOLIC_MAX_LEVEL = int(os.environ.get("DEEP_CLOSER_SYMBOLIC_MAX_LEVEL", "500"))
SYMBOLIC_MAX_NODES = int(os.environ.get("DEEP_CLOSER_SYMBOLIC_MAX_NODES", "2000000"))

t0 = time.time()

# ── Core functions ───────────────────────────────────────────────────────────

def compute_descent(r, k, max_steps=MAX_STEPS):
    a, b, c = 1, 0, 0; n = r; valid = True; odd_count = 0
    for m in range(1, max_steps + 1):
        if c >= k: valid = False
        if n % 2 == 0: c += 1; n >>= 1
        else: a = 3*a; b = 3*b + (1 << c); n = 3*n + 1; odd_count += 1
        two_c = 1 << c
        if two_c > a:
            return (m, a, b, c, (b + two_c - a - 1) // (two_c - a), valid, odd_count)
    return None

def find_valid_k(r, k_min=KMAX, max_k=MAX_K_VALID):
    for k in range(k_min, max_k + 1):
        rep = r % (1 << k)
        if rep % 2 == 0: continue
        res = compute_descent(rep, k)
        if res is not None and res[5]: return k, res
    return None, None

# ── Exact and symbolic closers ───────────────────────────────────────────────

def exact_enumerate_parent(r0, depth):
    n_sib = 1 << depth
    parent_fails = 0
    parent_max_k = 0
    parent_max_B = 0
    parent_min_delta = math.inf
    b_over_limit = []

    for j in range(n_sib):
        s = r0 + j * (1 << KMAX)
        kf, res = find_valid_k(s, k_min=KMAX, max_k=MAX_K_VALID)
        if kf is None:
            parent_fails += 1
            continue

        _, a, b, c, B, _, o = res
        delta = c - o * LOG2_3
        if delta < parent_min_delta:
            parent_min_delta = delta
        if kf > parent_max_k:
            parent_max_k = kf
        if B > parent_max_B:
            parent_max_B = B
        if B > B_LIMIT and len(b_over_limit) < 5:
            b_over_limit.append((s, kf, B))

    return {
        "closed": parent_fails == 0,
        "siblings": n_sib,
        "fails": parent_fails,
        "max_k": parent_max_k,
        "max_B": parent_max_B,
        "min_delta": parent_min_delta,
        "b_over_limit": b_over_limit,
    }

def branch_and_bound_parent(r0, depth):
    """
    Deterministic symbolic search over n = r0 (mod 2^16).

    Each stack node represents one residue class n = residue (mod 2^level)
    plus the affine prefix T^m(n) = (a*n + b) / 2^c. When c < level, the next
    parity is known for the whole class. When c >= level, the class is split on
    the next bit. A branch closes only when c - odd_count*log2(3) > 0.
    """
    stack = [(r0, KMAX, 1, 0, 0, 0, 0)]
    nodes = 0
    closed_branches = 0
    max_B = 0
    min_delta = math.inf
    delta_blockers = []
    b_over_limit = []
    open_branches = []

    while stack:
        residue, level, a, b, c, odd_count, steps = stack.pop()
        nodes += 1

        if nodes > SYMBOLIC_MAX_NODES:
            open_branches.append((residue, level, steps, c - odd_count * LOG2_3, "node_cap"))
            break
        if steps >= SYMBOLIC_MAX_STEPS:
            open_branches.append((residue, level, steps, c - odd_count * LOG2_3, "step_cap"))
            continue
        if level >= SYMBOLIC_MAX_LEVEL:
            open_branches.append((residue, level, steps, c - odd_count * LOG2_3, "level_cap"))
            continue

        delta = c - odd_count * LOG2_3
        if delta > 0:
            denom = (1 << c) - a
            B = (b + denom - 1) // denom
            closed_branches += 1
            if delta < min_delta:
                min_delta = delta
            if B > max_B:
                max_B = B
            if B > B_LIMIT and len(b_over_limit) < 10:
                b_over_limit.append((residue, level, steps, B, delta))
            continue

        if len(delta_blockers) < 10:
            delta_blockers.append((residue, level, steps, delta))

        if c >= level:
            stack.append((residue + (1 << level), level + 1, a, b, c, odd_count, steps))
            stack.append((residue, level + 1, a, b, c, odd_count, steps))
            continue

        parity = ((a * residue + b) >> c) & 1
        if parity == 0:
            stack.append((residue, level, a, b, c + 1, odd_count, steps + 1))
        else:
            stack.append((residue, level, 3 * a, 3 * b + (1 << c), c, odd_count + 1, steps + 1))

    return {
        "closed": not stack and not open_branches,
        "nodes": nodes,
        "closed_branches": closed_branches,
        "open_branches": open_branches,
        "max_B": max_B,
        "min_delta": min_delta,
        "delta_blockers": delta_blockers,
        "b_over_limit": b_over_limit,
        "target_depth": depth,
    }

# ── Build parent list ─────────────────────────────────────────────────────────

print("="*72)
print("DEEP SIBLING CLOSURE LAW")
print("="*72)
print()
print("Building deep parent list (depth > 14) ...")
parents = []
for r0 in range(1, 1 << KMAX, 2):
    res0 = compute_descent(r0, KMAX)
    if res0 is None or res0[5]: continue
    kv, res = find_valid_k(r0, k_min=KMAX)
    if kv is None: continue
    d = kv - KMAX
    if d > 14:
        parents.append((r0, kv, d, res[1], res[2], res[3], res[4]))  # r0,k',d,a,b,c,B
parents.sort(key=lambda x: x[2])
print(f"  Found {len(parents)} deep parents ({time.time()-t0:.1f}s)")
print()

# ── Exact enumeration: depth 15..17, then depth 18 if enabled ───────────────

exact_depth_cap = EXACT_DEPTH_OPTIONAL if RUN_DEPTH18_EXACT else EXACT_DEPTH_REQUIRED
exact_parents = [(r0, kv, d, a, b, c, B) for r0, kv, d, a, b, c, B in parents if d <= exact_depth_cap]
symbolic_parents = [(r0, kv, d, a, b, c, B) for r0, kv, d, a, b, c, B in parents if d > exact_depth_cap]

exact_closed = 0
exact_open = 0
exact_total_siblings = 0
exact_fails = 0
exact_max_k = 0
max_B = 0
min_delta = math.inf
max_depth_exact_closed = 0
b_over_limit = []
delta_nonpositive = []
closed_parent_ids = set()

print("EXACT ENUMERATION")
print(f"  Required depth cap : {EXACT_DEPTH_REQUIRED}")
print(f"  Depth 18 enabled   : {RUN_DEPTH18_EXACT}")
print(f"  Active depth cap   : {exact_depth_cap}")
print()

t_exact = time.time()
for depth in range(15, exact_depth_cap + 1):
    depth_parents = [p for p in parents if p[2] == depth]
    print(f"Depth {depth}: {len(depth_parents)} parents, {1 << depth:,} siblings each", flush=True)
    for idx, (r0, kv, d, a_par, b_par, c_par, B_par) in enumerate(depth_parents):
        result = exact_enumerate_parent(r0, d)
        exact_total_siblings += result["siblings"]
        exact_fails += result["fails"]
        max_B = max(max_B, result["max_B"])
        exact_max_k = max(exact_max_k, result["max_k"])
        if result["min_delta"] < min_delta:
            min_delta = result["min_delta"]
        b_over_limit.extend(result["b_over_limit"])

        if result["closed"]:
            exact_closed += 1
            closed_parent_ids.add(r0)
            max_depth_exact_closed = max(max_depth_exact_closed, d)
        else:
            exact_open += 1
            delta_nonpositive.append((r0, d, "exact_fail", result["fails"]))

        if idx % 10 == 0 or not result["closed"]:
            status = "CLOSED" if result["closed"] else f"OPEN({result['fails']} fails)"
            print(f"  [{idx+1:3d}/{len(depth_parents)}] r0={r0:8d} k'={kv:3d} "
                  f"max_k={result['max_k']:3d} max_B={result['max_B']:6d} "
                  f"min_delta={result['min_delta']:.6f} {status} "
                  f"({time.time()-t_exact:.0f}s)", flush=True)
    print()

print("EXACT RESULT")
print(f"  Exact parents closed : {exact_closed} / {len(exact_parents)}")
print(f"  Exact open parents   : {exact_open}")
print(f"  Total siblings       : {exact_total_siblings:,}")
print(f"  Failures             : {exact_fails}")
print(f"  Max depth closed     : {max_depth_exact_closed}")
print(f"  Max k needed         : {exact_max_k}")
print(f"  Max B                : {max_B}")
print(f"  Min delta            : {min_delta:.12f}")
print(f"  Time                 : {time.time() - t_exact:.1f}s")
print()

# ── Branch-and-bound parity proof for parents beyond exact cap ──────────────

print(f"SYMBOLIC BRANCH-AND-BOUND: depth > {exact_depth_cap}")
print(f"  Parents            : {len(symbolic_parents)}")
print(f"  Target             : c/o > log2(3) = {LOG2_3:.12f}")
print(f"  Node cap / parent  : {SYMBOLIC_MAX_NODES:,}")
print(f"  Level cap / branch : {SYMBOLIC_MAX_LEVEL}")
print()

symbolic_closed = 0
symbolic_open = 0
t_symbolic = time.time()

for idx, (r0, kv, depth, a_par, b_par, c_par, B_par) in enumerate(symbolic_parents):
    result = branch_and_bound_parent(r0, depth)
    max_B = max(max_B, result["max_B"])
    if result["min_delta"] < min_delta:
        min_delta = result["min_delta"]
    b_over_limit.extend(result["b_over_limit"])

    if result["closed"]:
        symbolic_closed += 1
        closed_parent_ids.add(r0)
    else:
        symbolic_open += 1
        if result["open_branches"]:
            delta_nonpositive.extend((r0, depth, *branch) for branch in result["open_branches"][:5])
        else:
            delta_nonpositive.extend((r0, depth, *branch) for branch in result["delta_blockers"][:5])

    if idx % 10 == 0 or result["closed"]:
        status = "CLOSED" if result["closed"] else f"OPEN({len(result['open_branches'])} blockers)"
        min_delta_text = "inf" if result["min_delta"] == math.inf else f"{result['min_delta']:.6f}"
        print(f"  [{idx+1:3d}/{len(symbolic_parents)}] r0={r0:8d} d={depth:3d} k'={kv:3d} "
              f"nodes={result['nodes']:8,} branches={result['closed_branches']:7,} "
              f"max_B={result['max_B']:6d} min_delta={min_delta_text} {status}",
              flush=True)

print()
print("SYMBOLIC RESULT")
print(f"  Symbolic parents closed : {symbolic_closed} / {len(symbolic_parents)}")
print(f"  Symbolic open parents   : {symbolic_open}")
print(f"  Time                    : {time.time() - t_symbolic:.1f}s")
print()

# ── Equivalence theorem ────────────────────────────────────────────────────

print("="*72)
print("EQUIVALENCE THEOREM (structural statement)")
print("="*72)
print(f"""
Theorem [Deep Sibling Closure ↔ Collatz Descent]:

  Let r0 be a deep invalid parent at k=16, with depth d = k' - 16.
  The following are equivalent:
  
  (A) Every sibling s_j = r0 + j*2^16 (j >= 0) has a valid descent certificate
      at some level k <= MAX_K_PRIME.

  (B) Every odd integer n in the arithmetic progression {{r0 + t*2^16 : t >= 0}}
      satisfies T^m(n) < n for some m (Collatz descent property).

  Proof sketch:
    (A) → (B): certificate at level k gives T^m(n mod 2^k, k) triggers with a < 2^c,
    so for all n > B in that class, T^m(n) < n. The small-n bridge must cover n ≤ B ≤ {B_LIMIT}.
    
    (B) → (A): if T^m(n) < n for some m, then the orbit prefix of length m has a
    specific (a,b,c) satisfying a < 2^c (since T^m(n) = (a*n+b)/2^c < n for all n > B).
    This certificate is valid at level k = c. So (A) holds.

  Conclusion:
    A parent is CLOSED here only if every depth-d sibling was exact-enumerated,
    or if the symbolic branch-and-bound search closed every branch with
    c - o*log2(3) > 0.
    
    Current deterministic status:
      - {exact_closed} of {len(exact_parents)} depth-≤{exact_depth_cap} parents: EXACTLY VERIFIED
      - {symbolic_closed} of {len(symbolic_parents)} depth>{exact_depth_cap} parents: SYMBOLICALLY CLOSED
      - {exact_open + symbolic_open} parents remain open
    
    Gap:
      The proof remains incomplete until every depth > 16 parent has either:
        A) exact sibling enumeration, or
        B) a symbolic parent-level certificate.
""")

# ── Final summary ─────────────────────────────────────────────────────────────

open_parents_left = len(parents) - len(closed_parent_ids)
min_delta_text = "inf" if min_delta == math.inf else f"{min_delta:.12f}"

print("="*72)
print("CLOSURE LAW SUMMARY")
print("="*72)
print(f"  Deep parents total          : {len(parents)}")
print(f"  Exact parents closed        : {exact_closed} / {len(exact_parents)}")
print(f"  Symbolic parents closed     : {symbolic_closed} / {len(symbolic_parents)}")
print(f"  Open parents left           : {open_parents_left}")
print(f"  Max depth exact closed      : {max_depth_exact_closed}")
print(f"  Exact siblings verified     : {exact_total_siblings:,}")
print(f"  Exact failures              : {exact_fails}")
print(f"  Max B                       : {max_B}")
print(f"  Min delta                   : {min_delta_text}")
print()
print("  Branches with delta <= 0:")
if delta_nonpositive:
    for item in delta_nonpositive[:10]:
        print(f"    {item}")
else:
    print("    none")
print()
print(f"  Branches/certificates with B > {B_LIMIT}:")
if b_over_limit:
    for item in b_over_limit[:10]:
        print(f"    {item}")
else:
    print("    none")
print()
if open_parents_left == 0:
    print("  OVERALL STATUS: COMPLETE")
else:
    print("  OVERALL STATUS: INCOMPLETE")
    print("  Reason: at least one depth >16 parent lacks exact enumeration or a symbolic certificate.")
print(f"\n  Total time: {time.time()-t0:.1f}s")
