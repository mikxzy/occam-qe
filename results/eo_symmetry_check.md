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

C2 (PBEsol) never produced a tensor (GGA not implemented, see
`ELop_IMPLEMENTATION_NOTES.md`). Checked against both completed LDA (C3) branches —
`LDA@PBEsol-geometry` and `LDA@LDA-relaxed` — using `scripts/eo_analysis.py`, with a
numerical-zero tolerance of 1.0 Ry a.u. (roughly 2.75 pm/V raw, well below the smallest
allowed nonzero component, ~250-420 Ry a.u. — see `results/eo_tensor_converted.csv`).

**Result: 0 of 36 checked slots (2 branches × 18 (i,j)-pair×field-direction combinations)
violate the symmetry-forbidden set.** Every one of the 14 theoretically-zero components
came out at machine-precision noise (≤6×10⁻⁸ Ry a.u.) in both branches — QE's internal
`symmatrix3` symmetrization is doing exactly what it should.

The 4 independent parameters resolve cleanly and match their required equalities to
5+ significant figures (e.g. `LDA@LDA-relaxed`: r1y=-22.4675 pm/V = -r6x exactly;
r2y=+22.4675 pm/V = -r1y exactly; r1z=r2z=+35.0157 pm/V exactly; r5x=r4y=+35.3054 pm/V
exactly). Full raw values: `results/eo_tensor_raw.csv`/`.json`; converted r_μk (pm/V):
`results/eo_tensor_converted.csv`.

**H0-C4 (calculated tensor obeys the expected crystal symmetry within numerical
tolerance): PASS**, for both completed branches.
