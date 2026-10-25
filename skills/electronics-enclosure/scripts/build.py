#!/usr/bin/env python3
"""Build an enclosure from a JSON spec.

    python build.py spec.json outdir

Writes  base.stl  lid.stl  (print orientation)
        lid_assembled.stl  components.stl  parts/<name>.stl  (checks / previews)
        layout.json        (derived dimensions, snap / label positions)
"""
import json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pythonscad as ps
import encl


def safe(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def main():
    spec_path, out = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.join(out, "parts"), exist_ok=True)
    t0 = time.time()
    E = encl.load(spec_path)
    ps.export(E.base(), os.path.join(out, "base.stl"))
    ps.export(E.lid_print(), os.path.join(out, "lid.stl"))
    ps.export(E.lid_assembled(), os.path.join(out, "lid_assembled.stl"))
    comps = E.components()
    for k, v in comps.items():
        ps.export(v, os.path.join(out, "parts", safe(k) + ".stl"))
    for k, (shell, mold) in E.usb_plugs().items():
        ps.export(shell | mold, os.path.join(out, "parts", safe(k) + "_plug.stl"))
    if comps:
        ps.export(encl.union(list(comps.values())), os.path.join(out, "components.stl"))
    layout = dict(outer=[E.OL, E.OW, E.OH], inner=[E.L, E.W, E.H], base_height=E.BH,
                  snap_positions=E.snap_positions() if E.lid_cfg["fix"] == "snap" else None,
                  labels=[(w, t, round(u, 2), round(z, 2)) for (w, t, u, z, _) in E.label_layout()],
                  lid_windows=[(round(x, 2), round(y, 2), d) for (x, y, d, _, _) in E.lid_windows()],
                  font=encl.pick_font(E.lab["font"]), build_seconds=round(time.time() - t0, 1))
    json.dump(layout, open(os.path.join(out, "layout.json"), "w"), indent=1)
    print(json.dumps(layout, indent=1))


if __name__ == "__main__":
    main()
