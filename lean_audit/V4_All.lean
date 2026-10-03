import Mathlib

set_option autoImplicit false

namespace VelazquezEveryNRouteID
def collatz (n : Nat) : Nat :=
  if n % 2 = 0 then n / 2 else 3 * n + 1
def routePrefix : Nat → Nat → List Nat
  | n, 0 => [n]
  | n, fuel + 1 =>
      if n = 1 then [1]
      else n :: routePrefix (collatz n) fuel
def entryDigit (n : Nat) : Nat := n % 10
def everyNID (n fuel : Nat) : List Nat :=
  (routePrefix n fuel).map entryDigit
theorem every_n_has_a_deterministic_route_prefix
    (n fuel : Nat) :
    ∃ r : List Nat, r = routePrefix n fuel := by
  exact ⟨routePrefix n fuel, rfl⟩
theorem every_n_has_a_deterministic_id_prefix
    (n fuel : Nat) :
    ∃ id : List Nat, id = everyNID n fuel := by
  exact ⟨everyNID n fuel, rfl⟩
theorem route_prefix_starts_at_n
    (n fuel : Nat) :
    (routePrefix n fuel).head? = some n := by
  cases fuel <;> simp [routePrefix]
  split <;> simp [routePrefix, *]
theorem id_prefix_starts_at_entry_digit
    (n fuel : Nat) :
    (everyNID n fuel).head? = some (n % 10) := by
  simp [everyNID, route_prefix_starts_at_n, entryDigit]
#print axioms every_n_has_a_deterministic_route_prefix
#print axioms every_n_has_a_deterministic_id_prefix
end VelazquezEveryNRouteID

namespace VelazquezTenEntry
def Entry (n : Nat) : List Nat :=
  [(16 * n) % 10, (8 * n) % 10, (4 * n) % 10, (2 * n) % 10, n % 10]
theorem entry_0 (n : Nat) (h : n % 10 = 0) :
    Entry n = [0,0,0,0,0] := by simp [Entry]; omega
theorem entry_1 (n : Nat) (h : n % 10 = 1) :
    Entry n = [6,8,4,2,1] := by simp [Entry]; omega
theorem entry_2 (n : Nat) (h : n % 10 = 2) :
    Entry n = [2,6,8,4,2] := by simp [Entry]; omega
theorem entry_3 (n : Nat) (h : n % 10 = 3) :
    Entry n = [8,4,2,6,3] := by simp [Entry]; omega
theorem entry_4 (n : Nat) (h : n % 10 = 4) :
    Entry n = [4,2,6,8,4] := by simp [Entry]; omega
theorem entry_5 (n : Nat) (h : n % 10 = 5) :
    Entry n = [0,0,0,0,5] := by simp [Entry]; omega
theorem entry_6 (n : Nat) (h : n % 10 = 6) :
    Entry n = [6,8,4,2,6] := by simp [Entry]; omega
theorem entry_7 (n : Nat) (h : n % 10 = 7) :
    Entry n = [2,6,8,4,7] := by simp [Entry]; omega
theorem entry_8 (n : Nat) (h : n % 10 = 8) :
    Entry n = [8,4,2,6,8] := by simp [Entry]; omega
theorem entry_9 (n : Nat) (h : n % 10 = 9) :
    Entry n = [4,2,6,8,9] := by simp [Entry]; omega
