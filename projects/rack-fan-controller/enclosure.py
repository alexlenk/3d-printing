#!/usr/bin/env python3
"""
Rack Fan Controller enclosure - Dupont / WAGO version (no carrier board).

Parametric PythonSCAD model: every dimension is a variable in the PARAMETERS block.
Contents: Waveshare ESP32-C3-Zero and DC5-36-TO-DC3V3-5 buck module (both with header pins
pointing UP, sitting on 3 mm ledges and held by spring latches), 2x WAGO 221-413, panel DC jack.
Screwless lid: 4 snap arms click into windows in the front and back walls.

Requirements:  pip install pythonscad      (tested: pythonscad 1.1.2, Python 3.12 / 3.13)
Usage:
    python enclosure.py base base.stl            # base, print orientation
    python enclosure.py lid  lid.stl             # lid, print orientation (outer face on the bed)
    python enclosure.py assembly assembly.stl    # base + lid as mounted
    python enclosure.py components parts.stl     # dummy modules / plugs / WAGOs (checking only)
Override parameters on the command line (Python literals):
    python enclosure.py base base.stl power_entry='"hole"' light_pipe=True

Coordinates: X = length (left -> right), Y = depth (front wall at Y = 0), Z = up.
Layout (top view):
        back wall
   +---------------------------------------+
   | jack->|[WAGO][WAGO]|       |  vents   |
   |  12V  |  entries v |     [BUCK]       |
   USB [ESP32-C3]ant              [    ]   |
   |                                       |
   +--FAN----SENSOR------------ vents -----+
        front wall
Layout positions below are INNER coordinates: measured from the inside of the left wall,
the inside of the front wall and the top of the floor.
"""

import sys
import pythonscad as ps

# =============================================================================
# PARAMETERS
# =============================================================================

# --- General / print -----------------------------------------------------------
wall        = 2.0
floor_t     = 2.0
lid_t       = 2.0
tol         = 0.25    # fit tolerance
r_out       = 2.0     # vertical outer edge radius
chamfer     = 0.8     # 45 deg chamfer on edges that lie on the bed
fn          = 64

# --- Clearances ----------------------------------------------------------------
margin      = 10.0    # free space around each module (Dupont plugs, wiring)
headroom    = 28.0    # free height above each module's PCB (Dupont housing + wire bend)

# --- Module seats (pocket + ledges + spring latches) ------------------------------------
ledge_h     = 3.0     # PCB underside above the floor (header solder stubs need >= 3)
# The PCBs rest on ledge SEGMENTS between the header rows: a rim all round would hit the header
# solder joints (ESP pins are 1.38 mm from the long edges, first pad ~0.7 mm from the short ends).
# Segments are (along, across) ranges in POCKET coordinates (from the pocket's USB/front corner).
esp_ledges  = [((0.0, 1.8), (3.0, 15.5)),      # USB end (from the PCB edge), between the header rows (no USB-C legs underneath)
               ((-2.5, 0.0), (3.0, 15.5))]     # antenna end (negative = from the far end)
buck_ledges = [((4.0, -4.0), (0.0, 1.2)), ((4.0, -4.0), (-1.2, 0.0))]   # long sides, clear of the pin ends
rim_t       = 1.2     # pocket rim wall thickness (rim top = PCB top: flat glue surface)
latch_t     = 1.2     # spring latch plate thickness (flexes sideways, outwards)
latch_len   = 9.0     # free spring length (root -> nose)
latch_nose_w = 4.0    # nose width along the PCB edge
latch_over  = 0.6     # how far the nose reaches over the PCB edge
esp_latch_y = 12.4    # ESP latch nose centre, from the PCB's front long edge (5V/GND/3V3 side): between the
esp_latch_w = 3.0     #   ceramic antenna (2.9-10.6 mm) and the round test pads 14/15/16 (from 13.9 mm)
antenna_y   = (2.9, 10.6)   # ceramic antenna incl. pads, from the PCB's front long edge (for the metal keep-out check)
buck_latch_from_vin = 15.0  # buck latch noses (both long sides), from the VIN end: clear of the diode / output capacitors
buck_latch_w = 3.5
# buck pins (from the product photo): VIN end 4 holes, 3.5 mm in, 3.5 mm pitch; output end 6 pins, 1.4 mm in, 2.54 pitch
buck_vin_holes = (3.5, [2.5, 6.0, 9.4, 12.9])            # (from VIN end, across positions)
buck_out_pins  = (1.4, [1.6 + i * 2.54 for i in range(6)])  # (from output end, across positions)
latch_gap   = 0.4     # slot on the pocket side of the plate
latch_back  = 0.4     # extra slot behind the plate beyond the nose deflection
# the latch plate stands in a slot through the floor (prints from the bed, free to flex)

# ESP32-C3-Zero  (USB-C end against the LEFT wall, antenna end towards +X)
esp_pcb_l   = 23.55   # along X  (measured)
esp_pcb_w   = 18.0    # along Y
esp_pcb_t   = 1.0
esp_pocket_l = None   # None = USB-C overhang + PCB + 0.5
esp_pocket_w = None   # None = PCB + 0.5 (18.5)
esp_y0      = None    # pocket front edge (inner Y); None = margin
usb_overhang = 1.7    # USB-C receptacle sticks out past the PCB edge (from the product photo - MEASURE)
usb_w       = 8.94    # receptacle
usb_h       = 3.2
usb_len     = 7.6     # receptacle length from its front face
usb_cut_w   = 10.0
usb_cut_h   = 4.5
usb_cut_z   = 5.6     # cutout centre above the floor = ledge 3 + PCB 1 + 1.6
usb_recess  = True    # outside pocket so the plug overmold gets closer (wall 0.8 in front of the port)
usb_recess_w = 13.0
usb_recess_h = 7.5
usb_recess_wall = 0.8
usb_wedge   = True    # wedge on the inside of the USB wall over the receptacle (holds the USB end down)
usb_wedge_len = 1.6   # how far the wedge reaches in over the receptacle
led_from_usb = 9.3    # RGB LED (GPIO10) from the USB end   (Waveshare drawing: 14.2 from the antenna end of 23.5)
led_from_front = 8.93 # RGB LED from the front long edge
led_window  = True
led_hole_d  = 3.0
light_pipe  = False   # tube from the lid down to light_pipe_gap above the LED
light_pipe_od = 5.0
light_pipe_gap = 4.0  # stays above the USB-C receptacle (3.2 mm)

