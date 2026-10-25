#!/usr/bin/env python3
"""Verification for enclosure.py (Dupont/WAGO version).
Usage: check.py <outdir> [param=value ...]
Needs: pythonscad trimesh manifold3d shapely scipy rtree"""
import os, sys, json, itertools
import numpy as np
import trimesh
import pythonscad as ps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE if os.path.exists(os.path.join(HERE, "enclosure.py")) else os.path.join(HERE, ".."))
import enclosure as E

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
E.apply_overrides(sys.argv[2:])
E.setup()
G = E.G
problems, notes = [], []

def export(obj, name):
    p = os.path.join(OUT, name)
    ps.export(obj, p)
    return trimesh.load(p, force="mesh")

def inter_vol(a, b):
    try:
        r = trimesh.boolean.intersection([a, b], engine="manifold")
        return 0.0 if r.is_empty else float(r.volume)
    except Exception:
        return float("nan")

def min_dist(a, b, n=5000):
    pts = np.vstack([a.sample(n), a.vertices])
    _, d, _ = trimesh.proximity.closest_point(b, pts)
    return float(d.min())

def boxmesh(x0, y0, z0, x1, y1, z1):
    return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])

# ------------------------------------------------------------------ meshes
base = export(E.base(), "base.stl")
lid_a = export(E.lid_assembled(), "lid_assembled.stl")
lid_p = export(E.lid_print(), "lid.stl")
comps_ps = E.components()
comps = {k: export(v, f"_c_{i}.stl") for i, (k, v) in enumerate(comps_ps.items())}
export(ps.union(*comps_ps.values()), "components.stl")
shell, mold = E.usb_plug()
shell_m, mold_m = export(shell, "_shell.stl"), export(mold, "_mold.stl")
export(ps.union(shell, mold), "plug.stl")
metal = {k: export(v, f"_m_{i}.stl") for i, (k, v) in enumerate(E.metal_parts().items())}
ant = export(E.antenna_zone(), "_antenna.stl")

# the print-orientation lid, flipped back over its long edge, must be exactly the assembled lid
flip = lid_p.copy()
flip.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
flip.apply_translation([0, G["outer_w"], G["base_h"] + E.lid_t])
diff = trimesh.boolean.difference([flip, lid_a], engine="manifold").volume + trimesh.boolean.difference([lid_a, flip], engine="manifold").volume
if diff > 0.5:
    problems.append(f"lid.stl flipped over does not match the assembled lid ({diff:.1f} mm^3 differ) - mirrored export?")

for name, m in (("base", base), ("lid", lid_p)):
    if not m.is_watertight:
        problems.append(f"{name} mesh not watertight")
    nb = len(m.split(only_watertight=False))
    if nb != 1:
        problems.append(f"{name} has {nb} separate bodies")
    if abs(m.bounds[0][2]) > 1e-6:
        problems.append(f"{name} does not sit on z=0")

dims = dict(outer=(G["outer_l"], G["outer_w"], G["outer_h"]), inner=(G["inner_l"], G["inner_w"], G["inner_h"]),
            footprint_with_tabs=tuple(np.round(base.bounds[1][:2] - base.bounds[0][:2], 1)),
            base_cm3=round(base.volume / 1000, 1), lid_cm3=round(lid_p.volume / 1000, 1))

# ------------------------------------------------------------------ collisions
skip_pairs = [{"ESP PCB", "ESP USB-C"}, {"ESP PCB", "ESP Dupont plugs"}, {"ESP PCB", "ESP antenna"}, {"buck module", "buck edge capacitors"}]
for k, m in comps.items():
    for nm, enc in (("base", base), ("lid", lid_a)):
        v = inter_vol(m, enc)
        if v > 0.001:
            problems.append(f"{k} collides with {nm} ({v:.2f} mm^3)")
for (a, ma), (b, mb) in itertools.combinations(comps.items(), 2):
    if {a, b} in skip_pairs:
        continue
    v = inter_vol(ma, mb)
    if v > 0.001:
        problems.append(f"{a} collides with {b} ({v:.2f} mm^3)")
v = inter_vol(base, lid_a)
if v > 0.001:
    problems.append(f"lid intersects base ({v:.2f} mm^3)")
clear = {k: (round(min_dist(m, base), 2), round(min_dist(m, lid_a), 2)) for k, m in comps.items()}

# ------------------------------------------------------------------ headroom
ft = E.floor_t
esp_top = ft + E.ledge_h + E.esp_pcb_t
buck_top = ft + E.ledge_h + E.buck_pcb_t
lid_under = G["base_h"]
head = dict(esp=round(lid_under - esp_top, 2), buck=round(lid_under - buck_top, 2))
for k, v in head.items():
    if v < E.headroom - 1e-6:
        problems.append(f"headroom above {k} PCB {v} < {E.headroom}")

