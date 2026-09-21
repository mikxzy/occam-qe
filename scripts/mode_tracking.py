"""Track phonon modes between two DEL B geometries (e.g. B0 -> B1) using eigenvector
overlap, per instruction -- NOT by array index (relaxation can reorder modes, and
individual eigenvectors within a degenerate subspace are only defined up to an arbitrary
unitary rotation, so naive index-by-index or vector-by-vector dot products are not
meaningful for degenerate pairs).

Method: group near-degenerate modes (frequency within DEGEN_TOL_CM1) into subspaces,
then score subspace-to-subspace overlap as trace(P_A P_B) / min(dim_A, dim_B) in [0, 1]
(1.0 = B's subspace lies entirely within A's span). This is invariant to the arbitrary
internal basis choice QE's diagonalizer makes within a degenerate subspace at each
geometry, which a plain |<e_i|e_j>|^2 is not.

    python scripts/mode_tracking.py --a runs/delB/B0/dynmat_fix --b runs/delB/B1/artifact/clean_scf
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from qe_dynmat_out import parse_eigenvectors, parse_dynmat_freq_table

DEGEN_TOL_CM1 = 0.5
N_ATOMS = 10


def group_degenerate(freqs_cm1, tol=DEGEN_TOL_CM1):
    order = sorted(range(len(freqs_cm1)), key=lambda i: freqs_cm1[i])
    groups = []
    cur = [order[0]]
    for idx in order[1:]:
        if abs(freqs_cm1[idx] - freqs_cm1[cur[-1]]) <= tol:
            cur.append(idx)
        else:
            groups.append(cur)
            cur = [idx]
    groups.append(cur)
    return groups


def subspace_overlap(eigvecs_a, group_a, eigvecs_b, group_b) -> float:
    Ea = eigvecs_a[group_a]  # (dA, 3N)
    Eb = eigvecs_b[group_b]  # (dB, 3N)
    S = Ea.conj() @ Eb.T  # (dA, dB) overlap matrix
    trace_PaPb = float(np.sum(np.abs(S) ** 2))
    return trace_PaPb / min(len(group_a), len(group_b))


def load(dir_path: str):
    d = Path(dir_path)
    freq_table_path = d / "dynmat.out"
    fileig_path = d / "dynmat.eig.out"
    eig = parse_eigenvectors(fileig_path, n_atoms=N_ATOMS)
    ft = parse_dynmat_freq_table(freq_table_path) if freq_table_path.exists() else None
    return eig["freqs_cm1"], eig["eigvecs"], ft


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="directory with dynmat.out + dynmat.eig.out (reference, e.g. B0)")
    ap.add_argument("--b", required=True, help="directory with dynmat.out + dynmat.eig.out (candidate, e.g. B1)")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    freqs_a, vecs_a, ft_a = load(args.a)
    freqs_b, vecs_b, ft_b = load(args.b)

    groups_a = group_degenerate(freqs_a)
    groups_b = group_degenerate(freqs_b)

    rows = []
    for ga in groups_a:
        fa = np.mean([freqs_a[i] for i in ga])
        scores = [(gb, subspace_overlap(vecs_a, ga, vecs_b, gb)) for gb in groups_b]
        best_gb, best_score = max(scores, key=lambda t: t[1])
        fb = np.mean([freqs_b[i] for i in best_gb])
        rows.append(dict(
            a_modes=",".join(str(i + 1) for i in ga), a_freq_cm1=round(fa, 3), a_degeneracy=len(ga),
            b_modes=",".join(str(i + 1) for i in best_gb), b_freq_cm1=round(fb, 3), b_degeneracy=len(best_gb),
            overlap=round(best_score, 4),
            ambiguous=(len(scores) > 1 and sorted((s for _, s in scores), reverse=True)[0] -
                       sorted((s for _, s in scores), reverse=True)[1] < 0.1) if len(scores) > 1 else False,
        ))

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"wrote {args.out}")

    print(f"{args.label_a} ({len(freqs_a)} modes, {len(groups_a)} groups) -> "
          f"{args.label_b} ({len(freqs_b)} modes, {len(groups_b)} groups)")
    for r in rows:
        flag = "  <-- AMBIGUOUS" if r["ambiguous"] else ""
        print(f"  {args.label_a} modes {r['a_modes']:>6s} ({r['a_freq_cm1']:+9.3f} cm-1, deg={r['a_degeneracy']}) "
              f"-> {args.label_b} modes {r['b_modes']:>6s} ({r['b_freq_cm1']:+9.3f} cm-1, deg={r['b_degeneracy']}) "
              f"overlap={r['overlap']:.4f}{flag}")


if __name__ == "__main__":
    main()
