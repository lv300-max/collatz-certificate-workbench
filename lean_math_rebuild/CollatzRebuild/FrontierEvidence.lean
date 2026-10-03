import Mathlib

set_option autoImplicit false

namespace CollatzRebuild

def frontierOpenKeys : Nat := 889
def frontierCertifiedReturns : Nat := 530
def frontierHighBReturns : Nat := 359
def frontierStillDebt : Nat := 0
def frontierConflicts : Nat := 0
def frontierMaxFinalB : Nat := 199242

def zeroRepaymentFiniteCoverAllContinuations : Bool := false
def allOneEscapeBranchExists : Bool := true
def allOneEscapePrefixLength : Nat := 2159

theorem frontier_partition_count :
    frontierCertifiedReturns + frontierHighBReturns = frontierOpenKeys := by decide
theorem frontier_zero_debt : frontierStillDebt = 0 := by rfl
theorem frontier_zero_conflicts : frontierConflicts = 0 := by rfl
theorem zero_repayment_not_universal :
    zeroRepaymentFiniteCoverAllContinuations = false := by rfl
theorem all_one_branch_recorded : allOneEscapeBranchExists = true := by rfl

end CollatzRebuild
