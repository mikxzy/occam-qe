"""DEL C / C3: run ONE frozen LDA cutoff-check SCF job (hash-verified pw.in +
Li_LDA.upf/Nb_LDA.upf/O_LDA.upf against the manifest).

    python scripts/run_delC_c3_cutoff.py --job C3_cutoff_ecut120_k4 --np 4 [--out artifacts/C3_cutoff_ecut120_k4]
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

from qe_out import parse_pwout

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue" / "delC_jobs.json"
PSEUDO_DIR = ROOT / "pseudo"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()

    jobs = json.loads(QUEUE.read_text())
    job = jobs[a.job]
    d = ROOT / job["dir"]
    out = Path(a.out) if a.out else d / "artifact"
    out.mkdir(parents=True, exist_ok=True)

    res = dict(job=dict(id=a.job, **job), started=time.strftime("%Y-%m-%dT%H:%M:%S"), np=a.np)

    ok = sha256(d / "pw.in") == job["pwin_sha256"]
    manifest = (ROOT / "00_environment" / "pseudopotentials_manifest.txt").read_text()
    res["pseudopotentials"] = {}
    for el, fname in [("Li", "Li_LDA.upf"), ("Nb", "Nb_LDA.upf"), ("O", "O_LDA.upf")]:
        hp = sha256(PSEUDO_DIR / fname)
        expected_line = next((l for l in manifest.splitlines() if l.strip().startswith(fname)), "")
        expected = expected_line.split()[-1] if expected_line else None
        entry_ok = expected is not None and hp == expected
        res["pseudopotentials"][el] = dict(file=fname, expected=expected, observed=hp, ok=entry_ok)
        ok = ok and entry_ok
    if not Path("/work/pseudo").exists():
        ok = False
    res["preconditions_ok"] = ok
    if not ok:
        res["status"] = "FAILED"
        res["reason"] = "precondition failure (hash/paths)"
        json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
        print(json.dumps(res, indent=1, default=str))
        sys.exit(4)

    for f in ["pw.out", "pw.err"]:
        if (d / f).exists():
            (d / f).unlink()
    cmd = f'cd "{d}" && mpirun --oversubscribe --bind-to none -np {a.np} pw.x -in pw.in > pw.out 2> pw.err'
    t0 = time.time()
    p = subprocess.run(cmd, shell=True)
    wall = time.time() - t0
    subprocess.run("rm -rf /tmp/qe_*", shell=True)
    res.update(exit_code=p.returncode, wall_s=round(wall, 1))

    r = parse_pwout(d / "pw.out") if (d / "pw.out").exists() else None
    why = []
    if r is None:
        why.append("no pw.out")
    else:
        if not r["job_done"]:
            why.append("no JOB DONE")
        if not r["converged"]:
            why.append("SCF not converged")
        res.update(E_final_Ry=r["E_final_Ry"], stress_final_kbar=r["stress_final"], pressure_kbar=r["pressure_kbar"])
    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why and p.returncode == 0 else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why)
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    for f in ["pw.in", "pw.out", "pw.err"]:
        if (d / f).exists():
            shutil.copy(d / f, out / f)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "job"}, indent=1, default=str))
    sys.exit(0 if res["status"] == "DONE" else 3)


if __name__ == "__main__":
    main()
