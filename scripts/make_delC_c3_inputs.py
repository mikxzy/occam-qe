"""Freeze DEL C, C3 (LDA/PZ branch) inputs:
  - a short cutoff check (3 points: 80/100/120 Ry, k=4x4x4, LDA pseudopotentials) on
    B2's PBEsol-relaxed geometry (a reasonable, already-available starting point --
    convergence behaviour depends mainly on the pseudopotentials/basis, only weakly on
    the exact geometry, so this is a legitimate "short" check per instruction, not the
    full DEL A 12-point matrix)
  - a full vc-relax input (same production settings: ecutwfc=120 Ry, ecutrho=480 Ry,
    k=4x4x4) for the internally-consistent LDA equilibrium reference

Structure blocks (CELL_PARAMETERS/ATOMIC_POSITIONS) are copied verbatim from DEL B's B2
clean_scf/pw.in -- never re-derived from the CIF -- only ATOMIC_SPECIES is changed to
point at the LDA pseudopotentials.

    python scripts/make_delC_c3_inputs.py
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B2_PWIN = ROOT / "runs" / "delB" / "B2" / "artifact" / "clean_scf" / "pw.in"
B0_PWIN = ROOT / "runs" / "convergence_dfpt" / "dfpt_ecut120_k4" / "pw.in"
OUT_ROOT = ROOT / "runs" / "delC" / "C3_LDA"
QUEUE = ROOT / "queue" / "delC_jobs.json"

LDA_SPECIES_BLOCK = "ATOMIC_SPECIES\nLi 6.94000 Li_LDA.upf\nNb 92.90637 Nb_LDA.upf\nO 15.99900 O_LDA.upf\n"

SCF_TEMPLATE = """&CONTROL
   calculation = 'scf'
   prefix      = 'linbo3lda'
   outdir      = './tmp/'
   pseudo_dir  = '/work/pseudo'
   verbosity   = 'high'
   tstress     = .true.
   tprnfor     = .true.
/
&SYSTEM
   ibrav       = 0
   nat         = 10
   ntyp        = 3
   ecutwfc     = {ecutwfc:.1f}
   ecutrho     = {ecutrho:.1f}
   occupations = 'fixed'
/
&ELECTRONS
   conv_thr    = 1.0d-10
   mixing_beta = 0.7d0
   electron_maxstep = 200
/
{cell_block}
{species_block}
{positions_block}
K_POINTS automatic
4 4 4 0 0 0
"""

PH_EO_TEMPLATE = """Gamma-point DFPT: dielectric + Born charges + phonons + electro-optic tensor (LDA)
&inputph
   prefix   = 'linbo3lda'
   outdir   = './tmp/'
   fildyn   = 'mat.dyn'
   epsil    = .true.
   trans    = .true.
   zeu      = .true.
   elop     = .true.
   tr2_ph   = 1.0d-14
/
0.0 0.0 0.0
"""

VCRELAX_TEMPLATE = """&CONTROL
   calculation = 'vc-relax'
   prefix      = 'linbo3lda'
   outdir      = './tmp/'
   pseudo_dir  = '/work/pseudo'
   verbosity   = 'high'
   tstress     = .true.
   tprnfor     = .true.
   etot_conv_thr = 1.0d-8
   forc_conv_thr = 5.0d-5
/
&SYSTEM
   ibrav       = 0
   nat         = 10
   ntyp        = 3
   ecutwfc     = 120.0
   ecutrho     = 480.0
   occupations = 'fixed'
/
&ELECTRONS
   conv_thr    = 1.0d-10
   mixing_beta = 0.7d0
   electron_maxstep = 200
/
&IONS
   ion_dynamics = 'bfgs'
/
&CELL
   cell_dynamics = 'bfgs'
   press_conv_thr = 0.1
