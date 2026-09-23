"""C-VAL4 Step 5: QE vs ABINIT_PEAD vs Veithen literature comparison table for the
electronic (clamped-ion) EO/nonlinear response at the exact G1 geometry.

QE side: r_ijk = -(d(eps_ij)/dE_k) / (eps_ii * eps_jj), the SAME formula already
validated in C-VAL1/C-VAL2 (eo_cval_audit.py), applied to the "contribution # 1"
(electronic) block of collected/run-35759163712/delC-CVAL3_G1_k8/ph.out.

ABINIT side: r_ijk = -8*pi*chi2_ijk / (n_i^2 * n_j^2), Eq. (3) (electronic/first term
only) of Veithen, Gonze & Ghosez, PRB 71, 125107 (2005), n_i^2 = eps_ii (the same
electronic dielectric tensor, cross-checked against QE's own G1 eps to <0.003%
agreement). ABINIT prints "d" (pm/V), the standard SHG coefficient; chi2 = 2*d is the
standard textbook relation (Boyd, Nonlinear Optics) -- NOT independently confirmed
against ABINIT's own source code or an anaddb run in this pass (anaddb needs a DDB
file this run did not produce; a rerun with prtddb enabled would remove this
ambiguity, at a cost of another ~5h ABINIT job). Both the chi2=2d and chi2=d cases are
reported; the qualitative conclusion (ABINIT reproduces the SAME large-magnitude
regime as QE, not Veithen's small literature values) is unaffected by which is used.

    python scripts/build_cval4_code_parity.py
"""
from __future__ import annotations
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "cval4_code_parity.csv"

RY_TO_PMV = 2.7502  # QE's own stated conversion (ph.out header)

# --- QE, G1 geometry, electronic-only (contribution #1), Ry a.u. raw d(eps)/dE ---
QE_EPS_XX = 5.552321451
QE_EPS_ZZ = 5.467398197
QE_RAW = dict(  # Ry a.u., from ph.out "Electro-optic tensor: contribution # 1"
    r22=-200.968140663,  # d(eps_yy)/dE_y
    r13=-415.549979238,  # d(eps_xx)/dE_z
    r51=-415.549979238,  # d(eps_xz)/dE_x
    r33=-377.847190485,  # d(eps_zz)/dE_z
)
QE_DENOM = dict(r22=QE_EPS_XX * QE_EPS_XX, r13=QE_EPS_XX * QE_EPS_ZZ,
                r51=QE_EPS_XX * QE_EPS_ZZ, r33=QE_EPS_ZZ * QE_EPS_ZZ)

# --- ABINIT, G1 geometry, PEAD electronic-only, d tensor (pm/V), dataset 4 eps ---
ABINIT_EPS_XX = 5.5521642265
ABINIT_EPS_ZZ = 5.4673269408
ABINIT_D_PMV = dict(r22=-1.212188793, r13=-7.797225035, r51=-7.797225035, r33=-29.623415618)
ABINIT_DENOM = dict(r22=ABINIT_EPS_XX * ABINIT_EPS_XX, r13=ABINIT_EPS_XX * ABINIT_EPS_ZZ,
                     r51=ABINIT_EPS_XX * ABINIT_EPS_ZZ, r33=ABINIT_EPS_ZZ * ABINIT_EPS_ZZ)

# --- Veithen & Ghosez PRB 71, 125107 (2005), Table I, "Electronic" row (pm/V) ---
VEITHEN_ELECTRONIC = dict(r22=None, r13=1.4, r51=1.0, r33=0.2)  # r22 not tabulated (blank in Table I)

COEFFS = ["r22", "r13", "r51", "r33"]


def main():
    rows = []
    for c in COEFFS:
        qe_r = -(QE_RAW[c] * RY_TO_PMV) / QE_DENOM[c]

        chi2_eq_d = ABINIT_D_PMV[c]           # if ABINIT's printed d == Eq.3's chi2 directly
        chi2_eq_2d = 2 * ABINIT_D_PMV[c]       # if standard d = chi2/2 convention holds
        abinit_r_caseA = -8 * math.pi * chi2_eq_d / ABINIT_DENOM[c]
        abinit_r_caseB = -8 * math.pi * chi2_eq_2d / ABINIT_DENOM[c]

        veithen = VEITHEN_ELECTRONIC[c]
        rows.append(dict(
            quantity=c,
            QE=round(qe_r, 3),
            ABINIT_PEAD_caseA_chi2eqd=round(abinit_r_caseA, 3),
            ABINIT_PEAD_caseB_chi2eq2d=round(abinit_r_caseB, 3),
            Veithen_reference_electronic=veithen,
            QE_over_Veithen=round(qe_r / veithen, 1) if veithen else "n/a (Veithen r22 not tabulated)",
            ABINIT_caseB_over_Veithen=round(abinit_r_caseB / veithen, 1) if veithen else "n/a",
            ABINIT_over_QE_caseB=round(abinit_r_caseB / qe_r, 2),
            H0_CODE_pass_lt10pct=abs(abinit_r_caseB - qe_r) / abs(qe_r) < 0.10,
        ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {OUT.relative_to(ROOT)}")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
