#!/usr/bin/env python3
"""Package a skill from skills/<name>/ into dist/<name>.skill (a zip) for upload to Claude.ai.

    python tools/package_skill.py [electronics-enclosure]

The component library (components/) is copied into references/components/ so the packaged skill
is self-contained. Test cases (evals/) and caches are left out.
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"__pycache__", "evals", ".pytest_cache"}


def files_under(base):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            if not f.endswith(".pyc"):
                yield os.path.join(dirpath, f)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "electronics-enclosure"
    skill = os.path.join(ROOT, "skills", name)
    if not os.path.isfile(os.path.join(skill, "SKILL.md")):
        sys.exit(f"no SKILL.md in {skill}")
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", f"{name}.skill")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files_under(skill):
            z.write(p, os.path.join(name, os.path.relpath(p, skill)))
        comp = os.path.join(ROOT, "components")
        for p in files_under(comp):
            z.write(p, os.path.join(name, "references", "components", os.path.relpath(p, comp)))
        print(out)
        for i in z.infolist():
            print(f"  {i.filename}")


if __name__ == "__main__":
    main()
