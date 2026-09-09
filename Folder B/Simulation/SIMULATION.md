# Simulation

**Team CO Coders · Lightning McQueen · Robo Rumble 2026 · Robo Grand Prix**

> *Bonus category: Technical Excellence & Simulation — evidence of rigorous
> testing in a simulation environment before physical fabrication.*

---

## 1. Why we simulated first

We wanted the control law settled before any hardware existed, for one specific
reason: **the interesting part of a line follower is not "does it follow the
line", it is "how fast can it go into a corner and still come out on the line".**
Answering that on hardware means repeatedly running a real car off a real track
at increasing speed, which costs sensors, tyres and afternoons.

In simulation we could sweep the speed policy across dozens of runs in minutes,
find the point where the car starts running wide, and understand *why* — which
is what told us the outer wheel saturating, not grip, was the binding constraint.

---

## 2. Environment

| | |
|---|---|
| Simulator | Webots 2023b |
| Robot model | e-puck (differential drive, 2 wheels + 3 ground sensors) |
| Controller | C++, [`../../Folder A/simulation/robograndprix_sim.cpp`](../../Folder%20A/simulation/robograndprix_sim.cpp) |
| Track | `track_circuit.png` floor texture, tightest corner 76 mm radius |
| Time step | 16 ms (62.5 Hz) — Webots' default e-puck basic time step |

A video of the simulated car running the circuit accompanies this submission.

---

## 3. What the e-puck is and is not

The e-puck is not Lightning McQueen. It is 74 mm across with a 52 mm wheel
separation and a 0.129 m/s top speed; our car is 211 mm across with a 170 mm
track and a 0.58 m/s top speed. We were never trying to simulate our vehicle
dimensionally.

**What transfers is the control law**, because the law is written in units that
do not depend on the vehicle:

- error in metres, not in "sensor counts";
- steering output in curvature (1/m), not in "PWM difference";
- the speed schedule expressed as a function of curvature and wheel separation.

Swap `WHEEL_RADIUS`, `AXLE_LENGTH` and `MAX_WHEEL_OMEGA` and the same equations
describe a different car. That is the whole reason for choosing those units, and
it is why the Arduino firmware in `Folder A/firmware` reads as a near-transcription
of the simulation controller.

---

## 4. What the sweeps told us

### 4.1 The outer wheel saturates before grip runs out

The first thing the simulation showed is that the limit on corner speed was not
sliding — it was the outer wheel hitting its own maximum angular velocity. At
curvature κ, the outer wheel must run at `v · (1 + κ·b/2)`. Ask for more and the
wheel is clipped, the *actual* curvature is lower than the *commanded*
curvature, and the car runs wide on exactly the corner where you needed it not
to.

That produced the `v_wheel` ceiling, which is arithmetic rather than a tuned
number:

```
v_wheel = V_MAX / (1 + |κ|·b/2)
```

On the e-puck: 0.129 m/s flat out, but only **0.096 m/s** through the 76 mm
corner before the outer wheel saturates. The measured best lap matched that
prediction, which is what gave us confidence in the model.

### 4.2 Scale both wheels, never clamp one

The corollary. When saturation happens anyway, scaling **both** wheels by the
same factor preserves the ratio between them and therefore the path curvature —
the car takes the corner it asked for, just slower. Clamping only the fast wheel
changes the radius and runs the car wide. This is four lines of code and it was
worth the whole exercise:

```cpp
const double peak = std::max(std::fabs(wl), std::fabs(wr));
if (peak > MAX_WHEEL_OMEGA) {
  const double s = MAX_WHEEL_OMEGA / peak;
  wl *= s; wr *= s;
}
```

### 4.3 The comfort limit needs its own term

`v_wheel` alone still ran the car to the edge of its tracking envelope, with no
margin for sensor error. Adding a second, softer ceiling gave us a single knob
for how aggressive to be:

```
v_curve = V_STRAIGHT / (1 + CORNER_SLOW · |κ|)
```

