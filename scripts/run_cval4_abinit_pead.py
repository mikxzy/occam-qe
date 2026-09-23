"""C-VAL4 Step 2: run the ABINIT PEAD electronic-only nonlinear-response job with
prtddb=1, so it produces DS4_DDB (dielectric) and DS5_DDB (3rd-order) files.

v3: mrgddb/anaddb moved OUT of this script into a separate one
(run_cval4_abinit_anaddb.py, short/cheap) after v2's combined run got killed by the
330-min GH Actions workflow timeout -- writing the DDB apparently pushes total wall
time just past the previous ~300min mark, and a 6h GH-hosted-runner hard cap leaves
no safe margin to also run mrgddb+anaddb in the same job. This script now ONLY runs
abinit and saves the two DDB files to the artifact; the merge+anaddb step runs
separately, fast, once the DDB files are committed to the repo.

Do NOT run until Step 1 (ground-state parity, run_cval4_abinit_gs.py) has confirmed
QE and ABINIT agree on electron count / eigenvalues / dielectric tensor -- per the
task's own gate: "If eigenvalues/band gap/dielectric response differ grossly, STOP
and diagnose before third-order comparison."

    python scripts/run_cval4_abinit_pead.py --np 4 [--out artifacts/CVAL4_abinit_pead_G1]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue" / "delC_jobs.json"
PSEUDO_DIR = ROOT / "pseudo"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", default="CVAL4_abinit_pead_G1")
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()

    job = json.loads(QUEUE.read_text())[a.job]
    d = ROOT / job["dir"]
    out = Path(a.out) if a.out else d / "artifact"
    out.mkdir(parents=True, exist_ok=True)

    res = dict(job=job, started=time.strftime("%Y-%m-%dT%H:%M:%S"), np=a.np)

    abi_file = d / "abinit_pead_G1.abi"
    ok = sha256(abi_file) == job["abi_sha256"]
    res["pseudopotentials"] = {}
    for el, fname in [("Li", "Li_LDA.upf"), ("Nb", "Nb_LDA.upf"), ("O", "O_LDA.upf")]:
        res["pseudopotentials"][el] = dict(file=fname, sha256=sha256(PSEUDO_DIR / fname))
    if not Path("/work/pseudo").exists():
        ok = False
    res["preconditions_ok"] = ok
    if not ok:
        res["status"] = "FAILED"
        res["reason"] = "precondition failure (hash/paths)"
        json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
        print(json.dumps(res, indent=1, default=str))
        sys.exit(4)

    for f in list(d.glob("abinit_pead_G1.abo")) + list(d.glob("abinit_pead_G1o_*")) + \
             list(d.glob("run.log")) + list(d.glob("run.err")):
        f.unlink()

    t0 = time.time()
    p = subprocess.run(
        f'cd "{d}" && mpirun -np {a.np} abinit abinit_pead_G1.abi > run.log 2> run.err',
        shell=True)
    wall = time.time() - t0
    res.update(abinit_exit_code=p.returncode, wall_s=round(wall, 1))

    abo_path = next(iter(d.glob("abinit_pead_G1.abo")), None) or (d / "run.log")
    abo_text = abo_path.read_text(errors="ignore") if abo_path.exists() else ""
    res["converged"] = "Calculation completed" in abo_text or "have converged" in abo_text.lower()
    res["dataset5_present"] = "DATASET  5" in abo_text or "jdtset  5" in abo_text or "optdriver" in abo_text

    why = []
    if p.returncode != 0:
        why.append("abinit exit code != 0")
    if not res["converged"]:
        why.append("no completion marker found in output")

    # --- confirm DS4_DDB (dielectric) + DS5_DDB (3rd-order) were produced.
    # mrgddb/anaddb run separately (run_cval4_abinit_anaddb.py) to stay well clear
    # of the GH-hosted-runner 6h hard timeout. ---
    ddb4 = next(iter(d.glob("abinit_pead_G1o_DS4_DDB")), None)
    ddb5 = next(iter(d.glob("abinit_pead_G1o_DS5_DDB")), None)
    res["ddb4_present"] = ddb4 is not None
    res["ddb5_present"] = ddb5 is not None
    if not (ddb4 and ddb5):
        why.append("DS4_DDB or DS5_DDB missing")

    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why)
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    for f in list(d.glob("abinit_pead_G1.abi")) + list(d.glob("abinit_pead_G1.abo")) + \
             list(d.glob("run.log")) + list(d.glob("run.err")) + \
             list(d.glob("abinit_pead_G1o_DS4_DDB")) + list(d.glob("abinit_pead_G1o_DS5_DDB")):
        shutil.copy(f, out / f.name)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "job"}, indent=1, default=str))
    sys.exit(0 if res["status"] == "DONE" else 3)


if __name__ == "__main__":
    main()
