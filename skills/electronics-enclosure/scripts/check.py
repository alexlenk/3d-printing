#!/usr/bin/env python3
"""Verify a built enclosure against its spec.

    python check.py spec.json builddir            (run build.py first)

PROBLEMS must be fixed before printing. WARNINGS are design-quality hints (crowding, symmetry,
spec deviations) - read them and either fix them or tell the user why they stay.
Writes builddir/report.json.
"""
import itertools, json, math, os, sys
import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import encl
import pythonscad as ps

spec_path, B = sys.argv[1], sys.argv[2]
E = encl.load(spec_path)
problems, warnings, info = [], [], {}
w = E.wall


def load(name):
    return trimesh.load(os.path.join(B, name), force="mesh")


def solid(obj, name):
    p = os.path.join(B, "_chk_" + name + ".stl")
    ps.export(obj, p)
    return trimesh.load(p, force="mesh")


def ivol(a, b):
    try:
        r = trimesh.boolean.intersection([a, b], engine="manifold")
        return 0.0 if r.is_empty else float(r.volume)
    except Exception:
        return float("nan")


def dvol(a, b):
    r = trimesh.boolean.difference([a, b], engine="manifold")
    return 0.0 if r.is_empty else float(r.volume)


def min_dist(a, b, n=4000):
    pts = np.vstack([a.sample(n), a.vertices])
    _, d, _ = trimesh.proximity.closest_point(b, pts)
    return float(d.min())


def near(a, b, m):
    return not (a[1] + m <= b[0] or b[1] + m <= a[0] or a[3] + m <= b[2] or b[3] + m <= a[2])


base, lid_a, lid_p = load("base.stl"), load("lid_assembled.stl"), load("lid.stl")
info["outer_mm"] = [round(E.OL, 1), round(E.OW, 1), round(E.OH, 1)]
info["inner_mm"] = [E.L, E.W, E.H]
info["footprint_with_tabs_mm"] = [round(v, 1) for v in (base.bounds[1][:2] - base.bounds[0][:2])]

# ------------------------------------------------------------------ meshes
for name, m in (("base", base), ("lid", lid_p)):
    if not m.is_watertight:
        problems.append(f"{name}: mesh is not watertight")
    nb = len(m.split(only_watertight=False))
    if nb != 1:
        problems.append(f"{name}: {nb} separate bodies (touching faces? add overlap)")
    if abs(m.bounds[0][2]) > 1e-6:
        problems.append(f"{name}: does not sit on z=0")

# print-orientation lid must be a ROTATION of the assembled lid (a mirror would not fit)
flip = lid_p.copy()
flip.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
flip.apply_translation([0, E.OW, E.BH + E.lid_t])
d = dvol(flip, lid_a) + dvol(lid_a, flip)
if d > 0.5:
    problems.append(f"lid.stl turned back over differs from the assembled lid by {d:.1f} mm^3 (mirrored export?)")
if ivol(base, lid_a) > 0.01:
    problems.append(f"lid intersects base ({ivol(base, lid_a):.2f} mm^3)")
# does the lid also fit turned 180 degrees? (error tolerance)
rot = lid_a.copy()
rot.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1], point=[E.OL / 2, E.OW / 2, 0]))
v180 = ivol(base, rot)
info["lid_fits_both_ways"] = v180 < 0.01
if v180 >= 0.01:
    warnings.append(f"lid only fits one way round ({v180:.1f} mm^3 clash when turned 180 deg) - make it symmetric or mark it clearly")

# ------------------------------------------------------------------ dummies
comps = {k: solid(v, "c_" + str(i)) for i, (k, v) in enumerate(E.components().items())}
owner = {}
for b in E.boards:
    for k in comps:
        if k == f"{b['id']} pcb" or k == f"{b['id']} plugs" or k.startswith(b["id"] + "/"):
            owner[k] = b["id"]
for k, m in comps.items():
    for nm, enc in (("base", base), ("lid", lid_a)):
        v = ivol(m, enc)
        if v > 0.001:
            problems.append(f"{k} collides with the {nm} ({v:.2f} mm^3)")
for (a, ma), (b2, mb) in itertools.combinations(comps.items(), 2):
    if owner.get(a) and owner.get(a) == owner.get(b2):
        continue
    v = ivol(ma, mb)
    if v > 0.001:
        problems.append(f"{a} collides with {b2} ({v:.2f} mm^3)")
