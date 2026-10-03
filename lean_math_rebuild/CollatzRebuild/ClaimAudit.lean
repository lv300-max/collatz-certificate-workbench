import CollatzRebuild.K12ResidueAudit
import CollatzRebuild.ExactStateEvidence
import CollatzRebuild.FrontierEvidence
import CollatzRebuild.UniversalClosure

set_option autoImplicit false

namespace CollatzRebuild

theorem rebuilt_finite_facts :
    oddResidues.length = 2048 ∧
    k12ClosedResidues.length = 1632 ∧
    k12DeepResidues.length = 416 ∧
    exactStateTotal = 1235 ∧
    exactStateStillOpen = 0 ∧
    frontierStillDebt = 0 := by
  exact ⟨odd_residue_count, k12_closed_count, k12_deep_count, rfl, rfl, rfl⟩

theorem k12_layer_requires_deep_argument : k12DeepResidues ≠ [] :=
  k12_has_deep_residues

end CollatzRebuild
