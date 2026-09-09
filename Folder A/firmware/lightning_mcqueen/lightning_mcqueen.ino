/* =====================================================================
 * Lightning McQueen  -  autonomous line-following racer
 * Team CO Coders  |  Robo Rumble 2026  |  Robo Grand Prix
 * ---------------------------------------------------------------------
 * Target : Arduino Uno R3 + L298N dual H-bridge + 2 x TT gear motor
 * Sensing: 5-channel TCRT5000 reflective array, 20 mm pitch
 *
 * CATEGORY COMPLIANCE
 *   Robo Grand Prix requires the robot to be fully autonomous. There is
 *   no radio, no Wi-Fi, no Bluetooth and no serial command path in this
 *   firmware. The only human input is a momentary ARM button pressed
 *   before the run starts, and the hardware E-Stop, which cuts battery
 *   positive and is therefore invisible to software by design.
 *
 * CONTROL ARCHITECTURE
 *   A non-blocking fixed-rate (200 Hz) superloop running a four-stage
 *   pipeline, plus a five-state supervisory machine:
 *
 *     SENSE  -> read 5 ADCs, normalise against calibration
 *     FUSE   -> weighted centroid gives a cross-track error in metres
 *     PLAN   -> PID on that error outputs a PATH CURVATURE (1/m), then
 *               a speed schedule picks the fastest speed that curvature
 *               allows before the outer wheel saturates
 *     ACT    -> differential-drive kinematics turns (v, kappa) into two
 *               wheel speeds, slew-limited, deadband-compensated, PWM
 *
 *   Steering in curvature rather than in "PWM difference" is the tweak
 *   that carries over from our Webots work: the same gains behave the
 *   same way at every speed, because curvature is a property of the
 *   path, not of the throttle.
 *
 * See ../../PROGRAMMING.md for the flowcharts and the derivation.
 * ===================================================================== */

#include "config.h"

/* ------------------------------------------------------------------ */
/* Supervisory states                                                  */
/* ------------------------------------------------------------------ */
enum State {
  ST_BOOT,      // power-up self-test
  ST_DISARMED,  // waiting for the ARM button, motors electrically idle
  ST_ARMED,     // armed, 3 s countdown, still not moving
  ST_RACING,    // closed-loop line following
  ST_FAULT      // line lost too long, or self-test failed: motors off
};

static State state = ST_BOOT;

/* Controller memory ------------------------------------------------- */
static float integral      = 0.0f;
static float prevError     = 0.0f;
static float filteredD     = 0.0f;
static float lastKappa     = 0.0f;
static float vCmd          = 0.0f;
static float kappaCmd      = 0.0f;
static bool  firstStep     = true;

/* Timing ------------------------------------------------------------ */
static uint32_t lastControlUs = 0;
static uint32_t lastTelemMs   = 0;
static uint32_t stateEnteredMs = 0;
static uint32_t lostMs        = 0;

/* Telemetry --------------------------------------------------------- */
static float distanceM = 0.0f;
static float vPeak     = 0.0f;
static uint32_t lapMs  = 0;

/* ------------------------------------------------------------------ */
/* Small helpers                                                       */
/* ------------------------------------------------------------------ */
static inline float clampf(float v, float lo, float hi) {
  return v < lo ? lo : (v > hi ? hi : v);
}

/* Move `current` toward `target` no faster than maxRate per second. */
static inline float slew(float target, float current, float maxRate, float dt) {
  const float lim = maxRate * dt;
  return current + clampf(target - current, -lim, lim);
}

static void enterState(State s) {
  state = s;
  stateEnteredMs = millis();
}

/* ------------------------------------------------------------------ */
/* SENSE + FUSE                                                        */
/* ------------------------------------------------------------------ */
/* Returns true when the line is visible. On true, *errorM holds the
 * cross-track error in metres: positive means the line is to the RIGHT
 * of the vehicle centreline, so the car must steer right.
 *
 * A weighted centroid is used rather than the discrete (a - b) / total
 * of the Webots prototype. With five analog channels the centroid is
 * continuous, which removes the quantisation steps that forced the
 * simulator's derivative term to be so heavily filtered.
 */
