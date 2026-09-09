# Folder A — Source Code

All programming scripts, firmware and code required to run Lightning McQueen,
plus the documentation of the programming methods, frameworks and design.

**Start here:** [`PROGRAMMING.md`](PROGRAMMING.md) — the frameworks we use, the
control law derived from first principles, and all five flowcharts.

| Path | What it is |
|---|---|
| [`PROGRAMMING.md`](PROGRAMMING.md) | Programming methods, frameworks, architecture and flowcharts |
| [`firmware/lightning_mcqueen/`](firmware/lightning_mcqueen) | The race firmware — 200 Hz control superloop and five-state supervisor |
| [`firmware/lightning_mcqueen/config.h`](firmware/lightning_mcqueen/config.h) | Every tunable in one place, each traceable to a datasheet, the CAD model or a simulation sweep |
| [`firmware/calibration/`](firmware/calibration) | Measures sensor thresholds, motor trim and PWM deadband on the real track |
| [`simulation/`](simulation) | The Webots C++ controller the control law was developed in |
| [`flowcharts/`](flowcharts) | Five diagrams as Mermaid source (`.mmd`) and rendered PNG |

## Building and flashing

```
Arduino IDE 2.x  →  Board: Arduino Uno  →  Port: your Uno
Open  firmware/lightning_mcqueen/lightning_mcqueen.ino  →  Upload
```

`config.h` must sit in the same folder as the `.ino` — the Arduino IDE requires
the sketch folder name to match the sketch name, which is why the structure
looks the way it does.

**Order of operations on a new car:**

1. Flash `firmware/calibration/calibration.ino`.
2. Send `1` over serial at 115200 and sweep the car across the line for 10 s.
   Paste the printed `SENSOR_MIN[]` / `SENSOR_MAX[]` arrays into `config.h`.
3. Send `3` and note the duty at which each wheel first turns. That is
   `PWM_DEADBAND`.
4. Send `2` and measure the travel of each wheel. That ratio is `TRIM_RIGHT`.
5. Flash `firmware/lightning_mcqueen/lightning_mcqueen.ino`.

## Category alignment

This is autonomous racing code and nothing else. No radio, no Wi-Fi, no
Bluetooth, no serial command path — `Serial` is written to and never read. The
only human input is the ARM button pressed before the car is released.