# Buck module  (long side along Y, VIN end at the back, VOUT/GND end at the front)
buck_pcb_l  = 33.0    # along Y
buck_pcb_w  = 16.0    # along X
buck_pcb_t  = 1.6
buck_h      = 5.7     # module height incl. PCB (components)
buck_pocket_l = None  # None = PCB + 0.5 (33.5)
buck_pocket_w = None  # None = PCB + 0.5 (16.5)

# WAGO 221-413 x2 (side by side, wire entries facing the FRONT, levers up)
wago_l      = 20.0    # pocket length (wire direction, Y)
wago_w      = 14.0    # pocket width (X)
wago_h      = 9.0     # WAGO height (for checks)
wago_wall   = 1.2
wago_wall_h = 5.0     # cradle wall height (levers stay free)

# --- Openings -------------------------------------------------------------------------
# 12 V input on the LEFT wall, behind the ESP
power_entry = "jack"  # "jack": panel DC jack 5.5/2.1;  "hole": cable hole + zip-tie anchor
jack_d      = 8.0
jack_flat   = 0.0     # >0: D-flat for anti-rotation, = hole width across the flat (e.g. 7.2) - only if YOUR jack has a flat
jack_y      = None    # inner Y of the jack centre; None = just behind the ESP's clearance zone
jack_z      = 10.0    # above the floor (nut 12.7 a/c clears the floor)
jack_depth  = 16.0    # jack + nut length inside the box
power_hole_d = 5.0
# Fan cable (front wall) and DHT22 cable (front wall)
fan_entry   = "slot"  # "slot": passes a 4-pin fan / Dupont plug;  "hole": round hole
fan_x       = 13.0    # inner X
fan_slot_w  = 12.0
fan_slot_h  = 6.0
fan_hole_d  = 6.0
dht_x       = 32.0
dht_hole_d  = 6.0
cable_z     = 8.0     # centre height of fan / DHT openings above the floor
window_chamfer = 1.5
teardrop    = True

# --- Zip-tie anchors on the floor --------------------------------------------------
anchor_l    = 8.0     # along the tunnel
anchor_w    = 5.0
anchor_h    = 4.0
tunnel_w    = 3.2     # for ties up to 3 mm wide
tunnel_h    = 1.6
anchors     = [(13.0, 4.0, 0), (32.0, 4.0, 0), (24.0, 33.5, 0)]   # (inner x, inner y, rotation): fan, DHT, 12V wiring

# --- Ventilation (front + back walls at the buck) -------------------------------------
vent_w      = 1.5
vent_pitch  = 3.0
vent_z0     = 6.0
vent_len    = 12.0    # keeps a 3 mm web below the lid catch windows

# --- Labels (raised text on the walls) ---------------------------------------------
labels      = True
label_size  = 3.5
label_relief = 0.6
label_font  = "Liberation Sans:style=Bold"
label_gap   = 1.2

# --- Lid -----------------------------------------------------------------------------
lid_fix     = "snap"  # "snap": 4 snap arms on the lid click into windows in the long walls (no screws)
                      # "screws": 4 posts with M3 self-tapping screws
snap_w      = 8.0     # arm width
snap_t      = 1.6     # arm thickness (flexes inwards)
snap_len    = 11.0    # arm length below the lid
snap_engage = 0.9     # how far the nose reaches into the wall window
snap_play   = 0.2     # vertical play of the nose in the window
snap_pos    = None    # [(wall, u), ...]; None = 2 on the front wall, 2 on the back wall, outside the module zones
post_d      = 6.0
post_inset  = 3.0     # post centre distance from the inner wall(s)
# lid screw posts: back-left, back-right and front-right corners + one in the middle of the front wall
# (a front-left corner post would sit 4 mm from the ESP's plug row)
lid_screw_pilot = 2.5 # M3 self-tapping
post_hole_depth = 9.0
lid_hole_d  = 3.4
lip_h       = 3.0
lip_t       = 1.2

# --- Mounting -----------------------------------------------------------------------
tabs        = True
tab_len     = 12.0
tab_w       = 14.0
tab_t       = 4.0
tab_r       = 3.0
tab_hole_d  = 4.5
tab_y       = None    # inner Y of the tab centre; None = between the USB plug and the 12 V plug
magnets     = True    # 4 x d4 x 2 press-fit, flush with the bottom (under the posts, or in corner bosses for the snap lid)
magnet_inset = 4.5    # snap lid: boss centre distance from both inner walls
magnet_boss_d = 8.0
magnet_boss_h = 1.2   # floor 2.0 + 1.2 boss = 1.2 mm above the magnet
magnet_hole_d = 4.1
magnet_depth = 2.0

# =============================================================================
# DERIVED LAYOUT  (inner coordinates)
# =============================================================================
G = {}

def EPL(): return esp_pocket_l if esp_pocket_l is not None else usb_overhang + esp_pcb_l + 0.5
def EPW(): return esp_pocket_w if esp_pocket_w is not None else esp_pcb_w + 0.5
def EY0(): return esp_y0 if esp_y0 is not None else margin
def BPL(): return buck_pocket_l if buck_pocket_l is not None else buck_pcb_l + 0.5
def BPW(): return buck_pocket_w if buck_pocket_w is not None else buck_pcb_w + 0.5
def JY(): return jack_y if jack_y is not None else EY0() + EPW() + margin + 8.0
def TY():
    if tab_y is not None:
        return tab_y
    return ((EY0() + EPW() / 2 + 6.0) + (JY() - 5.5)) / 2      # USB overmold half-width 6, jack plug ~5.5