static bool readLine(float *errorM, float *totalWeight) {
  float sumW = 0.0f;
  float sumWX = 0.0f;

  for (uint8_t i = 0; i < N_SENSORS; i++) {
    const int raw = analogRead(SENSOR_PIN[i]);

    /* Normalise this channel against its own calibration. Per-channel
     * calibration matters: the five TCRT5000s have different LED
     * brightness and different phototransistor gain. */
    float n = (float)(raw - SENSOR_MIN[i]) /
              (float)(SENSOR_MAX[i] - SENSOR_MIN[i]);
    n = clampf(n, 0.0f, 1.0f);

    /* Anything below the on-line fraction is floor, not line. Squaring
     * what remains sharpens the centroid against reflections. */
    if (n < ON_LINE_FRACTION) continue;
    const float w = (n - ON_LINE_FRACTION) / (1.0f - ON_LINE_FRACTION);
    const float w2 = w * w;

    sumW  += w2;
    sumWX += w2 * SENSOR_OFFSET_MM[i];
  }

  *totalWeight = sumW;
  if (sumW < MIN_TOTAL_WEIGHT) return false;

  *errorM = (sumWX / sumW) / 1000.0f;   // mm -> m
  return true;
}

/* ------------------------------------------------------------------ */
/* ACT  -  differential drive, deadband compensation, PWM              */
/* ------------------------------------------------------------------ */
static void driveWheel(uint8_t inA, uint8_t inB, uint8_t en, float omega) {
  const bool forward = (omega >= 0.0f);
  float mag = fabsf(omega) / MAX_WHEEL_OMEGA;      // 0..1
  mag = clampf(mag, 0.0f, 1.0f);

  int pwm = 0;
  if (mag > 0.002f) {
    /* Map 0..1 onto DEADBAND..255 so a small command still turns the
     * wheel instead of only heating the H-bridge. */
    pwm = PWM_DEADBAND + (int)(mag * (255.0f - PWM_DEADBAND));
    pwm = constrain(pwm, 0, 255);
  }

  digitalWrite(inA, forward ? HIGH : LOW);
  digitalWrite(inB, forward ? LOW  : HIGH);
  analogWrite(en, pwm);
}

static void coast() {
  analogWrite(PIN_ENA, 0);
  analogWrite(PIN_ENB, 0);
  digitalWrite(PIN_IN1, LOW); digitalWrite(PIN_IN2, LOW);
  digitalWrite(PIN_IN3, LOW); digitalWrite(PIN_IN4, LOW);
  vCmd = 0.0f;
  kappaCmd = 0.0f;
}

/* Convert a body command (v m/s, kappa 1/m) into two wheel speeds.
 *   v_left  = v (1 - kappa * b / 2)
 *   v_right = v (1 + kappa * b / 2)
 * If either wheel saturates, BOTH are scaled by the same factor. That
 * preserves the path curvature and sacrifices only speed - the car
 * still takes the corner, just slower. Clamping one wheel alone would
 * change the radius and run us wide. */
static void applyBodyCommand(float v, float kappa) {
  const float half = kappa * AXLE_LENGTH_M / 2.0f;
  float vl = v * (1.0f - half);
  float vr = v * (1.0f + half);

  float wl = vl / WHEEL_RADIUS_M;
  float wr = vr / WHEEL_RADIUS_M;

  const float peak = fmaxf(fabsf(wl), fabsf(wr));
  if (peak > MAX_WHEEL_OMEGA) {
    const float s = MAX_WHEEL_OMEGA / peak;
    wl *= s;
    wr *= s;
  }

  driveWheel(PIN_IN1, PIN_IN2, PIN_ENA, wl * TRIM_LEFT);
  driveWheel(PIN_IN3, PIN_IN4, PIN_ENB, wr * TRIM_RIGHT);

  const float vActual = (wl + wr) * 0.5f * WHEEL_RADIUS_M;
  distanceM += vActual * (CONTROL_PERIOD_MS / 1000.0f);
  if (vActual > vPeak) vPeak = vActual;
}

