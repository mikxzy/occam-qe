"""Parse Born effective charges (Z*) from ph.out's "Effective charges (d Force / dE)"
blocks. ph.x prints this twice (once mid-run, once in the final summary); this uses the
LAST occurrence of each (without-ASR, with-ASR) block, the converged values.
"""
from __future__ import annotations
import re
from pathlib import Path

ATOM_BLOCK_RE = re.compile(
    r"atom\s+(\d+)\s+(\S+)\s+Mean Z\*:\s+(-?\d+\.\d+)\s*\n"
    r"\s*E\*?x\s*\(\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*\)\s*\n"
    r"\s*E\*?y\s*\(\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*\)\s*\n"
    r"\s*E\*?z\s*\(\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*\)"
)


def _parse_block(block_text: str) -> list[dict]:
    atoms = []
    for m in ATOM_BLOCK_RE.finditer(block_text):
        idx, el, mean_z = int(m.group(1)), m.group(2), float(m.group(3))
        nums = [float(x) for x in m.groups()[3:]]
        tensor = [nums[0:3], nums[3:6], nums[6:9]]
        atoms.append(dict(atom=idx, element=el, mean_zstar=mean_z, tensor=tensor))
    return atoms


def parse_born_charges(ph_out_path) -> dict:
    txt = Path(ph_out_path).read_text(errors="ignore")

    without_asr_sections = list(re.finditer(
        r"Effective charges \(d Force / dE\) in cartesian axis without acoustic sum rule applied \(asr\)\s*\n(.*?)(?=\n\s*Effective charges Sum)",
        txt, flags=re.S))
    with_asr_sections = list(re.finditer(
        r"Effective charges \(d Force / dE\) in cartesian axis with asr applied:\s*\n(.*?)(?=\n\n|\Z)",
        txt, flags=re.S))

    without_asr = _parse_block(without_asr_sections[-1].group(1)) if without_asr_sections else []
    with_asr = _parse_block(with_asr_sections[-1].group(1)) if with_asr_sections else []

    return dict(without_asr=without_asr, with_asr=with_asr)
