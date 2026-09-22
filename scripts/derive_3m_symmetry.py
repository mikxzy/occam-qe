"""Derive, from first principles, the symmetry-allowed pattern of a 3rd-rank tensor
r_ijk (symmetric in i,j -- the electro-optic/piezoelectric tensor family) under point
group 3m (C3v): build the 6 group elements as exact 3x3 orthogonal matrices, impose
invariance as a linear system on the 18 independent (i<=j) components, solve the null
space symbolically (exact, not numerical -- avoids rounding artifacts from cos(120deg)/
sin(120deg)). Used for DEL C, C5 (results/eo_symmetry_check.md) instead of trusting a
textbook table from memory.

    python scripts/derive_3m_symmetry.py
"""
from __future__ import annotations
from sympy import Matrix, Rational, sqrt, simplify, eye

AXES = "xyz"


def build_c3v_group():
    c, s = Rational(-1, 2), sqrt(3) / 2
    C3 = Matrix([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    sigma_v = Matrix([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])  # mirror, normal along x

    ops = [eye(3)]

    def add(op):
        for o in ops:
            if o == op:
                return
        ops.append(op)

    frontier = [C3, sigma_v]
    while frontier:
        for f in frontier:
            add(f)
        new_frontier = []
        for a in list(ops):
            for b in list(ops):
                p = simplify(a * b)
                before = len(ops)
                add(p)
                if len(ops) > before:
                    new_frontier.append(p)
        frontier = new_frontier
    return ops


def solve_invariant_tensor(ops):
    idx_sym = [(i, j, k) for i in range(3) for j in range(i, 3) for k in range(3)]
    n = len(idx_sym)
    slot = {}
    for m, (i, j, k) in enumerate(idx_sym):
        slot[(i, j, k)] = m
        slot[(j, i, k)] = m

    rows = []
    for R in ops:
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
    return idx_sym, A.nullspace()


def voigt(i, j):
    if i == j:
        return i + 1
    return {(1, 2): 4, (0, 2): 5, (0, 1): 6}[tuple(sorted((i, j)))]


def main():
    ops = build_c3v_group()
    print(f"group order: {len(ops)} (expect 6 for point group 3m / C3v)")
    idx_sym, ns = solve_invariant_tensor(ops)
    print(f"independent components: {len(ns)}\n")
    for p, v in enumerate(ns):
        terms = [(idx_sym[i], v[i]) for i in range(len(idx_sym)) if simplify(v[i]) != 0]
        readable = [f"r_{voigt(i,j)}{AXES[k]} = {val}" for (i, j, k), val in terms]
        print(f"parameter {chr(65+p)}: " + ",  ".join(readable))


if __name__ == "__main__":
    main()
