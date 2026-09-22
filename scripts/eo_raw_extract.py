"""DEL C, C4: extract the raw QE electro-optic tensor (total + electronic + XC-derivative
contributions) from a ph.out file, with correct whitespace handling (QE prints
"contribution #   1" with variable spacing -- fixed here after the embedded parser in
run_delC_c3_*.py under-matched this and returned None for the sub-contributions).

    python scripts/eo_raw_extract.py <ph.out>
"""
from __future__ import annotations
import re
from pathlib import Path


def parse_elop_full(ph_out_text: str) -> dict:
    out = dict(total=None, electronic=None, xc_derivative=None)
    m = re.search(r"Electro-optic tensor in cartesian axis:\s*\n\s*\n((?:.*\n){12})", ph_out_text)
    if m:
        nums = [float(x) for x in re.findall(r"-?\d+\.\d+(?:e[+-]?\d+)?", m.group(1))]
        if len(nums) >= 27:
            out["total"] = [nums[i:i + 3] for i in range(0, 27, 3)]
    for label, key in [(r"#\s*1", "electronic"), (r"#\s*2", "xc_derivative")]:
        m2 = re.search(rf"Electro-optic tensor: contribution {label}\s*\n\s*\n((?:.*\n){{12}})", ph_out_text)
        if m2:
            nums = [float(x) for x in re.findall(r"-?\d+\.\d+(?:e[+-]?\d+)?", m2.group(1))]
            if len(nums) >= 27:
                out[key] = [nums[i:i + 3] for i in range(0, 27, 3)]
    return out


if __name__ == "__main__":
    import sys
    import json
    txt = Path(sys.argv[1]).read_text(errors="ignore")
    print(json.dumps(parse_elop_full(txt), indent=1))
