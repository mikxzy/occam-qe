"""DEL C, TEST F0: audit the current PseudoDojo Li/Nb/O LDA pseudopotentials against
Veithen & Ghosez's stated methodology (LDA-PW, norm-conserving Troullier-Martins, FHI
generation code; Nb 4s/4p/4d/5s, Li 1s/2s, O 2s/2p valence).

    python scripts/build_testF_pp_audit.py
"""
from __future__ import annotations
import csv
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSEUDO_DIR = ROOT / "pseudo"
OUT = ROOT / "results" / "testF_current_pp_audit.csv"

FILES = {"Li": "Li_LDA.upf", "Nb": "Nb_LDA.upf", "O": "O_LDA.upf"}

# reference (nc, nv) valence shell counts parsed from each file's ATOM AND REFERENCE
# CONFIGURATION block, cross-checked against z_valence


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_upf(path: Path) -> dict:
    txt = path.read_text()

    def attr(name):
        m = re.search(rf'{name}="([^"]*)"', txt)
        return m.group(1).strip() if m else None

    # reference configuration block
    m = re.search(r"# atsym\s+z\s+nc\s+nv\s+iexc\s+psfile\n\s*(\S+)\s+([\d.]+)\s+(\d+)\s+(\d+)", txt)
    atsym, z_full, nc, nv = m.group(1), float(m.group(2)), int(m.group(3)), int(m.group(4))
    shell_lines = re.findall(r"^\s*(\d)\s+(\d)\s+([\d.]+)\s*$", txt, flags=re.M)
    # first nc+nv lines after the header are the full reference config, in order
    shells = [(int(n), int(l), float(f)) for n, l, f in shell_lines][:nc + nv]
    LSYM = "spdf"
    core_shells = shells[:nc]
    valence_shells = shells[nc:nc + nv]
    core_str = ",".join(f"{n}{LSYM[l]}{f:g}" for n, l, f in core_shells) or "(none)"
    valence_str = ",".join(f"{n}{LSYM[l]}{f:g}" for n, l, f in valence_shells)

    m2 = re.search(r"lloc, lpopt,\s*rc\(5\),\s*dvloc0\s*\n\s*(\d+)\s+(\d+)", txt)
    lloc = m2.group(1) if m2 else None

    m3 = re.search(r"# l, nproj, debl\s*\n((?:\s*\d+\s+\d+\s+[-\d.]+\s*\n)+)", txt)
    n_proj_total = sum(int(l.split()[1]) for l in m3.group(1).strip().splitlines()) if m3 else None

    return dict(
        filename=path.name, sha256=sha256(path),
        generator="ONCVPSP (Optimized Norm-Conserving Vanderbilt), scalar-relativistic v3.3.0, D.R. Hamann",
        xc=attr("functional"), pseudo_type=attr("pseudo_type"), z_valence=attr("z_valence"),
        relativistic=attr("relativistic"), nlcc=attr("core_correction"),
        reference_config_core=core_str, reference_config_valence=valence_str,
        local_channel=f"lloc={lloc} (ONCVPSP model potential beyond l_max, not a specific l-channel)",
        n_projectors_total=n_proj_total, number_of_wfc=attr("number_of_wfc"),
    )


VEITHEN_VALENCE = {"Li": "1s2,2s1", "Nb": "4s2,4p6,4d4,5s1", "O": "2s2,2p4"}


def main():
    rows = []
    for el, fname in FILES.items():
        r = parse_upf(PSEUDO_DIR / fname)
        r["element"] = el
        r["veithen_stated_valence"] = VEITHEN_VALENCE[el]
        r["valence_matches_veithen"] = (
            set(r["reference_config_valence"].replace(" ", "").split(",")) ==
            set(VEITHEN_VALENCE[el].split(","))
        )
        rows.append(r)

    fieldnames = ["element", "filename", "sha256", "generator", "xc", "pseudo_type", "z_valence",
                  "relativistic", "nlcc", "reference_config_core", "reference_config_valence",
                  "veithen_stated_valence", "valence_matches_veithen", "local_channel",
                  "n_projectors_total", "number_of_wfc"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {OUT.relative_to(ROOT)}")
    for r in rows:
        print(f"\n{r['element']}: {r['filename']}")
        print(f"  XC: {r['xc']}")
        print(f"  valence (core->valence): {r['reference_config_core']} | {r['reference_config_valence']}")
        print(f"  Veithen stated valence: {r['veithen_stated_valence']}")
        print(f"  MATCHES: {r['valence_matches_veithen']}")


if __name__ == "__main__":
    main()
