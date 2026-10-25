#!/usr/bin/env python3
"""Pure-Python review renders (numpy z-buffer rasterizer, no OpenGL / Docker needed).

    python render.py spec.json builddir sheet.png [--views all|name,name,...] [--tile 760x520]

Default views: closed iso (front-left, back-right), open with dummy parts, top view, the four
walls, bottom, lid as printed, and sections through every board and through one snap arm.
Each image gets a title; look at every one of them before calling a design done.
"""
import argparse, json, math, os, sys
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BG = (247, 247, 245)
COL = {"base": (74, 120, 168), "lid": (143, 177, 214), "pcb": (40, 40, 40), "part": (190, 190, 190),
       "plugs": (242, 201, 76), "block": (224, 224, 224), "body": (130, 130, 130), "plug": (221, 153, 68),
       "antenna": (220, 50, 50), "cut": (40, 130, 120)}


def font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def camera(azim, elev):
    """Unit view direction (camera -> scene) for azimuth (deg, 0 = looking from -Y) and elevation."""
    a, e = math.radians(azim), math.radians(elev)
    eye = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
    d = -eye
    up = np.array([0.0, 0.0, 1.0]) if abs(e) < math.radians(89) else np.array([0.0, 1.0, 0.0])
    right = np.cross(d, up); right /= np.linalg.norm(right)
    up2 = np.cross(right, d)
    return d, right, up2


def rasterize(meshes, azim, elev, size, pad=0.06, ss=2):
    """meshes: list of (trimesh, rgb, cut) with cut = (plane_origin, plane_normal) or None. Returns PIL image."""
    W, H = size[0] * ss, size[1] * ss
    d, right, up = camera(azim, elev)
    allv = np.vstack([m.vertices for m, _, _ in meshes])
    sx, sy = allv @ right, allv @ up
    x0, x1, y0, y1 = sx.min(), sx.max(), sy.min(), sy.max()
    scale = min(W * (1 - 2 * pad) / max(x1 - x0, 1e-6), H * (1 - 2 * pad) / max(y1 - y0, 1e-6))
    ox, oy = W / 2 - scale * (x0 + x1) / 2, H / 2 + scale * (y0 + y1) / 2
    zbuf = np.full((H, W), np.inf)
    img = np.empty((H, W, 3)); img[:] = BG
    fid = np.full((H, W), -1, dtype=np.int64)
    light = -d * 0.75 + up * 0.45 + right * 0.25
    light /= np.linalg.norm(light)
    base_id = 0
    normals_all = []
    for m, rgb, cutn in meshes:
        tri = m.triangles
        n = m.face_normals
        normals_all.append(n)
        shade = 0.38 + 0.62 * np.clip(np.abs(n @ light), 0, 1) * np.where(n @ -d >= 0, 1.0, 0.75)
        cols = np.outer(shade, np.array(rgb, float))
        if cutn is not None:                       # colour only the cap faces lying ON the cutting plane
            org, nrm = np.asarray(cutn[0], float), np.asarray(cutn[1], float)
            iscut = (np.abs(n @ nrm) > 0.999) & (np.abs((m.triangles_center - org) @ nrm) < 1e-3)
            cols[iscut] = np.array(COL["cut"], float) * 0.95
        px = scale * (tri @ right) + ox
        py = -scale * (tri @ up) + oy
        pz = tri @ d
        for i in range(len(tri)):
            xa, ya, za = px[i], py[i], pz[i]
            bx0, bx1 = max(int(xa.min()), 0), min(int(xa.max()) + 1, W - 1)
            by0, by1 = max(int(ya.min()), 0), min(int(ya.max()) + 1, H - 1)
            if bx1 < bx0 or by1 < by0:
                continue
            gx, gy = np.meshgrid(np.arange(bx0, bx1 + 1) + 0.5, np.arange(by0, by1 + 1) + 0.5)
            (x_0, x_1, x_2), (y_0, y_1, y_2) = xa, ya
            den = (y_1 - y_2) * (x_0 - x_2) + (x_2 - x_1) * (y_0 - y_2)
            if abs(den) < 1e-12:
                continue
            l0 = ((y_1 - y_2) * (gx - x_2) + (x_2 - x_1) * (gy - y_2)) / den
            l1 = ((y_2 - y_0) * (gx - x_2) + (x_0 - x_2) * (gy - y_2)) / den
            l2 = 1 - l0 - l1
            inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            if not inside.any():
                continue
            z = l0 * za[0] + l1 * za[1] + l2 * za[2]
            sub = zbuf[by0:by1 + 1, bx0:bx1 + 1]
            upd = inside & (z < sub - 1e-9)
            if upd.any():
                sub[upd] = z[upd]
                img[by0:by1 + 1, bx0:bx1 + 1][upd] = cols[i]
                fid[by0:by1 + 1, bx0:bx1 + 1][upd] = base_id + i
        base_id += len(tri)
    # edge lines: face normal changes or depth jumps
    N = np.vstack(normals_all) if normals_all else np.zeros((0, 3))
    nb = np.zeros((H, W, 3))
    ok = fid >= 0
    nb[ok] = N[fid[ok]]
    zf = np.where(np.isfinite(zbuf), zbuf, zbuf[np.isfinite(zbuf)].max() + 50 if np.isfinite(zbuf).any() else 0)
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a_n, b_n = nb[: H - dy, : W - dx], nb[dy:, dx:]
        a_z, b_z = zf[: H - dy, : W - dx], zf[dy:, dx:]
        a_o, b_o = ok[: H - dy, : W - dx], ok[dy:, dx:]
        both = a_o & b_o
        e = (both & ((a_n * b_n).sum(-1) < 0.85)) | (both & (np.abs(a_z - b_z) > 4.8 / scale)) | (a_o != b_o)
        edge[: H - dy, : W - dx] |= e
    img[edge] = img[edge] * 0.35
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return im.resize(size, Image.LANCZOS)