def setup():
    G.clear()
    esp_x1 = EPL()
    corner = (post_inset * 2 if lid_fix == "screws" else (magnet_inset + magnet_boss_d / 2 if magnets else 0.0)) + 0.5
    wago_x0 = max(jack_depth + 0.5, corner) if power_entry == "jack" else corner
    wago_y0 = EY0() + EPW() + margin
    wago_cradle_w = 2 * wago_w + 3 * wago_wall
    front_gap = post_d + 1.0 if lid_fix == "screws" else snap_w + 1.2     # front-wall post / snap arm between the zones
    buck_x0 = max(wago_x0 + wago_cradle_w + margin, esp_x1 + 2 * margin + front_gap)
    G["inner_w"] = max(wago_y0 + wago_l + 0.5, margin + BPL() + margin)
    buck_y0 = (G["inner_w"] - BPL()) / 2           # centred front-to-back
    bx1 = buck_x0 + BPW()
    need = margin + post_d / 2                               # corner posts keep `margin` from the module
    il = bx1 + margin
    for dy in (buck_y0 - post_inset, G["inner_w"] - post_inset - (buck_y0 + BPL())):
        if lid_fix == "screws" and dy < need:
            il = max(il, bx1 + post_inset + (need * need - dy * dy) ** 0.5)
    G["inner_l"] = -(-il * 10 // 1) / 10                 # round up to 0.1 mm
    G["inner_h"] = max(ledge_h + esp_pcb_t, ledge_h + buck_pcb_t) + headroom
    G["outer_l"] = G["inner_l"] + 2 * wall
    G["outer_w"] = G["inner_w"] + 2 * wall
    G["base_h"] = floor_t + G["inner_h"]
    G["outer_h"] = G["base_h"] + lid_t
    G.update(esp_x0=0.0, esp_x1=esp_x1, wago_x0=wago_x0, wago_y0=wago_y0, wago_cw=wago_cradle_w,
             buck_x0=buck_x0, buck_y0=buck_y0)

def W(x, y, z=0.0):
    """inner -> world"""
    return [wall + x, wall + y, floor_t + z]

# =============================================================================
# HELPERS
# =============================================================================

def rrect(l, w, r):
    if r <= 0.01:
        return ps.square([l, w])
    return ps.offset(ps.square([l - 2 * r, w - 2 * r]).translate([r, r, 0]), r=r, fn=fn)

def rbox(l, w, h, r):
    return ps.linear_extrude(rrect(l, w, r), height=h)

def chamfered_rbox(l, w, h, r, c):
    bottom = ps.linear_extrude(rrect(l - 2 * c, w - 2 * c, max(r - c, 0.01)), height=0.01).translate([c, c, 0])
    top = rbox(l, w, 0.01, r).translate([0, 0, c])
    return ps.hull(bottom, top) | rbox(l, w, h - c, r).translate([0, 0, c])

def cyl(d, h):
    return ps.cylinder(d=d, h=h, fn=fn)

def box(x0, y0, z0, x1, y1, z1):
    return ps.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])

# wall frames: local x along the wall (reading direction from outside), local y = up, local z = outwards
_ROT = {"front": [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
        "back":  [[-1, 0, 0], [0, 0, 1], [0, 1, 0]],
        "left":  [[0, 0, -1], [-1, 0, 0], [0, 1, 0]],
        "right": [[0, 0, 1], [1, 0, 0], [0, 1, 0]]}

def on_wall(obj, wall_name, u, z):
    """Place a local object on the INNER face of a wall. u = world coordinate along the wall
    (X for front/back, Y for left/right, inner coords), z = height above the floor."""
    il, iw = G["inner_l"], G["inner_w"]
    p = {"front": (wall + u, wall, floor_t + z), "back": (wall + u, wall + iw, floor_t + z),
         "left": (wall, wall + u, floor_t + z), "right": (wall + il, wall + u, floor_t + z)}[wall_name]
    R = _ROT[wall_name]
    return ps.multmatrix(obj, [R[0] + [p[0]], R[1] + [p[1]], R[2] + [p[2]], [0, 0, 0, 1]])

def through(profile):
    """Cutter through the wall from a 2D profile centred on (0,0)."""
    return ps.linear_extrude(profile, height=wall + 2).translate([0, 0, -1])

def window_profile(w, h, ch):
    ch = min(ch, h / 3, w / 3)
    return ps.polygon([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2 - ch], [w / 2 - ch, h / 2],
                       [-w / 2 + ch, h / 2], [-w / 2, h / 2 - ch]])

def hole_profile(d, flat=0.0):
    c = ps.circle(d=d, fn=fn)
    r = d / 2
    if teardrop:
        c = ps.hull(c, ps.polygon([[-r * 0.7071, r * 0.7071], [r * 0.7071, r * 0.7071], [0, r * 1.4142]]))
    if flat > 0:
        c = c & ps.square([d + 2, flat]).translate([-(d + 2) / 2, -r, 0])   # flat on top (z = -r + flat)
    return c

def hole_top(d, flat=0.0):
    if flat > 0:
        return flat - d / 2
    return d / 2 * (1.4142 if teardrop else 1.0)

def text_w(txt):
    return ps.textmetrics(txt, size=label_size, font=label_font)["size"][0]

# =============================================================================
# WALL FEATURES
# =============================================================================