# ------------------------------------------------------------------ 10 mm zones around the modules
w = E.wall
zones = {}
ex0, ex1 = w + G["esp_x0"], w + G["esp_x1"]
ey0, ey1 = w + E.EY0(), w + E.EY0() + E.EPW()
nose_e = (E.EPL() - E.esp_pcb_l - E.usb_overhang) + E.latch_over + E.latch_t / 2
zones["ESP"] = boxmesh(ex0 + 0.01, ey0 - E.margin, esp_top + nose_e + 0.6, ex1 + E.margin, ey1 + E.margin, lid_under - E.lip_h - 0.01)
bx0, bx1 = w + G["buck_x0"], w + G["buck_x0"] + E.BPW()
by0, by1 = w + G["buck_y0"], w + G["buck_y0"] + E.BPL()
nose_b = (E.BPW() - E.buck_pcb_w) / 2 + E.latch_over + E.latch_t / 2
zones["buck"] = boxmesh(bx0 - E.margin, by0 - E.margin, buck_top + nose_b + 0.6, bx1 + E.margin, by1 + E.margin, lid_under - E.lip_h - 0.01)
zone_report = {}
for zn, zm in zones.items():
    rep = {}
    v = inter_vol(zm, base)
    if v > 0.01:
        rep["base (posts/wedge)"] = round(v, 1)
    for k, m in comps.items():
        if (zn == "ESP" and k.startswith("ESP")) or (zn == "buck" and k.startswith("buck")):
            continue
        v = inter_vol(zm, m)
        if v > 0.01:
            rep[k] = round(v, 1)
            problems.append(f"{k} intrudes into the {E.margin:.0f} mm zone around the {zn} ({v:.1f} mm^3)")
    zone_report[zn] = rep
# what intrudes from the base: only allowed are the corner posts and the USB wedge
post_meshes = []
for (px, py) in (E.post_centres() if E.lid_fix == "screws" else []):
    c = trimesh.creation.cylinder(radius=E.post_d / 2 + 0.6, height=200)
    c.apply_translation([w + px, w + py, 0])
    post_meshes.append(c)
for zn, zm in zones.items():
    rest = zm
    for pm in post_meshes:
        rest = trimesh.boolean.difference([rest, pm], engine="manifold")
    if zn == "ESP":
        rest = trimesh.boolean.difference([rest, boxmesh(w - 1, ey0 - 1, 0, w + 3, ey1 + 1, 100)], engine="manifold")   # USB wedge
    v = inter_vol(rest, base)
    if v > 0.05:
        problems.append(f"enclosure geometry (other than corner posts / USB wedge) intrudes into the {zn} zone ({v:.1f} mm^3)")
    lid_rest = lid_a
    if E.light_pipe and E.led_window and zn == "ESP":     # the light pipe is meant to sit over the ESP (between the pin rows)
        lx, ly = E.led_xy()
        lp = trimesh.creation.cylinder(radius=E.light_pipe_od / 2 + 0.3, height=200)
        lp.apply_translation([w + lx, w + ly, 0])
        lid_rest = trimesh.boolean.difference([lid_a, lp], engine="manifold")
    v = inter_vol(zones[zn], lid_rest)
    if v > 0.05:
        problems.append(f"lid (snap arms / lip) intrudes into the {zn} zone ({v:.1f} mm^3)")
# distance of the corner posts to the module footprints
post_clear = {}
for zn, (x0, y0, x1, y1) in (("ESP", (ex0, ey0, ex1, ey1)), ("buck", (bx0, by0, bx1, by1))):
    ds = []
    for (px, py) in (E.post_centres() if E.lid_fix == "screws" else []):
        cx, cy = w + px, w + py
        dx = max(x0 - cx, 0, cx - x1)
        dy = max(y0 - cy, 0, cy - y1)
        ds.append((dx * dx + dy * dy) ** 0.5 - E.post_d / 2)
    post_clear[zn] = round(min(ds), 1) if ds else None

# ------------------------------------------------------------------ antenna keep-out (>= 10 mm to metal)
ant_d = {}
for k, m in metal.items():
    d = min_dist(ant, m)
    ant_d[k] = round(d, 1)
    if d < 10.0:
        problems.append(f"antenna only {d:.1f} mm from {k}")
