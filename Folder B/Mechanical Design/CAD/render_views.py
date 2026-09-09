#!/usr/bin/env python3
"""
Render shaded views of the Lightning McQueen chassis straight from the
CadQuery solids (no external renderer required).

Every view merges all parts into a single triangle soup before drawing, so
the painter's-algorithm depth sort is global and parts occlude each other
correctly.

Produces, in ../renders/:
    01_isometric.png        - hero view, assembled
    02_exploded.png         - exploded assembly with part callouts
    03_orthographic.png     - top / side / front
    04_safety_annotated.png - E-Stop and ON/OFF switch called out (rules 3 & 4)
    05_underside.png        - drivetrain, castor and sensor boom

Run:  python3 render_views.py
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.lines import Line2D

import lightning_mcqueen_cad as M

TOL = 0.30
LIGHT = np.array([-0.40, -0.62, 0.68])
LIGHT /= np.linalg.norm(LIGHT)
BG = "#F4F5F7"
INK = "#1B1F24"


MAX_EDGE = 18.0        # mm; keeps the painter's-algorithm sort honest


def _subdivide(tri, max_edge=MAX_EDGE, cap=400000):
    """Longest-edge bisection until no triangle spans more than max_edge.

    Flat faces tessellate into a handful of very large triangles, and a
    depth sort keyed on triangle centroids then puts a 300 mm deck plate
    behind parts that sit on top of it. Splitting the big ones fixes the
    ordering without changing the geometry.
    """
    work = list(tri)
    out = []
    while work:
        if len(out) + len(work) > cap:
            out.extend(work)
            break
        t = work.pop()
        e = [np.linalg.norm(t[1] - t[0]),
             np.linalg.norm(t[2] - t[1]),
             np.linalg.norm(t[0] - t[2])]
        i = int(np.argmax(e))
        if e[i] <= max_edge:
            out.append(t)
            continue
        a, b, c = t[i], t[(i + 1) % 3], t[(i + 2) % 3]
        m = (a + b) / 2.0
        work.append(np.array([a, m, c]))
        work.append(np.array([m, b, c]))
    return np.array(out)


def tessellate(wp):
    verts, tris = wp.val().tessellate(TOL)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    return v, np.array(tris, dtype=int)


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def build_meshes():
    solids = M.build()
    out = []
    for name, fn, colour, desc in M.PARTS:
        v, t = tessellate(solids[name])
        out.append((name, v, t, colour))
    return out, {n: d for n, _, _, d in M.PARTS}


def soup(meshes, lift=None, alpha_map=None):
    """Merge parts into one (tris, facecolors) pair with Lambert shading."""
    tri_list, col_list = [], []
    for name, v, t, colour in meshes:
        vv = v.copy()
        if lift:
            vv[:, 2] = vv[:, 2] + lift.get(name, 0)
        tri = _subdivide(vv[t])
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        ln = np.linalg.norm(n, axis=1)
        ln[ln == 0] = 1.0
        n /= ln[:, None]
        lam = np.clip(np.abs(n @ LIGHT), 0.0, 1.0)
        f = 0.40 + 0.60 * lam
        base = hex_rgb(colour)
        rgb = np.clip(base[None, :] * f[:, None], 0, 1)
        a = 1.0 if alpha_map is None else alpha_map.get(name, 1.0)
        rgba = np.concatenate([rgb, np.full((len(rgb), 1), a)], axis=1)
        tri_list.append(tri)
        col_list.append(rgba)
    return np.vstack(tri_list), np.vstack(col_list)


def draw(ax, tris, cols, edge=None, lw=0.0):
    pc = Poly3DCollection(tris, facecolors=cols, linewidths=lw,
                          edgecolors=edge if edge else "none")
    pc.set_zsort("average")
    ax.add_collection3d(pc)


def frame(ax, tris, elev, azim, pad=0.04, roll=0.0):
    p = tris.reshape(-1, 3)
    lo, hi = p.min(axis=0), p.max(axis=0)
    span = np.maximum(hi - lo, 1e-6)
    m = span * pad
    lo, hi = lo - m, hi + m
    span = hi - lo
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(tuple(span))     # true 1:1:1 proportions
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_facecolor(BG)


def title(fig, main, sub):
    fig.text(0.04, 0.962, main, fontsize=18, color=INK, weight="bold",
             va="top")
    fig.text(0.04, 0.918, sub, fontsize=10.5, color="#5B6470", va="top")
    fig.text(0.965, 0.030, "Team CO Coders  ·  Lightning McQueen  ·  "
                           "Robo Rumble 2026 · Robo Grand Prix",
             fontsize=8.5, color="#98A0AA", ha="right", va="bottom")


def note(fig, x, y, text, fg, bg, ec):
    fig.text(x, y, text, fontsize=9.5, color=fg, va="top",
             bbox=dict(boxstyle="round,pad=0.6", fc=bg, ec=ec, lw=1.4))


# ------------------------------------------------------------------ views

def view_isometric(meshes, outdir):
    fig = plt.figure(figsize=(13, 8), facecolor=BG)
    ax = fig.add_subplot(111, projection="3d", facecolor=BG)
    tris, cols = soup(meshes)
    draw(ax, tris, cols)
    frame(ax, tris, elev=26, azim=-56)
    title(fig, "Assembled chassis — isometric",
          "300 × 200 mm acrylic deck · 170 mm track · 65 mm drive wheels · "
          "overall envelope 300 × 211 × 107 mm against a 500 × 500 mm limit")
    fig.subplots_adjust(left=0, right=1, top=0.90, bottom=0)
    fig.savefig(os.path.join(outdir, "01_isometric.png"), dpi=165,
                facecolor=BG)
    plt.close(fig)


def view_exploded(meshes, descs, outdir):
    fig = plt.figure(figsize=(13.5, 9), facecolor=BG)
    ax = fig.add_subplot(111, projection="3d", facecolor=BG)
    tris, cols = soup(meshes, M.EXPLODE)
    draw(ax, tris, cols)
    frame(ax, tris, elev=16, azim=-60)

    seen, handles = set(), []
    for name, v, t, c in meshes:
        d = descs[name]
        if d in seen:
            continue
        seen.add(d)
        handles.append(Line2D([0], [0], marker="s", linestyle="none",
                              markersize=9, markerfacecolor=c,
                              markeredgecolor="#00000033", label=d))
    fig.legend(handles=handles, loc="center right", bbox_to_anchor=(0.995, 0.46),
               frameon=False, fontsize=9, labelspacing=0.85)
    title(fig, "Exploded assembly — fastening and stack-up",
          "Deck modules bolt down on M3 nylon standoffs · motors, castor and "
          "sensor boom hang below the deck · every joint bolted, none glued")
    fig.subplots_adjust(left=-0.06, right=0.80, top=0.90, bottom=0)
    fig.savefig(os.path.join(outdir, "02_exploded.png"), dpi=165, facecolor=BG)
    plt.close(fig)


def view_orthographic(meshes, outdir):
    fig = plt.figure(figsize=(15.5, 5.4), facecolor=BG)
    tris, cols = soup(meshes)
    views = [(89.0, -90.0, "TOP — 300 × 200 mm deck, 170 mm track"),
             (0.0, -90.0, "SIDE — 45 mm deck height, 42 mm clearance"),
             (0.0, 0.0, "FRONT — 211 mm wide, 12 mm sensor ride height")]
    for i, (elev, azim, lab) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d", facecolor=BG)
        draw(ax, tris, cols)
        frame(ax, tris, elev=elev, azim=azim)
        ax.set_title(lab, fontsize=10.5, color=INK, y=0.02)
    title(fig, "Orthographic views",
          "Drawn 1:1 from the parametric model in lightning_mcqueen_cad.py · "
          "all dimensions in millimetres")
    fig.subplots_adjust(left=0.0, right=1.0, top=0.88, bottom=0.0, wspace=0.0)
    fig.savefig(os.path.join(outdir, "03_orthographic.png"), dpi=165,
                facecolor=BG)
    plt.close(fig)


def view_safety(meshes, outdir):
    """Rule 3 (ON/OFF) and Rule 4 (E-Stop) called out explicitly."""
    fig = plt.figure(figsize=(13.5, 8.4), facecolor=BG)
    ax = fig.add_subplot(111, projection="3d", facecolor=BG)
    hot = {"estop_head", "estop_mast", "power_switch"}
    alpha = {n: (1.0 if n in hot else 0.22) for n, _, _, _ in meshes}
    tris, cols = soup(meshes, alpha_map=alpha)
    draw(ax, tris, cols)
    frame(ax, tris, elev=28, azim=-124)

    note(fig, 0.045, 0.80,
         "E-STOP  —  Universal Constraint 4\n"
         "22 mm latching mushroom head on a 48 mm mast,\n"
         "rear centreline, nothing overhanging it.\n"
         "Wired in the battery positive line UPSTREAM of\n"
         "the ON/OFF switch and the L298N, so one palm\n"
         "strike cuts logic and motor power together.\n"
         "Latches down — power cannot restore itself.",
         "#8E1512", "#FCEAE9", "#D5231F")
    note(fig, 0.045, 0.34,
         "ON/OFF  —  Universal Constraint 3\n"
         "SPST rocker on the rear-left corner, clear of\n"
         "the wheels and the sensor boom. Reachable with\n"
         "the car sitting on the track, no lifting, no\n"
         "reaching over a spinning wheel.",
         "#1B3A5C", "#E9F0F8", "#2C6FA8")
    title(fig, "Safety hardware — annotated",
          "Robo Rumble Universal Design Constraints 3 and 4 · "
          "both devices operable without touching the drivetrain")
    fig.subplots_adjust(left=0, right=1, top=0.90, bottom=0)
    fig.savefig(os.path.join(outdir, "04_safety_annotated.png"), dpi=165,
                facecolor=BG)
    plt.close(fig)


def view_underside(meshes, outdir):
    fig = plt.figure(figsize=(13, 8), facecolor=BG)
    ax = fig.add_subplot(111, projection="3d", facecolor=BG)
    hide = {"breadboard", "arduino_uno", "l298n", "batteries",
            "estop_mast", "estop_head", "power_switch"}
    sub = [m for m in meshes if m[0] not in hide]
    tris, cols = soup(sub)
    draw(ax, tris, cols)
    frame(ax, tris, elev=-32, azim=-62)
    title(fig, "Underside — drivetrain and sensing",
          "TT gear motors bolted through the deck · rear ball castor · "
          "5-channel TCRT5000 array on 30 mm standoffs, 12 mm above the floor")
    fig.subplots_adjust(left=0, right=1, top=0.90, bottom=0)
    fig.savefig(os.path.join(outdir, "05_underside.png"), dpi=165, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.abspath(os.path.join(here, "..", "renders"))
    os.makedirs(outdir, exist_ok=True)

    meshes, descs = build_meshes()
    view_isometric(meshes, outdir)
    view_exploded(meshes, descs, outdir)
    view_orthographic(meshes, outdir)
    view_safety(meshes, outdir)
    view_underside(meshes, outdir)
    print("renders written to", outdir)
