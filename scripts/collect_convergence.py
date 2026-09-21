"""Aggregate result.json files from finished DEL A convergence jobs into
results/convergence.csv, with %-change vs. the tightest (highest ecutwfc, densest k-grid)
setting for total energy per formula unit and pressure.

    python scripts/collect_convergence.py

Looks for runs/convergence/<job_id>/artifact/result.json (produced by run_qe_job.py, or
downloaded from the qe-convergence-probe GitHub Actions artifact into the same path).
Jobs with no result.json yet are listed as NOT CALCULATED, not silently skipped.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue" / "jobs.json"
RUNS = ROOT / "runs" / "convergence"
OUT = ROOT / "results" / "convergence.csv"
N_FORMULA_UNITS = 2  # primitive cell = 2 formula units of Material A


def main():
    jobs = json.loads(QUEUE.read_text())
    rows = []
    for job_id, job in sorted(jobs.items(), key=lambda kv: (kv[1]["ecutwfc_Ry"], kv[1]["kgrid"][0])):
        result_path = RUNS / job_id / "artifact" / "result.json"
        row = dict(job_id=job_id, ecutwfc_Ry=job["ecutwfc_Ry"], ecutrho_Ry=job["ecutrho_Ry"],
                   kgrid=f"{job['kgrid'][0]}x{job['kgrid'][1]}x{job['kgrid'][2]}",
                   status="NOT CALCULATED", E_per_fu_Ry=None, pressure_kbar=None, wall_s=None)
        if result_path.exists():
            r = json.loads(result_path.read_text())
            row["status"] = r.get("status", "UNKNOWN")
            if r.get("E_final_Ry") is not None:
                row["E_per_fu_Ry"] = r["E_final_Ry"] / N_FORMULA_UNITS
            row["pressure_kbar"] = r.get("pressure_kbar")
            row["wall_s"] = r.get("wall_s")
        rows.append(row)

    # tightest setting = highest ecutwfc, densest k-grid actually computed
    done = [r for r in rows if r["status"] == "DONE" and r["E_per_fu_Ry"] is not None]
    ref = max(done, key=lambda r: (r["ecutwfc_Ry"], r["kgrid"]), default=None)
    for r in rows:
        r["dE_vs_tightest_pct"] = "NOT CALCULATED"
        r["dP_vs_tightest_kbar"] = "NOT CALCULATED"
        if ref and r["status"] == "DONE" and r["E_per_fu_Ry"] is not None:
            r["dE_vs_tightest_pct"] = round(100 * abs(r["E_per_fu_Ry"] - ref["E_per_fu_Ry"]) / abs(ref["E_per_fu_Ry"]), 5)
            if r["pressure_kbar"] is not None and ref["pressure_kbar"] is not None:
                r["dP_vs_tightest_kbar"] = round(r["pressure_kbar"] - ref["pressure_kbar"], 4)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["job_id", "ecutwfc_Ry", "ecutrho_Ry", "kgrid", "status", "E_per_fu_Ry",
                  "dE_vs_tightest_pct", "pressure_kbar", "dP_vs_tightest_kbar", "wall_s"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    n_done = sum(1 for r in rows if r["status"] == "DONE")
    print(f"wrote {OUT.relative_to(ROOT)}: {n_done}/{len(rows)} jobs DONE"
          + (f", reference = {ref['job_id']}" if ref else ", no reference (nothing DONE yet)"))


if __name__ == "__main__":
    main()
