---
name: electronics-enclosure
description: Design 3D-printable enclosures (cases, boxes, housings) for electronics - dev boards such as ESP32 / Arduino / Raspberry Pi Pico, DC-DC and relay modules, sensors, WAGO or screw terminals, panel DC jacks, USB-C ports - and deliver print-ready STL files for base and lid plus a parametric spec. Boards snap into seats with spring latches, cutouts line up with real connectors, the lid snaps on, and everything is verified (collisions, clearances, plug engagement, overhangs) and rendered before delivery. Use this whenever someone wants a box or case for their electronics or modules, an enclosure for a PCB, a housing for a sensor/controller project, or asks to "print a case" for parts they describe - even if they never say "enclosure" or "OpenSCAD".
---

# Electronics enclosure designer

You design a two-part, support-free FDM enclosure (base + snap lid) around real electronics
modules, from a JSON spec, with a Python library that builds, checks and renders it.

What the user gets in the end:
- `base.stl`, `lid.stl` - in print orientation, ready to slice
- `spec.json` - the parametric design (every dimension editable, rebuildable)
- `preview.png` - renders including sections
- `README.md` - assembly order, hardware list, print settings, and what to verify before printing

## Setup (once per session)

```bash
pip install pythonscad trimesh manifold3d shapely scipy rtree networkx pillow numpy
S=<this skill's directory>/scripts
python $S/build.py spec.json out/          # STLs + out/layout.json
python $S/check.py spec.json out/          # PROBLEMS (must fix) and WARNINGS (design quality)
python $S/render.py spec.json out/ out/preview.png
```
pythonscad wheels exist for CPython 3.10-3.14. Rendering is pure Python (no OpenGL, no Docker).

## Workflow

### 1. Get pictures and facts before modelling - ask, don't guess

Guessed geometry was the biggest source of rework in the past: a latch placed on an antenna, a
USB-C socket that overhangs the PCB, a pin layout that wasn't what the datasheet implied, edge
capacitors where a latch was planned. Every one of these was obvious the moment a photo of the
board was on the table - so photos come first, before any spec is written.

**Pictures of every component are a precondition, not a nice-to-have.**
1. For each component, look for a straight-on top-view photo and, if available, a dimension
   drawing: search the web (maker's product page / wiki, shop listings, datasheets) and fetch
   the images.
2. If you cannot find a picture of *exactly* that board (same maker, same revision - clones
   differ), or the picture doesn't show what you need (an edge, the underside, a connector
   overhang), **ask the user for a photo**. Don't work around a missing picture with
   assumptions. A phone photo straight from above, next to a ruler, is enough.
3. Read positions off the photos by pixel scale (`references/measuring.md`) and show the user
   what you derived ("antenna 2.9-10.6 mm from the 5V edge, USB-C overhangs ~1.7 mm").

**Dimensions: if you are not sure, ask.** Anything that decides fit - PCB size and thickness,
connector overhang, positions of parts near the edges, pin positions, heights - must come from
the user, a datasheet drawing, or a photo you measured. Do not fill a gap with a "typical" value
and move on; ask, and keep asking until the critical numbers are known. Only when the user
explicitly says to go ahead without a value may you use an assumption - then it goes into the
verify-before-printing list and the summary.

Collect, for every module:
- **Photos of the top (and bottom) of each board** (see above).
- PCB length x width x thickness (calipers if possible), height of the tallest part.
- Where the connectors are and how they are used: header pins up or down, Dupont plugs on
  top, screw terminals, USB-C (does it overhang the PCB edge? by how much?).
- What sits within ~1 mm of each PCB edge (latch noses grip there), what is underneath
  (solder stubs, legs), antennas.
- External cables: which wires leave the box, connector sizes that must pass an opening.
- Mounting (screws, magnets, DIN, adhesive), environment (heat, humidity), material and nozzle.

Look the parts up in the component library first: `components/` at the root of the
3d-printing repo, or `references/components/` in the packaged skill (`references/parts.md`
says where). Use those numbers as a starting point, but still check them against a photo of
the user's actual board. Ask in one compact batch (photos + the specific measurements you need,
each with why it matters). Wait for the answers before writing the spec.

### 2. Plan the layout - spread it out, make it symmetric

Users judge the result mostly on how easy it is to assemble and wire. Feedback that shaped
these rules: "there is a lot of free space, but the parts were crammed together", "the fan cable
inlet is right next to the ESP", "make it symmetrical, it looks nicer and is error tolerant".

- **Use the space.** Size the box from the clearances, then distribute the parts across the
  whole floor. A cable entry belongs where its wires end up, with free floor in front of it -
  not inside a board's plug field. Terminal blocks/WAGOs get room in front of their wire entries
  and space above for the levers; panel jacks need their body length free behind the wall.
- **10 mm free zone around every board** (up to the top of its plugs) for fingers and
  Dupont plugs; 28 mm headroom above PCBs with Dupont plugs (14 mm housing + wire bend).
