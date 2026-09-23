"""C-VAL4 Step 2 part 1/2: run ABINIT datasets 1-4 (ground state through
electric-field DFPT response) only. Produces the WF/DEN/DDB files dataset 5 needs
(abinit_pead_G1o_DS2_WF*, abinit_pead_G1o_DS4_1WF*, abinit_pead_G1o_DS4_DEN*,
abinit_pead_G1o_DS4_DDB), which are copied to the artifact output so a separate,
short follow-up job (run_cval4_abinit_pead_ds5.py) can continue from them.

    python scripts/run_cval4_abinit_pead_ds14.py --np 4 [--out artifacts/CVAL4_abinit_pead_G1_ds14]
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
    ap.add_argument("--job", default="CVAL4_abinit_pead_G1_ds14")
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()

    job = json.loads(QUEUE.read_text())[a.job]
    d = ROOT / job["dir"]
    out = Path(a.out) if a.out else d / "artifact_ds14"
    out.mkdir(parents=True, exist_ok=True)

    res = dict(job=job, started=time.strftime("%Y-%m-%dT%H:%M:%S"), np=a.np)

    abi_file = d / "abinit_pead_G1_ds14.abi"
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

    for f in list(d.glob("abinit_pead_G1_ds14.abo")) + list(d.glob("run_ds14.log")) + list(d.glob("run_ds14.err")):
        f.unlink()

    t0 = time.time()
    p = subprocess.run(
        f'cd "{d}" && mpirun -np {a.np} abinit abinit_pead_G1_ds14.abi > run_ds14.log 2> run_ds14.err',
        shell=True)
    wall = time.time() - t0
    res.update(abinit_exit_code=p.returncode, wall_s=round(wall, 1))

    abo_path = next(iter(d.glob("abinit_pead_G1_ds14.abo")), None) or (d / "run_ds14.log")
    abo_text = abo_path.read_text(errors="ignore") if abo_path.exists() else ""
    res["converged"] = "Calculation completed" in abo_text or "have converged" in abo_text.lower()

    why = []
    if p.returncode != 0:
        why.append("abinit exit code != 0")
    if not res["converged"]:
        why.append("no completion marker found in output")

    ds2_wf = list(d.glob("abinit_pead_G1o_DS2_WF"))
    ds4_1wf = list(d.glob("abinit_pead_G1o_DS4_1WF*"))
    ds4_den = list(d.glob("abinit_pead_G1o_DS4_DEN*"))
    ddb4 = next(iter(d.glob("abinit_pead_G1o_DS4_DDB")), None)
    res["ds2_wf_present"] = len(ds2_wf) > 0
    res["ds4_1wf_count"] = len(ds4_1wf)
    res["ds4_den_count"] = len(ds4_den)
    res["ddb4_present"] = ddb4 is not None
    if not (ds2_wf and ds4_1wf and ds4_den and ddb4):
        why.append("one or more checkpoint files (DS2_WF/DS4_1WF/DS4_DEN/DS4_DDB) missing")

    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why)
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    checkpoint_files = (
        list(d.glob("abinit_pead_G1_ds14.abi")) + list(d.glob("abinit_pead_G1_ds14.abo")) +
        list(d.glob("run_ds14.log")) + list(d.glob("run_ds14.err")) +
        list(d.glob("abinit_pead_G1_ds5.abi")) +  # carried forward for the ds5 job
        list(d.glob("abinit_pead_G1o_DS2_WF")) +
        list(d.glob("abinit_pead_G1o_DS4_1WF*")) +
        list(d.glob("abinit_pead_G1o_DS4_DEN*")) +
        list(d.glob("abinit_pead_G1o_DS4_DDB"))
    )
    for f in checkpoint_files:
        shutil.copy(f, out / f.name)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "job"}, indent=1, default=str))
    sys.exit(0 if res["status"] == "DONE" else 3)


if __name__ == "__main__":
    main()
