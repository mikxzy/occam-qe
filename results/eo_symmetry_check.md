# DEL C, C5 — symmetry analysis of the electro-optic tensor

## Point group

DEL A/B confirmed "6 Sym. Ops. (no inversion)" throughout B0/B1/B2 (see
`DEL_B_STRUCTURAL_RELAXATION.md` §3-4) — order-6, no inversion, matching point group
3m (Schoenflies C₃ᵥ). This is used below, not assumed from the compound's identity.

## Theoretical symmetry-allowed form (derived, not looked up)

Rather than quote a textbook table from memory (risk of misremembering a sign or an
index-swap convention), the allowed pattern was derived directly: build the 6 elements
of C₃ᵥ as exact 3×3 orthogonal matrices (C₃ = 120° rotation about z, σᵥ = mirror with
normal along x, and their products), impose invariance of a general 3rd-rank tensor
r_ijk (symmetric in i,j — the same index symmetry as the EO/piezoelectric tensor family)
under all 6 operations as a linear system, and solve its null space exactly (symbolic,
not numerical, to avoid rounding artifacts) — reproducible with any CAS. Result:

* **Group order: 6** (confirms the C₃ᵥ assumption is self-consistent).
* **4 independent components**, with these exact relations (μ = 1..6 Voigt index for
  the symmetric i,j pair: 1=xx, 2=yy, 3=zz, 4=yz, 5=xz, 6=xy; k = field direction x,y,z):

  ```
           k=x     k=y     k=z
  r_1k:  [  0     -A       B  ]
  r_2k:  [  0      A       B  ]
  r_3k:  [  0      0       D  ]
  r_4k:  [  0      C       0  ]
  r_5k:  [  C      0       0  ]
  r_6k:  [ -A      0       0  ]
  ```

  i.e. **r22 = -r12 = -r61** (parameter A), **r13 = r23** (parameter B),
  **r51 = r42** (parameter C), **r33** independent (parameter D). All other 14 of the 18
  symmetric-pair×field-direction components are forced to be exactly zero by symmetry.

This matches the standard class-3m result found in tensor-property references (e.g. Nye,
*Physical Properties of Crystals*) — cross-checked against, not copied from, that source.

## Comparison against QE's raw output

*(Filled in once C2 succeeds — this section reports which of QE's raw output components
land in the theoretically forbidden set and by how much, using an explicit numerical zero
tolerance defined at that point relative to the smallest allowed nonzero component.)*