/
{cell_block}
{species_block}
{positions_block}
K_POINTS automatic
4 4 4 0 0 0
"""


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def extract_cell_and_positions(pw_in_text: str):
    m = re.search(r"(CELL_PARAMETERS.*?\n(?:.*\n){3})", pw_in_text)
    cell_block = m.group(1).rstrip("\n")
    m2 = re.search(r"(ATOMIC_POSITIONS.*?\n(?:.*\n)+?)(?=K_POINTS)", pw_in_text)
    positions_block = m2.group(1).rstrip("\n")
    return cell_block, positions_block


def main():
    b2_text = B2_PWIN.read_text()
    cell_block, positions_block = extract_cell_and_positions(b2_text)

    jobs = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}

    # --- short cutoff check ---
    for ecut in [80.0, 100.0, 120.0]:
        job_id = f"C3_cutoff_ecut{int(ecut)}_k4"
        job_dir = OUT_ROOT / "cutoff_check" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        text = SCF_TEMPLATE.format(ecutwfc=ecut, ecutrho=4.0 * ecut, cell_block=cell_block,
                                    species_block=LDA_SPECIES_BLOCK.rstrip("\n"), positions_block=positions_block)
        (job_dir / "pw.in").write_text(text, newline="\n")
        jobs[job_id] = dict(dir=str(job_dir.relative_to(ROOT)).replace("\\", "/"), calc="scf-lda-cutoff-check",
                             ecutwfc_Ry=ecut, ecutrho_Ry=4.0 * ecut, kgrid=[4, 4, 4],
                             pwin_sha256=sha256(job_dir / "pw.in"))

    # --- LDA@PBEsol-geometry EO (methodological comparison only, no LDA relaxation) ---
    eo_pbeg_dir = OUT_ROOT / "EO_at_PBEsol_geom"
    eo_pbeg_dir.mkdir(parents=True, exist_ok=True)
    eo_pw_text = SCF_TEMPLATE.format(ecutwfc=120.0, ecutrho=480.0, cell_block=cell_block,
                                      species_block=LDA_SPECIES_BLOCK.rstrip("\n"), positions_block=positions_block)
    (eo_pbeg_dir / "pw.in").write_text(eo_pw_text, newline="\n")
    (eo_pbeg_dir / "ph.in").write_text(PH_EO_TEMPLATE, newline="\n")
    jobs["C3_EO_at_PBEsol_geom"] = dict(
        dir=str(eo_pbeg_dir.relative_to(ROOT)).replace("\\", "/"), calc="scf+dfpt-gamma-zeu-elop-lda",
        pwin_sha256=sha256(eo_pbeg_dir / "pw.in"), phin_sha256=sha256(eo_pbeg_dir / "ph.in"),
        note="LDA pseudopotentials + zeu + elop on B2's PBEsol-relaxed geometry, UNRELAXED under LDA -- methodological comparison only, not the internally-consistent LDA reference")

    # --- LDA@B0-original-geometry EO (for C12: true B0-vs-B2 comparison, same LDA method) ---
    b0_text = B0_PWIN.read_text()
    b0_cell_block, b0_positions_block = extract_cell_and_positions(b0_text)
    eo_b0_dir = OUT_ROOT / "EO_at_B0_geom"
    eo_b0_dir.mkdir(parents=True, exist_ok=True)
    eo_b0_pw_text = SCF_TEMPLATE.format(ecutwfc=120.0, ecutrho=480.0, cell_block=b0_cell_block,
                                         species_block=LDA_SPECIES_BLOCK.rstrip("\n"), positions_block=b0_positions_block)
    (eo_b0_dir / "pw.in").write_text(eo_b0_pw_text, newline="\n")
    (eo_b0_dir / "ph.in").write_text(PH_EO_TEMPLATE, newline="\n")
    jobs["C3_EO_at_B0_geom"] = dict(
        dir=str(eo_b0_dir.relative_to(ROOT)).replace("\\", "/"), calc="scf+dfpt-gamma-zeu-elop-lda",
        pwin_sha256=sha256(eo_b0_dir / "pw.in"), phin_sha256=sha256(eo_b0_dir / "ph.in"),
        note="LDA pseudopotentials + zeu + elop on B0's ORIGINAL (DEL A/B unrelaxed) geometry -- for C12's true B0-vs-B2 comparison under the same (LDA) EO method")

    # --- vc-relax (production cutoff) ---
    vcr_dir = OUT_ROOT / "vcrelax"
    vcr_dir.mkdir(parents=True, exist_ok=True)
    vcr_text = VCRELAX_TEMPLATE.format(cell_block=cell_block,
                                        species_block=LDA_SPECIES_BLOCK.rstrip("\n"), positions_block=positions_block)
    (vcr_dir / "vcrelax.in").write_text(vcr_text, newline="\n")
    jobs["C3_vcrelax"] = dict(dir=str(vcr_dir.relative_to(ROOT)).replace("\\", "/"), calc="vc-relax-lda",
                               vcrelax_in_sha256=sha256(vcr_dir / "vcrelax.in"),
                               note="starting geometry = B2 PBEsol-relaxed coordinates (initial guess only)")

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(jobs)} total jobs to {QUEUE.relative_to(ROOT)}")
    for k in jobs:
        if k.startswith("C3"):
            print(" ", k)


if __name__ == "__main__":
    main()
