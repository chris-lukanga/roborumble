#include <webots/Robot.hpp>
#include <webots/Motor.hpp>
#include <webots/DistanceSensor.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>

using namespace webots;

// ===================== e-puck physical constants =========================
static const double WHEEL_RADIUS    = 0.0205;   // m
static const double AXLE_LENGTH     = 0.052;    // m, wheel separation
static const double MAX_WHEEL_OMEGA = 6.28;     // rad/s, motor limit
static const double V_MAX = WHEEL_RADIUS * MAX_WHEEL_OMEGA;   // 0.1287 m/s

// ===================== Track / sensing ===================================
static const double THRESHOLD = 600.0;   // below = on the line (floor ~860, line ~300)

// +1.0 is the sign confirmed working on your setup. This replaces the old
// INVERT_STEERING = true. Use -1.0 if you ever change the sensor wiring.
static const double STEERING_SIGN = +1.0;

// ===================== Speed policy (m/s) ================================
// Ceilings computed from the kinematics: 12.9 cm/s flat out, 9.6 cm/s is
// the most the 76 mm corner on track_circuit.png allows before the outer
// wheel saturates. Leaving a little margin for tracking error.
static const double V_STRAIGHT = 0.120;
static const double V_FLOOR    = 0.045;   // never crawl slower than this
static const double CORNER_SLOW = 0.060;  // how hard to brake for curvature

// ===================== Steering (path curvature, 1/m) ====================
// error is one of -1, -0.5, 0, +0.5, +1. At error = 0.5 (centre + one outer
// sensor on the line, i.e. normal cornering) this asks for 1/13 = 77 mm
// radius, which matches the tightest corner on the circuit.
static const double K_P       = 26.0;
static const double K_D       = 1.1;
static const double KAPPA_MAX = 18.0;     // 1/m, ~56 mm radius
static const double D_ALPHA   = 0.30;

// ===================== Rate limits =======================================
// The motors could slam to full speed in 19 ms, which would make the
// commanded curvature jump around with the discrete sensor states. These
// limits are about smooth tracking, not about faking motor weakness.
static const double MAX_LIN_ACCEL  = 0.80;   // m/s^2
static const double MAX_KAPPA_RATE = 110.0;  // (1/m) per second

// ===================== Line loss =========================================
static const double RECOVER_SPEED = 0.055;   // m/s, always forward
static const double RECOVER_KAPPA = 9.0;     // 1/m, ~110 mm radius
static const int    LOST_TIMEOUT_MS = 2500;

static const bool DIAGNOSTIC_MODE = false;
static const int  REPORT_MS = 2000;

static double clampd(double v, double lo, double hi) {
  return v < lo ? lo : (v > hi ? hi : v);
}

static double slew(double target, double current, double maxRate, double dt) {
  const double lim = maxRate * dt;
  return current + clampd(target - current, -lim, lim);
}

