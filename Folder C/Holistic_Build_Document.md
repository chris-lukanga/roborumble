# Lightning McQueen — Holistic Build Document

**Team Name:** CO Coders
**Solution Name:** Lightning McQueen
**Category:** Robo Grand Prix (autonomous racing)
**Event:** Robo Rumble 2026 — Elimination Round

---

## 1. Context and competition constraints

Robo Grand Prix is autonomous racing. There is no problem statement to validate,
because the problem is given: get a robot around a line-marked circuit, on its
own, faster than everyone else. What there *is* to address is a set of hard
constraints, and a build either satisfies them or it does not.

| Constraint | Requirement | How Lightning McQueen addresses it |
|---|---|---|
| **Footprint** | ≤ 500 × 500 mm | **300 × 211 × 107 mm.** The CAD build script asserts this on every run and fails loudly if a parameter change ever breaks it. |
| **Mass** | strictly below 5 kg | **0.86 kg** — 17 % of the allowance. Full budget in §6.1. |
| **ON/OFF switch** | mandatory, easily accessible | **SW2**, SPST rocker at the rear-left corner of the deck. Operable with the car on the grid. |
| **Emergency Stop** | mandatory, cuts power instantly, clearly annotated | **SW1**, 22 mm latching mushroom head on a 48 mm mast at the rear centreline, wired **first** in the battery positive line. |
| **Full autonomy** | no remote control, no Wi-Fi, no human contact during the run | No radio, no Wi-Fi, no Bluetooth, no serial command path anywhere on the vehicle. |

### The constraints as an advantage

The mass and size limits are generous for a line follower, and we treated the
headroom as something to spend deliberately rather than something to ignore.
Every gram not on the car is a gram the same TT gearboxes do not have to
accelerate and the same tyres do not have to hold through a corner. That is why
the deck is 3 mm acrylic rather than 5 mm, why the fasteners are nylon rather
than steel, and — the decision our concept notes committed to first — why the
car runs on **two 9 V PP3 cells rather than twelve 1.5 V AA cells**: 92 g against
276 g, on a car whose entire assembled mass is 855 g.

The honest cost of that choice is capacity. Two PP3 cells give roughly 1.2 Ah at
9 V, which is comfortable for a heat but not for an afternoon of testing, and the
terminal voltage sags under a stall. We mitigate by swapping packs between heats
(hook-and-loop straps, ten seconds) and by bench-testing from a supply rather
than from cells.

---

## 2. Solution overview

We are building an autonomous line-following racer that:

- reads the track with a **five-channel TCRT5000 reflective array** at 20 mm
  pitch, 12 mm above the floor, mounted 138 mm ahead of the drive axle;
- computes a **cross-track error in metres** from a weighted centroid of those
  five analog channels;
- runs a **PID whose output is a path curvature** (1/m), not a motor difference;
- chooses its **speed from that curvature**, before the curvature is applied, so
  the car is already at corner speed when the corner arrives;
- drives two TT gear motors through an L298N H-bridge from an Arduino Uno at
  200 Hz;
- and stops safely and stays stopped when it loses the line.

**The strategy in one line.** Most line followers lose time because they brake
for corners they have already entered. Ours sheds speed during the 138 mm of
travel between the sensor bar detecting the corner and the axle reaching it.

---

## 3. BOM summary

Core components only. The complete breakdown — quantities, unit costs,
suppliers, stock codes and buy links — is in
[**`Bill_of_Materials.xlsx`**](./Bill_of_Materials.xlsx), where the total is
highlighted in red.

