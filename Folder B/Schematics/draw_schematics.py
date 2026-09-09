#!/usr/bin/env python3
"""
Lightning McQueen - circuit schematics
Team CO Coders | Robo Rumble 2026 | Robo Grand Prix

Hand-laid SVG schematics on an explicit coordinate grid, so nothing
overlaps and every annotation lands where it is meant to - in particular
the ON/OFF switch (Universal Design Constraint 3) and the Emergency Stop
(Universal Design Constraint 4), which the elimination rubric requires to
be explicitly drawn and annotated.

Generates, in this folder:
    01_power_safety_chain.svg / .png
    02_full_system.svg / .png

Run:  python3 draw_schematics.py
"""

import os
import subprocess

INK = "#1B1F24"
GREY = "#5B6470"
LIGHT = "#98A0AA"
RED = "#C4211D"
REDBG = "#FCEAE9"
BLUE = "#2C6FA8"
BLUEBG = "#E9F0F8"
GREEN = "#1F7A4D"
GREENBG = "#E7F5EE"
AMBER = "#9A6800"
AMBERBG = "#FFF6E0"
BG = "#FFFFFF"
FONT = ("ui-sans-serif, -apple-system, 'Segoe UI', Roboto, "
        "'Helvetica Neue', Arial, sans-serif")


