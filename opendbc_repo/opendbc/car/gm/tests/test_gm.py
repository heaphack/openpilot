import math
import unittest

import numpy as np

from opendbc.can import CANPacker
from opendbc.car import DT_CTRL, Bus, gen_empty_fingerprint, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.ascm import AscmSupervisor
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.fingerprints import FINGERPRINTS
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_ascm import feed
from opendbc.car.gm.tests.test_volt_longitudinal import make_control, make_controller, make_state
from opendbc.car.gm.values import CAR, CAMERA_ACC_CAR, DBC, GM_RX_OFFSET, CarControllerParams
from opendbc.safety.tests.libsafety.libsafety_py import libsafety, make_CANPacket
from opendbc.testing import parameterized

CAMERA_DIAGNOSTIC_ADDRESS = 0x24b


class TestGMFingerprint(unittest.TestCase):
  @parameterized("car_model, fingerprints", FINGERPRINTS.items())
  def test_can_fingerprints(self, car_model, fingerprints):
    assert len(fingerprints) > 0

    assert all(len(finger) for finger in fingerprints)

    # The camera can sometimes be communicating on startup
    if car_model in CAMERA_ACC_CAR:
      for finger in fingerprints:
        for required_addr in (CAMERA_DIAGNOSTIC_ADDRESS, CAMERA_DIAGNOSTIC_ADDRESS + GM_RX_OFFSET):
          assert finger.get(required_addr) == 8, required_addr


class TestGMLowSpeedAlert(unittest.TestCase):
  def setUp(self):
    self.cp = CarInterface.get_params(CAR.CHEVROLET_VOLT, gen_empty_fingerprint(), [], False, False, False)
    self.cs = CarState(self.cp)
    self.parsers = CarState.get_can_parsers(self.cp)
    self.packer = CANPacker(DBC[CAR.CHEVROLET_VOLT][Bus.pt])
    self.frame = 0
    self.cs.update(self.parsers)  # Register the signals consumed by the dynamic parsers.

  def update(self, speed, eps_status=0):
    self.frame += 1
    wheel_speed = speed * CV.MS_TO_KPH
    messages = [
      self.packer.make_can_msg("EBCMWheelSpdFront", 0, {"FLWheelSpd": wheel_speed, "FRWheelSpd": wheel_speed}),
      self.packer.make_can_msg("EBCMWheelSpdRear", 0, {"RLWheelSpd": wheel_speed, "RRWheelSpd": wheel_speed}),
      self.packer.make_can_msg("PSCMStatus", 0, {"LKATorqueDeliveredStatus": eps_status}),
    ]
    for parser in self.parsers.values():
      parser.update([(self.frame * 10_000_000, messages)])
    return self.cs.update(self.parsers)

  def test_zero_minimum_does_not_warn_when_speed_filter_undershoots(self):
    self.assertEqual(self.cp.minSteerSpeed, 0.)
    for _ in range(100):
      self.update(1.)
    stopped = [self.update(0.) for _ in range(100)]
    # Reproduce the real filter's negative estimate despite stationary wheels.
    self.assertLess(min(state.vEgo for state in stopped), 0.)
    for state in stopped:
      self.assertEqual(state.vEgoRaw, 0.)
      self.assertTrue(state.standstill)
      self.assertFalse(state.lowSpeedAlert)

  def test_positive_minimum_still_warns_and_clears(self):
    self.cp.minSteerSpeed = 7 * CV.MPH_TO_MS
    for speed, expected in ((4., False), (0., True), (4., False)):
      for _ in range(100):
        state = self.update(speed)
      self.assertEqual(state.lowSpeedAlert, expected)

  def test_eps_faults_are_reported_at_zero_speed(self):
    for status in (0, 1, 2, 3):
      with self.subTest(status=status):
        state = self.update(0., eps_status=status)
        self.assertFalse(state.lowSpeedAlert)
        self.assertEqual(state.steerFaultTemporary, status == 2)
        self.assertEqual(state.steerFaultPermanent, status == 3)