info["clearance_to_base_lid_mm"] = {k: [round(min_dist(m, base), 2), round(min_dist(m, lid_a), 2)] for k, m in comps.items()}

# ------------------------------------------------------------------ boards: headroom, zones, latches
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union

lat = {}
zones_info = {}
for b in E.boards:
    top = E.floor + b["_top"]
    head = E.BH - top
    if head < b["headroom"] - 1e-6:
        problems.append(f"{b['id']}: only {head:.1f} mm above the PCB, needs {b['headroom']}")
    bb = E.pcb_aabb(b)
    plug_top = top + b["plug"]["seat"] + b["plug"]["height"]
    nose_max = 0.0
    for (_, _, _, nose, cfg) in E._latch_frames(b):
        nose_max = max(nose_max, nose + cfg["t"] / 2)
        strain = 1.5 * cfg["t"] * nose / cfg["len"] ** 2
        lat[f"{b['id']} latch {cfg.get('edge')}@{cfg.get('at')}"] = dict(nose=round(nose, 2), strain_pct=round(strain * 100, 2))
        if strain > 0.03:
            problems.append(f"{b['id']}: latch strain {strain * 100:.1f}% > 3% (longer plate or less reach)")
    # hard zone: footprint + margin, from just above the hold-downs to the top of the plugs
    poly = sbox(w + bb[0], w + bb[2], w + bb[1], w + bb[3]).buffer(b["zone"]) & sbox(w, w, w + E.L, w + E.W)
    z0, z1 = top + nose_max + 0.6, max(plug_top, top + 6.0)
    zone = trimesh.creation.extrude_polygon(poly, z1 - z0)
    zone.apply_translation([0, 0, z0])
    intr = {}
    for k, m in comps.items():
        if owner.get(k) == b["id"]:
            continue
        v = ivol(zone, m)
        if v > 0.05:
            intr[k] = round(v, 1)
            problems.append(f"{k} is inside the {b['zone']:.0f} mm free zone around {b['id']} ({v:.1f} mm^3)")
    v = ivol(zone, base)                       # the USB wedge belongs to the board it holds
    if v > 0.05:
        wedges = [solid(x, f"wedge{i}") for i, x in enumerate(E.usb_wedges())]
        vw = sum(ivol(zone, x) for x in wedges)
        if v - vw > 0.05:
            problems.append(f"enclosure geometry intrudes into the free zone around {b['id']} ({v - vw:.1f} mm^3)")
    v = ivol(zone, lid_a)
    if v > 0.05:
        pipes = [x for x in E.lid_windows() if x[3]]
        if not pipes:
            problems.append(f"lid (snap arms/lip) reaches into the free zone around {b['id']} below plug height ({v:.1f} mm^3)")
    zones_info[b["id"]] = dict(z=[round(z0, 1), round(z1, 1)], intrusions=intr)
info["board_zones"] = zones_info
info["latches"] = lat

# ------------------------------------------------------------------ antenna keep-out
ant = {}
metal = {k: solid(v, "m_" + str(i)) for i, (k, v) in enumerate(E.metal_parts().items())}
for an, (sol, keep) in E.antennas().items():
    am = solid(sol, "ant_" + an.replace("/", "_"))
    for k, m in metal.items():
        dd = min_dist(am, m)
        ant[f"{an} -> {k}"] = round(dd, 1)
        if dd < keep:
            problems.append(f"antenna {an} is {dd:.1f} mm from metal '{k}' (keep {keep})")
info["antenna_to_metal_mm"] = ant

# ------------------------------------------------------------------ USB-C
usb = {}
for oid, (shell, mold) in E.usb_plugs().items():
    o = next(x for x in E.openings if x["id"] == oid)
    for nm, sol in (("shell", shell), ("overmold", mold)):
        v = ivol(solid(sol, f"{oid}_{nm}"), base)
        if v > 0.001:
            problems.append(f"{oid}: plug {nm} collides with the wall ({v:.2f} mm^3)")
    stop = (E.wall - o["recess"]["wall"]) if o.get("recess") else 0.0
    gap = None
    if "_part_aabb" in o:
        bb = o["_part_aabb"]
        gap = {"left": bb[0], "right": E.L - bb[1], "front": bb[2], "back": E.W - bb[3]}[o["wall"]]
        eng = 6.6 - (E.wall - stop) - gap
        usb[oid] = dict(receptacle_to_inner_wall=round(gap, 2), engagement_mm=round(eng, 2))
        if eng < 5.0:
            problems.append(f"{oid}: USB-C plug only engages {eng:.1f} of 6.6 mm (recess / move board to the wall)")
        if o.get("wedge"):
            play = o["z"] + o["h"] / 2 - o["_part_top"]
            usb[oid]["wedge_play_mm"] = round(play, 2)
