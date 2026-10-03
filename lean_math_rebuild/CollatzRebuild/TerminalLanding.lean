import Mathlib

set_option autoImplicit false

namespace CollatzRebuild

def standardTerminalLanding (oddEnding : Nat) : Nat :=
  (3 * oddEnding + 1) % 10

def targetZeroAddition : Nat → Nat
  | 1 => 7 | 3 => 1 | 5 => 5 | 7 => 9 | 9 => 3 | _ => 1

def targetSixAddition : Nat → Nat
  | 1 => 3 | 3 => 7 | 5 => 1 | 7 => 5 | 9 => 9 | _ => 1

def terminalLanding (oddEnding addition : Nat) : Nat :=
  (3 * oddEnding + addition) % 10

theorem standard_endings :
    standardTerminalLanding 1 = 4 ∧
    standardTerminalLanding 3 = 0 ∧
    standardTerminalLanding 5 = 6 ∧
    standardTerminalLanding 7 = 2 ∧
    standardTerminalLanding 9 = 8 := by decide

theorem target_zero_all_five :
    terminalLanding 1 (targetZeroAddition 1) = 0 ∧
    terminalLanding 3 (targetZeroAddition 3) = 0 ∧
    terminalLanding 5 (targetZeroAddition 5) = 0 ∧
    terminalLanding 7 (targetZeroAddition 7) = 0 ∧
    terminalLanding 9 (targetZeroAddition 9) = 0 := by decide

theorem target_six_all_five :
    terminalLanding 1 (targetSixAddition 1) = 6 ∧
    terminalLanding 3 (targetSixAddition 3) = 6 ∧
    terminalLanding 5 (targetSixAddition 5) = 6 ∧
    terminalLanding 7 (targetSixAddition 7) = 6 ∧
    terminalLanding 9 (targetSixAddition 9) = 6 := by decide

theorem ending5_standard_lands6
    (n : Nat) (h : n % 10 = 5) :
    (3 * n + 1) % 10 = 6 := by omega

theorem ending5_add5_lands0
    (n : Nat) (h : n % 10 = 5) :
    (3 * n + 5) % 10 = 0 := by omega

end CollatzRebuild
