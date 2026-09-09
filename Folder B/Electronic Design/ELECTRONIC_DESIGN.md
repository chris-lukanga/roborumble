# Electronic Design

**Team CO Coders · Lightning McQueen · Robo Rumble 2026 · Robo Grand Prix**

This document justifies every active component on the vehicle. For each one we
state what it does, why it was chosen, and what we rejected instead. The wiring
itself is in [`../Schematics`](../Schematics).

---

## 1. Control unit — Arduino Uno R3 (ATmega328P)

**Role.** Reads five analog channels, runs the control law at 200 Hz, drives six
pins into the H-bridge.

**Why.** The job is small and the requirements are specific: at least five ADC
channels, two independent hardware PWM timers, and enough determinism to trust a
5 ms loop. The ATmega328P has six ADC channels and three timers, and its
successive-approximation ADC converts in 104 µs. Five conversions cost 520 µs —
10 % of the control period. The whole pipeline measures ~760 µs, so we run at
15 % CPU with 85 % headroom.

**Why not an ESP32.** It is faster, it has more ADC resolution, and we
considered it seriously. Two things ruled it out. First, its ADC is
non-linear near the rails and needs per-channel characterisation to be trusted —
extra work for a signal we are already normalising. Second, and decisively, it
arrives with Wi-Fi and Bluetooth radios on the die. Robo Grand Prix forbids
remote control of any kind. We would rather hand a judge a board that
*physically cannot* be commanded remotely than a board where the argument
depends on firmware we claim we did not write.

**Why not a bare ATmega328P on the breadboard.** It saves 15 g and R120, and
costs an afternoon of bootloader and crystal work at the point in the schedule
where we can least afford it.

**Pin map and the one non-obvious decision.**

| Function | Pin | Note |
|---|---|---|
| Sensor channels 1–5 | A0–A4 | A5 left free for a future encoder or I²C |
| Motor A direction | D2, D4 | plain digital |
| Motor A speed | **D9** | Timer1 |
| Motor B direction | D7, D8 | plain digital |
| Motor B speed | **D10** | Timer1 |
| ARM button | D12 | `INPUT_PULLUP`, active low |
| Status LED | D13 | on-board LED doubles as the status light |
| Buzzer | D3 | Timer2 via `tone()` |

The PWM pins are on **Timer1 (D9, D10), not Timer0 (D5, D6)**. Timer0 drives
`millis()` and `micros()`, which the fixed-rate scheduler depends on. Sharing it
with motor PWM is the kind of coupling that produces a bug you only see at one
particular duty cycle, three days before the event.

---

## 2. Motor driver — L298N dual H-bridge module

**Role.** Takes 9 V from the switched battery rail and six logic lines from the
Uno, and drives two motors bidirectionally. Its on-board 78M05 also generates
the 5 V logic rail.

**Why.** It handles 2 A per channel against a stall current of roughly 1.2 A per
TT motor, so there is real margin. The module carries flyback diodes and the
regulator already, which removes a whole subcircuit from the breadboard — and a
breadboard is exactly where a hand-wired flyback diode goes intermittent.

**The honest downside.** The L298 is a bipolar bridge and drops roughly 1.9 V
across itself. From a 9 V pack, the motors see about 7.1 V, and the wheels do
not turn at all below about 16 % duty. We handle this in two places:

- `PWM_DEADBAND = 42` in `config.h` maps the controller's 0–1 output onto duty
  42–255, so a small correction actually produces movement instead of only
  heating the bridge;
- the calibration sketch (mode 3) measures the real deadband on the actual
  motors, because it varies between gearboxes.

**Why not a TB6612FNG.** It is a MOSFET bridge, drops ~0.5 V instead of 1.9 V,
and is genuinely the better part — we would gain roughly 18 % top speed. It was
rejected on availability and cost risk: the L298N is stocked by every South
African hobby supplier and costs a third as much. If a TB6612FNG is in hand
before the build, it is a drop-in swap: same six control lines, same pin map,
and only `PWM_DEADBAND` and `MAX_WHEEL_RPM` change.

---

## 3. Sensing — 5-channel TCRT5000 reflective array

**Role.** Measures how far the car is off the line.

**Why this sensor.** The TCRT5000 is an IR emitter and phototransistor in one
package with a daylight-blocking filter over the detector. Its datasheet optimum
standoff is 8–15 mm; we mount at 12 mm, in the middle of that band, so ±3 mm of
deck deflection or track unevenness does not move us out of it.

**Why five channels and not three.** This is the single most consequential
electronic decision on the car.

Three binary sensors can only report five distinct error values:
{−1, −0.5, 0, +0.5, +1}. That is what our Webots prototype had, and the
quantisation is why its derivative term needed such heavy filtering — every
transition was a step change. Five **analog** channels let us compute a weighted
centroid, which is continuous. Continuous error means:

- the derivative term is usable, so the car damps its own oscillation instead of
  weaving down the straights;
- the speed schedule sees corner entry developing gradually rather than as a
  step, so it sheds speed smoothly instead of lurching;
- a 40 mm sensing span at 20 mm pitch straddles a 19 mm competition line with a
  channel to spare on each side, so a moderate excursion is still measured
  rather than simply "lost".