def load(path):
    return trimesh.load(path, force="mesh")


def clip(mesh, origin, normal):
    """Keep the half-space on the side of `normal`, with a cap on the cut."""
    try:
        return mesh.slice_plane(origin, normal, cap=True)
    except Exception:
        return mesh.slice_plane(origin, normal)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("build"); ap.add_argument("out")
    ap.add_argument("--views", default="all")
    ap.add_argument("--tile", default="760x520")
    a = ap.parse_args()
    tw, th = [int(v) for v in a.tile.split("x")]
    import encl
    E = encl.load(a.spec)
    B = a.build
    base = load(os.path.join(B, "base.stl"))
    lid = load(os.path.join(B, "lid_assembled.stl"))
    lidp = load(os.path.join(B, "lid.stl"))
    pdir = os.path.join(B, "parts")
    parts = []
    for f in sorted(os.listdir(pdir)):
        name = f[:-4]
        m = load(os.path.join(pdir, f))
        if name.endswith("_plug"):
            c = COL["plug"]
        elif name.endswith("plugs"):
            c = COL["plugs"]
        elif name.endswith("pcb"):
            c = COL["pcb"]
        elif "antenna" in name:
            c = COL["antenna"]
        elif name.endswith("body"):
            c = COL["body"]
        elif any(name == k["id"] for k in E.blocks):
            c = COL["block"]
        else:
            c = COL["part"]
        parts.append((name, m, c))
    no_plugs = [(m, c, None) for n, m, c in parts if not n.endswith("plugs") and not n.endswith("_plug")]
    all_parts = [(m, c, None) for n, m, c in parts]

    views = []
    views.append(("closed - front/left", [(base, COL["base"], None), (lid, COL["lid"], None)], -35, 28))
    views.append(("closed - back/right", [(base, COL["base"], None), (lid, COL["lid"], None)], 145, 28))
    views.append(("open, dummy parts + plugs", [(base, COL["base"], None)] + all_parts, -30, 50))
    views.append(("top view (no plugs)", [(base, COL["base"], None)] + no_plugs, 0, 90))
    for wall, az in (("front", 0), ("back", 180), ("left", -90), ("right", 90)):
        views.append((f"{wall} wall", [(base, COL["base"], None), (lid, COL["lid"], None)], az, 4))
    views.append(("bottom", [(base, COL["base"], None)], -30, -55))
    views.append(("lid as printed", [(lidp, COL["lid"], None)], -30, 45))
    w = E.wall
    for b in E.boards:
        bb = E.pcb_aabb(b)
        cx, cy = w + (bb[0] + bb[1]) / 2, w + (bb[2] + bb[3]) / 2
        n = np.array([0, 1.0, 0])
        cut = ([0, cy, 0], n)
        sec = [(clip(base, [0, cy, 0], n), COL["base"], cut), (clip(lid, [0, cy, 0], n), COL["lid"], cut)]
        for nm, m, c in parts:
            if not nm.endswith("_plug"):
                cm = clip(m, [0, cy, 0], n)
                if len(cm.faces):
                    sec.append((cm, c, cut))
        views.append((f"section through {b['id']} (Y={cy - w:.1f}, seen from front)", sec, 0, 0))
    if E.lid_cfg["fix"] == "snap":
        wl, u = E.snap_positions()[0]
        if wl in ("front", "back"):
            n = np.array([1.0, 0, 0])
            cut = ([w + u, 0, 0], n)
            sec = [(clip(base, [w + u, 0, 0], n), COL["base"], cut), (clip(lid, [w + u, 0, 0], n), COL["lid"], cut)]
            views.append((f"section through snap arm ({wl}, u={u:.1f})", sec, -90, 0))
    if a.views != "all":
        keep = [v.strip() for v in a.views.split(",")]
        views = [v for v in views if any(k in v[0] for k in keep)]
    tiles = []
    for title, ms, az, el in views:
        ms = [(m, c, cn) for (m, c, cn) in ms if m is not None and len(m.faces)]
        im = rasterize(ms, az, el, (tw, th))
        ImageDraw.Draw(im).text((10, 8), title, fill=(0, 0, 0), font=font(18))
        tiles.append(im)
        print("rendered", title, flush=True)
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (tw * cols, th * rows), "white")
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    sheet.save(a.out)
    print("sheet", a.out, sheet.size)


if __name__ == "__main__":
    main()
