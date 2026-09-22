# DEL C, C6 — conversion from QE's raw `elop` tensor to the conventional Pockels tensor

This derives the equations needed to go from QE's raw output to a conventional r_ijk in
pm/V, so the result is independently reproducible from `ph.out` alone. Numbers are filled
in once C2/C3 produce actual output; this section is the methodology.

## 1. What QE gives us

Per `results/ELop_IMPLEMENTATION_NOTES.md` (source: `PHonon/PH/el_opt.f90`), QE's raw,
symmetrized, cartesian-axis tensor is

  QE_raw_ijk = dε_ij / dE_k    (electronic/clamped-ion only, Rydberg a.u.)

reported in Rydberg atomic units, convertible to pm/V for the *same* dε/dE quantity by
the source-documented factor 2.7502 (see ELop_IMPLEMENTATION_NOTES.md for the caveat on
this factor's independent re-derivation). This is **not yet** r_ijk — two more steps are
needed.

## 2. Susceptibility convention

ε_ij = δ_ij + 4π χ_ij (Gaussian/Rydberg convention, consistent with QE's `fpi` = 4π
appearing explicitly in `el_opt.f90`'s `fac` expression). QE's own comment "to obtain the
static chi^2 multiply by 1/2" means

  chi2_ijk (static, QE's internal convention) = (1/2) * QE_raw_ijk

This chi2 is the second-order (quadratic electro-optic / Pockels-adjacent) susceptibility
in QE's normalization — but note this is *not yet* guaranteed to equal the standard SI/CGS
χ⁽²⁾ used in nonlinear-optics literature without also tracking the 4π/ε₀ factors hidden in
the Gaussian-vs-SI unit choice. Because the target quantity here is r_ijk (which absorbs
the ε_ii·ε_jj normalization directly, see step 3), we do **not** need to resolve the
absolute χ⁽²⁾ SI normalization separately — it cancels out of the final r_ijk definition
as long as dε/dE is used consistently. This is stated explicitly so no hidden factor is
silently dropped.

## 3. From dε/dE to r_ijk (impermeability form)

The conventional (Pockels) linear electro-optic coefficient is defined via the
impermeability tensor η_ij = (1/n²)_ij = (ε⁻¹)_ij:

  Δη_ij = Δ(1/n²)_ij = Σ_k r_ijk E_k

Differentiating ε⁻¹ with respect to E_k using d(ε⁻¹)/dE = -ε⁻¹ (dε/dE) ε⁻¹ (standard
matrix-derivative identity):

  r_ijk = -[ε⁻¹ (dε/dE_k) ε⁻¹]_ij

For Material A's B2 geometry, ε is diagonal in the crystal Cartesian frame (ε_xy = ε_xz =
ε_yz = 0, confirmed in DEL B, §7 of `DEL_B_STRUCTURAL_RELAXATION.md`), so this simplifies
to a direct elementwise relation for each independent component:

  r_ijk = - (dε_ij/dE_k) / (ε_ii · ε_jj)     [i, j both diagonal-frame indices]

This uses the **raw electronic dε/dE from QE directly** (not the "static chi^2"
intermediate from step 2 — that factor-of-1/2 quantity is a different, named object QE
also reports and must not be substituted here by mistake). ε_ii, ε_jj are the **static**
(zero-frequency-limit-of-this-DFPT, i.e. the `epsil=.true.` output) principal dielectric
constants already measured in DEL A/B/C0 (ε_xx=ε_yy=5.493765, ε_zz=5.328291 for B2).

## 4. Units

* dε_ij/dE_k: Rydberg a.u. → pm/V via the ×2.7502 factor (§1).
* ε_ii, ε_jj: dimensionless (already SI/Gaussian-consistent relative permittivity).
* Therefore r_ijk (pm/V) = -2.7502 × QE_raw_ijk(Ry a.u.) / (ε_ii · ε_jj), with QE_raw_ijk
  taken from the **total** (`il=1`) printed tensor (electronic + XC-derivative terms
  combined) unless the electronic-only contribution is specifically wanted (QE prints
  that separately as "contribution # 1" per the source, see implementation notes).

## 5. Cartesian ↔ crystal axis

QE's tensor is already reported "in cartesian axis" post-symmetrization (`symmatrix3`
call in `el_opt.f90`), in the **same Cartesian frame as the CELL_PARAMETERS / stress
tensor** used throughout DEL A/B/C — i.e. the frame in which our primitive rhombohedral
cell vectors are expressed (not the conventional hexagonal a,b,c frame). Converting to
the conventional hexagonal crystallographic frame (z ‖ c-axis, standard for reporting
3m-class r_ijk against the textbook contracted form in §C5) requires the same rotation
used in `00_environment/structure_source.md` relating the primitive and conventional
cells. This rotation is applied in `results/eo_tensor_converted.csv` (C7), not silently
folded into this equation.

## 6. Index ordering (contracted notation)

Standard Voigt-like contraction for a 3x3x3 tensor symmetric in the first two indices
(i,j): μ = 1..6 via (11)→1, (22)→2, (33)→3, (23)/(32)→4, (13)/(31)→5, (12)/(21)→6, so
`r_μk` is a 6×3 matrix. This is the form C7's coefficient table uses.
