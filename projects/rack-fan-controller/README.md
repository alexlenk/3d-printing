# Rack Fan Controller – enclosure (Dupont / WAGO version)

An enclosure for:
- a Waveshare ESP32-C3-Zero
- a DC5-36-TO-DC3V3-5 buck module (12 V → 5 V)
- 2 × WAGO 221-413 lever connectors
- a 5.5/2.1 mm panel DC jack

Everything is wired with Dupont jumpers and the WAGOs; there is no carrier board. It is a parametric PythonSCAD model. The lid is screwless: it snaps on.

**Status:** the base is printed and the modules fit and snap in. The lid in this folder is the corrected version (an earlier export was mirrored and did not fit).

This box was designed by hand before the [electronics-enclosure skill](../../skills/electronics-enclosure/SKILL.md) existed; the part data is in [components/](../../components/). Its lid snap arms are not symmetric - a new design should use the skill's symmetric default.

| File | What |
|---|---|
| `enclosure.py` | The model. All dimensions are variables at the top. |
| `base.stl` | The base, in print orientation. |
| `lid.stl` | The lid, in print orientation (outer face down). |
| `preview.png` | Renders: closed, open with dummy parts, top view, empty base, a section through the latches, the bottom and the lid. |
| `verification_report.json` | Output of `tools/check.py` for the delivered STLs. |
| `tools/check.py` | Checks for collisions, the 10 mm clearance zones, antenna-to-metal distances, headroom, USB-C engagement, latch strain, wall layout and bridges/overhangs. |
| `tools/render.py`, `tools/views.json` | Review renders (uses Docker `openscad/openscad:trixie`). |

## Build

```bash
pip install pythonscad                       # tested: pythonscad 1.1.2, Python 3.12 and 3.13
python enclosure.py base base.stl
python enclosure.py lid  lid.stl
python enclosure.py base base.stl lid_fix='"screws"'     # option: screw-on lid with 4 posts instead of snap arms
python tools/check.py build                             # needs: trimesh manifold3d shapely scipy rtree
```

## Size

- **Outside:** 88.6 × 63 × 36.6 mm, or 112.6 mm long with the mounting tabs.
- **Inside:** 84.6 × 59 × 32.6 mm.
- **Why it isn't ~85 × 60 × 40:** the length and width come from the required clearances, so the box is longer and wider than the target but lower.
  - 10 mm free space around each module.
  - The antenna at least 10 mm from metal.
- **Height:** 3 mm ledge + PCB + 28 mm headroom. The buck module gets exactly 28.0 mm and the ESP 28.6 mm.
- **Cable-hole option:** `power_entry="hole"` makes the box 83.8 mm long, because the jack body no longer needs room behind the left wall.

## Layout (top view, front wall at the bottom)

```
        back wall:  vents (at the buck)
   +-------------------------------------------+
   | jack  |[WAGO][WAGO]|            |  |      |
   |  ->   | entries v  |          [BUCK]      |
 12V IN                                |  |    |
 USB [ ESP32-C3 ]ant                   |  |    |
   |                                           |
   +---FAN----SENSOR----snap-------vents/snap--+
        front wall
```

- **ESP32-C3-Zero:** at the front-left. Its USB-C end is against the left wall; the antenna end points into the box.
  - Antenna distances: 11.9 mm to the WAGOs, 13.7 mm to the jack, 35 mm to the buck module and 14 mm to the magnets.
  - The lid above the antenna is plain plastic, with no screws anywhere.
- **WAGOs:** in a cradle against the back wall, wire entries facing forward, levers free from above. The cradle walls are 5 mm high.
- **Buck module:** at the right end, lengthwise front to back, so the VIN and VOUT pin ends get 10 mm of plug space at the front and back. It is centred between the vent slots in the front and back walls.
- **Left wall:**
  - USB-C cutout, 10 × 4.5 mm, centred 5.6 mm above the floor.
  - An outside recess thins the wall to 0.8 mm in front of the port, so a plug engages 5.3–5.8 of its 6.6 mm.
  - 12 V jack, Ø8 mm, centred 10 mm above the floor.
