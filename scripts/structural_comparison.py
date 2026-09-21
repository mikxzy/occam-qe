"""Structural comparison B0 vs B1 vs B2: lattice lengths/angles/volume/density, energy per
formula unit, residual pressure, full stress tensor, max force, and RMS/max atomic
displacement relative to B0 (minimum-image in fractional space, then converted to
Cartesian through B0's cell -- so it measures ionic motion cleanly for B1 (fixed cell) and
is a combined ionic+cell-strain displacement for B2, per instruction's own separate
Delta-V/V0 and lattice-parameter-change metrics that disentangle the two for B2).

    python scripts/structural_comparison.py
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

import numpy as np

from qe_in_parser import extract_blocks
from qe_relax_out import cellpar

ROOT = Path(__file__).resolve().parents[1]
DEL_A_PWIN = ROOT / "runs" / "convergence_dfpt" / "dfpt_ecut120_k4" / "pw.in"
DELB = ROOT / "runs" / "delB"
OUT = ROOT / "results" / "delB_structural.csv"

N_FORMULA_UNITS = 2
MASSES_AMU = dict(Li=6.94, Nb=92.90637, O=15.9994)
AMU_TO_G = 1.66053906660e-24
A3_TO_CM3 = 1e-24


def parse_pw_positions(pw_in_text: str):
    import re
    m = re.search(r"CELL_PARAMETERS.*?\n((?:.*\n){3})", pw_in_text)
    cell = np.array([[float(v) for v in l.split()] for l in m.group(1).strip().splitlines()])
    m2 = re.search(r"ATOMIC_POSITIONS.*?\n((?:.*\n)+?)(?=K_POINTS)", pw_in_text)
    rows = [l.split() for l in m2.group(1).strip().splitlines()]
    symbols = [r[0] for r in rows]
    frac = np.array([[float(v) for v in r[1:4]] for r in rows])
    return cell, symbols, frac


def load_b0():
    r = json.loads((DELB / "B0" / "artifact" / "result.json").read_text())
    cell, symbols, frac = parse_pw_positions(DEL_A_PWIN.read_text())
    a, b, c, alpha, beta, gamma = cellpar(cell)
    volume = float(abs(np.linalg.det(cell)))
    return dict(structure="B0", cell=cell, symbols=symbols, frac=frac,
                a=a, b=b, c=c, alpha=alpha, beta=beta, gamma=gamma, volume_A3=volume,
                E_final_Ry=r["scf_E_final_Ry"], stress_kbar=r["scf_stress_final_kbar"],
                pressure_kbar=r["scf_pressure_kbar"], max_force_eV_A=None, n_relax_steps=0)


def load_branch(name: str):
    r = json.loads((DELB / name / "artifact" / "result.json").read_text())
    fs = r["final_structure"]
    cell = np.array(fs["cell_A"])
    frac = np.array(fs["frac"])
    max_f = max(r["relax_trajectory"]["max_forces_eV_A"]) if r["relax_trajectory"]["max_forces_eV_A"] else None
    final_max_f = r["relax_trajectory"]["max_forces_eV_A"][-1] if r["relax_trajectory"]["max_forces_eV_A"] else None
    return dict(structure=name, cell=cell, symbols=fs["symbols"], frac=frac,
                a=fs["a"], b=fs["b"], c=fs["c"], alpha=fs["alpha"], beta=fs["beta"], gamma=fs["gamma"],
                volume_A3=fs["volume_A3"],
                E_final_Ry=r["clean_scf_E_final_Ry"], stress_kbar=r["clean_scf_stress_final_kbar"],
                pressure_kbar=r["clean_scf_pressure_kbar"],
                max_force_eV_A=final_max_f, n_relax_steps=r["relax_trajectory"]["n_steps"])


def displacement_vs_b0(b0, s):
    dfrac = s["frac"] - b0["frac"]
    dfrac -= np.round(dfrac)  # minimum image
    dcart = dfrac @ b0["cell"]  # through B0's cell
    dist = np.linalg.norm(dcart, axis=1)
    return float(np.sqrt(np.mean(dist ** 2))), float(np.max(dist))


def density_g_cm3(symbols, volume_A3):
    mass_amu = sum(MASSES_AMU[s] for s in symbols)
    return (mass_amu * AMU_TO_G) / (volume_A3 * A3_TO_CM3)


def main():
    b0 = load_b0()
    structures = [b0]
    for name in ["B1", "B2"]:
        d = DELB / name / "artifact" / "result.json"
        if d.exists():
            structures.append(load_branch(name))
        else:
            print(f"skip {name}: no result.json yet at {d}")

    rows = []
    for s in structures:
        rms, mx = displacement_vs_b0(b0, s) if s["structure"] != "B0" else (0.0, 0.0)
        rows.append(dict(
            structure=s["structure"],
            a=round(s["a"], 6), b=round(s["b"], 6), c=round(s["c"], 6),
            alpha=round(s["alpha"], 6), beta=round(s["beta"], 6), gamma=round(s["gamma"], 6),
            volume_A3=round(s["volume_A3"], 6),
            density_g_cm3=round(density_g_cm3(s["symbols"], s["volume_A3"]), 6),
            E_per_fu_Ry=round(s["E_final_Ry"] / N_FORMULA_UNITS, 8) if s["E_final_Ry"] is not None else None,
            pressure_kbar=s["pressure_kbar"],
            stress_xx=s["stress_kbar"][0][0] if s["stress_kbar"] else None,
            stress_yy=s["stress_kbar"][1][1] if s["stress_kbar"] else None,
            stress_zz=s["stress_kbar"][2][2] if s["stress_kbar"] else None,
            stress_xy=s["stress_kbar"][0][1] if s["stress_kbar"] else None,
            stress_xz=s["stress_kbar"][0][2] if s["stress_kbar"] else None,
            stress_yz=s["stress_kbar"][1][2] if s["stress_kbar"] else None,
            max_force_eV_A=s["max_force_eV_A"],
            n_relax_steps=s["n_relax_steps"],
            rms_displacement_vs_B0_A=round(rms, 6),
            max_displacement_vs_B0_A=round(mx, 6),
            delta_V_over_V0_pct=round(100 * (s["volume_A3"] - b0["volume_A3"]) / b0["volume_A3"], 4),
            delta_a_pct=round(100 * (s["a"] - b0["a"]) / b0["a"], 4),
            delta_c_pct=round(100 * (s["c"] - b0["c"]) / b0["c"], 4),
            delta_alpha_pct=round(100 * (s["alpha"] - b0["alpha"]) / b0["alpha"], 4),
        ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} structures)")
    for r in rows:
        print(f"  {r['structure']}: a={r['a']:.4f} c={r['c']:.4f} alpha={r['alpha']:.4f} "
              f"V={r['volume_A3']:.4f} dV/V0={r['delta_V_over_V0_pct']}% "
              f"E/fu={r['E_per_fu_Ry']} P={r['pressure_kbar']} "
              f"RMSd={r['rms_displacement_vs_B0_A']} maxd={r['max_displacement_vs_B0_A']}")


if __name__ == "__main__":
    main()
