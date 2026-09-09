# Folder B — Designs

The physical and electronic blueprints for Lightning McQueen.

| Subfolder | Start here | Contents |
|---|---|---|
| [`Mechanical Design/`](Mechanical%20Design) | [`MECHANICAL_DESIGN.md`](Mechanical%20Design/MECHANICAL_DESIGN.md) | Fabrication method, fastening scheme, mass budget, parametric CAD (STEP/STL/DXF) and five shaded renders |
| [`Electronic Design/`](Electronic%20Design) | [`ELECTRONIC_DESIGN.md`](Electronic%20Design/ELECTRONIC_DESIGN.md) | Justification for every sensor, driver and control unit, with the alternatives we rejected and why |
| [`Schematics/`](Schematics) | [`SCHEMATICS.md`](Schematics/SCHEMATICS.md) | Full system schematic plus a dedicated power-and-safety-chain drawing with the ON/OFF switch and E-Stop annotated |
| [`Simulation/`](Simulation) | [`SIMULATION.md`](Simulation/SIMULATION.md) | What we tested in Webots, what the sweeps told us, which constants came out of them, and what simulation could not tell us |

## Safety compliance at a glance

| Constraint | Where it is drawn | Where it is rendered |
|---|---|---|
| **3 — accessible ON/OFF switch** | [`Schematics/01_power_safety_chain.svg`](Schematics/01_power_safety_chain.svg) — SW2, annotated | [`Mechanical Design/renders/04_safety_annotated.png`](Mechanical%20Design/renders/04_safety_annotated.png) |
| **4 — Emergency Stop** | [`Schematics/01_power_safety_chain.svg`](Schematics/01_power_safety_chain.svg) — SW1, annotated, first in the battery positive line | [`Mechanical Design/renders/04_safety_annotated.png`](Mechanical%20Design/renders/04_safety_annotated.png) |

## Everything here is reproducible

```bash
pip install cadquery schemdraw matplotlib numpy

python3 "Mechanical Design/CAD/lightning_mcqueen_cad.py"   # STEP, STL, DXF
python3 "Mechanical Design/CAD/render_views.py"            # the five renders
python3 "Schematics/draw_schematics.py"                    # both schematics
```

The CAD build script asserts the 50 × 50 cm footprint rule on every run and
fails loudly if a parameter change ever breaks it.
