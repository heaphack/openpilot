import math
import unittest
from types import SimpleNamespace

from opendbc.can import CANParser
from opendbc.car import Bus, structs, ACCELERATION_DUE_TO_GRAVITY
from opendbc.car.gm import gmcan
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.values import CAR, DBC, CanBus, LongOwner


def make_controller(car=CAR.CHEVROLET_VOLT, network="gateway"):
  cp = structs.CarParams.new_message(carFingerprint=car, networkLocation=network, openpilotLongitudinalControl=True,
                                    flags=int(car.config.flags))
  return CarController(DBC[car], cp)


def make_state(speed=0.5, minimum=100., valid=True, standstill=False, cruise_standstill=False):
  out = structs.CarState.new_message(vEgo=speed, standstill=standstill)
  out.cruiseState.standstill = cruise_standstill
  return SimpleNamespace(out=out, axle_torque_min=minimum, axle_torque_min_valid=valid,
                         lka_steering_cmd_counter=0, pt_lka_steering_cmd_counter=0, loopback_lka_steering_cmd_updated=False,
                         loopback_lka_steering_cmd_ts_nanos=0)


def make_control(pitch=None):
  control = structs.CarControl.new_message(enabled=True, longActive=True)
  control.actuators.longControlState = "pid"
  if pitch is not None:
    control.orientationNED = [0., pitch, 0.]
  return control


class TestAllocateLong(unittest.TestCase):
  def setUp(self):
    self.controller = make_controller()
    self.state = make_state()
    self.control = make_control()

  def allocate(self, accel, frames=1, stopping=False, pitch=None):
    self.control.actuators.accel = accel
    if pitch is not None:
      self.control.orientationNED = [0., pitch, 0.]
    for _ in range(frames):
      result = self.controller.allocate_long(self.control.as_reader(), self.state, stopping)
    return result

  def test_signed_request_between_entry_and_release(self):
    # A small positive request does not hand the request to the brake controller from the powertrain.
    self.allocate(0.1)
    self.assertEqual(self.controller.owner, LongOwner.POWERTRAIN)
    # Once the brake controller owns it, the request follows the corrected acceleration through zero.
    for accel, expected in ((-0.3, 30), (-0.1, 10), (0., 0), (0.02, -2), (0.1, -10), (-0.05, 5)):
      self.assertEqual(self.allocate(accel), (-650., expected))
      self.assertEqual(self.controller.owner, LongOwner.BRAKE)

  def test_release_and_reentry_hysteresis(self):
    p = self.controller.params
    for speed in (0.4, 1.0, 4., 15.):
      with self.subTest(speed=speed):
        self.controller = make_controller()
        self.state = make_state(speed=speed, minimum=100. if speed < 2. else -650.)
        a_regen = p.regen_accel_available(self.state.axle_torque_min, speed)
        self.allocate(a_regen - 0.5)
        self.assertEqual(self.controller.owner, LongOwner.BRAKE)
        self.allocate(a_regen + 0.1)
        self.assertEqual(self.controller.owner, LongOwner.BRAKE)
        gas, brake = self.allocate(a_regen + 0.3)
        self.assertEqual(self.controller.owner, LongOwner.POWERTRAIN)
        self.assertEqual(brake, 0)
        self.assertAlmostEqual(gas, p.torque_ff(a_regen + 0.3, speed), delta=0.01)  # float32 accel
        # No chatter: falling back inside the band does not hand the request back to the brakes.
        for accel in (a_regen + 0.1, a_regen, a_regen - 0.05):
          self.allocate(accel)
          self.assertEqual(self.controller.owner, LongOwner.POWERTRAIN)

  def test_downhill_keeps_brake_controller_with_positive_request(self):
    # A 5% downgrade supplies ~0.49 m/s^2; a modest positive request is still braking effort.
    pitch = -math.atan(0.05)
    grade = math.sin(pitch) * ACCELERATION_DUE_TO_GRAVITY
    for _ in range(300):  # settle the pitch filter
      self.allocate(-0.3, pitch=pitch)
    self.assertEqual(self.controller.owner, LongOwner.BRAKE)
    gas, brake = self.allocate(0.3, pitch=pitch)
    self.assertEqual(self.controller.owner, LongOwner.BRAKE)
    self.assertEqual((gas, brake), (-650., -int(round((0.3 + grade) * 100))))
    # Flat ground with the same request hands the request back to the powertrain.
    for _ in range(300):
      gas, brake = self.allocate(0.3, pitch=0.)
    self.assertEqual(self.controller.owner, LongOwner.POWERTRAIN)
    self.assertEqual(brake, 0)

  def test_grade_filter_settles_at_its_time_constant(self):
    # The filter runs at the 25 Hz allocation rate: a 0.5 s time constant means 63% of a pitch step after
    # 0.5 s (12-13 calls) and 95% after 1.5 s, not the 2 s a 100 Hz-configured filter would take.
    pitch = math.atan(0.05)
    for _ in range(13):
      self.allocate(0.5, pitch=pitch)
    self.assertAlmostEqual(self.controller.pitch.x / pitch, 1 - math.exp(-13 * 0.04 / 0.5), delta=0.05)
    for _ in range(25):
      self.allocate(0.5, pitch=pitch)
    self.assertGreater(self.controller.pitch.x / pitch, 0.94)

  def test_uphill_feedforward_carries_the_grade(self):
    p = self.controller.params
    pitch = math.atan(0.05)
    grade = math.sin(pitch) * ACCELERATION_DUE_TO_GRAVITY
    for _ in range(300):
      gas, brake = self.allocate(0.5, pitch=pitch)
    self.assertEqual(self.controller.owner, LongOwner.POWERTRAIN)
    self.assertAlmostEqual(gas, p.torque_ff(0.5 + grade, self.state.out.vEgo), delta=2.)  # filter settling
    self.assertGreater(gas, p.torque_ff(0.5, self.state.out.vEgo))

  def test_stopping_and_standstill_stay_non_positive(self):
    for state, stopping in ((self.state, True), (make_state(standstill=True), False), (make_state(cruise_standstill=True), False)):
      self.controller = make_controller()
      self.state = make_state()
      self.allocate(-0.3)
      self.assertEqual(self.allocate(0.1)[1], -10)
      self.state = state
      _, brake = self.allocate(0.1, stopping=stopping)
      self.assertEqual(brake, 0)
      self.assertEqual(self.controller.owner, LongOwner.BRAKE)

  def test_maximum_authority(self):
    self.assertEqual(self.allocate(-4.), (-650., 400))
    self.assertEqual(self.allocate(-6.), (-650., 400))

  def test_powertrain_feedforward_is_invertible(self):
    p = self.controller.params
    gas, brake = self.allocate(0.5)
    self.assertEqual(self.controller.owner, LongOwner.POWERTRAIN)
    self.assertEqual(brake, 0)
    self.assertAlmostEqual(p.accel_from_torque(gas, self.state.out.vEgo), 0.5, places=6)


