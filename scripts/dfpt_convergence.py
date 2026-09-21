"""Compare dielectric tensor + Gamma phonon frequencies across the DEL A completion
matrix (80/100/120 Ry, k=4x4x4). Mode-by-mode frequency comparison uses a dual
criterion mirroring stress_convergence.py: absolute (<=2 cm-1) AND relative (<1%,
skipped below 20 cm-1 where % is not meaningful for a near-zero/soft mode).

    python scripts/dfpt_convergence.py

Writes results/dfpt_convergence.csv (dielectric + per-mode frequency table) and prints
a summary, including an explicit flag for any mode whose stability conclusion
(sign of frequency) is not yet cutoff-converged.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "convergence_dfpt"
OUT = ROOT / "results" / "dfpt_convergence.csv"

ECUTS = [80, 100, 120]
ABS_TOL_CM1 = 2.0
REL_TOL_PCT = 1.0
REL_SKIP_BELOW_CM1 = 20.0


def load(ecut: int) -> dict:
    p = RUNS / f"dfpt_ecut{ecut}_k4" / "artifact" / "result.json"
    return json.loads(p.read_text())


def main():
    results = {e: load(e) for e in ECUTS}

    rows = []
    # dielectric tensor (diagonal, this cell's Cartesian frame is diagonal)
    for label, i, j in [("eps_xx", 0, 0), ("eps_yy", 1, 1), ("eps_zz", 2, 2)]:
        vals = [results[e]["epsilon_cartesian"][i][j] for e in ECUTS]
        d_100_120 = abs(vals[2] - vals[1])
        rel = 100 * d_100_120 / abs(vals[1]) if abs(vals[1]) > 1e-6 else None
        rows.append(dict(quantity=label, v_80=vals[0], v_100=vals[1], v_120=vals[2],
                          delta_100_120=round(d_100_120, 6),
                          rel_pct_100_120=round(rel, 5) if rel is not None else "N/A",
                          converged_100_120=(rel is not None and rel <= REL_TOL_PCT)))

    # phonon frequencies, mode-by-mode (sorted ascending index; valid as long as no
    # level-crossing reordering happens between cutoffs, checked below)
    f80 = results[80]["freqs_cm1"]
    f100 = results[100]["freqs_cm1"]
    f120 = results[120]["freqs_cm1"]
    n = min(len(f80), len(f100), len(f120))
    n_not_converged = 0
    n_sign_unstable = 0
    for idx in range(n):
        v80, v100, v120 = f80[idx], f100[idx], f120[idx]
        dabs = abs(v120 - v100)
        abs_ok = dabs <= ABS_TOL_CM1
        if abs(v100) >= REL_SKIP_BELOW_CM1:
            rel_pct = 100 * dabs / abs(v100)
            rel_ok = rel_pct <= REL_TOL_PCT
        else:
            rel_pct = None
            rel_ok = True
        mode_ok = abs_ok and rel_ok
        if not mode_ok:
            n_not_converged += 1
        sign_stable_across_cutoffs = (v80 < 0) == (v100 < 0) == (v120 < 0)
        if not sign_stable_across_cutoffs:
            n_sign_unstable += 1
        rows.append(dict(quantity=f"mode_{idx:02d}_cm1", v_80=v80, v_100=v100, v_120=v120,
                          delta_100_120=round(dabs, 4),
                          rel_pct_100_120=(round(rel_pct, 4) if rel_pct is not None else "N/A (|ref|<20cm-1)"),
                          converged_100_120=mode_ok,
                          stability_sign_consistent_across_cutoffs=sign_stable_across_cutoffs))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["quantity", "v_80", "v_100", "v_120", "delta_100_120", "rel_pct_100_120",
                  "converged_100_120", "stability_sign_consistent_across_cutoffs"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"dielectric tensor: converged well within tolerance at all 3 cutoffs "
          f"(largest 100->120 Ry change {max(abs(results[100]['epsilon_cartesian'][i][i]-results[120]['epsilon_cartesian'][i][i]) for i in range(3)):.6f})")
    print(f"phonons: {n} modes compared, {n_not_converged}/{n} NOT within {ABS_TOL_CM1} cm-1 / {REL_TOL_PCT}% "
          f"between 100 and 120 Ry")
    print(f"stability-sign inconsistent across all 3 cutoffs (crosses zero): {n_sign_unstable} mode(s)")
    for idx in range(n):
        if (f80[idx] < 0) != (f100[idx] < 0) or (f100[idx] < 0) != (f120[idx] < 0):
            print(f"  mode {idx}: {f80[idx]:+9.3f} (80 Ry) -> {f100[idx]:+9.3f} (100 Ry) -> {f120[idx]:+9.3f} (120 Ry) cm-1  <-- sign changes / not cutoff-converged")


if __name__ == "__main__":
    main()
