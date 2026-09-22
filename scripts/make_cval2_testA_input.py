"""DEL C-VAL2, TEST A: freeze an isolated elop job (epsil+elop only, trans=.false.,
zeu=.false.) on the exact same LDA-relaxed geometry/pseudopotentials/cutoff/k-grid/
tr2_ph as the existing trans=.true. run, to test whether combining elop with the
phonon/Born-charge machinery changes the electronic-only result.

    python scripts/make_cval2_testA_input.py
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PWIN = ROOT / "runs" / "delC" / "C3_LDA" / "vcrelax" / "artifact" / "clean_scf" / "pw.in"
OUT_DIR = ROOT / "runs" / "delC" / "CVAL2_testA_isolated_elop"
QUEUE = ROOT / "queue" / "delC_jobs.json"

PH_IN = "Isolated elop test: epsil+elop only, trans=.false. (TEST A, C-VAL2)\n&inputph\n   prefix   = 'linbo3lda'\n   outdir   = './tmp/'\n   fildyn   = 'mat.dyn'\n   epsil    = .true.\n   trans    = .false.\n   zeu      = .false.\n   elop     = .true.\n   tr2_ph   = 1.0d-14\n/\n0.0 0.0 0.0\n"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    text = SRC_PWIN.read_text()  # byte-identical geometry/pseudopotentials/cutoff/k-grid
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "pw.in").write_text(text, newline="\n")
    (OUT_DIR / "ph.in").write_text(PH_IN, newline="\n")
    assert sha256(OUT_DIR / "pw.in") == sha256(SRC_PWIN), "pw.in must be byte-identical to the C3_vcrelax clean_scf input"

    jobs = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}
    jobs["CVAL2_testA_isolated_elop"] = dict(
        dir=str(OUT_DIR.relative_to(ROOT)).replace("\\", "/"), calc="scf+dfpt-gamma-elop-only-lda",
        pwin_sha256=sha256(OUT_DIR / "pw.in"), phin_sha256=sha256(OUT_DIR / "ph.in"),
        note="C-VAL2 TEST A: identical geometry/pseudopotentials/cutoff/k-grid/tr2_ph to "
             "C3_vcrelax's clean_scf+DFPT, but trans=.false. zeu=.false. -- isolates elop from the phonon/Z* machinery",
    )
    QUEUE.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT_DIR}, registered CVAL2_testA_isolated_elop")
    print(f"  pw.in sha256: {jobs['CVAL2_testA_isolated_elop']['pwin_sha256']}")


if __name__ == "__main__":
    main()
