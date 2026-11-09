import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.fingerprints import FINGERPRINTS
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, CAMERA_ACC_CAR, DBC, GM_RX_OFFSET
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
