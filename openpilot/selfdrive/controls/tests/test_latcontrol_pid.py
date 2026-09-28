import unittest

from openpilot.cereal import log
from opendbc.car import DT_CTRL
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR
from opendbc.car.structs import car
from opendbc.car.vehicle_model import VehicleModel
from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID


class TestLatControlPID(unittest.TestCase):
  def setUp(self):
    CP = CarInterface.get_non_essential_params(CAR.CHEVROLET_VOLT)
    self.controller = LatControlPID(CP, CarInterface(CP), DT_CTRL)
    self.vm = VehicleModel(CP)
    self.cs = car.CarState.new_message(vEgo=20.)
    self.params = log.VehicleParameters.new_message()

  def update(self, active=True, limited=False, curvature_limited=False):
    return self.controller.update(active, self.cs, self.vm, self.params, limited, 0., curvature_limited, 0.2)

  def build_integral(self, angle):
    self.cs.vEgo = 20.
    self.cs.steeringAngleDeg = angle
    for _ in range(100):
      self.update(curvature_limited=True)
    self.assertGreater(abs(self.controller.pid.i), 0.01)
    self.assertGreater(self.controller.sat_time, 0.)

  def test_reset_clears_integral_before_reactivation(self):
    for angle in (-2., 2.):
      for speed in (4., 20.):
        with self.subTest(angle=angle, reactivation_speed=speed):
          self.build_integral(angle)
          # Match controlsd: reset before update on every laterally inactive frame.
          for _ in range(10):
            self.controller.reset()
            output, _, state = self.update(active=False)
            self.assertEqual(output, 0.)
            self.assertFalse(state.active)
          self.assertEqual(self.controller.pid.i, 0.)
          self.assertEqual(self.controller.sat_time, 0.)

          self.cs.vEgo = speed
          self.cs.steeringAngleDeg = 0.
          for _ in range(100):
            output, _, state = self.update()
            self.assertTrue(state.active)
            self.assertEqual(state.i, 0.)
            self.assertEqual(output, 0.)

  def test_active_integration_guards_still_preserve_integral(self):
    self.build_integral(-2.)
    integral = self.controller.pid.i
    for speed, pressed, limited in ((4., False, False), (20., True, False), (20., False, True)):
      with self.subTest(speed=speed, pressed=pressed, limited=limited):
        self.cs.vEgo = speed
        self.cs.steeringPressed = pressed
        for _ in range(10):
          self.update(limited=limited)
        self.assertEqual(self.controller.pid.i, integral)
