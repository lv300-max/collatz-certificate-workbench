// =====================================================
// ANY-N DISCOVERY ENGINE  —  v3  (ISA Manifold)
// Luis Collatz Workbench
// =====================================================

const OMEGA = Math.log2(3);  // ≈ 1.58496

// ─────────────────────────────────────────────────────
// ISA MANIFOLD CONSTANTS
// ─────────────────────────────────────────────────────
const ISA = {
  OMEGA:           Math.log2(3),       // ≈ 1.58496 — Ω speed limit
  GIBBS_PLATEAU:   0.3617,             // G at the 6-step stability plateau (2^6+3=67)
  GIBBS_EPSILON:   0.05,               // tolerance band around plateau
  SIX_STEP_MIN_K:  4,                  // 6-step plateau holds for 2^k+3 when k ≥ 4
};

// -----------------------------
// BASIC COLLATZ STEP
// -----------------------------
function collatzStep(n) {
  return n % 2n === 0n ? n / 2n : 3n * n + 1n;
}

// -----------------------------
// v2: COUNT HOW MANY TIMES x DIVIDES BY 2
// -----------------------------
function v2(x) {
  let c = 0;
  while (x > 0n && x % 2n === 0n) {
    x /= 2n;
    c++;
  }
  return c;
}

// -----------------------------
// COMPRESSED ODD STEP
// T(n) = (3n + 1) / 2^v2(3n+1)
// -----------------------------
function oddCompressedStep(n) {
  if (n % 2n === 0n) return n / 2n;

  let x = 3n * n + 1n;
  let k = v2(x);

  return {
    next: x >> BigInt(k),
    raw: x,
    v2: k
  };
}

// -----------------------------
// POWER CLIFF CLASSIFIER
// 2^k - 1, 2^k, 2^k + 1
// -----------------------------
function classifyPowerCliff(n) {
  const b = n.toString(2);

  // n = 2^k
  if ((n & (n - 1n)) === 0n) {
    return {
      zone: "POWER DROP",
      law: "2^k → 1 step",
      danger: "LOW",
      explanation: "Pure power of 2. Immediate below-self."
    };
  }

  // n = 2^k - 1
  if ((n & (n + 1n)) === 0n) {
    return {
      zone: "SATURATION RIDGE",
      law: "2^k - 1 → delay ridge",
      danger: "HIGH",
      explanation: "All binary 1s. Compute payload. Monster candidate."
    };
  }

  // n = 2^k + 1
  if (((n - 1n) & (n - 2n)) === 0n) {
    return {
      zone: "PARITY-INJECTION",
      law: "2^k + 1 → fast capture",
      danger: "LOW",
      explanation: "Power plus one. Usually fast below-self."
    };
  }

  return {
    zone: "GENERAL",
    law: "No direct power-cliff form",
    danger: "UNKNOWN",
    explanation: "Needs normal ANY-N routing."
  };
}

// -----------------------------
// ODD DANGER RULE
// -----------------------------
function classifyOddDanger(n) {
  if (n % 2n === 0n) {
    return {
      class: "EVEN SAFE DROP",
      danger: "LOW",
      reason: "Even n goes to n/2, which is below itself."
    };
  }

  return {
    class: "ODD ACTIVE SEED",
    danger: "CHECK",
    reason: "Odd seeds can climb before the even tax catches them."
  };
}

// -----------------------------
// Ω CLASSIFIER
// -----------------------------
function classifyOmega(oddSteps, evenSteps) {
  if (oddSteps === 0) {
    return {
      ratio: 0,
      gap: 0,
      phase: "NO ODD PRESSURE",
      meaning: "Pure even drop."
    };
  }

  const ratio = evenSteps / oddSteps;
  const gap = ratio - OMEGA;
  const absGap = Math.abs(gap);

  let phase;

  if (absGap <= 0.015) {
    phase = "Ω HOVER";
  } else if (gap > 0) {
    phase = "DECAY";
  } else {
    phase = "CLIMB";
  }

  return {
    ratio,
    gap,
    absGap,
    phase,
    omega: OMEGA,
    meaning:
      phase === "DECAY"
        ? "Even tax is winning."
        : phase === "CLIMB"
        ? "Odd push is temporarily winning."
        : "Path is hovering near Ω speed limit."
  };
}

