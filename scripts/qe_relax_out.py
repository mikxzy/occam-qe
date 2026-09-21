"""Parser for QE `relax`/`vc-relax` pw.out: per-iteration trajectory (energy, max force,
pressure, volume, cell parameters) and the final converged structure. Numpy-only,
adapted from the equivalent parser used for Level-C Test 4B.
"""
from __future__ import annotations
import re
from pathlib import Path

import numpy as np

RY_EV = 13.605693122994
BOHR_A = 0.529177210903
RYBOHR_EVA = RY_EV / BOHR_A


def parse_relax_out(path) -> dict:
    txt = Path(path).read_text(errors="ignore")

    # total energy per SCF-converged geometry step ("!    total energy = ... Ry")
    energies = [float(x) for x in re.findall(r"^!\s+total energy\s+=\s+(-?\d+\.\d+) Ry", txt, flags=re.M)]

    # max force per step: "Total force = ... Total SCF correction = ..." isn't max force;
    # use the per-atom force block and take max |F| for each step.
    max_forces_eVA = []
    for blk in re.findall(r"Forces acting on atoms \(cartesian axes, Ry/au\):\s*\n\n((?:\s+atom\s+\d+ type\s+\d+\s+force =\s+\S+\s+\S+\s+\S+\n)+)", txt):
        F = np.array([[float(v) for v in l.split("=")[1].split()] for l in blk.strip().splitlines()]) * RYBOHR_EVA
        max_forces_eVA.append(float(np.abs(F).max()))

    # pressure per step (vc-relax only): "P= ... kbar" on the "total stress" line
    pressures = [float(x) for x in re.findall(r"total\s+stress\s+\(Ry/bohr\*\*3\)\s+\(kbar\)\s+P=\s*(-?\d+\.\d+)", txt)]

    # cell volume per step (vc-relax only): "unit-cell volume          =     NNN.NNNN (a.u.)^3"
    volumes_bohr3 = [float(x) for x in re.findall(r"unit-cell volume\s+=\s+([\d.]+)\s*\(a\.u\.\)\^3", txt)]
    volumes_A3 = [v * BOHR_A ** 3 for v in volumes_bohr3]

    # final structure block
    fin = re.search(r"Begin final coordinates(.*?)End final coordinates", txt, flags=re.S)
    cell = frac = syms = final_volume_A3 = None
    if fin:
        s = fin.group(1)
        cm = re.search(r"CELL_PARAMETERS \(angstrom\)\n((?:.*\n){3})", s)
        if cm:
            cell = np.array([[float(v) for v in l.split()] for l in cm.group(1).strip().splitlines()])
        pm = re.search(r"ATOMIC_POSITIONS \(crystal\)\n((?:\s*\S+\s+\S+\s+\S+\s+\S+.*\n)+)", s)
        if pm:
            rows = [l.split() for l in pm.group(1).strip().splitlines()]
            syms = [r[0] for r in rows]
            frac = np.array([[float(v) for v in r[1:4]] for r in rows])
        if cell is not None:
            final_volume_A3 = float(abs(np.linalg.det(cell)))

    bfgs_converged = "bfgs converged" in txt or "Final scf calculation at the relaxed structure" in txt
    job_done = "JOB DONE" in txt

    return dict(
        energies_Ry=energies, E_final_Ry=energies[-1] if energies else None,
        max_forces_eV_A=max_forces_eVA, pressures_kbar=pressures,
        volumes_A3=volumes_A3,
        final_cell_A=cell, final_frac=frac, final_symbols=syms, final_volume_A3=final_volume_A3,
        bfgs_converged=bfgs_converged, job_done=job_done,
        n_steps=len(energies),
    )


def cellpar(lattice_A):
    """(a,b,c,alpha,beta,gamma) from 3x3 lattice vectors (angstrom, rows = vectors)."""
    import math
    lat = np.asarray(lattice_A)
    a, b, c = [float(np.linalg.norm(v)) for v in lat]

    def ang(u, v):
        return math.degrees(math.acos(float(np.dot(u, v)) / (np.linalg.norm(u) * np.linalg.norm(v))))
    alpha = ang(lat[1], lat[2])
    beta = ang(lat[0], lat[2])
    gamma = ang(lat[0], lat[1])
    return a, b, c, alpha, beta, gamma
