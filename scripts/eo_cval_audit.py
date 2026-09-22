"""DEL C-VAL: rigorous tensor audit (C-VAL1, C-VAL2, C-VAL3/4).

C-VAL1: re-extract the unmodified QE elop tensor G_ijk = d(eps_ij)/dE_k, with raw QE
value, QE units, and the converted length/voltage-unit derivative (pm/V, SI-derived) --
NOT yet the Pockels r tensor. -> results/elop_qe_raw.csv

C-VAL2: convert to the Pockels tensor via the full matrix identity
r_k = -eps^-1 G_k eps^-1 (k = field direction), NOT the diagonal shortcut, and validate
it numerically against central finite-difference differentiation of eta=eps^-1 along E.
-> results/pockels_cartesian.csv

C-VAL3/4: QE's raw Cartesian frame was PROVEN (scripts/derive_symmetry_from_actual_frame.py,
using the real spglib Cartesian symmetry operations, not an assumed frame) to already
coincide with the conventional "mirror normal along x" 3m frame -- rotation R = identity
to numerical noise. So the Cartesian-frame tensor IS the conventional-frame tensor here;
saved a second time under the conventional-frame filename with that derivation recorded
explicitly, not silently assumed. -> results/pockels_conventional_frame.csv

    python scripts/eo_cval_audit.py
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

import numpy as np

from eo_raw_extract import parse_elop_full
from qe_ph_out import parse_phout

ROOT = Path(__file__).resolve().parents[1]
DELC = ROOT / "runs" / "delC" / "C3_LDA"
RY_TO_PMV = 2.7502  # QE source-documented factor for the raw d(eps)/dE quantity itself
AXES = "xyz"


def branches():
    out = {}
    b = DELC / "EO_at_PBEsol_geom" / "artifact"
    if (b / "ph.out").exists():
        out["LDA@PBEsol-geometry"] = b
    b = DELC / "vcrelax" / "artifact" / "clean_scf"
    if (b / "ph.out").exists():
        out["LDA@LDA-relaxed"] = b
    b = DELC / "EO_at_B0_geom" / "artifact"
    if (b / "ph.out").exists():
        out["LDA@B0-geometry"] = b
    b = ROOT / "runs" / "delC" / "C13_k6" / "artifact"
    if (b / "ph.out").exists():
        out["LDA-relaxed@k6"] = b
    return out


def elop_at(raw9x3, i, j, k):
    return raw9x3[3 * k + j][i]


def build_G_matrix(raw9x3, k):
    """3x3 matrix G_k[i,j] = d(eps_ij)/dE_k, in raw Ry a.u."""
    G = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            G[i, j] = elop_at(raw9x3, i, j, k)
    return G


def main():
    br = branches()
    if not br:
        print("no branches found")
        return

    val1_rows = []
    val2_rows = []
    audit_summary = []

    for name, d in br.items():
        ph_text = (d / "ph.out").read_text(errors="ignore")
        elop = parse_elop_full(ph_text)
        total = elop["total"]
        eps_r = parse_phout(d / "ph.out")
        eps = np.array(eps_r["epsilon_cartesian"])

        # ---- C-VAL1: raw tensor, unmodified
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    raw_val = elop_at(total, i, j, k)
                    val1_rows.append(dict(
                        branch=name, i=AXES[i], j=AXES[j], k=AXES[k],
                        G_ijk_raw_Ry_au=raw_val,
                        qe_units="Rydberg a.u. (d(epsilon_ij)/dE_k, symmetrized cartesian axis, electronic+XC-derivative total)",
                        G_ijk_pmV=round(raw_val * RY_TO_PMV, 6),
                        note="this is G_ijk = d(eps)/dE, NOT yet the Pockels r tensor -- see pockels_cartesian.csv for that conversion",
                        provenance=f"{d}/ph.out",
                    ))

        # ---- C-VAL2: full matrix r_k = -eps^-1 G_k eps^-1, plus finite-difference validation
        eps_inv = np.linalg.inv(eps)
        # h chosen via explicit convergence scan (not guessed): 1e-4 gave ~1e-3 relative
        # error (h*G ~ 0.07, not small compared to eps~5.5 -- real O(h^2) truncation
        # error, not a formula bug); 1e-8 agrees with the analytic result to 2e-14
        # absolute, well past the 1e-6 target, before floating-point roundoff would set
        # in at even smaller h. See results/eo_cval_h_convergence.csv for the full scan.
        h = 1e-8
        branch_audit = dict(branch=name, eps=eps.tolist(), eps_inv=eps_inv.tolist(), max_rel_diff=0.0)
        for k in range(3):
            Gk_raw = build_G_matrix(total, k)  # Ry a.u.
            Gk_pmV = Gk_raw * RY_TO_PMV

            # analytic: r_k = -eps^-1 G_k eps^-1 (full matrix operation, per instruction)
            r_k_analytic = -eps_inv @ Gk_pmV @ eps_inv

            # finite-difference validation (pure linear-algebra self-consistency check)
            eps_plus = eps + h * Gk_pmV
            eps_minus = eps - h * Gk_pmV
            eta_plus = np.linalg.inv(eps_plus)
            eta_minus = np.linalg.inv(eps_minus)
            r_k_findiff = (eta_plus - eta_minus) / (2 * h)

            # Components consistent with zero (symmetry-forbidden or numerically null) sit
            # at the h=1e-8 finite-difference noise floor (~1e-9 pm/V, see
            # eo_cval_h_convergence.csv) -- a relative error there is meaningless
            # (near-zero / near-zero). 1e-3 pm/V is ~4 orders of magnitude above that
            # noise floor and ~4-5 orders below the real coefficients (~20-40 pm/V).
            NOISE_FLOOR_PMV = 1e-3
            denom = np.where(np.abs(r_k_analytic) > NOISE_FLOOR_PMV, np.abs(r_k_analytic), np.nan)
            abs_diff = np.abs(r_k_findiff - r_k_analytic)
            rel_diff = abs_diff / denom
            max_rel = np.nanmax(rel_diff) if not np.all(np.isnan(rel_diff)) else 0.0
            max_abs_on_noise_floor = float(np.max(abs_diff[np.abs(r_k_analytic) <= NOISE_FLOOR_PMV])) if np.any(np.abs(r_k_analytic) <= NOISE_FLOOR_PMV) else 0.0
            branch_audit["max_rel_diff"] = max(branch_audit["max_rel_diff"], float(max_rel) if not np.isnan(max_rel) else 0.0)
            branch_audit["max_abs_diff_on_near_zero_components"] = max(branch_audit.get("max_abs_diff_on_near_zero_components", 0.0), max_abs_on_noise_floor)

            for i in range(3):
                for j in range(3):
                    val2_rows.append(dict(
                        branch=name, i=AXES[i], j=AXES[j], k=AXES[k],
                        r_ijk_analytic_pmV=round(r_k_analytic[i, j], 6),
                        r_ijk_findiff_pmV=round(r_k_findiff[i, j], 6),
                        rel_diff=(round(float(rel_diff[i, j]), 10) if not np.isnan(rel_diff[i, j]) else "n/a (near-zero component)"),
                        method="full 3x3 matrix: r_k = -eps^-1 G_k eps^-1 (G_k, eps^-1 both genuine matrices, not diagonal shortcut)",
                    ))
        audit_summary.append(branch_audit)
        print(f"{name}: max relative diff (analytic vs finite-difference) = {branch_audit['max_rel_diff']:.3e}"
              f"  {'PASS (<1e-6)' if branch_audit['max_rel_diff'] < 1e-6 else 'FAIL'}")

    OUT1 = ROOT / "results" / "elop_qe_raw.csv"
    with open(OUT1, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(val1_rows[0].keys()))
        w.writeheader()
        for r in val1_rows:
            w.writerow(r)
    print(f"wrote {OUT1.relative_to(ROOT)} ({len(val1_rows)} rows)")

    OUT2 = ROOT / "results" / "pockels_cartesian.csv"
    with open(OUT2, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(val2_rows[0].keys()))
        w.writeheader()
        for r in val2_rows:
            w.writerow(r)
    print(f"wrote {OUT2.relative_to(ROOT)} ({len(val2_rows)} rows)")

    # C-VAL3/4: conventional frame = Cartesian frame here (R=identity, proven separately)
    OUT3 = ROOT / "results" / "pockels_conventional_frame.csv"
    conv_rows = []
    for r in val2_rows:
        conv_rows.append(dict(**r, rotation_applied="IDENTITY (proven via scripts/derive_symmetry_from_actual_frame.py: "
                                                      "QE's raw Cartesian frame already coincides with the conventional "
                                                      "mirror-normal-along-x 3m frame, verified against the actual spglib "
                                                      "Cartesian symmetry operations, not assumed)"))
    with open(OUT3, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(conv_rows[0].keys()))
        w.writeheader()
        for r in conv_rows:
            w.writerow(r)
    print(f"wrote {OUT3.relative_to(ROOT)} ({len(conv_rows)} rows)")

    (ROOT / "results" / "eo_cval_audit_summary.json").write_text(json.dumps(audit_summary, indent=1))
    print(f"wrote results/eo_cval_audit_summary.json")


if __name__ == "__main__":
    main()
