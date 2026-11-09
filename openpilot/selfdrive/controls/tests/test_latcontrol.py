import math
from dataclasses import replace
from types import SimpleNamespace

import numpy as np

from openpilot.common.test import OpenpilotTestCase
from openpilot.common.parameterized import parameterized

from openpilot.cereal import log
from opendbc.car.structs import car
from opendbc.car.car_helpers import interfaces
from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.toyota.values import CAR as TOYOTA
from opendbc.car.nissan.values import CAR as NISSAN
from opendbc.car.gm.values import CAR as GM
from opendbc.car.volkswagen.values import CAR as VOLKSWAGEN
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle
from openpilot.selfdrive.controls.lib.latcontrol_curvature import LatControlCurvature
from openpilot.selfdrive.controls.lib.latcontrol_torque import KP_INTERP
from openpilot.selfdrive.controls.lib.latcontrol_steer import FEEDBACK_NM_PER_ACCEL, KP_SCALE
from openpilot.selfdrive.controls.lib.latcontrol_steer import DRIVER_STEER_HOLD, DRIVER_TORQUE_FRICTION, FRICTION_RATE_WIDTH, LatControlSteer, \
  SLOPE_GAIN, SLOPE_SCALE_MIN, STEER_LIMITED_LAG, TANH_SLEW_SHARE, TUNE_RAMP, TUNED_VERSION_BIT, YAW_CORRECTION_MAX, shipped_tune
from openpilot.selfdrive.controls.controlsd import Controls


