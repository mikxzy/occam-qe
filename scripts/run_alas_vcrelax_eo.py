"""DEL C-VAL2, TEST D: AlAs vc-relax -> clean production SCF -> Gamma DFPT
(epsil+trans+zeu+elop) -> dynmat.x ASR. Independent reference-material control case.

    python scripts/run_alas_vcrelax_eo.py --np 4 [--out artifacts/CVAL2_AlAs_vcrelax]
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
from qe_relax_out import parse_relax_out, cellpar

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue" / "delC_jobs.json"
PSEUDO_DIR = ROOT / "pseudo"

SPECIES_BLOCK = "ATOMIC_SPECIES\nAl 26.9815385 Al_LDA.upf\nAs 74.9216 As_LDA.upf\n"
CLEAN_SCF_TEMPLATE = """&CONTROL
   calculation = 'scf'
   prefix      = 'alas_lda'
   outdir      = './tmp/'
   pseudo_dir  = '/work/pseudo'
   verbosity   = 'high'
   tstress     = .true.
   tprnfor     = .true.
/
&SYSTEM
   ibrav       = 0
   nat         = {nat}
   ntyp        = 2
   ecutwfc     = 60.0
   ecutrho     = 240.0
   occupations = 'fixed'
/
&ELECTRONS
   conv_thr    = 1.0d-10
   mixing_beta = 0.7d0
   electron_maxstep = 200
