"""DEL C-VAL3: geometry parity test. Freeze two QE jobs, both at k=8x8x8, epsil+elop
(trans=.false., matching TEST A's already-validated isolated-elop configuration),
same LDA/PZ NC Li/Nb/O pseudopotentials and cutoff (ecutwfc=120 Ry) throughout:

  G0: our internally-consistent LDA-relaxed Material A geometry (C3_vcrelax's final
      structure) -- re-run only because k=8x8x8 was never tested before (only 4x4x4
      production, 6x6x6 convergence check).
  G1: the published Veithen & Ghosez PRB 65, 214302 (2002) "Present (LDA)"
      ferroelectric R3c structure (Table I formulas + Table III parameters:
      a=5.067 A, c=13.721 A, z=0.0337, u=0.01250, v=0.0302, w=0.0183), reduced to its
      10-atom primitive cell via the OFFICIAL space group 161 symmetry operators (not
      hand-copied) -- verified to reproduce the paper's own O2/O3 formulas exactly as
      an independent consistency check. NOT relaxed with our pseudopotentials (would
      destroy the one-variable comparison, per instruction).

    python scripts/make_cval3_geometry_parity.py
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import numpy as np
from ase.spacegroup import crystal
from ase.data import chemical_symbols
import spglib

ROOT = Path(__file__).resolve().parents[1]
G0_SRC = ROOT / "runs" / "delC" / "C3_LDA" / "vcrelax" / "artifact" / "clean_scf" / "pw.in"
OUT_ROOT = ROOT / "runs" / "delC" / "CVAL3_geometry_parity"
QUEUE = ROOT / "queue" / "delC_jobs.json"

SPECIES_BLOCK = "ATOMIC_SPECIES\nLi 6.94000 Li_LDA.upf\nNb 92.90637 Nb_LDA.upf\nO 15.99900 O_LDA.upf\n"

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
   ecutwfc     = 120.0
   ecutrho     = 480.0
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
8 8 8 0 0 0
"""

PH_IN = "Gamma-point DFPT: dielectric + electro-optic tensor (isolated elop, TEST A config)\n&inputph\n   prefix   = 'linbo3lda'\n   outdir   = './tmp/'\n   fildyn   = 'mat.dyn'\n   epsil    = .true.\n   trans    = .false.\n   zeu      = .false.\n   elop     = .true.\n   tr2_ph   = 1.0d-14\n/\n0.0 0.0 0.0\n"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fmt_cell(cell):
    return "CELL_PARAMETERS angstrom\n" + "\n".join(f"{v[0]: .10f} {v[1]: .10f} {v[2]: .10f}" for v in cell)


def fmt_positions(symbols, frac):
    return "ATOMIC_POSITIONS crystal\n" + "\n".join(
        f"{s} {p[0]: .10f} {p[1]: .10f} {p[2]: .10f}" for s, p in zip(symbols, frac))


def g0_blocks():
    import re
    text = G0_SRC.read_text()
    m = re.search(r"(CELL_PARAMETERS.*?\n(?:.*\n){3})", text)
    cell_block = m.group(1).rstrip("\n")
    m2 = re.search(r"(ATOMIC_POSITIONS.*?\n(?:.*\n)+?)(?=K_POINTS)", text)
    positions_block = m2.group(1).rstrip("\n")
    return cell_block, positions_block