# nothing above the antenna in the lid except plastic: no screw / magnet column over it
for (px, py) in (E.post_centres() if E.lid_fix == "screws" else []):
    if ex1 - 4 - 3 < w + px < ex1 + 3 and ey0 < w + py < ey1:
        problems.append("lid screw above the antenna")

# ------------------------------------------------------------------ USB-C
usb = {}
for nm, m in (("shell", shell_m), ("overmold", mold_m)):
    v = inter_vol(m, base)
    if v > 0.001:
        problems.append(f"USB plug {nm} collides with the wall ({v:.2f} mm^3)")
stop = (E.wall - E.usb_recess_wall) if E.usb_recess else 0.0
slack = E.EPL() - E.esp_pcb_l - E.usb_overhang
usb["overmold_gap_pushed_to_wall"] = round(E.wall - stop, 2)
usb["engagement_mm"] = (round(6.6 - (E.wall - stop) - slack, 2), round(6.6 - (E.wall - stop), 2))
if 6.6 - (E.wall - stop) < 5.0:
    problems.append("USB-C plug engagement < 5 mm")
rec_top = E.ledge_h + E.esp_pcb_t + E.usb_h
if E.usb_wedge:
    z_root = E.usb_cut_z + E.usb_cut_h / 2
    usb["wedge_play_at_wall"] = round(z_root - rec_top, 2)
    usb["wedge_play_slid_back"] = round(z_root + slack - rec_top, 2)
    if z_root < rec_top + 0.1:
        problems.append("USB wedge collides with the receptacle")
cz = E.usb_cut_z
if abs(cz - (E.ledge_h + E.esp_pcb_t + E.usb_h / 2)) > 0.3:
    problems.append("USB cutout centre not aligned with the receptacle")

# ------------------------------------------------------------------ latches
n0, n1 = E.esp_latch_y - E.esp_latch_w / 2, E.esp_latch_y + E.esp_latch_w / 2
if not (n0 >= E.antenna_y[1] + 0.3 or n1 <= E.antenna_y[0] - 0.3):
    problems.append(f"ESP latch nose ({n0:.1f}-{n1:.1f}) overlaps the antenna ({E.antenna_y})")
if n0 < 2.65 or n1 > E.esp_pcb_w - 2.65:
    problems.append("ESP latch nose reaches the header rows")
lat = {}
for nm, nose in (("ESP", (E.EPL() - E.esp_pcb_l - E.usb_overhang) + E.latch_over), ("buck", (E.BPW() - E.buck_pcb_w) / 2 + E.latch_over)):
    strain = 1.5 * E.latch_t * nose / E.latch_len ** 2
    lat[nm] = dict(nose=round(nose, 2), strain_pct=round(strain * 100, 2))
    if strain > 0.03:
        problems.append(f"{nm} latch strain {strain * 100:.1f}% > 3%")
    if E.latch_back < 0.2:
        problems.append("latch has no room to flex")

# ------------------------------------------------------------------ wall layout
ops = E.wall_openings()
labs = E.label_layout(ops) if E.labels else []
items = {}
for o in ops:
    items.setdefault(o["wall"], []).append((o["name"], o["box"]))
for (wn, t, u, z, b) in labs:
    items.setdefault(wn, []).append((f'label "{t}"', b))
for wn, u in E.vent_slots():
    items.setdefault(wn, []).append(("vent", (u - E.vent_w / 2, u + E.vent_w / 2, E.vent_z0, E.vent_z0 + E.vent_len)))
snap = {}
if E.lid_fix == "snap":
    g = E.snap_geometry()
    for wn, u in E.snap_positions():
        items.setdefault(wn, []).append(("lid catch window", (u - E.snap_w / 2 - 0.5, u + E.snap_w / 2 + 0.5, g["win0"], g["win1"])))
    strain = 1.5 * E.snap_t * E.snap_engage / E.snap_len ** 2
    snap = dict(arms=len(E.snap_positions()), positions=[(wn, round(u, 1)) for wn, u in E.snap_positions()],
                deflection_mm=E.snap_engage, strain_pct=round(strain * 100, 2),
                window_z_above_floor=(round(g["win0"], 2), round(g["win1"], 2)))
    if strain > 0.03:
        problems.append(f"snap arm strain {strain * 100:.1f}% > 3%")
def near(a, b, m):
    return not (a[1] + m <= b[0] or b[1] + m <= a[0] or a[3] + m <= b[2] or b[3] + m <= a[2])
