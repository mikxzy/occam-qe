"""Relaxation-trajectory plots for B1/B2, per instruction: energy vs iteration, max force
vs iteration (both branches); pressure vs iteration and volume vs iteration for B2 (B1's
cell is fixed, so its pressure/volume series are also plotted for completeness but are
expected to show the internal stress the fixed cell develops / a flat volume line).

    python scripts/trajectory_plots.py
"""
from __future__ import annotations
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DELB = ROOT / "runs" / "delB"
OUT_DIR = ROOT / "results" / "plots"

COLORS = dict(B1="#4C72B0", B2="#DD8452")


def load_trajectory(name: str):
    p = DELB / name / "artifact" / "result.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text())
    return r.get("relax_trajectory")


def plot_series(trajs: dict, key: str, ylabel: str, title: str, fname: str, log_y=False):
    fig, ax = plt.subplots(figsize=(6, 4))
    any_data = False
    for name, traj in trajs.items():
        vals = traj.get(key) if traj else None
        if not vals:
            continue
        any_data = True
        ax.plot(range(1, len(vals) + 1), vals, marker="o", ms=4, color=COLORS[name], label=name)
    if not any_data:
        plt.close(fig)
        return False
    ax.set_xlabel("BFGS iteration")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if log_y:
        ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / fname, dpi=140)
    plt.close(fig)
    return True


def main():
    trajs = {n: load_trajectory(n) for n in ["B1", "B2"]}
    trajs = {n: t for n, t in trajs.items() if t is not None}
    if not trajs:
        print("no B1/B2 result.json yet -- nothing to plot")
        return

    made = []
    if plot_series(trajs, "energies_Ry", "Total energy (Ry)", "DEL B: energy vs relaxation step", "delB_energy_vs_iteration.png"):
        made.append("delB_energy_vs_iteration.png")
    if plot_series(trajs, "max_forces_eV_A", "Max |force| (eV/A)", "DEL B: max force vs relaxation step", "delB_maxforce_vs_iteration.png", log_y=True):
        made.append("delB_maxforce_vs_iteration.png")
    if plot_series(trajs, "pressures_kbar", "Pressure (kbar)", "DEL B: pressure vs relaxation step", "delB_pressure_vs_iteration.png"):
        made.append("delB_pressure_vs_iteration.png")
    if plot_series(trajs, "volumes_A3", "Cell volume (A^3)", "DEL B: cell volume vs relaxation step", "delB_volume_vs_iteration.png"):
        made.append("delB_volume_vs_iteration.png")

    print(f"wrote {len(made)} plot(s) to {OUT_DIR.relative_to(ROOT)}: {made}")


if __name__ == "__main__":
    main()
