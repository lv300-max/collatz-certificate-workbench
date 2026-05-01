"""
parity_drift_monitor.py  —  EL-JEFE Parity Drift Early Warning System
=======================================================================
Built on the Collatz structural law:
  - Even numbers face HALVING PRESSURE  (n → n/2, mean reversion)
  - Odd numbers face EXPANSION PRESSURE (n → 3n+1, price extension)

Anchor nodes are gravity wells (round numbers, power-of-2 price levels).
Drift measures the arithmetic stress between current price and nearest anchor.

EARLY DETECTOR LOGIC:
  If this never fires  →  system is stable, no critical drift building.
  If this fires        →  price is far from anchor AND in halving zone.
                          Prepare for mean reversion.

The detector is silent by design. Silence = confirmation.
"""

import numpy as np

# ─── EL-JEFE AUTHORITY NODES ──────────────────────────────────────────────────
# Gravity wells: key price anchors (round numbers, power-of-2 levels)
ANCHOR_NODES = np.array([2, 4, 8, 16, 32, 64, 80, 96, 128, 256])

# Alert thresholds
DRIFT_THRESHOLD  = 10    # Max tolerable drift before alert
STRESS_THRESHOLD = 20    # Critical stress — imminent reversion


# ─── PARITY DRIFT ENGINE ──────────────────────────────────────────────────────
def get_parity_drift(price):
    """
    Map price to its nearest gravity anchor and measure arithmetic stress.

    Returns:
      n             — integer manifold price
      anchor        — nearest EL-JEFE gravity well
      drift         — signed distance from anchor (stress measure)
      phase         — HALVING_PRESSURE or EXPANSION_PHASE
    """
    n = int(round(price))
    anchor = int(ANCHOR_NODES[np.abs(ANCHOR_NODES - n).argmin()])
    drift  = n - anchor

    # Collatz parity law applied to price:
    #   Even → halving pressure (mean reversion candidate)
    #   Odd  → expansion phase  (continuation candidate)
    phase = "HALVING_PRESSURE" if n % 2 == 0 else "EXPANSION_PHASE"

    return n, anchor, drift, phase


# ─── ALERT CLASSIFIER ─────────────────────────────────────────────────────────
def classify_drift(drift, phase):
    """Return risk label based on drift magnitude and parity phase."""
    adrift = abs(drift)

    if phase == "HALVING_PRESSURE":
        if adrift > STRESS_THRESHOLD:  return "🔴  CRITICAL  — mean reversion imminent"
        if adrift > DRIFT_THRESHOLD:   return "🟠  WARNING   — halving pressure elevated"
        return                                 "🟢  STABLE    — near anchor, even"
    else:  # EXPANSION_PHASE
        if adrift > STRESS_THRESHOLD:  return "🟡  EXTENDED  — expansion far from anchor"
        if adrift > DRIFT_THRESHOLD:   return "🔵  ACTIVE    — expansion phase, watch anchor"
        return                                 "🟢  STABLE    — near anchor, odd"


# ─── TICKER MONITOR ───────────────────────────────────────────────────────────
def monitor_ticker(ticker_name, current_price, verbose=True):
    """
    Run parity drift check on a single price.

    Prints nothing if stable (silent confirmation).
    Prints alert if drift exceeds threshold in halving zone.
    """
    n, anchor, drift, phase = get_parity_drift(current_price)
    label = classify_drift(drift, phase)

    alert = (abs(drift) > DRIFT_THRESHOLD and phase == "HALVING_PRESSURE")

    if alert:
        print(f"\n{'!' * 56}")
        print(f"  ALERT  {ticker_name}")
        print(f"  Price   : {n}")
        print(f"  Anchor  : {anchor}  (nearest gravity well)")
        print(f"  Drift   : {drift:+d}  ({label})")
        print(f"  Phase   : {phase}")
        print(f"  Signal  : PREPARE FOR MEAN REVERSION  (n → n/2)")
        print(f"{'!' * 56}\n")
    elif verbose:
        dir_arrow = "↑" if drift > 0 else ("↓" if drift < 0 else "=")
        print(f"  {ticker_name:<12}  price={n:>6}  anchor={anchor:>4}  "
              f"drift={drift:>+5}  {dir_arrow}  {phase:<18}  {label}")

    return {
        'ticker':  ticker_name,
        'price':   n,
        'anchor':  anchor,
        'drift':   drift,
        'phase':   phase,
        'label':   label,
        'alert':   alert,
    }


def monitor_portfolio(tickers: dict, verbose=True):
    """
    Run the full portfolio scan.
    tickers = {'AAPL': 183.5, 'BTC': 64100, ...}
    Returns list of results sorted by |drift| descending.
    """
    print("=" * 64)
    print("  EL-JEFE PARITY DRIFT MONITOR")
    print("=" * 64)
    results = [monitor_ticker(name, price, verbose) for name, price in tickers.items()]
    results.sort(key=lambda r: abs(r['drift']), reverse=True)

    alerts = [r for r in results if r['alert']]
    print()
    print(f"  Scanned : {len(results)} tickers")
    print(f"  Alerts  : {len(alerts)}")
    if not alerts:
        print("  ✅  SYSTEM STABLE — no critical parity drift detected.")
        print("      Silence is the signal. No mean reversion imminent.")
    else:
        print(f"  ❌  {len(alerts)} ALERT(S) — review above.")

    return results


# ─── DEMO ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    demo_portfolio = {
        "STABLE_A":  64,      # exactly on anchor — no drift
        "STABLE_B":  81,      # odd, near 80 anchor — expansion, low drift
        "WARN_ODD":  107,     # odd, between 96 and 128 — extended expansion
        "WARN_EVEN": 112,     # even, drift +16 from 96 — halving pressure warning
        "CRIT_EVEN": 48,      # even, drift +16 from 32 — halving pressure critical
        "EXPND_ODD": 105,     # odd, far from anchor — active expansion
        "AT_ANCHOR": 128,     # exactly on anchor
        "DEEP_DRIFT": 52,     # even, +20 from 32 — critical
    }

    monitor_portfolio(demo_portfolio)