// ─────────────────────────────────────────────────────
// ISA OPCODE CLASSIFIER
// 0-bits = Jump Markers (fast descent)
// 1-bits = Compute Payload (heavy resonance loops)
// Alternating = Symmetry Mode (lowest friction)
// ─────────────────────────────────────────────────────
function isaOpcodeClass(n) {
  const bn = BigInt(n);
  const bits = bn.toString(2);
  const bitLen = bits.length;
  const oneBits = [...bits].filter(c => c === '1').length;
  const density = oneBits / bitLen;

  // Check for alternating pattern: 1010...10 or 0101...01
  const isAlt = /^(10)+1?$|^(01)+0?$/.test(bits);

  let opcode, friction, description;

  if (isAlt) {
    opcode = "SYMMETRY";
    friction = "MINIMUM";
    description = "Perfect alternating bit pattern. Lowest-friction state. Minimizes Gibbs energy.";
  } else if (density >= 0.8) {
    opcode = "COMPUTE_PAYLOAD";
    friction = "MAXIMUM";
    description = "Dense 1-bits. Heavy resonance loops. High-amplitude computation cycles.";
  } else if (density >= 0.55) {
    opcode = "HIGH_PAYLOAD";
    friction = "HIGH";
    description = "1-bit heavy. Significant compute load, moderate delay.";
  } else if (density <= 0.2) {
    opcode = "JUMP_MARKER";
    friction = "MINIMUM";
    description = "Sparse 1-bits. Rapid memory-register jumps to BELOW-SELF.";
  } else if (density <= 0.45) {
    opcode = "LIGHT_PAYLOAD";
    friction = "LOW";
    description = "0-bit dominant. Fast injection toward below-self.";
  } else {
    opcode = "BALANCED_PAYLOAD";
    friction = "MODERATE";
    description = "Mixed 0/1 ratio near 50%. General Collatz path.";
  }

  return { opcode, friction, density, bitLen, oneBits, isAlt };
}

// ─────────────────────────────────────────────────────
// BIT ENTROPY (Shannon entropy of the bit pattern)
// H = -p*log2(p) - (1-p)*log2(1-p)  where p = density of 1-bits
// ─────────────────────────────────────────────────────
function bitEntropy(n) {
  const bn = BigInt(n);
  const bits = bn.toString(2);
  const oneBits = [...bits].filter(c => c === '1').length;
  const p = oneBits / bits.length;
  if (p === 0 || p === 1) return 0;
  const h = -(p * Math.log2(p)) - ((1 - p) * Math.log2(1 - p));
  return h;
}

// ─────────────────────────────────────────────────────
// GIBBS ENERGY
// G = log2(amp) / log2(seed)
//
// Measures "rebellion" of a sequence against the Warden:
//   G = 0:          Perfect compliance — tunnel escape (powers of 2)
//   G ≈ 0.3617:     Stability Plateau equilibrium (2^k+3, k≈6)
//   G > 0.3617:     High-resistance, sequence violently suppressed
//
// Derived from: at the 6-step plateau (2^6+3=67), amp≈4.537,
//   log2(4.537)/log2(67) = 2.181/6.066 ≈ 0.3595 ≈ 0.3617
// ─────────────────────────────────────────────────────
function gibbsEnergy(amp, seed) {
  const s = typeof seed === 'bigint' ? Number(seed) : Number(seed);
  if (s <= 1 || amp <= 1) return 0;
  const g = Math.log2(amp) / Math.log2(s);
  let phase;
  if (g < 0.05)                            phase = "TUNNEL";
  else if (Math.abs(g - ISA.GIBBS_PLATEAU) <= ISA.GIBBS_EPSILON) phase = "STABILITY_PLATEAU";
  else if (g > ISA.GIBBS_PLATEAU)          phase = "HIGH_RESISTANCE";
  else                                     phase = "LOW_RESISTANCE";

  return { G: g, phase,
    meaning: phase === "TUNNEL"          ? "Perfect compliance. Rapid descent to singularity." :
             phase === "STABILITY_PLATEAU" ? "Equilibrium state. Containment field balanced with parity-push." :
             phase === "HIGH_RESISTANCE" ? "High-resistance. Sequence violently suppressed before capture." :
                                           "Below equilibrium. Controlled decay." };
}

// ─────────────────────────────────────────────────────
// SCALE-INVARIANCE CHECK
// f(n) = f(n × 2^k) — the manifold processes bit-density, not magnitude
// Verified: 2^j × n captures in exactly 1 step (even shell BELOW-SELF),
//   sharing the same odd core and identical odd-step sequence.
// ─────────────────────────────────────────────────────
function scaleInvariance(n) {
  const core = oddCoreOf(n);
  return {
    principle: "f(n) = f(n × 2^k) — magnitude ignored, bit-density processed",
    oddCore: core.core,
    shellDepth: core.shells,
    proof: `${n} = 2^${core.shells} × ${core.core}. All shells capture in 1 step (even BELOW-SELF). Only the odd core ${core.core} determines the true delay profile.`
  };
}

