"""Minimal, numpy-free `ph.out` parser: macroscopic dielectric tensor + Gamma phonon
frequencies (cm-1). QE prints imaginary frequencies as negative numbers.
"""
from __future__ import annotations
import re
from pathlib import Path


def parse_phout(path) -> dict:
    txt = Path(path).read_text(errors="ignore")

    eps = None
    m = re.search(r"Dielectric constant in cartesian axis\s*\n\s*\n((?:\s*\(.*\)\s*\n){3})", txt)
    if m:
        rows = []
        for line in m.group(1).strip().splitlines():
            nums = [float(x) for x in re.findall(r"-?\d+\.\d+", line)]
            rows.append(nums)
        eps = rows

    freqs_cm1 = [float(x) for x in re.findall(r"freq\s*\(\s*\d+\)\s*=\s*-?\d+\.\d+\s*\[THz\]\s*=\s*(-?\d+\.\d+)\s*\[cm-1\]", txt)]
    n_imaginary = sum(1 for f in freqs_cm1 if f < -5.0)  # Gamma acoustic modes are nominally 0 but commonly show a few cm-1 of numerical noise; -5 cm-1 separates that from a real instability

    ph_done = "PHONON" in txt and ("JOB DONE" in txt)
    converged = "convergence has been achieved" in txt or bool(freqs_cm1)

    return dict(
        epsilon_cartesian=eps,
        freqs_cm1=freqs_cm1,
        n_modes=len(freqs_cm1),
        n_imaginary=n_imaginary,
        job_done=ph_done,
        converged=converged,
    )
