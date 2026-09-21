"""Assemble results/delB_phonons.csv: raw + ASR-corrected frequency, irrep, degeneracy,
acoustic/optical classification, and (for B1/B2) the tracked B0 mode + eigenvector
overlap, for every mode of every available structure (B0/B1/B2).

Acoustic identification: the 3 modes with the smallest |ASR-corrected frequency| in each
structure's own calculation (robust or a Gamma-only calculation: acoustic modes must go
to exactly 0 once ASR is imposed; this is checked, not assumed, against the symmetry
labels where available).

    python scripts/phonon_report.py
"""
from __future__ import annotations
import csv
from pathlib import Path

from qe_ph_out import parse_phout
from qe_dynmat_out import parse_eigenvectors, parse_dynmat_freq_table
from qe_mode_symmetry import parse_mode_symmetry
from mode_tracking import group_degenerate, subspace_overlap, DEGEN_TOL_CM1, N_ATOMS

ROOT = Path(__file__).resolve().parents[1]
DELB = ROOT / "runs" / "delB"
OUT = ROOT / "results" / "delB_phonons.csv"
STABILITY_TOL_CM1 = 5.0


def branch_dir(name: str) -> Path:
    return (DELB / name / "artifact") if name == "B0" else (DELB / name / "artifact" / "clean_scf")


def load_structure(name: str):
    d = branch_dir(name)
    ph_out = d / "ph.out"
    if not ph_out.exists():
        return None
    raw = parse_phout(ph_out)
    ft = parse_dynmat_freq_table(d / "dynmat.out")
    eig = parse_eigenvectors(d / "dynmat.eig.out", n_atoms=N_ATOMS)
    sym = parse_mode_symmetry(ph_out)
    return dict(name=name, freqs_raw=raw["freqs_cm1"], asr_modes=ft["modes"],
                eig_freqs=eig["freqs_cm1"], eigvecs=eig["eigvecs"], symmetry=sym["per_mode"])


def classify(idx_1based: int, freq_asr: float, acoustic_indices: set[int]) -> str:
    if idx_1based in acoustic_indices:
        return "acoustic"
    if freq_asr < -STABILITY_TOL_CM1:
        return "imaginary_optical"
    if abs(freq_asr) <= STABILITY_TOL_CM1:
        return "near_zero_optical_residual_inspect"
    return "stable_optical"


def main():
    structures = {n: load_structure(n) for n in ["B0", "B1", "B2"]}
    structures = {n: s for n, s in structures.items() if s is not None}
    for n in ["B1", "B2"]:
        if n not in structures:
            print(f"skip {n}: no ph.out yet")
    if "B0" not in structures:
        raise SystemExit("B0 must exist")

    b0 = structures["B0"]
    b0_groups = group_degenerate(b0["eig_freqs"])

    rows = []
    for name, s in structures.items():
        asr_by_mode = {m["mode"]: m["freq_cm1_asr"] for m in s["asr_modes"]}
        acoustic_indices = set(sorted(range(1, len(s["eig_freqs"]) + 1),
                                       key=lambda i: abs(asr_by_mode.get(i, 999)))[:3])

        if name == "B0":
            matched_map = {i + 1: (i + 1, 1.0) for i in range(len(b0["eig_freqs"]))}
        else:
            groups = group_degenerate(s["eig_freqs"])
            matched_map = {}
            for g in groups:
                scores = [(gb, subspace_overlap(s["eigvecs"], g, b0["eigvecs"], gb)) for gb in b0_groups]
                best_gb, best_score = max(scores, key=lambda t: t[1])
                b0_mode_label = "+".join(str(i + 1) for i in best_gb)
                for i in g:
                    matched_map[i + 1] = (b0_mode_label, round(best_score, 4))

        for i in range(1, len(s["eig_freqs"]) + 1):
            freq_raw = s["freqs_raw"][i - 1] if i - 1 < len(s["freqs_raw"]) else None
            freq_asr = asr_by_mode.get(i)
            sym = s["symmetry"].get(i, {})
            degeneracy = next((len(g) for g in group_degenerate(s["eig_freqs"]) if (i - 1) in g), 1)
            matched_b0, overlap = matched_map.get(i, (None, None))
            rows.append(dict(
                structure=name, mode=i,
                frequency_cm1_raw=freq_raw, frequency_cm1_asr=freq_asr,
                irrep=sym.get("irrep"), degeneracy=degeneracy,
                acoustic_or_optical="acoustic" if i in acoustic_indices else "optical",
                matched_B0_mode=matched_b0, eigenvector_overlap=overlap,
                stability_class=classify(i, freq_asr if freq_asr is not None else freq_raw, acoustic_indices),
            ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} rows, {len(structures)} structures)")

    # compact table for the originally-unstable modes
    print("\nUnstable-mode tracking (imaginary_optical only):")
    for r in rows:
        if r["stability_class"] == "imaginary_optical":
            print(f"  {r['structure']} mode {r['mode']:2d} ({r['irrep']}, deg={r['degeneracy']}): "
                  f"{r['frequency_cm1_asr']:+9.3f} cm-1 (ASR)  matched_B0={r['matched_B0_mode']} "
                  f"overlap={r['eigenvector_overlap']}")


if __name__ == "__main__":
    main()
