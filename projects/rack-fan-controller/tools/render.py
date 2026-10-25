#!/usr/bin/env python3
"""Render review images of exported STLs (verification only).

Uses the official openscad/openscad:trixie image purely as a PNG renderer.
Usage: render.py <outdir> <sheet.png> <views.json>
views.json: [{"name":..., "parts":[["base.stl","#4f7cac"],...], "eye":[x,y,z], "center":[x,y,z],
              "proj":"p"|"o", "size":[w,h], "clip":[x0,y0,z0,x1,y1,z1] (optional box to keep)}]
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.abspath(sys.argv[1])
SHEET = sys.argv[2]
views = json.load(open(sys.argv[3]))

for old in [f for f in os.listdir(OUT) if f.startswith("_v_view")]:
    os.remove(os.path.join(OUT, old))
cmds, tiles = [], []
for i, v in enumerate(views):
    v["file"] = f"view{i}"
    body = " ".join(f'color("{c}") import("{f}");' for f, c in v["parts"])
    if "clip" in v:
        x0, y0, z0, x1, y1, z1 = v["clip"]
        body = f"intersection(){{ union(){{ {body} }} translate([{x0},{y0},{z0}]) cube([{x1 - x0},{y1 - y0},{z1 - z0}]); }}"
    fn = f"_v_{v['file']}.scad"
    open(os.path.join(OUT, fn), "w").write(body + "\n")
    cam = ",".join(str(a) for a in v["eye"] + v["center"])
    w, h = v.get("size", [900, 700])
    cmds.append(f"openscad -o /w/_v_{v['file']}.png --render --camera={cam} --imgsize={w},{h} "
                f"--projection={v.get('proj', 'p')} --colorscheme=Tomorrow /w/{fn} 2>/dev/null || echo FAIL {v['file']}")
    tiles.append((v["file"], v["name"]))
r = subprocess.run(["docker", "run", "--rm", "-v", f"{OUT}:/w", "openscad/openscad:trixie", "bash", "-c", " ; ".join(cmds)],
                   capture_output=True, text=True)
if r.stdout.strip():
    print(r.stdout)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
ims = []
for f, n in tiles:
    p = os.path.join(OUT, f"_v_{f}.png")
    if not os.path.exists(p):
        sys.exit(f"render failed: {n} (is Docker running?)")
    im = Image.open(p).convert("RGB")
    ImageDraw.Draw(im).text((10, 8), n, fill=(0, 0, 0), font=font)
    ims.append(im)
cols = 2 if len(ims) > 1 else 1
rows = (len(ims) + cols - 1) // cols
W = max(i.size[0] for i in ims); H = max(i.size[1] for i in ims)
sheet = Image.new("RGB", (W * cols, H * rows), "white")
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * W, (i // cols) * H))
sheet.save(SHEET)
print("sheet", SHEET, sheet.size)
