#!/usr/bin/env python3
"""
Lightning McQueen - Robo Grand Prix 2026 - Team CO Coders
=========================================================
Parametric CAD model of the autonomous line-following chassis.

Built with CadQuery 2.x (OpenCASCADE kernel). Every dimension below is a
named parameter, so the whole vehicle can be re-proportioned by editing the
PARAMETERS block and re-running this file.

Outputs (written to ../CAD/ and ../renders/):
    STEP/*.step   - exchange format, opens in Fusion 360 / SolidWorks / FreeCAD
    STL/*.stl     - mesh format, for 3D printing and laser-cut DXF derivation
    assembly.step - full assembly, coloured
    renders/*.png - shaded views generated from the tessellated solids

Run:  python3 lightning_mcqueen_cad.py
"""

import os
import math
import cadquery as cq
from cadquery import exporters

# =========================================================================
# PARAMETERS  (all dimensions in millimetres)
# =========================================================================

# --- Competition envelope -------------------------------------------------
MAX_FOOTPRINT = 500.0          # Robo Rumble rule: 50 cm x 50 cm
MAX_MASS_KG = 5.0              # Robo Rumble rule: strictly below 5 kg

# --- Base plate (the 20 x 30 cm deck the README specifies) ---------------
PLATE_L = 300.0                # X, nose-to-tail
PLATE_W = 200.0                # Y, across the car
PLATE_T = 3.0                  # 3 mm cast acrylic, laser cut
PLATE_CORNER_R = 12.0

# --- Ride height ----------------------------------------------------------
WHEEL_D = 65.0
WHEEL_R = WHEEL_D / 2.0
WHEEL_W = 26.0
PLATE_UNDERSIDE_Z = 42.0       # ground clearance to the underside of the deck
PLATE_TOP_Z = PLATE_UNDERSIDE_Z + PLATE_T

# --- Drivetrain -----------------------------------------------------------
AXLE_X = 150.0                 # drive axle position measured from the tail
TRACK = 170.0                  # centre-to-centre of the two wheels
MOTOR_BODY_L = 70.0            # TT gearbox, along the axle
MOTOR_BODY_W = 22.5
MOTOR_BODY_H = 18.8
MOTOR_CAN_D = 24.0             # the round motor can hanging off the gearbox
MOTOR_CAN_L = 36.0

# --- Castor (rear) --------------------------------------------------------
CASTOR_X = 32.0
CASTOR_BALL_D = 20.0
CASTOR_PLATE = 32.0

# --- Sensor boom (front) --------------------------------------------------
SENSOR_X = 288.0               # array centreline, from the tail
SENSOR_PCB_L = 20.0
SENSOR_PCB_W = 96.0
SENSOR_PCB_T = 1.6
SENSOR_RIDE_H = 12.0           # emitter face to floor: TCRT5000 optimum 8-15 mm
SENSOR_COUNT = 5
SENSOR_PITCH = 20.0            # spacing between adjacent TCRT5000 packages
SENSOR_PKG = 10.2              # TCRT5000 body, square-ish
STANDOFF_D = 6.0

# --- Electronics footprints ----------------------------------------------
BREADBOARD_L, BREADBOARD_W, BREADBOARD_H = 165.0, 55.0, 10.0
BREADBOARD_X = 175.0
ARDUINO_L, ARDUINO_W, ARDUINO_H = 68.6, 53.4, 15.0
ARDUINO_X, ARDUINO_Y = 75.0, -56.0
L298N_L, L298N_W, L298N_H = 43.0, 43.0, 27.0
L298N_X, L298N_Y = 75.0, 55.0
BATT_L, BATT_W, BATT_H = 50.0, 27.0, 19.0
BATT_X = 240.0
BATT_Y = 66.0

