import Mathlib

set_option autoImplicit false

namespace CollatzRebuild

def scaledSeed (oddBase power : Nat) : Nat := oddBase * 30 ^ power
def scaledOddFloor (oddBase power : Nat) : Nat := oddBase * 15 ^ power

theorem thirty_power_factorization (power : Nat) :
    30 ^ power = 2 ^ power * 15 ^ power := by
  calc
    30 ^ power = (2 * 15) ^ power := by norm_num
    _ = 2 ^ power * 15 ^ power := by rw [mul_pow]

theorem scaled_seed_factorization (oddBase power : Nat) :
    scaledSeed oddBase power = scaledOddFloor oddBase power * 2 ^ power := by
  simp [scaledSeed, scaledOddFloor, thirty_power_factorization]
  ring

theorem scaled_initial_drop (oddBase power : Nat) :
    scaledSeed oddBase power / 2 ^ power = scaledOddFloor oddBase power := by
  rw [scaled_seed_factorization]
  simp

theorem multiplier5_closure : (3 ^ 1 * 5 + 1) / 2 ^ 4 = 1 := by norm_num
theorem multiplier7_closure : (3 ^ 5 * 7 + 347) / 2 ^ 11 = 1 := by norm_num
theorem multiplier9_closure : (3 ^ 6 * 9 + 1631) / 2 ^ 13 = 1 := by norm_num

end CollatzRebuild
