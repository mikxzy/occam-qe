# DEL C, C8 — what the computed dielectric values can and cannot say about n at 1550 nm

## What was actually computed

Every ε tensor in this project (DEL A/B/C, all branches) comes from `ph.x` with
`epsil=.true.`, which is a **static (ω→0) linear-response DFPT quantity**: the electronic
(clamped-ion, since these are `epsil` calculations on a single fixed geometry, not
`fpol`) dielectric response in the zero-frequency limit. This is **not**:

* the finite-frequency optical dielectric function ε(ω) at 0.8 eV / 1550 nm (that needs
  `epsilon.x`, per DEL A's original task Del H — not run in DEL C), and
* the "clamped-ion high-frequency" ε∞ some EO literature uses as a separate named
  quantity (this DFPT `epsil` result already is the electronic/clamped-ion piece — no
  ionic/phonon contribution to ε is included at any q≠0 or finite-ω dispersion has been
  probed).

## Explicit rule for this project

**Do not compute `n = sqrt(epsilon_static)` and call it the 1550 nm refractive index.**
The static DFPT ε (used throughout C0-C13 for the r_ijk = -(dε/dE)/(ε_ii ε_jj) conversion)
is the correct, self-consistent object to combine with the *equally static* dε/dE from
`elop` — that internal consistency is what makes r_ijk meaningful as a DC/low-frequency
Pockels coefficient. But that same ε value is **not** validated as an estimate of the
1550 nm optical index, because:

1. LiNbO3-family materials are known to show meaningful dielectric dispersion between
   ω=0 and the near-IR/visible range (the static ε includes ionic/lattice polarization
   response that optical-frequency light does not have time to follow — though note
   again, THIS calculation's ε is already electronic/clamped-ion only, so the concern
   here is dispersion *within the electronic response itself* between ω=0 and 0.8 eV,
   which is a real, separate effect DFPT-at-ω=0 does not capture).
2. PBEsol/LDA both have well-documented band-gap underestimation, which systematically
   biases any frequency-dependent ε(ω) computed at the bare DFT level near the gap
   (0.8 eV is far from either functional's underestimated gap for this material class,
   so this specific concern is milder here than for near-gap probes, but it is not zero
   and was not quantified).

## What would be required

A proper 1550 nm value needs `epsilon.x` (frequency-dependent dielectric function,
independent-particle/RPA level, per DEL A's original DEL H task) run on whichever
geometry/XC combination is judged appropriate (this raises its own version of the
PBEsol-vs-LDA question from C1-C3, since `epsilon.x` has no documented elop-style
functional restriction but was never tested here) — **not performed in DEL C**. Until
then, every ε value in this project's results files should be read strictly as "static
DFPT dielectric constant," never silently equated with an optical refractive index.