class TestVoltCreepCAN(unittest.TestCase):
  def setUp(self):
    self.controller = make_controller()
    self.state = make_state()
    self.control = make_control()
    self.parser = CANParser(DBC[CAR.CHEVROLET_VOLT][Bus.chassis], [("EBCMFrictionBrakeCmd", 25)], CanBus.CHASSIS)
    self.tick = 0

  def update(self, accel):
    self.control.actuators.accel = accel
    self.controller.frame = self.tick * 4
    nanos = 1_000_000_000 + self.tick * 40_000_000
    _, messages = self.controller.update(self.control.as_reader(), self.state, nanos)
    self.assertTrue(0x315 in self.parser.update([[nanos, messages]]))
    self.tick += 1
    brake_message = next(message for message in messages if message[0] == 0x315)
    mode = int(self.parser.vl["EBCMFrictionBrakeCmd"]["FrictionBrakeMode"])
    demand = self.parser.vl["EBCMFrictionBrakeCmd"]["FrictionBrakeCmd"]
    # Check the actual packet's checksum, including the independently selected active bit.
    data = brake_message[1]
    raw_brake = ((data[0] & 0xf) << 8) | data[1]
    idx = data[4] & 3
    self.assertEqual(int.from_bytes(data[2:4], "big"), (0x10000 - (mode << 12) - raw_brake - idx) & 0xffff)
    return mode, demand

  def test_signed_demand_holds_0xa_until_release(self):
    for accel, expected in ((-0.3, -30.), (0., 0.), (0.02, 2.), (0.1, 10.), (-0.05, -5.)):
      self.assertEqual(self.update(accel), (0xa, expected))
    self.assertEqual(self.controller.apply_gas, -650.)
    self.assertEqual(self.update(0.3), (0x1, 0.))
    for accel in (0.1, 0., -0.05, 0.1):
      self.assertEqual(self.update(accel), (0x1, 0.))

  def test_stop_intent_drops_positive_request(self):
    self.update(-0.3)
    self.assertEqual(self.update(0.1), (0xa, 10.))
    self.control.actuators.longControlState = "stopping"
    self.assertEqual(self.update(0.1), (0xa, 0.))
    self.assertEqual(self.update(-0.3), (0xa, -30.))
    self.control.actuators.longControlState = "pid"
    self.assertEqual(self.update(-0.3)[0], 0xa)

  def test_other_platforms_keep_lookup_allocation(self):
    self.controller = make_controller(CAR.CHEVROLET_MALIBU)
    self.assertFalse(self.controller.params.ASCM_LONG)
    mode, demand = self.update(-0.3)
    self.assertEqual(mode, 0xa)
    self.assertLess(demand, 0.)
    self.assertEqual(self.controller.owner, LongOwner.POWERTRAIN)
    self.assertEqual(self.update(0.1), (0x1, 0.))

  def test_disengagement_clears_retained_path(self):
    self.update(-0.3)
    self.assertEqual(self.update(0.1), (0xa, 10.))
    # CC.enabled can remain true for lateral control while longitudinal is inactive.
    self.control.longActive = False
    self.assertEqual(self.update(0.), (0x1, 0.))
    self.assertEqual(self.controller.owner, LongOwner.POWERTRAIN)

  def test_stopping_still_sends_full_stop_mode(self):
    self.control.actuators.longControlState = "stopping"
    self.state.out.standstill = True
    self.state.out.cruiseState.standstill = True
    self.assertEqual(self.update(-2.), (0xd, -200.))

  def test_disabled_helper_cannot_force_active_zero_demand(self):
    message = gmcan.create_friction_brake_command(self.controller.packer_ch, CanBus.CHASSIS, 0, 0,
                                                 False, True, False, self.controller.CP, brake_active=True)
    self.assertEqual(message[1][0] >> 4, 0x1)


if __name__ == "__main__":
  unittest.main()
