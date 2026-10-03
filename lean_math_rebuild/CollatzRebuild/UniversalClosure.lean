import CollatzRebuild.DescentInduction

set_option autoImplicit false

namespace CollatzRebuild

def GlobalDescentStatement : Prop :=
  ∀ n : Nat, 1 < n → Terminates n ∨ HasDescent n

theorem universal_collatz_closure_from_global_descent
    (h : GlobalDescentStatement) :
    ∀ n : Nat, 0 < n → Terminates n := by
  exact terminates_from_global_descent h

theorem no_positive_exception_from_global_statement
    (h : GlobalDescentStatement) :
    ¬ ∃ n : Nat, 0 < n ∧ ¬ Terminates n := by
  exact no_positive_exception_from_global_descent h

end CollatzRebuild
