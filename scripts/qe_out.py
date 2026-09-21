"""Minimal, numpy-only `pw.out` parser for the DEL A SCF convergence series
(total energy, stress tensor + pressure, SCF convergence/iteration count).
Adapted from the equivalent parser used for Level-C Test 4B.
"""
from __future__ import annotations
import re
from pathlib import Path

import numpy as np


def parse_pwout(path) -> dict:
    txt = Path(path).read_text(errors="ignore")
    energies = [float(x) for x in re.findall(r"^!\s+total energy\s+=\s+(-?\d+\.\d+) Ry", txt, flags=re.M)]
    stress = None
    pressure = None
    m = re.search(r"total\s+stress\s+\(Ry/bohr\*\*3\)\s+\(kbar\)\s+P=\s*(-?\d+\.\d+)\n((?:.*\n){3})", txt)
    if m:
        pressure = float(m.group(1))
        stress = np.array([[float(v) for v in l.split()[3:6]] for l in m.group(2).strip().splitlines()]).tolist()
    n_iter = len(re.findall(r"^\s*total cpu time spent up to now is", txt, flags=re.M))
    converged = "convergence has been achieved" in txt and "JOB DONE" in txt
    return dict(
        energies_Ry=energies,
        E_final_Ry=energies[-1] if energies else None,
        stress_final=stress,
        pressure_kbar=pressure,
        converged=converged,
        job_done="JOB DONE" in txt,
        n_scf_iterations=n_iter,
    )
