"""C-VAL4 Step 2 (post-processing): merge the DS4 (dielectric)/DS5 (3rd-order) DDB
files with mrgddb and run anaddb (dieflag=1, nlflag=1) to get ABINIT's own
authoritative electronic EO tensor directly -- no hand-derived d-to-chi2 conversion.

Expects abinit_pead_G1o_DS4_DDB and abinit_pead_G1o_DS5_DDB to already be present in
the job directory (committed to the repo from run_cval4_abinit_pead.py's artifact,
since that job's own ~5h runtime leaves no safe margin for this step too, given the
GH-hosted-runner 6h hard timeout).

mrgddb/anaddb input structure (files-file format, dummy placeholder files) copied
verbatim from ABINIT's own official tutorial test chain
(tests/tutorespfn/Input/tnlo_3.abi, tnlo_4.abi, tnlo_4.files), restricted to
dieflag+nlflag only since this DDB has no phonon/strain (rfphon/rfstrs) data -- only
the electronic contribution is being sought here, per instruction.

    python scripts/run_cval4_abinit_anaddb.py [--out artifacts/CVAL4_abinit_anaddb_G1]
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOB_DIR = ROOT / "runs" / "delC" / "CVAL4_code_parity" / "abinit_pead_G1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()

    d = JOB_DIR
    out = Path(a.out) if a.out else d / "artifact_anaddb"
    out.mkdir(parents=True, exist_ok=True)

    res = dict(started=time.strftime("%Y-%m-%dT%H:%M:%S"))

    ddb4 = d / "abinit_pead_G1o_DS4_DDB"
    ddb5 = d / "abinit_pead_G1o_DS5_DDB"
    ok = ddb4.exists() and ddb5.exists()
    res["ddb4_present"] = ddb4.exists()
    res["ddb5_present"] = ddb5.exists()
    res["preconditions_ok"] = ok
    if not ok:
        res["status"] = "FAILED"
        res["reason"] = "DS4_DDB or DS5_DDB not found in job directory"
        json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
        print(json.dumps(res, indent=1, default=str))
        sys.exit(4)

    for f in list(d.glob("mrgddb.*")) + list(d.glob("anaddb.*")) + list(d.glob("merged.ddb")):
        f.unlink()

    (d / "mrgddb.in").write_text(
        "merged.ddb\nC-VAL4 PEAD electronic-only: dielectric (DS4) + 3rd-order (DS5)\n2\n"
        "abinit_pead_G1o_DS4_DDB\nabinit_pead_G1o_DS5_DDB\n", newline="\n")
    pm = subprocess.run(f'cd "{d}" && mrgddb < mrgddb.in > mrgddb.log 2> mrgddb.err', shell=True)
    res["mrgddb_exit_code"] = pm.returncode
    why = []
    if pm.returncode != 0 or not (d / "merged.ddb").exists():
        why.append("mrgddb failed or produced no merged.ddb")

    if not why:
        (d / "anaddb.in").write_text("dieflag  1\nnlflag   1\n", newline="\n")
        for dummy in ["anaddb_thm_dummy", "anaddb_gkk_dummy", "anaddb_ep_dummy", "anaddb_ddk_dummy"]:
            (d / dummy).write_text("", newline="\n")
        (d / "anaddb.files").write_text(
            "anaddb.in\nanaddb.abo\nmerged.ddb\nanaddb_thm_dummy\nanaddb_gkk_dummy\n"
            "anaddb_ep_dummy\nanaddb_ddk_dummy\n", newline="\n")
        pa = subprocess.run(f'cd "{d}" && anaddb < anaddb.files > anaddb.log 2> anaddb.err', shell=True)
        res["anaddb_exit_code"] = pa.returncode
        anaddb_abo = d / "anaddb.abo"
        res["anaddb_abo_present"] = anaddb_abo.exists()
        if pa.returncode != 0 or not anaddb_abo.exists():
            why.append("anaddb failed or produced no anaddb.abo")

    res["integrity"] = dict(ok=not why, issues=why)
    res["status"] = "DONE" if not why else "FAILED"
    res["reason"] = "ok" if res["status"] == "DONE" else "; ".join(why)
    res["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    for f in list(d.glob("mrgddb.in")) + list(d.glob("mrgddb.log")) + list(d.glob("mrgddb.err")) + \
             list(d.glob("merged.ddb")) + list(d.glob("anaddb.in")) + list(d.glob("anaddb.files")) + \
             list(d.glob("anaddb.abo")) + list(d.glob("anaddb.log")) + list(d.glob("anaddb.err")):
        shutil.copy(f, out / f.name)
    json.dump(res, open(out / "result.json", "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))
    if res["status"] == "DONE":
        print("\n--- anaddb.abo ---")
        print((d / "anaddb.abo").read_text(errors="ignore"))
    sys.exit(0 if res["status"] == "DONE" else 3)


if __name__ == "__main__":
    main()
