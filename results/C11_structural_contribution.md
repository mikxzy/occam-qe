# DEL C, C11 — electronic vs ionic (clamped-ion vs relaxed-ion) EO decomposition

## What QE's `elop` actually decomposes (not what C11 is asking for)

Per `ELop_IMPLEMENTATION_NOTES.md`, `ph.x` with `elop=.true.` prints the total tensor
plus two sub-contributions ("contribution # 1" and "# 2"): a wavefunction/electric-field
response term and an exchange-correlation third-derivative term (both extracted in
`results/eo_tensor_raw.json`/`.csv` for every branch). **This is a decomposition of the
purely electronic response into its own two physical pieces — it is not the
electronic-vs-ionic (clamped-ion vs relaxed-ion) split C11 asks about.** Nowhere in
`el_opt.f90` do phonon eigenvectors, mode frequencies, or Born effective charges enter
the calculation (verified by reading the source, not assumed).

## What the real electronic/ionic decomposition would require

The standard formula for the ionic (phonon-mediated, "relaxed-ion" or low-frequency)
contribution to a Pockels-type coefficient is

  r_ionic_ijk ≈ (something like) Σ_modes [ (dχ_ij/du_mode) · (Z*_mode · ê_k) ] / ω_mode²

i.e. it needs the **Raman tensor** (dχ/du, the atomic-displacement derivative of the
susceptibility — a *separate* QE calculation, `lraman=.true.`, not run anywhere in this
project) combined by hand with the phonon eigenvectors/frequencies (already computed,
`dynmat.eig.out`) and Born effective charges (already computed, `zeu=.true.`, in every
DEL C branch's `ph.out`).

## What was actually done here

**No `lraman=.true.` calculation was run.** Per instruction ("If QE does NOT directly
support a rigorous decomposition, state this rather than inventing one"), this is stated
plainly: **every r_ijk value in this project (`results/eo_tensor_converted.csv`) is the
purely electronic (clamped-ion) static Pockels coefficient.** It does not include the
ionic/lattice contribution that would matter for the true low-frequency (e.g. slow bias
modulation, well below the lowest optical-phonon frequency) EO response of a real
device — only the fast/clamped-ion response relevant to modulation frequencies well
above the acoustic-phonon-limited mechanical response but still below electronic
timescales. For a TFLN-style device operating at RF/microwave modulation rates (well
below THz optical-phonon frequencies), the *total* static coefficient (electronic +
ionic) is usually the physically relevant one — so **this project's r_ijk values should
be treated as a lower/partial bound on the true static EO response, not the full
answer**, until a `lraman=.true.` run is added.

This limitation applies identically to all three EO branches computed (PBEsol-geometry,
LDA-relaxed, B0-geometry) since none of them ran `lraman`.
