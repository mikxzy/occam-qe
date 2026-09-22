"""DEL C, C4/C5/C7: extract raw elop tensors for all completed EO branches, verify them
against the symmetry-derived form (C5), and convert to the conventional contracted
Pockels tensor r_mu,k in pm/V (C6/C7) using r_ijk = -(dEps_ij/dEk)/(Eps_ii*Eps_jj) with
QE's own documented Ry-a.u.-to-pm/V factor (2.7502), per results/EO_CONVERSION.md.

    python scripts/eo_analysis.py

Writes results/eo_tensor_raw.json, results/eo_tensor_raw.csv, results/eo_tensor_converted.csv,
and prints the symmetry check (appended to results/eo_symmetry_check.md by hand after review).
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

from eo_raw_extract import parse_elop_full
from qe_ph_out import parse_phout

ROOT = Path(__file__).resolve().parents[1]
DELC = ROOT / "runs" / "delC" / "C3_LDA"

RY_TO_PMV = 2.7502  # QE source-documented factor, see results/ELop_IMPLEMENTATION_NOTES.md

VOIGT = [("1", 0, 0), ("2", 1, 1), ("3", 2, 2), ("4", 1, 2), ("5", 0, 2), ("6", 0, 1)]
AXES = "xyz"

# theoretical symmetry-allowed (i,j) pairs per component: only these 4*3=12 of the 18
# (mu,k) slots may be nonzero, per results/eo_symmetry_check.md (derived via
# scripts/derive_3m_symmetry.py)
ALLOWED = {("1", "y"), ("2", "y"), ("6", "x"), ("1", "z"), ("2", "z"), ("5", "x"), ("4", "y"), ("3", "z")}


def elop_at(raw9x3, i, j, k):
    return raw9x3[3 * k + j][i]


def branches():
    out = {}
    b = DELC / "EO_at_PBEsol_geom" / "artifact"
    if (b / "ph.out").exists():
        out["LDA@PBEsol-geometry"] = dict(dir=b, geometry="B2 (PBEsol-relaxed), UNRELAXED under LDA",
                                           note="methodological comparison only")
    b = DELC / "vcrelax" / "artifact" / "clean_scf"
    if (b / "ph.out").exists():
        out["LDA@LDA-relaxed"] = dict(dir=b, geometry="C3_vcrelax final geometry (internally consistent)",
                                       note="primary LDA reference")
    b = DELC / "EO_at_B0_geom" / "artifact"
    if (b / "ph.out").exists():
        out["LDA@B0-geometry"] = dict(dir=b, geometry="B0 (DEL A/B original, unrelaxed), UNRELAXED under LDA",
                                       note="for C12: true B0-vs-B2 comparison, same (LDA) EO method")
    b = ROOT / "runs" / "delC" / "C13_k6" / "artifact"
    if (b / "ph.out").exists():
        out["LDA-relaxed@k6"] = dict(dir=b, geometry="C3_vcrelax final geometry, k=6x6x6 (vs production 4x4x4)",
                                      note="C13: numerical convergence check for H0-C3")
    return out


def main():
    br = branches()
    if not br:
        print("no completed EO branches found yet")
        return

    raw_records = []
    converted_records = []
    for name, info in br.items():
        ph_text = (info["dir"] / "ph.out").read_text(errors="ignore")
        elop = parse_elop_full(ph_text)
        eps_r = parse_phout(info["dir"] / "ph.out")
        eps = eps_r["epsilon_cartesian"]

        for contrib_name, tensor in [("total", elop["total"]), ("electronic", elop["electronic"]),
                                      ("xc_derivative", elop["xc_derivative"])]:
            if tensor is None:
                continue
            for i in range(3):
                for j in range(3):
                    for k in range(3):
                        raw_records.append(dict(
                            branch=name, geometry=info["geometry"], xc="LDA (PZ/PW)",
                            pseudopotentials="Li_LDA.upf/Nb_LDA.upf/O_LDA.upf",
                            contribution=contrib_name,
                            i=AXES[i], j=AXES[j], k=AXES[k],
                            raw_value_Ry_au=elop_at(tensor, i, j, k),
                            qe_definition="d(epsilon_ij)/dE_k, Rydberg a.u., symmetrized cartesian axis",
                        ))

        # contracted, TOTAL tensor only, converted to r_mu,k (pm/V)
        total = elop["total"]
        for mu, i, j in VOIGT:
            for k in range(3):
                raw_val = elop_at(total, i, j, k)
                pmv_raw = raw_val * RY_TO_PMV  # raw dEps/dE in pm/V, not yet r_ijk
                eps_ii, eps_jj = eps[i][i], eps[j][j]
                r_ijk = -pmv_raw / (eps_ii * eps_jj) if (eps_ii and eps_jj) else None
                allowed = (mu, AXES[k]) in ALLOWED
                converted_records.append(dict(
                    branch=name, mu=mu, k=AXES[k], raw_value_Ry_au=raw_val,
                    deps_dE_pmV=round(pmv_raw, 4),
                    eps_ii=eps_ii, eps_jj=eps_jj,
                    r_pmV=round(r_ijk, 4) if r_ijk is not None else None,
                    symmetry_allowed=allowed,
                    flag="" if (allowed or abs(raw_val) < 1.0) else "NONZERO IN FORBIDDEN SLOT",
                ))

    OUT_JSON = ROOT / "results" / "eo_tensor_raw.json"
    OUT_JSON.write_text(json.dumps(raw_records, indent=1))
    print(f"wrote {OUT_JSON.relative_to(ROOT)} ({len(raw_records)} entries)")

    OUT_CSV = ROOT / "results" / "eo_tensor_raw.csv"
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(raw_records[0].keys()))
        w.writeheader()
        for r in raw_records:
            w.writerow(r)
    print(f"wrote {OUT_CSV.relative_to(ROOT)}")

    OUT_CONV = ROOT / "results" / "eo_tensor_converted.csv"
    with open(OUT_CONV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(converted_records[0].keys()))
        w.writeheader()
        for r in converted_records:
            w.writerow(r)
    print(f"wrote {OUT_CONV.relative_to(ROOT)}")

    print("\nSymmetry check (any forbidden slot with |raw| >= 1.0 Ry a.u. flagged):")
    n_flagged = 0
    for r in converted_records:
        if r["flag"]:
            n_flagged += 1
            print(" ", r)
    print(f"{n_flagged} flagged out of {len(converted_records)} (branches x 18 slots)")

    print("\nPrincipal coefficients (r_pmV), allowed slots only, per branch:")
    for name in br:
        print(f"  {name}:")
        for r in converted_records:
            if r["branch"] == name and r["symmetry_allowed"]:
                print(f"    r{r['mu']}{r['k']} = {r['r_pmV']:+.4f} pm/V  (raw {r['raw_value_Ry_au']:+.6f} Ry a.u.)")


if __name__ == "__main__":
    main()
