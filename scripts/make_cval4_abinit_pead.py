"""C-VAL4 Step 2: build the ABINIT PEAD (usepead=1, default) 5-dataset input for the
purely electronic / clamped-ion third-order response (chi2_eee, elfd-elfd-elfd only)
at the exact Veithen & Ghosez G1 geometry, identical PseudoDojo Li/Nb/O LDA UPF2
pseudopotentials and cutoff/k-grid as the QE and ABINIT-GS branches.

Dataset structure adapted directly from ABINIT's official nlo tutorial reference
input (tests/tutorespfn/Input/tnlo_2.abi, co-authored by M. Veithen -- fetched
verbatim from github.com/abinit/abinit, not reconstructed from memory), with the
rfphon4/rfstrs4 (phonon/strain response) and d3e_pert1_phon5/d3e_pert1_atpol5
(mixed elfd-phon perturbation) lines REMOVED: the task requires the purely
electronic/clamped-ion response only (no atomic relaxation, no phonon-mediated
contribution, no piezoelectric contribution).

    python scripts/make_cval4_abinit_pead.py
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QE_G1_PWIN = ROOT / "runs" / "delC" / "CVAL3_geometry_parity" / "G1_k8" / "pw.in"
OUT_DIR = ROOT / "runs" / "delC" / "CVAL4_code_parity" / "abinit_pead_G1"
PSEUDO_DIR = ROOT / "pseudo"
QUEUE = ROOT / "queue" / "delC_jobs.json"

BOHR_PER_ANGSTROM = 1.8897259886
RY_PER_HA = 2.0

ZNUCL = {"Li": 3, "Nb": 41, "O": 8}
PP_FILES = {"Li": "Li_LDA.upf", "Nb": "Nb_LDA.upf", "O": "O_LDA.upf"}
ELEMENT_ORDER = ["Li", "Nb", "O"]


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
    n_occ = nelec_expected // 2  # PEAD tutorial convention: nband = filled bands only, nbdbuf=0

    pp_paths = [PP_FILES[el] for el in ELEMENT_ORDER]
    pp_hashes = {el: dict(filename=PP_FILES[el], sha256=sha256(PSEUDO_DIR / PP_FILES[el])) for el in ELEMENT_ORDER}

    rprim_lines = "\n".join(f"  {v[0]: .12f}  {v[1]: .12f}  {v[2]: .12f}" for v in cell_bohr)
    xred_lines = "\n".join(f"  {p[0]: .10f}  {p[1]: .10f}  {p[2]: .10f}" for p in frac)
    typat_str = " ".join(str(t) for t in typat)
    znucl_str = " ".join(str(ZNUCL[e]) for e in ELEMENT_ORDER)
    atpol_str = " ".join(str(i) for i in range(1, len(species) + 1))

    abi = f"""# C-VAL4 Step 2: ABINIT PEAD purely-electronic (clamped-ion) 3rd-order response,
# elfd-elfd-elfd only (no rfphon/rfstrs, no d3e_pert1_phon/atpol), at the exact
# Veithen & Ghosez G1 geometry, identical LDA UPF2 pseudopotentials, ecut/k-grid
# matched to the QE and ABINIT-GS branches. Dataset structure adapted from ABINIT's
# official tests/tutorespfn/Input/tnlo_2.abi (M. Veithen co-author), electronic-only.

ndtset 5

#DATASET1 : scf calculation: GS WF in the IBZ
   prtden1    1
    prtwf1    1
   kptopt1    1
   toldfe1    1.0d-12

#DATASET2 : non-scf calculation: GS WF in half BZ (time-reversal only)
   getden2    1
   kptopt2    2
   getwfk2    1
     iscf2   -2
   tolwfr2    1.0d-22
    prtwf2    1

#DATASET3 : d/dk derivative of WF (needed for electric-field response)
   getwfk3    2
   kptopt3    2
   rfelfd3    2
   tolwfr3    1.0d-22
    prtwf3    1

#DATASET4 : 1st-order WF response to electric field ONLY (rfphon/rfstrs
#           deliberately omitted -- purely electronic/clamped-ion response,
#           per C-VAL4 Step 2: no atomic relaxation, no phonon-mediated
#           contribution, no piezoelectric contribution)
   getwfk4    2
   kptopt4    2
   getddk4    3
   rfelfd4    3
   tolvrs4    1.0d-12
  prepanl4    1
    prtwf4    1
   prtden4    1

#DATASET5 : 3rd-order derivative of E, electric field triple perturbation only
#           (d3e_pert1_phon / d3e_pert1_atpol deliberately omitted -- this gives
#           chi2_eee, the purely electronic clamped-ion nonlinear susceptibility)
   getwfk5           2
  get1den5           4
   get1wf5           4
   kptopt5           2
optdriver5           5
  d3e_pert1_elfd5    1
  d3e_pert2_elfd5    1
  d3e_pert3_elfd5    1

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
nband {n_occ}
nbdbuf 0
occopt 1
nstep 200

# --- k-points: unshifted 8x8x8, matches QE K_POINTS automatic 8 8 8 0 0 0 ---
ngkpt {ngkpt[0]} {ngkpt[1]} {ngkpt[2]}
nshiftk 1
shiftk 0.0 0.0 0.0

# --- pseudopotentials (identical UPF2 files used by the QE and ABINIT-GS branches) ---
pp_dirpath "/work/pseudo"
pseudos "{', '.join(pp_paths)}"

prtwf 0
prtden 0
prteig 0
"""

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "abinit_pead_G1.abi").write_text(abi, newline="\n")
    (OUT_DIR / "provenance.json").write_text(json.dumps(dict(
        source_pwin=str(QE_G1_PWIN.relative_to(ROOT)).replace("\\", "/"),
        source_pwin_sha256=sha256(QE_G1_PWIN),
        dataset_template_source="github.com/abinit/abinit tests/tutorespfn/Input/tnlo_2.abi "
                                 "(fetched verbatim, authors incl. M. Veithen); rfphon4/rfstrs4 "
                                 "and d3e_pert1_phon5/d3e_pert1_atpol5 removed for electronic-only response",
        pseudopotential_sha256=pp_hashes,
        ecutwfc_ry_qe=ecutwfc_ry, ecut_ha_abinit=ecut_ha,
        ngkpt=ngkpt, nband=n_occ, nbdbuf=0, nelec_expected=nelec_expected,
        method="ABINIT_PEAD", usepead_default=True,
        perturbations="d3e_pert{1,2,3}_elfd only -- chi2_eee purely electronic clamped-ion tensor",
    ), indent=1))

    jobs = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}
    jobs["CVAL4_abinit_pead_G1"] = dict(
        dir=str(OUT_DIR.relative_to(ROOT)).replace("\\", "/"),
        calc="abinit-pead-electronic-nlo-5dataset",
        abi_sha256=sha256(OUT_DIR / "abinit_pead_G1.abi"),
        note="C-VAL4 Step 2 (ABINIT_PEAD label): purely electronic clamped-ion "
             "chi2_eee via ABINIT's PEAD (usepead=1 default) route, elfd-elfd-elfd "
             "perturbation only, at the exact QE CVAL3_G1_k8 geometry/cutoff/k-grid.",
    )
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")

    print(f"wrote {OUT_DIR / 'abinit_pead_G1.abi'}")
    print(f"nband={n_occ} (occupied only, nbdbuf=0), ngkpt={ngkpt}, ecut={ecut_ha} Ha")


if __name__ == "__main__":
    main()
