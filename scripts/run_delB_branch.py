"""DEL B / B1 or B2: run the frozen relax.in or vcrelax.in, extract the final geometry,
build+run a clean production-settings SCF on it, then ph.x (epsil+trans+zeu) and
dynmat.x (ASR) -- all in one job (the ephemeral runner needs one continuous tmp/ outdir
per QE `prefix`, so each stage must feed the next within the same filesystem session).

Never edits the frozen relax.in/vcrelax.in. The clean-SCF input IS generated from the
relaxation's own numerical result (unavoidable -- it does not exist until relax finishes)
but is archived alongside its sha256 for the audit trail, same discipline as everything
frozen ahead of time.

    python scripts/run_delB_branch.py --branch B1 --np 4 [--out artifacts/B1]
    python scripts/run_delB_branch.py --branch B2 --np 4 [--out artifacts/B2]
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
from qe_relax_out import parse_relax_out, cellpar

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue" / "delB_jobs.json"
PSEUDO_DIR = ROOT / "pseudo"

CONTROL_TAIL = """   pseudo_dir  = '/work/pseudo'
   verbosity   = 'high'
   tstress     = .true.
   tprnfor     = .true.
/
"""
SYSTEM_BLOCK = """&SYSTEM
   ibrav       = 0
   nat         = {nat}
   ntyp        = {ntyp}
   ecutwfc     = 120.0
   ecutrho     = 480.0
   occupations = 'fixed'
/
"""
ELECTRONS_BLOCK = """&ELECTRONS
   conv_thr    = 1.0d-10
   mixing_beta = 0.7d0
   electron_maxstep = 200
