"""Add ONE more SCF job to queue/jobs.json at a given ecutwfc (ecutrho scaled by the same
4x dual as the original DEL A matrix), fixed k-grid. Used to extend the cutoff series
(120, 140, 160 Ry ...) without touching or re-freezing the original 12 jobs / their hashes.

    python scripts/extend_ecut_series.py --ecutwfc 120 --k 4
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from cif_to_qe import load_primitive, render_qe_blocks
from pw_scf_template import render

ROOT = Path(__file__).resolve().parents[1]
CIF = ROOT / "structures" / "material_A_R3c_COD1541936.cif"
RUNS = ROOT / "runs" / "convergence"
QUEUE = ROOT / "queue" / "jobs.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ecutwfc", type=float, required=True)
    ap.add_argument("--k", type=int, required=True)
    a = ap.parse_args()

    d = load_primitive(str(CIF))
    structure_block = render_qe_blocks(d["lattice"], d["symbols"], d["positions"])

    job_id = f"scf_ecut{int(a.ecutwfc)}_k{a.k}"
    job_dir = RUNS / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    pw_in = job_dir / "pw.in"
    pw_in.write_text(render(structure_block, a.ecutwfc, a.k), newline="\n")

    jobs = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}
    if job_id in jobs:
        print(f"{job_id} already in queue/jobs.json (sha256 {jobs[job_id]['pwin_sha256'][:12]}...) -- not overwritten")
        return
    jobs[job_id] = dict(
        dir=str(pw_in.parent.relative_to(ROOT)).replace("\\", "/"),
        calc="scf",
        ecutwfc_Ry=a.ecutwfc,
        ecutrho_Ry=4.0 * a.ecutwfc,
        kgrid=[a.k, a.k, a.k],
        n_atoms=10,
        pwin_sha256=sha256(pw_in),
    )
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")
    print(f"added {job_id} (ecutwfc={a.ecutwfc} Ry, ecutrho={4.0*a.ecutwfc} Ry, k={a.k}x{a.k}x{a.k})")
    print(f"  pw.in sha256: {jobs[job_id]['pwin_sha256']}")


if __name__ == "__main__":
    main()
