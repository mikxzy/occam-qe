"""Freeze the DEL A numerical-convergence pw.in matrix (>=4 ecutwfc x >=3 k-grids, per the
task spec) into runs/convergence/<job_id>/pw.in, and record each job (dir, sha256 of the
frozen input, ecutwfc, k-grid) in queue/jobs.json.

This never runs QE itself — scripts/run_qe_job.py executes ONE frozen, hash-verified job
at a time (mirrors the pattern used for Level-C Test 4B).

    python scripts/make_convergence_matrix.py
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from cif_to_qe import load_primitive, render_qe_blocks
from pw_scf_template import render

ROOT = Path(__file__).resolve().parents[1]
CIF = ROOT / "structures" / "material_A_R3c_COD1541936.cif"
RUNS = ROOT / "runs" / "convergence"
QUEUE = ROOT / "queue" / "jobs.json"

ECUTWFC_RY = [40.0, 60.0, 80.0, 100.0]   # >= 4 cutoffs, task rule (DEL A)
KGRIDS = [2, 4, 6]                        # >= 3 k-grids, task rule (DEL A); N x N x N (rhombohedral, 3-fold symmetric)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    d = load_primitive(str(CIF))
    structure_block = render_qe_blocks(d["lattice"], d["symbols"], d["positions"])

    jobs = {}
    for ecut in ECUTWFC_RY:
        for k in KGRIDS:
            job_id = f"scf_ecut{int(ecut)}_k{k}"
            job_dir = RUNS / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            pw_in = job_dir / "pw.in"
            pw_in.write_text(render(structure_block, ecut, k), newline="\n")
            jobs[job_id] = dict(
                dir=str(pw_in.parent.relative_to(ROOT)).replace("\\", "/"),
                calc="scf",
                ecutwfc_Ry=ecut,
                ecutrho_Ry=4.0 * ecut,
                kgrid=[k, k, k],
                n_atoms=10,
                pwin_sha256=sha256(pw_in),
            )

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(jobs)} jobs to {QUEUE.relative_to(ROOT)}")
    for jid in jobs:
        print(" ", jid)


if __name__ == "__main__":
    main()