/* ------------------------------------------------------------------ */
/* PLAN  -  one control step                                           */
/* ------------------------------------------------------------------ */
static void controlStep(float dt) {
  float errorM = 0.0f, weight = 0.0f;
  const bool seen = readLine(&errorM, &weight);

  float vTarget, kappaTarget;

  if (seen) {
    lostMs = 0;

    if (firstStep) { prevError = errorM; firstStep = false; }

    /* Derivative on a low-pass filter: the ADC noise floor is a couple
     * of LSB and raw differentiation would amplify it straight into
     * the motors. */
    const float rawD = (errorM - prevError) / dt;
    filteredD = D_ALPHA * rawD + (1.0f - D_ALPHA) * filteredD;

    /* Integral only accumulates while we are actually tracking, and is
     * clamped, so a long corner cannot wind it up into an overshoot on
     * the following straight. */
    integral = clampf(integral + errorM * dt, -I_CLAMP, I_CLAMP);
    prevError = errorM;

    kappaTarget = K_P * errorM + K_I * integral + K_D * filteredD;
    kappaTarget = clampf(kappaTarget, -KAPPA_MAX, KAPPA_MAX);
    lastKappa = kappaTarget;

    /* Speed schedule. Two independent ceilings, take the lower:
     *   vWheelLimit - the speed at which the OUTER wheel would hit its
     *                 own maximum at this curvature
     *   vCurve      - a comfort limit that trades speed for grip and
     *                 tracking margin as the corner tightens          */
    const float vWheelLimit =
        V_MAX / (1.0f + fabsf(kappaTarget) * AXLE_LENGTH_M / 2.0f);
    const float vCurve =
        V_STRAIGHT / (1.0f + CORNER_SLOW * fabsf(kappaTarget));

    vTarget = fminf(V_STRAIGHT, fminf(vWheelLimit, vCurve));
    if (vTarget < V_FLOOR) vTarget = V_FLOOR;

  } else {
    /* Line lost. Keep going forward on the last curvature - the car is
     * almost always mid-corner when this happens, so continuing the arc
     * sweeps the sensor bar back over the line. Never reverse: reversing
     * on a track with other traffic is how you cause a collision. */
    lostMs += (uint32_t)(dt * 1000.0f);

    if (lostMs > STOP_TIMEOUT_MS) {
      enterState(ST_FAULT);
      return;
    }

    kappaTarget = clampf(lastKappa, -RECOVER_KAPPA, RECOVER_KAPPA);
    vTarget = (lostMs > LOST_TIMEOUT_MS) ? RECOVER_SPEED * 0.5f
                                         : RECOVER_SPEED;
    integral = 0.0f;   // do not integrate blind
  }

  kappaCmd = slew(kappaTarget, kappaCmd, MAX_KAPPA_RATE, dt);
  vCmd     = slew(vTarget,     vCmd,     MAX_LIN_ACCEL,  dt);

  applyBodyCommand(vCmd, kappaCmd);
}

/* ------------------------------------------------------------------ */
/* Self-test                                                           */
/* ------------------------------------------------------------------ */
/* Confirms every ADC channel is alive and inside a sane band. A channel
 * reading rail-to-rail or dead flat means a disconnected sensor, and we
 * would rather find that in the pit than on the grid. */
static bool selfTest() {
  bool ok = true;
  for (uint8_t i = 0; i < N_SENSORS; i++) {
    const int raw = analogRead(SENSOR_PIN[i]);
    if (raw < 8 || raw > 1015) {
      Serial.print(F("SELFTEST FAIL: channel "));
      Serial.print(i);
      Serial.print(F(" reads "));
      Serial.println(raw);
      ok = false;
    }
  }
  return ok;
}

static void beep(uint16_t f, uint16_t ms) {
  tone(PIN_BUZZER, f, ms);
  delay(ms);
  noTone(PIN_BUZZER);
}

