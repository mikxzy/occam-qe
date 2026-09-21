"""Extract CELL_PARAMETERS / ATOMIC_SPECIES / ATOMIC_POSITIONS / K_POINTS blocks verbatim
from an existing, already-frozen `pw.in` -- used by DEL B to reuse the exact DEL A
production structure without ever re-deriving it from the CIF (per instruction).
"""
from __future__ import annotations
import re
from pathlib import Path


def extract_blocks(pw_in_path) -> dict:
    txt = Path(pw_in_path).read_text()

    def block(tag, next_tags):
        pat = rf"^{tag}.*?\n((?:.*\n)+?)(?=^(?:{'|'.join(next_tags)})|\Z)"
        m = re.search(pat, txt, flags=re.M)
        if not m:
            raise ValueError(f"block {tag!r} not found in {pw_in_path}")
        return m.group(0).rstrip("\n") + "\n"

    cell = block("CELL_PARAMETERS", ["ATOMIC_SPECIES", "ATOMIC_POSITIONS", "K_POINTS"])
    species = block("ATOMIC_SPECIES", ["CELL_PARAMETERS", "ATOMIC_POSITIONS", "K_POINTS"])
    positions = block("ATOMIC_POSITIONS", ["CELL_PARAMETERS", "ATOMIC_SPECIES", "K_POINTS"])
    kpoints = block("K_POINTS", ["CELL_PARAMETERS", "ATOMIC_SPECIES", "ATOMIC_POSITIONS"])

    nat = len(re.findall(r"^\S+\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+", positions.split("\n", 1)[1], flags=re.M))
    ntyp = len(re.findall(r"^\S+\s+[\d.]+\s+\S+\.upf", species.split("\n", 1)[1], flags=re.M))

    return dict(cell_block=cell, species_block=species, positions_block=positions,
                kpoints_block=kpoints, nat=nat, ntyp=ntyp)


if __name__ == "__main__":
    import sys
    d = extract_blocks(sys.argv[1])
    print(f"nat={d['nat']} ntyp={d['ntyp']}")
    print(d["cell_block"], end="")
    print(d["species_block"], end="")
    print(d["positions_block"], end="")
    print(d["kpoints_block"], end="")