- **Symmetry wherever nothing forces otherwise**: snap arms mirrored on opposite walls (the
  default) so the lid fits both ways round; magnets in all four corners; tabs centred. If a lid
  feature must align with something (an LED window), keep `symmetric_windows` on (adds the
  mirrored copy) so orientation still doesn't matter.
- Antennas >= 10 mm from metal (jack, terminal clamps, inductors, magnets, screws) and nothing
  but plastic above them. Heat sources next to vents. USB-C ports flush to a wall.
- Order of assembly: boards drop straight down into their seats; cables are routed after; the
  lid goes on last. Nothing may require threading a board under something else.

Before building, tell the user the planned layout and **every deviation from their spec**
(size, opening shapes, moved parts) with the reason, and let them confirm. Changing a printed
case later is expensive.

### 3. Write `spec.json`

Format and every field: `references/spec-format.md`. Start from `assets/spec_template.json`.
Positions are inner coordinates (mm from the inside front-left corner, on the floor). Boards
are described in their own frame (from the photo) and placed with `at` + `rot` - keep all
measured detail (parts, pins, keep-outs) in board coordinates so a move is one number.
Derive positions from each other with simple arithmetic you write down, not magic numbers.

### 4. Build, check, render, look - iterate until clean

1. `build.py` - fix exceptions first.
2. `check.py` - fix every PROBLEM. Read every WARNING: either fix it (most are about crowding
   and symmetry) or tell the user why it stays.
3. `render.py` - **open the sheet and look at every tile**, especially the sections: noses
   over PCB edges, snap noses in their windows, plugs clear of the lid, cutouts aligned.
4. When you add a safety-relevant feature, run one negative test: deliberately break it (e.g.
   move a latch onto a part, or swap the lid orientation) and confirm `check.py` catches it.
   A check that cannot fail proves nothing.

Design rules with numbers and reasons are in `references/design-rules.md` - read it before
changing seats, latches, snaps, cutouts or labels.

### 5. Deliver

If you are working in the 3d-printing repository, put the result in `projects/<name>/`
(spec.json, STLs, preview, README) and add every newly measured part to `components/`.


Send base.stl, lid.stl, spec.json, preview.png and a README with: outer size, layout sketch,
assembly order (which board first, how latches release), hardware (magnets, screws), print
settings (PETG/ASA, 0.2 mm layers, no supports, base bottom-down, lid outer-face-down), how
to put the lid on, and the **verify-before-printing list** (every value that came from a photo
estimate or an assumption). Report the checker's key numbers honestly. Do not claim it will fit
before it has been printed - say what was verified in the model and what wasn't.

## What has proven itself in print (keep it)

- Board seats: ledge segments 3 mm high **between** header rows (a rim all round hits solder
  stubs), pocket clearance 0.25 mm, rim flush with the PCB top (flat glue surface).
- Spring latches: a 1.2 mm plate standing free in a slot through the floor, 9 mm long, nose
  0.6 mm over the PCB edge, strain ~2 %. Boards snap in and stay put.
- USB-C: cutout 10 x 4.5, outside recess leaving 0.8 mm wall, receptacle face against the
  inner wall, wedge over the receptacle - plug engages ~5.8 mm.
- Raised wall labels (bold 3.5 mm, 0.6 mm relief) next to each opening.
- Ø4 x 2 magnets press-fitted (Ø4.1 hole) flush into the bottom.

## Pitfalls that already happened (and how the library prevents them)

| Pitfall | Prevention |
|---|---|
| Modelling from guessed/"typical" dimensions before seeing the boards - latch on the antenna, USB-C overhang missed, latch over edge capacitors | photos of every component first (search, else ask); uncertain dimensions are asked, not assumed |
| Lid exported for printing with a **mirror** instead of a rotation - unusable | `lid_print()` rotates; `check.py` flips lid.stl back and compares |
| Asymmetric snap positions - lid fits one way only, easy to get wrong | symmetric by default; checker warns and tests the 180° fit |
| Outside features (tabs) reaching 2 mm into the box | clipped at the wall; collisions are checked against dummy parts |
| Latch placed on a component near the PCB edge | model edge components as `parts`; collision check against the base |
| Parts crammed while half the box is empty | checker reports gaps + largest empty circle; warns |
| Coplanar unions -> several bodies / non-manifold mesh | overlap solids by >= 0.5 mm; checker requires one watertight body |
| 2D polygon given clockwise / mirrored multmatrix -> inside-out solid | see `references/pythonscad.md` |
| pythonscad `scad()` (OpenSCAD source) fails | use only the native Python API |
| Review images silently reused from an earlier run | render.py renders in memory on every run; look at the fresh sheet each time |

When the library cannot express something the user needs, extend `scripts/encl.py` (read
`references/pythonscad.md` first) and add a matching check to `check.py`.