def wall_openings():
    """list of dict(wall, name, u, z, cut(local solid), box=(u0,u1,z0,z1), label, label_pos)"""
    ops = []
    # USB-C (left wall)
    uy = EY0() + EPW() / 2
    ow, oh = (usb_recess_w, usb_recess_h) if usb_recess else (usb_cut_w, usb_cut_h)
    cut = through(window_profile(usb_cut_w, usb_cut_h, window_chamfer))
    if usb_recess:
        cut = cut | box(-usb_recess_w / 2, -usb_recess_h / 2, usb_recess_wall, usb_recess_w / 2, usb_recess_h / 2, wall + 1)
    ops.append(dict(wall="left", name="USB-C", u=uy, z=usb_cut_z, cut=cut,
                    box=(uy - ow / 2, uy + ow / 2, usb_cut_z - oh / 2, usb_cut_z + oh / 2), label="USB", label_pos="above"))
    # 12 V (left wall)
    if power_entry == "jack":
        ops.append(dict(wall="left", name="12V jack", u=JY(), z=jack_z, cut=through(hole_profile(jack_d, jack_flat)),
                        box=(JY() - jack_d / 2, JY() + jack_d / 2, jack_z - jack_d / 2, jack_z + hole_top(jack_d, jack_flat)),
                        label="12V IN", label_pos="above"))
    else:
        ops.append(dict(wall="left", name="12V hole", u=JY(), z=cable_z, cut=through(hole_profile(power_hole_d)),
                        box=(JY() - power_hole_d / 2, JY() + power_hole_d / 2, cable_z - power_hole_d / 2, cable_z + hole_top(power_hole_d)),
                        label="12V IN", label_pos="above"))
    # FAN (front)
    if fan_entry == "slot":
        ops.append(dict(wall="front", name="fan slot", u=fan_x, z=cable_z, cut=through(window_profile(fan_slot_w, fan_slot_h, window_chamfer)),
                        box=(fan_x - fan_slot_w / 2, fan_x + fan_slot_w / 2, cable_z - fan_slot_h / 2, cable_z + fan_slot_h / 2),
                        label="FAN", label_pos="above"))
    else:
        ops.append(dict(wall="front", name="fan hole", u=fan_x, z=cable_z, cut=through(hole_profile(fan_hole_d)),
                        box=(fan_x - fan_hole_d / 2, fan_x + fan_hole_d / 2, cable_z - fan_hole_d / 2, cable_z + hole_top(fan_hole_d)),
                        label="FAN", label_pos="above"))
    # SENSOR (front)
    ops.append(dict(wall="front", name="DHT22 hole", u=dht_x, z=cable_z, cut=through(hole_profile(dht_hole_d)),
                    box=(dht_x - dht_hole_d / 2, dht_x + dht_hole_d / 2, cable_z - dht_hole_d / 2, cable_z + hole_top(dht_hole_d)),
                    label="SENSOR", label_pos="above"))
    return ops