# --- Safety hardware (MANDATORY per Robo Rumble rules 3 and 4) -----------
ESTOP_X, ESTOP_Y = 64.0, 0.0   # rear centre: reachable from above and behind
ESTOP_MAST_D = 30.0
ESTOP_MAST_H = 48.0
ESTOP_HEAD_D = 40.0            # 22 mm thread, 40 mm mushroom head
ESTOP_HEAD_H = 14.0
SWITCH_X, SWITCH_Y = 20.0, -58.0
SWITCH_L, SWITCH_W, SWITCH_H = 21.0, 15.0, 14.0

# --- Fasteners ------------------------------------------------------------
M3 = 3.2                       # clearance hole for M3
LIGHTEN_D = 20.0               # mass-reduction holes in the deck


# =========================================================================
# PART BUILDERS
# =========================================================================

def _drill(solid, points, dia):
    """Subtract a set of through-holes at absolute (x, y) deck coordinates."""
    for x, y in points:
        cutter = (
            cq.Workplane("XY").workplane(offset=-5.0)
            .center(x, y).circle(dia / 2.0).extrude(PLATE_T + 10.0)
        )
        solid = solid.cut(cutter)
    return solid


def base_plate():
    """3 mm laser-cut acrylic deck: rounded shell, lightening holes, and the
    full mounting hole pattern for every module and the safety hardware.

    The hole pattern below is what gets projected to DXF for the laser
    cutter; nothing on this vehicle is drilled by hand."""
    p = (
        cq.Workplane("XY")
        .box(PLATE_L, PLATE_W, PLATE_T, centered=(False, True, False))
        .edges("|Z").fillet(PLATE_CORNER_R)
    )

    # --- M3 clearance holes -------------------------------------------
    m3_points = []

    # Motor mounts: the TT gearbox bolts through the deck, two bolts a side.
    for side in (-1, 1):
        y = side * (TRACK / 2.0 - WHEEL_W / 2.0 - 6.0)
        m3_points += [(AXLE_X - 18.0, y), (AXLE_X + 18.0, y)]

    # Castor mounting square.
    c = (CASTOR_PLATE - 8.0) / 2.0
    m3_points += [(CASTOR_X - c, -c), (CASTOR_X + c, -c),
                  (CASTOR_X - c, c), (CASTOR_X + c, c)]

    # Sensor boom standoffs.
    m3_points += [(SENSOR_X, -40.0), (SENSOR_X, 40.0)]

    # Deck module mounts: breadboard corners, Arduino, L298N, battery straps.
    for dx in (-1, 1):
        for dy in (-1, 1):
            m3_points.append((BREADBOARD_X + dx * 74.0, dy * 22.0))
            m3_points.append((ARDUINO_X + dx * 24.0, ARDUINO_Y + dy * 22.0))
            m3_points.append((L298N_X + dx * 18.0, L298N_Y + dy * 18.0))

    # E-Stop mast bolt circle (4 x M3 on a 22 mm radius).
    for i in range(4):
        a = math.radians(45 + 90 * i)
        m3_points.append((ESTOP_X + 22.0 * math.cos(a),
                          ESTOP_Y + 22.0 * math.sin(a)))

    p = _drill(p, m3_points, M3)

    # --- 22 mm through-hole for the E-Stop button body ----------------
    p = _drill(p, [(ESTOP_X, ESTOP_Y)], 22.5)

    # --- Lightening holes: two rows outboard of the breadboard --------
    light = [(x, y) for x in (120.0, 150.0, 180.0, 210.0, 240.0)
             for y in (-40.0, 40.0)]
    p = _drill(p, light, LIGHTEN_D)

    # --- Cable pass-throughs between the deck and the underside loom --
    for x in (AXLE_X - 45.0, AXLE_X + 45.0):
        slot = (
            cq.Workplane("XY").workplane(offset=-5.0)
            .center(x, 0.0).slot2D(30.0, 9.0, 90).extrude(PLATE_T + 10.0)
        )
        p = p.cut(slot)

    return p.translate((0, 0, PLATE_UNDERSIDE_Z))


