"""Add more AlAs cutoff-check points (100, 120 Ry at k=8) after finding 60 Ry badly
unconverged (pressure -616 kbar) and 80 Ry much closer (-15 kbar) but not yet confirmed
converged.

    python scripts/extend_alas_cutoff.py
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from make_cval2_testD_alas import get_blocks, SCF_TEMPLATE, SPECIES_BLOCK, sha256

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "runs" / "delC" / "CVAL2_testD_AlAs"
QUEUE = ROOT / "queue" / "delC_jobs.json"


def main():
    cell_block, positions_block = get_blocks()
    jobs = json.loads(QUEUE.read_text())
    for ecut, k, tag in [(100.0, 8, "ecut100_k8"), (120.0, 8, "ecut120_k8")]:
        job_id = f"CVAL2_AlAs_cutoff_{tag}"
        job_dir = OUT_ROOT / "cutoff_check" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        text = SCF_TEMPLATE.format(ecutwfc=ecut, ecutrho=4.0 * ecut, k=k, cell_block=cell_block,
                                    species_block=SPECIES_BLOCK.rstrip("\n"), positions_block=positions_block)
        (job_dir / "pw.in").write_text(text, newline="\n")
        jobs[job_id] = dict(dir=str(job_dir.relative_to(ROOT)).replace("\\", "/"),
                             calc="scf-alas-cutoff-check", ecutwfc_Ry=ecut, kgrid=[k, k, k],
                             pwin_sha256=sha256(job_dir / "pw.in"))
        print("added", job_id)
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
