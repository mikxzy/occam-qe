"""C-VAL4 Step 0/1: build the ABINIT ground-state input for Material A at the exact
Veithen & Ghosez G1 geometry, using the identical cell/positions already frozen for
QE's CVAL3_G1_k8 job (runs/delC/CVAL3_geometry_parity/G1_k8/pw.in) and the identical
PseudoDojo Li/Nb/O LDA UPF2 pseudopotential files QE uses.

Only the code changes (QE -> ABINIT); geometry, XC, pseudopotentials, k-grid and
plane-wave cutoff are held fixed for a like-for-like ground-state parity check before
any nonlinear-response (Step 2+) comparison is attempted.

    python scripts/make_cval4_abinit.py
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QE_G1_PWIN = ROOT / "runs" / "delC" / "CVAL3_geometry_parity" / "G1_k8" / "pw.in"
OUT_DIR = ROOT / "runs" / "delC" / "CVAL4_code_parity" / "abinit_gs_G1"
PSEUDO_DIR = ROOT / "pseudo"
QUEUE = ROOT / "queue" / "delC_jobs.json"

BOHR_PER_ANGSTROM = 1.8897259886
RY_PER_HA = 2.0

ZNUCL = {"Li": 3, "Nb": 41, "O": 8}
PP_FILES = {"Li": "Li_LDA.upf", "Nb": "Nb_LDA.upf", "O": "O_LDA.upf"}
ELEMENT_ORDER = ["Li", "Nb", "O"]  # typat index order (1-based) matches this


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_qe_g1(text: str):
    m = re.search(r"CELL_PARAMETERS angstrom\n((?:.*\n){3})", text)
    cell_lines = m.group(1).strip("\n").splitlines()
    cell_ang = [[float(x) for x in line.split()] for line in cell_lines]

    m2 = re.search(r"ATOMIC_POSITIONS crystal\n((?:.*\n)+?)(?=K_POINTS)", text)
    pos_lines = m2.group(1).strip("\n").splitlines()
    species, frac = [], []
    for line in pos_lines:
        parts = line.split()
        species.append(parts[0])
        frac.append([float(x) for x in parts[1:4]])

    m3 = re.search(r"ecutwfc\s*=\s*([\d.]+)", text)
    ecutwfc_ry = float(m3.group(1))

    m4 = re.search(r"K_POINTS automatic\n(\d+)\s+(\d+)\s+(\d+)", text)
    ngkpt = [int(m4.group(i)) for i in (1, 2, 3)]

    return cell_ang, species, frac, ecutwfc_ry, ngkpt


def main():
    text = QE_G1_PWIN.read_text()
    cell_ang, species, frac, ecutwfc_ry, ngkpt = parse_qe_g1(text)
    cell_bohr = [[v * BOHR_PER_ANGSTROM for v in row] for row in cell_ang]
    ecut_ha = ecutwfc_ry / RY_PER_HA

    typat = [ELEMENT_ORDER.index(s) + 1 for s in species]
    nelec_expected = sum({"Li": 3, "Nb": 13, "O": 6}[s] for s in species)
    n_occ = nelec_expected // 2
    nband = n_occ + 8  # a few empty conduction bands, for CBM/gap comparison (QE ran occ-only)

    pp_paths = []
    pp_hashes = {}
    for el in ELEMENT_ORDER:
        p = PSEUDO_DIR / PP_FILES[el]
        pp_paths.append(PP_FILES[el])
        pp_hashes[el] = dict(filename=PP_FILES[el], sha256=sha256(p))

    rprim_lines = "\n".join(f"  {v[0]: .12f}  {v[1]: .12f}  {v[2]: .12f}" for v in cell_bohr)
    xred_lines = "\n".join(f"  {p[0]: .10f}  {p[1]: .10f}  {p[2]: .10f}" for p in frac)
    typat_str = " ".join(str(t) for t in typat)
    znucl_str = " ".join(str(ZNUCL[e]) for e in ELEMENT_ORDER)

    abi = f"""# C-VAL4 Step 1: ABINIT ground-state SCF at the exact Veithen & Ghosez G1
# geometry, identical PseudoDojo LDA UPF2 pseudopotentials, ecut/k-grid matched to
# the QE CVAL3_G1_k8 job for like-for-like ground-state parity.

ndtset 1

# --- cell (Bohr; acell=1 so rprim carries the real vectors directly) ---
acell 1.0 1.0 1.0
rprim
{rprim_lines}

# --- atoms ---
natom {len(species)}
ntypat {len(ELEMENT_ORDER)}
znucl {znucl_str}
typat {typat_str}
xred
{xred_lines}

# --- plane-wave basis / electrons ---
ecut {ecut_ha:.6f}
nband {nband}
occopt 1
nstep 200
toldfe 1.0d-12
diemac 6.0

# --- k-points: unshifted 8x8x8, matches QE K_POINTS automatic 8 8 8 0 0 0 ---
kptopt 1
ngkpt {ngkpt[0]} {ngkpt[1]} {ngkpt[2]}
nshiftk 1
shiftk 0.0 0.0 0.0

# --- pseudopotentials (identical UPF2 files used by the QE branch) ---
pp_dirpath "/work/pseudo"
pseudos "{', '.join(pp_paths)}"

prtwf 1
prtden 1
"""

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "abinit_gs_G1.abi").write_text(abi, newline="\n")
    (OUT_DIR / "provenance.json").write_text(json.dumps(dict(
        source_pwin=str(QE_G1_PWIN.relative_to(ROOT)).replace("\\", "/"),
        source_pwin_sha256=sha256(QE_G1_PWIN),
        pseudopotential_sha256=pp_hashes,
        ecutwfc_ry_qe=ecutwfc_ry, ecut_ha_abinit=ecut_ha,
        ngkpt=ngkpt, nband=nband, n_occ=n_occ, nelec_expected=nelec_expected,
        note="Cell/positions transcribed directly from the frozen QE CVAL3_G1_k8 "
             "pw.in (bytes hashed above), not re-derived, to guarantee identical "
             "geometry input to both codes.",
    ), indent=1))

    jobs = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}
    jobs["CVAL4_abinit_gs_G1"] = dict(
        dir=str(OUT_DIR.relative_to(ROOT)).replace("\\", "/"),
        calc="abinit-scf-groundstate-parity-check",
        abi_sha256=sha256(OUT_DIR / "abinit_gs_G1.abi"),
        note="Step 0/1 of C-VAL4: ABINIT ground-state SCF at exact QE CVAL3_G1_k8 "
             "geometry/cutoff/k-grid/pseudopotentials, for eigenvalue/electron-count/"
             "dielectric-tensor parity check before any nonlinear-response comparison.",
    )
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")

    print(f"wrote {OUT_DIR / 'abinit_gs_G1.abi'}")
    print(f"ecutwfc {ecutwfc_ry} Ry -> ecut {ecut_ha} Ha")
    print(f"nband={nband} (n_occ={n_occ}, nelec={nelec_expected}), ngkpt={ngkpt}")
    print("pseudopotential hashes:", json.dumps(pp_hashes, indent=1))


if __name__ == "__main__":
    main()
