"""Run ONE frozen, hash-verified pw.x job from queue/jobs.json (adapted from the pattern
used for Level-C Test 4B: verify every hash before running, record the runner/software
environment, run under `/usr/bin/time -v`, then validate the output before declaring
success). Never edits pw.in.

    python scripts/run_qe_job.py --job scf_ecut60_k4 --np 4 [--out artifacts/scf_ecut60_k4]

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

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue" / "jobs.json"
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
        nproc=run("nproc"),
        cpu=run("lscpu | grep -E 'Model name|^CPU\\(s\\)|Thread|Core' | tr -s ' '"),
        meminfo=run("grep -E 'MemTotal|MemAvailable' /proc/meminfo"),
        pw_x=run("which pw.x"), pw_version=run("pw.x -h 2>&1 | head -2 | tail -1 || true"),
        mpirun=run("mpirun --version | head -1"),
        conda_packages=run("mamba list 2>/dev/null | grep -iE '^ *(qe|openmpi|libopenblas|libblas|liblapack|fftw|scalapack|elpa|python|numpy) '"),
        github=dict(runner=os.environ.get("RUNNER_NAME"), os=os.environ.get("RUNNER_OS"),
                    arch=os.environ.get("RUNNER_ARCH"), image=os.environ.get("ImageOS"),
                    run_id=os.environ.get("GITHUB_RUN_ID"), job=os.environ.get("GITHUB_JOB"),
                    sha=os.environ.get("GITHUB_SHA"), workflow=os.environ.get("GITHUB_WORKFLOW")),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    ap.add_argument("--nk", type=int, default=1)
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
               np=a.np, nk=a.nk, environment=env_record())

    # ---- preconditions: frozen input + pseudopotential hashes
    h = sha256(d / "pw.in")
    res["pwin_sha256_observed"] = h
    ok = h == job["pwin_sha256"]
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

    # ---- run pw.x
    for f in ["pw.out", "pw.err", "time.txt"]:
        if (d / f).exists():
            (d / f).unlink()
    gtime = next((t for t in [shutil.which("time"), "/usr/bin/time", "/opt/conda/bin/time"] if t and Path(t).exists()), None)
    timer = f"{gtime} -v -o time.txt " if gtime else ""
    res["gnu_time"] = gtime
    cmd = f'cd "{d}" && {timer}mpirun --oversubscribe --bind-to none -np {a.np} pw.x -nk {a.nk} -in pw.in > pw.out 2> pw.err'
    t0 = time.time()
    p = subprocess.run(cmd, shell=True)
    wall = time.time() - t0
    subprocess.run("rm -rf /tmp/qe_*", shell=True)
    peak_rss_kb = None
    if (d / "time.txt").exists():
        for l in open(d / "time.txt"):
            if "Maximum resident set size" in l:
                peak_rss_kb = int(l.split()[-1])
    res.update(exit_code=p.returncode, wall_s=round(wall, 1),
               peak_rss_per_rank_MB=round(peak_rss_kb / 1024, 1) if peak_rss_kb else None)

    # ---- validate
    r = parse_pwout(d / "pw.out") if (d / "pw.out").exists() else None
    why = []
    if r is None:
        why.append("no pw.out")
    else:
        if not r["job_done"]:
            why.append("no JOB DONE")
        if not r["converged"]:
            why.append("SCF not converged")
        if r["stress_final"] is None:
            why.append("stress missing")
        if r["E_final_Ry"] is None:
            why.append("total energy missing")
        res.update(E_final_Ry=r["E_final_Ry"], n_scf_iterations=r["n_scf_iterations"],
                    stress_final_kbar=r["stress_final"], pressure_kbar=r["pressure_kbar"])
    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why and p.returncode == 0 else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why) or f"exit {p.returncode}"
    res["output_hashes"] = {f: sha256(d / f) for f in ["pw.in", "pw.out", "pw.err"] if (d / f).exists()}
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    for f in ["pw.in", "pw.out", "pw.err", "time.txt"]:
        if (d / f).exists():
            shutil.copy(d / f, out / f)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k not in ("environment", "job")}, indent=1, default=str))
    sys.exit(0 if res["status"] == "DONE" else (3 if p.returncode != 0 else 2))


if __name__ == "__main__":
    main()
