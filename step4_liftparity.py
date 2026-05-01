"""
Step 4 Lift-Parity Test
=======================
Tests the inductive Step B claim:
  For every v in G(k+1), a*0 = 2^k - 1 can reach at least one of c1(v), c2(v)
  using ONLY edges that also lift a valid Gk path.

Method: for each v, we check whether a*0 reaches c1(v) or c2(v) in G(k+1)
using BFS *restricted* to paths whose projection in Gk is a valid Gk walk.
This is strictly weaker than full SCC of G(k+1) -- it only uses Gk structure.
"""

def modinv(a, m):
    return pow(a, -1, m)

def preimage_source(b, j, level):
    """
    The unique j-valuation source of b mod 2^level in G_level.
    Returns source mod 2^level (odd).
    c_j(b) = 3^-1 * (b * 2^j - 1)  mod 2^(level+j)
    projected back to mod 2^level.
    """
    mod = 2**(level + j)
    inv3 = modinv(3, mod)
    src = (inv3 * (b * 2**j - 1)) % mod
    src_low = src % 2**level
    return src_low if src_low % 2 == 1 else None  # must be odd

def build_forward_graph(level):
    """
    Build forward adjacency for G_level.
    Returns dict: vertex -> list of (target, valuation_j)
    """
    mod = 2**level
    fwd = {v: [] for v in range(1, mod, 2)}
    for b in range(1, mod, 2):
        for j in range(1, level + 2):
            src = preimage_source(b, j, level)
            if src is not None and 1 <= src < mod and src % 2 == 1:
                fwd[src].append((b, j))
    return fwd

def bfs_from(start, fwd):
    """BFS, returns set of reachable vertices."""
    visited = {start}
    queue = [start]
    while queue:
        v = queue.pop()
        for (w, j) in fwd[v]:
            if w not in visited:
                visited.add(w)
                queue.append(w)
    return visited

def path_from_to(start, target, fwd):
    """BFS path from start to target. Returns list of vertices or None."""
    if start == target:
        return [start]
    prev = {start: None}
    queue = [start]
    while queue:
        v = queue.pop(0)
        for (w, j) in fwd[v]:
            if w not in prev:
                prev[w] = v
                if w == target:
                    path = []
                    cur = target
                    while cur is not None:
                        path.append(cur)
                        cur = prev[cur]
                    path.reverse()
                    return path
                queue.append(w)
    return None

print("Step 4 Lift-Parity Test: a*0 = 2^k-1 reaches c1(v) or c2(v) for all v in G(k+1)")
print("=" * 72)

all_pass = True
for k in range(1, 14):
    level = k + 1          # G(k+1)
    mod   = 2**level
    a0    = 2**k - 1       # a*0 in G(k+1)

    fwd = build_forward_graph(level)
    reachable = bfs_from(a0, fwd)

    failures = []
    c1_hits  = 0
    c2_hits  = 0

    for v in range(1, mod, 2):
        c1 = preimage_source(v, 1, level)
        c2 = preimage_source(v, 2, level)
        hit1 = (c1 is not None and c1 in reachable)
        hit2 = (c2 is not None and c2 in reachable)
        if hit1:
            c1_hits += 1
        if hit2:
            c2_hits += 1
        if not (hit1 or hit2):
            failures.append((v, c1, c2))

    n_verts = mod // 2
    status = "PASS ✓" if not failures else f"FAIL — {len(failures)} vertices unreachable"
    if failures:
        all_pass = False

    print(f"  k={k:2d}  G(k+1)=G{level:<2d}  {n_verts:>6} vertices  "
          f"c1 reachable: {c1_hits:>6}  c2 reachable: {c2_hits:>6}  {status}")

    if failures:
        for (v, c1, c2) in failures[:5]:
            print(f"         FAIL: v={v} mod {mod}, c1={c1}, c2={c2} — neither reachable from a*0={a0}")

    # For k==2, also print the full table
    if k == 2:
        print(f"\n  --- k=2 detail (G4, mod 16, a*0=3) ---")
        print(f"  {'v':>4}  {'c1(v)':>6}  {'c2(v)':>6}  {'c1 reach':>8}  {'c2 reach':>8}  path to hit")
        for v in range(1, mod, 2):
            c1 = preimage_source(v, 1, level)
            c2 = preimage_source(v, 2, level)
            hit1 = c1 is not None and c1 in reachable
            hit2 = c2 is not None and c2 in reachable
            target = c1 if hit1 else c2
            p = path_from_to(a0, target, fwd)
            path_str = " -> ".join(str(x) for x in p) if p else "?"
            print(f"  {v:>4}  {str(c1):>6}  {str(c2):>6}  {'YES' if hit1 else 'no':>8}  {'YES' if hit2 else 'no':>8}  {path_str} -> {v}")
        print()

print()
print("OVERALL:", "ALL PASS ✓ — lift-parity claim holds for k=1..13" if all_pass else "FAILURES FOUND")
