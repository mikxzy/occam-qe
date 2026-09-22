# DEL C, C9/C10 — finite-field cross-check: NOT PERFORMED this pass

## Decision

The finite-field (`lelfield=.true.`) linearity cross-check was **not run** in this DEL C
pass. Stated explicitly rather than silently skipped, per the task's own standard.

## Why

1. The task itself frames this as conditional and secondary: "Where technically
   feasible... this is a cross-check, not necessarily the primary coefficient extraction
   route." The primary route (linear-response `elop`, C2-C7) is complete, symmetry-
   validated (C5: 0/54 forbidden-slot violations), and internally consistent across three
   geometries (C12).
2. `lelfield` (Berry-phase polarization under a finite homogeneous field) is a materially
   different and typically much more finicky QE calculation than what's been run so far
   in this project: it requires careful field-strength selection to stay in the linear
   regime without losing numerical precision, generally needs denser k-point sampling
   than a zero-field DFPT run for reliable Berry-phase convergence, and does not have the
   same "run it and see" cost profile as `elop` (a single `elop` DFPT run already took
   ~3h on the GH-hosted runner; a `-E2...+E2` five-point sequence in two field directions,
   each needing its own convergence verification, is a substantially larger and less
   predictable undertaking — plausibly several times the wall-clock already spent on all
   of DEL C combined, with a real chance of hitting convergence problems specific to
   `lelfield` that would need diagnosis before any usable data emerges).
3. Given the primary EO result is already well-supported (source-verified `elop`
   semantics, symmetry-consistent output, cross-checked across 3 geometries, converged
   at the production k-grid pending C13's result), the added confidence from a finite-
   field cross-check is real but marginal relative to its cost.

## What would be needed to add this later

A separate, explicitly-scoped follow-up task: `lelfield=.true.` runs on the LDA-relaxed
geometry (the trustworthy reference from C12) at symmetric field points along z
(extraordinary axis) and one transverse direction, starting at ~0.1-0.5 V/µm converted
carefully to QE's Hartree-atomic-unit field convention, fitting `P(E) = P0 + aE + bE² +
cE³` per field direction, and testing H0-C1 (linear within 2%) using the Berry-phase
polarization as the observable — not a refractive-index probe (task's own caution: "Do
not claim device-level Pockels linearity solely from bulk polarization if the calculated
observable does not directly probe refractive-index response," which is exactly the
observable `lelfield` gives here). H0-C1 is therefore left as **NOT TESTED**, not
assumed passing, in the null-hypothesis table (C15).
