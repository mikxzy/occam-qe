# occam-qe

Quantum ESPRESSO material-parameter validation, DEL A (numerical convergence). Structure source and pseudopotential provenance/hashes are in `00_environment/`. Every job verifies frozen `pw.in` + pseudopotential hashes before running and uploads `pw.out`/`pw.err`/`time.txt`/`result.json` as a GitHub Actions artifact.

Workflows: `qe-environment` (records installed QE version/executables), `qe-convergence-probe` (runs one job from `queue/jobs.json`).
