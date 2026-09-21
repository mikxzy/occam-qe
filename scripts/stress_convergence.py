"""Compare the full 6 independent stress-tensor components (not just scalar pressure)
between two DEL A convergence jobs, applying BOTH:
  - the existing relative criterion (<1% change, task rule "malet ar <1% forandring")
  - an absolute criterion (<=1 kbar change per independent component)
A pair is CONVERGED only if every independent component satisfies BOTH criteria
(the relative criterion is skipped, not failed, for components whose reference
magnitude is < 0.05 kbar, where a relative % is not meaningful).

    python scripts/stress_convergence.py --a scf_ecut100_k4 --b scf_ecut120_k4

Appends one row per checked pair to results/stress_convergence.csv.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "convergence"
OUT = ROOT / "results" / "stress_convergence.csv"

COMPONENTS = [("xx", 0, 0), ("yy", 1, 1), ("zz", 2, 2), ("xy", 0, 1), ("xz", 0, 2), ("yz", 1, 2)]
ABS_TOL_KBAR = 1.0
REL_TOL_PCT = 1.0
REL_SKIP_BELOW_KBAR = 0.05  # relative % is not meaningful below this magnitude


def load(job_id: str) -> dict:
    p = RUNS / job_id / "artifact" / "result.json"
    if not p.exists():
        raise SystemExit(f"no result.json for {job_id} at {p} -- run/download it first")
    return json.loads(p.read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="reference (tighter or earlier) job id")
    ap.add_argument("--b", required=True, help="candidate (looser or later) job id")
    args = ap.parse_args()

    ra, rb = load(args.a), load(args.b)
    sa, sb = ra["stress_final_kbar"], rb["stress_final_kbar"]

    rows = []
    all_pass = True
    for name, i, j in COMPONENTS:
        va, vb = sa[i][j], sb[i][j]
        dabs = abs(vb - va)
        abs_ok = dabs <= ABS_TOL_KBAR
        if abs(va) >= REL_SKIP_BELOW_KBAR:
            rel_pct = 100.0 * dabs / abs(va)
            rel_ok = rel_pct <= REL_TOL_PCT
        else:
            rel_pct = None
            rel_ok = True  # not meaningful; absolute criterion governs
        component_ok = abs_ok and rel_ok
        all_pass = all_pass and component_ok
        rows.append(dict(component=name, value_a_kbar=va, value_b_kbar=vb,
                          delta_abs_kbar=round(dabs, 4),
                          delta_rel_pct=(round(rel_pct, 4) if rel_pct is not None else "N/A (|ref|<0.05 kbar)"),
                          abs_ok=abs_ok, rel_ok=rel_ok, component_ok=component_ok))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_header = not OUT.exists()
    with open(OUT, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pair", *rows[0].keys()])
        if write_header:
            w.writeheader()
        for r in rows:
            w.writerow(dict(pair=f"{args.a}_vs_{args.b}", **r))

    print(f"{args.a} vs {args.b}: E_a={ra['E_final_Ry']} Ry, E_b={rb['E_final_Ry']} Ry")
    for r in rows:
        print(f"  {r['component']}: {r['value_a_kbar']:+8.3f} -> {r['value_b_kbar']:+8.3f} kbar  "
              f"dAbs={r['delta_abs_kbar']:.3f} kbar  dRel={r['delta_rel_pct']}  "
              f"{'PASS' if r['component_ok'] else 'FAIL'}")
    print(f"PAIR RESULT: {'CONVERGED' if all_pass else 'NOT CONVERGED'} "
          f"(abs<= {ABS_TOL_KBAR} kbar AND rel<= {REL_TOL_PCT}% per component)")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
