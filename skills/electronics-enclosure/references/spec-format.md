# spec.json format

All lengths in mm. Anything left out takes the default shown (defaults live in `scripts/encl.py`,
`DEFAULTS`). Start from `assets/spec_template.json`.

## Coordinate systems

- **Inner coordinates** (used for every position): origin at the inside front-left corner, on
  top of the floor. X = length (left -> right), Y = depth (front wall at Y = 0), Z = up.
- **Walls**: `front` (Y=0), `back` (Y=W), `left` (X=0), `right` (X=L). On a wall, `u` is the
  inner X (front/back) or inner Y (left/right) of a feature's centre, `z` its height above the floor.
- **Board frame**: the PCB occupies x in [0, length], y in [0, width]. For parts and pins,
  z = 0 is the PCB's **top** surface. `at` = inner (x, y) where the board-frame origin lands,
  `rot` = rotation about Z in degrees (0/90/180/270, counter-clockwise seen from above).
  Example: rot 270 maps board +x to inner -Y and board +y to inner +X.

## Top level

```json
{
  "name": "short description",
  "inner": [L, W, H],              // inner size; H = floor-top to lid-underside
  "print": {"wall": 2, "floor": 2, "lid": 2, "tol": 0.25, "r_out": 2, "chamfer": 0.8, "fn": 64},
  "labels": {"size": 3.5, "relief": 0.6, "gap": 1.2, "font": "auto"},
  "boards": [...], "blocks": [...], "panel_parts": [...], "openings": [...],
  "vents": [...], "anchors": [...], "lid": {...}, "mount": {...}
}
```

## boards - PCBs that sit in a seat

```json
{"id": "esp", "size": [23.55, 18.0, 1.0], "at": [1.7, 20.0], "rot": 0,
 "ledge_h": 3.0,            // PCB underside above the floor (>= solder stub length)
 "clear": 0.25,             // pocket clearance per side
 "rim_t": 1.2,              // rim walls around the pocket (top = PCB top); skipped on edges against a wall
 "rim_skip": ["x-"],        // also skip the rim on these board edges (e.g. under an overhanging connector)
 "zone": 10.0,              // free zone around the PCB (checked up to the top of the plugs)
 "headroom": 28.0,          // required height above the PCB top
 "plug": {"seat": 3.5, "height": 14.0, "w": 2.54},   // Dupont housing on each pin with "plug": true
 "parts": [                 // anything on the board that matters, board frame, z from PCB top
   {"name": "usb-c", "box": [x0, y0, z0, x1, y1, z1], "metal": true},
   {"name": "antenna", "box": [...], "antenna": true},   // keeps metal >= antenna_keepout (10) away
   {"name": "led", "box": [...]}                        // lid windows can point at parts
 ],
 "pins": [{"at": [x, y], "d": 1.7, "plug": true}],      // single pins / holes
 "rows": [{"start": [x, y], "dir": [1, 0], "n": 9, "pitch": 2.54, "d": 1.7, "plug": true}],
 "ledges": [[x0, x1, y0, y1], ...],     // board frame; where the PCB rests (avoid solder stubs!)
 "latches": [{"edge": "x+", "at": 12.4, "width": 3.0}],  // edge x-/x+/y-/y+, at = position along it
 "latch": {"t": 1.2, "len": 9.0, "over": 0.6, "gap": 0.4, "back": 0.4, "width": 3.0}
}
```
Each pin gets a solder-stub dummy (d x 2.6 mm below the PCB) and, if `plug`, a Dupont housing
dummy - both are collision-checked. Parts may extend beyond the PCB (USB-C overhang: negative x).

## blocks - loose parts in a cradle (WAGO, relays, batteries...)

```json
{"id": "wago1", "size": [13.1, 18.6, 8.1], "at": [x, y], "rot": 0, "metal": true,
 "cradle": {"wall_h": 5.0, "t": 1.2, "clear": 0.45, "open": ["y-"]}}   // open = wire-entry side
```
Set `"cradle": null` for a dummy only (collision / layout checks, no walls).

## panel_parts - parts mounted through a wall (DC jack, switch, gland)

```json
{"id": "jack", "wall": "left", "u": 46.5, "z": 10.0,
 "cut": {"d": 8.0, "flat": 0, "teardrop": true},          // flat > 0: D-flat width across the flat
 "body": {"d": 11.0, "depth": 16.0, "nut_ac": 12.7, "nut_t": 2.0},   // inside dummy
 "metal": true, "label": "12V IN", "label_pos": "above"}
```

## openings - holes in walls

```json
{"id": "usb", "type": "usb-c", "wall": "left", "align": "esp/usb-c",   // u, z from that part
 "w": 10, "h": 4.5, "recess": true, "wedge": true, "label": "USB"},
{"id": "fan", "type": "slot", "wall": "front", "u": 20, "z": 8, "w": 12, "h": 6, "label": "FAN"},
{"id": "dht", "type": "hole", "wall": "front", "u": 60, "z": 8, "d": 6, "label": "SENSOR"}
```
`label_pos`: above (default) / below / left / right; labels slide sideways automatically when
crowded. `recess`: true or {"w": 13, "h": 7.5, "wall": 0.8}. `wedge`: true or {"len": 1.6}.
Slots get 45° chamfered top corners (`window_chamfer`, keeps bridges short); holes get a
teardrop top (`teardrop`).

## vents

```json
{"wall": "front", "from": 56, "to": 76, "z0": 6, "len": 12, "w": 1.5, "pitch": 3}
```
Keep >= 3 mm between vent tops and lid catch windows (checked).

## anchors - zip-tie anchors on the floor

```json
{"at": [x, y], "rot": 0, "l": 8, "w": 5, "h": 4, "tunnel_w": 3.2, "tunnel_h": 1.6}
```
The tunnel runs along the anchor's length (rot 0 = along X).

## lid

```json
{"fix": "snap",                    // or "screws"
 "lip_h": 3.0, "lip_t": 1.2,
 "snap": {"walls": ["front", "back"], "spread": 0.6,   // 2 arms per wall at centre +- spread*span/2
          "w": 8, "t": 1.6, "len": 11, "engage": 0.9, "play": 0.2,
          "positions": null},                         // or [["front", u], ...] - keep it symmetric
 "screws": {"post_d": 6, "inset": 3, "pilot": 2.5, "depth": 9, "hole": 3.4},
 "windows": [{"at": "esp/led", "d": 3.0, "pipe": false}],   // or "at": [x, y]
 "symmetric_windows": true,        // add the 180-degree copy so the lid fits both ways
 "light_pipe": {"od": 5.0, "gap": 4.0}}
```

## mount

```json
{"magnets": {"d": 4, "h": 2, "hole_d": 4.1, "inset": 4.5, "boss_d": 8, "boss_h": 1.2},  // null = none
 "tabs": {"walls": ["left", "right"], "len": 12, "w": 14, "t": 4, "r": 3, "hole": 4.5, "at": null}}  // at null = centred
```
Magnets sit in the four corners (under the posts for a screw lid), pressed in flush from below.

## Outputs of build.py

`base.stl`, `lid.stl` (print orientation), `lid_assembled.stl`, `components.stl`,
`parts/*.stl` (one dummy per part, plugs, USB plug), `layout.json` (outer size, snap positions,
label positions, lid windows, font used).