def wheel(side):
    """65 mm TT wheel: rim plus a soft tyre band."""
    y = side * TRACK / 2.0
    rim = (
        cq.Workplane("XZ").workplane(offset=-y)
        .circle(WHEEL_R - 5.4).extrude(WHEEL_W, both=False)
    )
    tyre = (
        cq.Workplane("XZ").workplane(offset=-y)
        .circle(WHEEL_R).circle(WHEEL_R - 5.0).extrude(WHEEL_W)
    )
    body = rim.union(tyre)
    return body.translate((AXLE_X, 0, WHEEL_R))


def tyre(side):
    y = side * TRACK / 2.0
    t = (
        cq.Workplane("XZ").workplane(offset=-y)
        .circle(WHEEL_R).circle(WHEEL_R - 5.0).extrude(WHEEL_W)
    )
    return t.translate((AXLE_X, 0, WHEEL_R))


def rim(side):
    y = side * TRACK / 2.0
    r = (
        cq.Workplane("XZ").workplane(offset=-y)
        .circle(WHEEL_R - 5.4).extrude(WHEEL_W)
    )
    return r.translate((AXLE_X, 0, WHEEL_R))


def tt_motor(side):
    """Yellow TT gear motor: rectangular gearbox with the can offset rearward."""
    inner = 4.0
    outer = TRACK / 2.0 - WHEEL_W / 2.0 - 2.0
    length = outer - inner
    y0 = side * inner
    gearbox = (
        cq.Workplane("XY")
        .box(MOTOR_BODY_W, length, MOTOR_BODY_H, centered=(True, False, True))
    )
    if side < 0:
        gearbox = gearbox.mirror("XZ")
    gearbox = gearbox.translate((AXLE_X, y0, WHEEL_R))

    can = (
        cq.Workplane("XY").workplane(offset=WHEEL_R)
        .center(AXLE_X - MOTOR_BODY_W / 2.0 - MOTOR_CAN_L / 2.0,
                side * (inner + length * 0.55))
        .circle(MOTOR_CAN_D / 2.0).extrude(0.1)
    )
    can = (
        cq.Workplane("YZ")
        .workplane(offset=AXLE_X - MOTOR_BODY_W / 2.0 - MOTOR_CAN_L)
        .center(side * (inner + length * 0.5), WHEEL_R)
        .circle(MOTOR_CAN_D / 2.0).extrude(MOTOR_CAN_L)
    )
    return gearbox.union(can)


def castor():
    """Rear ball castor: mounting plate, stem, ball."""
    stem_h = PLATE_UNDERSIDE_Z - CASTOR_BALL_D
    plate = (
        cq.Workplane("XY").workplane(offset=PLATE_UNDERSIDE_Z - 4.0)
        .center(CASTOR_X, 0).box(CASTOR_PLATE, CASTOR_PLATE, 4.0,
                                 centered=(True, True, False))
    )
    stem = (
        cq.Workplane("XY").workplane(offset=CASTOR_BALL_D * 0.6)
        .center(CASTOR_X, 0).circle(9.0)
        .extrude(PLATE_UNDERSIDE_Z - 4.0 - CASTOR_BALL_D * 0.6)
    )
    ball = cq.Workplane("XY").sphere(CASTOR_BALL_D / 2.0)
    ball = ball.translate((CASTOR_X, 0, CASTOR_BALL_D / 2.0))
    return plate.union(stem).union(ball)


def sensor_array():
    """5-channel TCRT5000 reflective array on a downward-facing PCB."""
    z = SENSOR_RIDE_H + SENSOR_PKG
    pcb = (
        cq.Workplane("XY").workplane(offset=z)
        .center(SENSOR_X, 0).box(SENSOR_PCB_L, SENSOR_PCB_W, SENSOR_PCB_T,
                                 centered=(True, True, False))
    )
    return pcb