- **Front wall:**
  - FAN slot, 12 × 6 mm. It passes a 4-pin fan plug or a 4-pin Dupont housing.
  - SENSOR hole, Ø6 mm. It passes single Dupont housings; a 3-pin housing (7.6 mm) does not.
  - A zip-tie anchor on the floor behind each opening. A third anchor sits on the 12 V wiring path.
- **Labels:** raised text, Liberation Sans Bold 3.5 mm.
  - "USB" and "12V IN" are on the left wall.
  - "FAN" and "SENSOR" are on the front wall.
  - There is no lid label.
- **Flat surfaces for hot glue:** the pocket rims are flat and level with the top of each PCB. The floor around the modules is flat.

## How the modules are held

- **Ledges:** both modules sit on 3 mm ledges, which leaves 3 mm under the solder joints. The ledges are segments, not a full rim. On the ESP the header rows are 1.38 mm from the long edges and the first pads are about 0.7 mm from the short ends, so a full rim would hit the solder joints.
  - **ESP, USB end:** one 1.8 mm ledge between the header rows. There are no USB-C legs underneath (confirmed on the real board).
  - **ESP, antenna end:** one 2.5 mm ledge between the header rows.
  - **Buck module:** ledges along both long sides, clear of the pin holes at the ends.
- **ESP position:** the USB-C socket sticks out about 1.7 mm past the PCB edge (`usb_overhang`). The socket face sits against the wall, and the PCB starts 1.7 mm in from it.
- **Spring latches:** each latch is a 1.2 mm plate that stands free in a slot through the floor. It flexes sideways and its nose snaps 0.6 mm over the PCB edge.
  - **ESP:** one latch at the antenna end. Its 3 mm nose sits 10.9–13.9 mm from the PCB's 5V/GND/3V3 edge, between the ceramic antenna (2.9–10.6 mm) and the round pads 14/15/16, so it never touches the antenna.
  - **Buck module:** one latch on each long side, 15 mm from the VIN end. That is clear of the diode on one side and of the two output capacitors on the other, which come within 0.4 mm of the edge.
  - The latch plates are 9 mm long and strain 2.4 % (ESP) and 1.9 % (buck) when they snap, which is safe for PETG and ASA.
  - A vertical hook only 4 mm tall would strain about 5 %, which is why I didn't use one.
  - The slots leave three small openings in the bottom face.
- **USB wedge:** a wedge on the inside of the left wall sits over the USB-C receptacle. It lets the USB end lift at most 0.65 mm.
- **Fitting the ESP:** put the USB end in first, under the wedge and against the wall, then press the antenna end down until the latch clicks.
- **Fitting the buck module:** press it straight down until both latches click.
- **Removing either module:** push the latch plate outwards with a small screwdriver.

## Snap-fit lid

- **Arms:** 4 spring arms hang 11 mm down from the lid. Each is 8 mm wide and 1.6 mm thick, with a nose that catches in a 9 × 3.3 mm window near the top of the wall.
  - Front wall: x = 41 and 66 mm.
  - Back wall: x = 12 and 66 mm.
- **Clearance:** all four arms sit outside the 10 mm zones around the modules.
- **Nose shape:**
  - 30° lead-in at the bottom, so the lid presses on easily (estimated about 12 N per arm).
  - 45° catch face, so it can't shake loose; pulling it off takes an estimated 20 N per arm (about 8 kg for all four).
  - Each arm flexes 0.9 mm (1.8 % strain).
- **Closing:** line up the lid (its locating lip guides it) and press down until all 4 click.
- **Opening:** press each nose inwards through its window with a small flat screwdriver, about 1 mm, while lifting that side of the lid. Do the front pair first, then the back.
- **Vents:** they are 12 mm high, so there is about 4.8 mm of solid wall between the vents and the catch windows.
- **Screws instead:** `lid_fix="screws"` brings back the 4 posts and M3 self-tapping screws.

## Hardware