info["usb"] = usb

# ------------------------------------------------------------------ snap lid
if E.lid_cfg["fix"] == "snap":
    s = E.snap_cfg()
    strain = 1.5 * s["t"] * s["engage"] / s["len"] ** 2
    info["snap"] = dict(positions=[(wl, round(u, 1)) for wl, u in E.snap_positions()], strain_pct=round(strain * 100, 2))
    if strain > 0.03:
        problems.append(f"snap arm strain {strain * 100:.1f}% > 3%")
    pos = set((wl, round(u, 2)) for wl, u in E.snap_positions())
    opp = {"front": "back", "back": "front", "left": "right", "right": "left"}
    mirrored = set((opp[wl], round(E.wall_span(wl) - u, 2)) for wl, u in E.snap_positions())
    if pos != mirrored:
        warnings.append("snap positions are not symmetric (180 deg): the lid will only fit one way")

# ------------------------------------------------------------------ wall layout
items = {}
for f in E.opening_features():
    items.setdefault(f["wall"], []).append((f["name"], f["box"]))
for (wl, t, u, z, bx) in E.label_layout():
    items.setdefault(wl, []).append((f'label "{t}"', bx))
for v in E.vent_slots():
    items.setdefault(v["wall"], []).append(("vent", (v["u"] - v["w"] / 2, v["u"] + v["w"] / 2, v["z0"], v["z0"] + v["len"])))
for (wl, u, g) in E.snap_windows():
    items.setdefault(wl, []).append(("lid catch window", g))
for wl, lst in items.items():
    span = E.wall_span(wl)
    for (n1, b1), (n2, b2) in itertools.combinations(lst, 2):
        if n1 == n2 == "vent":
            continue
        need = 3.0 if {n1, n2} == {"vent", "lid catch window"} else 1.0
        if near(b1, b2, need - 0.01):
            problems.append(f"{wl} wall: {n1} and {n2} closer than {need:.0f} mm")
    for n, b in lst:
        if b[0] < -w + E.p["r_out"] + 0.5 or b[1] > span + w - E.p["r_out"] - 0.5 or b[2] < -E.floor + E.p["chamfer"] + 0.3 or b[3] > E.H - 0.8:
            problems.append(f"{wl} wall: {n} too close to an edge {tuple(round(v, 1) for v in b)}")

# ------------------------------------------------------------------ layout quality (assembly friendliness)
foot = {}
for b in E.boards:
    bb = E.pcb_aabb(b)
    foot[b["id"]] = sbox(bb[0], bb[2], bb[1], bb[3])
for k in E.blocks:
    sx, sy, _ = k["size"]
    bb = E.local_aabb_to_inner(k, 0, 0, sx, sy)
    foot[k["id"]] = sbox(bb[0], bb[2], bb[1], bb[3])
for pp in E.panels:
    if pp.get("body"):
        m = comps.get(f"{pp['id']} body")
        if m is not None:
            lo, hi = m.bounds[0] - [w, w, 0], m.bounds[1] - [w, w, 0]
            foot[pp["id"]] = sbox(lo[0], lo[1], hi[0], hi[1])
gaps = []
for (a, pa), (b2, pb) in itertools.combinations(foot.items(), 2):
    gaps.append((round(pa.distance(pb), 1), a, b2))
gaps.sort()
info["component_gaps_mm"] = gaps
occupied = unary_union(list(foot.values())) if foot else None
xs, ys = np.meshgrid(np.arange(0.5, E.L, 1.0), np.arange(0.5, E.W, 1.0))
best = (0, None)
if occupied is not None:
    for x, y in zip(xs.ravel(), ys.ravel()):
        pt = Point(x, y)
        if occupied.contains(pt):
            continue
        r = min(occupied.distance(pt), x, y, E.L - x, E.W - y)
        if r > best[0]:
            best = (r, (round(float(x), 1), round(float(y), 1)))