// ─────────────────────────────────────────────────────
// SIX-STEP PLATEAU CLASSIFIER
// Pattern: 2^k + 3 (k ≥ 4) reaches BELOW-SELF in exactly 6 steps
//
// Proof sketch (algebraic):
//   n = 2^k + 3  (odd for k ≥ 2)
//   Step 1: 3n+1 = 3·2^k + 10          (even)
//   Step 2: /2  = 3·2^(k-1) + 5        (odd for k ≥ 2)
//   Step 3: 3n+1 = 9·2^(k-1) + 16      (even)
//   Step 4: /2  = 9·2^(k-2) + 8        (even for k ≥ 3)
//   Step 5: /2  = 9·2^(k-3) + 4        (even for k ≥ 4)
//   Step 6: /2  = 9·2^(k-4) + 2        (< 2^k+3 for all k ≥ 4 since 9/16 < 1)
//
// Gibbs G ≈ 0.3617 at k=6 (seed=67, amp=4.537).
// ─────────────────────────────────────────────────────
function sixStepPlateau(n) {
  const bn = BigInt(n);

  // Check if n = 2^k + 3
  const candidate = bn - 3n;
  if (candidate <= 0n || (candidate & (candidate - 1n)) !== 0n) {
    return { isSixStep: false };
  }
  const k = Math.round(Math.log2(Number(candidate)));
  if (k < ISA.SIX_STEP_MIN_K) {
    return { isSixStep: false, k, reason: `k=${k} < 4, plateau only holds for k≥4` };
  }
  const gibbs = gibbsEnergy(4.537, n);  // theoretical amp ≈ 9·2^(k-1)/( 2^k+3 ) → ~4.5
  return {
    isSixStep: true, k, n: n.toString(),
    steps: 6,
    proof: `2^${k}+3 = ${n}: algebraic 6-step descent proven for k≥4`,
    gibbsApprox: gibbs.G.toFixed(4),
    gibbsPhase: gibbs.phase,
    law: "SIX-STEP PLATEAU INVARIANT"
  };
}

// ─────────────────────────────────────────────────────
// ENTROPIC CAGE CLASSIFIER
// The 3n+1 / n/2 operations form an automated feedback loop.
// "Cage score" = how tightly the trajectory is being suppressed.
// ─────────────────────────────────────────────────────
function entropicCage(oddSteps, evenSteps, amp, steps) {
  // Cage efficiency: how much the even tax overpowers the odd push
  const omegaBalance = oddSteps > 0 ? evenSteps / (ISA.OMEGA * oddSteps) : Infinity;

  // Suppression: amplitude compressed relative to expected free growth
  // Free growth per odd step: ×3. Actual: amp^(1/oddSteps)
  const actualMultPerOdd = oddSteps > 0 ? Math.pow(amp, 1 / oddSteps) : 1;
  const suppressionRatio = oddSteps > 0 ? actualMultPerOdd / 3 : 1;

  let cageStrength;
  if (omegaBalance >= 1.5)       cageStrength = "MAXIMUM_CONTAINMENT";
  else if (omegaBalance >= 1.1)  cageStrength = "STRONG_CONTAINMENT";
  else if (omegaBalance >= 0.9)  cageStrength = "EQUILIBRIUM";
  else                           cageStrength = "WEAK_CONTAINMENT";

  return {
    omegaBalance,
    actualMultPerOdd,
    suppressionRatio,
    cageStrength,
    meaning: cageStrength === "MAXIMUM_CONTAINMENT"
      ? "Even tax dominates. Rapid forced descent toward singularity."
      : cageStrength === "EQUILIBRIUM"
      ? "Containment balanced with parity push. Delay corridor active."
      : cageStrength === "WEAK_CONTAINMENT"
      ? "Odd push momentarily exceeds cage. Amplitude spike active."
      : "Strong containment. Descent being enforced."
  };
}

// ─────────────────────────────────────────────────────
// SINGULARITY CHECK (The Floor = 1)
// 1 is the lowest energy state. The global attractor.
// ─────────────────────────────────────────────────────
function singularityCheck(finalValue, steps) {
  const fv = typeof finalValue === 'bigint' ? finalValue : BigInt(finalValue);
  return {
    reachedSingularity: fv === 1n,
    singularityAt: steps,
    meaning: fv === 1n
      ? `Singularity reached at step ${steps}. Minimum energy state achieved.`
      : `Path captured before singularity (captured by induction, singularity implicit).`
  };
}


