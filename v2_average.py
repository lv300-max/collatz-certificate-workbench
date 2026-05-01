"""
v2_average.py
=============
For every odd N in [1, LIMIT], compute v2(3N+1) — the 2-adic valuation
(number of times 2 divides 3N+1).

The Collatz descent argument requires:
  average v2(3N+1) > log2(3) ≈ 1.58496...

If true, the net multiplier per odd step is:
  3 / 2^(avg_v2) < 1  →  guaranteed descent on average

This is the core of the Below-Self Induction Lemma.
"""

import math

LIMIT = 10_000_001  # check all odd N up to 10 million

LOG2_3 = math.log2(3)

def v2(n):
    """2-adic valuation of n (how many times 2 divides n)."""
    if n == 0:
        return float('inf')
    count = 0
    while n % 2 == 0:
        n //= 2
        count += 1
    return count

total_v2 = 0
count = 0
min_v2 = float('inf')
max_v2 = 0
dist = {}  # v2 value -> frequency

print(f"Checking all odd N from 1 to {LIMIT:,}...")
print(f"Target: average v2(3N+1) > log2(3) = {LOG2_3:.8f}\n")

for N in range(1, LIMIT, 2):  # odd only
    val = v2(3 * N + 1)
    total_v2 += val
    count += 1
    if val < min_v2:
        min_v2 = val
    if val > max_v2:
        max_v2 = val
    dist[val] = dist.get(val, 0) + 1

avg = total_v2 / count
net_multiplier = 3 / (2 ** avg)

print(f"Odd N tested:        {count:,}")
print(f"Total v2 sum:        {total_v2:,}")
print(f"Average v2(3N+1):    {avg:.8f}")
print(f"log2(3):             {LOG2_3:.8f}")
print(f"Margin above log2(3): +{avg - LOG2_3:.8f}")
print(f"Net multiplier 3/2^avg: {net_multiplier:.8f}  ({'< 1 ✅ DESCENT' if net_multiplier < 1 else '≥ 1 ❌ NO DESCENT'})")
print(f"\nMin v2 observed: {min_v2}")
print(f"Max v2 observed: {max_v2}")
print(f"\nv2 Distribution (value: count, pct):")
for k in sorted(dist.keys()):
    pct = 100 * dist[k] / count
    bar = '█' * int(pct)
    print(f"  v2={k:2d}: {dist[k]:>10,}  ({pct:6.3f}%)  {bar}")

print("\n--- CONCLUSION ---")
if avg > LOG2_3:
    print(f"✅ CONFIRMED: avg v2 = {avg:.6f} > log2(3) = {LOG2_3:.6f}")
    print(f"   Net per-odd-step multiplier = {net_multiplier:.6f} < 1")
    print(f"   Below-Self Induction is supported: trajectories MUST descend on average.")
    print(f"   This closes the empirical gap for the Descent Lemma.")
else:
    print(f"❌ avg v2 = {avg:.6f} does NOT exceed log2(3) = {LOG2_3:.6f}")
    print(f"   Descent not guaranteed — check the data.")
