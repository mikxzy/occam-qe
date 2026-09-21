"""Run ONE frozen, hash-verified scf+DFPT(Gamma) job from queue/dfpt_jobs.json: pw.x SCF
first (writes the wavefunctions ph.x needs into the same outdir/prefix), then ph.x
(epsil+trans) in the same working directory. Never edits pw.in/ph.in.

    python scripts/run_dfpt_job.py --job dfpt_ecut100_k4 --np 4 [--out artifacts/dfpt_ecut100_k4]

Exit code: 0 = DONE (valid), 2 = QE ran but output invalid, 3 = QE non-zero exit,
4 = precondition (hash) failure.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from qe_out import parse_pwout
from qe_ph_out import parse_phout

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue" / "dfpt_jobs.json"
PSEUDO_DIR = ROOT / "pseudo"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def env_record() -> dict:
    def run(cmd):
        try:
            return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120).stdout.strip()
        except Exception as e:
            return f"ERR {e}"
    import os
    return dict(
        hostname=platform.node(), platform=platform.platform(),
        nproc=run("nproc"), meminfo=run("grep -E 'MemTotal|MemAvailable' /proc/meminfo"),
        pw_version=run("pw.x -h 2>&1 | head -2 | tail -1 || true"),
        ph_version=run("ph.x -h 2>&1 | head -2 | tail -1 || true"),
        github=dict(runner=os.environ.get("RUNNER_NAME"), run_id=os.environ.get("GITHUB_RUN_ID"),
                    job=os.environ.get("GITHUB_JOB"), sha=os.environ.get("GITHUB_SHA"),
                    workflow=os.environ.get("GITHUB_WORKFLOW")),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()

    jobs = json.loads(QUEUE.read_text())
    if a.job not in jobs:
        print(f"unknown job {a.job!r}; known jobs: {sorted(jobs)}", file=sys.stderr)
        sys.exit(4)
    job = jobs[a.job]
    d = ROOT / job["dir"]
    out = Path(a.out) if a.out else d / "artifact"
    out.mkdir(parents=True, exist_ok=True)

    res = dict(job=dict(id=a.job, **job), started=time.strftime("%Y-%m-%dT%H:%M:%S"),
               np=a.np, environment=env_record())

    # ---- preconditions: frozen pw.in + ph.in + pseudopotential hashes
    h_pw = sha256(d / "pw.in")
    h_ph = sha256(d / "ph.in")
    res["pwin_sha256_observed"] = h_pw
    res["phin_sha256_observed"] = h_ph
    ok = h_pw == job["pwin_sha256"] and h_ph == job["phin_sha256"]
    manifest = (ROOT / "00_environment" / "pseudopotentials_manifest.txt").read_text()
    res["pseudopotentials"] = {}
    for el, fname in [("Li", "Li.upf"), ("Nb", "Nb.upf"), ("O", "O.upf")]:
        hp = sha256(PSEUDO_DIR / fname)
        expected_line = next((l for l in manifest.splitlines() if l.strip().startswith(fname)), "")
        expected = expected_line.split()[-1] if expected_line else None
        entry_ok = expected is not None and hp == expected
        res["pseudopotentials"][el] = dict(file=fname, expected=expected, observed=hp, ok=entry_ok)
        ok = ok and entry_ok
    if not Path("/work/pseudo").exists():
        res["note"] = "/work/pseudo missing (pw.in uses pseudo_dir=/work/pseudo)"
        ok = False
    res["preconditions_ok"] = ok
    if not ok:
        res["status"] = "FAILED"
        res["reason"] = "precondition failure (hash/paths)"
        json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
        print(json.dumps(res, indent=1, default=str))
        sys.exit(4)

    # ---- run pw.x (SCF) then ph.x (Gamma DFPT), same working directory/prefix/outdir
    for f in ["pw.out", "pw.err", "ph.out", "ph.err"]:
        if (d / f).exists():
            (d / f).unlink()
    t0 = time.time()
    cmd_pw = f'cd "{d}" && mpirun --oversubscribe --bind-to none -np {a.np} pw.x -in pw.in > pw.out 2> pw.err'
    p1 = subprocess.run(cmd_pw, shell=True)
    pw_wall = time.time() - t0

    t1 = time.time()
    cmd_ph = f'cd "{d}" && mpirun --oversubscribe --bind-to none -np {a.np} ph.x -in ph.in > ph.out 2> ph.err'
    p2 = subprocess.run(cmd_ph, shell=True)
    ph_wall = time.time() - t1
    subprocess.run("rm -rf /tmp/qe_*", shell=True)

    res.update(pw_exit_code=p1.returncode, ph_exit_code=p2.returncode,
               pw_wall_s=round(pw_wall, 1), ph_wall_s=round(ph_wall, 1))

    # ---- validate
    why = []
    rpw = parse_pwout(d / "pw.out") if (d / "pw.out").exists() else None
    if rpw is None:
        why.append("no pw.out")
    elif not (rpw["job_done"] and rpw["converged"]):
        why.append("SCF stage did not converge / finish")
    res["scf_E_final_Ry"] = rpw["E_final_Ry"] if rpw else None

    rph = parse_phout(d / "ph.out") if (d / "ph.out").exists() else None
    if rph is None:
        why.append("no ph.out")
    else:
        if not rph["job_done"]:
            why.append("ph.x: no JOB DONE")
        if rph["epsilon_cartesian"] is None:
            why.append("dielectric tensor not found in ph.out")
        if not rph["freqs_cm1"]:
            why.append("no phonon frequencies found in ph.out")
        res.update(epsilon_cartesian=rph["epsilon_cartesian"], freqs_cm1=rph["freqs_cm1"],
                    n_modes=rph["n_modes"], n_imaginary=rph["n_imaginary"])

    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why and p1.returncode == 0 and p2.returncode == 0 else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why) or f"pw exit {p1.returncode}, ph exit {p2.returncode}"
    res["output_hashes"] = {f: sha256(d / f) for f in ["pw.in", "ph.in", "pw.out", "ph.out"] if (d / f).exists()}
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    for f in ["pw.in", "ph.in", "pw.out", "pw.err", "ph.out", "ph.err"]:
        if (d / f).exists():
            shutil.copy(d / f, out / f)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k not in ("environment", "job")}, indent=1, default=str))
    sys.exit(0 if res["status"] == "DONE" else (3 if (p1.returncode or p2.returncode) else 2))


if __name__ == "__main__":
    main()
