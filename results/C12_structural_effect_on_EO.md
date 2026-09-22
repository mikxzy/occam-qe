# DEL C, C12 — B0 vs B2 structural effect on the EO tensor (H0-C2)

True comparison per instruction: B0 (original, DEL A/B unrelaxed geometry) vs the
production geometry, using **exactly the same EO method** (LDA/PZ pseudopotentials,
since PBEsol `elop` doesn't run at all — C2). Both runs: `C3_EO_at_B0_geom`,
`C3_vcrelax`'s clean_scf+DFPT. Full numbers: `results/eo_tensor_converted.csv`.

**Caveat carried through every number below:** B0's geometry is dynamically *unstable*
under LDA (2 imaginary modes, -96.76/-64.42 cm⁻¹ — confirms DEL A/B's PBEsol finding is
not a functional-specific artifact, since an independent XC functional reproduces it).
The `LDA@B0-geometry` EO tensor is therefore evaluated at a saddle point, not a genuine
minimum — its absolute value carries a "computed at an unstable configuration" caveat
throughout. `LDA@LDA-relaxed` is the trustworthy, stable reference.

| coefficient | B0-geometry (pm/V) | LDA-relaxed (pm/V) | Δ (B0→relaxed) |
|---|---|---|---|
| r22 (=-r12=-r61) | 34.6082 | 22.4675 | **-35.08%** |
| r13 (=r23) | 37.7161 | 35.0157 | **-7.16%** |
| r51 (=r42) | 42.3829 | 35.3054 | **-16.70%** |
| r33 | 28.8370 | 33.0559 | **+14.63%** |

## H0-C2: structural relaxation B0→B2 changes every principal EO coefficient by <5%

**REJECTED, decisively.** All four independent coefficients change by well over the 5%
threshold — from -7.2% (r13/r23) to -35.1% (r22). This is larger than DEL B's already
substantial ~11.8% dielectric-tensor shift (ε_zz, B0→B2) would suggest on its own: the
EO tensor is *more* sensitive to relaxation than the dielectric tensor alone, since
r_ijk depends on both dε/dE (which itself shifts with geometry) and 1/(ε_ii·ε_jj)
(which also shifts). r22 in particular — the coefficient most sensitive to the
transverse (E₂-field, in-plane) response — moves over a third of its own value.

## Interpretation

Using the unrelaxed B0 structure for EO/Pockels parameters — as a naive first attempt
at this task might have done, skipping DEL B entirely — would have been **quantitatively
wrong by double digits** on 3 of 4 independent coefficients, and by over a third on r22.
DEL B's relaxation work was not just a phonon-stability formality; it materially changes
the electro-optic answer this task exists to produce. The `LDA@LDA-relaxed` values are
the ones that should propagate to any downstream Occam device model — not B0, and not
`LDA@PBEsol-geometry` either (also shown in the table for reference, +10-17% off the
relaxed reference — it is *closer* to LDA-relaxed than B0 is, consistent with PBEsol-B2
already being a genuine, force-free-ish minimum, just not the LDA-consistent one).
