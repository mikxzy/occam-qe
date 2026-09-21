"""Dielectric tensor + Born effective charge comparison across B0/B1/B2 (H0-B4).

    python scripts/dielectric_comparison.py

Writes results/delB_dielectric.csv (epsilon components + relative diffs vs B0) and
results/delB_born_charges.json (per-atom Z* tensors, with and without ASR, all structures).
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

from qe_ph_out import parse_phout
from qe_born_charges import parse_born_charges

ROOT = Path(__file__).resolve().parents[1]
DELB = ROOT / "runs" / "delB"
OUT_CSV = ROOT / "results" / "delB_dielectric.csv"
OUT_ZSTAR = ROOT / "results" / "delB_born_charges.json"


def ph_out_path(name: str) -> Path:
    return (DELB / name / "artifact" / "ph.out") if name == "B0" else (DELB / name / "artifact" / "clean_scf" / "ph.out")


def main():
    structures = []
    for name in ["B0", "B1", "B2"]:
        p = ph_out_path(name)
        if p.exists():
            structures.append((name, p))
        else:
            print(f"skip {name}: no ph.out yet at {p}")

    eps = {}
    zstar = {}
    for name, p in structures:
        r = parse_phout(p)
        eps[name] = r["epsilon_cartesian"]
        zstar[name] = parse_born_charges(p)

    OUT_ZSTAR.parent.mkdir(parents=True, exist_ok=True)
    OUT_ZSTAR.write_text(json.dumps(zstar, indent=1))
    print(f"wrote {OUT_ZSTAR.relative_to(ROOT)}")

    ref = eps.get("B0")
    rows = []
    comps = [("eps_xx", 0, 0), ("eps_yy", 1, 1), ("eps_zz", 2, 2),
             ("eps_xy", 0, 1), ("eps_xz", 0, 2), ("eps_yz", 1, 2)]
    for label, i, j in comps:
        row = dict(component=label)
        for name, _ in structures:
            v = eps[name][i][j] if eps[name] else None
            row[name] = v
            if name != "B0" and ref is not None and ref[i][j] is not None:
                d = None if v is None else v - ref[i][j]
                rel = None if (d is None or abs(ref[i][j]) < 1e-6) else 100 * d / abs(ref[i][j])
                row[f"{name}_minus_B0"] = d
                row[f"{name}_rel_pct"] = round(rel, 4) if rel is not None else None
        rows.append(row)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {OUT_CSV.relative_to(ROOT)}")
    for r in rows:
        print(" ", r)


if __name__ == "__main__":
    main()
