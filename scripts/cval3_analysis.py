"""DEL C-VAL3: geometry parity analysis. Compares G0 (our LDA-relaxed geometry) vs G1
(Veithen & Ghosez's published LDA geometry), both at k=8x8x8, same pseudopotentials/
cutoff/elop pipeline, at both the raw dEps/dE level and the final r_ijk level.

    python scripts/cval3_analysis.py

Writes results/cval3_geometry_parity.csv.
"""
from __future__ import annotations
import csv
import math
from pathlib import Path

from eo_raw_extract import parse_elop_full
from qe_ph_out import parse_phout

ROOT = Path(__file__).resolve().parents[1]
DELC3 = ROOT / "runs" / "delC" / "CVAL3_geometry_parity"
RY_TO_PMV = 2.7502

VOIGT = [("22", 1, 1, 1), ("13", 0, 0, 2), ("33", 2, 2, 2), ("51", 0, 2, 0)]  # (name, i, j, k)


def elop_at(raw9x3, i, j, k):
    return raw9x3[3 * k + j][i]


def load(name: str):
    d = DELC3 / name / "artifact"
    ph_text = (d / "ph.out").read_text(errors="ignore")
    total = parse_elop_full(ph_text)["total"]
    eps = parse_phout(d / "ph.out")["epsilon_cartesian"]
    return total, eps


def main():
    total_g0, eps_g0 = load("G0_k8")
    total_g1, eps_g1 = load("G1_k8")

    rows = []
    for name, i, j, k in VOIGT:
        g0_raw = elop_at(total_g0, i, j, k)
        g1_raw = elop_at(total_g1, i, j, k)
        g0_dEdE_pmV = g0_raw * RY_TO_PMV
        g1_dEdE_pmV = g1_raw * RY_TO_PMV
        ratio_raw = g1_raw / g0_raw if g0_raw else None

        eps_ii_g0, eps_jj_g0 = eps_g0[i][i], eps_g0[j][j]
        eps_ii_g1, eps_jj_g1 = eps_g1[i][i], eps_g1[j][j]
        r_g0 = -g0_dEdE_pmV / (eps_ii_g0 * eps_jj_g0)
        r_g1 = -g1_dEdE_pmV / (eps_ii_g1 * eps_jj_g1)
        ratio_r = r_g1 / r_g0 if r_g0 else None
        pct_change = 100 * (r_g1 - r_g0) / r_g0 if r_g0 else None

        rows.append(dict(
            coefficient=f"r{name}",
            G0_raw_Ry_au=round(g0_raw, 6), G1_raw_Ry_au=round(g1_raw, 6),
            ratio_G1_over_G0_raw=round(ratio_raw, 4) if ratio_raw else None,
            G0_r_pmV=round(r_g0, 4), G1_r_pmV=round(r_g1, 4),
            ratio_G1_over_G0_r=round(ratio_r, 4) if ratio_r else None,
            pct_change_G0_to_G1=round(pct_change, 2) if pct_change is not None else None,
            H0_GEO_reject=(abs(pct_change) > 5.0) if pct_change is not None else None,
        ))

    # dielectric tensor comparison too, useful context
    for label, i in [("eps_xx", 0), ("eps_zz", 2)]:
        v0, v1 = eps_g0[i][i], eps_g1[i][i]
        rows.append(dict(coefficient=label, G0_raw_Ry_au=None, G1_raw_Ry_au=None,
                          ratio_G1_over_G0_raw=None, G0_r_pmV=round(v0, 6), G1_r_pmV=round(v1, 6),
                          ratio_G1_over_G0_r=round(v1 / v0, 4), pct_change_G0_to_G1=round(100 * (v1 - v0) / v0, 3),
                          H0_GEO_reject=None))

    OUT = ROOT / "results" / "cval3_geometry_parity.csv"
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {OUT.relative_to(ROOT)}")

    print(f"\n{'coef':8s} {'G0_r_pmV':>10s} {'G1_r_pmV':>10s} {'%change':>9s} {'H0-GEO':>10s}")
    for r in rows:
        if r["coefficient"].startswith("r") and r["coefficient"] != "results":
            flag = "REJECTED" if r["H0_GEO_reject"] else "not rejected"
            print(f"{r['coefficient']:8s} {r['G0_r_pmV']:10.4f} {r['G1_r_pmV']:10.4f} "
                  f"{r['pct_change_G0_to_G1']:+8.2f}% {flag:>12s}")

    any_reject = any(r["H0_GEO_reject"] for r in rows if r["H0_GEO_reject"] is not None)
    max_abs_pct = max(abs(r["pct_change_G0_to_G1"]) for r in rows if r["coefficient"].startswith("r") and r["coefficient"] not in ("eps_xx", "eps_zz"))
    print(f"\nH0-GEO overall: {'REJECTED' if any_reject else 'NOT REJECTED'} (max |% change| = {max_abs_pct:.2f}%)")


if __name__ == "__main__":
    main()
