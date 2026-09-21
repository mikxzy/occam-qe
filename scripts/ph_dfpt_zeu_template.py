"""QE `ph.x` Gamma DFPT template for DEL B: epsil + trans + zeu (Born effective charges),
used identically for B0/B1/B2 so the comparison is apples-to-apples (task instruction).
Differs from DEL A's scripts/ph_dfpt_template.py only by zeu=.true.
"""
from __future__ import annotations

TEMPLATE = """\
Gamma-point DFPT: dielectric tensor + Born effective charges + phonon frequencies
&inputph
   prefix   = 'linbo3'
   outdir   = './tmp/'
   fildyn   = 'mat.dyn'
   epsil    = .true.
   trans    = .true.
   zeu      = .true.
   tr2_ph   = 1.0d-14
/
0.0 0.0 0.0
"""


def render() -> str:
    return TEMPLATE