| Component | Qty | Function |
|---|---:|---|
| [Arduino Uno R3](./Bill_of_Materials.xlsx) | 1 | Control — 5 ADC channels, Timer1 PWM |
| [L298N dual H-bridge module](./Bill_of_Materials.xlsx) | 1 | Motor drive + 5 V logic regulation |
| [TCRT5000 5-channel array](https://www.robotics.org.za/TRCT5000-4C) | 1 | Line sensing |
| [TT gear motor 1:48 + 65 mm wheel](./Bill_of_Materials.xlsx) | 2 | Drive |
| [9 V PP3 cell + holder](./Bill_of_Materials.xlsx) | 2 | Power |
| [22 mm latching E-Stop, NC](./Bill_of_Materials.xlsx) | 1 | **Constraint 4** |
| [SPST rocker switch](./Bill_of_Materials.xlsx) | 1 | **Constraint 3** |
| [830-point breadboard](./Bill_of_Materials.xlsx) | 1 | Interconnect |
| [3 mm acrylic deck, laser cut](./Bill_of_Materials.xlsx) | 1 | Chassis |

| | |
|---|---|
| Components subtotal | **R 1 676.00** |
| Contingency (10 %) | R 167.60 |
| **Total cost of implementation** | **R 1 843.60** |

Prices are indicative South African retail. The yellow cells in the spreadsheet
are the ones to confirm against each supplier's live listing before submission.

---

## 4. Mechanical design

*Full detail: [`../Folder B/Mechanical Design/MECHANICAL_DESIGN.md`](../Folder%20B/Mechanical%20Design/MECHANICAL_DESIGN.md)*

![Assembled chassis](../Folder%20B/Mechanical%20Design/renders/01_isometric.png)

### 4.1 Fabrication

**The deck is laser cut, not drilled.**
`Folder B/Mechanical Design/CAD/deck_plate_laser_cut.dxf` is a 1:1 flat profile
containing the outline, all 34 M3 clearance holes, the 22.5 mm E-Stop bore, the
lightening holes and the two cable slots. It goes to the cutter as-is. Nothing
is marked out by hand, because hand-drilled acrylic chips and hand-marked
patterns do not repeat.

We chose a laser-cut flat deck over a 3D-printed monocoque deliberately. A
printed 300 mm chassis warps, takes eight hours, and cannot be re-cut in an
afternoon when a mounting hole turns out to be 4 mm out. A flat plate takes
ninety seconds on the machine and is dimensionally exact. In a competition where
the schedule is the real constraint, that beats the better-looking option.

3 mm rather than 5 mm: 3 mm cast acrylic spanning 300 mm deflects about 0.4 mm
at the nose under the assembled mass — well inside the ±2 mm the sensor ride
height tolerates. 5 mm would add 240 g for stiffness we do not need.

The E-Stop mast is the only 3D-printed part: 30 mm diameter × 48 mm, four
perimeters, 40 % infill, PLA.

### 4.2 Fastening

![Exploded assembly](../Folder%20B/Mechanical%20Design/renders/02_exploded.png)

**Every joint is bolted. Nothing is glued.** Adhesive joints in acrylic are
brittle, cannot be adjusted, and leave no way back when a sensor turns out to be
2 mm too low. Bolted joints come apart.

Motors bolt through the deck from below on two M3 per side. The castor bolts to
a 24 mm square M3 pattern at the tail. The sensor boom hangs on two M3 × 30 mm
**nylon** standoffs — nylon and not steel, because the standoffs sit directly
beside the IR emitters and a steel post reflects. Deck modules sit on 8 mm
standoffs. The battery pack is strapped with hook-and-loop so a flat pack is a
ten-second swap between heats.

Two adjustments are designed in on purpose: **sensor ride height** (change the
standoff length) and **weight distribution** (move the battery straps). Motor
position is deliberately fixed, because it sets the sensor lead that the speed
schedule depends on.

### 4.3 Views

![Orthographic views](../Folder%20B/Mechanical%20Design/renders/03_orthographic.png)

![Underside](../Folder%20B/Mechanical%20Design/renders/05_underside.png)

The model is parametric — a Python script using CadQuery on the OpenCASCADE
kernel. Changing `TRACK` or `WHEEL_D` and re-running regenerates every STEP,
every STL, the DXF and all five renders consistently.

---

## 5. Electronic design

*Full detail: [`../Folder B/Electronic Design/ELECTRONIC_DESIGN.md`](../Folder%20B/Electronic%20Design/ELECTRONIC_DESIGN.md)
and [`../Folder B/Schematics/SCHEMATICS.md`](../Folder%20B/Schematics/SCHEMATICS.md)*

### 5.1 The safety chain — Constraints 3 and 4

![Power and safety chain](../Folder%20B/Schematics/01_power_safety_chain.png)

```
BT1/BT2  →  F1  →  SW1 (E-STOP)  →  SW2 (ON/OFF)  →  U1 (L298N)  →  motors
2 × 9 V     2 A     latching NC       SPST rocker      +12V           M1, M2
                                                          ↓
                                                   78M05 → +5 V rail
                                                          ↓
                                              Arduino Uno · TCRT5000 array
```

**SW1 — Emergency Stop.** A 22 mm latching mushroom head, normally closed, on a
48 mm mast at the rear centreline. It is the tallest object on the car and
nothing overhangs it, so it can be struck from above or behind with an open palm
while the car is moving. It is the **first device in the battery positive line**,
upstream of SW2 and of the H-bridge.

Three properties make it a real emergency stop rather than a decorative one:

1. **Everything is downstream.** The L298N's on-board 78M05 derives the 5 V
   logic rail from the same switched line that feeds the motors, so opening SW1
   de-energises the motors, the H-bridge, the regulator, the MCU and the sensor
   array in the same instant.
2. **Firmware cannot defeat it.** The contact is mechanically in series with the
   battery. There is no software left running once it opens.
3. **Stored energy cannot move the car.** The largest capacitor downstream is
   100 µF on the 5 V rail, storing 1.25 mJ. Turning a loaded TT gearbox through
   one revolution needs on the order of a joule — roughly a thousand times more.

This is also why we deliberately do **not** run a separate logic battery. A
second supply would keep the MCU alive after the motor rail opened, which is
exactly what Constraint 4 is written to prevent.

**SW2 — ON/OFF.** An SPST rocker at the rear-left corner of the deck, clear of
the wheels and the sensor boom, operable with the car on the grid. Both devices
are at the rear because that is the end an operator approaches from; the E-Stop
is raised and on the centreline, the rocker is flush and in the corner, so they
are not confusable by feel.

![Safety hardware annotated](../Folder%20B/Mechanical%20Design/renders/04_safety_annotated.png)

### 5.2 Full system wiring

![Full system schematic](../Folder%20B/Schematics/02_full_system.png)

### 5.3 Component justification, in brief

**Arduino Uno R3.** Six ADC channels, three timers, a 104 µs ADC conversion. The
whole control pipeline measures ~760 µs against a 5 ms period — 15 % CPU. We
seriously considered an ESP32 and rejected it for one decisive reason: it
arrives with Wi-Fi and Bluetooth radios on the die, and Robo Grand Prix forbids
remote control. We would rather hand a judge a board that *physically cannot* be
commanded remotely than a board where the argument depends on firmware we claim
we did not write.

**L298N.** 2 A per channel against a ~1.2 A stall, with flyback diodes and the
5 V regulator already on the module — which removes a hand-wired subcircuit from
a breadboard, and a hand-wired flyback diode on a breadboard is exactly what goes
intermittent. Its honest downside is a ~1.9 V bridge drop, so the wheels do not
turn below about 16 % duty; `PWM_DEADBAND` in the firmware maps the controller's
output onto the usable duty range, and the calibration sketch measures the real
figure. A TB6612FNG would be the better part and is a drop-in swap if one is in
hand; the L298N was chosen on availability and cost.

**Five analog sensor channels, not three digital ones.** This is the most
consequential electronic decision on the car, and it came directly out of
simulation — see §7.

**Pin map detail that matters.** The motor PWM pins are on **Timer1 (D9, D10)**,
not Timer0 (D5, D6). Timer0 drives `millis()`/`micros()`, which the fixed-rate
scheduler depends on. Sharing it with motor PWM is the kind of coupling that
produces a bug you only see at one duty cycle, three days before the event.

**Grounding.** Single star point at the L298N GND pad. The sensor array, the Uno
and the H-bridge each return there independently rather than daisy-chaining, so
motor current never shares a conductor with the analog sensor return.

---

## 6. Programming and framework design

*Full detail: [`../Folder A/PROGRAMMING.md`](../Folder%20A/PROGRAMMING.md)*

### 6.1 Architecture

A non-blocking fixed-rate **200 Hz superloop** with a four-stage pipeline, under
a five-state supervisor. No RTOS, no dynamic allocation, no `String`, no
`delay()` anywhere in the race path.

![System architecture](../Folder%20A/flowcharts/01_system_architecture.png)

![Main control loop](../Folder%20A/flowcharts/02_main_control_loop.png)

### 6.2 The control law

**Steering in curvature, not in PWM difference.** The naive line follower adds
its error to one motor's PWM and subtracts it from the other. The gain that
feels right at low speed oversteers at high speed, because the same PWM
difference produces a much tighter turn when the car is moving slowly. You end
up tuning one set of gains per speed.

Our PID instead outputs a **path curvature** κ in 1/m. For wheel separation *b*:

```
v_left  = v · (1 − κ·b/2)
v_right = v · (1 + κ·b/2)
```

κ = 5 1/m is a 200 mm radius turn at 0.2 m/s and a 200 mm radius turn at
0.5 m/s. One set of gains, every speed.

**The error is a distance, in metres**, from a weighted centroid over five
per-channel-normalised analog readings — not a unitless index. That is what lets
the gains be reasoned about geometrically: `K_P = 34` means a 20 mm offset asks
for roughly a 1.5 m radius.

**The speed schedule is where the time is won:**

```
v_wheel = V_MAX / (1 + |κ|·b/2)          # the outer wheel saturates here
v_curve = V_STRAIGHT / (1 + 0.075·|κ|)   # grip and tracking-margin limit
v       = max(V_FLOOR, min(V_STRAIGHT, v_wheel, v_curve))
```

`v_wheel` is arithmetic, not a tuned number: at curvature κ the outer wheel must
run at `v·(1 + κ·b/2)`, so any faster and the wheel is clipped, the actual
curvature is lower than commanded, and the car runs wide on exactly the corner
where it mattered. Speed is picked from the curvature the controller is *about
to* demand — and the sensor bar's 138 mm lead gives the car the distance in
which to shed that speed.

**On saturation, both wheels are scaled by the same factor.** This preserves the
ratio between them and therefore the path curvature: the car takes the corner it
asked for, just slower. Clamping only the fast wheel changes the radius and runs
the car wide — the classic way a fast line follower loses a corner.

### 6.3 States and failure

![State machine](../Folder%20A/flowcharts/03_state_machine.png)

Motors are commanded off in `setup()` before anything else runs, so a brown-out
reset cannot leave a wheel driven. The **E-Stop is deliberately not a state** —
it removes power from the MCU, so modelling it in firmware would imply software
could observe or override it. `ST_FAULT` latches; a car that lost the line and
stopped does not restart itself.

![Line loss recovery](../Folder%20A/flowcharts/04_line_loss_recovery.png)

On line loss the car **always continues forward and never reverses**, for two
reasons: the sensor bar leads the axle by 138 mm, so continuing the arc sweeps
the bar back over where the line geometrically is; and reversing on a shared
track is how you cause a collision with the car behind you. After 2500 ms it
stops and latches — a stationary car is a hazard a marshal can deal with, a car
searching at speed is not.

### 6.4 Category alignment

No radio, no Wi-Fi, no Bluetooth, no serial command path — `Serial` is written
to and never read. One human input, the ARM button, pressed before the car is
released. There is no weapon code, no combat logic, no teleoperation and nothing
borrowed from another category.

---

## 7. Simulation

*Full detail: [`../Folder B/Simulation/SIMULATION.md`](../Folder%20B/Simulation/SIMULATION.md)*

The control law was developed in **Webots** on an e-puck differential-drive
model before any hardware existed, because the interesting question — *how fast
can the car enter a corner and still come out on the line* — costs sensors,
tyres and afternoons to answer on real hardware.

Three findings changed the design:

1. **The outer wheel saturates before grip runs out.** On the simulated circuit
   the car could do 0.129 m/s flat out but only 0.096 m/s through the tightest
   corner before the outer wheel hit its limit. Measured lap times matched that
   prediction. This produced the `v_wheel` ceiling.
2. **Scale both wheels, never clamp one.** Four lines of code, and it was worth
   the whole exercise.
3. **Discrete sensing is what limits the derivative term.** The e-puck's three
   *binary* sensors quantise the error to five values, so every change is a step
   and differentiating it produces an impulse — which is why the simulation had
   to filter most of the derivative's usefulness away. **This is why Lightning
   McQueen carries five analog channels rather than three digital ones.** A
   weighted centroid is continuous, so the derivative term is genuinely usable.

What simulation did **not** tell us, stated plainly: there is no tyre friction
model, no sensor noise or ambient light, no H-bridge deadband, no battery sag,
and the e-puck is not our vehicle. Every scaled constant is a prediction to be
verified on the real car, and `calibration.ino` exists precisely to do that
verification.

---

## 8. Build status and next steps

| | |
|---|---|
| Control law | Developed and swept in Webots ✔ |
| Firmware | Written, commented, pin map fixed ✔ |
| CAD | Parametric model complete; STEP, STL and laser-cut DXF exported ✔ |
| Schematics | Complete, with both safety devices annotated ✔ |
| BOM | Costed at R 1 843.60 ✔ |
| Physical build | Documented, not yet assembled |

**Next, in order:** cut the deck from the DXF · assemble and loom · run
`calibration.ino` on the competition track surface · sweep `CORNER_SLOW` on the
physical car and compare against the simulation prediction · time laps.

---

## 9. Credits and attribution

- The Webots control law began from the standard e-puck line-following example
  distributed with Webots, and was rewritten around curvature control and a
  speed schedule. The original example's structure is acknowledged.
- TCRT5000 mounting follows the device datasheet's recommended 8–15 mm standoff.
- Everything else — the firmware, the CAD, the schematics and this
  documentation — is our own work.
