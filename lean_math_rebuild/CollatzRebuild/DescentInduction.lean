import CollatzRebuild.Core

set_option autoImplicit false

namespace CollatzRebuild

theorem terminates_from_global_descent
    (hglobal : ∀ n : Nat, 1 < n → Terminates n ∨ HasDescent n) :
    ∀ n : Nat, 0 < n → Terminates n := by
  intro n
  induction n using Nat.strong_induction_on with
  | h n ih =>
      intro hnpos
      by_cases h1 : n = 1
      · simpa [h1] using terminates_one
      · have hn1 : 1 < n := by omega
        rcases hglobal n hn1 with hterm | hdesc
        · exact hterm
        · rcases hdesc with ⟨k, v, hvpos, hvlt, hreach⟩
          have hvterm : Terminates v := ih v hvlt hvpos
          exact terminates_of_reaches hreach hvterm

theorem no_positive_exception_from_global_descent
    (hglobal : ∀ n : Nat, 1 < n → Terminates n ∨ HasDescent n) :
    ¬ ∃ n : Nat, 0 < n ∧ ¬ Terminates n := by
  rintro ⟨n, hn, hbad⟩
  exact hbad (terminates_from_global_descent hglobal n hn)

end CollatzRebuild