theorem ten_entry_exhaustive (n : Nat) :
    Entry n = [0,0,0,0,0] ∨
    Entry n = [6,8,4,2,1] ∨
    Entry n = [2,6,8,4,2] ∨
    Entry n = [8,4,2,6,3] ∨
    Entry n = [4,2,6,8,4] ∨
    Entry n = [0,0,0,0,5] ∨
    Entry n = [6,8,4,2,6] ∨
    Entry n = [2,6,8,4,7] ∨
    Entry n = [8,4,2,6,8] ∨
    Entry n = [4,2,6,8,9] := by
  have hlt : n % 10 < 10 := Nat.mod_lt n (by omega)
  have hcases :
      n % 10 = 0 ∨ n % 10 = 1 ∨ n % 10 = 2 ∨ n % 10 = 3 ∨
      n % 10 = 4 ∨ n % 10 = 5 ∨ n % 10 = 6 ∨ n % 10 = 7 ∨
      n % 10 = 8 ∨ n % 10 = 9 := by omega
  rcases hcases with h|h|h|h|h|h|h|h|h|h
  · exact Or.inl (entry_0 n h)
  · exact Or.inr (Or.inl (entry_1 n h))
  · exact Or.inr (Or.inr (Or.inl (entry_2 n h)))
  · exact Or.inr (Or.inr (Or.inr (Or.inl (entry_3 n h))))
  · exact Or.inr (Or.inr (Or.inr (Or.inr (Or.inl (entry_4 n h)))))
  · exact Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inl (entry_5 n h))))))
  · exact Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inl (entry_6 n h)))))))
  · exact Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inl (entry_7 n h))))))))
  · exact Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inl (entry_8 n h)))))))))
  · exact Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (Or.inr (entry_9 n h)))))))))
#print axioms ten_entry_exhaustive
end VelazquezTenEntry

namespace VelazquezOddFloor
def twoAdicDepthAux (n : Nat) : Nat → Nat
  | 0 => 0
  | fuel + 1 =>
      if n ≠ 0 ∧ n % 2 = 0 then
        1 + twoAdicDepthAux (n / 2) fuel
      else 0
def twoAdicDepth (n : Nat) : Nat := twoAdicDepthAux n n
def oddFloor (n : Nat) : Nat := n / 2 ^ twoAdicDepth n
def IsOddFloorDecomposition (n k v : Nat) : Prop :=
  n = 2 ^ k * v ∧ v % 2 = 1
def UniqueOddFloorClosure : Prop :=
  ∀ n : Nat, 0 < n →
    ∃! p : Nat × Nat, n = 2 ^ p.1 * p.2 ∧ p.2 % 2 = 1
#check UniqueOddFloorClosure
end VelazquezOddFloor

namespace VelazquezFiveVLock
def phi (m : Nat) : List Nat :=
  [(16*m)%10, (8*m)%10, (4*m)%10, (2*m)%10, m%10]
def IsResolvedVLock (x : List Nat) : Prop :=
  x = [6,8,4,2,1] ∨ x = [8,4,2,6,3] ∨ x = [0,0,0,0,5] ∨
  x = [2,6,8,4,7] ∨ x = [4,2,6,8,9]
theorem odd_ending_has_one_of_five
    (m : Nat) (hodd : m % 2 = 1) :
    IsResolvedVLock (phi m) := by
  have hlt : m % 10 < 10 := Nat.mod_lt m (by omega)
  have hmod2 : (m % 10) % 2 = 1 := by
    have hd : 2 ∣ 10 := by omega
    exact (Nat.mod_mod_of_dvd m hd).trans hodd
  have hcases :
      m % 10 = 1 ∨ m % 10 = 3 ∨ m % 10 = 5 ∨ m % 10 = 7 ∨ m % 10 = 9 := by
    omega
  rcases hcases with h|h|h|h|h
  all_goals
    unfold IsResolvedVLock phi
    simp [Nat.mul_mod, h]
#print axioms odd_ending_has_one_of_five
end VelazquezFiveVLock

namespace VelazquezVLockInvariant
def SameOddFloor (a b : Nat) : Prop :=
  ∃ v ka kb : Nat, v % 2 = 1 ∧ a = 2 ^ ka * v ∧ b = 2 ^ kb * v
theorem dyadic_family_has_same_odd_representative
    (v r : Nat) (hv : v % 2 = 1) :
    SameOddFloor v (2 ^ r * v) := by
  refine ⟨v, 0, r, hv, ?_, ?_⟩
  · simp
  · rfl
#print axioms dyadic_family_has_same_odd_representative
end VelazquezVLockInvariant

namespace VelazquezOddStep
def collatz (n : Nat) : Nat :=
  if n % 2 = 0 then n / 2 else 3*n + 1
