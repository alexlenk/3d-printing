"""
encl - spec-driven generator for 3D-printable electronics enclosures (PythonSCAD).

All geometry comes from one JSON spec (see references/spec-format.md). Units: mm.

Coordinates
    World:  outer box corner at (0,0,0). X = length, Y = depth (front wall at Y=0), Z = up.
    Inner:  origin at the inside front-left corner on top of the floor: world = inner + (wall, wall, floor).
            Every position in the spec is an inner coordinate.
    Board-local: a board's PCB occupies x in [0, L], y in [0, W]; z = 0 is the PCB's TOP surface
            for parts/pins. "at" + "rot" place the local frame in inner coordinates.
    Walls:  "front" (Y=0), "back" (Y=W), "left" (X=0), "right" (X=L). On a wall, "u" is the inner
            X (front/back) or inner Y (left/right) coordinate and "z" is the height above the floor.

Only pythonscad's native Python API is used (its scad() bridge is unreliable in 1.1.x).
"""

import copy
import json
import math
import shutil
import subprocess

import pythonscad as ps

# ----------------------------------------------------------------------------- defaults

DEFAULTS = {
    "print": {"wall": 2.0, "floor": 2.0, "lid": 2.0, "tol": 0.25, "r_out": 2.0, "chamfer": 0.8, "fn": 64},
    "labels": {"size": 3.5, "relief": 0.6, "gap": 1.2, "font": "auto"},
    "board": {
        "ledge_h": 3.0, "clear": 0.25, "rim_t": 1.2, "zone": 10.0, "headroom": 28.0,
        "plug": {"seat": 3.5, "height": 14.0, "w": 2.54},
        "latch": {"t": 1.2, "len": 9.0, "over": 0.6, "gap": 0.4, "back": 0.4, "width": 3.0},
        "stub": {"len": 2.6},
        "antenna_keepout": 10.0,
    },
    "block": {"cradle": {"wall_h": 5.0, "t": 1.2, "clear": 0.45, "open": []}},
    "opening": {"window_chamfer": 1.5, "teardrop": True, "anchor": None},
    "usb": {"w": 10.0, "h": 4.5, "recess": {"w": 13.0, "h": 7.5, "wall": 0.8},
            "wedge": {"len": 1.6, "extra_w": 2.0}},
    "vent": {"w": 1.5, "pitch": 3.0},
    "anchor": {"l": 8.0, "w": 5.0, "h": 4.0, "tunnel_w": 3.2, "tunnel_h": 1.6},
    "lid": {
        "fix": "snap", "lip_h": 3.0, "lip_t": 1.2, "windows": [], "symmetric_windows": True,
        "snap": {"walls": ["front", "back"], "spread": 0.6, "w": 8.0, "t": 1.6, "len": 11.0,
                 "engage": 0.9, "play": 0.2, "positions": None},
        "screws": {"post_d": 6.0, "inset": 3.0, "pilot": 2.5, "depth": 9.0, "hole": 3.4},
        "light_pipe": {"od": 5.0, "gap": 4.0},
    },
    "mount": {
        "magnets": {"d": 4.0, "h": 2.0, "hole_d": 4.1, "inset": 4.5, "boss_d": 8.0, "boss_h": 1.2},
        "tabs": {"walls": ["left", "right"], "len": 12.0, "w": 14.0, "t": 4.0, "r": 3.0, "hole": 4.5, "at": None},
    },
}

WALLS = ("front", "back", "left", "right")


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


# ----------------------------------------------------------------------------- primitives

def box(x0, y0, z0, x1, y1, z1):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    return ps.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def union(objs):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    return objs[0] if len(objs) == 1 else ps.union(*objs)


def rot2(x, y, deg):
    a = math.radians(deg)
    c, s = round(math.cos(a), 12), round(math.sin(a), 12)
    return x * c - y * s, x * s + y * c


_FONT = None


def pick_font(pref):
    """Bold sans font that exists on this machine (labels must print: ~0.5 mm stems at 3.5 mm)."""
    global _FONT
    if pref and pref != "auto":
        return pref
    if _FONT:
        return _FONT
    cands = ["Liberation Sans:style=Bold", "DejaVu Sans:style=Bold", "Noto Sans:style=Bold",
             "FreeSans:style=Bold", "Arial:style=Bold"]
    found = ""
    if shutil.which("fc-list"):
        found = subprocess.run(["fc-list", ":", "family", "style"], capture_output=True, text=True).stdout
    _FONT = cands[0]
    for c in cands:
        fam = c.split(":")[0]
        if fam in found:
            _FONT = c
            break
    return _FONT


# ----------------------------------------------------------------------------- enclosure