def g1_blocks():
    a, c = 5.067, 13.721
    z, u, v, w = 0.0337, 0.01250, 0.0302, 0.0183
    Nb, Li, O1 = (0, 0, 0), (0, 0, 0.25 + z), (-1 / 3 - u, -1 / 3 + v, 7 / 12 - w)
    atoms = crystal(["Nb", "Li", "O"], basis=[Nb, Li, O1], spacegroup=161, cellpar=[a, a, c, 90, 90, 120])
    cell = (atoms.cell[:], atoms.get_scaled_positions(), atoms.get_atomic_numbers())

    # consistency check: does the generated orbit reproduce the paper's own O2/O3 formulas?
    O2_expected = np.array([(1 / 3 - v) % 1, (-u - v) % 1, (7 / 12 - w) % 1])
    O3_expected = np.array([(u + v) % 1, (1 / 3 + u) % 1, (7 / 12 - w) % 1])
    syms_full = atoms.get_chemical_symbols()
    frac_full = atoms.get_scaled_positions() % 1.0
    Opos = frac_full[[i for i, s in enumerate(syms_full) if s == "O"]]
    assert any(np.allclose(o, O2_expected, atol=1e-5) for o in Opos), "G1 does not reproduce paper's O2"
    assert any(np.allclose(o, O3_expected, atol=1e-5) for o in Opos), "G1 does not reproduce paper's O3"

    plattice, ppositions, pnumbers = spglib.find_primitive(cell, symprec=1e-4)
    plattice = np.array(plattice)
    psyms = [chemical_symbols[zz] for zz in pnumbers]
    order = sorted(range(len(psyms)), key=lambda i: {"Li": 0, "Nb": 1, "O": 2}[psyms[i]])
    psyms = [psyms[i] for i in order]
    ppositions = [ppositions[i] % 1.0 for i in order]
    assert len(psyms) == 10 and psyms.count("Li") == 2 and psyms.count("Nb") == 2 and psyms.count("O") == 6

    # verify no hidden rotation relative to G0's primitive-cell axis convention
    import ase.io
    atoms0 = ase.io.read(str(ROOT / "structures" / "material_A_R3c_COD1541936.cif"))
    cell0 = (atoms0.cell[:], atoms0.get_scaled_positions(), atoms0.get_atomic_numbers())
    plattice0, _, _ = spglib.find_primitive(cell0, symprec=1e-4)
    plattice0 = np.array(plattice0)
    for i in range(3):
        v1 = plattice[i] / np.linalg.norm(plattice[i])
        v0 = plattice0[i] / np.linalg.norm(plattice0[i])
        cosang = float(np.dot(v1, v0))
        assert cosang > 0.9999, f"G1 primitive axis {i} not aligned with G0 convention (cos={cosang})"

    cell_block = fmt_cell(plattice)
    positions_block = fmt_positions(psyms, ppositions)
    return cell_block, positions_block, dict(a=a, c=c, z=z, u=u, v=v, w=w,
                                              primitive_a=float(np.linalg.norm(plattice[0])),
                                              volume_A3=float(abs(np.linalg.det(plattice))))


def main():
    jobs = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}

    g0_cell, g0_pos = g0_blocks()
    g0_dir = OUT_ROOT / "G0_k8"
    g0_dir.mkdir(parents=True, exist_ok=True)
    (g0_dir / "pw.in").write_text(SCF_TEMPLATE.format(cell_block=g0_cell, species_block=SPECIES_BLOCK.rstrip("\n"),
                                                        positions_block=g0_pos), newline="\n")
    (g0_dir / "ph.in").write_text(PH_IN, newline="\n")
    jobs["CVAL3_G0_k8"] = dict(dir=str(g0_dir.relative_to(ROOT)).replace("\\", "/"),
                                calc="scf+dfpt-gamma-elop-only-lda-k8",
                                pwin_sha256=sha256(g0_dir / "pw.in"), phin_sha256=sha256(g0_dir / "ph.in"),
                                note="G0 = our LDA-relaxed geometry (C3_vcrelax), k=8x8x8 (not tested before)")

    g1_cell, g1_pos, g1_meta = g1_blocks()
    g1_dir = OUT_ROOT / "G1_k8"
    g1_dir.mkdir(parents=True, exist_ok=True)
    (g1_dir / "pw.in").write_text(SCF_TEMPLATE.format(cell_block=g1_cell, species_block=SPECIES_BLOCK.rstrip("\n"),
                                                        positions_block=g1_pos), newline="\n")
    (g1_dir / "ph.in").write_text(PH_IN, newline="\n")
    (g1_dir / "structure_provenance.json").write_text(json.dumps(dict(
        source="Veithen & Ghosez, Phys. Rev. B 65, 214302 (2002), Tables I and III, 'Present (LDA)' ferroelectric R3c",
        **g1_meta), indent=1))
    jobs["CVAL3_G1_k8"] = dict(dir=str(g1_dir.relative_to(ROOT)).replace("\\", "/"),
                                calc="scf+dfpt-gamma-elop-only-lda-k8",
                                pwin_sha256=sha256(g1_dir / "pw.in"), phin_sha256=sha256(g1_dir / "ph.in"),
                                note="G1 = Veithen & Ghosez PRB 65, 214302 (2002) published LDA geometry, NOT relaxed with our pseudopotentials")

    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")
    print("wrote CVAL3_G0_k8, CVAL3_G1_k8")
    print("G1 metadata:", g1_meta)


if __name__ == "__main__":
    main()
