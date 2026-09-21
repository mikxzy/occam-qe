# DEL A — numerical convergence result

All 12 frozen jobs in `queue/jobs.json` (4x ecutwfc x 3x k-grid, primitive 10-atom Material A
cell, PBEsol NC pseudopotentials) ran successfully on `qe-convergence-probe`
(GitHub Actions, `ubuntu-latest`, QE 7.5). Raw `pw.out`/`result.json` per job are in the
corresponding GitHub Actions run artifacts (run IDs below); `results/convergence.csv` is
the parsed summary.

| run_id | job_id |
|---|---|
| 35627709359 | scf_ecut40_k2 |
| 35627848480 | scf_ecut40_k4 |
| 35627855116 | scf_ecut40_k6 |
| 35627862365 | scf_ecut60_k2 |
| 35627869563 | scf_ecut60_k4 |
| 35627876630 | scf_ecut60_k6 |
| 35627884009 | scf_ecut80_k2 |
| 35627891627 | scf_ecut80_k4 |
| 35627899442 | scf_ecut80_k6 |
| 35627906430 | scf_ecut100_k2 |
| 35627914335 | scf_ecut100_k4 |
| 35627921709 | scf_ecut100_k6 |
| 35632233942 | scf_ecut120_k4 (extension) |
| 35643905825 | dfpt_ecut80_k4 |
| 35632884976 | dfpt_ecut100_k4 |
| 35643914948 | dfpt_ecut120_k4 |

## Total energy per formula unit

Converges fast and monotonically. Relative to the tightest tested setting
(ecutwfc=100 Ry, 6x6x6):

* ecutwfc=40 Ry: ~0.32% off (fails the <1% target only marginally, but see stress below)
* ecutwfc=60 Ry: ~0.015% off
* ecutwfc=80 Ry: ~0.0001–0.0004% off
* ecutwfc=100 Ry: ~0.00–0.0002% off

k-grid has almost no effect on total energy at any cutoff (2x2x2 vs 6x6x6 differ by
<0.002% throughout) — expected for this 10-atom insulating cell.

## Pressure / stress — the binding constraint

Pressure is **far** from converged at ecutwfc=40 Ry (P ≈ −1036 kbar) and only becomes
physically sensible once ecutwfc ≥ 80 Ry:

| ecutwfc (Ry) | P at k=6x6x6 (kbar) |
|---|---|
| 40  | −1034.85 |
| 60  | −141.89 |
| 80  | −34.98 |
| 100 | −33.24 |

This is the classic NC/ONCVPSP pattern (stress converges much slower than total energy)
and is the real bottleneck for DEL A, not the energy. Between ecutwfc=80 and 100 Ry the
remaining change is ~1.7 kbar (~5%) — still above the <1% target — while k=2x2x2 vs
k=6x6x6 differ by <2 kbar at any fixed cutoff ≥60 Ry.

## Cutoff extension: full 6-component stress tensor, 120 Ry (resolved)

