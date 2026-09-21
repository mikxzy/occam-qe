"""Deterministic CIF -> QE `pw.x` structure block, via ASE (CIF parsing + symmetry
expansion from the CIF's own symop list) and spglib (primitive-cell reduction).

No coordinates are invented: everything traces back to the CIF's asymmetric unit +
documented symmetry operators. Re-running this script on an unmodified CIF must
reproduce byte-identical output (used by scripts/make_convergence_matrix.py to freeze
pw.in files with a checkable sha256).

    python scripts/cif_to_qe.py structures/material_A_R3c_COD1541936.cif [--conventional]

Requires: ase, spglib (see requirements.txt).
"""
from __future__ import annotations
import argparse
import sys

import numpy as np
import ase.io
import spglib
from ase.data import chemical_symbols, atomic_masses

SPECIES_ORDER = ["Li", "Nb", "O"]
PSEUDO_FILE = {"Li": "Li.upf", "Nb": "Nb.upf", "O": "O.upf"}


def load_primitive(cif_path: str, symprec: float = 1e-4):
    atoms = ase.io.read(cif_path)
    cell = (atoms.cell[:], atoms.get_scaled_positions(), atoms.get_atomic_numbers())
    dataset = spglib.get_symmetry_dataset(cell, symprec=symprec)
    plattice, ppositions, pnumbers = spglib.find_primitive(cell, symprec=symprec)
    pdataset = spglib.get_symmetry_dataset((plattice, ppositions, pnumbers), symprec=symprec)
    if pdataset.number != dataset.number:
        raise RuntimeError(
            f"space group changed under primitive-cell reduction: "
            f"{dataset.international} (#{dataset.number}) -> "
            f"{pdataset.international} (#{pdataset.number})"
        )
    syms = [chemical_symbols[z] for z in pnumbers]
    order = sorted(range(len(syms)), key=lambda i: SPECIES_ORDER.index(syms[i]))
    syms = [syms[i] for i in order]
    positions = [ppositions[i] % 1.0 for i in order]
    return dict(
        space_group=dataset.international,
        space_group_number=dataset.number,
        lattice=np.asarray(plattice),
        symbols=syms,
        positions=positions,
        n_atoms_conventional=len(atoms),
    )


def load_conventional(cif_path: str):
    atoms = ase.io.read(cif_path)
    syms = atoms.get_chemical_symbols()
    order = sorted(range(len(syms)), key=lambda i: SPECIES_ORDER.index(syms[i]))
    syms = [syms[i] for i in order]
    positions = [p % 1.0 for p in atoms.get_scaled_positions()[order]]
    return dict(lattice=atoms.cell[:], symbols=syms, positions=positions)


def render_qe_blocks(lattice, symbols, positions) -> str:
    lines = ["CELL_PARAMETERS angstrom"]
    for v in lattice:
        lines.append(f"{v[0]: .10f} {v[1]: .10f} {v[2]: .10f}")
    lines.append("")
    lines.append("ATOMIC_SPECIES")
    for el in SPECIES_ORDER:
        if el in symbols:
            mass = atomic_masses[chemical_symbols.index(el)]
            lines.append(f"{el} {mass:.5f} {PSEUDO_FILE[el]}")
    lines.append("")
    lines.append("ATOMIC_POSITIONS crystal")
    for s, p in zip(symbols, positions):
        lines.append(f"{s} {p[0]: .10f} {p[1]: .10f} {p[2]: .10f}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cif_path")
    ap.add_argument("--conventional", action="store_true",
                     help="emit the 30-atom hexagonal cell as deposited, instead of the "
                          "10-atom spglib-reduced primitive cell")
    a = ap.parse_args()

    if a.conventional:
        d = load_conventional(a.cif_path)
        sys.stdout.write(render_qe_blocks(d["lattice"], d["symbols"], d["positions"]))
    else:
        d = load_primitive(a.cif_path)
        print(f"# space group (re-verified by spglib): {d['space_group']} #{d['space_group_number']}",
              file=sys.stderr)
        print(f"# {d['n_atoms_conventional']} atoms (conventional) -> {len(d['symbols'])} atoms (primitive)",
              file=sys.stderr)
        sys.stdout.write(render_qe_blocks(d["lattice"], d["symbols"], d["positions"]))


if __name__ == "__main__":
    main()
