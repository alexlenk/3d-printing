# Instructions for agents

This repo holds 3D-printable designs and the tooling to make new ones. Read this first.

## Designing an enclosure for electronics

1. Read [skills/electronics-enclosure/SKILL.md](skills/electronics-enclosure/SKILL.md) and follow
   its workflow. It is written for exactly this task.
2. Before asking the user for dimensions, look the parts up in [components/](components/README.md).
   Library numbers are a starting point: still get a photo of the user's actual part.
3. Ask before you model: photos of every component, and every dimension you are not sure of.
   Do not fill gaps with "typical" values unless the user explicitly says to.
4. Put the finished design in `projects/<short-name>/`:
   `spec.json`, `base.stl`, `lid.stl`, `preview.png`, `README.md` (assembly, hardware, print
   settings, verify-before-printing list).
5. Add every part you measured or researched to `components/` (copy `components/_template.md`)
   and list it in `components/README.md`. Record the source of each number.
6. If the library can't express something the design needs, extend
   `skills/electronics-enclosure/scripts/encl.py` and add a matching check to `check.py`.
   Keep `assets/spec_template.json` building with 0 problems.

## Hard rules (each one cost a failed print)

- Print orientation by **rotation only**, never a mirror. `check.py` verifies the lid.
- Snap arms / lid features symmetric, so the lid fits both ways round.
- Spread parts out; no cable entry inside a board's 10 mm plug field.
- Every exported part is one watertight body.
- Look at every rendered view before calling a design done.

## Public repository

Everything here is public. Do not commit personal data: no addresses, room or house details,
names of other people, private photos, network names, credentials or API keys. Link product
pages and datasheets instead of copying their images. Only commit models the user designed
or that carry a license allowing redistribution (say which, and credit the author).

## Commits

Author commits as the repo owner unless told otherwise. Small, descriptive commits.