def sensor_packages():
    """The five TCRT5000 emitter/detector bodies, looking straight down."""
    z = SENSOR_RIDE_H
    pts = [(SENSOR_X, (i - (SENSOR_COUNT - 1) / 2.0) * SENSOR_PITCH)
           for i in range(SENSOR_COUNT)]
    body = None
    for x, y in pts:
        b = (
            cq.Workplane("XY").workplane(offset=z)
            .center(x, y).box(SENSOR_PKG, SENSOR_PKG * 0.6, SENSOR_PKG,
                              centered=(True, True, False))
        )
        body = b if body is None else body.union(b)
    return body


def sensor_standoffs():
    z0 = SENSOR_RIDE_H + SENSOR_PKG + SENSOR_PCB_T
    h = PLATE_UNDERSIDE_Z - z0
    s = None
    for y in (-40.0, 40.0):
        p = (
            cq.Workplane("XY").workplane(offset=z0)
            .center(SENSOR_X, y).circle(STANDOFF_D / 2.0).extrude(h)
        )
        s = p if s is None else s.union(p)
    return s


def _deck_box(x, y, l, w, h, z=None):
    z = PLATE_TOP_Z + 0.4 if z is None else z
    return (
        cq.Workplane("XY").workplane(offset=z)
        .center(x, y).box(l, w, h, centered=(True, True, False))
    )


def breadboard():
    bb = _deck_box(BREADBOARD_X, 0.0, BREADBOARD_L, BREADBOARD_W, BREADBOARD_H)
    return bb.edges("|Z").fillet(2.0)


def arduino():
    return _deck_box(ARDUINO_X, ARDUINO_Y, ARDUINO_L, ARDUINO_W, ARDUINO_H,
                     z=PLATE_TOP_Z + 8.0)


def l298n():
    return _deck_box(L298N_X, L298N_Y, L298N_L, L298N_W, L298N_H,
                     z=PLATE_TOP_Z + 8.0)


def batteries():
    b = None
    for side in (-1, 1):
        p = _deck_box(BATT_X, side * BATT_Y, BATT_L, BATT_W, BATT_H)
        b = p if b is None else b.union(p)
    return b


def estop_mast():
    """Mast that lifts the latching mushroom head clear of the loom."""
    return (
        cq.Workplane("XY").workplane(offset=PLATE_TOP_Z)
        .center(ESTOP_X, ESTOP_Y).circle(ESTOP_MAST_D / 2.0)
        .extrude(ESTOP_MAST_H)
    )


def estop_head():
    """22 mm latching emergency stop, red mushroom head.
    Breaks the battery positive line ahead of everything else."""
    z = PLATE_TOP_Z + ESTOP_MAST_H
    head = (
        cq.Workplane("XY").workplane(offset=z)
        .circle(ESTOP_HEAD_D / 2.0).extrude(ESTOP_HEAD_H)
        .edges(">Z").fillet(4.0)
    )
    return head.translate((ESTOP_X, ESTOP_Y, 0))


def power_switch():
    """Mandatory, easily accessible ON/OFF rocker on the left flank."""
    body = _deck_box(SWITCH_X, SWITCH_Y, SWITCH_L, SWITCH_W, SWITCH_H,
                     z=PLATE_TOP_Z + 6.0)
    bracket = _deck_box(SWITCH_X, SWITCH_Y, SWITCH_L + 6, 2.0, 6.0)
    return body.union(bracket)


# =========================================================================
# ASSEMBLY
# =========================================================================