def vent_slots():
    """(wall, u_centre) for every vent slot: front and back walls, across the buck pocket."""
    x0, x1 = G["buck_x0"] - 2, G["buck_x0"] + BPW() + 2
    n = int((x1 - x0 - vent_w) // vent_pitch) + 1
    start = (x0 + x1) / 2 - (n - 1) * vent_pitch / 2
    us = [start + i * vent_pitch for i in range(n)]
    return [("front", u) for u in us] + [("back", u) for u in us]

def label_layout(ops):
    """(wall, text, u, zc, box) - labels above their opening, slid sideways if crowded."""
    out = []
    obst = {}
    for o in ops:
        obst.setdefault(o["wall"], []).append(o["box"])
    for w, u in vent_slots():
        obst.setdefault(w, []).append((u - vent_w / 2, u + vent_w / 2, vent_z0, vent_z0 + vent_len))
    placed = {}
    lim = {"front": (G["inner_l"], ), "back": (G["inner_l"], ), "left": (G["inner_w"], ), "right": (G["inner_w"], )}
    for o in ops:
        w = text_w(o["label"])
        zc = o["box"][3] + label_gap + label_size / 2
        if o["label_pos"] == "below":
            zc = o["box"][2] - label_gap - label_size / 2
        hi = lim[o["wall"]][0] + wall - r_out - 0.6
        lo = -wall + r_out + 0.6
        best = None
        for du in sorted([i * 0.25 for i in range(-60, 61)], key=abs):
            b = (o["u"] + du - w / 2, o["u"] + du + w / 2, zc - label_size / 2, zc + label_size / 2)
            if b[0] < lo or b[1] > hi:
                continue
            if not any(_near(b, ob, 1.0) for ob in obst.get(o["wall"], []) + placed.get(o["wall"], [])):
                best = b
                break
        if best is None:
            best = (o["u"] - w / 2, o["u"] + w / 2, zc - label_size / 2, zc + label_size / 2)
        placed.setdefault(o["wall"], []).append(best)
        out.append((o["wall"], o["label"], (best[0] + best[1]) / 2, zc, best))
    return out

def _near(a, b, m):
    return not (a[1] + m <= b[0] or b[1] + m <= a[0] or a[3] + m <= b[2] or b[3] + m <= a[2])

def label_solid(wall_name, txt, u, zc):
    t = ps.text(txt, size=label_size, font=label_font, halign="center", valign="center", fn=fn)
    t3 = ps.linear_extrude(t, height=label_relief + 0.01).translate([0, 0, wall - 0.01])
    return on_wall(t3, wall_name, u, zc)

# =============================================================================
# SEATS (pocket rim, ledges, latches)
# =============================================================================

def latch(catch_z, nose, L, nose_w=None):
    """Spring latch in local coords: plate x in [0, latch_t] (local +x = away from the pocket),
    free end at y = +nose_w/2, root at y = -L; nose at y in [-w/2, w/2] reaching to x = -nose,
    flat underside at world height catch_z (+0.1), 45 deg lead-in on top. z is WORLD height."""
    nw = nose_w or latch_nose_w
    w2 = nw / 2
    zc = floor_t + catch_z + 0.1
    e = latch_t / 2                                           # nose overlaps into the plate (one solid)
    plate = box(0, -L - 1.0, 0, latch_t, w2, zc + nose + e)  # 1 mm into the root (rim + floor)
    prof = ps.polygon([[e, zc], [e, zc + nose + e], [-nose, zc]])   # 45 deg lead-in, counter-clockwise
    n = ps.linear_extrude(prof, height=nw).rotate([90, 0, 0]).translate([0, w2, 0])
    return plate | n

def latch_slot(catch_z, nose, L, nose_w=None):
    """Cutter around the latch plate: through the floor, the rim and the ledge (local coords)."""
    w2 = (nose_w or latch_nose_w) / 2
    return box(-latch_gap, -L, -1, latch_t + nose + latch_back, w2 + 0.5, floor_t + catch_z + nose + 1)

def place_w(obj, x, y, rot):
    """Local coords (world z) -> world at inner (x, y), rotated about Z by rot degrees."""
    return obj.rotate([0, 0, rot]).translate([wall + x, wall + y, 0])

def ledge_boxes(segs, a0, b0, a1, b1, along_x):
    """Ledge segments; ranges are measured from the pocket start, negative values from its end."""
    out = []
    for (u0, u1), (v0, v1) in segs:
        ua = lambda u: a0 + u if u >= 0 and not (u == 0 and u0 < 0) else a1 + u
        va = lambda v: b0 + v if v >= 0 and not (v == 0 and v0 < 0) else b1 + v
        A0, A1 = sorted((ua(u0), ua(u1)))
        B0, B1 = sorted((va(v0), va(v1)))
        out.append(box(A0, B0, 0, A1, B1, ledge_h) if along_x else box(B0, A0, 0, B1, A1, ledge_h))
    return out

def seat_esp():
    """Rim around the ESP pocket (not at the USB wall), ledges under both short ends,
    latch at the antenna end, wedge from the USB wall."""
    x0, x1 = G["esp_x0"], G["esp_x1"]
    y0, y1 = EY0(), EY0() + EPW()
    top = ledge_h + esp_pcb_t
    add = [box(x0, y0 - rim_t, 0, x1 + rim_t, y0, top),            # front rim
           box(x0, y1, 0, x1 + rim_t, y1 + rim_t, top),            # back rim
           box(x1, y0 - rim_t, 0, x1 + rim_t, y1 + rim_t, top),    # antenna-end rim
           ] + ledge_boxes(esp_ledges, x0 + usb_overhang, y0, x1, y1, along_x=True)
    add = [ps.translate(a, [wall, wall, floor_t]) for a in add]
    cut = []
    # spring latch at the antenna end, beside the antenna; nose points -X over the PCB end
    hy = y0 + (EPW() - esp_pcb_w) / 2 + esp_latch_y
    nose = (x1 - (x0 + usb_overhang + esp_pcb_l)) + latch_over
    cut.append(place_w(latch_slot(top, nose, latch_len, esp_latch_w), x1, hy, 0))
    lt = place_w(latch(top, nose, latch_len, esp_latch_w), x1, hy, 0)
    return add, cut, [lt], dict(esp_latch_nose=nose)

def seat_buck():
    x0, x1 = G["buck_x0"], G["buck_x0"] + BPW()
    y0, y1 = G["buck_y0"], G["buck_y0"] + BPL()
    top = ledge_h + buck_pcb_t
    add = [box(x0 - rim_t, y0 - rim_t, 0, x1 + rim_t, y0, top), box(x0 - rim_t, y1, 0, x1 + rim_t, y1 + rim_t, top),
           box(x0 - rim_t, y0, 0, x0, y1, top), box(x1, y0, 0, x1 + rim_t, y1, top),
           ] + ledge_boxes(buck_ledges, y0, x0, y1, x1, along_x=False)
    add = [ps.translate(a, [wall, wall, floor_t]) for a in add]
    cut, latches = [], []
    nose = (BPW() - buck_pcb_w) / 2 + latch_over
    yn = y0 + (BPL() - buck_pcb_l) / 2 + buck_pcb_l - buck_latch_from_vin      # VIN end is at the back (+Y)
    for xe, rot in ((x1, 0), (x0, 180)):
        cut.append(place_w(latch_slot(top, nose, latch_len, buck_latch_w), xe, yn, rot))
        latches.append(place_w(latch(top, nose, latch_len, buck_latch_w), xe, yn, rot))
    return add, cut, latches

def usb_wedge_solid():
    """Wedge on the inside of the left wall above the USB receptacle: 45 deg underside,
    reaches usb_wedge_len over the receptacle; its root starts at the cutout top."""
    uy = EY0() + EPW() / 2
    z_root = usb_cut_z + usb_cut_h / 2          # cutout top edge
    L = usb_wedge_len + 0.25                     # +gap pocket-wall -> receptacle face
    h = L + 2.0
    prof = ps.polygon([[0, 0], [L, L], [L, h], [0, h]])   # x = into the box, y = up
    w = usb_w + 2.0
    wedge = ps.linear_extrude(prof, height=w).rotate([90, 0, 0]).translate([0, w / 2, 0])
    return wedge.translate(W(0, uy, z_root))

def wago_cradle():
    x0, y0 = G["wago_x0"], G["wago_y0"]
    iw = G["inner_w"]
    parts = []
    for i in range(3):
        xi = x0 + i * (wago_w + wago_wall)
        parts.append(box(xi, y0, 0, xi + wago_wall, iw, wago_wall_h))
    return [ps.translate(p, [wall, wall, floor_t]) for p in parts]

def zip_anchor(x, y, rot):
    blk = box(-anchor_l / 2, -anchor_w / 2, 0, anchor_l / 2, anchor_w / 2, anchor_h)
    tun = box(-anchor_l / 2 - 1, -tunnel_w / 2, 0.8, anchor_l / 2 + 1, tunnel_w / 2, 0.8 + tunnel_h)
    # 45 deg chamfered top edges along the tunnel direction keep it smooth; tunnel ceiling bridge = tunnel_w
    return (blk - tun).rotate([0, 0, rot]).translate(W(x, y, 0))

def post_centres():
    il, iw = G["inner_l"], G["inner_w"]
    front_mid = (G["esp_x1"] + margin + G["buck_x0"] - margin) / 2
    return [(front_mid, post_inset), (il - post_inset, post_inset), (post_inset, iw - post_inset), (il - post_inset, iw - post_inset)]

def snap_positions():
    if snap_pos is not None:
        return snap_pos
    front_mid = (G["esp_x1"] + margin + G["buck_x0"] - margin) / 2
    buck_mid = G["buck_x0"] + BPW() / 2
    return [("front", front_mid), ("front", buck_mid), ("back", 12.0), ("back", buck_mid)]

def snap_geometry():
    """Heights (above the floor) of the arm bottom and of the catch window."""
    h0 = G["inner_h"] - snap_len
    p = snap_engage + tol                      # nose reach beyond the arm's outer face
    lead = 1.732 * (p + 0.6)                  # 30 deg lead-in (from vertical)
    flat = 0.4
    top = h0 + lead + flat + p + 0.6           # top of the nose
    win0 = h0 + 1.732 * (p - snap_engage + 0.6) - 0.3     # where the nose starts to enter the wall, minus clearance
    win1 = h0 + lead + flat + 0.6 + tol + snap_play         # catch face where it crosses the wall face (+ play)
    return dict(h0=h0, p=p, lead=lead, flat=flat, top=top, win0=win0, win1=win1)

def snap_arm_local():
    """Arm in on_wall local coords (x along wall, y = height above floor, z = outwards).
    Outer face at z = -tol, nose reaching to z = -tol + p (into the wall window)."""
    g = snap_geometry()
    arm = box(-snap_w / 2, g["h0"], -tol - snap_t, snap_w / 2, G["inner_h"] + 0.5, -tol)
    e = 0.6
    prof = ps.polygon([[-tol - e, g["h0"]], [-tol + g["p"], g["h0"] + g["lead"]], [-tol + g["p"], g["h0"] + g["lead"] + g["flat"]],
                       [-tol - e, g["h0"] + g["lead"] + g["flat"] + g["p"] + e]])
    nose = ps.multmatrix(ps.linear_extrude(prof, height=snap_w), [[0, 0, -1, snap_w / 2], [0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1]])
    return arm | nose

def snap_window_local():
    g = snap_geometry()
    w = snap_w + 1.0
    return box(-w / 2, g["win0"], -1, w / 2, g["win1"], wall + 1)

def magnet_centres():
    il, iw = G["inner_l"], G["inner_w"]
    if lid_fix == "screws":
        return post_centres()
    m = magnet_inset
    return [(m, m), (il - m, m), (m, iw - m), (il - m, iw - m)]

def post_solid(px, py, h):
    """Post fused to the nearest wall(s): hull of the cylinder and the wall contact point(s)."""
    il, iw = G["inner_l"], G["inner_w"]
    pts = []
    near_x = 0.0 if px < post_inset + 0.01 else (il - 0.01 if px > il - post_inset - 0.01 else None)
    near_y = 0.0 if py < post_inset + 0.01 else (iw - 0.01 if py > iw - post_inset - 0.01 else None)
    if near_x is not None and near_y is not None:
        pts.append(ps.cube([0.01, 0.01, h]).translate(W(near_x, near_y)))
    elif near_y is not None:
        pts.append(ps.cube([post_d, 0.01, h]).translate(W(px - post_d / 2, near_y)))
    elif near_x is not None:
        pts.append(ps.cube([0.01, post_d, h]).translate(W(near_x, py - post_d / 2)))
    return ps.hull(cyl(post_d, h).translate(W(px, py)), *pts)

# =============================================================================
# BASE
# =============================================================================

def base():
    ol, ow, bh = G["outer_l"], G["outer_w"], G["base_h"]
    il, iw = G["inner_l"], G["inner_w"]
    body = chamfered_rbox(ol, ow, bh, r_out, chamfer) - rbox(il, iw, bh, 0).translate([wall, wall, floor_t])

    add, cut = [], []
    ph = G["inner_h"]
    if lid_fix == "screws":
        for (px, py) in post_centres():
            add.append(post_solid(px, py, ph))
    elif magnets:
        for (mx, my) in magnet_centres():
            add.append(cyl(magnet_boss_d, magnet_boss_h + 0.01).translate(W(mx, my, -0.01)))
    a, c, latches_e, _ = seat_esp()
    add += a; cut += c
    a, c, latches_b = seat_buck()
    add += a; cut += c
    add += wago_cradle()
    for (x, y, r) in anchors:
        add.append(zip_anchor(x, y, r))
    if tabs:
        for side in (0, 1):
            t = rbox(tab_len + 2 * tab_r, tab_w, tab_t, tab_r).translate([-tab_len, wall + TY() - tab_w / 2, 0])
            t = t & box(-tab_len - 1, -1, -1, wall / 2, ow + 1, tab_t + 1)     # stops inside the wall
            add.append(t if side == 0 else t.mirror([1, 0, 0]).translate([ol, 0, 0]))
    if usb_wedge:
        add.append(usb_wedge_solid())
    body = body | ps.union(*add)

    ops = wall_openings()
    for o in ops:
        cut.append(on_wall(o["cut"], o["wall"], o["u"], o["z"]))
    for (w, u) in vent_slots():
        cut.append(on_wall(through(ps.square([vent_w, vent_len]).translate([-vent_w / 2, 0, 0])), w, u, vent_z0))
    if lid_fix == "screws":
        for (px, py) in post_centres():
            cut.append(cyl(lid_screw_pilot, post_hole_depth + 0.01).translate([wall + px, wall + py, bh - post_hole_depth]))
    else:
        for (w_, u) in snap_positions():
            cut.append(on_wall(snap_window_local(), w_, u, 0))
    if magnets:
        for (mx, my) in magnet_centres():
            cut.append(cyl(magnet_hole_d, magnet_depth + 0.01).translate([wall + mx, wall + my, -0.01]))
    if tabs:
        for tx in (-tab_len / 2 - 0.5, ol + tab_len / 2 + 0.5):
            cut.append(cyl(tab_hole_d, tab_t + 2).translate([tx, wall + TY(), -1]))
    body = body - ps.union(*cut)
    # latches are added after the cuts (they stand in slots cut through floor, rim and ledge)
    body = body | ps.union(*(latches_e + latches_b))
    if labels:
        body = body | ps.union(*[label_solid(w, t, u, z) for (w, t, u, z, _) in label_layout(ops)])
    return body

# =============================================================================
# LID
# =============================================================================

def led_xy():
    return (G["esp_x0"] + usb_overhang + led_from_usb, EY0() + (EPW() - esp_pcb_w) / 2 + led_from_front)

def lid_assembled():
    ol, ow, bh = G["outer_l"], G["outer_w"], G["base_h"]
    il, iw = G["inner_l"], G["inner_w"]
    plate = chamfered_rbox(ol, ow, lid_t, r_out, chamfer).mirror([0, 0, 1]).translate([0, 0, bh + lid_t])
    ring = ps.linear_extrude(ps.offset(ps.square([il, iw]), delta=-tol) - ps.offset(ps.square([il, iw]), delta=-(tol + lip_t)),
                             height=lip_h + 0.01).translate([wall, wall, bh - lip_h])
    if lid_fix == "screws":
        r = post_d / 2 + tol
        for (px, py) in post_centres():
            x0 = -1 if px <= post_inset + 0.01 else px - r
            x1 = il + 1 if px >= il - post_inset - 0.01 else px + r
            y0 = -1 if py <= post_inset + 0.01 else py - r
            y1 = iw + 1 if py >= iw - post_inset - 0.01 else py + r
            ring = ring - box(wall + x0, wall + y0, bh - lip_h - 1, wall + x1, wall + y1, bh + 0.5)
        lid = plate | ring
    else:
        for (w_, u) in snap_positions():      # gap in the lip around each arm so it can flex
            ring = ring - on_wall(box(-snap_w / 2 - 0.6, G["inner_h"] - lip_h - 1, -5, snap_w / 2 + 0.6, G["inner_h"] + 0.2, 1), w_, u, 0)
        lid = plate | ring | ps.union(*[on_wall(snap_arm_local(), w_, u, 0) for (w_, u) in snap_positions()])
    lx, ly = led_xy()
    if led_window and light_pipe:
        z_end = floor_t + ledge_h + esp_pcb_t + light_pipe_gap
        lid = lid | cyl(light_pipe_od, bh - z_end + 0.01).translate([wall + lx, wall + ly, z_end])
    cut = [cyl(lid_hole_d, lid_t + 2).translate([wall + px, wall + py, bh - 1]) for (px, py) in post_centres()] \
        if lid_fix == "screws" else []
    if led_window:
        cut.append(cyl(led_hole_d, bh).translate([wall + lx, wall + ly, 10]))
    return lid - ps.union(*cut) if cut else lid

def lid_print():
    """Lid turned over for printing: a 180 deg ROTATION about the X axis (not a mirror, which would
    swap front and back). Flip it back over its long edge to put it on the box."""
    return lid_assembled().rotate([180, 0, 0]).translate([0, G["outer_w"], G["base_h"] + lid_t])

# =============================================================================
# DUMMY PARTS (checks / previews only)
# =============================================================================

def dupont_row(x0, y, z_pcb_top, n, along="x", pitch=2.54):
    """n Dupont housings (2.54 x 2.54 x 14, seated 3.5 above the PCB) on a header row."""
    hs = []
    for i in range(n):
        if along == "x":
            hs.append(box(x0 + i * pitch - 1.27, y - 1.27, z_pcb_top + 3.5, x0 + i * pitch + 1.27, y + 1.27, z_pcb_top + 17.5))
        else:
            hs.append(box(y - 1.27, x0 + i * pitch - 1.27, z_pcb_top + 3.5, y + 1.27, x0 + i * pitch + 1.27, z_pcb_top + 17.5))
    return ps.union(*hs)

def components():
    c = {}
    # ESP: pushed against the USB wall, centred in the pocket width
    ex0 = G["esp_x0"] + usb_overhang      # PCB starts behind the overhanging USB-C receptacle
    ey0 = EY0() + (EPW() - esp_pcb_w) / 2
    ez = ledge_h
    pcb = box(ex0, ey0, ez, ex0 + esp_pcb_l, ey0 + esp_pcb_w, ez + esp_pcb_t)
    top = ez + esp_pcb_t
    rows = [ey0 + 1.38, ey0 + esp_pcb_w - 1.38]
    strips = ps.union(*[box(ex0 + 0.32, r - 1.27, top, ex0 + 0.32 + 22.86, r + 1.27, top + 2.5) for r in rows])
    stubs = ps.union(*[cyl(1.7, 2.6).translate([ex0 + 1.59 + i * 2.54, r, ez - 2.6]) for r in rows for i in range(9)])
    usb = box(G["esp_x0"], ey0 + esp_pcb_w / 2 - usb_w / 2, top, G["esp_x0"] + usb_len, ey0 + esp_pcb_w / 2 + usb_w / 2, top + usb_h)
    c["ESP PCB"] = ps.translate(pcb | strips | stubs, [wall, wall, floor_t])
    c["ESP USB-C"] = ps.translate(usb, [wall, wall, floor_t])
    c["ESP antenna"] = ps.translate(box(ex0 + esp_pcb_l - 2.2, ey0 + antenna_y[0], top, ex0 + esp_pcb_l, ey0 + antenna_y[1], top + 1.2),
                                    [wall, wall, floor_t])
    c["ESP Dupont plugs"] = ps.translate(ps.union(*[dupont_row(ex0 + 1.59, r, top, 9) for r in rows]), [wall, wall, floor_t])
    # buck
    bx0 = G["buck_x0"] + (BPW() - buck_pcb_w) / 2
    by0 = G["buck_y0"] + (BPL() - buck_pcb_l) / 2
    bz = ledge_h
    btop = bz + buck_pcb_t
    bm = box(bx0, by0, bz, bx0 + buck_pcb_w, by0 + buck_pcb_l, btop) | \
        box(bx0 + 1.0, by0 + 3.0, btop, bx0 + buck_pcb_w - 1.0, by0 + buck_pcb_l - 5.5, bz + buck_h)   # parts: >= 1 mm from the long edges, clear of the pin holes
    # pin positions: "across" is measured from the long edge that faces +X (the photo's top edge)
    pins = [(bx0 + buck_pcb_w - a, by0 + buck_pcb_l - buck_vin_holes[0], 2.0) for a in buck_vin_holes[1]] + \
           [(bx0 + buck_pcb_w - a, by0 + buck_out_pins[0], 1.7) for a in buck_out_pins[1]]
    bstubs = ps.union(*[cyl(d, 2.6).translate([px, py, bz - 2.6]) for (px, py, d) in pins])
    c["buck module"] = ps.translate(bm | bstubs, [wall, wall, floor_t])
    # the two output capacitors that sit 0.4 mm from one long edge (photo: bottom edge, 19-30 mm from the VIN end)
    c["buck edge capacitors"] = ps.translate(box(bx0 + 0.4, by0 + buck_pcb_l - 30.0, btop, bx0 + 2.4, by0 + buck_pcb_l - 19.0, btop + 1.2),
                                             [wall, wall, floor_t])
    c["buck Dupont plugs"] = ps.translate(ps.union(*[box(px - 1.27, py - 1.27, btop + 3.5, px + 1.27, py + 1.27, btop + 17.5)
                                                     for (px, py, d) in pins]), [wall, wall, floor_t])
    # WAGOs (13.1 x 18.6 x 8.1) + levers open (12 mm up)
    ws = []
    for i in range(2):
        xi = G["wago_x0"] + wago_wall + i * (wago_w + wago_wall) + (wago_w - 13.1) / 2
        ws.append(box(xi, G["inner_w"] - 18.6 - 0.3, 0, xi + 13.1, G["inner_w"] - 0.3, 8.1))
    c["WAGO 221-413"] = ps.translate(ps.union(*ws), [wall, wall, floor_t])
    if power_entry == "jack":
        nut = ps.cylinder(d=12.7, h=2.0, fn=6).rotate([0, 90, 0]).translate(W(0.01, JY(), jack_z))
        bodyj = cyl(11.0, jack_depth - 2.0).rotate([0, 90, 0]).translate(W(2.0, JY(), jack_z))
        c["DC jack (metal)"] = nut | bodyj
    return c

def usb_plug():
    uy = EY0() + EPW() / 2
    stop = (wall - usb_recess_wall) if usb_recess else 0.0          # plug overmold stops here (world x)
    zc = floor_t + usb_cut_z
    shell = box(stop, wall + uy - 4.125, zc - 1.2, stop + 6.6, wall + uy + 4.125, zc + 1.2)
    mold = box(stop - 20, wall + uy - 6.0, zc - 3.25, stop, wall + uy + 6.0, zc + 3.25)
    return shell, mold

def metal_parts():
    """Metal near the antenna: jack, WAGO clamps, buck module, screws, magnets (for distance checks)."""
    m = {}
    c = components()
    for k in ("buck module", "WAGO 221-413", "DC jack (metal)"):
        if k in c:
            m[k] = c[k]
    if lid_fix == "screws":
        m["lid screws"] = ps.union(*[cyl(3.0, post_hole_depth + lid_t).translate([wall + px, wall + py, G["base_h"] - post_hole_depth])
                                     for (px, py) in post_centres()])
    if magnets:
        m["magnets"] = ps.union(*[cyl(4.0, 2.0).translate([wall + px, wall + py, 0]) for (px, py) in magnet_centres()])
    return m

def antenna_zone():
    """Last 4 mm of the ESP at the antenna end (PCB to 2 mm above)."""
    ex1 = G["esp_x0"] + usb_overhang + esp_pcb_l
    ey0 = EY0() + (EPW() - esp_pcb_w) / 2
    return ps.translate(box(ex1 - 2.2, ey0 + antenna_y[0], ledge_h, ex1, ey0 + antenna_y[1], ledge_h + esp_pcb_t + 2), [wall, wall, floor_t])

# =============================================================================
# CLI
# =============================================================================

def build(part):
    setup()
    if part == "base":
        return base()
    if part == "lid":
        return lid_print()
    if part == "lid_assembled":
        return lid_assembled()
    if part == "assembly":
        return base() | lid_assembled()
    if part == "components":
        return ps.union(*components().values())
    if part == "plug":
        return ps.union(*usb_plug())
    raise SystemExit("part must be base, lid, lid_assembled, assembly, components or plug")

def apply_overrides(args):
    gl = globals()
    for a in args:
        k, v = a.split("=", 1)
        if k not in gl:
            raise SystemExit(f"unknown parameter: {k}")
        gl[k] = eval(v, {}, {})

if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    apply_overrides(sys.argv[3:])
    ps.export(build(sys.argv[1]), sys.argv[2])
    print("wrote", sys.argv[2], {k: round(v, 1) for k, v in G.items()})
