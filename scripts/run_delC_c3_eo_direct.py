"""DEL C / C3: run the "LDA@PBEsol-geometry" EO job (C3_EO_at_PBEsol_geom) -- LDA
pseudopotentials + zeu + elop directly on B2's PBEsol-relaxed geometry, UNRELAXED under
LDA. Methodological comparison only, per instruction -- not the internally-consistent
LDA reference (that's C3_vcrelax -> clean_scf -> DFPT, run separately).

    python scripts/run_delC_c3_eo_direct.py --np 4 [--out artifacts/C3_EO_at_PBEsol_geom]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from qe_out import parse_pwout
from qe_ph_out import parse_phout

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue" / "delC_jobs.json"
PSEUDO_DIR = ROOT / "pseudo"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_elop(ph_out_text: str) -> dict:
    out = dict(total=None, electronic=None, xc_derivative=None)
    m = re.search(r"Electro-optic tensor in cartesian axis:\s*\n\s*\n((?:.*\n){12})", ph_out_text)
    if m:
        nums = [float(x) for x in re.findall(r"-?\d+\.\d+", m.group(1))]
        if len(nums) >= 27:
            out["total"] = [nums[i:i + 3] for i in range(0, 27, 3)]
    for label, key in [("# 1", "electronic"), ("# 2", "xc_derivative")]:
        m2 = re.search(rf"Electro-optic tensor: contribution {re.escape(label)}\s*\n\s*\n((?:.*\n){{12}})", ph_out_text)
        if m2:
            nums = [float(x) for x in re.findall(r"-?\d+\.\d+", m2.group(1))]
            if len(nums) >= 27:
                out[key] = [nums[i:i + 3] for i in range(0, 27, 3)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", default="C3_EO_at_PBEsol_geom",
                     choices=["C3_EO_at_PBEsol_geom", "C3_EO_at_B0_geom", "C13_k6",
                              "CVAL2_testA_isolated_elop"])
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()

    job = json.loads(QUEUE.read_text())[a.job]
    d = ROOT / job["dir"]
    out = Path(a.out) if a.out else d / "artifact"
    out.mkdir(parents=True, exist_ok=True)

    res = dict(job=job, started=time.strftime("%Y-%m-%dT%H:%M:%S"), np=a.np)

    ok = sha256(d / "pw.in") == job["pwin_sha256"] and sha256(d / "ph.in") == job["phin_sha256"]
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

    for f in ["pw.out", "pw.err", "ph.out", "ph.err", "dynmat.out", "dynmat.err"]:
        if (d / f).exists():
            (d / f).unlink()

    t0 = time.time()
    p1 = subprocess.run(f'cd "{d}" && mpirun --oversubscribe --bind-to none -np {a.np} pw.x -in pw.in > pw.out 2> pw.err', shell=True)
    pw_wall = time.time() - t0
    t1 = time.time()
    p2 = subprocess.run(f'cd "{d}" && mpirun --oversubscribe --bind-to none -np {a.np} ph.x -in ph.in > ph.out 2> ph.err', shell=True)
    ph_wall = time.time() - t1

    fildyn = next((f for f in ["mat.dyn", "mat.dyn1"] if (d / f).exists()), None)
    p3_rc = None
    t2 = time.time()
    if fildyn:
        (d / "dynmat.in").write_text(f"&input\n  fildyn='{fildyn}'\n  asr='crystal'\n  filout='dynmat.freq.out'\n  fileig='dynmat.eig.out'\n/\n", newline="\n")
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

    ph_text = (d / "ph.out").read_text(errors="ignore") if (d / "ph.out").exists() else ""
    rph = parse_phout(d / "ph.out") if (d / "ph.out").exists() else None
    if rph is None or not rph["job_done"]:
        why.append("ph.x did not report JOB DONE")
    else:
        res.update(epsilon_cartesian=rph["epsilon_cartesian"], freqs_cm1_raw=rph["freqs_cm1"], n_modes=rph["n_modes"])

    elop_present = "Electro-optic tensor" in ph_text
    res["elop_section_present"] = elop_present
    if not elop_present:
        why.append("ph.out contains no 'Electro-optic tensor' section")
    else:
        res["elop_raw"] = parse_elop(ph_text)
        if res["elop_raw"]["total"] is None:
            why.append("elop section present but tensor not parsed")

    qe_errors = re.findall(r"%+\s*\n\s*Error in routine.*?\n.*?\n\s*%+", ph_text, flags=re.S)
    res["qe_error_blocks"] = qe_errors

    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why and p1.returncode == 0 and p2.returncode == 0 else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why)
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    for f in ["pw.in", "ph.in", "pw.out", "ph.out", "dynmat.in", "dynmat.out",
              "mat.dyn", "mat.dyn1", "dynmat.freq.out", "dynmat.eig.out"]:
        if (d / f).exists():
            shutil.copy(d / f, out / f)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k not in ("job", "elop_raw")}, indent=1, default=str))
    sys.exit(0 if res["status"] == "DONE" else 3)


if __name__ == "__main__":
    main()