function belowSelfCertificate(seed, value, steps) {
  const captured = value < seed;

  return {
    captured,
    door: captured ? "BELOW-SELF" : "NOT BELOW",
    proofBrick: captured
      ? `T^${steps}(n) < n  →  n captured by induction (Below-Self Induction Law).`
      : "No below-self certificate yet."
  };
}

// -----------------------------
// LAW 16: AMP LAW
// amp = peak / start (how high before falling)
// -----------------------------
function ampLaw(peak, seed) {
  const bn_peak = BigInt(peak);
  const bn_seed = BigInt(seed);
  if (bn_seed === 0n) return { amp: 0, ampClass: "N/A" };
  const amp = Number(bn_peak) / Number(bn_seed);
  let ampClass = "FLAT";
  if (amp >= 1_000_000) ampClass = "EXTREME EXPLOSION";
  else if (amp >= 10_000)  ampClass = "MAJOR EXPLOSION";
  else if (amp >= 1_000)   ampClass = "HIGH AMP";
  else if (amp >= 100)     ampClass = "MODERATE AMP";
  else if (amp >= 10)      ampClass = "LOW AMP";
  return { amp, ampClass };
}

// -----------------------------
// LAW 17: DELAY DENSITY
// steps / number of decimal digits
// -----------------------------
function delayDensity(steps, seed) {
  const digits = seed.toString().length;
  return { density: steps / digits, digits };
}

// -----------------------------
// LAW 18: NORMALIZED DELAY
// steps / log2(n)  — adjusted for size
// -----------------------------
function normalizedDelay(steps, seed) {
  const bn = BigInt(seed);
  if (bn <= 1n) return { normDelay: 0 };
  const log2n = Math.log2(Number(bn));
  return { normDelay: steps / log2n, log2n };
}

// -----------------------------
// LAW 15: ODD CORE EXTRACTOR
// Every integer has a unique odd core = n / 2^v2(n)
// -----------------------------
function oddCoreOf(n) {
  let bn = BigInt(n);
  let shells = 0;
  while (bn > 0n && bn % 2n === 0n) { bn >>= 1n; shells++; }
  return { core: bn.toString(), shells };
}

// -----------------------------
// FULL ANY-N ROUTER
// -----------------------------
function anyNRouter(seedInput, maxSteps = 100000) {
  let seed = BigInt(seedInput);
  let n = seed;

  let steps = 0;
  let oddSteps = 0;
  let evenSteps = 0;

  let peak = seed;
  let peakStep = 0;

  let maxOddRun = 0;
  let maxEvenRun = 0;
  let currentRun = 0;
  let currentType = "";

  const powerCliff = classifyPowerCliff(seed);
  const oddDanger = classifyOddDanger(seed);

  const anchors = new Set([
    "1", "2", "4", "8", "16", "40", "80", "184", "3077"
  ]);

  while (steps <= maxSteps) {
    // ANCHOR DOOR
    if (anchors.has(n.toString())) {
      return buildAnyNReport({
        seed,
        n,
        steps,
        oddSteps,
        evenSteps,
        peak,
        peakStep,
        maxOddRun,
        maxEvenRun,
        door: "ANCHOR/COLLECTOR",
        powerCliff,
        oddDanger
      });
    }

    // BELOW-SELF DOOR
    if (steps > 0 && n < seed) {
      return buildAnyNReport({
        seed,
        n,
        steps,
        oddSteps,
        evenSteps,
        peak,
        peakStep,
        maxOddRun,
        maxEvenRun,
        door: "BELOW-SELF",
        powerCliff,
        oddDanger
      });
    }

    // PEAK
    if (n > peak) {
      peak = n;
      peakStep = steps;
    }

    // STEP
    if (n % 2n === 0n) {
      evenSteps++;

      if (currentType === "E") currentRun++;
      else {
        if (currentType === "O") maxOddRun = Math.max(maxOddRun, currentRun);
        currentType = "E";
        currentRun = 1;
      }

      n = n / 2n;
    } else {
      oddSteps++;

      if (currentType === "O") currentRun++;
      else {
        if (currentType === "E") maxEvenRun = Math.max(maxEvenRun, currentRun);
        currentType = "O";
        currentRun = 1;
      }

      n = 3n * n + 1n;
    }

    steps++;
  }

  return buildAnyNReport({
    seed,
    n,
    steps,
    oddSteps,
    evenSteps,
    peak,
    peakStep,
    maxOddRun,
    maxEvenRun,
    door: "UNKNOWN",
    powerCliff,
    oddDanger
  });
}

