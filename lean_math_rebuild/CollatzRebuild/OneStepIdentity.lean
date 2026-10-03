import Mathlib

set_option autoImplicit false

namespace CollatzRebuild

structure DirectState where
  node : Nat
  oddMoves : Nat
  totalHalvings : Nat
  beta : Nat
  threePower : Nat
  deriving Repr, DecidableEq

theorem combine_one_odd_node
    (start node next oddMoves totalHalvings beta drops : Nat)
    (hNode : 3 ^ oddMoves * start + beta = node * 2 ^ totalHalvings)
    (hPhase : 3 * node + 1 = next * 2 ^ drops) :
    3 ^ (oddMoves + 1) * start + (3 * beta + 2 ^ totalHalvings) =
      next * 2 ^ (totalHalvings + drops) := by
  calc
    3 ^ (oddMoves + 1) * start + (3 * beta + 2 ^ totalHalvings) =
        3 * (3 ^ oddMoves * start + beta) + 2 ^ totalHalvings := by
          rw [pow_succ]
          ring
    _ = 3 * (node * 2 ^ totalHalvings) + 2 ^ totalHalvings := by rw [hNode]
    _ = (3 * node + 1) * 2 ^ totalHalvings := by ring
    _ = (next * 2 ^ drops) * 2 ^ totalHalvings := by rw [hPhase]
    _ = next * 2 ^ (totalHalvings + drops) := by
          rw [pow_add]
          ring

theorem direct_equation_to_one
    (start oddMoves totalHalvings beta : Nat)
    (hTerminal : 3 ^ oddMoves * start + beta = 2 ^ totalHalvings) :
    (3 ^ oddMoves * start + beta) / 2 ^ totalHalvings = 1 := by
  rw [hTerminal]
  simp

theorem direct_75_to_one :
    (3 ^ 3 * 75 + 23) / 2 ^ 11 = 1 := by norm_num

theorem direct_23_to_one :
    (3 ^ 4 * 23 + 185) / 2 ^ 11 = 1 := by norm_num

theorem direct_27_to_one :
    (3 ^ 41 * 27 + 195820718533800070543) / 2 ^ 70 = 1 := by norm_num

end CollatzRebuild
