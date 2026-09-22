"""DEL C, C13: freeze a tighter-k-grid (6x6x6, vs production 4x4x4) EO job on the
LDA-relaxed geometry, to test H0-C3 (EO coefficients converge <2% under a tighter
numerical setting). Structure copied verbatim from C3_vcrelax's clean_scf/pw.in.

    python scripts/make_delC_c13_input.py
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PWIN = ROOT / "runs" / "delC" / "C3_LDA" / "vcrelax" / "artifact" / "clean_scf" / "pw.in"
OUT_DIR = ROOT / "runs" / "delC" / "C13_k6"
QUEUE = ROOT / "queue" / "delC_jobs.json"

PH_IN = "Gamma-point DFPT: dielectric + Born charges + phonons + electro-optic tensor (LDA, k=6x6x6 convergence check)\n&inputph\n   prefix   = 'linbo3lda'\n   outdir   = './tmp/'\n   fildyn   = 'mat.dyn'\n   epsil    = .true.\n   trans    = .true.\n   zeu      = .true.\n   elop     = .true.\n   tr2_ph   = 1.0d-14\n/\n0.0 0.0 0.0\n"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    text = SRC_PWIN.read_text()
    text_k6 = re.sub(r"K_POINTS automatic\n4 4 4 0 0 0", "K_POINTS automatic\n6 6 6 0 0 0", text)
    assert "6 6 6 0 0 0" in text_k6 and text_k6 != text, "k-grid substitution failed"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "pw.in").write_text(text_k6, newline="\n")
    (OUT_DIR / "ph.in").write_text(PH_IN, newline="\n")

    jobs = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}
    jobs["C13_k6"] = dict(dir=str(OUT_DIR.relative_to(ROOT)).replace("\\", "/"),
                           calc="scf+dfpt-gamma-zeu-elop-lda-k6",
                           pwin_sha256=sha256(OUT_DIR / "pw.in"), phin_sha256=sha256(OUT_DIR / "ph.in"),
                           note="LDA-relaxed geometry (C3_vcrelax), k=6x6x6 vs production 4x4x4, for H0-C3")
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT_DIR}, registered C13_k6")
    print(f"  pw.in sha256: {jobs['C13_k6']['pwin_sha256']}")


if __name__ == "__main__":
    main()
