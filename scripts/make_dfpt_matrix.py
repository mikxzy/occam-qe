"""Freeze the DEL A completion matrix: Gamma-point DFPT (dielectric tensor + phonon
frequencies) at a reduced set of cutoffs, per instruction "centered on 80 Ry, 100 Ry and
the selected production cutoff" (120 Ry, resolved by the ecutwfc extension above). Fixed
k-grid = 4x4x4 throughout (same grid used for the cutoff-resolution stress test, already
shown to be k-converged in the original 12-point matrix).

Each job pairs a frozen pw.in (identical SCF settings to the corresponding scf_ecutNN_k4
job) with a frozen ph.in (Gamma DFPT), under runs/convergence_dfpt/<job_id>/, and is
recorded in queue/dfpt_jobs.json. Never runs QE -- scripts/run_dfpt_job.py does that for
one job at a time.

    python scripts/make_dfpt_matrix.py
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from cif_to_qe import load_primitive, render_qe_blocks
from pw_scf_template import render as render_pw
from ph_dfpt_template import render as render_ph

ROOT = Path(__file__).resolve().parents[1]
CIF = ROOT / "structures" / "material_A_R3c_COD1541936.cif"
RUNS = ROOT / "runs" / "convergence_dfpt"
QUEUE = ROOT / "queue" / "dfpt_jobs.json"

ECUTWFC_RY = [80.0, 100.0, 120.0]  # reduced matrix centered on 80, 100, and the selected production cutoff
K = 4


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    d = load_primitive(str(CIF))
    structure_block = render_qe_blocks(d["lattice"], d["symbols"], d["positions"])

    jobs = {}
    for ecut in ECUTWFC_RY:
        job_id = f"dfpt_ecut{int(ecut)}_k{K}"
        job_dir = RUNS / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        pw_in = job_dir / "pw.in"
        ph_in = job_dir / "ph.in"
        pw_in.write_text(render_pw(structure_block, ecut, K), newline="\n")
        ph_in.write_text(render_ph(), newline="\n")
        jobs[job_id] = dict(
            dir=str(job_dir.relative_to(ROOT)).replace("\\", "/"),
            calc="scf+dfpt-gamma",
            ecutwfc_Ry=ecut,
            ecutrho_Ry=4.0 * ecut,
            kgrid=[K, K, K],
            n_atoms=10,
            pwin_sha256=sha256(pw_in),
            phin_sha256=sha256(ph_in),
        )

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(jobs)} jobs to {QUEUE.relative_to(ROOT)}")
    for jid in jobs:
        print(" ", jid)


if __name__ == "__main__":
    main()
