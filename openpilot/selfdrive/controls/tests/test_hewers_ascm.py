"""Hewers' lateral controller through this fork's configuration and ASCM sender."""
import math
from types import SimpleNamespace
from unittest.mock import Mock, patch

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.ascm import AscmSupervisor
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_ascm import feed
from opendbc.car.gm.tests.test_volt_longitudinal import make_state
from opendbc.car.gm.values import CAR, DBC, CarControllerParams, GMFlags, GMSafetyFlags
from opendbc.safety.tests.libsafety.libsafety_py import libsafety, make_CANPacket
from openpilot.cereal import log
from openpilot.common.params import Params, ParamKeyFlag, ParamKeyType
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
from openpilot.selfdrive.controls.lib.latcontrol_steer import LatControlSteer
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque


class TestHewersAscm(OpenpilotTestCase):
  def make_controls(self, candidate=CAR.CHEVROLET_VOLT, baseline=False, driver_model=False, sm=None):
    cp = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], False, False, False)
    params = Params()
    params.put('CarParams', cp.to_bytes(), block=True)
    params.put_bool('LateralTorqueBaseline', baseline, block=True)
    params.put_bool('LateralDriverModel', driver_model, block=True)
    with patch('openpilot.selfdrive.controls.controlsd.messaging.SubMaster', return_value=sm or Mock()), \
         patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      controls = Controls()
    return controls, cp

  def test_controller_selection(self):
    for baseline, driver_model in ((False, False), (False, True), (True, False)):
      with self.subTest(baseline=baseline, driver_model=driver_model):
        controls, cp = self.make_controls(baseline=baseline, driver_model=driver_model)
        self.assertIsInstance(controls.LaC, LatControlTorque if baseline else LatControlSteer)
        if not baseline:
          self.assertEqual(controls.LaC.driver_model, driver_model)
        self.assertEqual(cp.lateralTuning.which(), 'torque')
        self.assertAlmostEqual(cp.lateralTuning.torque.latAccelOffset, -.40)
        self.assertAlmostEqual(cp.steerRatio, 16.5)
        self.assertAlmostEqual(cp.steerActuatorDelay, .1)
        self.assertTrue(cp.flags & GMFlags.ASCM_C11)
        self.assertTrue(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_C11)
        self.assertTrue(cp.autoResumeSng and cp.openpilotLongitudinalControl)
        self.assertEqual(list(cp.longitudinalTuning.kiBP), [5., 15.])
    controls, _ = self.make_controls(CAR.CADILLAC_ATS)
    self.assertIsInstance(controls.LaC, LatControlPID)
    controls, _ = self.make_controls(CAR.CHEVROLET_BOLT_EUV)
    self.assertIsInstance(controls.LaC, LatControlTorque)

  def test_native_tuning_parameters_and_clear_policy(self):
    params = Params()
    self.assertFalse(params.get_bool('LateralTorqueBaseline'))
    self.assertFalse(params.get_bool('LateralDriverModel'))
    self.assertEqual(params.get_type('LateralTune'), ParamKeyType.JSON)
    controls, _ = self.make_controls(driver_model=True)
    params.put('LateralTune', {'kp_scale': 1.2}, block=True)
    controls.update_lateral_tune()
    self.assertEqual(controls.LaC.tune_to['kp_scale'], 1.2)
    for flag in (ParamKeyFlag.CLEAR_ON_OFFROAD_TRANSITION, ParamKeyFlag.CLEAR_ON_MANAGER_START):
      params.put('LateralTune', {'kp_scale': 1.2}, block=True)
      params.clear_all(flag)
      self.assertIsNone(params.get('LateralTune'))
      self.assertTrue(params.get_bool('LateralDriverModel'))
    controls.update_lateral_tune()
    self.assertEqual(controls.LaC.tune_to, controls.LaC.tune_shipped)

  def test_volt_only_steering_limits_and_baseline_scaling(self):
    for candidate in CAR:
      cp = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], False, False, False)
      params = CarControllerParams(cp)
      volt = candidate == CAR.CHEVROLET_VOLT
      self.assertEqual(params.STEER_MAX, 400 if volt else 300)
      self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.VOLT_4NM), volt)
      if volt:
        self.assertEqual(cp.minSteerSpeed, 0.)
        self.assertFalse(cp.steerAtStandstill)
        ci = CarInterface(cp)
        to_torque = ci.torque_from_lateral_accel()
        from_torque = ci.lateral_accel_from_torque()
        for accel in (-3., -1., 0., 1., 3.):
          # Original 3 Nm calibration must request the same physical torque below saturation.
          original = math.copysign(1 / (1 + math.exp(-abs(1.75 * accel))) - .5, accel) + .191 * accel + .053
          torque = to_torque(accel, cp.lateralTuning.torque)
          self.assertAlmostEqual(torque * 400, original * 300, places=5)
          self.assertAlmostEqual(from_torque(torque, cp.lateralTuning.torque), accel, places=5)

  def test_controlsd_to_ascm_sender_and_panda(self):
    torque = self.run_controlsd_to_ascm_sender_and_panda(20., -.003)
    self.assertTrue(any(abs(t) > .05 for t in torque))

  def test_low_speed_steering_and_standstill(self):
    for speed in (0., .2, .31, 1., 3.):
      with self.subTest(speed=speed):
        torque = self.run_controlsd_to_ascm_sender_and_panda(speed, -.02)
        if speed <= .3:
          self.assertTrue(all(t == 0. for t in torque))
        else:
          self.assertTrue(any(abs(t) > 0. for t in torque))

  def test_four_nm_reaches_sender_and_panda_in_both_directions(self):
    for direction in (-1, 1):
      with self.subTest(direction=direction):
        torque = self.run_controlsd_to_ascm_sender_and_panda(10., -.05 * direction, active_frames=300)
        self.assertEqual(max(direction * t for t in torque), 1.)
        self.assertTrue(all(abs(t) <= 1. for t in torque))

  def run_controlsd_to_ascm_sender_and_panda(self, speed, curvature, active_frames=60):
    controls, cp = self.make_controls()
    state = make_state(speed=speed)
    state.out.canValid = state.out.ascmReady = True
    state.out.gearShifter = 'drive'
    state.out.cruiseState.available = state.out.cruiseState.enabled = True
    state.ascm = AscmSupervisor()
    for seq in range(3):
      feed(state.ascm, seq, 1. + seq * .04)
    sender = CarController(DBC[CAR.CHEVROLET_VOLT], cp)
    sm = {
      'carState': state.out,
      'vehicleParameters': log.VehicleParameters(stiffnessFactor=1., steerRatio=cp.steerRatio),
      'lateralTorqueParameters': SimpleNamespace(useParams=False),
      'longitudinalPlan': SimpleNamespace(aTarget=0., shouldStop=False, hasLead=False),
      'modelV2': SimpleNamespace(meta=SimpleNamespace(laneChangeState=log.LaneChangeState.off),
                                 action=SimpleNamespace(desiredCurvature=curvature)),
      'selfdriveState': log.SelfdriveState(state='enabled', enabled=True, active=True),
      'onroadEvents': [],
      'lateralDelay': SimpleNamespace(lateralDelay=.1),
      'carOutput': SimpleNamespace(actuatorsOutput=structs.CarControl.Actuators()),
      'driverMonitoringState': SimpleNamespace(noResponseForceDecel=False),
    }

    class Subscriptions(dict):
      valid = {'lateralManeuverPlan': False, 'driverAssistance': False}
      logMonoTime = {'longitudinalPlan': 0, 'modelV2': 0}

      def all_checks(self, services):
        return False

    controls.sm = Subscriptions(sm)
    libsafety.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam)
    libsafety.init_tests()
    libsafety.set_controls_allowed(True)
    sent_torque = []
    for frame in range(active_frames + 20):
      libsafety.set_timer(frame * 10_000)
      now_nanos = 1_080_000_000 + frame * 10_000_000
      if frame and frame % 4 == 0:
        feed(state.ascm, 2 + frame // 4, now_nanos * 1e-9)
      if frame == active_frames:
        state.out.ascmReady = False  # Sender must release even while controlsd is still enabled.
        libsafety.set_controls_allowed(False)
      cc, lateral_log = controls.state_control()
      self.assertEqual(cc.latActive, speed > .3)
      controls.publish(cc, lateral_log)
      published = {call.args[0]: call.args[1] for call in controls.pm.send.call_args_list[-2:]}
      self.assertEqual(published['controlsState'].controlsState.lateralControlState.which(), 'torqueState')
      self.assertTrue(cc.cruiseControl.cancel)  # Synthetic PCM cancel cannot disengage the ASCM session.
      actuators, messages = sender.update(cc.as_reader(), state, now_nanos)
      controls.sm['carOutput'].actuatorsOutput = actuators
      for address, data, bus in messages:
        self.assertEqual(bus, 1)
        self.assertTrue(libsafety.safety_tx_hook(make_CANPacket(address, bus, data)), (frame, hex(address), data.hex()))
        if address == 0x180:
          raw_torque = int.from_bytes(data[:2], 'big') & 0x7FF
          raw_torque -= 0x800 if raw_torque & 0x400 else 0
          self.assertEqual(raw_torque, round(actuators.torque * 400))
          state.loopback_lka_steering_cmd_updated = True
          state.loopback_lka_steering_cmd_counter = (data[0] >> 4) & 3
          state.loopback_lka_steering_cmd_ts_nanos = now_nanos
          if frame >= active_frames:
            self.assertEqual(int.from_bytes(data[:2], 'big') & 0xFFF, 0)
          else:
            sent_torque.append(actuators.torque)
        elif address in state.ascm_next_counters:
          state.ascm_next_counters[address] = (((data[0] >> 6) if address == 0x2CB else (data[4] & 3)) + 1) % 4
        if frame >= active_frames and address == 0x37F:
          self.assertEqual(data[:2], bytes.fromhex('1000'))
        if frame >= active_frames and address == 0x2CB:
          self.assertFalse(data[0] & 1)
      if frame >= active_frames:
        self.assertFalse(sender.c11_engaged)
    return sent_torque
