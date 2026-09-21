"""Freeze the DEL B B0/B1/B2 inputs. Reuses the exact DEL A production structure blocks
verbatim from runs/convergence_dfpt/dfpt_ecut120_k4/pw.in (never re-derived from the CIF,
per instruction) -- and asserts that file is byte-identical to what DEL A committed.

    python scripts/make_delB_inputs.py

Writes:
  runs/delB/B0/pw.in, ph.in                        -- exact DEL A structure, re-run to
                                                        capture eigenvectors + Born charges
                                                        (not saved by the original DEL A run)
  runs/delB/B1/relax.in                             -- calculation='relax', fixed cell
  runs/delB/B2/vcrelax.in                           -- calculation='vc-relax'
queue/delB_jobs.json records each frozen input's sha256.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from qe_in_parser import extract_blocks
from ph_dfpt_zeu_template import render as render_ph_zeu

ROOT = Path(__file__).resolve().parents[1]
DEL_A_PWIN = ROOT / "runs" / "convergence_dfpt" / "dfpt_ecut120_k4" / "pw.in"
RUNS = ROOT / "runs" / "delB"
QUEUE = ROOT / "queue" / "delB_jobs.json"

CONTROL_COMMON = """   pseudo_dir  = '/work/pseudo'
   verbosity   = 'high'
"""
SYSTEM_COMMON = """   ecutwfc     = 120.0
   ecutrho     = 480.0
   occupations = 'fixed'
"""
ELECTRONS_COMMON = """&ELECTRONS
   conv_thr    = 1.0d-10
   mixing_beta = 0.7d0
   electron_maxstep = 200
/
"""


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def b0_scf_input(blocks: dict) -> str:
    # byte-identical to the DEL A production pw.in (SCF, tstress+tprnfor) -- re-run only
    # because this ephemeral runner needs a fresh tmp/ outdir before ph.x can read it.
    return DEL_A_PWIN.read_text()


def relax_input(blocks: dict) -> str:
    return f"""&CONTROL
   calculation = 'relax'
   prefix      = 'linbo3'
   outdir      = './tmp/'
{CONTROL_COMMON}   tstress     = .true.
   tprnfor     = .true.
   etot_conv_thr = 1.0d-8
   forc_conv_thr = 5.0d-5
/
&SYSTEM
   ibrav       = 0
   nat         = {blocks['nat']}
   ntyp        = {blocks['ntyp']}
{SYSTEM_COMMON}/
{ELECTRONS_COMMON}&IONS
   ion_dynamics = 'bfgs'
/
{blocks['cell_block']}
{blocks['species_block']}
{blocks['positions_block']}
{blocks['kpoints_block']}"""


def vcrelax_input(blocks: dict) -> str:
    return f"""&CONTROL
   calculation = 'vc-relax'
   prefix      = 'linbo3'
   outdir      = './tmp/'
{CONTROL_COMMON}   tstress     = .true.
   tprnfor     = .true.
   etot_conv_thr = 1.0d-8
   forc_conv_thr = 5.0d-5
/
&SYSTEM
   ibrav       = 0
   nat         = {blocks['nat']}
   ntyp        = {blocks['ntyp']}
{SYSTEM_COMMON}/
{ELECTRONS_COMMON}&IONS
   ion_dynamics = 'bfgs'
/
&CELL
   cell_dynamics = 'bfgs'
   press_conv_thr = 0.1
/
{blocks['cell_block']}
{blocks['species_block']}
{blocks['positions_block']}
{blocks['kpoints_block']}"""


def main():
    assert DEL_A_PWIN.exists(), f"missing DEL A production input: {DEL_A_PWIN}"
    blocks = extract_blocks(DEL_A_PWIN)
    assert blocks["nat"] == 10 and blocks["ntyp"] == 3, blocks

    jobs = {}

    # --- B0: exact DEL A structure, re-run to capture eigenvectors + Born charges
    b0_dir = RUNS / "B0"
    b0_dir.mkdir(parents=True, exist_ok=True)
    (b0_dir / "pw.in").write_text(b0_scf_input(blocks), newline="\n")
    (b0_dir / "ph.in").write_text(render_ph_zeu(), newline="\n")
    assert sha256(b0_dir / "pw.in") == sha256(DEL_A_PWIN), "B0 pw.in must be byte-identical to the DEL A production input"
    jobs["B0"] = dict(dir="runs/delB/B0", calc="scf+dfpt-gamma-zeu",
                       pwin_sha256=sha256(b0_dir / "pw.in"), phin_sha256=sha256(b0_dir / "ph.in"),
                       note="byte-identical to runs/convergence_dfpt/dfpt_ecut120_k4/pw.in")

    # --- B1: fixed-cell ionic relax
    b1_dir = RUNS / "B1"
    b1_dir.mkdir(parents=True, exist_ok=True)
    (b1_dir / "relax.in").write_text(relax_input(blocks), newline="\n")
    jobs["B1"] = dict(dir="runs/delB/B1", calc="relax(fixed-cell)+scf+dfpt-gamma-zeu",
                       relax_in_sha256=sha256(b1_dir / "relax.in"))

    # --- B2: full vc-relax
    b2_dir = RUNS / "B2"
    b2_dir.mkdir(parents=True, exist_ok=True)
    (b2_dir / "vcrelax.in").write_text(vcrelax_input(blocks), newline="\n")
    jobs["B2"] = dict(dir="runs/delB/B2", calc="vc-relax+scf+dfpt-gamma-zeu",
                       vcrelax_in_sha256=sha256(b2_dir / "vcrelax.in"))

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")
    print(f"wrote {QUEUE.relative_to(ROOT)}")
    for k, v in jobs.items():
        print(f"  {k}: {v['dir']}")


if __name__ == "__main__":
    main()
