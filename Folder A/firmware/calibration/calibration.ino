/* =====================================================================
 * Lightning McQueen  -  sensor and drivetrain calibration
 * Team CO Coders  |  Robo Rumble 2026  |  Robo Grand Prix
 * ---------------------------------------------------------------------
 * Flash this BEFORE the race firmware, on the actual track surface,
 * under the actual lighting. It prints two blocks you paste straight
 * into ../lightning_mcqueen/config.h.
 *
 *   MODE 1  Sensor sweep
 *     Slide the car sideways across the line for ~10 s. The sketch
 *     records the min and max each channel ever sees and prints the
 *     SENSOR_MIN / SENSOR_MAX arrays.
 *
 *   MODE 2  Motor trim
 *     Runs both wheels at a fixed duty for 3 s. Measure how far each
 *     wheel travels (mark the tyre, count revolutions, or run the car
 *     against a straight edge). Enter the ratio into TRIM_RIGHT.
 *
 *   MODE 3  Deadband hunt
 *     Ramps duty from 0 upward and prints the value at which each wheel
 *     first turns. That number is PWM_DEADBAND.
 *
 * Send '1', '2' or '3' over the serial monitor at 115200 to pick a mode.
 * ===================================================================== */

#include "../lightning_mcqueen/config.h"

static int lo[N_SENSORS], hi[N_SENSORS];

static void resetSweep() {
  for (uint8_t i = 0; i < N_SENSORS; i++) { lo[i] = 1023; hi[i] = 0; }
}

static void raw(uint8_t inA, uint8_t inB, uint8_t en, int pwm) {
  digitalWrite(inA, pwm >= 0 ? HIGH : LOW);
  digitalWrite(inB, pwm >= 0 ? LOW : HIGH);
  analogWrite(en, abs(pwm));
}

static void stopAll() {
  analogWrite(PIN_ENA, 0);
  analogWrite(PIN_ENB, 0);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_IN1, OUTPUT); pinMode(PIN_IN2, OUTPUT); pinMode(PIN_ENA, OUTPUT);
  pinMode(PIN_IN3, OUTPUT); pinMode(PIN_IN4, OUTPUT); pinMode(PIN_ENB, OUTPUT);
  stopAll();
  resetSweep();
  Serial.println(F("CALIBRATION - send 1 (sensors), 2 (trim), 3 (deadband)"));
}

/* ---------------------------------------------------------------- */
static void modeSensors() {
  Serial.println(F("Sweep the car across the line for 10 s..."));
  resetSweep();
  const uint32_t t0 = millis();
  while (millis() - t0 < 10000) {
    for (uint8_t i = 0; i < N_SENSORS; i++) {
      const int v = analogRead(SENSOR_PIN[i]);
      if (v < lo[i]) lo[i] = v;
      if (v > hi[i]) hi[i] = v;
    }
    delay(2);
  }
  Serial.println(F("\n--- paste into config.h ---"));
  Serial.print(F("static const int SENSOR_MIN[N_SENSORS] = { "));
  for (uint8_t i = 0; i < N_SENSORS; i++) {
    Serial.print(lo[i]); if (i < N_SENSORS - 1) Serial.print(F(", "));
  }
  Serial.println(F(" };"));
  Serial.print(F("static const int SENSOR_MAX[N_SENSORS] = { "));
  for (uint8_t i = 0; i < N_SENSORS; i++) {
    Serial.print(hi[i]); if (i < N_SENSORS - 1) Serial.print(F(", "));
  }
  Serial.println(F(" };"));

  /* Contrast check: a channel with less than ~350 counts of separation
   * will not survive track lighting. Better to know now. */
  for (uint8_t i = 0; i < N_SENSORS; i++) {
    const int span = hi[i] - lo[i];
    if (span < 350) {
      Serial.print(F("WARNING ch ")); Serial.print(i);
      Serial.print(F(" contrast only ")); Serial.print(span);
      Serial.println(F(" counts - adjust ride height or the trim pot"));
    }
  }
}

/* ---------------------------------------------------------------- */
static void modeTrim() {
  Serial.println(F("Both wheels at duty 160 for 3 s. Measure the travel."));
  delay(1500);
  raw(PIN_IN1, PIN_IN2, PIN_ENA, 160);
  raw(PIN_IN3, PIN_IN4, PIN_ENB, 160);
  delay(3000);
  stopAll();
  Serial.println(F("TRIM_RIGHT = left_distance / right_distance"));
}

/* ---------------------------------------------------------------- */
static void modeDeadband() {
  Serial.println(F("Ramping duty. Note the value where each wheel starts."));
  for (int d = 0; d <= 120; d += 2) {
    raw(PIN_IN1, PIN_IN2, PIN_ENA, d);
    raw(PIN_IN3, PIN_IN4, PIN_ENB, d);
    Serial.print(F("duty ")); Serial.println(d);
    delay(400);
  }
  stopAll();
  Serial.println(F("PWM_DEADBAND = the higher of the two start values"));
}

void loop() {
  if (!Serial.available()) return;
  switch (Serial.read()) {
    case '1': modeSensors();  break;
    case '2': modeTrim();     break;
    case '3': modeDeadband(); break;
    default: break;
  }
}
