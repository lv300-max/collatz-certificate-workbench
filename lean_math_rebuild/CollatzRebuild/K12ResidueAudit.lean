import CollatzRebuild.Core

set_option autoImplicit false
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace CollatzRebuild

def MASTER_K : Nat := 12
def MASTER_MODULUS : Nat := 2 ^ MASTER_K

def oddResidues : List Nat :=
  (List.range 2048).map (fun i => 2 * i + 1)

def oddCount : Nat → Nat → Nat
  | 0, _ => 0
  | m + 1, r =>
      (if r % 2 = 1 then 1 else 0) + oddCount m (T r)

def halfCount : Nat → Nat → Nat
  | 0, _ => 0
  | m + 1, r =>
      (if r % 2 = 0 then 1 else 0) + halfCount m (T r)

def positiveGapAt (r m : Nat) : Bool :=
  3 ^ oddCount m r < 2 ^ halfCount m r

def hasPositiveGapWithin (r k : Nat) : Bool :=
  (List.range k).any (fun j => positiveGapAt r (j + 1))

def k12ClosedResidues : List Nat :=
  oddResidues.filter (fun r => hasPositiveGapWithin r MASTER_K)

def k12DeepResidues : List Nat :=
  oddResidues.filter (fun r => !(hasPositiveGapWithin r MASTER_K))

theorem master_modulus_4096 : MASTER_MODULUS = 4096 := by decide
theorem odd_residue_count : oddResidues.length = 2048 := by decide

theorem k12_closed_count : k12ClosedResidues.length = 1632 := by native_decide
theorem k12_deep_count : k12DeepResidues.length = 416 := by native_decide

theorem k12_has_deep_residues : k12DeepResidues ≠ [] := by
  intro h
  have hz : k12DeepResidues.length = 0 := by simpa [h]
  have hc := k12_deep_count
  omega

end CollatzRebuild