/
"""


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fmt_cell(cell):
    return "CELL_PARAMETERS angstrom\n" + "\n".join(f"{v[0]: .10f} {v[1]: .10f} {v[2]: .10f}" for v in cell) + "\n"


def fmt_positions(symbols, frac):
    return "ATOMIC_POSITIONS crystal\n" + "\n".join(
        f"{s} {p[0]: .10f} {p[1]: .10f} {p[2]: .10f}" for s, p in zip(symbols, frac)) + "\n"


SPECIES_BLOCK = "ATOMIC_SPECIES\nLi 6.94000 Li.upf\nNb 92.90637 Nb.upf\nO 15.99900 O.upf\n"
KPOINTS_BLOCK = "K_POINTS automatic\n4 4 4 0 0 0\n"


def build_clean_scf(cell, symbols, frac, nat, ntyp) -> str:
    return (
        "&CONTROL\n   calculation = 'scf'\n   prefix      = 'linbo3'\n   outdir      = './tmp/'\n"
        + CONTROL_TAIL
        + SYSTEM_BLOCK.format(nat=nat, ntyp=ntyp)
        + ELECTRONS_BLOCK
        + fmt_cell(cell) + "\n" + SPECIES_BLOCK + "\n" + fmt_positions(symbols, frac) + "\n" + KPOINTS_BLOCK
    )


def run(cmd) -> int:
    return subprocess.run(cmd, shell=True).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", required=True, choices=["B1", "B2"])
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()

    job = json.loads(QUEUE.read_text())[a.branch]
    d = ROOT / job["dir"]
    out = Path(a.out) if a.out else d / "artifact"
    out.mkdir(parents=True, exist_ok=True)

    relax_file = "relax.in" if a.branch == "B1" else "vcrelax.in"
    expected_hash_key = "relax_in_sha256" if a.branch == "B1" else "vcrelax_in_sha256"

    res = dict(job=job, branch=a.branch, started=time.strftime("%Y-%m-%dT%H:%M:%S"), np=a.np)

    ok = sha256(d / relax_file) == job[expected_hash_key]
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
    res["preconditions_ok"] = ok
    if not ok:
        res["status"] = "FAILED"
        res["reason"] = "precondition failure (hash/paths)"
        json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
        print(json.dumps(res, indent=1, default=str))
        sys.exit(4)

    why = []

    # ---- stage 1: relax or vc-relax
    for f in [relax_file.replace(".in", ".out"), relax_file.replace(".in", ".err")]:
        if (d / f).exists():
            (d / f).unlink()
    t0 = time.time()
    rc1 = run(f'cd "{d}" && mpirun --oversubscribe --bind-to none -np {a.np} pw.x -in {relax_file} '
              f'> {relax_file.replace(".in", ".out")} 2> {relax_file.replace(".in", ".err")}')
    relax_wall = time.time() - t0
    relax_out_path = d / relax_file.replace(".in", ".out")
    rr = parse_relax_out(relax_out_path) if relax_out_path.exists() else None
    res["relax_wall_s"] = round(relax_wall, 1)
    res["relax_exit_code"] = rc1
    res["relax_trajectory"] = dict(
        energies_Ry=rr["energies_Ry"], max_forces_eV_A=rr["max_forces_eV_A"],
        pressures_kbar=rr["pressures_kbar"], volumes_A3=rr["volumes_A3"], n_steps=rr["n_steps"],
    ) if rr else None
    if rr is None or not (rr["job_done"] and rr["bfgs_converged"]) or rr["final_frac"] is None:
        why.append(f"{relax_file}: relaxation did not converge / no final coordinates")
        res["integrity"] = dict(ok=False, issues=why)
        res["status"] = "FAILED"
        res["reason"] = "; ".join(why)
        json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
        for f in [relax_file, relax_file.replace(".in", ".out"), relax_file.replace(".in", ".err")]:
            if (d / f).exists():
                shutil.copy(d / f, out / f)
        print(json.dumps({k: v for k, v in res.items() if k != "job"}, indent=1, default=str))
        sys.exit(2)

    final_cell = rr["final_cell_A"] if rr["final_cell_A"] is not None else _cell_from_input(d / relax_file)
    final_symbols, final_frac = rr["final_symbols"], rr["final_frac"]
    a_len, b_len, c_len, alpha, beta, gamma = cellpar(final_cell)
    res["final_structure"] = dict(
        cell_A=final_cell.tolist(), a=a_len, b=b_len, c=c_len, alpha=alpha, beta=beta, gamma=gamma,
        volume_A3=rr["final_volume_A3"], symbols=final_symbols, frac=final_frac.tolist(),
    )

    # ---- stage 2: clean SCF on the relaxed structure
    scf_dir = d / "clean_scf"
    scf_dir.mkdir(exist_ok=True)
    scf_text = build_clean_scf(final_cell, final_symbols, final_frac, len(final_symbols), 3)
    (scf_dir / "pw.in").write_text(scf_text, newline="\n")
    res["clean_scf_pwin_sha256"] = sha256(scf_dir / "pw.in")
    t1 = time.time()
    rc2 = run(f'cd "{scf_dir}" && mpirun --oversubscribe --bind-to none -np {a.np} pw.x -in pw.in > pw.out 2> pw.err')
    scf_wall = time.time() - t1
    res["clean_scf_wall_s"] = round(scf_wall, 1)
    res["clean_scf_exit_code"] = rc2
    rpw = parse_pwout(scf_dir / "pw.out") if (scf_dir / "pw.out").exists() else None
    if rpw is None or not (rpw["job_done"] and rpw["converged"]):
        why.append("clean SCF did not converge")
    res["clean_scf_E_final_Ry"] = rpw["E_final_Ry"] if rpw else None
    res["clean_scf_stress_final_kbar"] = rpw["stress_final"] if rpw else None
    res["clean_scf_pressure_kbar"] = rpw["pressure_kbar"] if rpw else None

    # ---- stage 3: ph.x (Gamma DFPT, epsil+trans+zeu) on the clean SCF's tmp/
    ph_text = "Gamma-point DFPT: dielectric tensor + Born effective charges + phonon frequencies\n&inputph\n   prefix   = 'linbo3'\n   outdir   = './tmp/'\n   fildyn   = 'mat.dyn'\n   epsil    = .true.\n   trans    = .true.\n   zeu      = .true.\n   tr2_ph   = 1.0d-14\n/\n0.0 0.0 0.0\n"
    (scf_dir / "ph.in").write_text(ph_text, newline="\n")
    res["ph_in_sha256"] = sha256(scf_dir / "ph.in")
    t2 = time.time()
    rc3 = run(f'cd "{scf_dir}" && mpirun --oversubscribe --bind-to none -np {a.np} ph.x -in ph.in > ph.out 2> ph.err')
    ph_wall = time.time() - t2
    res["ph_wall_s"] = round(ph_wall, 1)
    res["ph_exit_code"] = rc3
    rph = parse_phout(scf_dir / "ph.out") if (scf_dir / "ph.out").exists() else None
    if rph is None or not rph["job_done"] or rph["epsilon_cartesian"] is None or not rph["freqs_cm1"]:
        why.append("ph.x dielectric/phonon output incomplete")
    else:
        res.update(epsilon_cartesian=rph["epsilon_cartesian"], freqs_cm1_raw=rph["freqs_cm1"], n_modes=rph["n_modes"])

    # ---- stage 4: dynmat.x (ASR)
    fildyn = next((f for f in ["mat.dyn", "mat.dyn1"] if (scf_dir / f).exists()), None)
    res["fildyn_used"] = fildyn
    rc4 = None
    if fildyn:
        (scf_dir / "dynmat.in").write_text(f"&input\n  fildyn='{fildyn}'\n  asr='crystal'\n  filout='dynmat.freq.out'\n  fileig='dynmat.eig.out'\n/\n", newline="\n")
        rc4 = run(f'cd "{scf_dir}" && dynmat.x -in dynmat.in > dynmat.out 2> dynmat.err')
    res["dynmat_exit_code"] = rc4
    subprocess.run("rm -rf /tmp/qe_*", shell=True)

    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why and rc1 == 0 and rc2 == 0 and rc3 == 0 else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why)
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    for f in [relax_file, relax_file.replace(".in", ".out")]:
        if (d / f).exists():
            shutil.copy(d / f, out / f)
    scf_out_dir = out / "clean_scf"
    scf_out_dir.mkdir(exist_ok=True)
    for f in ["pw.in", "pw.out", "ph.in", "ph.out", "dynmat.in", "dynmat.out",
              "mat.dyn", "mat.dyn1", "dynmat.freq.out", "dynmat.eig.out"]:
        if (scf_dir / f).exists():
            shutil.copy(scf_dir / f, scf_out_dir / f)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "job"}, indent=1, default=str))
    sys.exit(0 if res["status"] == "DONE" else 3)


def _cell_from_input(relax_in_path: Path):
    import re
    import numpy as np
    txt = relax_in_path.read_text()
    m = re.search(r"CELL_PARAMETERS.*?\n((?:.*\n){3})", txt)
    return np.array([[float(v) for v in l.split()] for l in m.group(1).strip().splitlines()])


if __name__ == "__main__":
    main()
