"""Shared QE `pw.x` SCF input template for the DEL A numerical-convergence series.

Kept separate from make_convergence_matrix.py so the exact same template can later be
reused for DEL B (relaxation) and beyond without duplicating boilerplate.
"""
from __future__ import annotations

TEMPLATE = """\
&CONTROL
   calculation = 'scf'
   prefix      = 'linbo3'
   outdir      = './tmp/'
   pseudo_dir  = '/work/pseudo'
   tstress     = .true.
   tprnfor     = .true.
   verbosity   = 'high'
/
&SYSTEM
   ibrav       = 0
   nat         = 10
   ntyp        = 3
   ecutwfc     = {ecutwfc:.1f}
   ecutrho     = {ecutrho:.1f}
   occupations = 'fixed'
/
&ELECTRONS
   conv_thr    = 1.0d-10
   mixing_beta = 0.7d0
   electron_maxstep = 200
/
{structure_block}
K_POINTS automatic
{kx} {ky} {kz} 0 0 0
"""


def render(structure_block: str, ecutwfc: float, k: int) -> str:
    return TEMPLATE.format(
        structure_block=structure_block,
        ecutwfc=ecutwfc,
        ecutrho=4.0 * ecutwfc,  # standard NC/ONCVPSP dual
        kx=k, ky=k, kz=k,
    )
