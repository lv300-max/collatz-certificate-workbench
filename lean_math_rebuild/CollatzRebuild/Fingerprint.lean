import Mathlib

set_option autoImplicit false

namespace CollatzRebuild

inductive Fingerprint where
  | f1 | f3 | f5 | f7 | f9
  deriving Repr, DecidableEq

def Fingerprint.code : Fingerprint → Nat
  | .f1 => 68421
  | .f3 => 84263
  | .f5 => 5
  | .f7 => 26847
  | .f9 => 42689

def oddFloorFuel : Nat → Nat → Nat
  | n, 0 => n
  | n, fuel + 1 =>
      if n ≠ 0 ∧ n % 2 = 0 then oddFloorFuel (n / 2) fuel else n

def oddFloor (n : Nat) : Nat := oddFloorFuel n n

def fingerprintOfOdd (n : Nat) : Fingerprint :=
  match n % 10 with
  | 1 => .f1
  | 3 => .f3
  | 5 => .f5
  | 7 => .f7
  | _ => .f9

def finalFingerprint (n : Nat) : Fingerprint :=
  fingerprintOfOdd (oddFloor n)

theorem odd_last_digit_five_cases
    (n : Nat)
    (hodd : n % 2 = 1) :
    n % 10 = 1 ∨ n % 10 = 3 ∨ n % 10 = 5 ∨ n % 10 = 7 ∨ n % 10 = 9 := by
  omega

theorem fingerprint_ending_1 (n : Nat) (h : n % 10 = 1) :
    (fingerprintOfOdd n).code = 68421 := by simp [fingerprintOfOdd, h, Fingerprint.code]
theorem fingerprint_ending_3 (n : Nat) (h : n % 10 = 3) :
    (fingerprintOfOdd n).code = 84263 := by simp [fingerprintOfOdd, h, Fingerprint.code]
theorem fingerprint_ending_5 (n : Nat) (h : n % 10 = 5) :
    (fingerprintOfOdd n).code = 5 := by simp [fingerprintOfOdd, h, Fingerprint.code]
theorem fingerprint_ending_7 (n : Nat) (h : n % 10 = 7) :
    (fingerprintOfOdd n).code = 26847 := by simp [fingerprintOfOdd, h, Fingerprint.code]
theorem fingerprint_ending_9 (n : Nat) (h : n % 10 = 9) :
    (fingerprintOfOdd n).code = 42689 := by simp [fingerprintOfOdd, h, Fingerprint.code]

theorem every_N_has_one_final_fingerprint (n : Nat) :
    ∃! f : Fingerprint, f = finalFingerprint n := by
  refine ⟨finalFingerprint n, rfl, ?_⟩
  intro y hy
  exact hy

theorem fingerprint_3152 : (finalFingerprint 3152).code = 26847 := by decide
theorem fingerprint_592  : (finalFingerprint 592).code = 26847 := by decide
theorem fingerprint_40   : (finalFingerprint 40).code = 5 := by decide
theorem fingerprint_152  : (finalFingerprint 152).code = 42689 := by decide

end CollatzRebuild
