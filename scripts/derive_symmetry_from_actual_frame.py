"""DEL C-VAL, C-VAL3/C-VAL4: derive the symmetry-allowed EO tensor pattern using the
ACTUAL Cartesian symmetry operations of Material A's primitive cell (from spglib),
in QE's ACTUAL Cartesian frame (as printed in CELL_PARAMETERS) -- not an assumed/
idealized "mirror normal along x" frame. This settles whether QE's raw output frame
already coincides with the conventional 3m frame, or needs an explicit rotation.

    python scripts/derive_symmetry_from_actual_frame.py
"""
from __future__ import annotations
import numpy as np
import ase.io
import spglib
from sympy import Matrix, nsimplify, simplify

CIF = "structures/material_A_R3c_COD1541936.cif"


def get_cartesian_ops():
    atoms = ase.io.read(CIF)
    cell = (atoms.cell[:], atoms.get_scaled_positions(), atoms.get_atomic_numbers())
    plattice, ppositions, pnumbers = spglib.find_primitive(cell, symprec=1e-4)
    plattice = np.array(plattice)
    ds = spglib.get_symmetry_dataset((plattice, ppositions, pnumbers), symprec=1e-4)
    L = plattice.T
    Linv = np.linalg.inv(L)
    ops_cart = [L @ R @ Linv for R in ds.rotations]
    return ops_cart, ds


def solve_invariant_tensor(ops_cart):
    idx_sym = [(i, j, k) for i in range(3) for j in range(i, 3) for k in range(3)]
    n = len(idx_sym)
    slot = {}
    for m, (i, j, k) in enumerate(idx_sym):
        slot[(i, j, k)] = m
        slot[(j, i, k)] = m

    rows = []
    for Rnp in ops_cart:
        R = Matrix([[nsimplify(x, tolerance=1e-9, rational=True) for x in row] for row in Rnp.tolist()])
        for (i, j, k) in idx_sym:
            row = [0] * n
            row[slot[(i, j, k)]] -= 1
            for a in range(3):
                for b in range(3):
                    for c in range(3):
                        coeff = simplify(R[i, a] * R[j, b] * R[k, c])
                        if coeff != 0:
                            row[slot[(a, b, c)]] += coeff
            rows.append(row)
    A = Matrix(rows).applyfunc(simplify)
    ns = A.nullspace()
    return idx_sym, ns


AXES = "xyz"


def voigt(i, j):
    if i == j:
        return i + 1
    return {(1, 2): 4, (0, 2): 5, (0, 1): 6}[tuple(sorted((i, j)))]


def main():
    ops_cart, ds = get_cartesian_ops()
    print(f"space group: {ds.international} #{ds.number}, {len(ops_cart)} ops")
    for i, R in enumerate(ops_cart):
        print(f"\nop {i} (Cartesian, QE's actual frame):")
        print(np.round(R, 6))
        print(f"  det = {np.linalg.det(R):.4f}")

    idx_sym, ns = solve_invariant_tensor(ops_cart)
    print(f"\nindependent components in QE's actual raw frame: {len(ns)}")
    for p, v in enumerate(ns):
        terms = [(idx_sym[i], v[i]) for i in range(len(idx_sym)) if simplify(v[i]) != 0]
        readable = [f"r_{voigt(i,j)}{AXES[k]} = {val}" for (i, j, k), val in terms]
        print(f"parameter {chr(65+p)}: " + ",  ".join(readable))


if __name__ == "__main__":
    main()