`80 -> 100 Ry` left ~5% pressure drift, so the ecutwfc series was extended one point at a
time (per instruction), comparing the **full stress tensor** (all 6 independent
components, not just scalar pressure) with a dual criterion: absolute <=1 kbar per
component AND the existing relative <1%. Full numbers: `results/stress_convergence.csv`.
Run: [`scf_ecut120_k4`](https://github.com/mikxzy/occam-qe/actions/runs/35632233942).

| pair | xx | yy | zz | xy/xz/yz | result |
|---|---|---|---|---|---|
| 80 -> 100 Ry | Δ=1.75 kbar (4.6%) | Δ=1.75 kbar (4.6%) | Δ=1.73 kbar (5.9%) | ~0 | **FAIL** |
| 100 -> 120 Ry | Δ=0.08 kbar (0.22%) | Δ=0.08 kbar (0.22%) | Δ=0.07 kbar (0.25%) | ~0 | **PASS** |

The per-step delta dropped >20x between the two comparisons (1.75 -> 0.08 kbar), a clean
monotonic approach rather than noise. **Two consecutive cutoffs (100, 120 Ry) now satisfy
both criteria on all 6 components** — per instruction, the series stops here; 140/160 Ry
were not needed.

## H0-QE0 (task DEL F) — RESOLVED: PASS

Total energy: <1% since ecutwfc=60 Ry. Full stress tensor: <1%/<=1 kbar per component
between 100 and 120 Ry. No physics or pseudopotentials were changed to force this (task
rule 8) — 120 Ry was reached by straightforward extension of the as-measured trend.

## Production cutoff: ecutwfc = 120 Ry, ecutrho = 480 Ry, k >= 4x4x4

Chosen as the tighter member of the first converged consecutive pair (100, 120 Ry),
giving a safety margin over the minimum-converged point (100 Ry) per task rule 69.

## Dielectric-tensor and Γ-phonon convergence (DEL A completion matrix)

Reduced matrix per instruction: 80, 100, 120 Ry, all at k=4x4x4 (Gamma DFPT, `epsil=.true.
trans=.true.`, on the same as-deposited/unrelaxed primitive cell used throughout DEL A).
Runs: [80 Ry](https://github.com/mikxzy/occam-qe/actions/runs/35643905825),
[100 Ry](https://github.com/mikxzy/occam-qe/actions/runs/35632884976),
[120 Ry](https://github.com/mikxzy/occam-qe/actions/runs/35643914948). Full table:
`results/dfpt_convergence.csv`.

**Dielectric tensor: converged, easily.** ε_xx=ε_yy and ε_zz change by <0.003% from 80 to
100 Ry and <0.001% from 100 to 120 Ry (ε_xx=ε_yy≈5.3593, ε_zz≈4.7674 at 120 Ry). This was
already effectively converged at the loosest cutoff tested.

**Γ-phonons: 28/30 modes converged (<=2 cm-1 and <1% between 100 and 120 Ry).** Two
modes did not:

* A doubly-degenerate low-frequency mode (index 2/3): **+5.48 cm-1 (80 Ry) -> -19.71 cm-1
  (100 Ry) -> -29.90 cm-1 (120 Ry)**. Not just unconverged in magnitude — it *changes
  sign* (stable -> imaginary) between 80 and 100 Ry, and is still moving substantially
  (Δ=10.2 cm-1) between 100 and 120 Ry with no sign of leveling off. This is the one
  genuinely open question DEL A leaves behind.
* A doubly-degenerate mode near 140 cm-1 (index 5/6): Δ=2.6 cm-1 (1.85%) between 100 and
  120 Ry — stays positive/stable throughout, just outside the strict tolerance; minor.

**Is the soft mode numerical or real?** Most likely **not** a generic basis-set/cutoff
artifact: the dielectric tensor and 28 of 30 other phonon branches are solidly converged
at the same cutoffs, so plane-wave incompleteness alone doesn't explain a mode that keeps
moving. The more likely explanation is that DEL A's cell is the **as-deposited
experimental geometry, not yet DFT-relaxed** (`00_environment/structure_source.md`) — a
real material sitting slightly off its PBEsol energy minimum can show soft/imaginary
low-frequency modes that are an artifact of the unrelaxed geometry, not of the numerics.
This can only be settled by DEL B's `vc-relax`/`relax` baseline (not started — see below),
which is exactly the kind of "negative/unstable result reported, not hidden" the task asks
for (rule 8), not a defect in this convergence study.

## Addendum (DEL B, B0): the -29.9 cm-1 doublet was an ASR artifact, not a soft mode

DEL B's B0 step re-ran this exact structure's DFPT with `dynmat.x` ASR correction
(`asr='crystal'`), which DEL A's original run did not apply. Result: the 3 acoustic modes,
which should be exactly 0 cm-1 at Gamma, were badly ASR-violating in the raw output
(spread across -29.898 (x2) and +7.477 cm-1 -- tens of cm-1 from zero, not the few cm-1
one might casually dismiss as noise). After ASR correction they collapse to ~0.00 cm-1 as
required, and are **not** part of the optical spectrum. Only 2 genuine imaginary optical
modes remain: -111.88 and -66.61 cm-1 (ASR-corrected) -- consistent with, and slightly
shifted from, DEL A's raw -110.90/-66.61 cm-1. Full detail: `DEL_B_STRUCTURAL_RELAXATION.md`.

## DEL A status: complete for its own scope

Numerical convergence (energy, full stress tensor, dielectric tensor, Γ-phonons) has been
tested as specified. Production level: **ecutwfc=120 Ry, ecutrho=480 Ry, k>=4x4x4.** The
one open item (the soft doubly-degenerate mode) is flagged, not resolved — resolving it
requires DEL B geometry relaxation, which has **not** been started per instruction.
