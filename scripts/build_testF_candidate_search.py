"""DEL C, TEST F1: document the candidate-search results for a reference-parity
(Perdew-Wang LDA, norm-conserving Troullier-Martins, matching Veithen valence) Li/Nb/O
pseudopotential set.

    python scripts/build_testF_candidate_search.py
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "testF_candidate_pp_sets.csv"

ROWS = [
    dict(element="Nb", source="QE legacy table / fhi-pp-from-abinit-web-site (Nb.pw-mt_fhi.UPF)",
         generator="FHI98PP (fhi2upf.x converted)", xc="SLA-PW (Perdew-Wang LDA)",
         type="Troullier-Martins NC", z_valence=5, valence_config="5s2,5p0,4d3",
         veithen_valence="4s2,4p6,4d4,5s1", matches_veithen=False,
         note="THE ONLY LDA-PW Troullier-Martins/FHI Nb pseudopotential found on any "
              "publicly accessible table (checked: QE legacy pseudopotential site's "
              "fhi-pp-from-abinit-web-site mirror; ABINIT's own www.abinit.org "
              "lda_fhi table link is dead/404, GitHub Pages 404). Explicitly the SAME "
              "pseudopotential the task warned against using as a false-equivalent "
              "benchmark replacement -- confirmed by direct inspection, not assumed."),
    dict(element="Li", source="QE legacy table / fhi-pp-from-abinit-web-site (Li.pw-mt_fhi.UPF)",
         generator="FHI98PP (fhi2upf.x converted)", xc="SLA-PW (Perdew-Wang LDA)",
         type="Troullier-Martins NC", z_valence=1, valence_config="2s1,2p0",
         veithen_valence="1s2,2s1", matches_veithen=False,
         note="1s treated as frozen core (z_valence=1, only 2s in valence) -- Veithen "
              "explicitly used 1s+2s (z_valence=3, no frozen core for Li). Mismatch."),
    dict(element="O", source="QE legacy table / fhi-pp-from-abinit-web-site (O.pw-mt_fhi.UPF)",
         generator="FHI98PP (fhi2upf.x converted)", xc="SLA-PW (Perdew-Wang LDA)",
         type="Troullier-Martins NC", z_valence=6, valence_config="2s2,2p4",
         veithen_valence="2s2,2p4", matches_veithen=True,
         note="Matches Veithen's stated O valence exactly."),
    dict(element="(all)", source="Hartwigsen-Goedecker-Hutter (HGH) table, QE legacy site",
         generator="HGH separable pseudopotential formalism",
         xc="LDA available", type="HGH (NOT Troullier-Martins)", z_valence="varies",
         valence_config="n/a", veithen_valence="n/a", matches_veithen=False,
         note="Rejected as a candidate: fails the task's explicit Troullier-Martins "
              "requirement (a genuinely different NC pseudopotential formalism, not "
              "just a different parametrization of the same one) -- listed here to "
              "show it was considered and excluded on stated grounds, not overlooked."),
    dict(element="(all)", source="SIESTA 'Virtual Vault for Pseudopotentials' (3rd-party archive)",
         generator="unknown / unverified", xc="unverified", type="unverified",
         z_valence="unverified", valence_config="unverified", veithen_valence="n/a",
         matches_veithen="UNVERIFIED",
         note="Found via web search only; SIESTA no longer hosts an official psf "
              "database itself. Not inspected -- no UPF/psf file obtained, provenance "
              "and generation parameters not confirmed. Not usable as a citable "
              "reference-parity source without direct file inspection, which was not "
              "performed in this pass."),
]


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ROWS[0].keys()))
        w.writeheader()
        for r in ROWS:
            w.writerow(r)
    print(f"wrote {OUT.relative_to(ROOT)}")
    for r in ROWS:
        print(f"{r['element']:6s} matches_veithen={r['matches_veithen']}  {r['source']}")


if __name__ == "__main__":
    main()