/* ------------------------------------------------------------------ */
/* setup / loop                                                        */
/* ------------------------------------------------------------------ */
void setup() {
  Serial.begin(115200);

  pinMode(PIN_IN1, OUTPUT); pinMode(PIN_IN2, OUTPUT); pinMode(PIN_ENA, OUTPUT);
  pinMode(PIN_IN3, OUTPUT); pinMode(PIN_IN4, OUTPUT); pinMode(PIN_ENB, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_START, INPUT_PULLUP);

  coast();   /* motors are commanded off BEFORE anything else runs */

  Serial.println(F("Lightning McQueen | CO Coders | Robo Grand Prix 2026"));
  Serial.print(F("v_max ")); Serial.print(V_MAX, 2);
  Serial.print(F(" m/s | kappa_max ")); Serial.print(KAPPA_MAX, 1);
  Serial.print(F(" 1/m | min radius "));
  Serial.print(1000.0f / KAPPA_MAX, 0); Serial.println(F(" mm"));

  enterState(ST_BOOT);
}

void loop() {
  const uint32_t nowUs = micros();
  const uint32_t nowMs = millis();

  /* Fixed-rate scheduler. Everything below runs exactly once per
   * CONTROL_PERIOD_MS; nothing in the pipeline blocks. */
  if ((uint32_t)(nowUs - lastControlUs) < (uint32_t)CONTROL_PERIOD_MS * 1000UL)
    return;
  const float dt = (nowUs - lastControlUs) / 1000000.0f;
  lastControlUs = nowUs;

  const bool startPressed = (digitalRead(PIN_START) == LOW);

  switch (state) {

    case ST_BOOT:
      if (selfTest()) {
        beep(1800, 60);
        Serial.println(F("self-test OK - press ARM"));
        enterState(ST_DISARMED);
      } else {
        enterState(ST_FAULT);
      }
      break;

    case ST_DISARMED:
      coast();
      digitalWrite(PIN_LED, (nowMs / 500) % 2);   // slow blink
      if (startPressed) {
        beep(1200, 80);
        Serial.println(F("ARMED - 3 s"));
        enterState(ST_ARMED);
      }
      break;

    case ST_ARMED: {
      coast();
      const uint32_t held = nowMs - stateEnteredMs;
      digitalWrite(PIN_LED, (nowMs / 150) % 2);   // fast blink
      if (held >= 3000) {
        /* Reset the controller so the run starts from a clean state. */
        integral = 0; prevError = 0; filteredD = 0; lastKappa = 0;
        vCmd = 0; kappaCmd = 0; firstStep = true;
        lostMs = 0; distanceM = 0; vPeak = 0;
        lapMs = nowMs;
        beep(2200, 120);
        Serial.println(F("GO"));
        enterState(ST_RACING);
      }
      break;
    }

    case ST_RACING:
      digitalWrite(PIN_LED, HIGH);
      controlStep(dt);
      /* A press of the ARM button during a run is a soft abort. It is a
       * convenience for testing only - the hardware E-Stop is the
       * mechanism that satisfies the competition rule. */
      if (startPressed) {
        Serial.println(F("soft abort"));
        coast();
        enterState(ST_DISARMED);
      }
      break;

    case ST_FAULT:
      coast();
      digitalWrite(PIN_LED, (nowMs / 100) % 2);   // urgent blink
      if (startPressed) {
        lostMs = 0;
        enterState(ST_DISARMED);
      }
      break;
  }

  /* Telemetry. Serial is output-only - nothing is ever read from it, so
   * it cannot become a control channel. */
  if (nowMs - lastTelemMs >= TELEMETRY_PERIOD_MS) {
    lastTelemMs = nowMs;
    const float radius = (fabsf(kappaCmd) > 1e-4f) ? 1.0f / fabsf(kappaCmd)
                                                   : 0.0f;
    Serial.print(F("st ")); Serial.print((int)state);
    Serial.print(F(" | v ")); Serial.print(vCmd, 2);
    Serial.print(F(" m/s | k ")); Serial.print(kappaCmd, 2);
    Serial.print(F(" 1/m | R ")); Serial.print(radius * 1000.0f, 0);
    Serial.print(F(" mm | d ")); Serial.print(distanceM, 2);
    Serial.print(F(" m | peak ")); Serial.println(vPeak, 2);
  }
}