info["largest_empty_circle"] = dict(diameter=round(2 * best[0], 1), centre=best[1])
min_gap = gaps[0][0] if gaps else None
if min_gap is not None and min_gap < 10 and best[0] * 2 > min_gap + 25:
    warnings.append(f"crowded: {gaps[0][1]} and {gaps[0][2]} are only {min_gap} mm apart while a free area of "
                    f"d{2 * best[0]:.0f} mm sits at {best[1]} - spread the parts out for easier assembly")
for g, a, b2 in gaps:
    if g < 3:
        warnings.append(f"{a} and {b2} are only {g} mm apart (fingers, wires, hot glue need room)")
# cable entries next to boards they do not need to be next to
for o in list(E.openings) + E.panels:
    if o.get("type") == "usb-c":
        continue
    wl, u = o["wall"], o["u"]
    p = {"front": (u, 0), "back": (u, E.W), "left": (0, u), "right": (E.L, u)}[wl]
    for b in E.boards:
        dd = foot[b["id"]].distance(Point(*p))
        if dd < 1.5 * b["zone"]:
            warnings.append(f"entry '{o['id']}' is only {dd:.1f} mm from {b['id']} - incoming cables crowd its plugs; "
                            f"put entries where there is free floor space / near where the wires terminate")
info["layout_note"] = "component_gaps_mm: edge-to-edge distances in plan view; largest_empty_circle: biggest unused floor area"

# symmetry of fasteners / mounting
if E.tabs and E.tabs["at"] is not None and abs(E.tabs["at"] - E.W / 2) > 0.5:
    warnings.append(f"mounting tabs are off-centre (at {E.tabs['at']}, centre {E.W / 2}) - fine if needed for clearance, say why")

# ------------------------------------------------------------------ printability
def overhangs(m):
    from shapely.geometry import Polygon
    from scipy.spatial import cKDTree
    n, c = m.face_normals, m.triangles_center
    idx = np.nonzero((n[:, 2] < -0.7072) & (c[:, 2] > 0.05))[0]
    out = []
    if len(idx) == 0:
        return out
    for patch in m.submesh([idx], append=True).split(only_watertight=False):
        if patch.area < 0.05:
            continue
        z = float(patch.bounds[0][2])
        poly = unary_union([Polygon(t[:, :2]).buffer(1e-4) for t in patch.triangles])
        minx, miny, maxx, maxy = poly.bounds
        ring = poly.buffer(0.3).difference(poly)
        cand = np.array([(x, y) for x in np.arange(minx - 0.4, maxx + 0.4, 0.2) for y in np.arange(miny - 0.4, maxy + 0.4, 0.2)
                         if ring.contains(Point(x, y))] or np.zeros((0, 2)))
        sup = cand[m.contains(np.column_stack([cand, np.full(len(cand), z - 0.15)]))] if len(cand) else cand
        cells = np.array([(x, y) for x in np.arange(minx, maxx, 0.2) for y in np.arange(miny, maxy, 0.2)
                          if poly.contains(Point(x, y))] or [poly.representative_point().coords[0]])
        dmax = float("inf") if len(sup) == 0 else float(cKDTree(sup).query(cells)[0].max())
        out.append(dict(z=round(z, 2), x=(round(minx, 1), round(maxx, 1)), y=(round(miny, 1), round(maxy, 1)), max_dist_to_support=round(dmax, 2)))
    return out

pr = {}
for name, m in (("base", base), ("lid", lid_p)):
    pr[name] = overhangs(m)
    for o in pr[name]:
        if 2 * o["max_dist_to_support"] > 10.3:
            problems.append(f"{name}: bridge/overhang ~{2 * o['max_dist_to_support']:.1f} mm at z={o['z']} x={o['x']} y={o['y']}")
info["max_bridge_mm"] = {k: round(2 * max([o["max_dist_to_support"] for o in v] or [0]), 1) for k, v in pr.items()}

for f in os.listdir(B):
    if f.startswith("_chk_"):
        os.remove(os.path.join(B, f))
report = dict(info=info, problems=problems, warnings=warnings, overhangs=pr)
json.dump(report, open(os.path.join(B, "report.json"), "w"), indent=1, default=str)
print(json.dumps(info, indent=1, default=str))
print("\nWARNINGS:", len(warnings))
for x in warnings:
    print("  -", x)
print("PROBLEMS:", len(problems))
for x in problems:
    print("  -", x)
sys.exit(1 if problems else 0)
