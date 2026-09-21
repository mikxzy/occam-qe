"""QE `ph.x` Gamma-point DFPT input template (epsil + trans -> dielectric tensor +
Gamma phonon frequencies). Shared by scripts/make_dfpt_matrix.py.
"""
from __future__ import annotations

TEMPLATE = """\
Gamma-point DFPT: dielectric tensor + phonon frequencies
&inputph
   prefix   = 'linbo3'
   outdir   = './tmp/'
   fildyn   = 'mat.dyn'
   epsil    = .true.
   trans    = .true.
   tr2_ph   = 1.0d-14
/
0.0 0.0 0.0
"""


def render() -> str:
    return TEMPLATE