class Enclosure:
    def __init__(self, spec):
        self.spec = spec
        self.p = deep_merge(DEFAULTS["print"], spec.get("print"))
        self.lab = deep_merge(DEFAULTS["labels"], spec.get("labels"))
        self.lid_cfg = deep_merge(DEFAULTS["lid"], spec.get("lid"))
        m = spec.get("mount", {})
        self.magnets = None if m.get("magnets") is None else deep_merge(DEFAULTS["mount"]["magnets"], m.get("magnets"))
        self.tabs = None if m.get("tabs") is None else deep_merge(DEFAULTS["mount"]["tabs"], m.get("tabs"))
        self.fn = self.p["fn"]
        self.wall, self.floor, self.lid_t, self.tol = self.p["wall"], self.p["floor"], self.p["lid"], self.p["tol"]
        self.L, self.W, self.H = spec["inner"]
        self.OL, self.OW = self.L + 2 * self.wall, self.W + 2 * self.wall
        self.BH = self.floor + self.H                   # base height
        self.OH = self.BH + self.lid_t
        self.boards = [self._board(b) for b in spec.get("boards", [])]
        self.blocks = [self._block(b) for b in spec.get("blocks", [])]
        self.panels = [deep_merge({"metal": True, "label_pos": "above"}, pp) for pp in spec.get("panel_parts", [])]
        self.openings = [self._opening(o) for o in spec.get("openings", [])]
        self.vents = [deep_merge(DEFAULTS["vent"], v) for v in spec.get("vents", [])]
        self.anchors = [deep_merge(DEFAULTS["anchor"], a) for a in spec.get("anchors", [])]

    # ---------------------------------------------------------------- spec normalisation
    def _board(self, b):
        b = deep_merge(DEFAULTS["board"], b)
        b.setdefault("rot", 0)
        b.setdefault("parts", [])
        b.setdefault("pins", [])
        b.setdefault("rows", [])
        b.setdefault("ledges", [])
        b.setdefault("latches", [])
        L, W, T = b["size"]
        pins = [dict(p) for p in b["pins"]]
        for r in b["rows"]:
            sx, sy = r["start"]
            dx, dy = r.get("dir", [1, 0])
            for i in range(r["n"]):
                pins.append({"at": [sx + dx * i * r.get("pitch", 2.54), sy + dy * i * r.get("pitch", 2.54)],
                             "d": r.get("d", 1.7), "plug": r.get("plug", True)})
        b["_pins"] = pins
        b["_top"] = b["ledge_h"] + T
        return b

    def _block(self, k):
        k = deep_merge({"rot": 0, "metal": False, "cradle": DEFAULTS["block"]["cradle"]}, k)
        if k.get("cradle") is not None:
            k["cradle"] = deep_merge(DEFAULTS["block"]["cradle"], k["cradle"])
        return k

    def _opening(self, o):
        o = deep_merge(DEFAULTS["opening"], o)
        o.setdefault("label_pos", "above")
        if o["type"] == "usb-c":
            user = dict(o)
            o = deep_merge(DEFAULTS["usb"], o)
            for key in ("wedge", "recess"):          # true -> defaults, false/null -> off
                if user.get(key) is True:
                    o[key] = copy.deepcopy(DEFAULTS["usb"][key])
                elif key in user and not user[key]:
                    o[key] = None
            if "align" in o:
                bid, pname = o["align"].split("/")
                b = self.board(bid)
                part = next(p for p in b["parts"] if p["name"] == pname)
                x0, y0, z0, x1, y1, z1 = part["box"]
                bb = self.local_aabb_to_inner(b, x0, y0, x1, y1)
                wall = o["wall"]
                o["u"] = (bb[0] + bb[1]) / 2 if wall in ("front", "back") else (bb[2] + bb[3]) / 2
                o["z"] = b["_top"] + (z0 + z1) / 2
                o["_part_top"] = b["_top"] + z1
                o["_part_aabb"] = bb
        return o

    def board(self, bid):
        return next(b for b in self.boards if b["id"] == bid)

    # ---------------------------------------------------------------- transforms
    def W_(self, x, y, z=0.0):
        return [self.wall + x, self.wall + y, self.floor + z]

    def place_local(self, obj, b):
        """board-local solid (z relative to the floor top) -> world"""
        return obj.rotate([0, 0, b["rot"]]).translate(self.W_(b["at"][0], b["at"][1], 0))

    def local_to_inner(self, b, x, y):
        rx, ry = rot2(x, y, b["rot"])
        return b["at"][0] + rx, b["at"][1] + ry

    def local_aabb_to_inner(self, b, x0, y0, x1, y1):
        pts = [self.local_to_inner(b, x, y) for x in (x0, x1) for y in (y0, y1)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return (min(xs), max(xs), min(ys), max(ys))

    def pcb_aabb(self, b):
        L, W, _ = b["size"]
        return self.local_aabb_to_inner(b, 0, 0, L, W)

    def edge_against_wall(self, b, edge, margin=1.0):
        """True if this local edge of the pocket lies on an inner wall."""
        L, W, _ = b["size"]
        c = b["clear"]
        pts = {"x-": [(-c, -c), (-c, W + c)], "x+": [(L + c, -c), (L + c, W + c)],
               "y-": [(-c, -c), (L + c, -c)], "y+": [(-c, W + c), (L + c, W + c)]}[edge]
        (ax, ay), (bx, by) = [self.local_to_inner(b, *p) for p in pts]
        if abs(ax - bx) < 1e-6:          # vertical line in inner coords
            return ax <= margin or ax >= self.L - margin
        return ay <= margin or ay >= self.W - margin

    # ---------------------------------------------------------------- 2D profiles
    def window_profile(self, w, h, ch):
        ch = min(ch, h / 3, w / 3)
        return ps.polygon([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2 - ch], [w / 2 - ch, h / 2],
                           [-w / 2 + ch, h / 2], [-w / 2, h / 2 - ch]])

    def hole_profile(self, d, teardrop=True, flat=0.0):
        c = ps.circle(d=d, fn=self.fn)
        r = d / 2
        if teardrop:
            c = ps.hull(c, ps.polygon([[-r * 0.7071, r * 0.7071], [r * 0.7071, r * 0.7071], [0, r * 1.4142]]))
        if flat > 0:
            c = c & ps.square([d + 2, flat]).translate([-(d + 2) / 2, -r, 0])
        return c

    @staticmethod
    def hole_top(d, teardrop=True, flat=0.0):
        if flat > 0:
            return flat - d / 2
        return d / 2 * (1.4142 if teardrop else 1.0)

    # ---------------------------------------------------------------- walls
    _ROT = {"front": [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
            "back": [[-1, 0, 0], [0, 0, 1], [0, 1, 0]],
            "left": [[0, 0, -1], [-1, 0, 0], [0, 1, 0]],
            "right": [[0, 0, 1], [1, 0, 0], [0, 1, 0]]}

    def on_wall(self, obj, wall, u, z):
        """Local wall frame (x along the wall as read from outside, y up, z outwards; z=0 = inner face)."""
        w = self.wall
        p = {"front": (w + u, w, self.floor + z), "back": (w + u, w + self.W, self.floor + z),
             "left": (w, w + u, self.floor + z), "right": (w + self.L, w + u, self.floor + z)}[wall]
        R = self._ROT[wall]
        return ps.multmatrix(obj, [R[0] + [p[0]], R[1] + [p[1]], R[2] + [p[2]], [0, 0, 0, 1]])

    def through(self, prof):
        return ps.linear_extrude(prof, height=self.wall + 2).translate([0, 0, -1])

    def wall_span(self, wall):
        return self.L if wall in ("front", "back") else self.W

    # ---------------------------------------------------------------- wall features
    def opening_features(self):
        """Every wall feature: dict(wall, name, u, z, cut (local solid), box=(u0,u1,z0,z1), label, label_pos)."""
        feats = []
        tear = lambda o: o.get("teardrop", True)
        for o in self.openings:
            t = o["type"]
            if t == "usb-c":
                rw, rh = (o["recess"]["w"], o["recess"]["h"]) if o.get("recess") else (o["w"], o["h"])
                cut = self.through(self.window_profile(o["w"], o["h"], o["window_chamfer"]))
                if o.get("recess"):
                    cut = cut | box(-rw / 2, -rh / 2, o["recess"]["wall"], rw / 2, rh / 2, self.wall + 1)
                feats.append(dict(wall=o["wall"], name=o["id"], u=o["u"], z=o["z"], cut=cut,
                                  box=(o["u"] - rw / 2, o["u"] + rw / 2, o["z"] - rh / 2, o["z"] + rh / 2),
                                  label=o.get("label"), label_pos=o["label_pos"]))
            elif t in ("slot", "rect"):
                cut = self.through(self.window_profile(o["w"], o["h"], o["window_chamfer"]))
                feats.append(dict(wall=o["wall"], name=o["id"], u=o["u"], z=o["z"], cut=cut,
                                  box=(o["u"] - o["w"] / 2, o["u"] + o["w"] / 2, o["z"] - o["h"] / 2, o["z"] + o["h"] / 2),
                                  label=o.get("label"), label_pos=o["label_pos"]))
            elif t == "hole":
                d = o["d"]
                cut = self.through(self.hole_profile(d, tear(o), o.get("flat", 0.0)))
                feats.append(dict(wall=o["wall"], name=o["id"], u=o["u"], z=o["z"], cut=cut,
                                  box=(o["u"] - d / 2, o["u"] + d / 2, o["z"] - d / 2, o["z"] + self.hole_top(d, tear(o), o.get("flat", 0.0))),
                                  label=o.get("label"), label_pos=o["label_pos"]))
            else:
                raise ValueError(f"unknown opening type {t}")
        for pp in self.panels:
            c = pp["cut"]
            d = c["d"]
            cut = self.through(self.hole_profile(d, c.get("teardrop", True), c.get("flat", 0.0)))
            feats.append(dict(wall=pp["wall"], name=pp["id"], u=pp["u"], z=pp["z"], cut=cut,
                              box=(pp["u"] - d / 2, pp["u"] + d / 2, pp["z"] - d / 2, pp["z"] + self.hole_top(d, c.get("teardrop", True), c.get("flat", 0.0))),
                              label=pp.get("label"), label_pos=pp.get("label_pos", "above")))
        return feats

    def vent_slots(self):
        out = []
        for v in self.vents:
            x0, x1 = v["from"], v["to"]
            n = int((x1 - x0 - v["w"]) // v["pitch"]) + 1
            start = (x0 + x1) / 2 - (n - 1) * v["pitch"] / 2
            for i in range(n):
                out.append(dict(wall=v["wall"], u=start + i * v["pitch"], w=v["w"], z0=v["z0"], len=v["len"]))
        return out

    def text_w(self, txt):
        return ps.textmetrics(txt, size=self.lab["size"], font=pick_font(self.lab["font"]))["size"][0]

    def label_layout(self):
        """(wall, text, u, zc, box): labels next to their openings, slid sideways when crowded."""
        feats = self.opening_features()
        obst = {}
        for f in feats:
            obst.setdefault(f["wall"], []).append(f["box"])
        for v in self.vent_slots():
            obst.setdefault(v["wall"], []).append((v["u"] - v["w"] / 2, v["u"] + v["w"] / 2, v["z0"], v["z0"] + v["len"]))
        for (w, u, g) in self.snap_windows():
            obst.setdefault(w, []).append(g)
        placed, out = {}, []
        size, gap = self.lab["size"], self.lab["gap"]
        for f in feats:
            if not f.get("label"):
                continue
            tw = self.text_w(f["label"])
            u0, u1, z0, z1 = f["box"]
            pos = f["label_pos"]
            cands = []
            if pos == "left":
                cands.append((u0 - gap - tw / 2, f["z"]))
            elif pos == "right":
                cands.append((u1 + gap + tw / 2, f["z"]))
            elif pos == "below":
                cands.append((f["u"], z0 - gap - size / 2))
            else:
                cands.append((f["u"], z1 + gap + size / 2))
            span = self.wall_span(f["wall"])
            lo, hi = -self.wall + self.p["r_out"] + 0.6, span + self.wall - self.p["r_out"] - 0.6
            best = None
            for (uc, zc) in cands:
                for du in sorted([i * 0.25 for i in range(-80, 81)], key=abs):
                    bx = (uc + du - tw / 2, uc + du + tw / 2, zc - size / 2, zc + size / 2)
                    if bx[0] < lo or bx[1] > hi:
                        continue
                    if not any(_near(bx, ob, 1.0) for ob in obst.get(f["wall"], []) + placed.get(f["wall"], [])):
                        best = bx
                        break
                if best:
                    break
            if best is None:
                uc, zc = cands[0]
                best = (uc - tw / 2, uc + tw / 2, zc - size / 2, zc + size / 2)
            placed.setdefault(f["wall"], []).append(best)
            out.append((f["wall"], f["label"], (best[0] + best[1]) / 2, (best[2] + best[3]) / 2, best))
        return out

    def label_solid(self, wall, txt, u, zc):
        t = ps.text(txt, size=self.lab["size"], font=pick_font(self.lab["font"]), halign="center", valign="center", fn=self.fn)
        t3 = ps.linear_extrude(t, height=self.lab["relief"] + 0.01).translate([0, 0, self.wall - 0.01])
        return self.on_wall(t3, wall, u, zc)

    # ---------------------------------------------------------------- board seats
    def _latch_frames(self, b):
        """For each latch: (origin local (x,y), angle deg, extend sign, nose, edge)."""
        L, W, _ = b["size"]
        c = b["clear"]
        out = []
        for la in b["latches"]:
            cfg = deep_merge(b["latch"], la)
            e, a = la["edge"], la["at"]
            origin, ang = {"x+": ((L + c, a), 0), "x-": ((-c, a), 180), "y+": ((a, W + c), 90), "y-": ((a, -c), 270)}[e]
            tx, ty = rot2(0, 1, ang)
            to_c = (L / 2 - origin[0]) * tx + (W / 2 - origin[1]) * ty
            sign = 1 if to_c > 0 else -1
            nose = c + cfg["over"]
            out.append((origin, ang, sign, nose, cfg))
        return out

    def _latch_solid(self, b, cfg, nose, sign):
        t, Ln, w = cfg["t"], cfg["len"], cfg["width"]
        zc = b["_top"] + 0.1
        e = t / 2
        y0, y1 = (-w / 2, Ln + 1.0) if sign > 0 else (-Ln - 1.0, w / 2)
        plate = box(0, y0, -self.floor, t, y1, zc + nose + e)
        prof = ps.polygon([[e, zc], [e, zc + nose + e], [-nose, zc]])
        n = ps.linear_extrude(prof, height=w).rotate([90, 0, 0]).translate([0, w / 2, 0])
        return plate | n

    def _latch_slot(self, b, cfg, nose, sign):
        t, Ln, w = cfg["t"], cfg["len"], cfg["width"]
        zc = b["_top"] + 0.1
        y0, y1 = (-w / 2 - 0.5, Ln) if sign > 0 else (-Ln, w / 2 + 0.5)
        return box(-cfg["gap"], y0, -self.floor - 1, t + nose + cfg["back"], y1, zc + nose + 1)

    def board_seat(self, b):
        """(adds, cuts, after) in world coords. `after` = latches, added after all cuts."""
        L, W, T = b["size"]
        c, rt, top = b["clear"], b["rim_t"], b["_top"]
        adds = []
        edges = {"y-": box(-c - rt, -c - rt, 0, L + c + rt, -c, top), "y+": box(-c - rt, W + c, 0, L + c + rt, W + c + rt, top),
                 "x-": box(-c - rt, -c, 0, -c, W + c, top), "x+": box(L + c, -c, 0, L + c + rt, W + c, top)}
        for e, solid in edges.items():
            if not self.edge_against_wall(b, e) and e not in b.get("rim_skip", []):
                adds.append(solid)
        for (x0, x1, y0, y1) in b["ledges"]:
            x0, x1 = max(x0, -c), min(x1, L + c)
            y0, y1 = max(y0, -c), min(y1, W + c)
            adds.append(box(x0, y0, 0, x1, y1, b["ledge_h"]))
        cuts, after = [], []
        for (origin, ang, sign, nose, cfg) in self._latch_frames(b):
            tr = lambda o: o.rotate([0, 0, ang]).translate([origin[0], origin[1], 0])
            cuts.append(tr(self._latch_slot(b, cfg, nose, sign)))
            after.append(tr(self._latch_solid(b, cfg, nose, sign)))
        P = lambda objs: [self.place_local(o, b) for o in objs]
        return P(adds), P(cuts), P(after)

    def usb_wedges(self):
        out = []
        for o in self.openings:
            if o["type"] != "usb-c" or not o.get("wedge") or "_part_top" not in o:
                continue
            bb = o["_part_aabb"]
            gap = {"left": bb[0], "right": self.L - bb[1], "front": bb[2], "back": self.W - bb[3]}[o["wall"]]
            z_root = o["z"] + o["h"] / 2
            Lw = o["wedge"]["len"] + gap
            h = Lw + 2.0
            prof = ps.polygon([[0, 0], [Lw, Lw], [Lw, h], [0, h]])      # local wall frame: -z = into the box
            w = (bb[1] - bb[0] if o["wall"] in ("front", "back") else bb[3] - bb[2]) + o["wedge"]["extra_w"]
            wedge = ps.linear_extrude(prof, height=w)                  # x = into box, y = up, z = along wall
            wedge = ps.multmatrix(wedge, [[0, 0, 1, -w / 2], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1]])   # proper rotation
            out.append(self.on_wall(wedge, o["wall"], o["u"], z_root))
        return out

    def block_cradle(self, k):
        cr = k.get("cradle")
        if not cr:
            return []
        sx, sy, _ = k["size"]
        c, t, h = cr["clear"], cr["t"], cr["wall_h"]
        fake = {"size": [sx, sy, 0], "clear": c, "rot": k["rot"], "at": k["at"]}
        walls = {"y-": box(-c - t, -c - t, 0, sx + c + t, -c, h), "y+": box(-c - t, sy + c, 0, sx + c + t, sy + c + t, h),
                 "x-": box(-c - t, -c, 0, -c, sy + c, h), "x+": box(sx + c, -c, 0, sx + c + t, sy + c, h)}
        out = []
        for e, s in walls.items():
            if e in cr.get("open", []) or self.edge_against_wall(fake, e):
                continue
            out.append(self.place_local(s, k))
        return out

    def anchor_solid(self, a):
        l, w, h, tw, th = a["l"], a["w"], a["h"], a["tunnel_w"], a["tunnel_h"]
        blk = box(-l / 2, -w / 2, 0, l / 2, w / 2, h)
        tun = box(-l / 2 - 1, -tw / 2, 0.8, l / 2 + 1, tw / 2, 0.8 + th)
        return (blk - tun).rotate([0, 0, a.get("rot", 0)]).translate(self.W_(a["at"][0], a["at"][1], 0))

    # ---------------------------------------------------------------- lid fixing
    def snap_cfg(self):
        return self.lid_cfg["snap"]

    def snap_positions(self):
        s = self.snap_cfg()
        if s.get("positions"):
            return [tuple(p) for p in s["positions"]]
        out = []
        for wall in s["walls"]:
            span = self.wall_span(wall)
            d = s["spread"] * span / 2
            out += [(wall, span / 2 - d), (wall, span / 2 + d)]
        return out

    def snap_geometry(self):
        s = self.snap_cfg()
        h0 = self.H - s["len"]
        p = s["engage"] + self.tol
        lead = 1.732 * (p + 0.6)
        flat = 0.4
        win0 = h0 + 1.732 * (p - s["engage"] + 0.6) - 0.3
        win1 = h0 + lead + flat + 0.6 + self.tol + s["play"]
        return dict(h0=h0, p=p, lead=lead, flat=flat, win0=win0, win1=win1)

    def snap_windows(self):
        if self.lid_cfg["fix"] != "snap":
            return []
        g, s = self.snap_geometry(), self.snap_cfg()
        return [(w, u, (u - s["w"] / 2 - 0.5, u + s["w"] / 2 + 0.5, g["win0"], g["win1"])) for (w, u) in self.snap_positions()]

    def snap_arm_local(self):
        s, g = self.snap_cfg(), self.snap_geometry()
        tol = self.tol
        arm = box(-s["w"] / 2, g["h0"], -tol - s["t"], s["w"] / 2, self.H + 0.5, -tol)
        e = 0.6
        prof = ps.polygon([[-tol - e, g["h0"]], [-tol + g["p"], g["h0"] + g["lead"]], [-tol + g["p"], g["h0"] + g["lead"] + g["flat"]],
                           [-tol - e, g["h0"] + g["lead"] + g["flat"] + g["p"] + e]])
        nose = ps.multmatrix(ps.linear_extrude(prof, height=s["w"]), [[0, 0, -1, s["w"] / 2], [0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1]])
        return arm | nose

    def post_centres(self):
        i = self.lid_cfg["screws"]["inset"]
        return [(i, i), (self.L - i, i), (i, self.W - i), (self.L - i, self.W - i)]

    def magnet_centres(self):
        if self.lid_cfg["fix"] == "screws":
            return self.post_centres()
        i = self.magnets["inset"]
        return [(i, i), (self.L - i, i), (i, self.W - i), (self.L - i, self.W - i)]

    # ---------------------------------------------------------------- shell helpers
    def rrect(self, l, w, r):
        if r <= 0.01:
            return ps.square([l, w])
        return ps.offset(ps.square([l - 2 * r, w - 2 * r]).translate([r, r, 0]), r=r, fn=self.fn)

    def rbox(self, l, w, h, r):
        return ps.linear_extrude(self.rrect(l, w, r), height=h)

    def chamfered_rbox(self, l, w, h, r, c):
        bottom = ps.linear_extrude(self.rrect(l - 2 * c, w - 2 * c, max(r - c, 0.01)), height=0.01).translate([c, c, 0])
        top = self.rbox(l, w, 0.01, r).translate([0, 0, c])
        return ps.hull(bottom, top) | self.rbox(l, w, h - c, r).translate([0, 0, c])

    def cyl(self, d, h):
        return ps.cylinder(d=d, h=h, fn=self.fn)

    # ---------------------------------------------------------------- BASE
    def base(self):
        w, fl = self.wall, self.floor
        body = self.chamfered_rbox(self.OL, self.OW, self.BH, self.p["r_out"], self.p["chamfer"]) - \
            self.rbox(self.L, self.W, self.BH, 0).translate([w, w, fl])
        adds, cuts, after = [], [], []
        for b in self.boards:
            a, c, l = self.board_seat(b)
            adds += a; cuts += c; after += l
        for k in self.blocks:
            adds += self.block_cradle(k)
        for a in self.anchors:
            adds.append(self.anchor_solid(a))
        adds += self.usb_wedges()
        if self.lid_cfg["fix"] == "screws":
            sc = self.lid_cfg["screws"]
            for (px, py) in self.post_centres():
                cx = 0 if px < self.L / 2 else self.L - 0.01
                cy = 0 if py < self.W / 2 else self.W - 0.01
                adds.append(ps.hull(self.cyl(sc["post_d"], self.H).translate(self.W_(px, py)),
                                    ps.cube([0.01, 0.01, self.H]).translate(self.W_(cx, cy))))
        elif self.magnets:
            mg = self.magnets
            for (mx, my) in self.magnet_centres():
                adds.append(self.cyl(mg["boss_d"], mg["boss_h"] + 0.01).translate(self.W_(mx, my, -0.01)))
        if self.tabs:
            tb = self.tabs
            for wall in tb["walls"]:
                at = tb["at"] if tb["at"] is not None else (self.W / 2 if wall in ("left", "right") else self.L / 2)
                t = self.rbox(tb["len"] + 2 * tb["r"], tb["w"], tb["t"], tb["r"])
                t = t.translate([-tb["len"], w + at - tb["w"] / 2, 0]) & box(-tb["len"] - 1, -1, -1, w / 2, self.OW + 1, tb["t"] + 1)
                if wall == "right":
                    t = t.mirror([1, 0, 0]).translate([self.OL, 0, 0])
                elif wall in ("front", "back"):
                    raise ValueError("tabs are supported on the left/right walls")
                adds.append(t)
        body = body | union(adds)

        for f in self.opening_features():
            cuts.append(self.on_wall(f["cut"], f["wall"], f["u"], f["z"]))
        for v in self.vent_slots():
            cuts.append(self.on_wall(self.through(ps.square([v["w"], v["len"]]).translate([-v["w"] / 2, 0, 0])), v["wall"], v["u"], v["z0"]))
        if self.lid_cfg["fix"] == "snap":
            for (wall, u, g) in self.snap_windows():
                cuts.append(self.on_wall(box(g[0] - u, g[2], -1, g[1] - u, g[3], self.wall + 1), wall, u, 0))
        else:
            sc = self.lid_cfg["screws"]
            for (px, py) in self.post_centres():
                cuts.append(self.cyl(sc["pilot"], sc["depth"] + 0.01).translate([w + px, w + py, self.BH - sc["depth"]]))
        if self.magnets:
            mg = self.magnets
            for (mx, my) in self.magnet_centres():
                cuts.append(self.cyl(mg["hole_d"], mg["h"] + 0.01).translate([w + mx, w + my, -0.01]))
        if self.tabs:
            tb = self.tabs
            for wall in tb["walls"]:
                at = tb["at"] if tb["at"] is not None else self.W / 2
                tx = -tb["len"] / 2 - 0.5 if wall == "left" else self.OL + tb["len"] / 2 + 0.5
                cuts.append(self.cyl(tb["hole"], tb["t"] + 2).translate([tx, w + at, -1]))
        body = body - union(cuts)
        if after:
            body = body | union(after)
        labs = self.label_layout()
        if labs:
            body = body | union([self.label_solid(wl, t, u, z) for (wl, t, u, z, _) in labs])
        return body

    # ---------------------------------------------------------------- LID
    def lid_windows(self):
        """(x, y, d, pipe) in inner coords, including the 180-degree copies when symmetric."""
        out = []
        for wdw in self.lid_cfg["windows"]:
            if isinstance(wdw["at"], str):
                bid, pname = wdw["at"].split("/")
                b = self.board(bid)
                p = next(pp for pp in b["parts"] if pp["name"] == pname)
                x0, y0, z0, x1, y1, z1 = p["box"]
                x, y = self.local_to_inner(b, (x0 + x1) / 2, (y0 + y1) / 2)
                pipe_bottom = b["_top"] + z1
            else:
                x, y = wdw["at"]
                pipe_bottom = wdw.get("pipe_bottom", 10.0)
            out.append((x, y, wdw.get("d", 3.0), wdw.get("pipe", False), pipe_bottom))
            if self.lid_cfg["symmetric_windows"]:
                out.append((self.L - x, self.W - y, wdw.get("d", 3.0), False, pipe_bottom))
        return out

    def lid_assembled(self):
        w, bh, tol = self.wall, self.BH, self.tol
        plate = self.chamfered_rbox(self.OL, self.OW, self.lid_t, self.p["r_out"], self.p["chamfer"]).mirror([0, 0, 1]).translate([0, 0, bh + self.lid_t])
        lip_h, lip_t = self.lid_cfg["lip_h"], self.lid_cfg["lip_t"]
        ring = ps.linear_extrude(ps.offset(ps.square([self.L, self.W]), delta=-tol) - ps.offset(ps.square([self.L, self.W]), delta=-(tol + lip_t)),
                                 height=lip_h + 0.01).translate([w, w, bh - lip_h])
        if self.lid_cfg["fix"] == "snap":
            s = self.snap_cfg()
            for (wall, u) in self.snap_positions():
                ring = ring - self.on_wall(box(-s["w"] / 2 - 0.6, self.H - lip_h - 1, -5, s["w"] / 2 + 0.6, self.H + 0.2, 1), wall, u, 0)
            lid = plate | ring | union([self.on_wall(self.snap_arm_local(), wl, u, 0) for (wl, u) in self.snap_positions()])
        else:
            sc = self.lid_cfg["screws"]
            r = sc["post_d"] / 2 + tol
            for (px, py) in self.post_centres():
                x0 = -1 if px < self.L / 2 else px - r
                x1 = self.L + 1 if px > self.L / 2 else px + r
                y0 = -1 if py < self.W / 2 else py - r
                y1 = self.W + 1 if py > self.W / 2 else py + r
                ring = ring - box(w + x0, w + y0, bh - lip_h - 1, w + x1, w + y1, bh + 0.5)
            lid = plate | ring
        cuts = []
        lp = self.lid_cfg["light_pipe"]
        for (x, y, d, pipe, pb) in self.lid_windows():
            if pipe:
                z_end = self.floor + pb + lp["gap"]
                lid = lid | self.cyl(lp["od"], bh - z_end + 0.01).translate([w + x, w + y, z_end])
            cuts.append(self.cyl(d, bh).translate([w + x, w + y, 5]))
        if self.lid_cfg["fix"] == "screws":
            sc = self.lid_cfg["screws"]
            cuts += [self.cyl(sc["hole"], self.lid_t + 2).translate([w + px, w + py, bh - 1]) for (px, py) in self.post_centres()]
        return lid - union(cuts) if cuts else lid

    def lid_print(self):
        """Turned over for printing by a 180-degree ROTATION about X (a mirror would swap front/back)."""
        return self.lid_assembled().rotate([180, 0, 0]).translate([0, self.OW, self.BH + self.lid_t])

    # ---------------------------------------------------------------- dummies (checks / previews)
    def components(self):
        """name -> solid (world) for collision checks and previews."""
        c = {}
        for b in self.boards:
            L, W, T = b["size"]
            lh = b["ledge_h"]
            top = b["_top"]
            pcb = box(0, 0, lh, L, W, top)
            stubs = [self.cyl(p.get("d", 1.7), b["stub"]["len"]).translate([p["at"][0], p["at"][1], lh - b["stub"]["len"]]) for p in b["_pins"]]
            c[f"{b['id']} pcb"] = self.place_local(union([pcb] + stubs), b)
            for p in b["parts"]:
                x0, y0, z0, x1, y1, z1 = p["box"]
                c[f"{b['id']}/{p['name']}"] = self.place_local(box(x0, y0, top + z0, x1, y1, top + z1), b)
            pl = b["plug"]
            plugs = [box(p["at"][0] - pl["w"] / 2, p["at"][1] - pl["w"] / 2, top + pl["seat"], p["at"][0] + pl["w"] / 2, p["at"][1] + pl["w"] / 2,
                         top + pl["seat"] + pl["height"]) for p in b["_pins"] if p.get("plug", True)]
            if plugs:
                c[f"{b['id']} plugs"] = self.place_local(union(plugs), b)
        for k in self.blocks:
            sx, sy, sz = k["size"]
            c[k["id"]] = self.place_local(box(0, 0, 0, sx, sy, sz), k)
        for pp in self.panels:
            bd = pp.get("body")
            if not bd:
                continue
            depth = bd["depth"]
            nut_ac, nut_t = bd.get("nut_ac", bd["d"] + 1.5), bd.get("nut_t", 2.0)
            # wall-local frame: z = 0 is the inner face, negative z points into the box
            body = self.cyl(bd["d"], depth - nut_t).translate([0, 0, -depth]) | ps.cylinder(d=nut_ac, h=nut_t, fn=6).translate([0, 0, -nut_t])
            c[f"{pp['id']} body"] = self.on_wall(body, pp["wall"], pp["u"], pp["z"])
        return c

    def usb_plugs(self):
        """name -> (shell, overmold) for every usb-c opening: shell 8.25 x 2.4 x 6.6, overmold 12 x 6.5."""
        out = {}
        for o in self.openings:
            if o["type"] != "usb-c":
                continue
            stop = (self.wall - o["recess"]["wall"]) if o.get("recess") else 0.0   # overmold stops this far out
            # wall-local z: 0 = inner face, + outwards; the 6.6 mm shell reaches inwards
            out[o["id"]] = (self.on_wall(box(-4.125, -1.2, self.wall - stop - 6.6, 4.125, 1.2, self.wall - stop), o["wall"], o["u"], o["z"]),
                            self.on_wall(box(-6.0, -3.25, self.wall - stop, 6.0, 3.25, self.wall - stop + 20), o["wall"], o["u"], o["z"]))
        return out

    def metal_parts(self):
        m = {}
        for b in self.boards:
            for p in b["parts"]:
                if p.get("metal"):
                    x0, y0, z0, x1, y1, z1 = p["box"]
                    m[f"{b['id']}/{p['name']}"] = self.place_local(box(x0, y0, b["_top"] + z0, x1, y1, b["_top"] + z1), b)
            if b.get("metal"):
                L, W, _ = b["size"]
                m[f"{b['id']} (module)"] = self.place_local(box(0, 0, b["ledge_h"], L, W, b["_top"] + b.get("height", 5)), b)
        comps = self.components()
        for k in self.blocks:
            if k.get("metal"):
                m[k["id"]] = comps[k["id"]]
        for pp in self.panels:
            if pp.get("metal") and f"{pp['id']} body" in comps:
                m[pp["id"]] = comps[f"{pp['id']} body"]
        if self.magnets:
            mg = self.magnets
            m["magnets"] = union([self.cyl(mg["d"], mg["h"]).translate([self.wall + x, self.wall + y, 0]) for (x, y) in self.magnet_centres()])
        if self.lid_cfg["fix"] == "screws":
            sc = self.lid_cfg["screws"]
            m["lid screws"] = union([self.cyl(3.0, sc["depth"] + self.lid_t).translate([self.wall + x, self.wall + y, self.BH - sc["depth"]])
                                     for (x, y) in self.post_centres()])
        return m

    def antennas(self):
        out = {}
        for b in self.boards:
            for p in b["parts"]:
                if p.get("antenna"):
                    x0, y0, z0, x1, y1, z1 = p["box"]
                    out[f"{b['id']}/{p['name']}"] = (self.place_local(box(x0, y0, b["_top"] + z0, x1, y1, b["_top"] + z1), b), b["antenna_keepout"])
        return out


def _near(a, b, m):
    return not (a[1] + m <= b[0] or b[1] + m <= a[0] or a[3] + m <= b[2] or b[3] + m <= a[2])


def load(path):
    with open(path) as f:
        return Enclosure(json.load(f))
