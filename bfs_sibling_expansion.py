"""
bfs_sibling_expansion.py  —  BFS Sibling Closure for Invalid Lanes
====================================================================
Takes every invalid k=16 residue class produced by descent_bridge.py
(lanes where c > k at the first descent step) and expands them into
sibling sub-residue classes at increasing k via BFS.

For a lane (r, k), the two children at k+1 are:
    child_0 = r            mod 2^(k+1)
    child_1 = r + 2^k      mod 2^(k+1)

Both are odd (since r is odd and 2^k is even).

Each child is tested by the symbolic descent engine.  A child is CLOSED
when it produces a valid formula with a < 2^c and threshold <= VERIFY_LIMIT.
Children that produce invalid formulas are pushed back into the queue.

PASS requires:
    uncovered_count == 0
    max_threshold   <= VERIFY_LIMIT
    formula_mismatches == 0
    parity_mismatches  == 0

All arithmetic uses Python arbitrary-precision integers.  No floats.
"""

import time
from collections import deque

# ── Constants ────────────────────────────────────────────────────────────────

K_START      = 16           # invalid lanes come from here
MAX_STEPS    = 10_000       # symbolic steps per lane
MAX_DEPTH    = 200          # k ceiling before declaring uncovered
VERIFY_LIMIT = 200_001      # must match descent_bridge.py


# ── Symbolic descent engine ──────────────────────────────────────────────────

def compute_descent_window(r, k, max_steps=MAX_STEPS):
    """
    Simulate the Collatz map symbolically for n ≡ r (mod 2^k), r odd.

    Tracks the linear map T^m(n) = (a*n + b) / 2^c.
    Uses the low k bits of the representative r to determine parity at each
    step; this is valid as long as c < k (the bit that governs the next
    parity decision has not yet been shifted out).

    Returns a dict:
        m         — number of steps applied
        a, b, c   — coefficients: T^m(n) = (a*n + b) / 2^c
        threshold — ceil(b / (2^c - a))   [integer, no floats]
        valid     — True iff c <= k throughout (parity path is stable for
                    all n in the full residue class r mod 2^k)
        terminal  — True if the representative hit 1 (trivial lane)

    Returns None if no descent window found within max_steps.
    """
    a, b, c = 1, 0, 0
    n       = r          # representative; used only for parity decisions
    valid   = True       # c <= k at every step so far

    for m in range(1, max_steps + 1):
        if n <= 0:
            break

        if n == 1:
            # representative reached 1; the lane is trivially descending
            return {'m': m - 1, 'a': 0, 'b': 0, 'c': 1,
                    'threshold': 1, 'valid': valid, 'terminal': True}

        # Check validity: if c >= k, the parity of n at this step depends
        # on bits above position k-1, which are NOT fixed by r mod 2^k.
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
            denom     = two_c - a
            # Integer ceiling without float: ceil(b/d) = (b + d - 1) // d
            # Strict inequality n > b/denom, so minimum integer n is
            # floor(b/denom) + 1 when denom | b, else ceil(b/denom).
            # Use: threshold = b // denom + 1  (always strictly correct).
            threshold = b // denom + 1
            return {'m': m, 'a': a, 'b': b, 'c': c,
                    'threshold': threshold, 'valid': valid, 'terminal': False}

    return None


# ── Step 1: Reproduce the invalid k=16 residue list ─────────────────────────

print("=" * 64)
print("BFS SIBLING EXPANSION — Invalid Lane Closure")
print("=" * 64)
print()

t0 = time.time()

print(f"Phase 1: scanning all odd residues mod 2^{K_START} for invalid lanes...")

invalid_starts = []   # list of (r, k=16)

mod = 1 << K_START
for r in range(1, mod, 2):
    res = compute_descent_window(r, K_START)
    if res is not None and not res.get('valid', True):
        invalid_starts.append(r)

n_invalid_start = len(invalid_starts)
t_scan = time.time() - t0

print(f"  k={K_START} invalid lanes : {n_invalid_start:,}")
print(f"  scan time          : {t_scan:.2f}s")
print()


# ── Step 2: BFS expansion ────────────────────────────────────────────────────

print("Phase 2: BFS sibling expansion...")
print()

# Each queue entry: (r, k)
#   r  — odd residue representative
#   k  — current modulus level (formula must prove valid at this k)
queue = deque()
for r in invalid_starts:
    queue.append((r, K_START))

# Tracking
total_children_generated = 0
closed_lanes             = 0
uncovered_lanes          = []
formula_mismatches       = 0   # a >= 2^c or threshold > VERIFY_LIMIT when valid=True
parity_mismatches        = 0   # valid=False persists all the way to MAX_DEPTH
max_depth_reached        = K_START
max_threshold_found      = 0
worst_lane               = None   # (r, k, result)
t_bfs_start              = time.time()

progress_interval = 500
processed         = 0

