#!/usr/bin/env python3
import unittest

from opendbc.car.gm.values import GMSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.common import CANPackerSafety
from opendbc.safety.tests.libsafety import libsafety_py


class TestGmSignedBrakeSafety(unittest.TestCase):
  """EBCMFrictionBrakeCmd carries a signed acceleration request (0.01 m/s^2): [-400, 200] while enabled, 0 otherwise."""

  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPackerSafety('gm_global_a_chassis')
    self.configure(GMSafetyFlags.EV)

  def configure(self, param):
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, param)
    self.safety.init_tests()

  def tx(self, request, mode=0xA, bus=2):
    msg = self.packer.make_can_msg_safety('EBCMFrictionBrakeCmd', bus,
                                          {'FrictionBrakeCmd': request * 0.01, 'FrictionBrakeMode': mode})
    return bool(self.safety.safety_tx_hook(msg))

  def test_entire_signed_range_modes_and_engagement_across_hardware(self):
    for param, bus in ((0, 2), (GMSafetyFlags.EV, 2),
                       (GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG, 0),
                       (GMSafetyFlags.EV | GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG, 0)):
      self.configure(param)
      for enabled in (False, True):
        self.safety.set_controls_allowed(enabled)
        for mode in range(16):
          for request in range(-2048, 2048):
            expected = request == 0 or (enabled and -400 <= request <= 200)
            self.assertEqual(self.tx(request, mode, bus), expected, (param, enabled, mode, request))

  def test_configurations_without_brake_tx_remain_blocked(self):
    for param, bus in ((GMSafetyFlags.HW_CAM, 0), (GMSafetyFlags.EV | GMSafetyFlags.HW_CAM, 0)):
      self.configure(param)
      self.safety.set_controls_allowed(True)
      for request in (-400, -14, 0, 1, 14, 199, 200, 201, 2047):
        self.assertFalse(self.tx(request, bus=bus))

  def test_gas_override_blocks_nonzero_requests_in_all_modes(self):
    for param, bus in ((0, 2), (GMSafetyFlags.EV, 2), (GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG, 0)):
      self.configure(param)
      self.safety.set_controls_allowed(True)
      self.safety.set_gas_pressed_prev(True)
      for mode in range(16):
        for request in (-400, -1, 1, 199, 200):
          self.assertFalse(self.tx(request, mode=mode, bus=bus))
        self.assertTrue(self.tx(0, mode=mode, bus=bus))

  def test_wrong_bus_remains_blocked(self):
    for param, bus in ((0, 0), (0, 1), (GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG, 2)):
      self.configure(param)
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.tx(200, bus=bus))

  def test_interceptor_allows_obstacle_bus_with_the_same_limits(self):
    for param in (GMSafetyFlags.ASCM_INTERCEPTOR, GMSafetyFlags.ASCM_INTERCEPTOR | GMSafetyFlags.EV):
      self.configure(param)
      for enabled in (False, True):
        self.safety.set_controls_allowed(enabled)
        for bus in (1, 2):
          for request in (-401, -400, -1, 0, 1, 200, 201):
            expected = request == 0 or (enabled and -400 <= request <= 200)
            self.assertEqual(self.tx(request, bus=bus), expected, (param, enabled, bus, request))
        self.assertFalse(self.tx(200, bus=0))


if __name__ == "__main__":
  unittest.main()