class SVG:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts = []

    def add(self, s):
        self.parts.append(s)
        return self

    # ---- primitives -------------------------------------------------
    def line(self, x1, y1, x2, y2, c=INK, w=2.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                        f'stroke="{c}" stroke-width="{w}" '
                        f'stroke-linecap="round"{d}/>')

    def poly(self, pts, c=INK, w=2.0, fill="none", dash=None):
        p = " ".join(f"{x},{y}" for x, y in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return self.add(f'<polyline points="{p}" fill="{fill}" stroke="{c}" '
                        f'stroke-width="{w}" stroke-linejoin="round" '
                        f'stroke-linecap="round"{d}/>')

    def rect(self, x, y, w, h, c=INK, sw=2.0, fill="none", r=6):
        return self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                        f'rx="{r}" fill="{fill}" stroke="{c}" '
                        f'stroke-width="{sw}"/>')

    def circle(self, cx, cy, r, c=INK, sw=2.0, fill="none"):
        return self.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
                        f'stroke="{c}" stroke-width="{sw}"/>')

    def dot(self, x, y, r=4.5, c=INK):
        return self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"/>')

    def text(self, x, y, s, size=13, c=INK, anchor="start", weight="400",
             spacing=1.35):
        out = [f'<text x="{x}" y="{y}" font-family="{FONT}" '
               f'font-size="{size}" fill="{c}" text-anchor="{anchor}" '
               f'font-weight="{weight}">']
        for i, ln in enumerate(s.split("\n")):
            dy = 0 if i == 0 else size * spacing
            ln = (ln.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;"))
            out.append(f'<tspan x="{x}" dy="{dy}">{ln}</tspan>')
        out.append("</text>")
        return self.add("".join(out))

    def callout(self, x, y, w, title, body, c, bg):
        pad = 15
        lines = body.split("\n")
        h = pad * 2 + 26 + len(lines) * 18
        self.rect(x, y, w, h, c=c, sw=2.0, fill=bg, r=9)
        self.text(x + pad, y + pad + 15, title, size=13.5, c=c, weight="700")
        self.text(x + pad, y + pad + 41, body, size=11.5, c=c, spacing=1.56)
        return h

    # ---- electrical symbols -----------------------------------------
    def battery(self, x, y, label=""):
        self.line(x - 34, y, x - 12, y)
        for dx, hh in ((-12, 16), (-4, 8), (4, 16), (12, 8)):
            self.line(x + dx, y - hh, x + dx, y + hh, w=2.6)
        self.line(x + 12, y, x + 34, y)
        if label:
            self.text(x, y - 56, label, size=11, anchor="middle")

    def fuse(self, x, y, label=""):
        self.line(x - 36, y, x - 24, y)
        self.rect(x - 24, y - 11, 48, 22, r=4)
        self.poly([(x - 24, y), (x - 13, y - 7), (x, y + 7), (x + 13, y - 7),
                   (x + 24, y)], w=1.8)
        self.line(x + 24, y, x + 36, y)
        if label:
            self.text(x, y + 34, label, size=11, anchor="middle")

    def estop(self, x, y):
        """Normally-closed latching mushroom pushbutton."""
        self.line(x - 44, y, x - 17, y, c=RED, w=2.8)
        self.circle(x - 17, y, 4.5, c=RED, sw=2.4, fill=BG)
        self.circle(x + 17, y, 4.5, c=RED, sw=2.4, fill=BG)
        self.line(x - 17, y - 4.5, x + 17, y - 4.5, c=RED, w=2.8)
        self.line(x + 17, y, x + 44, y, c=RED, w=2.8)
        self.line(x, y - 4.5, x, y - 28, c=RED, w=2.2, dash="5,4")
        self.add(f'<rect x="{x-24}" y="{y-44}" width="48" height="16" '
                 f'rx="8" fill="{RED}"/>')
        self.text(x, y - 56, "SW1   E-STOP", size=15, c=RED, anchor="middle",
                  weight="700")
        self.text(x, y + 34, "normally closed · latching", size=10.5, c=RED,
                  anchor="middle")

    def spst(self, x, y):
        self.line(x - 42, y, x - 17, y, c=BLUE, w=2.8)
        self.circle(x - 17, y, 4.5, c=BLUE, sw=2.4, fill=BG)
        self.circle(x + 17, y, 4.5, c=BLUE, sw=2.4, fill=BG)
        self.line(x - 14, y - 2, x + 16, y - 18, c=BLUE, w=2.8)
        self.line(x + 17, y, x + 42, y, c=BLUE, w=2.8)
        self.text(x, y - 36, "SW2   ON/OFF", size=15, c=BLUE, anchor="middle",
                  weight="700")
        self.text(x, y + 34, "SPST rocker", size=10.5, c=BLUE, anchor="middle")

    def button(self, x, y, label=""):
        """Momentary normally-open pushbutton, vertical."""
        self.line(x, y - 30, x, y - 12)
        self.circle(x, y - 12, 4, sw=2.0, fill=BG)
        self.circle(x, y + 12, 4, sw=2.0, fill=BG)
        self.line(x - 15, y - 7, x + 15, y - 7, w=2.4)
        self.line(x, y - 7, x, y - 20, w=2.0)
        self.line(x, y + 12, x, y + 30)
        if label:
            self.text(x + 22, y - 6, label, size=11)

    def resistor(self, x, y, label=""):
        self.line(x, y - 30, x, y - 20)
        self.rect(x - 9, y - 20, 18, 40, r=3)
        self.line(x, y + 20, x, y + 30)
        if label:
            self.text(x + 17, y + 4, label, size=11)

    def led(self, x, y, label="", c=INK):
        self.line(x, y - 30, x, y - 13)
        self.add(f'<polygon points="{x-13},{y-13} {x+13},{y-13} {x},{y+8}" '
                 f'fill="none" stroke="{c}" stroke-width="2"/>')
        self.line(x - 14, y + 8, x + 14, y + 8, c=c, w=2.4)
        self.line(x, y + 8, x, y + 30, c=c)
        for dx, dy in ((16, -12), (21, -4)):
            self.poly([(x + dx, y + dy), (x + dx + 12, y + dy - 12)], c=c,
                      w=1.6)
            self.poly([(x + dx + 12, y + dy - 12), (x + dx + 6, y + dy - 10),
                       (x + dx + 10, y + dy - 6)], c=c, w=1.4)
        if label:
            self.text(x + 40, y + 4, label, size=11, c=c)

    def motor(self, x, y, r=28, label=""):
        self.circle(x, y, r, sw=2.2, fill=BG)
        self.text(x, y + 7, "M", size=19, anchor="middle", weight="700")
        if label:
            self.text(x, y + r + 22, label, size=11, anchor="middle")

    def speaker(self, x, y, label=""):
        self.line(x, y - 30, x, y - 14)
        self.rect(x - 8, y - 14, 16, 28, r=2)
        self.add(f'<polygon points="{x+8},{y-14} {x+26},{y-26} '
                 f'{x+26},{y+26} {x+8},{y+14}" fill="none" stroke="{INK}" '
                 f'stroke-width="2"/>')
        self.line(x, y + 14, x, y + 30)
        if label:
            self.text(x + 36, y + 4, label, size=11)

    def ground(self, x, y):
        self.line(x, y, x, y + 14)
        for i, w in enumerate((24, 15, 7)):
            self.line(x - w / 2, y + 14 + i * 6, x + w / 2, y + 14 + i * 6,
                      w=2.4)

    def chip(self, x, y, w, h, title, sub="", left=(), right=(), bottom=(),
             c=INK, fill="#FBFCFD"):
        """Block with named pins. Offsets are measured from the block's
        top edge (or left edge, for bottom pins). Returns pin -> (x, y)."""
        self.rect(x, y, w, h, c=c, sw=2.2, fill=fill, r=9)
        self.text(x + w / 2, y + 28, title, size=15, anchor="middle",
                  weight="700", c=c)
        if sub:
            self.text(x + w / 2, y + 48, sub, size=10.5, c=GREY,
                      anchor="middle")
        pins = {}
        for off, name in left:
            py = y + off
            self.line(x - 22, py, x, py)
            self.text(x + 10, py + 4, name, size=11, c=INK)
            pins[name] = (x - 22, py)
        for off, name in right:
            py = y + off
            self.line(x + w, py, x + w + 22, py)
            self.text(x + w - 10, py + 4, name, size=11, c=INK, anchor="end")
            pins[name] = (x + w + 22, py)
        for off, name in bottom:
            px = x + off
            self.line(px, y + h, px, y + h + 22)
            self.text(px, y + h - 10, name, size=11, c=INK, anchor="middle")
            pins[name] = (px, y + h + 22)
        return pins

    def save(self, path):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
                f'height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<rect width="{self.w}" height="{self.h}" fill="{BG}"/>')
        with open(path, "w") as f:
            f.write(head + "".join(self.parts) + "</svg>")


