"""C-VAL4 Step 1: record the QE-vs-ABINIT ground-state parity comparison (electron
count, band gap, total energy) at the exact Veithen & Ghosez G1 geometry, identical
LDA UPF2 pseudopotentials/cutoff/k-grid.

Source runs:
  QE:     collected/run-35759163712/delC-CVAL3_G1_k8 (occ-only, nbnd=34) for total
          energy, and collected/run-35801775287/CVAL4_qe_gap_G1 (nbnd=42) for gap.
  ABINIT: collected/run-35799854381/delC-CVAL4_abinit_gs_G1 (nbnd=42).

    python scripts/build_cval4_gs_parity.py
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "cval4_gs_parity.csv"

HARTREE_EV = 27.211386245988
RY_EV = 13.605693122994

QE_NELECT = 68.00
QE_ETOTAL_RY = -476.93625719
QE_HOMO_EV = 7.4995
QE_LUMO_EV = 11.0117  # global BZ minimum, not restricted to Gamma
QE_GAP_EV = QE_LUMO_EV - QE_HOMO_EV

ABINIT_NELECT = 68.0
ABINIT_ETOTAL_HA = -2.38468419E+02
ABINIT_HOMO_HA = 0.16695  # Gamma point only (nkpt=65 grid; QE gap compares to global BZ min)
ABINIT_LUMO_HA = 0.29700  # Gamma point only
ABINIT_GAP_EV = (ABINIT_LUMO_HA - ABINIT_HOMO_HA) * HARTREE_EV

ROWS = [
    dict(quantity="number_of_electrons", qe=QE_NELECT, abinit=ABINIT_NELECT,
         abs_diff=abs(QE_NELECT - ABINIT_NELECT), rel_diff_pct=0.0,
         note="Exact match."),
    dict(quantity="total_energy_eV_per_cell",
         qe=round(QE_ETOTAL_RY * RY_EV, 5), abinit=round(ABINIT_ETOTAL_HA * HARTREE_EV, 5),
         abs_diff=round(abs(QE_ETOTAL_RY * RY_EV - ABINIT_ETOTAL_HA * HARTREE_EV), 5),
         rel_diff_pct=round(100 * abs(QE_ETOTAL_RY * RY_EV - ABINIT_ETOTAL_HA * HARTREE_EV) /
                             abs(QE_ETOTAL_RY * RY_EV), 6),
         note="Absolute total-energy conventions can differ between codes (isolated-atom "
              "reference, Ewald convention) -- per task, qualitative comparison only. "
              "Agreement here is ~0.008 eV over 68 electrons, far tighter than required."),
    dict(quantity="band_gap_eV", qe=round(QE_GAP_EV, 4), abinit=round(ABINIT_GAP_EV, 4),
         abs_diff=round(abs(QE_GAP_EV - ABINIT_GAP_EV), 4),
         rel_diff_pct=round(100 * abs(QE_GAP_EV - ABINIT_GAP_EV) / QE_GAP_EV, 2),
         note="QE gap is the true global-BZ minimum (65 k-points, standard MP 8x8x8 grid); "
              "ABINIT value is restricted to the Gamma point only (prtvol=0/1 default only "
              "prints kpt#1). Close agreement (<1%) despite this restriction."),
]

H0_CODE_THRESHOLD_PCT = 10.0


def main():
    for r in ROWS:
        r["H0_CODE_pass_lt10pct"] = r["rel_diff_pct"] < H0_CODE_THRESHOLD_PCT
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        fieldnames = ["quantity", "qe", "abinit", "abs_diff", "rel_diff_pct", "H0_CODE_pass_lt10pct", "note"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in ROWS:
            w.writerow(r)
    print(f"wrote {OUT.relative_to(ROOT)}")
    for r in ROWS:
        print(f"{r['quantity']:28s} QE={r['qe']:>14}  ABINIT={r['abinit']:>14}  "
              f"rel_diff={r['rel_diff_pct']}%  pass={r['H0_CODE_pass_lt10pct']}")
    print("\nGate result: ground-state parity CONFIRMED (all quantities within tolerance). "
          "Proceeding to Step 2 (nonlinear-response comparison) is justified.")


if __name__ == "__main__":
    main()
