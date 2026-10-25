# pythonscad notes (for extending scripts/encl.py)

`pip install pythonscad` gives the PythonSCAD engine as a Python module (`import pythonscad as ps`).

## Works well (native API)
- Primitives: `ps.cube([x,y,z])`, `ps.cylinder(d=, h=, fn=)`, `ps.sphere`, `ps.square`,
  `ps.circle(d=, fn=)`, `ps.polygon(points)`, `ps.text(txt, size=, font=, halign=, valign=)`.
- Transforms are methods: `obj.translate([..])`, `obj.rotate([..])`, `obj.mirror([..])`,
  `ps.multmatrix(obj, 4x4 rows)`.
- Booleans: `a | b` (union), `a - b`, `a & b`, `ps.union(*objs)`, `ps.hull(*objs)`,
  `ps.offset(obj2d, r= | delta=)`, `ps.linear_extrude(obj2d, height=)`.
- `ps.textmetrics(txt, size=, font=)["size"]` -> [width, height] for layout.
- `ps.export(obj, "file.stl")` evaluates (Manifold backend, fast: a full enclosure ~5 s).

## Does not work reliably
- `ps.scad("...openscad code...")` / `osinclude` / `osuse` in 1.1.x: fails even on simple
  modules or `difference()`. Do not try to run .scad source through it. If the user needs a
  `.scad` file, that requires real OpenSCAD.

## Traps
- **Polygon winding**: give 2D polygons counter-clockwise. A clockwise polygon extruded and
  unioned can produce zero-volume / inside-out pieces.
- **multmatrix with a mirror** (determinant -1) turns solids inside out. Check det = +1.
  Same for print orientation: rotate, never mirror.
- **Touching solids** (coplanar faces) union into separate shells or non-manifold edges.
  Overlap by >= 0.5 mm (e.g. latch plate 1 mm into its root, nose half into the plate).
- Fonts: text needs an installed font; `encl.pick_font()` picks Liberation/DejaVu/Noto Sans Bold.
- STL export is deterministic: an unchanged part exports byte-identical (useful to prove "the
  printed base did not change").
