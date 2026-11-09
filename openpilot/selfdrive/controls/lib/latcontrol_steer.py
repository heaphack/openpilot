import math
import numpy as np
from collections import deque
from dataclasses import dataclass, replace

from openpilot.cereal import log
from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.pid import PIDController
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.controls.lib.latcontrol import LatControl
from openpilot.selfdrive.controls.lib.latcontrol_torque import INTERP_SPEEDS, KP_INTERP

# This controller commands the torque the steering column needs, from a model of the column identified from drives:
#
#   LKA torque = k_la * a_s * tanh(lateral accel / a_s)              tire aligning torque, saturating with grip
#              + k_roll * g * roll + c                               road roll, offset
#              + Kc * tanh((angle - thc) / wc)                       rack centering (geometry + EPS active return)
#              + b * steering rate + Fc * tanh(steering rate / w)    damping and friction
#
# The feedforward applies that model to the planned path, so the wheel gets the torque to turn in, overcome friction
# and hold against the centering torque without waiting for an error. Feedback is LatControlTorque's: a delay-aligned
# PID on lateral acceleration, converted to torque at FEEDBACK_NM_PER_ACCEL. The measured curvature comes from the
# steering angle through the vehicle model, corrected by the yaw rate for what the vehicle model gets wrong (its gain
# changes with speed and tires), compared after the angle -> yaw lag so corner entries don't look like under-steer.
#
# The centering and friction terms are steepest where the planned angle or rate crosses zero, and on a quick lane
# shift at highway speed they swing faster than the EPS slews. They get a share of the EPS slew, leaving the rest to
# the lateral accel term and the feedback. Slow changes, like holding against stiction in a curve, are not limited.
#
# While the driver steers, the feedback pushes against them no stiffer than its highway gain. The angle-based
# measurement follows the wheel at once, so a driver turning in ahead of the plan reads as over-steer, and at low speed
# the gain is steep (~20 per m/s^2 at 9 mph against 0.8 on the highway): in a tight right turn (route 0000004a) it swung
# the request between full left and full right every ~0.5 s, and the car controller's driver torque limit cut each half
# that opposed the driver, so the assist dropped in and out. At highway speed nothing changes, so a hand resting on the
# wheel (steeringPressed is only 1 Nm) still gets corrected as before. Feedback that agrees with the driver is untouched.
#
# With LateralDriverModel set, the driver's torque is part of the plant instead. It adds to ours 1:1 at the column (the
# column model, fit to our torque alone, predicts the driver's torque in manual driving). Past the column friction it
# moves the wheel until the column's stiffness takes it up, so the expected lateral accel moves by that much, lagged
# like the wheel, and the feedback only corrects what the driver's torque doesn't explain, at any speed. A resting
# hand, inside the friction, is corrected as before; a firmer one moves the car and openpilot doesn't push back (the
# plan still steers back to the lane). On routes 0c-4b the driver's torque this way explained 53-64% of the error the
# feedback saw while they steered.
#
# With SLOPE_GAIN above 0, the feedback goes through the column model's local slope, the way LatControlTorque sends its
# whole output through the car's torque_from_lateral_accel: what one m/s^2 of correction costs in torque depends on where
# the column is on its curve. Straight ahead the centering torque is steep, and steeper the slower the car goes (one m/s^2
# takes more steering angle); the P schedule is tuned there. In a curve, past ~10 deg of wheel, the centering tanh is flat
# and only the tires' aligning slope is left, so the same correction needs a fraction of the torque, and the same P is that
# much stronger. Relative to straight ahead at the same speed, so on a straight nothing changes, and to the power
# SLOPE_GAIN: the drives (curve_gain.py, routes 07-8c) show the car answering torque 1.8-2.2x more at 8-20 deg than
# straight, where the model's slope ratio is 2.5-3.4x, about its 0.7th power.

