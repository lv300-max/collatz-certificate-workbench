import Mathlib

set_option autoImplicit false

namespace CollatzRebuild

def T (n : Nat) : Nat :=
  if n % 2 = 0 then n / 2 else 3 * n + 1

def iter : Nat → Nat → Nat
  | 0, n => n
  | k + 1, n => iter k (T n)

def Terminates (n : Nat) : Prop :=
  ∃ k : Nat, iter k n = 1

def HasDescent (n : Nat) : Prop :=
  ∃ k v : Nat, 0 < v ∧ v < n ∧ iter k n = v

@[simp] theorem iter_zero (n : Nat) : iter 0 n = n := rfl
@[simp] theorem iter_succ (k n : Nat) : iter (k + 1) n = iter k (T n) := rfl

theorem iter_add (a b n : Nat) :
    iter (a + b) n = iter b (iter a n) := by
  induction a generalizing n with
  | zero => simp [iter]
  | succ a ih =>
      simpa [Nat.succ_add, iter] using ih (T n)

theorem terminates_of_reaches
    {n v k : Nat}
    (hreach : iter k n = v)
    (hv : Terminates v) :
    Terminates n := by
  rcases hv with ⟨j, hj⟩
  refine ⟨k + j, ?_⟩
  rw [iter_add, hreach, hj]

theorem terminates_one : Terminates 1 := by
  exact ⟨0, rfl⟩

theorem even_has_descent
    (n : Nat)
    (hn : 1 < n)
    (heven : n % 2 = 0) :
    HasDescent n := by
  refine ⟨1, n / 2, ?_, ?_, ?_⟩
  · omega
  · omega
  · simp [iter, T, heven]

end CollatzRebuild
