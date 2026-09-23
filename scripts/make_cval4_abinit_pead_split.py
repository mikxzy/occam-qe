"""C-VAL4 Step 2 v4: split the PEAD input (make_cval4_abinit_pead.py) into two ABINIT
invocations that checkpoint across a GH Actions job boundary, after three ~5-6h
single-job attempts were lost to the platform's 6h hard timeout on hosted runners.

  ds14: ndtset 4, jdtset 1 2 3 4 -- ground state through the electric-field DFPT
        response (dataset 4). This is the expensive, iterative part (69 SCF-type
        iteration lines in the completed run's log for dataset 4 alone).
  ds5:  ndtset 1, jdtset 5 -- the third-order energy evaluation only. Confirmed
        non-iterative (0 "ETOT"/"iter" lines in dataset 5's log region of the one
        completed run) -- reads ds14's saved WF/DEN files (getwfk5=2, get1den5=4,
        get1wf5=4 -- ABINIT resolves these by the "<prefix>o_DS<N>_<type>" filename
        convention regardless of which invocation produced them, so ds14's output
        directory just needs to be carried forward as-is into ds5's working dir).

Both share the identical geometry/pseudopotentials/ecut/k-grid as the single-job
version -- this is a pure checkpoint split, not a physics change.

    python scripts/make_cval4_abinit_pead_split.py
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


def common_block(cell_bohr, species, frac, ecut_ha, ngkpt, n_occ, pp_paths):
    rprim_lines = "\n".join(f"  {v[0]: .12f}  {v[1]: .12f}  {v[2]: .12f}" for v in cell_bohr)
    xred_lines = "\n".join(f"  {p[0]: .10f}  {p[1]: .10f}  {p[2]: .10f}" for p in frac)
    typat_str = " ".join(str(ELEMENT_ORDER.index(s) + 1) for s in species)
    znucl_str = " ".join(str(ZNUCL[e]) for e in ELEMENT_ORDER)
    return f"""# --- cell (Bohr; acell=1 so rprim carries the real vectors directly) ---
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
prtddb 1
"""


def main():
    text = QE_G1_PWIN.read_text()
    cell_ang, species, frac, ecutwfc_ry, ngkpt = parse_qe_g1(text)
    cell_bohr = [[v * BOHR_PER_ANGSTROM for v in row] for row in cell_ang]
    ecut_ha = ecutwfc_ry / RY_PER_HA
    nelec_expected = sum({"Li": 3, "Nb": 13, "O": 6}[s] for s in species)
    n_occ = nelec_expected // 2
    pp_paths = [PP_FILES[el] for el in ELEMENT_ORDER]
    pp_hashes = {el: dict(filename=PP_FILES[el], sha256=sha256(PSEUDO_DIR / PP_FILES[el])) for el in ELEMENT_ORDER}
    common = common_block(cell_bohr, species, frac, ecut_ha, ngkpt, n_occ, pp_paths)

    ds14 = f"""# C-VAL4 Step 2 (part 1/2): ABINIT PEAD ground state through electric-field
# DFPT response (datasets 1-4). Split from the single 5-dataset run to checkpoint
# across a GH Actions job boundary -- this part carries essentially all the compute
# cost (dataset 4's DFPT response is iterative; dataset 5 is not).

ndtset 4
jdtset 1 2 3 4

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
#           deliberately omitted -- purely electronic/clamped-ion response)
   getwfk4    2
   kptopt4    2
   getddk4    3
   rfelfd4    3
   tolvrs4    1.0d-12
  prepanl4    1
    prtwf4    1
   prtden4    1

{common}"""

    ds5 = f"""# C-VAL4 Step 2 (part 2/2): ABINIT PEAD 3rd-order (electronic chi2_eee) response.
# Reads dataset 1-4's saved WF/DEN files (this job's working directory must already
# contain abinit_pead_G1o_DS2_WF*, abinit_pead_G1o_DS4_1WF*, abinit_pead_G1o_DS4_DEN*
# from the ds14 part -- carried forward via GH Actions artifact, not recomputed).
# jdtset 5 keeps ABINIT's "_DS5_" file-naming/get-variable convention identical to
# the single-job version, so getwfk5/get1den5/get1wf5 resolve exactly as before.

ndtset 1
jdtset 5

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

{common}"""

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "abinit_pead_G1_ds14.abi").write_text(ds14, newline="\n")
    (OUT_DIR / "abinit_pead_G1_ds5.abi").write_text(ds5, newline="\n")

    jobs = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}
    jobs["CVAL4_abinit_pead_G1_ds14"] = dict(
        dir=str(OUT_DIR.relative_to(ROOT)).replace("\\", "/"),
        calc="abinit-pead-electronic-nlo-ds1to4-checkpoint",
        abi_sha256=sha256(OUT_DIR / "abinit_pead_G1_ds14.abi"),
        note="C-VAL4 Step 2 part 1/2: ground state through electric-field DFPT "
             "response (datasets 1-4), checkpointed for a separate dataset-5 job.",
    )
    jobs["CVAL4_abinit_pead_G1_ds5"] = dict(
        dir=str(OUT_DIR.relative_to(ROOT)).replace("\\", "/"),
        calc="abinit-pead-electronic-nlo-ds5-from-checkpoint",
        abi_sha256=sha256(OUT_DIR / "abinit_pead_G1_ds5.abi"),
        note="C-VAL4 Step 2 part 2/2: 3rd-order (electronic chi2_eee) response, "
             "reading ds14's checkpointed WF/DEN files.",
    )
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")

    print(f"wrote {OUT_DIR / 'abinit_pead_G1_ds14.abi'}")
    print(f"wrote {OUT_DIR / 'abinit_pead_G1_ds5.abi'}")


if __name__ == "__main__":
    main()