# Feedback gains, from the 2026-10-24 road trip. Measured on the drives (column torque -> the angle-based lateral accel the
# feedback sees, feedforward torque as the instrument), the loop with upstream's lateral accel P schedule has a gain of only
# 0.25-0.35 at 0.1 Hz on the highway (0.7-1.0 in town), and phase reaches -180 deg only at 3-4 Hz. A sweep on one drive (P x0.8
# to x1.4, base every round, 49 min) left the 10-30 s lane ping-pong unchanged at every P; x1.25 tracked best (lat accel error
# 0.087 vs 0.096) with the least busy torque (0.3-1.5 Hz 0.125 vs 0.136 Nm), and x1.4 got busier
KP_SCALE = 1.25  # x LatControlTorque's KP_INTERP, at every speed
# The integrator is for slow biases (crown, wind, alignment), which the drives show are small (0.014 Nm rms below 0.01 Hz at
# highway speed). Its own loop crosses over at KI x 0.91 m/s^2/Nm / 2 pi: ~46 s at 0.15, inside the slow edge of the 10-30 s
# ping-pong band, which argues for ~0.08 (~85 s). The road trip doesn't back that: over its 250 clean highway minutes (route
# fixed effects, road adjusted) 0.08 tracked 5.5 +- 3.6% worse with no lane swing gain, and on route 8a, against the same road
# driven that morning, 0.08 with P x1.25 had more error and swing than the shipped half. 0.3 made the ping-pong worse (route 76).
# Kept at 0.15 until a base-every-round A/B shows otherwise
KI = 0.15
FEEDBACK_NM_PER_ACCEL = 1.0  # the aligning stiffness the feedback gains were tuned with (k_la before the tire saturation)
YAW_LAG = 0.12          # s, steering angle -> deviceMotion yaw (tire relaxation, yaw dynamics, sensor)
YAW_CORRECTION_TAU = 1.0
YAW_MIN_SPEED = 5.0
YAW_CORRECTION_MAX = 0.5  # m/s^2, ~5x what the drives needed: bounds a biased or failing gyro
RATE_FILTER_TAU = 0.2
FRICTION_RATE_WIDTH = 3.0  # deg/s
TANH_SLEW_SHARE = 0.5  # of the EPS slew, for the centering and friction terms
DRIVER_STEER_HOLD = 1.0  # s the driver counts as steering after steeringPressed drops (it drops below 1 Nm mid-turn)
STEER_LIMITED_LAG = 0.03  # s carOutput can trail carControl: the Volt sends every other frame, card runs a frame behind
DRIVER_TORQUE_FRICTION = 0.2  # Nm of the driver's torque the column friction takes before the wheel moves
DRIVER_RESPONSE_TAU = 0.2  # s, driver torque -> wheel and lateral accel
SLOPE_GAIN = 0.7  # power of the column slope ratio the feedback follows (0: off; 0.7 matches the drives; LateralTune slope_gain)
SLOPE_SCALE_MIN = 0.1  # the least the feedback is scaled to in a curve

# Live tuning on a tuning drive (the LateralTune param, set with tools/lateral_tune.py): these knobs, held to these
# ranges, blend in over TUNE_RAMP from the values in use, so a change never steps the torque. k_la sets k_roll with it
# (road roll loads the tires like lateral accel). The EPS limits, the torque ceiling and the panda's checks stay as they are
TUNE_RAMP = 2.0  # s
TUNE_LIMITS = {
  'kp_scale': (0.5, 2.0),  # x the feedback's proportional gain at every speed
  'ki': (0.0, 0.5),
  'k_la': (0.7, 1.5),
  'c': (-1.0, -0.3),
  'Kc': (0.3, 0.9),
  'thc': (-1.5, 0.5),
  'Fc': (0.0, 0.7),
  'friction_rate_width': (1.0, 10.0),
  'tanh_slew_share': (0.2, 1.0),
  'slope_gain': (0.0, 1.0),  # see SLOPE_GAIN
}
TUNED_VERSION_BIT = 4  # set in torqueState.version while LateralTune differs from the shipped values


@dataclass(frozen=True)
class ColumnModel:
  k_la: float     # Nm per m/s^2
  a_s: float      # m/s^2, scale of the aligning torque saturation
  k_roll: float   # Nm per m/s^2 of g * roll
  c: float        # Nm
  Kc: float       # Nm
  wc: float       # deg
  thc: float      # deg
  b: float        # Nm per deg/s
  Fc: float       # Nm
  steer_max_nm: float
  eps_slew_bp: tuple[float, ...]  # m/s
  eps_slew_v: tuple[float, ...]   # Nm/s the EPS lets its LKA input change by