/
{cell_block}
{species_block}
{positions_block}
K_POINTS automatic
8 8 8 0 0 0
"""
PH_EO_TEXT = "Gamma-point DFPT: dielectric + Born charges + phonons + electro-optic tensor (AlAs LDA control)\n&inputph\n   prefix   = 'alas_lda'\n   outdir   = './tmp/'\n   fildyn   = 'mat.dyn'\n   epsil    = .true.\n   trans    = .true.\n   zeu      = .true.\n   elop     = .true.\n   tr2_ph   = 1.0d-14\n/\n0.0 0.0 0.0\n"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fmt_cell(cell):
    return "CELL_PARAMETERS angstrom\n" + "\n".join(f"{v[0]: .10f} {v[1]: .10f} {v[2]: .10f}" for v in cell)


def fmt_positions(symbols, frac):
    return "ATOMIC_POSITIONS crystal\n" + "\n".join(
        f"{s} {p[0]: .10f} {p[1]: .10f} {p[2]: .10f}" for s, p in zip(symbols, frac))


def parse_elop(ph_out_text: str) -> dict:
    out = dict(total=None, electronic=None, xc_derivative=None)
    m = re.search(r"Electro-optic tensor in cartesian axis:\s*\n\s*\n((?:.*\n){12})", ph_out_text)
    if m:
        nums = [float(x) for x in re.findall(r"-?\d+\.\d+(?:e[+-]?\d+)?", m.group(1))]
        if len(nums) >= 27:
            out["total"] = [nums[i:i + 3] for i in range(0, 27, 3)]
    for label, key in [(r"#\s*1", "electronic"), (r"#\s*2", "xc_derivative")]:
        m2 = re.search(rf"Electro-optic tensor: contribution {label}\s*\n\s*\n((?:.*\n){{12}})", ph_out_text)
        if m2:
            nums = [float(x) for x in re.findall(r"-?\d+\.\d+(?:e[+-]?\d+)?", m2.group(1))]
            if len(nums) >= 27:
                out[key] = [nums[i:i + 3] for i in range(0, 27, 3)]
    return out


def run(cmd) -> int:
    return subprocess.run(cmd, shell=True).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()

    job = json.loads(QUEUE.read_text())["CVAL2_AlAs_vcrelax"]
    d = ROOT / job["dir"]
    out = Path(a.out) if a.out else d / "artifact"
    out.mkdir(parents=True, exist_ok=True)

    res = dict(job=job, started=time.strftime("%Y-%m-%dT%H:%M:%S"), np=a.np)
    ok = sha256(d / "vcrelax.in") == job["vcrelax_in_sha256"]
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
    t0 = time.time()
    rc1 = run(f'cd "{d}" && mpirun --oversubscribe --bind-to none -np {a.np} pw.x -in vcrelax.in > vcrelax.out 2> vcrelax.err')
    relax_wall = time.time() - t0
    rr = parse_relax_out(d / "vcrelax.out") if (d / "vcrelax.out").exists() else None
    res["relax_wall_s"] = round(relax_wall, 1)
    res["relax_exit_code"] = rc1
    res["relax_trajectory"] = dict(
        energies_Ry=rr["energies_Ry"], max_forces_eV_A=rr["max_forces_eV_A"],
        pressures_kbar=rr["pressures_kbar"], volumes_A3=rr["volumes_A3"], n_steps=rr["n_steps"],
    ) if rr else None
    if rr is None or not (rr["job_done"] and rr["bfgs_converged"]) or rr["final_frac"] is None:
        why.append("vc-relax did not converge / no final coordinates")
        res["integrity"] = dict(ok=False, issues=why)
        res["status"] = "FAILED"
        res["reason"] = "; ".join(why)
        json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
        for f in ["vcrelax.in", "vcrelax.out", "vcrelax.err"]:
            if (d / f).exists():
                shutil.copy(d / f, out / f)
        print(json.dumps({k: v for k, v in res.items() if k != "job"}, indent=1, default=str))
        sys.exit(2)

    final_cell = rr["final_cell_A"]
    final_symbols, final_frac = rr["final_symbols"], rr["final_frac"]
    import numpy as _np
    a_len, b_len, c_len, alpha, beta, gamma = cellpar(final_cell)
    final_volume = rr["final_volume_A3"] if rr["final_volume_A3"] is not None else float(abs(_np.linalg.det(final_cell)))
    res["final_structure"] = dict(cell_A=final_cell.tolist(), a=a_len, b=b_len, c=c_len,
                                   alpha=alpha, beta=beta, gamma=gamma, volume_A3=final_volume,
                                   symbols=final_symbols, frac=final_frac.tolist())

    scf_dir = d / "clean_scf"
    scf_dir.mkdir(exist_ok=True)
    scf_text = CLEAN_SCF_TEMPLATE.format(nat=len(final_symbols), cell_block=fmt_cell(final_cell),
                                          species_block=SPECIES_BLOCK.rstrip("\n"),
                                          positions_block=fmt_positions(final_symbols, final_frac))
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
    res["clean_scf_pressure_kbar"] = rpw["pressure_kbar"] if rpw else None

    (scf_dir / "ph.in").write_text(PH_EO_TEXT, newline="\n")
    res["ph_in_sha256"] = sha256(scf_dir / "ph.in")
    t2 = time.time()
    rc3 = run(f'cd "{scf_dir}" && mpirun --oversubscribe --bind-to none -np {a.np} ph.x -in ph.in > ph.out 2> ph.err')
    ph_wall = time.time() - t2
    res["ph_wall_s"] = round(ph_wall, 1)
    res["ph_exit_code"] = rc3
    ph_text = (scf_dir / "ph.out").read_text(errors="ignore") if (scf_dir / "ph.out").exists() else ""
    rph = parse_phout(scf_dir / "ph.out") if (scf_dir / "ph.out").exists() else None
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
    qe_errors = re.findall(r"%+\s*\n\s*Error in routine.*?\n.*?\n\s*%+", ph_text, flags=re.S)
    res["qe_error_blocks"] = qe_errors

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

    for f in ["vcrelax.in", "vcrelax.out"]:
        if (d / f).exists():
            shutil.copy(d / f, out / f)
    scf_out_dir = out / "clean_scf"
    scf_out_dir.mkdir(exist_ok=True)
    for f in ["pw.in", "pw.out", "ph.in", "ph.out", "dynmat.in", "dynmat.out",
              "mat.dyn", "mat.dyn1", "dynmat.freq.out", "dynmat.eig.out"]:
        if (scf_dir / f).exists():
            shutil.copy(scf_dir / f, scf_out_dir / f)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k not in ("job", "elop_raw")}, indent=1, default=str))
    sys.exit(0 if res["status"] == "DONE" else 3)


if __name__ == "__main__":
    main()
