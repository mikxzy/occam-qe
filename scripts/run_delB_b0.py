"""DEL B / B0: verify the frozen pw.in is byte-identical to the DEL A production input,
then pw.x SCF -> ph.x (epsil+trans+zeu) -> dynmat.x (ASR) in one job (ephemeral runner
needs its own fresh tmp/ outdir, so re-running the identical SCF is unavoidable even
though DEL A already produced the same numbers once).

    python scripts/run_delB_b0.py --np 4 [--out artifacts/B0]
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
from qe_ph_out import parse_phout

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue" / "delB_jobs.json"
PSEUDO_DIR = ROOT / "pseudo"
DEL_A_PWIN = ROOT / "runs" / "convergence_dfpt" / "dfpt_ecut120_k4" / "pw.in"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()

    job = json.loads(QUEUE.read_text())["B0"]
    d = ROOT / job["dir"]
    out = Path(a.out) if a.out else d / "artifact"
    out.mkdir(parents=True, exist_ok=True)

    res = dict(job=job, started=time.strftime("%Y-%m-%dT%H:%M:%S"), np=a.np)

    # ---- preconditions
    ok = sha256(d / "pw.in") == job["pwin_sha256"] == sha256(DEL_A_PWIN)
    ok = ok and sha256(d / "ph.in") == job["phin_sha256"]
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
        ok = False
        res["note"] = "/work/pseudo missing"
    res["preconditions_ok"] = ok
    if not ok:
        res["status"] = "FAILED"
        res["reason"] = "precondition failure (hash/paths) -- B0 must be byte-identical to DEL A"
        json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
        print(json.dumps(res, indent=1, default=str))
        sys.exit(4)

    for f in ["pw.out", "pw.err", "ph.out", "ph.err", "dynmat.out", "dynmat.err"]:
        if (d / f).exists():
            (d / f).unlink()

    t0 = time.time()
    p1 = subprocess.run(f'cd "{d}" && mpirun --oversubscribe --bind-to none -np {a.np} pw.x -in pw.in > pw.out 2> pw.err', shell=True)
    pw_wall = time.time() - t0

    t1 = time.time()
    p2 = subprocess.run(f'cd "{d}" && mpirun --oversubscribe --bind-to none -np {a.np} ph.x -in ph.in > ph.out 2> ph.err', shell=True)
    ph_wall = time.time() - t1

    # dynmat.x: ASR correction on the Gamma dynamical matrix ph.x just wrote
    fildyn_candidates = ["mat.dyn", "mat.dyn1"]
    fildyn = next((f for f in fildyn_candidates if (d / f).exists()), None)
    res["fildyn_used"] = fildyn
    dynmat_in = f"&input\n  fildyn='{fildyn}'\n  asr='crystal'\n  fileout='mat.dyn.asr'\n/\n" if fildyn else None
    p3_rc = None
    t2 = time.time()
    if dynmat_in:
        (d / "dynmat.in").write_text(dynmat_in, newline="\n")
        p3 = subprocess.run(f'cd "{d}" && dynmat.x -in dynmat.in > dynmat.out 2> dynmat.err', shell=True)
        p3_rc = p3.returncode
    dynmat_wall = time.time() - t2
    subprocess.run("rm -rf /tmp/qe_*", shell=True)

    res.update(pw_exit_code=p1.returncode, ph_exit_code=p2.returncode, dynmat_exit_code=p3_rc,
               pw_wall_s=round(pw_wall, 1), ph_wall_s=round(ph_wall, 1), dynmat_wall_s=round(dynmat_wall, 1))

    why = []
    rpw = parse_pwout(d / "pw.out") if (d / "pw.out").exists() else None
    if rpw is None or not (rpw["job_done"] and rpw["converged"]):
        why.append("SCF did not converge/finish")
    res["scf_E_final_Ry"] = rpw["E_final_Ry"] if rpw else None
    res["scf_stress_final_kbar"] = rpw["stress_final"] if rpw else None
    res["scf_pressure_kbar"] = rpw["pressure_kbar"] if rpw else None
    # sanity check against the already-committed DEL A number
    del_a_E = -476.32035238
    if rpw and rpw["E_final_Ry"] is not None and abs(rpw["E_final_Ry"] - del_a_E) > 1e-5:
        why.append(f"SCF energy {rpw['E_final_Ry']} Ry does not reproduce DEL A's committed {del_a_E} Ry")

    rph = parse_phout(d / "ph.out") if (d / "ph.out").exists() else None
    if rph is None or not rph["job_done"] or rph["epsilon_cartesian"] is None or not rph["freqs_cm1"]:
        why.append("ph.x dielectric/phonon output incomplete")
    else:
        res.update(epsilon_cartesian=rph["epsilon_cartesian"], freqs_cm1_raw=rph["freqs_cm1"], n_modes=rph["n_modes"])

    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why and p1.returncode == 0 and p2.returncode == 0 else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why)
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    for f in ["pw.in", "ph.in", "pw.out", "ph.out", "dynmat.in", "dynmat.out",
              "mat.dyn", "mat.dyn1", "mat.dyn.asr"]:
        if (d / f).exists():
            shutil.copy(d / f, out / f)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "job"}, indent=1, default=str))
    sys.exit(0 if res["status"] == "DONE" else 3)


if __name__ == "__main__":
    main()