| Qty | Part | Notes |
|---|---|---|
| 4 | Magnets Ø4 × 2 mm | Press-fitted flush into the bottom, one in each corner. A Ø8 × 1.2 mm boss inside leaves 1.2 mm of plastic above each magnet (pocket Ø4.1 × 2.0, `magnet_hole_d`). |
| 2 | Screws for the tabs | The holes are Ø4.5 mm. |
| 1 | Panel DC jack 5.5/2.1, M8 thread | The box allows up to 16 mm behind the wall (`jack_depth`). For an anti-rotation D-flat, set `jack_flat` to the width across your jack's flat (for example 7.2), but only if your jack has one. |

No screws are needed for the lid.

## Printing

- **Material:** PETG or ASA, 0.4 mm nozzle, 0.2 mm layers. **No supports.**
- **Base:** print as exported, bottom down.
- **Lid:** print as exported, outer face down, so the lip and the 4 snap arms point up. The noses' catch faces print at exactly 45°.
  - To fit it, flip the printed lid over its **long** edge.
  - The lid only fits one way round: the small LED hole goes over the ESP, in the corner with the USB-C.
  - Lids exported before this fix were mirror images and cannot fit.
- **Bridges:** the longest is about 9 mm (the FAN slot top, with 1.5 mm 45° corner chamfers). The others are the lid catch windows (9 mm), the USB cutout top, the zip-tie tunnels (3.2 mm) and the magnet pocket roofs (4.1 mm).
- **Overhangs:** the other overhangs are 45° (teardrop hole tops, the wedge, the latch lead-ins). The latch noses have a 0.6 mm horizontal catch underneath.

## Check before printing (each is a parameter)

The ESP layout comes from a public footprint ([NNTin/CanFactory pull request #72](https://github.com/NNTin/CanFactory/pull/72), taken from Waveshare's drawing): header rows 1.38 mm in from the long edges, first pin 1.59 mm from the end, RGB LED at 8.93 / 14.2 mm.

Product photos supplied:
- **ESP:** the antenna position, the USB-C overhang and the LED position.
- **Buck module:** the pin layout and the parts near its edges.

- **ESP board length:** set to the measured 23.55 mm (`esp_pcb_l`); the pocket is 24.05 mm.

1. **USB-C overhang:** `usb_overhang`, estimated at 1.7 mm from the photo. Measure from the PCB edge to the front of the USB-C socket. This sets where the PCB sits and how far the latch nose reaches.
2. **ESP antenna end:** check there is bare PCB 10.9–13.9 mm from the 5V/GND/3V3 edge, within 0.6 mm of the antenna-end edge. That is where the latch nose grips.
3. **Buck module:**
   - nothing soldered under the long edges (ledges);
   - PCB thickness `buck_pcb_t`, assumed 1.6 mm;
   - the VIN holes are about 3.5 mm apart. Standard 2.54 mm Dupont housings fit on pins there, but check the header actually fits the holes.
4. **LED window:** `led_from_usb` / `led_from_front` come from the footprint. Set `light_pipe=True` for a tube down to 4 mm above the board.
5. **WAGO 221-413:** cradle pockets are 20 × 14 mm, for a part of about 18.6 × 13.1 mm.

## Verified by `tools/check.py` (all pass)

- **Mesh:** one watertight body each for base and lid.
- **Collisions:** no collisions between the base, the lid (with its snap noses sitting in their windows) and any dummy part:
  - the ESP with its solder joints under the board, headers, USB-C and 18 Dupont housings;
  - the buck module with its solder joints, 4 VIN + 6 output Dupont housings, and the edge capacitors;
  - the ESP's ceramic antenna;
  - the WAGOs;
  - the jack and its nut.
- **Clearance zones:** nothing intrudes into the 10 mm zone around either module except the hold-downs.
- **Antenna:** at least 10 mm from all metal.
- **Headroom:** at least 28 mm above both PCBs.
- **USB-C:** plug and receptacle line up, and the engagement is reported.
- **Latches and snap arms:** strain stays under 3 %.
- **Wall layout:** labels, openings and vents keep at least 1 mm from each other and from the edges.
- **Bridges and overhangs:** at most 10 mm.
- **Variants checked:**
  - default (snap lid)
  - screw lid
  - screw lid with cable holes
  - 24 mm board
  - cable-hole entries
  - light pipe
  - no magnets, tabs, labels or wedge
  - D-flat jack hole
  - 12 mm clearance with 30 mm headroom