class TestLatControl(OpenpilotTestCase):

  @parameterized.expand([(HONDA.HONDA_CIVIC, LatControlPID), (TOYOTA.TOYOTA_RAV4, LatControlTorque),
                         (NISSAN.NISSAN_LEAF, LatControlAngle), (GM.CHEVROLET_BOLT_EUV, LatControlTorque),
                         (VOLKSWAGEN.VOLKSWAGEN_ID4_MK2, LatControlCurvature),
                         (GM.CHEVROLET_VOLT, LatControlSteer)])
  def test_saturation(self, car_name, controller):
    CarInterface = interfaces[car_name]
    CP = CarInterface.get_non_essential_params(car_name)
    CI = CarInterface(CP)
    VM = VehicleModel(CP)

    controller = controller(CP.as_reader(), CI, DT_CTRL)

    CS = car.CarState.new_message()
    CS.vEgo = 30
    CS.steeringPressed = False

    params = log.VehicleParameters.new_message()

    # Saturate for curvature limited and controller limited
    for _ in range(1000):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 0, True, 0.2)
    assert lac_log.saturated

    for _ in range(1000):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 0, False, 0.2)
    assert not lac_log.saturated

    for _ in range(1000):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 1, False, 0.2)
    assert lac_log.saturated

  def test_steer_yaw_correction_without_gyro(self):
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    controller = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
    CS = car.CarState.new_message()
    CS.vEgo = 20
    params = log.VehicleParameters.new_message()

    # a gyro reading far from what the steering angle implies: the correction saturates at its bound
    controller.update_yaw_rate(0.2)
    for _ in range(1000):
      controller.update(True, CS, VM, params, False, 0, False, 0.2)
    held = controller.yaw_correction.x
    assert abs(abs(held) * CS.vEgo ** 2 - YAW_CORRECTION_MAX) < 1e-6

    # gyro invalid: the correction holds instead of integrating the stale reading
    controller.update_yaw_rate(None)
    for _ in range(1000):
      controller.update(True, CS, VM, params, False, 0, False, 0.2)
    assert controller.yaw_correction.x == held


  def test_steer_no_windup_when_saturated(self):
    # a tight corner the torque budget can't hold: the feedforward alone asks for more than steer_max_nm, while the car
    # follows the path almost as asked (a small error). The PID sees the feedforward, so its integrator holds rather
    # than winding up behind the clipped output, which would overshoot the corner exit
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    controller = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
    CS = car.CarState.new_message()
    CS.vEgo = 12
    # Adverse road roll makes the feedforward exceed even the new 4 Nm budget.
    params = log.VehicleParameters.new_message(roll=0.1)
    CS.steeringAngleDeg = math.degrees(VM.get_steer_from_curvature(0.045, CS.vEgo, params.roll))  # asked for 0.05 (left)
    for _ in range(500):
      output, _, lac_log = controller.update(True, CS, VM, params, False, -0.05, False, 0.2)
    assert output == controller.steer_max and lac_log.saturated
    assert abs(controller.pid.i) < 0.05

  def test_four_nm_preserves_unsaturated_physical_torque(self):
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    new = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
    old = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
    old.model = replace(old.model, steer_max_nm=3.)
    old.pid.set_limits(3. / FEEDBACK_NM_PER_ACCEL, -3. / FEEDBACK_NM_PER_ACCEL)
    params = log.VehicleParameters.new_message()
    for speed in (1., 10., 30.):
      CS = car.CarState.new_message(vEgo=speed)
      for curvature in (-.0002, 0., .0002):
        for _ in range(100):
          before, _, _ = old.update(True, CS, VM, params, False, curvature, False, .1)
          after, _, _ = new.update(True, CS, VM, params, False, curvature, False, .1)
          assert abs(before) < .95
          assert abs(before * 3. - after * 4.) < 1e-9

  def test_steer_tanh_terms_slew_limited(self):
    # a step in the planned curvature at highway speed: the centering and friction terms follow at their share of the
    # EPS slew while active, and track at once while inactive so engaging doesn't start from a stale value
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    controller = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
    m = controller.model
    CS = car.CarState.new_message()
    CS.vEgo = 29
    params = log.VehicleParameters.new_message()
    max_step = TANH_SLEW_SHARE * float(np.interp(CS.vEgo, m.eps_slew_bp, m.eps_slew_v)) * DT_CTRL

    for _ in range(100):
      controller.update(True, CS, VM, params, False, 0, False, 0.2)
    prev, steps = controller.tanh_ff, []
    for _ in range(100):
      controller.update(True, CS, VM, params, False, -0.003, False, 0.2)
      steps.append(controller.tanh_ff - prev)
      prev = controller.tanh_ff
    assert max(abs(s) for s in steps) <= max_step + 1e-9
    assert sum(abs(s) > max_step - 1e-9 for s in steps) > 5  # the step asked for more: the limit bound

    controller.update(False, CS, VM, params, False, 0.003, False, 0.2)
    angle = math.degrees(VM.get_steer_from_curvature(-0.003, CS.vEgo, 0.))
    expected = m.Kc * math.tanh((angle - m.thc) / m.wc) + m.Fc * math.tanh(controller.rate_desired.x / FRICTION_RATE_WIDTH)
    assert abs(controller.tanh_ff - expected) < 1e-9

  def test_steer_aligning_torque_saturates(self):
    # the feedforward's aligning torque is near linear in gentle curves and falls short of linear as the tires saturate
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    aligning = {}
    for lat_accel in (0.3, 3.0):
      controller = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
      m = controller.model
      CS = car.CarState.new_message()
      CS.vEgo = 20
      curvature = -lat_accel / CS.vEgo ** 2  # left
      CS.steeringAngleDeg = math.degrees(VM.get_steer_from_curvature(-curvature, CS.vEgo, 0.))
      params = log.VehicleParameters.new_message()
      for _ in range(300):
        _, _, lac_log = controller.update(True, CS, VM, params, False, curvature, False, 0.2)
      aligning[lat_accel] = lac_log.f * m.steer_max_nm - m.c - controller.tanh_ff
    assert abs(aligning[0.3] / (m.k_la * 0.3) - 1) < 0.01
    assert 0.7 < aligning[3.0] / (m.k_la * 3.0) < 0.8

  def test_steer_limited_threshold(self):
    # carOutput trails the command: a command moving at the EPS slew isn't limited by the car until carOutput falls
    # further behind than the lag explains
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    controller = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
    m = controller.model
    for v in (5., 20., 30., 45.):
      slew = float(np.interp(v, m.eps_slew_bp, m.eps_slew_v)) / m.steer_max_nm  # per s, in the command's units
      threshold = controller.steer_limited_threshold(v)
      assert slew * STEER_LIMITED_LAG < threshold < slew * 3 * STEER_LIMITED_LAG + 0.01
    assert controller.steer_limited_threshold(45.) < controller.steer_limited_threshold(5.) < 0.1

  def _tight_right_turn(self, steer_more):
    # 9 mph, planned right curvature 0.1 (openpilot convention, right positive); the wheel is turned steer_more of the
    # plan's angle, the driver holding it right
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    controller = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
    CS = car.CarState.new_message()
    CS.vEgo = 4.0
    CS.steeringAngleDeg = math.degrees(VM.get_steer_from_curvature(-0.1 * steer_more, CS.vEgo, 0.))
    CS.steeringTorque = -2.0
    return controller, CS, VM, log.VehicleParameters.new_message()

  def test_steer_feedback_doesnt_fight_the_driver(self):
    # the driver turns in tighter than the plan (route 0000004a): the feedback would steer left against them, at the
    # steep low speed gain. Pressed, it gets the highway gain
    controller, CS, VM, params = self._tight_right_turn(1.3)
    for _ in range(100):
      unpressed, _, lac_log = controller.update(True, CS, VM, params, False, 0.1, False, 0.2)
    assert lac_log.p > 1.0  # left, against the turn
    p_unpressed, error = lac_log.p, abs(lac_log.error)
    CS.steeringPressed = True
    for _ in range(10):
      pressed, _, lac_log = controller.update(True, CS, VM, params, False, 0.1, False, 0.2)
    assert abs(lac_log.p - KP_SCALE * KP_INTERP[-1] * error) < 1e-3 and lac_log.p < 0.1 * p_unpressed
    assert pressed < unpressed and pressed < 0.  # the feedforward still turns right

    # it still holds off while the pressed flag drops for a moment mid-turn, and comes back after DRIVER_STEER_HOLD
    CS.steeringPressed = False
    for _ in range(round(0.5 * DRIVER_STEER_HOLD / DT_CTRL)):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 0.1, False, 0.2)
    assert lac_log.p < 0.1 * p_unpressed
    for _ in range(round(0.6 * DRIVER_STEER_HOLD / DT_CTRL)):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 0.1, False, 0.2)
    assert lac_log.p > 1.0

  def test_steer_feedback_helps_the_driver(self):
    # the driver steering right while the car turns less than the plan: feedback that agrees with them stays
    controller, CS, VM, params = self._tight_right_turn(0.7)
    CS.steeringPressed = True
    for _ in range(100):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 0.1, False, 0.2)
    assert lac_log.p < -1.0
    assert controller.pid.i == 0.0  # the integrator stays frozen while the driver steers

  def test_steer_driver_hand_at_highway_speed_unchanged(self):
    # at highway speed the gain is the highway gain already: a hand on the wheel changes nothing
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    outputs = []
    for pressed in (False, True):
      controller = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
      CS = car.CarState.new_message()
      CS.vEgo, CS.steeringTorque, CS.steeringPressed = 30., 1.2, pressed
      CS.steeringAngleDeg = math.degrees(VM.get_steer_from_curvature(0.001, CS.vEgo, 0.))  # a little left of the plan
      params = log.VehicleParameters.new_message()
      for _ in range(50):
        output, _, lac_log = controller.update(True, CS, VM, params, False, 0., False, 0.2)
      outputs.append((output, lac_log.p))
    assert abs(outputs[0][1] - outputs[1][1]) < 1e-9 and outputs[0][1] < 0.

  def _driver_holds_wheel(self, v, driver_torque, driver_model):
    # straight plan, the driver holding the wheel left with driver_torque, and the wheel where the column model says
    # that torque puts it (past the friction, against the column's stiffness)
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    controller = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL, driver_model=driver_model)
    past_friction = max(driver_torque - DRIVER_TORQUE_FRICTION, 0.)
    lat_accel = 0.
    for _ in range(20):
      angle = math.degrees(VM.get_steer_from_curvature(lat_accel / v ** 2, v, 0.))
      lat_accel = past_friction / controller.column_stiffness(VM, v, angle, lat_accel)
    CS = car.CarState.new_message()
    CS.vEgo, CS.steeringTorque, CS.steeringAngleDeg = v, driver_torque, angle
    params = log.VehicleParameters.new_message()
    for _ in range(300):
      output, _, lac_log = controller.update(True, CS, VM, params, False, 0., False, 0.2)
    return output, lac_log, lat_accel

  def test_steer_driver_model_doesnt_fight_the_driver(self):
    # where the wheel is the driver's doing, the driver model leaves the feedback nothing to correct; without it the
    # feedback pushes back (the driver's 0.8 Nm isn't steeringPressed)
    for v in (4., 15., 30.):
      _, with_model, lat_accel = self._driver_holds_wheel(v, 0.8, True)
      _, without, _ = self._driver_holds_wheel(v, 0.8, False)
      assert lat_accel > 0.1
      assert abs(with_model.p) < 0.02 and abs(with_model.error) < 0.01
      assert without.p < -0.05  # right, against the driver
      assert with_model.version == 2 and without.version == 0

  def test_steer_driver_model_resting_hand(self):
    # a hand resting inside the column friction moves nothing: the feedback corrects as before
    outputs = [self._driver_holds_wheel(20., 0.15, driver_model)[0] for driver_model in (True, False)]
    assert abs(outputs[0] - outputs[1]) < 1e-9

  def _steer_off_center(self, controller=None):
    # 30 m/s on a straight plan, the car 0.3 m/s^2 left of it: the feedback and the offset both work
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    controller = controller or LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
    CS = car.CarState.new_message()
    CS.vEgo = 30.
    CS.steeringAngleDeg = math.degrees(VM.get_steer_from_curvature(0.3 / CS.vEgo ** 2, CS.vEgo, 0.))
    params = log.VehicleParameters.new_message()
    def run(frames):
      outputs = []
      for _ in range(frames):
        output, _, lac_log = controller.update(True, CS, VM, params, False, 0., False, 0.2)
        outputs.append(output)
      return outputs, lac_log
    return controller, run

  def test_steer_tune_blends_in_and_out(self):
    # LateralTune: overrides held to their ranges, anything else ignored, blended in over TUNE_RAMP without a torque
    # step, and a reset blends back to exactly the shipped controller
    controller, run = self._steer_off_center()
    shipped = shipped_tune(controller.base_model)
    _, lac_log = run(200)
    assert lac_log.version == 0
    applied = controller.set_tune({'kp_scale': 5., 'c': -1.2, 'bogus': 1., 'ki': 'x', 'Fc': float('nan'), 'k_la': True})
    assert applied == {'kp_scale': 2.0, 'c': -1.0}

    half = round(TUNE_RAMP / 2 / DT_CTRL)
    first, _ = run(half)
    assert abs(controller.pid.k_p - 1.5 * KP_SCALE * KP_INTERP[-1]) < 1e-6 and abs(controller.model.c - (shipped['c'] - 1.0) / 2) < 1e-6
    second, lac_log = run(half)
    assert abs(controller.pid.k_p - 2.0 * KP_SCALE * KP_INTERP[-1]) < 1e-9 and controller.model.c == -1.0 and controller.model.Fc == shipped['Fc']
    assert lac_log.version == TUNED_VERSION_BIT
    steps = np.abs(np.diff(first + second))
    # both push right (the car is left of the plan): the torque moved a lot, a little at a time
    assert first[0] - second[-1] > 0.15 and max(steps) < 0.003

    assert controller.set_tune({}) == {}
    _, lac_log = run(2 * half)
    assert controller.tune_values() == shipped and controller.model == controller.base_model and lac_log.version == 0

  def test_steer_tune_shipped_unchanged(self):
    # no overrides: the same torque as a controller that never saw LateralTune
    outputs = []
    for tune in (None, {}):
      controller, run = self._steer_off_center()
      if tune is not None:
        controller.set_tune(tune)
      outputs.append(run(500)[0])
    assert outputs[0] == outputs[1]

  def test_controlsd_lateral_tune(self):
    # controlsd hands each new LateralTune to the controller once, and a param it can't use leaves the last tune in place
    controller, _ = self._steer_off_center()
    stub = SimpleNamespace(LaC=controller, lateral_tune=None, params=SimpleNamespace(get=lambda key: {'kp_scale': 1.5}))
    Controls.update_lateral_tune(stub)
    assert controller.tune_to['kp_scale'] == 1.5 and stub.lateral_tune == {'kp_scale': 1.5}
    controller.tune_frames = controller.tune_ramp_frames  # blended in: the same tune again doesn't restart the blend
    Controls.update_lateral_tune(stub)
    assert controller.tune_frames == controller.tune_ramp_frames

    def broken(key):
      raise ValueError("bad JSON")
    stub.params.get = broken
    Controls.update_lateral_tune(stub)
    assert controller.tune_to['kp_scale'] == 1.5

  def test_steer_slope_scale(self):
    # with slope_gain the feedback follows the column's slope against straight ahead: SLOPE_GAIN by default, 0 turns it
    # off, unchanged on a straight, weaker in a curve where the centering tanh is flat, to the power slope_gain, never
    # below SLOPE_SCALE_MIN
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    c = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
    assert c.slope_gain == SLOPE_GAIN > 0 and c.slope_scale(VM, 10., 30., 1.5) < 1.0
    c._apply_tune({**c.tune_shipped, 'slope_gain': 0.0})
    assert c.slope_scale(VM, 10., 30., 1.5) == 1.0
    c._apply_tune({**c.tune_shipped, 'slope_gain': 1.0})
    assert abs(c.slope_scale(VM, 10., 0., 0.) - 1.0) < 0.02
    ratio = c.column_stiffness(VM, 10., 30., 1.5) / c.column_stiffness(VM, 10., c.model.thc, 0.)
    assert ratio < 0.5 and abs(c.slope_scale(VM, 10., 30., 1.5) - ratio) < 1e-9
    assert c.slope_scale(VM, 3., 300., 2.5) == SLOPE_SCALE_MIN
    c._apply_tune({**c.tune_shipped, 'slope_gain': 0.7})
    assert abs(c.slope_scale(VM, 10., 30., 1.5) - ratio ** 0.7) < 1e-9

  def test_steer_slope_scale_scales_the_feedback(self):
    # in a steady curve with the car off the plan, P with slope_gain is P without it times the slope scale
    CarInterface = interfaces[GM.CHEVROLET_VOLT]
    CP = CarInterface.get_non_essential_params(GM.CHEVROLET_VOLT)
    VM = VehicleModel(CP)
    p = {}
    for gain in (0.0, 0.7):
      c = LatControlSteer(CP.as_reader(), CarInterface(CP), DT_CTRL)
      c._apply_tune({**c.tune_shipped, 'slope_gain': gain})
      CS = car.CarState.new_message()
      CS.vEgo = 10.
      CS.steeringAngleDeg = math.degrees(VM.get_steer_from_curvature(0.012, CS.vEgo, 0.))  # left, 1.2 m/s^2
      params = log.VehicleParameters.new_message()
      for _ in range(50):
        _, _, lac_log = c.update(True, CS, VM, params, False, -0.015, False, 0.2)  # the plan asks for 1.5 m/s^2
      p[gain] = (lac_log.p, c.slope_scale(VM, CS.vEgo, CS.steeringAngleDeg, -lac_log.actualLateralAccel))
    assert p[0.7][1] < 0.9 and abs(p[0.7][0] - p[0.0][0] * p[0.7][1]) < 1e-6