theorem odd_kick_is_even
    (n : Nat) (hodd : n % 2 = 1) :
    (3*n + 1) % 2 = 0 := by omega
theorem odd_kick_has_first_halving
    (n : Nat) (hodd : n % 2 = 1) :
    ∃ q : Nat, 3*n + 1 = 2*q := by
  refine ⟨(3*n + 1)/2, ?_⟩
  have hEven : (3*n + 1) % 2 = 0 := odd_kick_is_even n hodd
  omega
theorem first_halving_quotient_unique
    (n q₁ q₂ : Nat)
    (h₁ : 3*n + 1 = 2*q₁)
    (h₂ : 3*n + 1 = 2*q₂) :
    q₁ = q₂ := by omega
#print axioms odd_kick_is_even
#print axioms odd_kick_has_first_halving
#print axioms first_halving_quotient_unique
end VelazquezOddStep

namespace VelazquezAffineClosure
theorem combine_one_odd_phase
    (start node next oddMoves totalHalvings beta drops : Nat)
    (hNode : 3 ^ oddMoves * start + beta = node * 2 ^ totalHalvings)
    (hPhase : 3 * node + 1 = next * 2 ^ drops) :
    3 ^ (oddMoves + 1) * start + (3 * beta + 2 ^ totalHalvings) =
      next * 2 ^ (totalHalvings + drops) := by
  calc
    3 ^ (oddMoves + 1) * start + (3 * beta + 2 ^ totalHalvings)
        = 3 * (3 ^ oddMoves * start + beta) + 2 ^ totalHalvings := by
            rw [pow_succ]; ring
    _ = 3 * (node * 2 ^ totalHalvings) + 2 ^ totalHalvings := by rw [hNode]
    _ = (3 * node + 1) * 2 ^ totalHalvings := by ring
    _ = (next * 2 ^ drops) * 2 ^ totalHalvings := by rw [hPhase]
    _ = next * 2 ^ (totalHalvings + drops) := by rw [pow_add]; ring
theorem direct_23_to_1 :
    (3^4 * 23 + 185) / 2^11 = 1 := by norm_num
theorem direct_75_to_1 :
    (3^3 * 75 + 23) / 2^11 = 1 := by norm_num
#print axioms combine_one_odd_phase
#print axioms direct_23_to_1
#print axioms direct_75_to_1
end VelazquezAffineClosure

namespace VelazquezResidueForcing
def SameCylinder (A r n : Nat) : Prop :=
  n % 2^(A+1) = r % 2^(A+1)
def ExactResidueForcingClosure : Prop :=
  ∀ A r n : Nat, SameCylinder A r n → True
#check ExactResidueForcingClosure
end VelazquezResidueForcing

namespace VelazquezOddResidues
def K : Nat := 16
def M : Nat := 2^K
def laneResidue (n : Nat) : Nat := n % M
def LaneOwns (r n : Nat) : Prop := n % M = r
theorem modulus_exact : M = 65536 := by norm_num [M, K]
theorem odd_class_count_exact : 2^(K-1) = 32768 := by norm_num [K]
theorem every_n_has_one_residue (n : Nat) :
    LaneOwns (laneResidue n) n := by rfl
theorem owned_residue_unique
    (n r₁ r₂ : Nat)
    (h₁ : LaneOwns r₁ n) (h₂ : LaneOwns r₂ n) :
    r₁ = r₂ := by exact h₁.symm.trans h₂
theorem odd_residue_stays_odd
    (n : Nat) (hodd : n % 2 = 1) :
    (laneResidue n) % 2 = 1 := by
  have hd : 2 ∣ M := by norm_num [M, K]
  unfold laneResidue
  exact (Nat.mod_mod_of_dvd n hd).trans hodd
#print axioms every_n_has_one_residue
#print axioms owned_residue_unique
#print axioms odd_residue_stays_odd
end VelazquezOddResidues

namespace VelazquezExactDescent
theorem even_descent
    (n : Nat) (hn : 0 < n) (heven : n % 2 = 0) :
    n / 2 < n := by
  exact Nat.div_lt_self hn (by omega)
