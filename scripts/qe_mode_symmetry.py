"""Parse ph.x's final "Mode symmetry, <point group>" table -- irreducible representation
label per mode (indices are 1-based and match dynmat.x's fileig numbering, since dynmat.x
re-diagonalizes the same physical mode set ASR only projects/corrects, it does not
reorder). Frequencies in this table are RAW (pre-ASR); only the irrep label is used here.
"""
from __future__ import annotations
import re
from pathlib import Path

MODE_LINE_RE = re.compile(
    r"freq[ \t]*\([ \t]*(\d+)-[ \t]*(\d+)\)[ \t]*=[ \t]*(-?\d+\.\d+)[ \t]*\[cm-1\][ \t]*-->[ \t]*(\S+)[ \t]+(\S+)[ \t]*(\S*)[ \t]*(?=\n|\Z)"
)


def parse_mode_symmetry(ph_out_path) -> dict:
    txt = Path(ph_out_path).read_text(errors="ignore")
    headers = list(re.finditer(r"Mode symmetry,\s*(.+?)\s*point group:", txt))
    if not headers:
        return dict(point_group=None, per_mode={})
    last = headers[-1]
    point_group = last.group(1).strip()
    tail = txt[last.end():]
    per_mode = {}
    for mm in MODE_LINE_RE.finditer(tail):
        i0, i1, freq, irrep, l_label, activity = mm.groups()
        for idx in range(int(i0), int(i1) + 1):
            per_mode[idx] = dict(irrep=irrep, l_label=l_label, activity=activity or None,
                                  raw_freq_cm1_table=float(freq))
    return dict(point_group=point_group, per_mode=per_mode)
