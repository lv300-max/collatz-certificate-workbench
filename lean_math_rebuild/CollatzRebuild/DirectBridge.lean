import CollatzRebuild.Core

set_option autoImplicit false
set_option maxRecDepth 1000000
set_option maxHeartbeats 0

namespace CollatzRebuild

def reachesOneWithin : Nat → Nat → Bool
  | 0, n => n == 1
  | fuel + 1, n =>
      if n == 1 then true else reachesOneWithin fuel (T n)

theorem reachesOneWithin_sound
    (fuel n : Nat)
    (h : reachesOneWithin fuel n = true) :
    Terminates n := by
  induction fuel generalizing n with
  | zero =>
      simp [reachesOneWithin] at h
      subst n
      exact terminates_one
  | succ fuel ih =>
      by_cases hn : n = 1
      · subst n
        exact terminates_one
      · simp [reachesOneWithin, hn] at h
        rcases ih (T n) h with ⟨k, hk⟩
        refine ⟨k + 1, ?_⟩
        simpa [Nat.add_comm, iter] using hk

def DIRECT_BRIDGE_H : Nat := 200001

def directBridgeCheck : Bool :=
  (List.range (DIRECT_BRIDGE_H + 1)).all (fun n =>
    if n = 0 then true else reachesOneWithin 400 n)

theorem direct_bridge_check_pass : directBridgeCheck = true := by
  decide

theorem direct_bridge
    (n : Nat)
    (hnpos : 0 < n)
    (hnle : n ≤ DIRECT_BRIDGE_H) :
    Terminates n := by
  have hmem : n ∈ List.range (DIRECT_BRIDGE_H + 1) := by
    exact List.mem_range.mpr (Nat.lt_succ_of_le hnle)
  have hall := (List.all_eq_true.mp direct_bridge_check_pass) n hmem
  simp [directBridgeCheck, hnpos.ne'] at hall
  exact reachesOneWithin_sound 400 n hall

end CollatzRebuild
