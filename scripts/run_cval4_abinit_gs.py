"""C-VAL4 Step 0/1: run the ABINIT ground-state SCF job and extract the quantities
needed for QE-vs-ABINIT ground-state parity (electron count, eigenvalues near
VBM/CBM, band gap, electronic dielectric tensor if available at this stage).

    python scripts/run_cval4_abinit_gs.py --np 4 [--out artifacts/CVAL4_abinit_gs_G1]
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

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue" / "delC_jobs.json"
PSEUDO_DIR = ROOT / "pseudo"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_abo(text: str) -> dict:
    out = dict(nelect=None, etotal_ha=None, eig_ev=None, converged=None, gap_ev=None)

    m = re.search(r"nelect\s*=\s*([\d.]+)", text)
    if m:
        out["nelect"] = float(m.group(1))

    m = re.search(r"total_energy\s*:\s*etotal\s*=\s*(-?[\d.eEdD+-]+)", text)
    if not m:
        m = re.search(r">>>>>>>>> Etotal=\s*(-?[\d.eEdD+-]+)", text)
    if m:
        out["etotal_ha"] = float(m.group(1).replace("d", "e").replace("D", "E"))

    m = re.search(r"Fermi \(or HOMO\) energy \(hartree\)\s*=\s*(-?[\d.]+)", text)
    if m:
        out["fermi_ha"] = float(m.group(1))

    # last "kpt#" eigenvalue block at Gamma (first k-point line, last iteration)
    eig_blocks = re.findall(r"kpt#\s*1,.*?\n((?:\s*-?\d+\.\d+\s*)+)\n", text)
    if eig_blocks:
        out["eig_ev_gamma_last_ha"] = [float(x) for x in eig_blocks[-1].split()]

    out["converged"] = "Calculation completed" in text or "have converged" in text.lower()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", default="CVAL4_abinit_gs_G1")
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()

    job = json.loads(QUEUE.read_text())[a.job]
    d = ROOT / job["dir"]
    out = Path(a.out) if a.out else d / "artifact"
    out.mkdir(parents=True, exist_ok=True)

    res = dict(job=job, started=time.strftime("%Y-%m-%dT%H:%M:%S"), np=a.np)

    abi_file = d / "abinit_gs_G1.abi"
    ok = sha256(abi_file) == job["abi_sha256"]
    res["pseudopotentials"] = {}
    for el, fname in [("Li", "Li_LDA.upf"), ("Nb", "Nb_LDA.upf"), ("O", "O_LDA.upf")]:
        hp = sha256(PSEUDO_DIR / fname)
        res["pseudopotentials"][el] = dict(file=fname, sha256=hp)
    if not Path("/work/pseudo").exists():
        ok = False
    res["preconditions_ok"] = ok
    if not ok:
        res["status"] = "FAILED"
        res["reason"] = "precondition failure (hash/paths)"
        json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
        print(json.dumps(res, indent=1, default=str))
        sys.exit(4)

    for f in list(d.glob("abinit_gs_G1.abo")) + list(d.glob("abinit_gs_G1o_*")) + list(d.glob("log*")):
        f.unlink()

    t0 = time.time()
    p = subprocess.run(
        f'cd "{d}" && mpirun --oversubscribe --bind-to none -np {a.np} abinit abinit_gs_G1.abi > run.log 2> run.err',
        shell=True)
    wall = time.time() - t0
    res.update(abinit_exit_code=p.returncode, wall_s=round(wall, 1))

    abo_path = next(iter(d.glob("abinit_gs_G1.abo")), None) or (d / "run.log")
    abo_text = abo_path.read_text(errors="ignore") if abo_path.exists() else ""
    parsed = parse_abo(abo_text)
    res.update(parsed)

    why = []
    if p.returncode != 0:
        why.append("abinit exit code != 0")
    if not parsed.get("converged"):
        why.append("no completion marker found in output")
    if parsed.get("nelect") is not None and abs(parsed["nelect"] - 68.0) > 1e-6:
        why.append(f"nelect={parsed['nelect']} != expected 68")

    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why)
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    for f in list(d.glob("abinit_gs_G1.abi")) + list(d.glob("abinit_gs_G1.abo")) + \
             list(d.glob("run.log")) + list(d.glob("run.err")):
        shutil.copy(f, out / f.name)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "job"}, indent=1, default=str))
    sys.exit(0 if res["status"] == "DONE" else 3)


if __name__ == "__main__":
    main()