def header(s, title, sub):
    s.text(56, 54, title, size=26, c=INK, weight="700")
    s.text(56, 82, sub, size=13, c=GREY)
    s.line(56, 102, s.w - 56, 102, c="#DDE1E6", w=1.5)
    s.text(s.w - 56, 50, "Team CO Coders  ·  Lightning McQueen", size=12.5,
           c=LIGHT, anchor="end")
    s.text(s.w - 56, 70, "Robo Rumble 2026  ·  Robo Grand Prix", size=11,
           c=LIGHT, anchor="end")


# =====================================================================
# 1. POWER AND SAFETY CHAIN
# =====================================================================
def power_safety_chain(path):
    s = SVG(1600, 1000)
    header(s, "Power and safety chain",
           "The mandatory ON/OFF switch and Emergency Stop, and why they sit "
           "where they do in the circuit")

    Y = 280
    s.battery(170, Y, "BT1 · BT2\n2 × 9 V PP3\n9 V nominal, ~1.2 Ah")
    s.line(204, Y, 254, Y)
    s.fuse(290, Y, "F1\n2 A resettable polyfuse")
    s.line(326, Y, 386, Y)

    s.estop(430, Y)
    s.line(474, Y, 548, Y)
    s.spst(590, Y)
    s.line(632, Y, 740, Y)

    s.dot(740, Y)
    s.text(740, Y - 26, "V-MOTOR RAIL   switched +9 V", size=13,
           anchor="middle", weight="600")

    # power-on indicator
    s.line(740, Y, 740, Y + 62)
    s.line(740, Y + 62, 690, Y + 62)
    s.resistor(690, Y + 92, "R1   1 kΩ")
    s.led(690, Y + 162, "D1   POWER ON", c=AMBER)
    s.line(690, Y + 192, 690, Y + 224)
    s.ground(690, Y + 224)

    s.line(740, Y, 870, Y)

    pins = s.chip(870, Y - 60, 250, 260, "U1   L298N",
                  "dual H-bridge with\non-board 78M05 regulator",
                  left=[(60, "+12V"), (225, "GND")],
                  right=[(60, "+5V"), (140, "OUT 1/2"), (195, "OUT 3/4")],
                  c=AMBER, fill=AMBERBG)

    s.poly([pins["+5V"], (1250, pins["+5V"][1])], c=GREEN, w=2.2)
    s.dot(1250, pins["+5V"][1], c=GREEN)
    s.text(1264, pins["+5V"][1] - 14,
           "+5 V LOGIC RAIL\n→ Arduino Uno 5V pin\n→ TCRT5000 array Vcc",
           size=11.5, c=GREEN)

    s.line(*pins["OUT 1/2"], 1210, pins["OUT 1/2"][1])
    s.line(*pins["OUT 3/4"], 1210, pins["OUT 3/4"][1])
    s.rect(1210, pins["OUT 1/2"][1] - 36, 250, 128, r=9, fill="#FBFCFD")
    s.text(1335, pins["OUT 1/2"][1] + 6, "M1  +  M2", size=16,
           anchor="middle", weight="700")
    s.text(1335, pins["OUT 1/2"][1] + 32,
           "2 × TT gear motor 1:48\n65 mm wheels · 170 mm track",
           size=11, c=GREY, anchor="middle")

    GY = Y + 300
    s.poly([pins["GND"], (824, pins["GND"][1]), (824, GY), (136, GY),
            (136, Y)], w=2.0)
    s.ground(300, GY)
    s.text(346, GY + 5, "battery negative — single star ground", size=11,
           c=GREY)

    # ---- callouts ----------------------------------------------------
    s.line(430, Y + 46, 430, 690, c=RED, w=1.4, dash="6,5")
    s.callout(120, 700, 520,
              "SW1 · E-STOP  —  Universal Design Constraint 4",
              "22 mm latching mushroom head, normally closed, on a 48 mm mast at the\n"
              "rear centreline of the deck. Nothing overhangs it.\n\n"
              "It is the FIRST device in the battery positive line, upstream of SW2 and\n"
              "of U1. Striking it removes power from the motors, the H-bridge, the 5 V\n"
              "regulator, the MCU and the sensor array in the same instant. It latches\n"
              "down, so power cannot restore itself until an operator twists the head\n"
              "back out. The contact is mechanically in the battery line, so no firmware\n"
              "path can defeat it.",
              RED, REDBG)

    s.poly([(590, Y + 46), (590, 660), (800, 660), (800, 700)], c=BLUE,
           w=1.4, dash="6,5")
    s.callout(680, 700, 440,
              "SW2 · ON/OFF  —  Universal Design Constraint 3",
              "SPST rocker at the rear-left corner of the deck, clear of the\n"
              "wheels and of the sensor boom.\n\n"
              "Operable with the car sitting on the grid — no lifting, no\n"
              "tilting, no reaching over a wheel that is about to spin.\n"
              "It is the normal way to power the car up and down. SW1 is\n"
              "reserved for stopping a run that has gone wrong.",
              BLUE, BLUEBG)

    s.callout(1150, 700, 400,
              "Downstream of both devices",
              "U1 derives the +5 V logic rail from the same switched\n"
              "line, so nothing keeps the MCU alive after a stop. The\n"
              "largest capacitor downstream is 100 µF on the L298N\n"
              "rail — far too little stored energy to turn a loaded\n"
              "TT gearbox even once.",
              GREY, "#F4F5F7")

    s.save(path)


