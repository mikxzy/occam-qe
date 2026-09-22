"""DEL C-VAL2, TEST D: freeze the AlAs (zincblende) reference-material inputs.
Independent control case Veithen et al. also validated their method against (though
using a different starting reference for AlAs specifically than the LiNbO3 case).

Structure: F-43m #216 (zincblende), built via ASE bulk('AlAs', 'zincblende', a=5.660 A)
-- 5.660 A is the well-established experimental lattice constant (cross-checked via web
search, not memory), used only as a vc-relax starting point, matching the same
"real/documented starting geometry -> let LDA relax it" methodology used for Material A
throughout this project. No internal free coordinates (both atoms fixed by symmetry) --
vc-relax only adjusts the cell volume/lattice constant.

    python scripts/make_cval2_testD_alas.py
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from ase.build import bulk

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "runs" / "delC" / "CVAL2_testD_AlAs"
QUEUE = ROOT / "queue" / "delC_jobs.json"

SPECIES_BLOCK = "ATOMIC_SPECIES\nAl 26.9815385 Al_LDA.upf\nAs 74.9216 As_LDA.upf\n"

SCF_TEMPLATE = """&CONTROL
   calculation = 'scf'
   prefix      = 'alas_lda'
   outdir      = './tmp/'
   pseudo_dir  = '/work/pseudo'
   verbosity   = 'high'
   tstress     = .true.
   tprnfor     = .true.
/
&SYSTEM
   ibrav       = 0
   nat         = 2
   ntyp        = 2
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
{k} {k} {k} 0 0 0
"""

VCRELAX_TEMPLATE = """&CONTROL
   calculation = 'vc-relax'
   prefix      = 'alas_lda'
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
   nat         = 2
   ntyp        = 2
   ecutwfc     = 60.0
   ecutrho     = 240.0
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
8 8 8 0 0 0
"""

PH_EO_TEMPLATE = "Gamma-point DFPT: dielectric + electro-optic tensor, AlAs zincblende (LDA control)\n&inputph\n   prefix   = 'alas_lda'\n   outdir   = './tmp/'\n   fildyn   = 'mat.dyn'\n   epsil    = .true.\n   trans    = .true.\n   zeu      = .true.\n   elop     = .true.\n   tr2_ph   = 1.0d-14\n/\n0.0 0.0 0.0\n"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def get_blocks():
    atoms = bulk("AlAs", crystalstructure="zincblende", a=5.660)
    cell = atoms.cell[:]
    frac = atoms.get_scaled_positions()
    syms = atoms.get_chemical_symbols()
    cell_block = "CELL_PARAMETERS angstrom\n" + "\n".join(f"{v[0]: .10f} {v[1]: .10f} {v[2]: .10f}" for v in cell)
    positions_block = "ATOMIC_POSITIONS crystal\n" + "\n".join(
        f"{s} {p[0]: .10f} {p[1]: .10f} {p[2]: .10f}" for s, p in zip(syms, frac))
    return cell_block, positions_block


def main():
    cell_block, positions_block = get_blocks()
    jobs = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}

    for ecut, k, tag in [(60.0, 8, "ecut60_k8"), (60.0, 6, "ecut60_k6"), (80.0, 8, "ecut80_k8")]:
        job_id = f"CVAL2_AlAs_cutoff_{tag}"
        job_dir = OUT_ROOT / "cutoff_check" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        text = SCF_TEMPLATE.format(ecutwfc=ecut, ecutrho=4.0 * ecut, k=k, cell_block=cell_block,
                                    species_block=SPECIES_BLOCK.rstrip("\n"), positions_block=positions_block)
        (job_dir / "pw.in").write_text(text, newline="\n")
        jobs[job_id] = dict(dir=str(job_dir.relative_to(ROOT)).replace("\\", "/"), calc="scf-alas-cutoff-check",
                             ecutwfc_Ry=ecut, kgrid=[k, k, k], pwin_sha256=sha256(job_dir / "pw.in"))

    vcr_dir = OUT_ROOT / "vcrelax"
    vcr_dir.mkdir(parents=True, exist_ok=True)
    vcr_text = VCRELAX_TEMPLATE.format(cell_block=cell_block, species_block=SPECIES_BLOCK.rstrip("\n"),
                                        positions_block=positions_block)
    (vcr_dir / "vcrelax.in").write_text(vcr_text, newline="\n")
    jobs["CVAL2_AlAs_vcrelax"] = dict(dir=str(vcr_dir.relative_to(ROOT)).replace("\\", "/"), calc="vc-relax-alas-lda",
                                       vcrelax_in_sha256=sha256(vcr_dir / "vcrelax.in"),
                                       note="starting geometry: zincblende, a=5.660 A (experimental, web-verified), ASE bulk()")

    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(jobs)} total jobs")
    for k in jobs:
        if k.startswith("CVAL2_AlAs"):
            print(" ", k)


if __name__ == "__main__":
    main()
