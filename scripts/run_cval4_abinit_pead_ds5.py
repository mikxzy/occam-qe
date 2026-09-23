"""C-VAL4 Step 2 part 2/2: run ABINIT dataset 5 (3rd-order electronic chi2_eee)
using the checkpoint files from part 1/2 (already placed in the job directory by the
workflow's artifact-download step), then merge DDBs and run anaddb (dieflag=1,
nlflag=1) for ABINIT's own authoritative electronic EO tensor.

Expects abinit_pead_G1_ds5.abi, abinit_pead_G1o_DS2_WF, abinit_pead_G1o_DS4_1WF*,
abinit_pead_G1o_DS4_DEN*, abinit_pead_G1o_DS4_DDB already present in the job
directory (from run_cval4_abinit_pead_ds14.py's artifact).

    python scripts/run_cval4_abinit_pead_ds5.py --np 4 [--out artifacts/CVAL4_abinit_pead_G1_ds5]
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
    ap.add_argument("--job", default="CVAL4_abinit_pead_G1_ds5")
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()

    job = json.loads(QUEUE.read_text())[a.job]
    d = ROOT / job["dir"]
    out = Path(a.out) if a.out else d / "artifact_ds5"
    out.mkdir(parents=True, exist_ok=True)

    res = dict(job=job, started=time.strftime("%Y-%m-%dT%H:%M:%S"), np=a.np)

    abi_file = d / "abinit_pead_G1_ds5.abi"
    ok = abi_file.exists() and sha256(abi_file) == job["abi_sha256"]
    ds2_wf = d / "abinit_pead_G1o_DS2_WF"
    ds4_1wf = list(d.glob("abinit_pead_G1o_DS4_1WF*"))
    ds4_den = list(d.glob("abinit_pead_G1o_DS4_DEN*"))
    ddb4 = d / "abinit_pead_G1o_DS4_DDB"
    checkpoint_ok = ds2_wf.exists() and len(ds4_1wf) > 0 and len(ds4_den) > 0 and ddb4.exists()
    res["checkpoint_ok"] = checkpoint_ok
    res["pseudopotentials"] = {}
    for el, fname in [("Li", "Li_LDA.upf"), ("Nb", "Nb_LDA.upf"), ("O", "O_LDA.upf")]:
        res["pseudopotentials"][el] = dict(file=fname, sha256=sha256(PSEUDO_DIR / fname))
    if not Path("/work/pseudo").exists():
        ok = False
    ok = ok and checkpoint_ok
    res["preconditions_ok"] = ok
    if not ok:
        res["status"] = "FAILED"
        res["reason"] = "precondition failure (abi hash / missing checkpoint files / paths)"
        json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
        print(json.dumps(res, indent=1, default=str))
        sys.exit(4)

    for f in list(d.glob("abinit_pead_G1_ds5.abo")) + list(d.glob("run_ds5.log")) + list(d.glob("run_ds5.err")):
        f.unlink()

    t0 = time.time()
    p = subprocess.run(
        f'cd "{d}" && mpirun -np {a.np} abinit abinit_pead_G1_ds5.abi > run_ds5.log 2> run_ds5.err',
        shell=True)
    wall = time.time() - t0
    res.update(abinit_exit_code=p.returncode, wall_s=round(wall, 1))

    abo_path = next(iter(d.glob("abinit_pead_G1_ds5.abo")), None) or (d / "run_ds5.log")
    abo_text = abo_path.read_text(errors="ignore") if abo_path.exists() else ""
    res["converged"] = "Calculation completed" in abo_text or "have converged" in abo_text.lower()

    why = []
    if p.returncode != 0:
        why.append("abinit exit code != 0")
    if not res["converged"]:
        why.append("no completion marker found in output")

    ddb5 = d / "abinit_pead_G1o_DS5_DDB"
    res["ddb5_present"] = ddb5.exists()
    if not ddb5.exists():
        why.append("DS5_DDB missing")

    # --- mrgddb: merge DS4_DDB (dielectric) + DS5_DDB (3rd-order) ---
    if not why:
        for f in list(d.glob("mrgddb.*")) + list(d.glob("anaddb.*")) + list(d.glob("merged.ddb")):
            f.unlink()
        (d / "mrgddb.in").write_text(
            "merged.ddb\nC-VAL4 PEAD electronic-only: dielectric (DS4) + 3rd-order (DS5)\n2\n"
            "abinit_pead_G1o_DS4_DDB\nabinit_pead_G1o_DS5_DDB\n", newline="\n")
        pm = subprocess.run(f'cd "{d}" && mrgddb < mrgddb.in > mrgddb.log 2> mrgddb.err', shell=True)
        res["mrgddb_exit_code"] = pm.returncode
        if pm.returncode != 0 or not (d / "merged.ddb").exists():
            why.append("mrgddb failed or produced no merged.ddb")

    # --- anaddb: dieflag=1 + nlflag=1 only (electronic EO/dielectric) ---
    if not why:
        (d / "anaddb.in").write_text("dieflag  1\nnlflag   1\n", newline="\n")
        for dummy in ["anaddb_thm_dummy", "anaddb_gkk_dummy", "anaddb_ep_dummy", "anaddb_ddk_dummy"]:
            (d / dummy).write_text("", newline="\n")
        (d / "anaddb.files").write_text(
            "anaddb.in\nanaddb.abo\nmerged.ddb\nanaddb_thm_dummy\nanaddb_gkk_dummy\n"
            "anaddb_ep_dummy\nanaddb_ddk_dummy\n", newline="\n")
        pa = subprocess.run(f'cd "{d}" && anaddb < anaddb.files > anaddb.log 2> anaddb.err', shell=True)
        res["anaddb_exit_code"] = pa.returncode
        anaddb_abo = d / "anaddb.abo"
        res["anaddb_abo_present"] = anaddb_abo.exists()
        if pa.returncode != 0 or not anaddb_abo.exists():
            why.append("anaddb failed or produced no anaddb.abo")

    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why)
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    for f in (list(d.glob("abinit_pead_G1_ds5.abi")) + list(d.glob("abinit_pead_G1_ds5.abo")) +
              list(d.glob("run_ds5.log")) + list(d.glob("run_ds5.err")) +
              list(d.glob("abinit_pead_G1o_DS5_DDB")) +
              list(d.glob("mrgddb.in")) + list(d.glob("mrgddb.log")) + list(d.glob("mrgddb.err")) +
              list(d.glob("merged.ddb")) + list(d.glob("anaddb.in")) + list(d.glob("anaddb.files")) +
              list(d.glob("anaddb.abo")) + list(d.glob("anaddb.log")) + list(d.glob("anaddb.err"))):
        shutil.copy(f, out / f.name)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "job"}, indent=1, default=str))
    if res["status"] == "DONE":
        print("\n--- anaddb.abo ---")
        print((d / "anaddb.abo").read_text(errors="ignore"))
    sys.exit(0 if res["status"] == "DONE" else 3)


if __name__ == "__main__":
    main()
