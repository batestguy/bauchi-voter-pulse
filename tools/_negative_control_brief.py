"""Negative control: prove the brief's link verifier actually fails.

Not part of the build. This breaks exactly one thing -- the page-3 sheet's id --
and runs the real generator from a copy. If the build still passes, the verifier
is decorative and must not be trusted.
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
src = (ROOT / "tools" / "make_brief.py").read_text(encoding="utf-8")

old = 'f\'<section class="sheet" id="p{i + 1}">{chunk}\''
new = (
    'f\'<section class="sheet" '
    'id="{\'p\' + str(i + 1) if i != 2 else \'wrong3\'}">{chunk}\''
)
assert old in src, "anchor not found in make_brief.py"

out = ROOT / "tools" / "_negctl_brief.py"
out.write_text(src.replace(old, new), encoding="utf-8")

try:
    result = subprocess.run([sys.executable, str(out)], cwd=ROOT, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
finally:
    out.unlink(missing_ok=True)

tail = output.splitlines()[-3:]
print("\n".join(tail))
print(f"exit code: {result.returncode}")

# A non-zero exit is not enough. This first attempt failed because the copy sat
# in build/ and could not find the data files at all -- it "passed" the negative
# control for a reason that had nothing to do with the verifier. So require the
# verifier's own message, which is the only proof that it is the thing that fired.
fired = result.returncode != 0 and "FAILED" in output
print("VERIFIER BITES" if fired else "VERIFIER DID NOT FIRE -- DO NOT TRUST IT")
sys.exit(0 if fired else 1)