theorem affine_gap_descent_core
    (n y A s b G : Nat)
    (hFormula : y * 2^A = 3^s * n + b)
    (hGap : G + 3^s = 2^A)
    (hStrict : b < G * n) :
    y < n := by
  have hPow : 0 < 2^A := by positivity
  nlinarith
#print axioms even_descent
#print axioms affine_gap_descent_core
end VelazquezExactDescent

namespace VelazquezExactStateRouting
structure ExactState where
  residue : Nat
  certK : Nat
  oddSteps : Nat
  halvings : Nat
  beta : Nat
  gap : Nat
  threshold : Nat
  nextState : Option Nat
deriving Repr, DecidableEq
def StateSemanticallyValid (row : ExactState) : Prop :=
  0 < row.certK ∧ row.residue < 2^row.certK
def ExactStateRoutingClosure (rows : List ExactState) : Prop :=
  rows.length = 1235 ∧ ∀ row ∈ rows, StateSemanticallyValid row
#check ExactStateRoutingClosure
end VelazquezExactStateRouting

namespace VelazquezBridgeClosure
def Bmax : Nat := 199242
def bridgeCeiling : Nat := 200001
theorem threshold_inside_bridge : Bmax < bridgeCeiling := by
  norm_num [Bmax, bridgeCeiling]
def collatz (n : Nat) : Nat :=
  if n % 2 = 0 then n/2 else 3*n+1
def HasBelowSelf (n : Nat) : Prop :=
  ∃ m : Nat, 0 < m ∧ Nat.iterate collatz m n < n
def DirectBridgeClosure : Prop :=
  ∀ n : Nat, 3 ≤ n → n ≤ bridgeCeiling → n % 2 = 1 → HasBelowSelf n
#print axioms threshold_inside_bridge
#check DirectBridgeClosure
end VelazquezBridgeClosure

namespace VelazquezEveryNBelowSelf
def collatz (n : Nat) : Nat :=
  if n % 2 = 0 then n/2 else 3*n+1
def EveryNBelowSelf : Prop :=
  ∀ n : Nat, 1 < n →
    ∃ m : Nat, 0 < m ∧ Nat.iterate collatz m n < n
#check EveryNBelowSelf
end VelazquezEveryNBelowSelf

namespace VelazquezTermination
def collatz (n : Nat) : Nat :=
  if n % 2 = 0 then n/2 else 3*n+1
def Terminates (n : Nat) : Prop :=
  ∃ t : Nat, Nat.iterate collatz t n = 1
def HasBelowSelf (n : Nat) : Prop :=
  ∃ m : Nat, 0 < m ∧ Nat.iterate collatz m n < n
lemma collatz_positive
    (n : Nat) (hn : 0 < n) :
    0 < collatz n := by
  unfold collatz
  split <;> omega
lemma iterate_positive
    (n t : Nat) (hn : 0 < n) :
    0 < Nat.iterate collatz t n := by
  induction t generalizing n with
  | zero => simpa using hn
  | succ t ih =>
      rw [Function.iterate_succ_apply]
      exact ih (collatz n) (collatz_positive n hn)
theorem terminates_from_universal_below_self
    (hDescent : ∀ n : Nat, 1 < n → HasBelowSelf n) :
    ∀ n : Nat, 0 < n → Terminates n := by
  intro n
  induction n using Nat.strong_induction_on with
  | h n ih =>
      intro hn
      by_cases hOne : n = 1
      · subst n
        exact ⟨0, rfl⟩
      · have hgt : 1 < n := by omega
        rcases hDescent n hgt with ⟨m, hmPos, hmLt⟩
        let q := Nat.iterate collatz m n
        have hqPos : 0 < q := iterate_positive n m hn
        have hqTerm : Terminates q := ih q hmLt hqPos
        rcases hqTerm with ⟨j, hj⟩
        refine ⟨j + m, ?_⟩
        simpa [q, Function.iterate_add_apply] using hj