class TestVoltSteerCommand(unittest.TestCase):
  # openpilot sees its own steering command on the bus about 8 ms after sending it (hewers/opendbc 9b7efe7)
  LOOPBACK_DELAY_NS = 8_000_000

  def send_rate(self, car, loopback_delay_ns=LOOPBACK_DELAY_NS):
    """Steering commands per second while steering, with each loopback arriving loopback_delay_ns after its send."""
    controller = make_controller(car)
    state = make_state(speed=20.)
    control = make_control()
    control.latActive = True
    control.actuators.torque = 0.1
    control = control.as_reader()
    loopbacks, sends, frames = [], 0, 1000
    for frame in range(frames):
      now = frame * round(DT_CTRL * 1e9)
      arrived = [t for t in loopbacks if t <= now]
      loopbacks = [t for t in loopbacks if t > now]
      state.loopback_lka_steering_cmd_updated = len(arrived) > 0
      if arrived:
        state.loopback_lka_steering_cmd_ts_nanos = arrived[-1]
      _, messages = controller.update(control, state, now)
      if any(message[0] == 0x180 for message in messages):
        sends += 1
        loopbacks.append(now + loopback_delay_ns)
    return sends / (frames * DT_CTRL)

  def test_volt_commands_at_50hz(self):
    # The Volt does not wait on the loopback: one that arrives 12 or 18 ms after its send must not delay the next command
    for delay_ms in (3, 8, 12, 18):
      with self.subTest(delay_ms=delay_ms):
        self.assertAlmostEqual(self.send_rate(CAR.CHEVROLET_VOLT, delay_ms * 1_000_000), 50., delta=1.)

  def test_other_ascm_cars_stay_at_33hz(self):
    self.assertAlmostEqual(self.send_rate(CAR.GMC_ACADIA), 100. / 3, delta=1.)

  def test_other_ascm_cars_keep_the_loopback_gate(self):
    # A loopback 16 ms after its send is 14 ms old at the next due frame, inside the 15 ms gate: the command waits a frame
    self.assertAlmostEqual(self.send_rate(CAR.GMC_ACADIA, 16_000_000), 25., delta=1.)

  def test_volt_rate_limits(self):
    # hewers' schedule, 8.0 -> 2.4 Nm/s, the same up and down, as counts per 50 Hz command rounded up
    params = CarControllerParams(CarInterface.get_non_essential_params(CAR.CHEVROLET_VOLT))
    self.assertEqual((params.STEER_STEP, params.STEER_MAX, params.STEER_DELTA_DOWN_OVERRIDE), (2, 400, 16))
    for v_ego, counts, nm_per_s in ((10., 16, 8.0), (16.68, 16, 8.0), (29.06, 12, 5.92), (50.03, 5, 2.4), (60., 5, 2.4)):
      for bp, v in ((params.STEER_DELTA_UP_BP, params.STEER_DELTA_UP_V), (params.STEER_DELTA_DOWN_BP, params.STEER_DELTA_DOWN_V)):
        step = np.interp(v_ego, bp, v)
        self.assertAlmostEqual(step / 100. / (params.STEER_STEP * DT_CTRL), nm_per_s, delta=0.01)
        self.assertEqual(math.ceil(step), counts)

  def test_other_gm_rate_limits_are_unchanged(self):
    params = CarControllerParams(CarInterface.get_non_essential_params(CAR.GMC_ACADIA))
    self.assertEqual((params.STEER_STEP, params.STEER_MAX), (3, 300))
    self.assertEqual((params.STEER_DELTA_UP_V, params.STEER_DELTA_DOWN_V, params.STEER_DELTA_DOWN_OVERRIDE), ([10], [15], None))

  def test_c11_sender_through_panda(self):
    # The Volt's c11 sender into compiled Panda at its own safety parameter: full torque, then the driver pushes
    # against it at 5 Nm/s. Every message must be accepted, and the command must release at Panda's max_rate_down.
    cp = CarInterface.get_params(CAR.CHEVROLET_VOLT, gen_empty_fingerprint(), [], False, False, False)
    packer = CANPacker(DBC[CAR.CHEVROLET_VOLT][Bus.pt])
    for speed, rise_step in ((10., 16), (29.06, 12)):
      for direction in (-1, 1):
        with self.subTest(speed=speed, direction=direction):
          sender = CarController(DBC[CAR.CHEVROLET_VOLT], cp)
          state = make_state(speed=speed)
          state.out.canValid = state.out.ascmReady = True
          state.out.gearShifter = 'drive'
          state.out.cruiseState.available = state.out.cruiseState.enabled = True
          state.ascm = AscmSupervisor()
          for seq in range(3):
            feed(state.ascm, seq, 1. + seq * .04)
          libsafety.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam)
          libsafety.init_tests()
          libsafety.set_controls_allowed(True)
          control = structs.CarControl.new_message(enabled=True, latActive=True, longActive=True)
          control.actuators.torque = float(direction)
          control.actuators.longControlState = "pid"
          control = control.as_reader()
          commands, frames = [], []
          for frame in range(400):
            libsafety.set_timer(frame * 10_000)
            now_nanos = 1_080_000_000 + frame * 10_000_000
            if frame and frame % 4 == 0:
              feed(state.ascm, 2 + frame // 4, now_nanos * 1e-9)
            driver_torque = -direction * min(300, max(0, frame - 200) * 5)  # counts
            state.out.steeringTorque = driver_torque * 0.01
            address, data, bus = packer.make_can_msg("PSCMStatus", 0, {"LKADriverAppldTrq": driver_torque * 0.01})
            libsafety.safety_rx_hook(make_CANPacket(address, bus, data))
            actuators, messages = sender.update(control, state, now_nanos)
            for address, data, bus in messages:
              self.assertTrue(libsafety.safety_tx_hook(make_CANPacket(address, bus, data)), (frame, hex(address), data.hex()))
              if address == 0x180:
                commands.append(actuators.torqueOutputCan)
                frames.append(frame)
                state.loopback_lka_steering_cmd_updated = True
                state.loopback_lka_steering_cmd_counter = (data[0] >> 4) & 3
                state.loopback_lka_steering_cmd_ts_nanos = now_nanos
          steps = [abs(b - a) for a, b in zip(commands, commands[1:], strict=False)]
          self.assertEqual({b - a for a, b in zip(frames, frames[1:], strict=False)}, {2})
          self.assertEqual(max(direction * command for command in commands), 400)
          self.assertEqual(max(steps[:60]), rise_step)
          self.assertEqual(max(steps[100:]), 16)
          self.assertEqual(commands[-1], 0)