# =====================================================================
# 2. FULL SYSTEM
# =====================================================================
def full_system(path):
    s = SVG(1760, 1620)
    header(s, "Full system schematic",
           "Arduino Uno R3  ·  L298N dual H-bridge  ·  5-channel TCRT5000 "
           "array  ·  2 × TT gear motor  ·  2 × 9 V PP3")

    arr = s.chip(90, 200, 210, 340, "U3   TCRT5000 ×5",
                 "reflective array\n20 mm pitch · 12 mm ride height",
                 left=[(95, "Vcc"), (310, "GND")],
                 right=[(130, "OUT1"), (170, "OUT2"), (210, "OUT3"),
                        (250, "OUT4"), (290, "OUT5")],
                 c=GREEN, fill=GREENBG)

    uno = s.chip(620, 170, 250, 450, "U2   Arduino Uno R3",
                 "ATmega328P · 16 MHz",
                 left=[(130, "A0"), (170, "A1"), (210, "A2"), (250, "A3"),
                       (290, "A4"), (365, "5V"), (410, "GND")],
                 right=[(130, "D2"), (170, "D4"), (210, "D9~"), (250, "D7"),
                        (290, "D8"), (330, "D10~")],
                 bottom=[(70, "D12"), (125, "D13"), (180, "D3")],
                 c=BLUE, fill=BLUEBG)

    ic = s.chip(1160, 170, 230, 450, "U1   L298N",
                "dual H-bridge · 2 A / channel",
                left=[(130, "IN1"), (170, "IN2"), (210, "ENA"), (250, "IN3"),
                      (290, "IN4"), (330, "ENB"), (390, "+12V"),
                      (425, "GND")],
                right=[(120, "OUT1"), (160, "OUT2"), (240, "OUT3"),
                       (280, "OUT4"), (370, "+5V")],
                c=AMBER, fill=AMBERBG)

    for i, (sp, ap) in enumerate((("OUT1", "A0"), ("OUT2", "A1"),
                                  ("OUT3", "A2"), ("OUT4", "A3"),
                                  ("OUT5", "A4"))):
        x0, y0 = arr[sp]
        x1, y1 = uno[ap]
        mid = 370 + i * 18
        s.poly([(x0, y0), (mid, y0), (mid, y1), (x1, y1)], c=GREEN, w=1.8)
    s.text(360, 178, "5 analog channels → A0 … A4", size=11.5, c=GREEN,
           weight="600")

    for i, (up, ip) in enumerate((("D2", "IN1"), ("D4", "IN2"),
                                  ("D9~", "ENA"), ("D7", "IN3"),
                                  ("D8", "IN4"), ("D10~", "ENB"))):
        x0, y0 = uno[up]
        x1, y1 = ic[ip]
        mid = 930 + i * 18
        s.poly([(x0, y0), (mid, y0), (mid, y1), (x1, y1)], c=BLUE, w=1.8)
    s.text(925, 150, "2 direction pins + 1 PWM enable per motor —\n"
                     "ENA/ENB on Timer1 (D9, D10), away from millis()",
           size=11.5, c=BLUE)

    # motors
    for a, b, cy_lbl in (("OUT1", "OUT2", "M1   left  ·  TT 1:48"),
                         ("OUT3", "OUT4", "M2   right  ·  TT 1:48")):
        ya, yb = ic[a][1], ic[b][1]
        cy = (ya + yb) / 2
        s.poly([(ic[a][0], ya), (1530, ya), (1530, cy - 20)], w=2.0)
        s.poly([(ic[b][0], yb), (1530, yb), (1530, cy + 20)], w=2.0)
        s.line(1530, cy - 20, 1560, cy - 20)
        s.line(1530, cy + 20, 1560, cy + 20)
        s.motor(1600, cy, 28, cy_lbl)
        s.line(1560, cy - 20, 1572, cy - 20)
        s.line(1560, cy + 20, 1572, cy + 20)

    # +5 V logic rail across the top
    RY = 132
    x5, y5 = ic["+5V"]
    s.poly([(x5, y5), (1690, y5), (1690, RY), (340, RY)], c=GREEN, w=2.2)
    s.dot(340, RY, c=GREEN)
    s.poly([(340, RY), (340, uno["5V"][1]), uno["5V"]], c=GREEN, w=2.2)
    s.poly([(340, RY), (58, RY), (58, arr["Vcc"][1]), arr["Vcc"]], c=GREEN,
           w=2.2)
    s.text(760, RY - 14, "+5 V LOGIC RAIL   (U1 on-board 78M05)", size=12.5,
           c=GREEN, weight="600")

    # indicators under the Uno, fanned out so nothing collides
    bx, by = uno["D12"]
    s.poly([(bx, by), (bx, by + 40), (500, by + 40), (500, by + 70)], w=2.0)
    s.button(500, by + 100)
    s.text(500, by + 150, "SW3   ARM\nmomentary, INPUT_PULLUP\n"
                          "the only human input before a run",
           size=11, anchor="middle")
    s.line(500, by + 130, 500, by + 220)
    s.ground(500, by + 220)

    lx, ly = uno["D13"]
    s.poly([(lx, ly), (lx, ly + 26), (700, ly + 26), (700, ly + 56)], w=2.0)
    s.resistor(700, ly + 86, "R2   220 Ω")
    s.led(700, ly + 156, "D2   status", c=AMBER)
    s.line(700, ly + 186, 700, ly + 216)
    s.ground(700, ly + 216)

    sx, sy = uno["D3"]
    s.poly([(sx, sy), (sx, sy + 40), (880, sy + 40), (880, sy + 70)], w=2.0)
    s.speaker(880, sy + 100, "LS1   piezo")
    s.line(880, sy + 130, 880, sy + 216)
    s.ground(880, sy + 216)

    # power chain along the bottom
    PY = 1080
    s.battery(190, PY, "BT1 · BT2\n2 × 9 V PP3")
    s.line(224, PY, 268, PY)
    s.fuse(304, PY, "F1   2 A polyfuse")
    s.line(340, PY, 396, PY)
    s.estop(440, PY)
    s.line(484, PY, 552, PY)
    s.spst(594, PY)
    s.line(636, PY, 1110, PY)
    s.poly([(1110, PY), (1110, ic["+12V"][1]), ic["+12V"]], w=2.4)
    s.text(1120, PY - 16, "switched +9 V → U1 +12V terminal", size=11.5,
           c=GREY)

    GY = 1200
    s.poly([(156, PY), (156, GY), (1290, GY)], w=2.0)
    s.ground(700, GY)
    for pin, back in ((arr["GND"], 36), (uno["GND"], 240), (ic["GND"], 36)):
        s.poly([pin, (pin[0] - back, pin[1]), (pin[0] - back, GY)], w=1.8)
        s.dot(pin[0] - back, GY)
    s.text(740, GY - 14, "star ground — every return ties at battery negative",
           size=11, c=GREY)

    s.callout(60, 1290, 1640,
              "MANDATORY SAFETY DEVICES  —  Universal Design Constraints 3 and 4",
              "SW1 (E-Stop, 22 mm latching mushroom, normally closed) and SW2 (ON/OFF rocker) are wired in\n"
              "series in the battery positive line, ahead of U1. U1's on-board 78M05 derives the +5 V logic\n"
              "rail from that same switched line, so opening either device de-energises the MCU, the sensor\n"
              "array and the motors together — no path keeps logic alive after a stop.\n\n"
              "SW1 latches: once struck, power cannot restore itself until an operator twists the head back out.\n\n"
              "Robo Grand Prix compliance: there is no radio, no Wi-Fi and no Bluetooth anywhere on this\n"
              "schematic. SW3 (ARM) is pressed before the car is released; after that the only human input\n"
              "available is SW1.",
              RED, REDBG)

    s.save(path)


def rasterise(svg_path, png_path, w, h, scale=2):
    html = svg_path + ".tmp.html"
    with open(svg_path) as f:
        body = f.read()
    with open(html, "w") as f:
        f.write("<html><body style='margin:0;background:#fff'>" + body
                + "</body></html>")
    try:
        subprocess.run(
            ["/opt/pw-browsers/chromium", "--headless", "--no-sandbox",
             "--disable-gpu", "--hide-scrollbars",
             f"--screenshot={png_path}", f"--window-size={w},{h}",
             f"--force-device-scale-factor={scale}", f"file://{html}"],
            check=True, capture_output=True, timeout=180)
    finally:
        if os.path.exists(html):
            os.remove(html)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    for fn, stem, w, h in ((power_safety_chain, "01_power_safety_chain",
                            1600, 1000),
                           (full_system, "02_full_system", 1760, 1620)):
        svg = os.path.join(here, stem + ".svg")
        fn(svg)
        try:
            rasterise(svg, os.path.join(here, stem + ".png"), w, h)
        except Exception as e:
            print("  rasterise skipped:", e)
        print("wrote", stem)