#print axioms terminates_from_universal_below_self
end VelazquezTermination

namespace VelazquezCycleExclusion
def collatz (n : Nat) : Nat :=
  if n % 2 = 0 then n/2 else 3*n+1
def HasBelowSelf (n : Nat) : Prop :=
  ∃ m : Nat, 0 < m ∧ Nat.iterate collatz m n < n
def IsPeriodicFrom (n : Nat) : Prop :=
  ∃ p : Nat, 0 < p ∧ Nat.iterate collatz p n = n
def UniversalBelowSelf : Prop :=
  ∀ n : Nat, 1 < n → HasBelowSelf n
#check UniversalBelowSelf
#check IsPeriodicFrom
end VelazquezCycleExclusion

namespace VelazquezOneStep
theorem combine_one_phase
    (start node next o C beta c : Nat)
    (hAccum : 3^o * start + beta = node * 2^C)
    (hPhase : 3*node + 1 = next * 2^c) :
    3^(o+1) * start + (3*beta + 2^C) = next * 2^(C+c) := by
  calc
    3^(o+1) * start + (3*beta + 2^C)
        = 3*(3^o * start + beta) + 2^C := by rw [pow_succ]; ring
    _ = 3*(node * 2^C) + 2^C := by rw [hAccum]
    _ = (3*node + 1) * 2^C := by ring
    _ = (next * 2^c) * 2^C := by rw [hPhase]
    _ = next * 2^(C+c) := by rw [pow_add]; ring
theorem terminal_one_step_identity
    (N o C beta : Nat)
    (h : 3^o * N + beta = 2^C) :
    (3^o * N + beta) / 2^C = 1 := by
  rw [h]; simp
theorem seed23 : 3^4 * 23 + 185 = 2^11 := by norm_num
theorem seed75 : 3^3 * 75 + 23 = 2^11 := by norm_num
#print axioms combine_one_phase
#print axioms terminal_one_step_identity
#print axioms seed23
#print axioms seed75
end VelazquezOneStep

namespace VelazquezReverse
theorem reverse_one_phase
    (prev next c : Nat)
    (h : 3*prev + 1 = next * 2^c) :
    (next * 2^c - 1) / 3 = prev := by
  rw [← h]; simp
theorem reverse_accumulated_start
    (N o C beta : Nat)
    (h : 3^o * N + beta = 2^C) :
    (2^C - beta) / 3^o = N := by
  rw [← h]; simp
theorem reverse_23 : (2^11 - 185) / 3^4 = 23 := by norm_num
theorem reverse_75 : (2^11 - 23) / 3^3 = 75 := by norm_num
#print axioms reverse_one_phase
#print axioms reverse_accumulated_start
#print axioms reverse_23
#print axioms reverse_75
end VelazquezReverse

namespace VelazquezBeehiveAddress
def H : Nat := 1849
def cell (n : Nat) : Nat := n % H
def level (n : Nat) : Nat := n / H
theorem H_exact : H = 43^2 := by norm_num [H]
theorem address_reconstructs (n : Nat) :
    n = level n * H + cell n := by
  unfold level cell
  simpa [Nat.add_comm, Nat.mul_comm] using (Nat.mod_add_div n H).symm
theorem cell_in_range (n : Nat) : cell n < H := by
  unfold cell
  exact Nat.mod_lt n (by norm_num [H])
theorem address_cell_unique
    (n c k : Nat) (hc : c < H) (h : n = k*H + c) :
    cell n = c := by
  subst n
  unfold cell
  have hc' : c % H = c := Nat.mod_eq_of_lt hc
  simp [Nat.add_mod, Nat.mul_mod, hc', H]
theorem address_level_unique
    (n c k : Nat) (hc : c < H) (h : n = k*H + c) :
    level n = k := by
  subst n
  unfold level
  rw [Nat.add_div (k * H) c]
  simp [Nat.mul_div_left, Nat.div_eq_of_lt hc]
#print axioms address_reconstructs
#print axioms address_cell_unique
#print axioms address_level_unique
end VelazquezBeehiveAddress