PARTS = [
    ("base_plate",        base_plate,        "#B9C6D4", "3 mm laser-cut acrylic deck"),
    ("tyre_left",         lambda: tyre(-1),  "#2B2B30", "65 mm rubber tyre"),
    ("tyre_right",        lambda: tyre(1),   "#2B2B30", "65 mm rubber tyre"),
    ("rim_left",          lambda: rim(-1),   "#F2C230", "TT wheel rim"),
    ("rim_right",         lambda: rim(1),    "#F2C230", "TT wheel rim"),
    ("motor_left",        lambda: tt_motor(-1), "#E8B321", "TT gear motor 1:48"),
    ("motor_right",       lambda: tt_motor(1),  "#E8B321", "TT gear motor 1:48"),
    ("castor",            castor,            "#9AA3AD", "Rear ball castor"),
    ("sensor_pcb",        sensor_array,      "#1F7A4D", "5ch TCRT5000 array PCB"),
    ("sensor_packages",   sensor_packages,   "#141418", "TCRT5000 emitter/detector"),
    ("sensor_standoffs",  sensor_standoffs,  "#9AA3AD", "M3 nylon standoffs"),
    ("breadboard",        breadboard,        "#F4F4F0", "830-point breadboard"),
    ("arduino_uno",       arduino,           "#0E8A8A", "Arduino Uno R3"),
    ("l298n",             l298n,             "#123A6B", "L298N dual H-bridge"),
    ("batteries",         batteries,         "#3A3A42", "2 x 9 V PP3 holder"),
    ("estop_mast",        estop_mast,        "#5A6472", "E-Stop mast"),
    ("estop_head",        estop_head,        "#D5231F", "E-STOP latching mushroom"),
    ("power_switch",      power_switch,      "#101014", "ON/OFF rocker switch"),
]

# Exploded-view lift, applied per part along +Z.
EXPLODE = {
    "breadboard": 70, "arduino_uno": 70, "l298n": 70, "batteries": 70,
    "estop_mast": 100, "estop_head": 130, "power_switch": 85,
    "base_plate": 30,
    "sensor_pcb": -18, "sensor_packages": -30, "sensor_standoffs": -10,
    "motor_left": -25, "motor_right": -25, "castor": -25,
    "tyre_left": -45, "tyre_right": -45, "rim_left": -45, "rim_right": -45,
}


def build():
    solids = {}
    for name, fn, colour, desc in PARTS:
        solids[name] = fn()
    return solids


def export(solids, outdir):
    step_dir = os.path.join(outdir, "STEP")
    stl_dir = os.path.join(outdir, "STL")
    os.makedirs(step_dir, exist_ok=True)
    os.makedirs(stl_dir, exist_ok=True)

    asm = cq.Assembly(name="LightningMcQueen")
    for name, fn, colour, desc in PARTS:
        wp = solids[name]
        exporters.export(wp, os.path.join(step_dir, f"{name}.step"))
        exporters.export(wp, os.path.join(stl_dir, f"{name}.stl"))
        asm.add(wp, name=name, color=cq.Color(*_hex_rgb(colour), 1.0))
    asm.save(os.path.join(outdir, "lightning_mcqueen_assembly.step"))
    print(f"exported {len(PARTS)} parts + assembly -> {outdir}")


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    s = build()

    # Quick sanity report against the competition envelope.
    comp = None
    for name in s:
        comp = s[name].val() if comp is None else comp
    bb_all = cq.Compound.makeCompound([s[n].val() for n in s]).BoundingBox()
    print(f"overall envelope  L {bb_all.xlen:.1f} x W {bb_all.ylen:.1f} "
          f"x H {bb_all.zlen:.1f} mm")
    assert bb_all.xlen < MAX_FOOTPRINT and bb_all.ylen < MAX_FOOTPRINT, \
        "FAILS the 50 x 50 cm footprint rule"
    print("footprint rule: PASS")

    export(s, here)


def export_deck_dxf(outdir):
    """Flatten the deck to a 2D DXF profile for the laser cutter.

    This is the file that goes to the cutting house: outline, every M3
    clearance hole, the 22.5 mm E-Stop bore, the lightening holes and the
    two cable slots, all at 1:1 scale in millimetres.
    """
    plate = base_plate().translate((0, 0, -PLATE_UNDERSIDE_Z))
    section = plate.faces("<Z").wires().toPending()
    path = os.path.join(outdir, "deck_plate_laser_cut.dxf")
    exporters.exportDXF(cq.Workplane("XY").add(plate.faces("<Z").val()), path)
    return path
