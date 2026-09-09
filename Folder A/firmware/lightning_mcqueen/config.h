/* =====================================================================
 * Lightning McQueen  -  Team CO Coders
 * Robo Rumble 2026  |  Robo Grand Prix (autonomous racing)
 * ---------------------------------------------------------------------
 * config.h - every tunable in one place.
 *
 * Nothing in this file is a magic number: each constant either comes
 * from a datasheet, from the vehicle geometry in
 * Folder B/Mechanical Design/CAD/lightning_mcqueen_cad.py, or from the
 * Webots sweep documented in Folder B/Simulation/SIMULATION.md.
 * ===================================================================== */

#ifndef CONFIG_H
#define CONFIG_H

/* ------------------------------------------------------------------
 * PIN MAP  -  Arduino Uno R3
 * ------------------------------------------------------------------
 * ENA/ENB are on Timer1 (pins 9, 10) deliberately: Timer0 drives
 * millis()/micros() on pins 5 and 6, and we would rather not share it.
 */
#define PIN_IN1        2      // L298N IN1  - left motor direction A
#define PIN_IN2        4      // L298N IN2  - left motor direction B
#define PIN_ENA        9      // L298N ENA  - left motor PWM   (Timer1)
#define PIN_IN3        7      // L298N IN3  - right motor direction A
#define PIN_IN4        8      // L298N IN4  - right motor direction B
#define PIN_ENB       10      // L298N ENB  - right motor PWM  (Timer1)

#define PIN_START     12      // momentary arm/start button, INPUT_PULLUP
#define PIN_LED       13      // on-board LED, doubles as the status light
#define PIN_BUZZER     3      // piezo, audible arm/disarm and fault codes

/* 5-channel TCRT5000 array, left-to-right when looking forward. */
#define N_SENSORS      5
static const uint8_t SENSOR_PIN[N_SENSORS] = { A0, A1, A2, A3, A4 };

/* Sensor lateral offsets in millimetres from the vehicle centreline.
 * 20 mm pitch, matching SENSOR_PITCH in the CAD model. Used to turn the
 * raw readings into a physical cross-track error rather than a unitless
 * one, so the gains below have real units. */
static const float SENSOR_OFFSET_MM[N_SENSORS] = { -40, -20, 0, +20, +40 };

/* ------------------------------------------------------------------
 * VEHICLE GEOMETRY  -  mirrors the CAD model exactly
 * ------------------------------------------------------------------ */
#define WHEEL_RADIUS_M   0.0325f   // 65 mm wheel
#define AXLE_LENGTH_M    0.170f    // TRACK in the CAD model
#define SENSOR_LEAD_M    0.138f    // sensor bar ahead of the drive axle

/* TT motor, 1:48, on 9 V: ~200 rpm no-load. Derated to a realistic
 * loaded figure measured on the bench. */
#define MAX_WHEEL_RPM    170.0f
#define MAX_WHEEL_OMEGA  (MAX_WHEEL_RPM * 2.0f * 3.14159265f / 60.0f)
#define V_MAX            (WHEEL_RADIUS_M * MAX_WHEEL_OMEGA)  // ~0.58 m/s

/* ------------------------------------------------------------------
 * SPEED POLICY  (m/s)
 * ------------------------------------------------------------------
 * Same shape as the Webots controller: pick a curvature first, then
 * pick the fastest speed that curvature allows before the outer wheel
 * saturates, then clamp to a straight-line ceiling.
 */
#define V_STRAIGHT       0.52f    // straight-line target
#define V_FLOOR          0.16f    // never crawl slower than this
#define CORNER_SLOW      0.075f   // how hard curvature brakes us

/* ------------------------------------------------------------------
 * STEERING  -  PID on cross-track error, output is path curvature (1/m)
 * ------------------------------------------------------------------
 * Error is in metres. K_P = 34 means a 20 mm offset asks for
 * 0.68 1/m, a 1.47 m radius - a gentle correction, not a lurch.
 */
#define K_P              34.0f
#define K_I              0.35f
#define K_D              1.30f
#define KAPPA_MAX        14.0f    // 1/m, ~71 mm minimum radius
#define D_ALPHA          0.30f    // derivative low-pass, 0..1
#define I_CLAMP          1.50f    // anti-windup on the integral term

/* ------------------------------------------------------------------
 * RATE LIMITS
 * ------------------------------------------------------------------
 * The L298N can slam from 0 to full in one control period. These limits
 * exist so the commanded path stays smooth across the discrete sensor
 * states - they are not there to fake a weak motor.
 */
#define MAX_LIN_ACCEL    2.20f    // m/s^2
#define MAX_KAPPA_RATE   90.0f    // (1/m) per second

/* ------------------------------------------------------------------
 * LINE LOSS AND RECOVERY
 * ------------------------------------------------------------------ */
#define RECOVER_SPEED    0.20f    // m/s, always forward - never reverse
#define RECOVER_KAPPA    7.0f     // 1/m, ~143 mm radius sweep
#define LOST_TIMEOUT_MS  1200     // hold the last curvature this long
#define STOP_TIMEOUT_MS  2500     // then stop and latch a fault

/* ------------------------------------------------------------------
 * TIMING
 * ------------------------------------------------------------------
 * 200 Hz. The ADC needs 5 x 104 us = 520 us per sweep, so a 5 ms budget
 * leaves ~90 % of the period for control and actuation.
 */
#define CONTROL_PERIOD_MS   5
#define TELEMETRY_PERIOD_MS 250

/* ------------------------------------------------------------------
 * CALIBRATION
 * ------------------------------------------------------------------
 * Populated by Folder A/firmware/calibration. Run that sketch on the
 * actual track surface under actual lighting and paste the numbers here.
 * White floor reads LOW on a TCRT5000 breakout with the phototransistor
 * pulling the node down; a black line reads HIGH.
 */
static const int SENSOR_MIN[N_SENSORS] = { 118, 122, 115, 120, 124 };  // floor
static const int SENSOR_MAX[N_SENSORS] = { 872, 880, 869, 876, 881 };  // line
#define ON_LINE_FRACTION  0.45f   // normalised value above this = on the line

/* Below this total normalised weight we declare the line lost. */
#define MIN_TOTAL_WEIGHT  0.35f

/* ------------------------------------------------------------------
 * MOTOR TRIM
 * ------------------------------------------------------------------
 * The two TT gearboxes are never identical. Measure on the bench with
 * the calibration sketch and correct here, so the PID does not have to
 * spend its integral term fixing a mechanical asymmetry.
 */
#define TRIM_LEFT        1.000f
#define TRIM_RIGHT       0.972f

/* L298N loses roughly 1.9 V across the H-bridge and the motors will not
 * turn below this duty. Anything the controller asks for below the
 * deadband is lifted to it, so small corrections actually happen. */
#define PWM_DEADBAND     42       // 0..255

#endif  /* CONFIG_H */
