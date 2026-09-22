"""Freeze the C2 (PBEsol EO attempt) input: pw.in copied byte-identical from DEL B's B2
clean_scf (never re-derived), ph.in adds elop=.true. to the same epsil+trans+zeu block
used throughout DEL B, for apples-to-apples comparison with the already-known B2
dielectric/phonon result (C0).

    python scripts/make_delC_c2_input.py
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B2_PWIN = ROOT / "runs" / "delB" / "B2" / "artifact" / "clean_scf" / "pw.in"
OUT_DIR = ROOT / "runs" / "delC" / "C2_PBEsol_EO"
QUEUE = ROOT / "queue" / "delC_jobs.json"

PH_IN = """Gamma-point DFPT: dielectric + Born charges + phonons + electro-optic tensor
&inputph
   prefix   = 'linbo3'
   outdir   = './tmp/'
   fildyn   = 'mat.dyn'
   epsil    = .true.
   trans    = .true.
   zeu      = .true.
   elop     = .true.
   tr2_ph   = 1.0d-14
/
0.0 0.0 0.0
"""


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pw_text = B2_PWIN.read_text()
    (OUT_DIR / "pw.in").write_text(pw_text, newline="\n")
    (OUT_DIR / "ph.in").write_text(PH_IN, newline="\n")
    assert sha256(OUT_DIR / "pw.in") == sha256(B2_PWIN), "C2 pw.in must be byte-identical to B2's clean_scf/pw.in"

    jobs = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}
    jobs["C2_PBEsol_EO"] = dict(
        dir="runs/delC/C2_PBEsol_EO", calc="scf+dfpt-gamma-zeu-elop",
        pwin_sha256=sha256(OUT_DIR / "pw.in"), phin_sha256=sha256(OUT_DIR / "ph.in"),
        note="pw.in byte-identical to runs/delB/B2/artifact/clean_scf/pw.in",
    )
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT_DIR} and registered in {QUEUE.relative_to(ROOT)}")
    print(f"  pw.in sha256: {jobs['C2_PBEsol_EO']['pwin_sha256']}")
    print(f"  ph.in sha256: {jobs['C2_PBEsol_EO']['phin_sha256']}")


if __name__ == "__main__":
    main()
