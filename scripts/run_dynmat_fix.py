"""One-off: run dynmat.x on an already-computed mat.dyn (committed at the given path) with
the corrected &input namelist (filout/fileig, not the invalid 'fileout' used in the first
B0 attempt). Avoids re-running the expensive pw.x+ph.x stages just to fix a namelist typo.

    python scripts/run_dynmat_fix.py --dir runs/delB/B0/dynmat_fix
"""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    d = Path(a.dir)
    fildyn = next((f for f in ["mat.dyn", "mat.dyn1"] if (d / f).exists()), None)
    if not fildyn:
        raise SystemExit(f"no mat.dyn found in {d}")
    (d / "dynmat.in").write_text(
        f"&input\n  fildyn='{fildyn}'\n  asr='crystal'\n  filout='dynmat.freq.out'\n  fileig='dynmat.eig.out'\n/\n",
        newline="\n")
    rc = subprocess.run(f'cd "{d}" && dynmat.x -in dynmat.in > dynmat.out 2> dynmat.err', shell=True).returncode
    print(f"dynmat.x exit code: {rc}")


if __name__ == "__main__":
    main()
