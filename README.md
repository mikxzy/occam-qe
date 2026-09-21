# occam-qe

Quantum ESPRESSO material-parameter validation for LiO3 (Occam-1 / HEO-QIC v2.2, DEL A). Structure: COD 1541936 (Abrahams, Hamilton & Reddy 1966, R3c), reduced to the 10-atom primitive cell via spglib. Pseudopotentials: PseudoDojo NC-SR v0.4 PBEsol standard (Li, Nb, O), SHA-256 hashes in `00_environment/pseudopotentials_manifest.txt`. Every job verifies frozen `pw.in` + pseudopotential hashes before running and uploads `pw.out`/`pw.err`/`time.txt`/`result.json` as a GitHub Actions artifact.

Workflows: `qe-environment` (records installed QE version/executables), `qe-convergence-probe` (runs one job from `queue/jobs.json`).