int main(int argc, char **argv) {
  Robot *robot = new Robot();
  const int timeStep = (int)robot->getBasicTimeStep();
  const double dt = timeStep / 1000.0;

  Motor *leftMotor  = robot->getMotor("left wheel motor");
  Motor *rightMotor = robot->getMotor("right wheel motor");
  leftMotor->setPosition(INFINITY);
  rightMotor->setPosition(INFINITY);
  leftMotor->setVelocity(0.0);
  rightMotor->setVelocity(0.0);

  const char *names[3] = {"gs0", "gs1", "gs2"};
  DistanceSensor *gs[3];
  for (int i = 0; i < 3; i++) {
    gs[i] = robot->getDistanceSensor(names[i]);
    gs[i]->enable(timeStep);
  }

  printf("control period %d ms | top speed %.1f cm/s | %.1f mm travelled per step\n",
         timeStep, V_MAX * 100.0, V_MAX * dt * 1000.0);
  fflush(stdout);

  double vCmd = 0.0, kappaCmd = 0.0;
  double previousError = 0.0, filteredD = 0.0;
  double lastKappa = 0.0;
  int    lostMs = 0, reportMs = 0;
  bool   stopped = false, everSawLine = false, firstStep = true;
  double distance = 0.0, elapsed = 0.0;
  double vPeak = 0.0;

  while (robot->step(timeStep) != -1) {
    const double v0 = gs[0]->getValue();
    const double v1 = gs[1]->getValue();
    const double v2 = gs[2]->getValue();

    const double a = (v0 < THRESHOLD) ? 1.0 : 0.0;
    const double c = (v1 < THRESHOLD) ? 1.0 : 0.0;
    const double b = (v2 < THRESHOLD) ? 1.0 : 0.0;
    const double total = a + c + b;

    if (DIAGNOSTIC_MODE) {
      const double w = 0.04 / WHEEL_RADIUS;
      leftMotor->setVelocity(w);
      rightMotor->setVelocity(w);
      printf("gs0 %6.1f %s | gs1 %6.1f %s | gs2 %6.1f %s\n",
             v0, a > 0 ? "LINE" : "    ", v1, c > 0 ? "LINE" : "    ",
             v2, b > 0 ? "LINE" : "    ");
      fflush(stdout);
      continue;
    }

    double vTarget, kappaTarget;

    if (total > 0.0) {
      // ---------------- tracking ----------------
      everSawLine = true;
      lostMs = 0;
      stopped = false;

      const double error = (a - b) / total;
      if (firstStep) { previousError = error; firstStep = false; }

      const double rawD = (error - previousError) / dt;
      filteredD = D_ALPHA * rawD + (1.0 - D_ALPHA) * filteredD;
      previousError = error;

      kappaTarget = STEERING_SIGN * (K_P * error + K_D * filteredD);
      kappaTarget = clampd(kappaTarget, -KAPPA_MAX, KAPPA_MAX);
      lastKappa = kappaTarget;

      // Speed is chosen from the curvature we are about to demand, capped
      // by the point at which the outer wheel would saturate.
      const double vWheelLimit = V_MAX / (1.0 + std::fabs(kappaTarget) * AXLE_LENGTH / 2.0);
      const double vCurve      = V_STRAIGHT / (1.0 + CORNER_SLOW * std::fabs(kappaTarget));
      vTarget = std::max(V_FLOOR, std::min(V_STRAIGHT, std::min(vWheelLimit, vCurve)));

    } else {
      // ---------------- line lost ----------------
      lostMs += timeStep;
      if (lostMs > LOST_TIMEOUT_MS) {
        if (!stopped) {
          printf("LINE LOST -- stopped after %d ms.\n", LOST_TIMEOUT_MS);
          if (!everSawLine)
            printf("  Never saw the line at all -- check the start position "
                   "and the Floor tileSize.\n");
          fflush(stdout);
          stopped = true;
        }
        leftMotor->setVelocity(0.0);
        rightMotor->setVelocity(0.0);
        vCmd = 0.0;
        continue;
      }
      // Keep curving the way we were, slowly, always forward.
      kappaTarget = clampd(lastKappa, -RECOVER_KAPPA, RECOVER_KAPPA);
      vTarget = RECOVER_SPEED;
    }

    // ---------------- rate limiting ----------------
    kappaCmd = slew(kappaTarget, kappaCmd, MAX_KAPPA_RATE, dt);
    vCmd     = slew(vTarget,     vCmd,     MAX_LIN_ACCEL,  dt);

    // ---------------- differential drive kinematics ----------------
    // v_left  = v (1 - k b/2)
    // v_right = v (1 + k b/2)
    const double half = kappaCmd * AXLE_LENGTH / 2.0;
    double vl = vCmd * (1.0 - half);
    double vr = vCmd * (1.0 + half);

    double wl = vl / WHEEL_RADIUS;
    double wr = vr / WHEEL_RADIUS;

    // Scale both wheels together if saturated, so the path curvature is
    // preserved even if the speed cannot be.
    const double peak = std::max(std::fabs(wl), std::fabs(wr));
    if (peak > MAX_WHEEL_OMEGA) {
      const double s = MAX_WHEEL_OMEGA / peak;
      wl *= s; wr *= s;
    }

    leftMotor->setVelocity(wl);
    rightMotor->setVelocity(wr);

    const double vActual = (wl + wr) * 0.5 * WHEEL_RADIUS;
    distance += vActual * dt;
    elapsed  += dt;
    vPeak = std::max(vPeak, vActual);

    reportMs += timeStep;
    if (reportMs >= REPORT_MS) {
      reportMs = 0;
      const double R = (std::fabs(kappaCmd) > 1e-6) ? 1.0 / std::fabs(kappaCmd) : 0.0;
      printf("v %5.1f cm/s (peak %4.1f, mean %4.1f) | radius %6.1f mm | "
             "wheels %5.2f %5.2f rad/s | %.2f m covered\n",
             vActual * 100.0, vPeak * 100.0, distance / elapsed * 100.0,
             R * 1000.0, wl, wr, distance);
      fflush(stdout);
    }
  }

  delete robot;
  return 0;
}