import CollatzRebuild.Core

set_option autoImplicit false

namespace CollatzRebuild

theorem pow_two_even (k : Nat) :
    (2 ^ (k + 1)) % 2 = 0 := by
  simp [pow_succ]

theorem T_pow_two_succ (k : Nat) :
    T (2 ^ (k + 1)) = 2 ^ k := by
  simp [T, pow_two_even, pow_succ]

theorem iter_pow_two (k : Nat) :
    iter k (2 ^ k) = 1 := by
  induction k with
  | zero => simp [iter]
  | succ k ih =>
      simp [iter, T_pow_two_succ, ih]

theorem power_two_terminates (k : Nat) :
    Terminates (2 ^ k) := by
  exact ⟨k, iter_pow_two k⟩

end CollatzRebuild