The cost of the two extra channels is about R40 and two ADC pins we had spare.

**Per-channel calibration.** The five devices differ measurably in LED output
and phototransistor gain. `config.h` therefore stores `SENSOR_MIN[]` and
`SENSOR_MAX[]` per channel rather than one global threshold, and
`calibration.ino` mode 1 measures them on the actual track under the actual
lighting. It also warns if any channel shows less than 350 counts of
floor-to-line contrast, which is the signal that the ride height or the trim pot
is wrong — better to find that in the pit than on the grid.

---

## 4. Power — 2 × 9 V PP3

**Role.** One switched 9 V rail feeding the H-bridge, from which the 78M05
derives 5 V logic.

**Why 9 V PP3 and not AA cells.** Our concept notes committed to this and the
mass budget vindicates it: two PP3 cells weigh 92 g where twelve 1.5 V AA cells
weigh about 276 g. On a car whose whole assembled mass is 855 g, that is a
21 % difference in the load the same TT gearboxes have to accelerate.

**The honest downside.** A PP3 alkaline has roughly 550 mAh and a fairly high
internal resistance. Two in series-parallel give us about 1.2 Ah at 9 V, which is
comfortable for a race heat but not for an afternoon of testing — and under a
stall the terminal voltage sags enough to matter. Mitigations:

- the polyfuse and the wiring are sized for the sag, not the nominal;
- `TRIM_RIGHT` and the speed schedule are calibrated on a fresh pack, and the
  pack is swapped between heats (hook-and-loop straps, ten seconds);
- for bench testing we run from a 9 V bench supply, not from cells.

**Single rail, not two.** Some designs run separate logic and motor batteries so
that motor sag cannot brown out the MCU. We deliberately do not, because a
separate logic battery would keep the MCU alive after the E-Stop opens the motor
rail. A shared rail means one switch kills everything — which is exactly what
Universal Design Constraint 4 asks for. The trade is a 100 µF bulk capacitor on
the 5 V rail to ride out switching transients.

---

## 5. Protection and indication

| Part | Value | Why |
|---|---|---|
| **F1** polyfuse | 2 A hold | Against a stalled motor or a wiring short. Resettable, so a pit incident does not consume a spare. Sized above the 1.2 A per-motor stall so it does not nuisance-trip on a hard corner. |
| **D1** power LED | + 1 kΩ | Shows the rail is live. On a car whose normal state is "sitting still, waiting", this is the difference between a safe approach and an assumed-dead robot. |
| **D2** status LED | on-board D13, 220 Ω | Blink codes state: slow = disarmed, fast = armed countdown, solid = racing, urgent = fault. Readable from the side of the track. |
| **LS1** piezo | on D3 | Audible arm, countdown and fault. A marshal facing away still hears the fault tone. |
| **C1** bulk cap | 100 µF on the 5 V rail | Rides out H-bridge switching transients. Deliberately no larger — see the safety note below. |

**A note on that capacitor.** 100 µF at 5 V stores 1.25 mJ. A loaded TT gearbox
needs on the order of a joule to turn once. There is no combination of
downstream capacitance on this vehicle that could move a wheel after the E-Stop
opens, and that is a design constraint we checked rather than assumed.

---

## 6. Safety devices — Universal Design Constraints 3 and 4

Detailed in [`../Schematics/SCHEMATICS.md`](../Schematics/SCHEMATICS.md) and
drawn in `../Schematics/01_power_safety_chain.svg`. In summary:

- **SW1, E-Stop:** 22 mm latching mushroom, normally closed, **first device in
  the battery positive line**, upstream of SW2 and of the L298N.
- **SW2, ON/OFF:** SPST rocker, second in the same line.

Because the 5 V logic rail is derived downstream of both, opening either one
de-energises the MCU, the sensor array and the motors together. No firmware path
can defeat SW1, because the contact is mechanically in the battery line.

---

## 7. Component summary

| Ref | Component | Qty | Function |
|---|---|---:|---|
| U1 | L298N dual H-bridge module | 1 | Motor drive + 5 V regulation |
| U2 | Arduino Uno R3 | 1 | Control |
| U3 | 5-channel TCRT5000 array | 1 | Line sensing |
| M1, M2 | TT gear motor 1:48 + 65 mm wheel | 2 | Drive |
| BT1, BT2 | 9 V PP3 + holder | 2 | Power |
| SW1 | 22 mm latching E-Stop, NC | 1 | **Emergency stop (Constraint 4)** |
| SW2 | SPST rocker switch | 1 | **ON/OFF (Constraint 3)** |
| SW3 | Momentary pushbutton | 1 | ARM |
| F1 | 2 A resettable polyfuse | 1 | Overcurrent protection |
| D1 | 5 mm LED + 1 kΩ | 1 | Power-on indication |
| D2 | Status LED + 220 Ω | 1 | State indication |
| LS1 | Piezo buzzer | 1 | Audible state |
| C1 | 100 µF electrolytic | 1 | 5 V rail bulk |
| — | 830-point breadboard | 1 | Interconnect |
| — | Ball castor, 20 mm | 1 | Tail support |

Costs, suppliers, stock codes and buy links are in
[`../../Folder C/Bill_of_Materials.xlsx`](../../Folder%20C/Bill_of_Materials.xlsx).