# identified from Volt drives: the torque the engaged, hands-off controller applied, against the feedforward's own inputs
# (planned lateral accel, planned steering angle and rate), on routes 0c-66 (2026-10), checked route by route. Road roll
# loads the tires like lateral accel, so k_roll = k_la; damping didn't show beyond the friction term, so b = 0. c also
# absorbs the roll bias of how the device is mounted, and thc moves with the alignment. The aligning torque falls below
# linear from ~1.5 m/s^2 (0.3 Nm short at 2-2.5, 1 Nm at 3-4), the same with the driver's torque doing the steering in
# manual driving, so it is the tires, not the controller; a_s fits both. The EPS slew is from its firmware (at a 100 Hz
# tick)
STEER_MODELS = {
  "CHEVROLET_VOLT": ColumnModel(k_la=1.10, a_s=3.0, k_roll=1.10, c=-0.644, Kc=0.605, wc=5.0, thc=-0.5, b=0.0, Fc=0.364,
                                 steer_max_nm=4.0, eps_slew_bp=(16.68, 50.03), eps_slew_v=(8.0, 2.4)),
}


def shipped_tune(model):
  """the TUNE_LIMITS knobs as shipped, for a car's column model"""
  return {'kp_scale': 1.0, 'ki': KI, 'k_la': model.k_la, 'c': model.c, 'Kc': model.Kc, 'thc': model.thc, 'Fc': model.Fc,
          'friction_rate_width': FRICTION_RATE_WIDTH, 'tanh_slew_share': TANH_SLEW_SHARE, 'slope_gain': SLOPE_GAIN}


