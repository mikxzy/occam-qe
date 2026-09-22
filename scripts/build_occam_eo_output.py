"""DEL C, C14: build results/occam_material_A_eo.csv -- the validated parameter set for
transfer to the next simulation level. Primary source: LDA@LDA-relaxed (the only branch
that is simultaneously internally consistent -- geometry, pseudopotentials and EO method
all LDA -- AND Gamma-dynamically stable). Numerical uncertainty from C13 (k-grid
convergence, max 1.71%, reported conservatively as +/-2%).

    python scripts/build_occam_eo_output.py
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "occam_material_A_eo.csv"

FIELDNAMES = ["parameter", "tensor_indices", "conventional_name", "value", "units", "xc",
              "geometry", "method", "clamped_or_relaxed", "numerical_uncertainty",
              "symmetry_allowed", "usable_for_device_model", "notes"]

GEOM = "LDA-relaxed (C3_vcrelax, internally consistent LDA equilibrium)"
METHOD_EPS = "DFPT (epsil=.true.), static/zero-frequency, electronic (clamped-ion)"
METHOD_EO = "DFPT (elop=.true.), static/zero-frequency, electronic (clamped-ion) -- see C11"

ROWS = [
    dict(parameter="epsilon_xx", tensor_indices="xx", conventional_name="eps_xx = eps_yy",
         value=5.573331875, units="dimensionless (relative permittivity)", xc="LDA",
         geometry=GEOM, method=METHOD_EPS, clamped_or_relaxed="electronic/clamped-ion",
         numerical_uncertainty="not separately re-checked at k=6x6x6 for eps (only for r_ijk, C13); DEL A/B precedent (PBEsol) showed eps converges faster than stress/EO -- treat as <=1%",
         symmetry_allowed="n/a (diagonal by symmetry, confirmed)", usable_for_device_model="CONDITIONAL",
         notes="static DFPT value -- NOT the 1550nm optical index, see C8. Not the finite-frequency epsilon(0.8eV)."),
    dict(parameter="epsilon_zz", tensor_indices="zz", conventional_name="eps_zz",
         value=5.527594746, units="dimensionless (relative permittivity)", xc="LDA",
         geometry=GEOM, method=METHOD_EPS, clamped_or_relaxed="electronic/clamped-ion",
         numerical_uncertainty="see epsilon_xx row",
         symmetry_allowed="n/a (diagonal by symmetry, confirmed)", usable_for_device_model="CONDITIONAL",
         notes="static DFPT value -- NOT the 1550nm optical index, see C8."),
    dict(parameter="r22", tensor_indices="i=j=y, k=y (Voigt: mu=2,k=y)", conventional_name="r22 = -r12 = -r61",
         value=22.4675, units="pm/V", xc="LDA", geometry=GEOM, method=METHOD_EO,
         clamped_or_relaxed="electronic/clamped-ion ONLY (no ionic/lraman contribution, C11)",
         numerical_uncertainty="+/-2% (C13: k-grid convergence, largest observed 1.71% on r33; r22 itself 0.55%)",
         symmetry_allowed="True (class 3m/C3v)", usable_for_device_model="YES",
         notes="Gamma-dynamically stable geometry (0/30 imaginary modes). Most relaxation-sensitive coefficient: B0-geometry value differs by -35% (C12)."),
    dict(parameter="r13_r23", tensor_indices="i=j=x or y, k=z (Voigt: mu=1/2,k=z)", conventional_name="r13 = r23",
         value=35.0157, units="pm/V", xc="LDA", geometry=GEOM, method=METHOD_EO,
         clamped_or_relaxed="electronic/clamped-ion ONLY (no ionic/lraman contribution, C11)",
         numerical_uncertainty="+/-2% (C13: 1.07%)",
         symmetry_allowed="True (class 3m/C3v)", usable_for_device_model="YES",
         notes="B0-geometry value differs by -7.2% (C12) -- the least relaxation-sensitive of the 4."),
    dict(parameter="r51_r42", tensor_indices="i=x,j=z,k=x or i=y,j=z,k=y (Voigt: mu=5/4,k=x/y)", conventional_name="r51 = r42",
         value=35.3054, units="pm/V", xc="LDA", geometry=GEOM, method=METHOD_EO,
         clamped_or_relaxed="electronic/clamped-ion ONLY (no ionic/lraman contribution, C11)",
         numerical_uncertainty="+/-2% (C13: 0.66%)",
         symmetry_allowed="True (class 3m/C3v)", usable_for_device_model="YES",
         notes="B0-geometry value differs by -16.7% (C12)."),
    dict(parameter="r33", tensor_indices="i=j=k=z (Voigt: mu=3,k=z)", conventional_name="r33",
         value=33.0559, units="pm/V", xc="LDA", geometry=GEOM, method=METHOD_EO,
         clamped_or_relaxed="electronic/clamped-ion ONLY (no ionic/lraman contribution, C11)",
         numerical_uncertainty="+/-2% (C13: 1.71%, the largest of the 4 -- still under threshold)",
         symmetry_allowed="True (class 3m/C3v)", usable_for_device_model="YES",
         notes="Usually the device-relevant coefficient for a z-cut/extraordinary-axis TFLN modulator. B0-geometry value differs by +14.6% (C12)."),
]


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in ROWS:
            w.writerow(r)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(ROWS)} parameters)")


if __name__ == "__main__":
    main()
