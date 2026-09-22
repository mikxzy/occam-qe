# DEL B — Structural Relaxation Baseline (Occam-1 / Material A)

All calculations: QE 7.5, PBEsol NC pseudopotentials (Li/Nb/O, same as DEL A), primitive
10-atom cell, `ecutwfc=120 Ry`, `ecutrho=480 Ry`, `K_POINTS automatic 4 4 4 0 0 0`,
`occupations='fixed'`, `conv_thr=1.0d-10` throughout. Structure reused verbatim from DEL A
(`runs/convergence_dfpt/dfpt_ecut120_k4/pw.in`) — never re-derived from the CIF. Raw
outputs: `runs/delB/{B0,B1,B2}/artifact/`. GitHub Actions runs:
[B0](https://github.com/mikxzy/occam-qe/actions/runs/35661874446) (+
[dynmat fix](https://github.com/mikxzy/occam-qe/actions/runs/35668018851)),
[B1](https://github.com/mikxzy/occam-qe/actions/runs/35668271229),
[B2](https://github.com/mikxzy/occam-qe/actions/runs/35668278235).

## 1. Executive result

DEL A found two genuine imaginary Gamma-point optical modes (A_1 at -111.9 cm⁻¹, A_2 at
-66.6 cm⁻¹) in the as-deposited experimental structure, after ruling out a third
candidate (a "-29.9 cm⁻¹ doublet") as an acoustic-mode ASR artifact, not a real
instability (§9). **Relaxing internal coordinates alone (B1, fixed cell) removes both
imaginary modes** — the relaxed structure is dynamically stable at Gamma with zero
imaginary optical modes. Full cell relaxation (B2) does not remove any *additional*
imaginary modes (there were none left to remove) but does lower the energy slightly
further, contract the cell by ~1%, and shift the dielectric tensor materially (up to
~12% on ε_zz). This is **CASE 1**: the instability was caused by non-equilibrium internal
coordinates, not cell/lattice mismatch. **Decision: `GO_TO_DEL_C`**, using B2 as the
recommended production geometry.

## 2. B0 reference (locked, unmodified)

Byte-identical to DEL A's production `pw.in` (sha256 `6d90d7d3...`, verified before every
run). Re-run only to capture what DEL A didn't save: Born charges (`zeu=.true.`) and
dynamical-matrix eigenvectors (`mat.dyn`, needed for mode tracking). SCF energy
reproduced DEL A's committed value exactly (-476.32035238 Ry).

| quantity | value |
|---|---|
| a = b = c | 5.494444 Å |
| α = β = γ | 55.8739° |
| volume | 106.0708 Å³ |
| density | 4.6290 g/cm³ |
| E / formula unit | -238.16017619 Ry |
| pressure | -33.16 kbar |
| stress (xx, yy, zz) | -35.98, -35.98, -27.53 kbar (off-diag ~0) |
| ε_xx = ε_yy / ε_zz | 5.35931 / 4.76737 |
| Gamma phonons | 30/30, ASR-corrected: 2 imaginary optical (-111.88, -66.61 cm⁻¹, see §9), 3 acoustic (~0), 25 stable optical |

## 3. B1 result — fixed-cell ionic relaxation

`calculation='relax'`, cell fixed at B0's, `ion_dynamics='bfgs'`,
`etot_conv_thr=1.0d-8 Ry`, `forc_conv_thr=5.0d-5 Ry/Bohr`. Converged in 23 BFGS steps
(final max |force| = 2.40e-4 eV/Å). Symmetry constant throughout ("6 Sym. Ops. (no
inversion)" at every step — matches the C₃ᵥ site symmetry, no breaking detected).

| quantity | B0 | B1 | Δ |
|---|---|---|---|
| E / formula unit (Ry) | -238.16017619 | -238.19935682 | **-0.039181 Ry = -0.5331 eV** |
| pressure (kbar) | -33.16 | -11.34 | +21.82 |
| stress (xx,yy,zz, kbar) | -35.98,-35.98,-27.53 | -10.95,-10.95,-12.14 | large drop, cell still not force-free (expected: cell is fixed) |
| RMS / max displacement vs B0 | — | 0.2823 / 0.5394 Å | substantial ionic motion |
| Gamma phonons | 2 imaginary optical | **0 imaginary optical** | **instability removed** |

## 4. B2 result — full vc-relax

`calculation='vc-relax'`, `ion_dynamics='bfgs'`, `cell_dynamics='bfgs'`,
`press_conv_thr=0.1 kbar`, same force/energy thresholds as B1. Converged in 26 steps
(final max |force| = 6.8e-5 eV/Å, final pressure ≈ 0.00 kbar). `ibrav=0` preserved
throughout, no cell-convention change. Symmetry constant ("6 Sym. Ops.", same as B0/B1 —
no breaking detected, checked at first and last step).

| quantity | B0 | B2 | Δ |
|---|---|---|---|
| a = b = c (Å) | 5.494444 | 5.476261 | -0.3309% |
| α (°) | 55.8739 | 55.865268 | -0.0154% |
| volume (Å³) | 106.0708 | 104.9975 | **ΔV/V0 = -1.0118%** |
| density (g/cm³) | 4.6290 | 4.6763 | +1.02% |
| E / formula unit (Ry) | -238.16017619 | -238.19949713 | **-0.039321 Ry = -0.5350 eV** |
| pressure (kbar) | -33.16 | -0.00 | converged |
| RMS / max displacement vs B0 | — | 0.2817 / 0.5397 Å | ~identical to B1 |
| Gamma phonons | 2 imaginary optical | **0 imaginary optical** | stable |

**B2 vs B1: ΔE = -0.000140 Ry/fu = -0.0019 eV/fu.** Cell relaxation adds a real but small
energy gain (~0.4% of the total relaxation energy) on top of what internal-coordinate
relaxation alone already captures — see H0-B2 (§10).

## 5. Structural comparison (H0-B3)

Full table: `results/delB_structural.csv`. B1's cell is exactly B0's (by construction).
B2's cell contracts modestly (~1% in volume, ~0.33% linear) with a negligible angle
change (~0.015%), while the **ionic displacement is substantial**: RMS ≈ 0.282 Å, max ≈
0.540 Å (B1 and B2 essentially identical here) — about 10% of the shortest Nb-O bond
length. This is not a negligible geometry change.

## 6. Stress / pressure comparison

Full 6-component stress tensor for all three structures in `results/delB_structural.csv`
(off-diagonal components are ~0 kbar for all of B0/B1/B2, consistent with the retained
C₃ᵥ symmetry). B0 → B1 → B2 pressure moves monotonically toward zero (-33.16 → -11.34 →
-0.00 kbar) as more degrees of freedom are allowed to relax, exactly as expected.

## 7. Dielectric comparison (H0-B4)

Full table + Born charges: `results/delB_dielectric.csv`, `results/delB_born_charges.json`.

| component | B0 | B1 | B1 vs B0 | B2 | B2 vs B0 |
|---|---|---|---|---|---|
| ε_xx = ε_yy | 5.35931 | 5.47009 | +2.07% | 5.49376 | +2.51% |
| ε_zz | 4.76737 | 5.28863 | **+10.93%** | 5.32829 | **+11.77%** |
| ε_xy, ε_xz, ε_yz | 0 | 0 | — | 0 | — |

**H0-B4 is rejected**: the dielectric tensor is clearly *not* insensitive to relaxation —
ε_zz shifts by ~11-12%. This is directly relevant to the later Occam EO model (task's own
note): any EO/Pockels modeling done on the unrelaxed B0 structure would be off by a
double-digit percentage on ε_zz specifically.

## 8. Phonon-mode mapping (eigenvector overlap, not index)

Full table: `results/delB_phonons.csv` (90 rows: 30 modes × 3 structures). Method:
near-degenerate modes grouped by frequency, matched via subspace overlap
`trace(P_A P_B) / min(dim)` on ASR-corrected, orthogonal eigenvectors (`dynmat.x
fileig`) — not by array index or raw eigenvector dot products, since individual vectors
within a degenerate subspace are only defined up to an arbitrary rotation. Self-test
(B0 vs itself) gives overlap = 1.0000 on all 19 mode groups, confirming the method is
correctly implemented.

| B0 mode | B0 freq (ASR) | irrep | → B1 mode | B1 freq | overlap | → B2 mode | B2 freq | overlap |
|---|---|---|---|---|---|---|---|---|
| 1 | -111.88 cm⁻¹ | A_1 | 9 | +241.11 cm⁻¹ | 0.549 | 12 | +271.60 cm⁻¹ | 0.561 |
| 2 | -66.61 cm⁻¹ | A_2 | 13 | +282.34 cm⁻¹ | 0.518 | 13 | +288.47 cm⁻¹ | 0.572 |
| 3,4 (E) / 5 (A_1) | ~0 (acoustic) | E / A_1 | 1,2 / 3 | ~0 | 1.000 | 1,2 / 3 | ~0 | 1.000 |

The two originally-unstable modes are tracked to specific B1/B2 modes of matching
symmetry (A_1→A_1, A_2→A_2), both now positive. **Overlap is moderate (~0.52-0.57), not
near 1** — this is reported honestly rather than oversold: the ~0.28-0.54 Å ionic
displacement is large enough that the normal-mode character substantially reorganizes
within each symmetry channel (mixes with neighboring same-symmetry modes), so this is
not a clean "the same mode just shifted frequency" story. What *is* robust: no A_1 or A_2
mode remains negative anywhere in the low-frequency region of B1 or B2 — the symmetry
channels that were unstable are populated only by stable modes after relaxation.

## 9. Soft-mode interpretation

Two independent lines of evidence agree on B0's true instability count (2, not 3):
1. `dynmat.x` with `asr='crystal'`: the raw "-29.9 cm⁻¹ doublet" (+ a +7.5 cm⁻¹ singlet)
   collapses to ~0.00 cm⁻¹ once the acoustic sum rule is imposed.
2. `ph.x`'s own point-group symmetry analysis (C₃ᵥ): those same 3 modes carry E + A_1
   labels — exactly the representations of translation (x,y → E, z → A_1) — while modes
   1 and 2 (A_1, A_2) are distinct, non-translational representations.

Both B1 and B2 confirm the 2 remaining imaginary modes (A_1, A_2) were real,
non-numerical instabilities of the unrelaxed structure, and that they are fully resolved
by relaxation. Acoustic modes remain correctly near-zero (≤5 cm⁻¹) in B1/B2 too — see
`results/delB_phonons.csv`'s `stability_class` column.

## 10. Null-hypothesis table

| ID | Hypothesis | Result | Evidence |
|---|---|---|---|
| H0-B1 | Internal-coordinate relaxation at fixed cell does NOT remove the imaginary modes | **REJECTED** | B1: 2→0 imaginary optical modes |
| H0-B2 | Full cell relaxation does NOT materially improve dynamic stability beyond B1 | **NOT REJECTED** (retained) | B2 removes 0 *additional* imaginary modes (none remained); ΔE(B2-B1) = -0.0019 eV/fu is real but small |
| H0-B3 | The relaxed B2 geometry differs negligibly from the original cell | **REJECTED** | ΔV/V0 = -1.01%, RMS ionic displacement = 0.282 Å (not negligible), though lattice angle change is negligible (-0.015%) |
| H0-B4 | The dielectric tensor is insensitive to structural relaxation | **REJECTED** | ε_zz shifts +11.8% (B0→B2), ε_xx/yy +2.5% |

## 11. Recommended Material A geometry for subsequent calculations

**Use B2 (full vc-relax)** as the production PBEsol equilibrium geometry: it is
dynamically stable, has the lowest energy of the three, a converged near-zero residual
pressure, and is the physically correct choice when both cell and ionic degrees of
freedom are allowed to respond (which is the physically relevant scenario — nothing
pins Material A's cell to the room-temperature neutron-diffraction lattice constants at
the PBEsol level of theory). B1 remains a useful cross-check (it already resolves the
dynamical-stability question on its own, isolating the ionic-coordinate contribution from
the cell-relaxation contribution) but is not recommended as the forward geometry.

Final cell (B2, Å, `ibrav=0` convention) and fractional coordinates are in
`runs/delB/B2/artifact/vcrelax.out` (`Begin final coordinates` block) and
`runs/delB/B2/artifact/clean_scf/pw.in` (the exact input used for B2's production
SCF+DFPT, ready to reuse directly for DEL C).

## 12. GO / HOLD decision for DEL C

**`GO_TO_DEL_C`**

Quantitative basis: B2, the recommended geometry, has zero imaginary optical modes (all
30 Gamma phonons classified `acoustic` or `stable_optical` in
`results/delB_phonons.csv`), converged residual pressure (0.00 kbar, well under the
0.1 kbar threshold), converged forces (6.8e-5 eV/Å, well under the 5e-5 Ry/Bohr ≈
2.6e-3 eV/Å threshold), and constant symmetry throughout relaxation (no unexpected
symmetry breaking). CASE 3 (B-SOFT trigger) does not apply — there is no robust
imaginary optical mode remaining in B2. DEL C (electro-optic response, per the original
Quantum ESPRESSO task) is not started here, per instruction.
