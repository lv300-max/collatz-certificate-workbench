import Mathlib

set_option autoImplicit false

namespace CollatzRebuild

theorem descent_arithmetic
    (Tm n o c b gap B : Nat)
    (hgap : gap + 3 ^ o = 2 ^ c)
    (hgapPos : 0 < gap)
    (hbound : b ≤ B * gap)
    (hn : B < n)
    (hformula : Tm * 2 ^ c = 3 ^ o * n + b) :
    Tm < n := by
  have hBgap : B * gap < n * gap := by
    exact Nat.mul_lt_mul_of_pos_right hn hgapPos
  have hb : b < n * gap := lt_of_le_of_lt hbound hBgap
  have hpow : 0 < 2 ^ c := pow_pos (by omega) c
  nlinarith

structure AffineCertificate where
  m : Nat
  o : Nat
  c : Nat
  b : Nat
  gap : Nat
  B : Nat
  gapEq : gap + 3 ^ o = 2 ^ c
  gapPos : 0 < gap
  bound : b ≤ B * gap

theorem certificate_descends_above_B
    (cert : AffineCertificate)
    (n Tm : Nat)
    (hn : cert.B < n)
    (hformula : Tm * 2 ^ cert.c = 3 ^ cert.o * n + cert.b) :
    Tm < n := by
  exact descent_arithmetic Tm n cert.o cert.c cert.b cert.gap cert.B
    cert.gapEq cert.gapPos cert.bound hn hformula

end CollatzRebuild
