# Lightning McQueen 

**Team Name:** CO Coders
**Solution Name:** Lightning McQueen
**Category:** Robo Grand Prix (autonomous racing)
**Event:** Robo Rumble 2026 — Elimination Round

---

## What we are building

Lightning McQueen is an **autonomous line-following racer**. It reads the track
with a five-channel infrared reflective array, works out how far it is off the
line, and steers by commanding a **path curvature** rather than a raw motor
difference. The speed it runs at is then chosen from that curvature — flat out on
the straights, backed off exactly as much as the corner requires and no more.

There is no radio, no Wi-Fi and no Bluetooth anywhere on this vehicle. The only
human input is an ARM button pressed before the car is released, and the
emergency stop. That is a deliberate design decision, not an omission: Robo
Grand Prix requires full autonomy, and any human intervention forfeits the run.

**The strategy in one line:** most line followers lose time because they brake
for corners they have already entered. We compute the curvature the controller
is *about* to demand, and set the speed from that — so the car is already at the
right speed when the corner arrives.

---

## How we are building it

| Phase | Tool | Status |
|---|---|---|
| Control-law development | **Webots** (e-puck differential-drive model) | Complete — see `Folder B/Simulation` |
| Circuit design and MCU logic | **Wokwi** | Complete — see `Folder B/Schematics` |
| Mechanical design | **CadQuery** parametric CAD (OpenCASCADE kernel) | Complete — see `Folder B/Mechanical Design` |
| Physical build | Laser-cut acrylic deck, bolted assembly | Documented, not yet assembled |

Everything in this repository is reproducible. The CAD is a Python script, the
schematics are a Python script, the flowcharts are Mermaid source. Run them and
you get the same files back.

---

## Competition compliance

| Universal Design Constraint | How Lightning McQueen meets it |
|---|---|
| **1. Footprint ≤ 50 × 50 cm** | Overall envelope **300 × 211 × 107 mm**. The CAD build script asserts this on every run and fails loudly if a change ever breaks it. |
| **2. Mass < 5 kg** | Estimated **0.86 kg** fully assembled. Full mass budget in `Folder C/Holistic_Build_Document.md`. |
| **3. Accessible ON/OFF switch** | **SW2**, an SPST rocker at the rear-left corner of the deck, clear of the wheels and the sensor boom. Drawn and annotated in `Folder B/Schematics/01_power_safety_chain.svg`. |
| **4. Emergency Stop** | **SW1**, a 22 mm latching mushroom head on a 48 mm mast at the rear centreline. Wired **first** in the battery positive line, upstream of SW2 and of the H-bridge. Drawn and annotated in the same schematic and rendered in `Folder B/Mechanical Design/renders/04_safety_annotated.png`. |
| **Robo Grand Prix: fully autonomous** | No radio, no Wi-Fi, no Bluetooth, no serial command path. Serial is output-only telemetry. |

The 20 × 30 cm breadboard-on-plate layout from our original concept is carried
through: the 830-point breadboard sits on a 300 × 200 mm laser-cut acrylic deck
that also carries the Arduino, the H-bridge and the battery pack. Light materials
keep mass off the wheels; the batteries are the heaviest single item, which is
why we run **two 9 V PP3 cells** rather than twelve 1.5 V cells.

---

## Directory map

### [`Folder A — Source Code`](./Folder%20A)

Everything needed to run the build, plus the documentation of *how* the software
is put together.

| Path | Contents |
|---|---|
| `firmware/lightning_mcqueen/` | The race firmware. `lightning_mcqueen.ino` is the 200 Hz control superloop and five-state supervisor; `config.h` holds every tunable, each traceable to a datasheet, the CAD model, or a simulation sweep. |
| `firmware/calibration/` | A separate sketch that measures the sensor thresholds, the motor trim and the PWM deadband on the actual track, and prints the numbers to paste into `config.h`. |
| `simulation/` | The Webots C++ controller the control law was developed in. |
| `flowcharts/` | Five diagrams — system architecture, the control loop, the state machine, line-loss recovery, and the power/safety chain — as Mermaid source and rendered PNG. |
| `PROGRAMMING.md` | The programming methods, frameworks and architecture, with the flowcharts inline and the control law derived from first principles. |

### [`Folder B — Designs`](./Folder%20B)

The physical and electronic blueprints.

| Path | Contents |
|---|---|
| `Mechanical Design/` | `MECHANICAL_DESIGN.md` (fabrication method, fastening, mass budget), `CAD/` (the parametric model, STEP and STL for every part, a laser-cut DXF of the deck), `renders/` (five shaded views including the annotated safety view). |
| `Electronic Design/` | `ELECTRONIC_DESIGN.md` — why each sensor, driver and controller was chosen, with the alternatives we rejected and the reason. |
| `Schematics/` | `SCHEMATICS.md`, the full system schematic, and a dedicated power-and-safety-chain drawing with the ON/OFF switch and E-Stop explicitly annotated. Both are generated by `draw_schematics.py`. |
| `Simulation/` | `SIMULATION.md` — what we tested in Webots, what the sweeps told us, and which firmware constants came out of them. |

### [`Folder C — Documentation`](./Folder%20C)

| Path | Contents |
|---|---|
| `Pitch_Deck.pdf` | 7 slides: introduction, solution, technical approach, cost, team. |
| `Bill_of_Materials.xlsx` | Every component with quantity, unit cost, supplier, stock code and buy link. **Total cost is highlighted in red.** |
| `Holistic_Build_Document.md` | The full written report: constraints, solution, BOM summary, and the three required technical sub-sections (mechanical, electronic, programming). |
| `FQA_Attendance_Log.md` | Facilitator Q&A attendance logbook. |
| `FQA_Proof/` | Attendance screenshots referenced by the logbook. |

---

## Reproducing the design files

```bash
pip install cadquery schemdraw matplotlib numpy

# CAD: STEP + STL for every part, plus the laser-cut DXF
python3 "Folder B/Mechanical Design/CAD/lightning_mcqueen_cad.py"

# Renders: five shaded views
python3 "Folder B/Mechanical Design/CAD/render_views.py"

# Schematics: SVG + PNG
python3 "Folder B/Schematics/draw_schematics.py"
```

---

## Team

| Member | Role |
|---|---|
| *(see `Folder C/Pitch_Deck.pdf`, Team Slide)* | |

---

## Credits and attribution

- The Webots control law began from the standard e-puck line-following example
  distributed with Webots, and was rewritten around curvature control and a
  speed schedule. The original example's structure is acknowledged.
- The TCRT5000 sensing approach follows the device datasheet's recommended
  8–15 mm standoff.
- Everything else — the firmware, the CAD, the schematics and the documentation
  in this repository — is our own work.
