// =====================================================
// PROOF MODE — Luis Collatz Workbench
// For each seed: which law captured it?
// Group seeds by law.
// Find first seed with no law.
// =====================================================

// Requires: anyN_engine.js + laws.js loaded first

const OMEGA = Math.log2(3);

// =====================================================
// STEP 1 — DETERMINE WHICH LAW CAPTURED A SEED
// =====================================================
function getCaptureLaw(seed, report) {
  const bn = BigInt(seed);

  // --- STRUCTURAL SHAPE LAWS (checked before running orbit) ---

  if (bn % 2n === 0n) {
    return { law: "EVEN DROP LAW", reason: "Even seed drops to n/2 immediately — below-self in 1 step." };
  }

  if ((bn & (bn - 1n)) === 0n) {
    return { law: "POWER DROP LAW", reason: `${seed} = 2^k — instant drop.` };
  }

  if ((bn & (bn + 1n)) === 0n) {
    return { law: "SATURATION RIDGE LAW", reason: `${seed} = 2^k−1 — saturation ridge, delay expected.` };
  }

  if (((bn - 1n) & (bn - 2n)) === 0n && bn > 2n) {
    return { law: "PARITY-INJECTION LAW", reason: `${seed} = 2^k+1 — fast parity injection.` };
  }

  // --- ORBIT-BASED LAWS (require report from anyNRouter) ---

  if (!report) {
    return { law: "UNCHECKED", reason: "No orbit report provided." };
  }

  if (report.door === "ANCHOR/COLLECTOR") {
    return { law: "ANCHOR LAW", reason: `Orbit hit anchor sentinel at step ${report.steps}.` };
  }

  if (report.door === "BELOW-SELF") {
    const omegaRatio = report.omegaRatio;

    if (omegaRatio > OMEGA + 0.015) {
      return { law: "EVEN DROP LAW (orbit)", reason: `Even tax dominated — ratio ${omegaRatio.toFixed(4)} > Ω.` };
    }

    if (Math.abs(omegaRatio - OMEGA) <= 0.015) {
      return { law: "Ω SPEED LIMIT LAW", reason: `Orbit hovered near Ω = ${OMEGA.toFixed(6)} then decayed below-self.` };
    }

    if (report.steps >= 100) {
      return { law: "MONSTER DELAY SIGNATURE", reason: `Long orbit (${report.steps} steps) — monster delay pattern, still captured.` };
    }

    return { law: "BELOW-SELF INDUCTION LAW", reason: `C^${report.steps}(n) < n — captured by induction at step ${report.steps}.` };
  }

  return { law: "NO LAW FOUND", reason: "Orbit did not terminate within step limit or match any law." };
}

// =====================================================
// STEP 2 — RUN PROOF MODE OVER A LIST OF SEEDS
// =====================================================
function runProofMode(seeds) {
  const results = [];
  const byLaw = {};

  for (const seed of seeds) {
    const report = typeof anyNRouter === "function" ? anyNRouter(seed) : null;
    const capture = getCaptureLaw(seed, report);

    const entry = {
      seed,
      law: capture.law,
      reason: capture.reason,
      steps: report ? report.steps : "—",
      door: report ? report.door : "—",
      status: capture.law === "NO LAW FOUND" ? "⚠ OPEN" : "✓ CAPTURED"
    };

    results.push(entry);

    if (!byLaw[capture.law]) byLaw[capture.law] = [];
    byLaw[capture.law].push(seed);
  }

  return { results, byLaw };
}

// =====================================================
// STEP 3 — FIND FIRST SEED WITH NO LAW
// Scans integers starting from `start` up to `limit`
// =====================================================
function findFirstNoLaw(start = 1, limit = 100000) {
  for (let i = start; i <= limit; i++) {
    const bn = BigInt(i);
    const report = typeof anyNRouter === "function" ? anyNRouter(i) : null;
    const capture = getCaptureLaw(i, report);

    if (capture.law === "NO LAW FOUND") {
      return {
        found: true,
        seed: i,
        steps: report ? report.steps : "—",
        door: report ? report.door : "—",
        message: `First seed with no law: ${i}`
      };
    }
  }

  return {
    found: false,
    message: `No uncaptured seed found in range [${start}, ${limit}]. All seeds covered by a law.`
  };
}

// =====================================================
// STEP 4 — PRINT PROOF MODE REPORT
// =====================================================
function printProofModeReport(seeds) {
  const { results, byLaw } = runProofMode(seeds);

  console.log("=".repeat(60));
  console.log("  PROOF MODE REPORT — Luis Collatz Workbench");
  console.log("=".repeat(60));

  // Per-seed
  console.log("\n── PER SEED ──────────────────────────────────────────");
  for (const r of results) {
    console.log(`\n  seed ${r.seed}`);
    console.log(`  ${r.status}`);
    console.log(`  Law    : ${r.law}`);
    console.log(`  Reason : ${r.reason}`);
    console.log(`  Steps  : ${r.steps}   Door: ${r.door}`);
  }

  // Grouped by law
  console.log("\n── GROUPED BY LAW ────────────────────────────────────");
  for (const [law, lawSeeds] of Object.entries(byLaw)) {
    console.log(`\n  [${law}]`);
    console.log(`  Seeds (${lawSeeds.length}): ${lawSeeds.slice(0, 20).join(", ")}${lawSeeds.length > 20 ? " ..." : ""}`);
  }

  // First no-law seed (scan up to max seed in list)
  const maxSeed = Math.max(...seeds.map(Number));
  console.log("\n── FIRST SEED WITH NO LAW ────────────────────────────");
  const noLaw = findFirstNoLaw(1, maxSeed);
  console.log(`  ${noLaw.message}`);

  console.log("\n" + "=".repeat(60));

  return { results, byLaw, noLaw };
}

// =====================================================
// QUICK TEST — remove or comment out if importing
// =====================================================
const TEST_SEEDS = [
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
  15, 16, 17, 27, 31, 32, 33, 63, 64, 65,
  127, 128, 129, 255, 256, 257,
  703, 871, 6171, 77031, 837799
];

printProofModeReport(TEST_SEEDS);
