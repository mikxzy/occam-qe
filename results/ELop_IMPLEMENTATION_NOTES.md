# QE 7.5 `elop` implementation notes (DEL C, C1)

Findings below are from QE 7.5's actual source (`PHonon/PH/el_opt.f90`, `PHonon/PH/ramanm.f90`)
and official documentation (`PHonon/Doc/INPUT_PH.txt`), fetched directly from the
`qe-7.5` tag of `github.com/QEF/q-e` — not from memory, per instruction. Exact URLs and
line numbers below so this is independently checkable.

## What `elop=.true.` actually computes

Source: [`PHonon/PH/el_opt.f90`](https://github.com/QEF/q-e/blob/qe-7.5/PHonon/PH/el_opt.f90)

The routine's own write-out (lines 148-153) states, verbatim:

> "Electro-optic tensor is defined as the derivative of the dielectric tensor with
> respect to one electric field, units are Rydberg a.u.; to obtain the static chi^2
> multiply by 1/2; to convert to pm/Volt multiply per 2.7502"

**This is a purely electronic (clamped-ion) quantity.** The subroutine computes two
physical terms and sums them (lines 45-73, 90-125):

1. A wavefunction-response term (`ps`, built from `depsi`/`chif` buffers — the
   electric-field-perturbed wavefunctions and their "chi" auxiliary functions from the
   linear-response machinery already computed by `epsil=.true.`/`trans=.true.`), and
2. An exchange-correlation third-derivative term (`ps3`, from `d2mxc`, the second
   derivative of the XC potential, contracted with the field-induced charge-density
   response `aux3`).

Both terms are **frozen-ion**: nowhere in `el_opt.f90` are phonon eigenvectors, Born
effective charges, or the dynamical matrix referenced. **No ionic/lattice-mediated
contribution to the EO response is included.** This matters directly for C11 below.

Confirmed from `ramanm.f90` (the shared module `el_opt.f90` and `raman.f90` both use):
`lraman` (Raman tensor, dχ/du — atomic-displacement derivative of the susceptibility)
and `elop` (this electro-optic tensor) are **separate, independently-triggered
calculations** (`LOGICAL :: lraman, elop`, both default `.false.`). QE does not
automatically combine them into a single "total EO tensor" output.

## Units and the raw-to-pm/V factor (verified, not just quoted)

Output is in "Rydberg a.u." per the source comment. Dimensional cross-check: ε is
dimensionless, so dε/dE has units of 1/[field] = length/voltage — the same physical
dimension as a Pockels coefficient r_ijk, which is reassuring (no unit-family mismatch
between QE's raw quantity and the target r_ijk). A first-principles re-derivation of the
exact numeric factor (2.7502) requires QE's internal Rydberg-unit field normalization
(`e2 = 2` in the `constants` module, i.e. `e^2 = 2` Ry·bohr rather than the Hartree
convention `e^2 = 1`), which shifts the electric-field atomic unit by a functional of
`sqrt(2)` relative to a naive Hartree-based estimate. My own naive dimensional estimate
(using `E_field_atomic_unit = Ry/(e·a0)`) gives ≈3.89 pm/V per raw unit, same order of
magnitude as QE's stated 2.7502 pm/V but not an exact match — the discrepancy is
consistent with the Rydberg-vs-Hartree charge-normalization difference, not evidence the
quoted factor is wrong. **Given the risk of a subtle sign/convention error in an ad hoc
by-hand re-derivation, the source-code-documented factor 2.7502 pm/V is used as
authoritative (primary source, directly in the routine that produces the numbers), and
this limitation is stated explicitly rather than presenting a shakier independent number
as if it were confirmed.**

Two clarifications from the same block:

* The raw printed tensor equals `elop_(:,:,:,1)` = electronic + XC-derivative terms
  **combined**. QE additionally prints (with `wr_all=.true.`, always on) the two terms
  **separately** as "contribution # 1" (electronic-only) and "contribution # 2" (XC
  third-derivative-only) — useful for C4/C11 bookkeeping, but note QE's on-screen
  numbering ("contribution # 1", "# 2") refers to the `il-1` loop index, not the
  `elop_(:,:,:,2)`/`elop_(:,:,:,3)` array slots directly — the parser must key off the
  "contribution #" header text, not raw array position.
* "to obtain the static chi^2 multiply by 1/2" — the raw tensor is **2×** the static
  second-order susceptibility χ⁽²⁾ in whatever convention QE uses internally; this
  factor must be tracked explicitly through the C6 conversion to conventional r_ijk
  (do not assume raw tensor = 2χ⁽²⁾ = r without deriving the χ⁽²⁾→r step too).

## Pseudopotential / XC requirements

**Nothing in `el_opt.f90` itself checks or restricts XC functional or pseudopotential
type.** The routine operates purely on whatever converged DFPT quantities
(`depsi`, `chif`, `aux3`, `d2muxc`) already exist from the preceding `epsil=.true.`/
`trans=.true.` run — it has no functional-family gate. No official QE example
(`PHonon/examples`) demonstrates `elop`, so there is no documented reference case to
check pseudopotential compatibility against. **The "LDA + norm-conserving required"
guidance carried over from the original DEL C task brief is therefore empirical/
community folklore, not a hard-coded QE restriction** as far as the source shows. This
does not rule out a *practical* numerical-stability reason for that guidance (e.g. PAW's
augmentation-region charge response may not be captured correctly by `d2muxc`/`aux3`,
which are computed on the plane-wave/soft-density grid) — but our existing DEL A/B/C0
pseudopotentials are already norm-conserving (never PAW), so that specific PAW concern
does not apply here regardless.

**Conclusion: there is no source-level reason PBEsol + the existing NC pseudopotentials
should fail.** The only way to know for certain is to attempt it (C2) and record exactly
what happens — this is what C2 does next, before deciding whether C3 (a separate
LDA/PZ branch) is actually needed.

## Tensor index convention

From the print loop (lines 165-172): `elop_(ipa, ipb, ipc, il)`, printed as `ipc` (outer
loop) × `ipb` (middle) rows of `ipa` (inner, printed across the row). The
`call dcopy(27, elop_, 1, eloptns, 1)` copies the **total** (`il=1`) tensor into the
module variable `eloptns(3,3,3)` used elsewhere. Symmetrization is applied via
`symmatrix3` (crystal point-group symmetry) before printing — the printed tensor is
already symmetry-reduced, not a raw unsymmetrized one.

## What remains open, honestly

* The exact one-line derivation of "2.7502" from `e2=2` Rydberg units was not
  reproduced to full numerical precision here (see above) — flagged, not glossed over.
* Whether QE 7.5's `elop` numerically converges/runs without error for our specific
  PBEsol-NC pseudopotential set on Material A is **not yet known** — this is C2's job.
* The ionic (phonon-mediated) contribution to the EO response is **not computed by
  `elop` at all**. Obtaining it would require a separate `lraman=.true.` DFPT run (Raman
  tensor dχ/du) combined by hand with the already-available Born charges and phonon
  data via the standard formula `r_ionic ~ Σ_modes (dχ/du_mode)(Z*·mode)/ω_mode²`. This
  has **not** been attempted in this pass (C11 will state this limitation explicitly
  rather than inventing a decomposition QE didn't provide).