class LatControlSteer(LatControl):
  def __init__(self, CP, CI, dt, driver_model=False):
    super().__init__(CP, CI, dt)
    self.base_model = STEER_MODELS[CP.carFingerprint]
    self.model = self.base_model
    self.driver_model = driver_model
    self.driver_torque = FirstOrderFilter(0.0, DRIVER_RESPONSE_TAU, dt)
    self.pid = PIDController([INTERP_SPEEDS, [k * KP_SCALE for k in KP_INTERP]], KI, rate=1 / dt)
    max_lat_accel = self.model.steer_max_nm / FEEDBACK_NM_PER_ACCEL
    self.pid.set_limits(max_lat_accel, -max_lat_accel)
    self.lat_accel_request_buffer = deque([0.] * int(1.0 / dt), maxlen=int(1.0 / dt))
    # desired curvature changes at the model's rate: differencing over a whole model period sees each step once,
    # where a per-frame difference spikes on every update and kicks the friction feedforward
    self.angle_desired_hist = deque(maxlen=round(DT_MDL / dt) + 1)
    self.rate_desired = FirstOrderFilter(0.0, RATE_FILTER_TAU, dt)
    self.tanh_ff = 0.0
    self.curvature_history = deque([0.] * int(YAW_LAG / dt + 1), maxlen=int(YAW_LAG / dt + 1))
    self.yaw_correction = FirstOrderFilter(0.0, YAW_CORRECTION_TAU, dt)
    self.yaw_rate = None
    self.driver_steer_time = DRIVER_STEER_HOLD  # since the driver last pressed the wheel
    self.driver_steer_dir = 0.
    self.kp_scale, self.ki = 1.0, KI
    self.friction_rate_width, self.tanh_slew_share = FRICTION_RATE_WIDTH, TANH_SLEW_SHARE
    self.slope_gain = SLOPE_GAIN
    self.tune_shipped = shipped_tune(self.base_model)
    self.tune_from = self.tune_to = self.tune_shipped
    self.tune_frames = self.tune_ramp_frames = max(round(TUNE_RAMP / dt), 1)  # into the blend, and its length

  def reset(self):
    super().reset()
    self.pid.reset()
    self.angle_desired_hist.clear()

  def update_yaw_rate(self, yaw_rate):
    """yaw rate [rad/s], left positive, or None while the sensor is invalid (the correction then holds)"""
    self.yaw_rate = yaw_rate

  def update_torque_parameters(self, latAccelFactor, latAccelOffset, friction):
    pass

  def tune_values(self):
    """the TUNE_LIMITS knobs as in use now, mid-blend included"""
    m = self.model
    return {'kp_scale': self.kp_scale, 'ki': self.ki, 'k_la': m.k_la, 'c': m.c, 'Kc': m.Kc, 'thc': m.thc, 'Fc': m.Fc,
            'friction_rate_width': self.friction_rate_width, 'tanh_slew_share': self.tanh_slew_share, 'slope_gain': self.slope_gain}

  @property
  def tuned(self):
    return self.tune_to != self.tune_shipped or self.tune_values() != self.tune_shipped

  def set_tune(self, tune):
    """LateralTune: {knob: value} overrides of the TUNE_LIMITS knobs, the rest as shipped. Values are held to their
    ranges, anything else is ignored, and the result blends in over TUNE_RAMP. Returns the overrides that apply"""
    target = dict(self.tune_shipped)
    for k, v in tune.items():
      if k in TUNE_LIMITS and isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
        target[k] = float(np.clip(v, *TUNE_LIMITS[k]))
    self.tune_from, self.tune_to, self.tune_frames = self.tune_values(), target, 0
    return {k: v for k, v in target.items() if v != self.tune_shipped[k]}

  def _apply_tune(self, values):
    m = self.base_model
    self.model = replace(m, k_la=values['k_la'], k_roll=m.k_roll * (values['k_la'] / m.k_la), c=values['c'], Kc=values['Kc'],
                         thc=values['thc'], Fc=values['Fc'])
    self.kp_scale, self.ki = values['kp_scale'], values['ki']
    # the integrator keeps what it has summed, so a new KI changes how fast it moves, not where it is
    self.pid._k_p = (INTERP_SPEEDS, [k * KP_SCALE * self.kp_scale for k in KP_INTERP])
    self.pid._k_i = ([0.], [self.ki])
    self.friction_rate_width, self.tanh_slew_share = values['friction_rate_width'], values['tanh_slew_share']
    self.slope_gain = values['slope_gain']

  def steer_limited_threshold(self, v):
    """how far carOutput's torque may be from this frame's command before the car limited it: what the command can move,
    at the EPS slew, in the time carOutput trails it. At upstream's 0.01 the lag alone held the integrator 61% of engaged
    time, where the car really limited the command 2%"""
    m = self.model
    return float(np.interp(v, m.eps_slew_bp, m.eps_slew_v)) * STEER_LIMITED_LAG / m.steer_max_nm + 0.01

  def column_stiffness(self, VM, v, angle, lateral_accel):
    """Nm of column torque per m/s^2 of lateral accel here: the tires' aligning torque, and the rack centering over the
    steering angle that lateral accel takes at this speed"""
    m = self.model
    u = max(v, 1.)
    deg_per_accel = math.degrees(VM.get_steer_from_curvature(1. / u ** 2, u, 0.))
    return m.k_la / math.cosh(lateral_accel / m.a_s) ** 2 + m.Kc / m.wc / math.cosh((angle - m.thc) / m.wc) ** 2 * deg_per_accel

  def slope_scale(self, VM, v, angle, lateral_accel):
    """what the feedback is scaled by here: the column's slope against straight ahead at this speed, to the power slope_gain"""
    if self.slope_gain <= 0.:
      return 1.
    ratio = self.column_stiffness(VM, v, angle, lateral_accel) / self.column_stiffness(VM, v, self.model.thc, 0.)
    return max(min(ratio, 1.) ** self.slope_gain, SLOPE_SCALE_MIN)

  def measured_curvature(self, CS, VM, params):
    """left positive: angle-based curvature, corrected by the yaw rate"""
    curvature = VM.calc_curvature(math.radians(CS.steeringAngleDeg - params.angleOffsetDeg), CS.vEgo, params.roll)
    self.curvature_history.append(curvature)
    if self.yaw_rate is not None and CS.vEgo > YAW_MIN_SPEED:
      self.yaw_correction.update(self.yaw_rate / CS.vEgo - self.curvature_history[0])
      max_correction = YAW_CORRECTION_MAX / CS.vEgo ** 2
      self.yaw_correction.x = float(np.clip(self.yaw_correction.x, -max_correction, max_correction))
    return curvature + self.yaw_correction.x

  def update(self, active, CS, VM, params, steer_limited_by_safety, desired_curvature, curvature_limited, lat_delay):
    if self.tune_frames < self.tune_ramp_frames:
      self.tune_frames += 1
      w = self.tune_frames / self.tune_ramp_frames
      self._apply_tune({k: a + w * (self.tune_to[k] - a) for k, a in self.tune_from.items()} if w < 1. else self.tune_to)
    m = self.model
    pid_log = log.ControlsState.LateralTorqueState.new_message()
    v = CS.vEgo
    desired_curvature_left = -desired_curvature
    desired_lateral_accel = desired_curvature_left * v ** 2
    self.lat_accel_request_buffer.append(desired_lateral_accel)
    delay_frames = int(np.clip(lat_delay / self.dt + 1, 1, len(self.lat_accel_request_buffer)))
    expected_lateral_accel = self.lat_accel_request_buffer[-delay_frames]
    measured_lateral_accel = self.measured_curvature(CS, VM, params) * v ** 2
    if self.driver_model:
      # the driver's torque past the column friction, as the wheel and the car follow it (left positive like ours)
      self.driver_torque.update(math.copysign(max(abs(CS.steeringTorque) - DRIVER_TORQUE_FRICTION, 0.), CS.steeringTorque))
      expected_lateral_accel += self.driver_torque.x / self.column_stiffness(VM, v, CS.steeringAngleDeg, measured_lateral_accel)
    error = expected_lateral_accel - measured_lateral_accel

    angle_desired = math.degrees(VM.get_steer_from_curvature(desired_curvature_left, v, params.roll)) + params.angleOffsetDeg
    self.angle_desired_hist.append(angle_desired)
    h = self.angle_desired_hist
    rate = (h[-1] - h[0]) / ((len(h) - 1) * self.dt) if len(h) > 1 else 0.0
    rate_desired = self.rate_desired.update(rate)

    tanh_ff = m.Kc * math.tanh((angle_desired - m.thc) / m.wc) + m.Fc * math.tanh(rate_desired / self.friction_rate_width)
    if active:
      max_step = self.tanh_slew_share * float(np.interp(v, m.eps_slew_bp, m.eps_slew_v)) * self.dt
      self.tanh_ff += float(np.clip(tanh_ff - self.tanh_ff, -max_step, max_step))
    else:
      self.tanh_ff = tanh_ff
    ff = (m.k_la * m.a_s * math.tanh(desired_lateral_accel / m.a_s) + m.k_roll * ACCELERATION_DUE_TO_GRAVITY * params.roll + m.c +
          m.b * rate_desired + self.tanh_ff)

    # the direction the driver steers (their torque, left positive like ours), for DRIVER_STEER_HOLD after a press
    if CS.steeringPressed:
      self.driver_steer_time, self.driver_steer_dir = 0., float(np.sign(CS.steeringTorque))
    else:
      self.driver_steer_time = min(self.driver_steer_time + self.dt, DRIVER_STEER_HOLD)
    driver_steering = self.driver_steer_time < DRIVER_STEER_HOLD
    if not self.driver_model and driver_steering and error * self.driver_steer_dir < 0.:
      error *= KP_INTERP[-1] / float(np.interp(v, INTERP_SPEEDS, KP_INTERP))
    error *= self.slope_scale(VM, v, CS.steeringAngleDeg, measured_lateral_accel)

    if not active:
      output_torque = 0.0
      pid_log.active = False
    else:
      freeze_integrator = steer_limited_by_safety or driver_steering or v < 5
      # the physics feedforward goes through the PID, in its lateral accel units, so the PID's anti-windup holds the
      # integrator while feedforward and feedback together saturate the torque budget
      control = self.pid.update(error, speed=v, feedforward=ff / FEEDBACK_NM_PER_ACCEL, freeze_integrator=freeze_integrator)
      output_torque = float(np.clip(FEEDBACK_NM_PER_ACCEL * control / m.steer_max_nm, -self.steer_max, self.steer_max))

      pid_log.active = True
      # which way the driver was handled, and whether LateralTune was on, for A/B drives
      pid_log.version = (2 if self.driver_model else 0) | (TUNED_VERSION_BIT if self.tuned else 0)
      pid_log.p = float(self.pid.p)
      pid_log.i = float(self.pid.i)
      pid_log.d = float(self.pid.d)
      pid_log.f = float(ff / m.steer_max_nm)
      pid_log.output = output_torque
      # logged in openpilot's curvature convention (right positive), like LatControlTorque
      pid_log.error = float(-error)
      pid_log.actualLateralAccel = float(-measured_lateral_accel)
      pid_log.desiredLateralAccel = float(-expected_lateral_accel)
      pid_log.saturated = bool(self._check_saturation(self.steer_max - abs(output_torque) < 1e-3, CS, steer_limited_by_safety, curvature_limited))

    return output_torque, 0.0, pid_log