Sweeping `CORNER_SLOW` in simulation: below 0.04 the car ran wide on the tight
corner; above 0.12 it was leaving obvious time on the table. **0.06** was the
best clean value on the e-puck. We carry **0.075** into the hardware firmware —
slightly more conservative, because the real car has sensor noise, tyre slip and
a deck that flexes, none of which the simulator models.

### 4.4 Discrete sensing is what limits the derivative term

The e-puck has three *binary* ground sensors, so the simulated error can only
take five values: {−1, −0.5, 0, +0.5, +1}. Every change is a step, and
differentiating a step produces an impulse. That is why the simulation
controller runs `D_ALPHA = 0.30` on the derivative and a relatively low
`K_D = 1.1` — most of the derivative's usefulness is being filtered away just to
keep it stable.

**This finding drove a hardware decision.** It is the reason Lightning McQueen
carries **five analog** channels rather than three digital ones. A weighted
centroid over five analog readings is continuous, so the derivative term is
genuinely usable — which is why the hardware firmware runs `K_D = 1.30` with the
same filter constant and gets real damping out of it.

### 4.5 Rate limits are about tracking, not about faking weak motors

Webots motors reach commanded velocity in one time step. Without rate limiting,
the commanded curvature jumped discontinuously with each sensor state change and
the car visibly twitched. `MAX_KAPPA_RATE` and `MAX_LIN_ACCEL` exist to keep the
*commanded path* smooth. The comment in the source says exactly this, because
it is the kind of constant a reader will otherwise assume is a fudge.

---

## 5. Constants that came out of simulation

| Simulation constant | Value | Hardware equivalent | Value | Note |
|---|---|---|---|---|
| `CORNER_SLOW` | 0.060 | `CORNER_SLOW` | 0.075 | More conservative on hardware |
| `D_ALPHA` | 0.30 | `D_ALPHA` | 0.30 | Unchanged |
| `KAPPA_MAX` | 18 1/m | `KAPPA_MAX` | 14 1/m | Scaled to our 170 mm track |
| `K_D` | 1.1 | `K_D` | 1.30 | Raised — analog sensing allows it |
| `RECOVER_KAPPA` | 9 1/m | `RECOVER_KAPPA` | 7 1/m | Scaled to our track |
| forward-only recovery | yes | yes | — | Confirmed in simulation |
| both-wheel scaling | yes | yes | — | The key finding |

`K_P` and `K_I` are **not** carried across, and deliberately so. The simulation's
error is unitless in the range ±1; the firmware's error is a cross-track
distance in metres. `K_P = 26` on a unitless error and `K_P = 34` on an error in
metres are not comparable quantities, and pretending otherwise would be the
easiest way to arrive at a badly tuned car. The hardware gains start from the
geometry (a 20 mm offset should ask for roughly a 1.5 m radius) and get trimmed
on the track.

---

## 6. What simulation did not tell us

Stated plainly, because a simulation section that claims everything transferred
is not worth reading:

- **No tyre model.** Webots' contact model is not a friction circle. Real slip
  angles will show up on the track and nowhere else.
- **No sensor noise, no ambient light.** Real TCRT5000s see track lighting,
  reflections and a floor that is not uniformly white. This is precisely what
  `calibration.ino` exists to measure.
- **No H-bridge deadband.** The simulated motors respond linearly from zero. The
  L298N does not turn a wheel below about 16 % duty, which is why
  `PWM_DEADBAND` exists in the firmware and has no counterpart in the simulator.
- **No battery sag.** The simulated supply is stiff. A PP3 pack under a stall is
  not.
- **Different vehicle.** Every scaled constant in the table above is a
  prediction to be verified on the real car, not a measured result.

The next step is exactly that verification: run `calibration.ino`, then a
speed-schedule sweep on the physical track, and compare against these
predictions.

---

## 7. Files

```
Simulation/
├── SIMULATION.md                          this document
└── grandPrixSimulation_original_notes.md  our original simulation notes

Folder A/simulation/
└── robograndprix_sim.cpp                  the Webots controller
```