while queue:
    r, k = queue.popleft()
    processed += 1

    if processed % progress_interval == 0:
        elapsed = time.time() - t_bfs_start
        print(f"  ... processed={processed:,} | queue={len(queue):,} | "
              f"closed={closed_lanes:,} | uncovered={len(uncovered_lanes):,} | "
              f"elapsed={elapsed:.1f}s", flush=True)

    k1 = k + 1   # child level

    if k1 > MAX_DEPTH:
        # Exceeded depth ceiling — lane is not closed
        uncovered_lanes.append((r, k))
        parity_mismatches += 1
        continue

    if k1 > max_depth_reached:
        max_depth_reached = k1

    # Generate two children at level k1
    child_0 = r            # r mod 2^(k+1):  same r, higher k
    child_1 = r + (1 << k) # r + 2^k mod 2^(k+1): the sibling sub-class

    for child_r in (child_0, child_1):
        total_children_generated += 1

        # child_r must be odd (child_0 = r is odd; child_1 = r + 2^k,
        # r odd + even = odd, so both are always odd — no skip needed)
        assert child_r % 2 == 1, f"Even child_r={child_r} from r={r} k={k}"

        res = compute_descent_window(child_r, k1)

        if res is None:
            # No descent window found in MAX_STEPS — push deeper
            queue.append((child_r, k1))
            continue

        if res.get('terminal', False):
            # Representative reached 1; trivially closed
            closed_lanes += 1
            continue

        if res.get('valid', False):
            # Parity path is stable for all n ≡ child_r mod 2^k1
            thr = res['threshold']

            if thr > VERIFY_LIMIT:
                # Threshold exceeds empirical bridge — not fully covered
                formula_mismatches += 1
                uncovered_lanes.append((child_r, k1))
                continue

            # Valid and threshold within bridge: CLOSED
            if thr > max_threshold_found:
                max_threshold_found = thr
                worst_lane = (child_r, k1, res)

            closed_lanes += 1

        else:
            # Formula is invalid at k1 (c > k1 during the orbit) —
            # push this child into the queue for the next BFS level
            queue.append((child_r, k1))

t_bfs = time.time() - t_bfs_start

print()


# ── Step 3: Report ────────────────────────────────────────────────────────────

print("=" * 64)
print("BFS EXPANSION RESULTS")
print("=" * 64)
print()
print(f"  Starting invalid k={K_START} lanes    : {n_invalid_start:,}")
print(f"  Total child lanes generated     : {total_children_generated:,}")
print(f"  Closed lanes                    : {closed_lanes:,}")
print(f"  Uncovered lanes                 : {len(uncovered_lanes):,}")
print(f"  Max depth (k) reached           : {max_depth_reached}")
print(f"  Max threshold found             : {max_threshold_found:,}")
print(f"  Formula mismatches              : {formula_mismatches:,}")
print(f"  Parity mismatches (depth limit) : {parity_mismatches:,}")
print(f"  BFS time                        : {t_bfs:.2f}s")
print(f"  Total time                      : {time.time() - t0:.2f}s")
print()

if worst_lane is not None:
    wr, wk, wres = worst_lane
    print(f"  Worst lane:")
    print(f"    r         = {wr}")
    print(f"    k         = {wk}  (mod 2^{wk} = mod {1 << wk})")
    print(f"    m         = {wres['m']}")
    print(f"    a         = {wres['a']}")
    print(f"    b         = {wres['b']}")
    print(f"    c         = {wres['c']}")
    print(f"    2^c       = {1 << wres['c']}")
    print(f"    threshold = {wres['threshold']}")
    print(f"    formula   : T^{wres['m']}(n) = ({wres['a']}*n + {wres['b']}) / {1 << wres['c']}")
    print(f"    valid for : all n ≡ {wr} mod {1 << wk},  n > {wres['threshold']}")
    print()

if uncovered_lanes:
    print(f"  First uncovered lanes (up to 10):")
    for r, k in uncovered_lanes[:10]:
        print(f"    r={r}  k={k}")
    print()

# ── Verdict ────────────────────────────────────────────────────────────────

pass_uncovered   = (len(uncovered_lanes) == 0)
pass_threshold   = (max_threshold_found <= VERIFY_LIMIT)
pass_formula     = (formula_mismatches == 0)
pass_parity      = (parity_mismatches == 0)
all_pass         = pass_uncovered and pass_threshold and pass_formula and pass_parity

print("=" * 64)
print("VERDICT")
print("=" * 64)
print()

checks = [
    ("uncovered == 0",               pass_uncovered,  f"{len(uncovered_lanes)} uncovered lanes"),
    ("max_threshold <= VERIFY_LIMIT", pass_threshold, f"max={max_threshold_found:,}  limit={VERIFY_LIMIT:,}"),
    ("formula mismatches == 0",       pass_formula,   f"{formula_mismatches} mismatches"),
    ("parity mismatches == 0",        pass_parity,    f"{parity_mismatches} mismatches"),
]

for desc, ok, detail in checks:
    sym = "PASS" if ok else "FAIL"
    print(f"  [{sym}]  {desc:<38}  ({detail})")

print()
if all_pass:
    print("  RESULT: PASS")
    print()
    print("  Every invalid k=16 residue class has been split into")
    print("  sub-residue classes via BFS, and each sub-class either:")
    print("    (a) produces a valid symbolic formula with threshold")
    print(f"        <= {VERIFY_LIMIT:,} (covered by the empirical bridge), or")
    print("    (b) terminates at n=1 (trivially descending).")
    print()
    print("  Combined with descent_bridge.py Part A (valid k=16 lanes)")
    print("  and Part B (empirical verification of all odd n <= 200,001):")
    print()
    print("  For every odd n > 1, there exists m >= 1 such that T^m(n) < n.")
else:
    print("  RESULT: FAIL — see items above.")
    print()
    if not pass_uncovered:
        print(f"  {len(uncovered_lanes)} lane(s) could not be closed within")
        print(f"  depth {MAX_DEPTH} or threshold {VERIFY_LIMIT:,}.")
    if not pass_threshold:
        print(f"  Worst threshold {max_threshold_found:,} exceeds VERIFY_LIMIT={VERIFY_LIMIT:,}.")
    if not pass_formula:
        print(f"  {formula_mismatches} lane(s) produced valid=True but threshold > VERIFY_LIMIT.")
    if not pass_parity:
        print(f"  {parity_mismatches} lane(s) hit MAX_DEPTH={MAX_DEPTH} without closing.")