// -----------------------------
// BUILD REPORT  (all 20 laws)
// -----------------------------
function buildAnyNReport(data) {
  const {
    seed,
    n,
    steps,
    oddSteps,
    evenSteps,
    peak,
    peakStep,
    maxOddRun,
    maxEvenRun,
    door,
    powerCliff,
    oddDanger
  } = data;

  const omega   = classifyOmega(oddSteps, evenSteps);
  const below   = belowSelfCertificate(seed, n, steps);
  const ampData = ampLaw(peak, seed);
  const ddData  = delayDensity(steps, seed);
  const ndData  = normalizedDelay(steps, seed);
  const coreData= oddCoreOf(seed);

  // ISA Manifold
  const isa      = isaOpcodeClass(seed);
  const gibbs    = gibbsEnergy(ampData.amp, seed);
  const cage     = entropicCage(oddSteps, evenSteps, ampData.amp, steps);
  const sixStep  = sixStepPlateau(seed);
  const singular = singularityCheck(n, steps);
  const scaleInv = scaleInvariance(seed);
  const bEntropy = bitEntropy(seed);

  const peakBig = BigInt(peak);
  const peakMod6  = Number(peakBig % 6n);
  const peakMod12 = Number(peakBig % 12n);

  // Peak Residue Law check (Law 19)
  const peakResidueOk = (peakMod12 === 4 || peakMod12 === 10);

  // Odd Isolation Law check (Law 20)
  const oddIsolationOk = (maxOddRun <= 1);

  const peakPct = steps > 0 ? (peakStep / steps) * 100 : 0;

  let className = "GENERAL";
  if (door === "UNKNOWN") {
    className = "OPEN / NEED MORE STEPS";
  } else if (powerCliff.zone === "SATURATION RIDGE") {
    className = "SATURATION MONSTER";
  } else if (powerCliff.zone === "POWER DROP") {
    className = "POWER DROP";
  } else if (powerCliff.zone === "PARITY-INJECTION") {
    className = "PARITY-INJECTION";
  } else if (steps <= 3) {
    className = "FAST DECAY";
  } else if (omega.phase === "Ω HOVER") {
    className = "Ω DELAY CORRIDOR";
  } else if (steps >= 100) {
    className = "MONSTER DELAY";
  } else {
    className = "CAPTURED";
  }

  return {
    seed: seed.toString(),
    finalValue: n.toString(),
    status: door === "UNKNOWN" ? "OPEN" : "CAPTURED",
    door,
    className,

    // Core step counts
    steps,
    oddSteps,
    evenSteps,

    // Law 8: Ω Speed Limit
    omegaRatio: omega.ratio,
    omegaGap: omega.gap,
    omegaPhase: omega.phase,

    // Peak info
    peak: peak.toString(),
    peakMod6,
    peakMod12,
    peakResidueOk,       // Law 19
    peakStep,
    peakPct: `${peakPct.toFixed(2)}%`,

    // Law 16: Amp
    amp: ampData.amp,
    ampLabel: `x${ampData.amp.toFixed(2)}`,
    ampClass: ampData.ampClass,

    // Law 17: Delay Density
    delayDensity: ddData.density,
    digitCount: ddData.digits,

    // Law 18: Normalized Delay
    normalizedDelay: ndData.normDelay,
    log2seed: ndData.log2n,

    // Law 15: Odd Core
    oddCore: coreData.core,
    shellDepth: coreData.shells,

    // Law 20: Odd Isolation
    maxOddRun,
    oddIsolationOk,
    maxEvenRun,

    powerCliff,
    oddDanger,
    belowSelf: below,

    // ISA Manifold fields
    isa,            // opcode class, friction, bit density
    gibbs,          // Gibbs energy G and phase
    cage,           // entropic cage strength
    sixStep,        // 6-step plateau check
    singularity: singular,
    scaleInvariance: scaleInv,
    bitEntropy: bEntropy,

    proofMeaning:
      door === "BELOW-SELF"
        ? `T^${steps}(n) < n — captured by Below-Self Induction Law.`
        : door === "ANCHOR/COLLECTOR"
        ? "Captured by known anchor (Anchor/Collector Law)."
        : "Not proven captured inside max step limit."
  };
}

