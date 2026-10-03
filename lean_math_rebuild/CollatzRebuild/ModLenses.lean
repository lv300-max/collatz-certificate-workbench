import Mathlib

set_option autoImplicit false

namespace CollatzRebuild

def activeMods : List Nat := (List.range 12).map (fun i => i + 1)

def modAddress (modulus n : Nat) : Nat := n % modulus

def modTrace (modulus : Nat) (route : List Nat) : List Nat :=
  route.map (fun n => modAddress modulus n)

def everyModTrace (route : List Nat) : List (Nat × List Nat) :=
  activeMods.map (fun modulus => (modulus, modTrace modulus route))

theorem active_mod_count : activeMods.length = 12 := by decide

theorem mod_trace_length (modulus : Nat) (route : List Nat) :
    (modTrace modulus route).length = route.length := by simp [modTrace]

theorem every_mod_trace_length (route : List Nat) :
    (everyModTrace route).length = 12 := by simp [everyModTrace, activeMods]

theorem exact_values_have_exact_mod_addresses
    (a b modulus : Nat) (h : a = b) :
    a % modulus = b % modulus := by simpa [h]

end CollatzRebuild