for wn, lst in items.items():
    span = G["inner_l"] if wn in ("front", "back") else G["inner_w"]
    for (n1, b1), (n2, b2) in itertools.combinations(lst, 2):
        if n1 == n2 == "vent":
            continue
        if near(b1, b2, 0.99) and not (n1 == "vent" and n2 == "lid catch window" and (b1[3] + 2.99 <= b2[2])) and \
                not (n2 == "vent" and n1 == "lid catch window" and b2[3] + 2.99 <= b1[2]):
            problems.append(f"{wn} wall: {n1} and {n2} closer than 1 mm")
    for n, b in lst:
        if b[0] < -E.wall + E.r_out + 0.5 or b[1] > span + E.wall - E.r_out - 0.5 or b[2] < -E.floor_t + E.chamfer + 0.3 or b[3] > G["inner_h"] - 0.8:
            problems.append(f"{wn} wall: {n} too close to an edge {tuple(round(v, 1) for v in b)}")
        if E.lid_fix == "screws" and (b[0] < E.post_inset + E.post_d / 2 + 0.5 or b[1] > span - (E.post_inset + E.post_d / 2 + 0.5)):
            if not n.startswith("label"):
                problems.append(f"{wn} wall: {n} cuts into a corner post")
# tabs must not sit under the USB plug / jack plug
if E.tabs:
    uy = E.EY0() + E.EPW() / 2
    if abs(E.TY() - uy) < E.tab_w / 2 + 6.0 + 0.5:
        problems.append("left tab under the USB plug")
    if abs(E.TY() - E.JY()) < E.tab_w / 2 + 5.5 + 0.5:
        problems.append("left tab under the 12 V plug")

# ------------------------------------------------------------------ screws / magnets
if E.lid_fix == "screws":
    notes.append(f"lid screws: M3 self-tapping, up to {E.lid_t + E.post_hole_depth - 0.5:.1f} mm long")
notes.append(f"magnets: d{E.magnet_hole_d} x {E.magnet_depth} press-fit pockets at {[(round(x, 1), round(y, 1)) for x, y in E.magnet_centres()]}")

# ------------------------------------------------------------------ printability
def overhang_report(m):
    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union
    from scipy.spatial import cKDTree
    n = m.face_normals
    c = m.triangles_center
    idx = np.nonzero((n[:, 2] < -0.7072) & (c[:, 2] > 0.05))[0]
    if len(idx) == 0:
        return []
    out = []
    for patch in m.submesh([idx], append=True).split(only_watertight=False):
        if patch.area < 0.05:
            continue
        z = float(patch.bounds[0][2])
        poly = unary_union([Polygon(t[:, :2]).buffer(1e-4) for t in patch.triangles])
        minx, miny, maxx, maxy = poly.bounds
        step = 0.2
        ring = poly.buffer(0.3).difference(poly)
        cand = np.array([(x, y) for x in np.arange(minx - 0.4, maxx + 0.4, step) for y in np.arange(miny - 0.4, maxy + 0.4, step)
                         if ring.contains(Point(x, y))] or np.zeros((0, 2)))
        sup = cand[m.contains(np.column_stack([cand, np.full(len(cand), z - 0.15)]))] if len(cand) else cand
        cells = np.array([(x, y) for x in np.arange(minx, maxx, step) for y in np.arange(miny, maxy, step)
                          if poly.contains(Point(x, y))] or [poly.representative_point().coords[0]])
        dmax = float("inf") if len(sup) == 0 else float(cKDTree(sup).query(cells)[0].max())
        out.append(dict(z=round(z, 2), x=(round(minx, 1), round(maxx, 1)), y=(round(miny, 1), round(maxy, 1)),
                        max_dist_to_support=round(dmax, 2), area=round(float(patch.area), 2)))
    return out
pr = {}
for name, m in (("base", base), ("lid", lid_p)):
    pr[name] = overhang_report(m)
    for o in pr[name]:
        if 2 * o["max_dist_to_support"] > 10.3:
            problems.append(f"{name}: bridge/overhang too long (~{2 * o['max_dist_to_support']:.1f} mm) at z={o['z']} x={o['x']} y={o['y']}")

report = dict(dimensions=dims, headroom=head, clearances_base_lid=clear, zones=zone_report, post_to_module_mm=post_clear,
              antenna_to_metal_mm=ant_d, usb=usb, latches=lat, snap_lid=snap, notes=notes,
              labels=[(wn, t, round(u, 1), round(z, 1)) for (wn, t, u, z, b) in labs], overhangs=pr, problems=problems)
json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in report.items() if k not in ("overhangs", "clearances_base_lid")}, indent=1, default=str))
print("max bridge ~", {k: round(2 * max([o["max_dist_to_support"] for o in v] or [0]), 1) for k, v in pr.items()})
print("PROBLEMS:", len(problems))
