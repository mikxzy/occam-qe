"""Parsers for dynmat.x output:
  - dynmat.out's "# mode [cm-1] [THz] IR" table -> ASR-corrected frequencies + IR activity
  - the `fileig` file -> ASR-corrected, orthogonal phonon eigenvectors (complex, per mode)
"""
from __future__ import annotations
import re
from pathlib import Path

import numpy as np


def parse_dynmat_freq_table(dynmat_out_path) -> dict:
    txt = Path(dynmat_out_path).read_text(errors="ignore")
    rows = re.findall(r"^\s*(\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$", txt, flags=re.M)
    modes = [dict(mode=int(m), freq_cm1_asr=float(f_cm1), freq_thz_asr=float(f_thz), ir_activity=float(ir))
             for m, f_cm1, f_thz, ir in rows]
    return dict(modes=modes, n_modes=len(modes))


def parse_eigenvectors(fileig_path, n_atoms: int) -> dict:
    """Returns freqs_cm1 (list) and eigvecs: complex ndarray shape (n_modes, 3*n_atoms)."""
    txt = Path(fileig_path).read_text(errors="ignore")
    blocks = re.split(r"freq\s*\(\s*(\d+)\)\s*=\s*(-?\d+\.\d+)\s*\[THz\]\s*=\s*(-?\d+\.\d+)\s*\[cm-1\]", txt)
    # blocks[0] is preamble; then repeating groups of (mode_idx, thz, cm1, body_text)
    freqs_cm1 = []
    eigvecs = []
    for i in range(1, len(blocks), 4):
        mode_idx, thz, cm1, body = blocks[i], blocks[i + 1], blocks[i + 2], blocks[i + 3]
        freqs_cm1.append(float(cm1))
        nums = [float(x) for x in re.findall(r"-?\d+\.\d+", body)][: 6 * n_atoms]
        if len(nums) < 6 * n_atoms:
            raise ValueError(f"mode {mode_idx}: expected {6*n_atoms} numbers, found {len(nums)}")
        re_im = np.array(nums).reshape(n_atoms, 3, 2)
        vec = (re_im[:, :, 0] + 1j * re_im[:, :, 1]).reshape(3 * n_atoms)
        eigvecs.append(vec)
    return dict(freqs_cm1=freqs_cm1, eigvecs=np.array(eigvecs))
