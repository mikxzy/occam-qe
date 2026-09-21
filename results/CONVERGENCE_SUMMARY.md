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

## H0-QE0 (task DEL F)

**INCONCLUSIVE at ecutwfc=100 Ry.** Total energy passes (<1% since ecutwfc=60 Ry), but
pressure has not yet demonstrated <1% change between the two highest tested cutoffs
(80 -> 100 Ry: ~5% change). The stress/pressure trend (−141.9 -> −35.0 -> −33.2 kbar) is
converging but the matrix as specified (4 cutoffs) does not yet reach a <1% pressure
plateau. Options, not yet acted on:

1. Extend the ecutwfc series (e.g. 120, 140 Ry) until pressure changes <1% between
   consecutive points — the task only mandates >=4 points, not that 100 Ry be the ceiling.
2. Accept ecutwfc=100 Ry / k>=4x4x4 as production with the pressure non-convergence
   flagged as a known limitation (stress-derived quantities carry larger uncertainty than
   energy-derived ones) — defensible since DEL B onward primarily needs relaxed
   geometry/dielectric/EO quantities, not the raw SCF pressure itself.

No physics or pseudopotentials were changed to force a "nicer" result (task rule 8) —
this is the as-measured trend.

## Recommended production level (pending option 1 vs 2 above, DEL B not yet started)

`ecutwfc = 100 Ry`, `ecutrho = 400 Ry`, k-grid >= `4x4x4`. Do **not** proceed to DEL B
(relaxation) until the H0-QE0 question above is explicitly resolved, per task rule 7
("Kör ALDRIG produktionsserien innan cutoff- och k-point-convergence är verifierade").

Gamma-point phonon frequency and dielectric-tensor convergence (also required by DEL A)
have **NOT** been measured yet — this run only covered SCF total energy/stress. That is
the next step before DEL A can be marked complete.
