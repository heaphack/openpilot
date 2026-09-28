import math
import numpy as np
import unittest
from types import SimpleNamespace

from opendbc.can import CANParser
from opendbc.car import Bus, structs, ACCELERATION_DUE_TO_GRAVITY
from opendbc.car.gm import gmcan
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.values import CAR, DBC, CanBus, GMFlags, LongOwner


def make_controller(car=CAR.CHEVROLET_VOLT, network="gateway", flags=None):
  cp = structs.CarParams.new_message(carFingerprint=car, networkLocation=network, openpilotLongitudinalControl=True,
                                    flags=int(car.config.flags) if flags is None else int(flags))
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


class TestAscmLongitudinal(unittest.TestCase):
  def setUp(self):
    self.controller = make_controller()
    self.state = make_state()
    self.control = make_control()

  def allocate(self, accel, frames=1, stopping=False, pitch=None):
    self.control.actuators.longControlState = "stopping" if stopping else "pid"
    self.control.actuators.accel = accel
    if pitch is not None:
      self.control.orientationNED = [0., pitch, 0.]
    for _ in range(frames):
      reader = self.control.as_reader()
      for _ in range(4):  # one 25 Hz allocation spans four control frames of pitch filtering
        self.controller.update_pitch(reader)
      self.controller.update_ascm_longitudinal(reader, self.state, 0)
    return self.controller.axle_torque_cmd, self.controller.brake_accel_cmd

  def test_signed_request_between_entry_and_release(self):
    self.state = make_state(speed=1.0)  # 0.1 m/s^2 lies inside the ownership band at this speed.
    # A small positive request does not hand the request to the brake controller from the powertrain.
    self.allocate(0.1)
    self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)
    # Once the brake controller owns it, the request follows the corrected acceleration through zero.
    for accel, expected in ((-0.3, -0.3), (-0.1, -0.1), (0., 0.), (0.02, 0.02), (0.1, 0.1), (-0.05, -0.05)):
      self.assertEqual(self.allocate(accel), (-650., expected))
      self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)

  def test_release_and_reentry_hysteresis(self):
    p = self.controller.params
    for speed in (0.4, 1.0, 4., 15.):
      with self.subTest(speed=speed):
        self.controller = make_controller()
        self.state = make_state(speed=speed, minimum=100. if speed < 2. else -650.)
        a_regen = p.predict_minimum_powertrain_accel(self.state.axle_torque_min, True, speed)
        self.allocate(a_regen - 0.5)
        self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
        self.allocate(a_regen + 0.1)
        self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
        gas, brake = self.allocate(a_regen + 0.3)
        self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)
        self.assertEqual(brake, 0.)
        self.assertAlmostEqual(gas, p.accel_to_axle_torque(a_regen + 0.3, speed), delta=0.01)  # float32 accel
        # No chatter: falling back inside the band does not hand the request back to the brakes.
        for accel in (a_regen + 0.1, a_regen, a_regen - 0.05):
          self.allocate(accel)
          self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)

  def test_downhill_keeps_brake_controller_with_positive_request(self):
    self.state = make_state(speed=1.0)
    # A 5% downgrade supplies ~0.49 m/s^2; a modest positive request is still braking effort.
    pitch = -math.atan(0.05)
    for _ in range(300):  # settle the pitch filter
      self.allocate(-0.3, pitch=pitch)
    self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
    gas, brake = self.allocate(0.3, pitch=pitch)
    self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
    self.assertEqual((gas, brake), (-650., 0.3))  # EBCM regulates vehicle acceleration, including on the descent.
    # Flat ground with the same request hands the request back to the powertrain.
    for _ in range(300):
      gas, brake = self.allocate(0.3, pitch=0.)
    self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)
    self.assertEqual(brake, 0)

  def test_pitch_tracks_while_long_control_is_inactive(self):
    # driven by hand from an 8% uphill onto an 8% downhill, then re-engaged: the allocation must see the descent
    # at once, not the uphill from the last disengagement
    uphill, downhill = math.atan(0.08), -math.atan(0.08)
    self.allocate(-0.5, frames=300, pitch=uphill)
    self.control.longActive = False
    self.control.orientationNED = [0., downhill, 0.]
    for k in range(500):  # 5 s of driving with long control off
      self.controller.frame = k
      self.controller.update(self.control.as_reader(), self.state, 0)
    self.assertAlmostEqual(self.controller.pitch_filter.x, downhill, places=4)
    self.control.longActive = True
    gas, brake = self.allocate(-0.5, pitch=downhill)
    self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
    self.assertEqual(gas, -650.)
    self.assertEqual(brake, -0.5)  # Grade affects ownership, not the EBCM acceleration target.

  def test_grade_filter_settles_at_its_time_constant(self):
    # Four 100 Hz pitch updates per allocation: a 0.5 s time constant means 63% of a step after
    # 0.5 s (12-13 allocations) and 95% after 1.5 s.
    pitch = math.atan(0.05)
    for _ in range(13):
      self.allocate(0.5, pitch=pitch)
    self.assertAlmostEqual(self.controller.pitch_filter.x / pitch, 1 - math.exp(-13 * 0.04 / 0.5), delta=0.05)
    for _ in range(25):
      self.allocate(0.5, pitch=pitch)
    self.assertGreater(self.controller.pitch_filter.x / pitch, 0.94)

  def test_uphill_feedforward_carries_the_grade(self):
    p = self.controller.params
    pitch = math.atan(0.05)
    grade = math.sin(pitch) * ACCELERATION_DUE_TO_GRAVITY
    for _ in range(300):
      gas, brake = self.allocate(0.5, pitch=pitch)
    self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)
    self.assertAlmostEqual(gas, p.accel_to_axle_torque(0.5 + grade, self.state.out.vEgo), delta=2.)  # filter settling
    self.assertGreater(gas, p.accel_to_axle_torque(0.5, self.state.out.vEgo))

  def test_near_stop_hold_keeps_the_request_non_positive(self):
    self.allocate(-0.3)
    self.assertEqual(self.allocate(0.1)[1], 0.1)  # easing while moving, no stop committed
    self.assertEqual(self.allocate(0.1, stopping=True)[1], 0.)  # committed to a stop
    self.state = make_state(standstill=True, cruise_standstill=True)
    self.assertEqual(self.allocate(0.1)[1], 0.)  # the hold outlives the stopping state at the stop
    self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
    # a standstill the controller did not stop into (engaged at a stop) is not held: the request may ease
    self.controller = make_controller()
    self.assertEqual(self.allocate(0.1)[1], 0.1)

  def test_held_minimum_does_not_release_on_mild_uphill(self):
    # Reconstructed first handoffs in the two September 26 drives: the reported floor was only 8 Nm.
    for speed, pitch, accel in ((0.0485, 0.01685, -0.03012), (0.0583, 0.01513, -0.00596),
                                (0.0544, 0.02806, -0.03437), (0.1186, 0.02378, -0.02034)):
      with self.subTest(speed=speed, pitch=pitch):
        self.controller = make_controller()
        self.controller.long_owner = LongOwner.BRAKE
        self.controller.pitch_filter.x = pitch
        self.state = make_state(speed=speed, minimum=8.)
        gas, brake = self.allocate(accel, pitch=pitch)
        self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
        self.assertEqual(gas, -650.)
        self.assertAlmostEqual(brake, round(accel, 2))  # Preserve the vehicle target while retaining brake ownership.

  def test_small_positive_target_below_creep_requires_brake(self):
    self.state = make_state(speed=0.5, minimum=8.)
    self.assertEqual(self.allocate(0.1), (-650., 0.1))
    self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
    self.assertEqual(self.allocate(0.5)[1], 0)
    self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)

  def test_maximum_authority(self):
    self.assertEqual(self.allocate(-4.), (-650., -4.))
    self.assertEqual(self.allocate(-6.), (-650., -4.))

  def test_release_request_is_bounded_to_the_safety_envelope(self):
    # a bogus but 'valid' minimum torque report would put the release threshold out of reach; the request the
    # brake controller then carries must still fit the panda's +200-count (+2.0 m/s^2) max_accel
    self.state = make_state(speed=1.0, minimum=10000.)
    self.controller.long_owner = LongOwner.BRAKE
    self.controller.pitch_filter.x = math.atan(0.05)
    gas, brake = self.allocate(2.1, pitch=math.atan(0.05))  # vehicle target exceeds the EBCM envelope
    self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
    self.assertEqual((gas, brake), (-650., self.controller.params.EBCM_ACCEL_SAFETY_MAX))

  def test_powertrain_feedforward_is_invertible(self):
    p = self.controller.params
    gas, brake = self.allocate(0.5)
    self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)
    self.assertEqual(brake, 0)
    self.assertAlmostEqual(p.axle_torque_to_accel(gas, self.state.out.vEgo), 0.5, places=6)


class TestMinimumPowertrainAccel(unittest.TestCase):
  def test_creep_estimate_and_valid_minimum(self):
    p = make_controller().params
    for valid in (True, False):
      self.assertEqual(p.predict_minimum_powertrain_accel(8., valid, 0.), p.axle_torque_to_accel(323., 0.))
      self.assertAlmostEqual(p.predict_minimum_powertrain_accel(8., valid, 0.44704),
                             p.axle_torque_to_accel(222.72644444444444, 0.44704))
    self.assertEqual(p.predict_minimum_powertrain_accel(350., True, 0.44704), p.axle_torque_to_accel(350., 0.44704))

  def test_above_creep_uses_live_limit_and_invalid_fallback(self):
    p = make_controller().params
    for speed in (1.44, 4., 15.):
      for minimum, valid, expected in ((-700., True, -650.), (-100., True, -100.), (80., True, 80.), (999., False, 0.), (-500., False, 0.)):
        with self.subTest(speed=speed, minimum=minimum, valid=valid):
          self.assertEqual(p.predict_minimum_powertrain_accel(minimum, valid, speed), p.axle_torque_to_accel(expected, speed))

  def test_invalid_report_never_releases_the_brakes(self):
    # a -1.1 m/s^2 request at 10 m/s needs more than the -450 Nm of regen the powertrain reports, so the brake
    # controller owns it; losing the report must not hand it to the powertrain on an assumed -650 Nm of regen
    controller = make_controller()
    control = make_control()
    for valid in (True, False, True):
      state = make_state(speed=10., minimum=-450., valid=valid)
      control.actuators.accel = -1.1
      controller.update_ascm_longitudinal(control.as_reader(), state, 0)
      gas, brake = controller.axle_torque_cmd, controller.brake_accel_cmd
      self.assertEqual(controller.long_owner, LongOwner.BRAKE, msg=f"valid={valid}")
      self.assertEqual((gas, brake), (-650., -1.1))

  def test_fade_is_continuous_and_respects_reported_limit(self):
    p = make_controller().params
    for minimum in (-650., -100., 8., 350.):
      for boundary in p.CREEP_FADE_BP:
        below = p.predict_minimum_powertrain_accel(minimum, True, boundary - 1e-6)
        above = p.predict_minimum_powertrain_accel(minimum, True, boundary + 1e-6)
        self.assertAlmostEqual(below, above, delta=0.002 / (p.MODEL_MASS * p.TIRE_RADIUS * p.DRIVETRAIN_EFFICIENCY))
      previous = p.predict_minimum_powertrain_accel(minimum, True, 1.10)
      for i in range(1, 101):
        speed = 1.10 + 0.34 * i / 100
        floor = p.predict_minimum_powertrain_accel(minimum, True, speed)
        self.assertGreaterEqual(floor, p.axle_torque_to_accel(minimum, speed))
        self.assertLessEqual(floor, previous + 1e-9)
        previous = floor
      self.assertEqual(previous, p.axle_torque_to_accel(minimum, 1.44))

  def test_other_powertrains_require_their_own_calibration(self):
    for car in CAR:
      if car == CAR.CHEVROLET_VOLT:
        continue
      with self.subTest(car=car):
        self.assertFalse(make_controller(car).params.ASCM_LONG)
        with self.assertRaisesRegex(ValueError, "ASCM longitudinal calibration missing"):
          make_controller(car, flags=int(car.config.flags) | int(GMFlags.ASCM_LONG))


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
    self.output, messages = self.controller.update(self.control.as_reader(), self.state, nanos)
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

  def test_reported_brake_accel_matches_signed_can_request(self):
    cases = ((0.1, math.atan(0.05), 8., True, 0.),  # positive vehicle target suppressed by stop hold
             (0.124, 0., 8., False, 0.12),          # positive release, quantized
             (-0.126, 0., 8., False, -0.13),        # negative request, quantized
             (-5., 0., 8., False, -4.),            # negative safety bound
             (3., 0., 10000., False, 2.))          # positive bound with an excessive reported floor
    for accel, pitch, minimum, stopping, expected in cases:
      with self.subTest(accel=accel, stopping=stopping):
        self.controller = make_controller()
        self.state = make_state(speed=0., minimum=minimum)
        self.control = make_control()
        self.controller.pitch_filter.x = pitch
        self.control.actuators.longControlState = "stopping" if stopping else "pid"
        _, demand = self.update(accel)
        self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
        self.assertAlmostEqual(demand, expected)
        self.assertAlmostEqual(self.output.accel, demand)
        self.assertAlmostEqual(self.output.brake, max(-demand, 0.))
        self.assertAlmostEqual(self.control.actuators.accel, accel)  # input remains available in carControl
        # At 100 Hz the output keeps the most recent 25 Hz command, not the new unsent input.
        self.control.actuators.accel = 1.
        for _ in range(3):
          output, messages = self.controller.update(self.control.as_reader(), self.state, 0)
          self.assertFalse(any(message[0] == 0x315 for message in messages))
          self.assertAlmostEqual(output.accel, demand)

  def test_brake_can_request_is_independent_of_grade(self):
    # The EBCM regulates vehicle acceleration. Gravity belongs in torque allocation, not its CAN target.
    cases = ((-0.08, -1.2), (0., -1.2), (0.08, -1.2), (-0.08, 0.), (-0.08, 0.3))
    for grade, accel in cases:
      with self.subTest(grade=grade, accel=accel):
        self.controller = make_controller()
        self.state = make_state(speed=0.5, minimum=8.)
        pitch = math.atan(grade)
        self.control = make_control(pitch=pitch)
        self.controller.pitch_filter.x = pitch
        mode, demand = self.update(accel)
        self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
        self.assertEqual(mode, 0xa)
        self.assertAlmostEqual(demand, accel)
        self.assertAlmostEqual(self.output.accel, demand)
        self.assertEqual(self.controller.axle_torque_cmd, -650.)

  def test_stop_hold_can_request_is_independent_of_grade(self):
    for grade in (-0.08, 0., 0.08):
      for accel, expected in ((-1., -1.), (0.1, 0.)):
        with self.subTest(grade=grade, accel=accel):
          self.controller = make_controller()
          self.state = make_state()
          pitch = math.atan(grade)
          self.control = make_control(pitch=pitch)
          self.control.actuators.longControlState = "stopping"
          self.controller.pitch_filter.x = pitch
          mode, demand = self.update(accel)
          self.assertEqual(mode, 0xb)
          self.assertTrue(self.controller.stop_hold_latched)
          self.assertAlmostEqual(demand, expected)
          self.assertAlmostEqual(self.output.accel, demand)

  def test_powertrain_accel_logging_remains_the_net_request(self):
    self.state = make_state(speed=0., minimum=8.)
    pitch = math.atan(0.05)
    self.controller.pitch_filter.x = pitch
    self.assertEqual(self.update(1.)[0], 0x1)
    self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)
    self.assertAlmostEqual(self.output.accel, 1. + math.sin(pitch) * ACCELERATION_DUE_TO_GRAVITY)
    self.control.longActive = False
    self.update(1.)
    self.assertEqual(self.output.accel, 0.)

  def test_signed_demand_holds_0xa_until_release(self):
    for accel, expected in ((-0.3, -30.), (0., 0.), (0.02, 2.), (0.1, 10.), (-0.05, -5.)):
      self.assertEqual(self.update(accel), (0xa, expected / 100))
    self.assertEqual(self.controller.axle_torque_cmd, -650.)
    self.assertEqual(self.update(0.3), (0xa, 0.3))  # Still below the released-creep handoff threshold.
    self.assertEqual(self.update(0.5), (0x1, 0.))
    for accel in (0.3, 0.2, 0.15, 0.3):
      self.assertEqual(self.update(accel), (0x1, 0.))
    self.assertEqual(self.update(0.1), (0xa, 0.1))

  def test_stop_intent_drops_positive_request(self):
    self.update(-0.3)
    self.assertEqual(self.update(0.1), (0xa, 0.1))
    # committing to the stop: near-stop submode, no positive request, and the hold outlives the stopping state
    self.control.actuators.longControlState = "stopping"
    self.assertEqual(self.update(0.1), (0xb, 0.))
    self.assertEqual(self.update(-0.3), (0xb, -0.3))
    self.control.actuators.longControlState = "pid"
    self.assertEqual(self.update(-0.3), (0xb, -0.3))

  def test_other_platforms_keep_lookup_allocation(self):
    self.controller = make_controller(CAR.CHEVROLET_MALIBU)
    self.assertFalse(self.controller.params.ASCM_LONG)
    mode, demand = self.update(-0.3)
    self.assertEqual(mode, 0xa)
    self.assertLess(demand, 0.)
    self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)
    self.assertEqual(self.update(0.1), (0x1, 0.))

  def test_disengagement_clears_retained_path(self):
    self.update(-0.3)
    self.assertEqual(self.update(0.1), (0xa, 0.1))
    # CC.enabled can remain true for lateral control while longitudinal is inactive.
    self.control.longActive = False
    self.assertEqual(self.update(0.), (0x1, 0.))
    self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)

  def test_near_stop_mode_is_held_through_a_flicker(self):
    self.control.actuators.longControlState = "stopping"
    self.assertEqual(self.update(-1.0), (0xb, -1))
    self.control.actuators.longControlState = "pid"
    for accel, demand in ((-0.05, -0.05), (0.07, 0.), (0.14, 0.)):
      self.assertEqual(self.update(accel), (0xb, demand))
    # intent below the creep floor: the brake controller keeps the request and eases it in 0xA
    self.assertEqual(self.update(0.32), (0xa, 0.32))
    # intent above it: torque
    self.assertEqual(self.update(0.5), (0x1, 0.))
    self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)

  def test_near_stop_mode_is_volt_only(self):
    self.controller = make_controller(flags=0)  # no two-owner allocation: the lookup tables and plain 0xA
    self.control.actuators.longControlState = "stopping"
    self.assertEqual(self.update(-2.0)[0], 0xa)  # the lookup tables brake here; no near-stop submode

  def test_stopping_still_sends_full_stop_mode(self):
    self.control.actuators.longControlState = "stopping"
    self.state.out.standstill = True
    self.state.out.cruiseState.standstill = True
    self.assertEqual(self.update(-2.), (0xd, -2))

  def test_manual_resume_releases_brake_hold_before_wheel_motion(self):
    for grade, accel, owner, mode in ((0., 0.5, LongOwner.BRAKE, 0xa),
                                      (-0.05, 0.5, LongOwner.BRAKE, 0xa),
                                      (-0.15, 0.5, LongOwner.BRAKE, 0xa),
                                      (0., 1., LongOwner.POWERTRAIN, 0x1)):
      with self.subTest(grade=grade, accel=accel):
        self.controller = make_controller()
        self.controller.CP.autoResumeSng = False
        self.state = make_state(speed=0., minimum=8., standstill=True, cruise_standstill=True)
        self.control = make_control()
        self.controller.pitch_filter.x = math.atan(grade)
        self.control.actuators.longControlState = "stopping"
        self.assertEqual(self.update(-2.)[0], 0xd)
        # Until longcontrol authorizes a launch, the stopping state keeps the hold.
        self.assertEqual(self.update(accel)[0], 0xd)
        self.state.out.cruiseState.standstill = False  # driver resume acknowledged by the ECM
        self.control.actuators.longControlState = "pid"
        # A brief cancellation or weak request must not release the stop latch.
        self.assertEqual(self.update(0.1)[0], 0xd)
        self.assertTrue(self.controller.stop_hold_latched)
        self.assertEqual(self.update(accel)[0], mode)
        self.assertFalse(self.controller.stop_hold_latched)
        self.assertEqual(self.controller.long_owner, owner)
        self.assertTrue(self.state.out.standstill)
        self.controller.frame = self.tick * 4
        _, messages = self.controller.update(self.control.as_reader(), self.state, 0)
        # Brake hold release does not alter the gateway powertrain handshake.
        self.assertEqual(self.powertrain_command(messages)[:2], (1, 1))

  def powertrain_command(self, messages):
    parser = CANParser(DBC[CAR.CHEVROLET_VOLT][Bus.pt], [("ACCPowertrainCmd", 25)], CanBus.POWERTRAIN)
    parser.update([[0, messages]])
    v = parser.vl["ACCPowertrainCmd"]
    return int(v["ACCActive"]), int(v["ACCFullStopActive"]), v["AxleTorqueCmd"]

  def test_standstill_keeps_the_acc_request_asserted(self):
    self.controller = make_controller()
    self.assertFalse(self.controller.CP.autoResumeSng)
    self.state.out.standstill = True
    self.state.out.cruiseState.standstill = True
    self.update(0.5)
    self.controller.frame = self.tick * 4
    _, msgs = self.controller.update(self.control.as_reader(), self.state, 0)
    self.assertEqual(self.powertrain_command(msgs)[:2], (1, 1))

  def test_disengagement_clears_hold_and_uses_platform_idle_mode(self):
    def command(accel):
      self.control.actuators.accel = accel
      messages = update_longitudinal(self.control.as_reader(), self.state, 0)
      data = next(message[1] for message in messages if message[0] == 0x315)
      return data[0] >> 4, ((data[0] & 0xF) << 8) | data[1]

    for car, network in ((CAR.CHEVROLET_VOLT, "gateway"), (CAR.CHEVROLET_BOLT_EUV, "fwdCamera")):
      for enabled in (False, True):
        with self.subTest(car=car, enabled=enabled):
          flags = GMFlags.ASCM_LONG if car == CAR.CHEVROLET_VOLT else 0
          self.controller = make_controller(car=car, network=network, flags=int(flags))
          self.controller.CP.autoResumeSng = False
          update_longitudinal = (self.controller.update_ascm_longitudinal if self.controller.params.ASCM_LONG
                                else self.controller.update_legacy_longitudinal)
          self.state = make_state(speed=0., minimum=8., standstill=True, cruise_standstill=True)
          self.control = make_control()
          self.control.actuators.longControlState = "stopping"
          self.assertEqual(command(-1.)[0], 0xD)
          self.control.enabled = enabled
          self.control.longActive = False
          expected_mode = 0x9 if enabled and car == CAR.CHEVROLET_BOLT_EUV else 0x1
          for accel in (-1., 0., 0.1):
            self.assertEqual(command(accel), (expected_mode, 0))
            self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)
            self.assertFalse(self.controller.stop_hold_latched)

  def test_frame_encodes_the_signed_request_and_its_checksum(self):
    for accel, counts in ((-4., -400), (-1.1, -110), (-0.01, -1), (0., 0), (0.01, 1), (0.32, 32), (2., 200), (-1.16, -116)):
      data = gmcan.create_friction_brake_command(self.controller.packer_ch, CanBus.OBSTACLE, accel, 2, 0xa)[1]
      raw = ((data[0] & 0xf) << 8) | data[1]
      self.assertEqual(raw, counts & 0xfff)
      self.assertEqual(raw - 0x1000 if raw >= 0x800 else raw, counts)
      self.assertEqual(int.from_bytes(data[2:4], "big"), (0x10000 - (0xa << 12) - raw - 2) & 0xffff)

  def test_legacy_lookup_matches_upstream_brake_frames(self):
    # Exercise the controller's mode selection as well as its magnitude. Zero rounded counts must be idle.
    for car, network in ((CAR.CHEVROLET_VOLT, "gateway"), (CAR.CADILLAC_ATS, "gateway"),
                         (CAR.CHEVROLET_BOLT_EUV, "fwdCamera")):
      controller = make_controller(car=car, network=network, flags=0)
      controller.CP.autoResumeSng = False
      p = controller.params
      control = make_control()
      bus = CanBus.POWERTRAIN if network == "fwdCamera" else CanBus.CHASSIS
      # Include the sub-count region at the lookup's release boundary alongside a full-range sweep.
      edge = p.LEGACY_BRAKE_ACCEL_BP[1]
      width_per_count = (edge - p.LEGACY_BRAKE_ACCEL_BP[0]) / 400.
      requests = list(np.arange(-4.5, 2.5, 0.01)) + [edge - c * width_per_count for c in (0.4, 0.5, 0.6, 1.5, 2.5)]
      for standstill, stopping in ((False, False), (True, False), (True, True)):
        with self.subTest(car=car, standstill=standstill, stopping=stopping):
          state = make_state(speed=0. if standstill else 1., standstill=standstill)
          control.actuators.longControlState = "stopping" if stopping else "pid"
          for idx, accel in enumerate(requests):
            control.actuators.accel = float(accel)
            old_counts = int(round(np.interp(control.actuators.accel, p.LEGACY_BRAKE_ACCEL_BP, [400., 0.])))
            mode = 0x9 if car == CAR.CHEVROLET_BOLT_EUV else 0x1
            if old_counts > 0:
              mode = 0xd if standstill and (network != "fwdCamera" or stopping) else 0xa
            expected = gmcan.create_friction_brake_command(controller.packer_ch, bus, -old_counts / 100., idx % 4, mode)
            messages = controller.update_legacy_longitudinal(control.as_reader(), state, idx % 4)
            actual = next(message for message in messages if message[0] == 0x315)
            self.assertEqual(actual, expected, msg=f"accel={control.actuators.accel}")

  def test_legacy_half_counts_keep_upstream_ties_to_even(self):
    controller = make_controller(flags=0)
    controller.CP.autoResumeSng = False
    controller.params.LEGACY_BRAKE_ACCEL_BP = [-4., 0.]  # exactly representable half-count inputs
    control = make_control()
    for accel, counts in ((-1.125, 112), (-1.375, 138)):
      with self.subTest(accel=accel):
        control.actuators.accel = accel
        messages = controller.update_legacy_longitudinal(control.as_reader(), make_state(), 0)
        data = next(message[1] for message in messages if message[0] == 0x315)
        self.assertEqual(((data[0] & 0xf) << 8) | data[1], (-counts) & 0xfff)

if __name__ == "__main__":
  unittest.main()


class TestNearStopHold(unittest.TestCase):
  """Committing to a stop turns the near-stop hold on; only clear launch intent turns it off."""

  def setUp(self):
    self.controller = make_controller()
    self.state = make_state(speed=0.1, minimum=8.)
    self.control = make_control()
    self.p = self.controller.params

  def allocate(self, accel, stopping, pitch=None):
    self.control.actuators.longControlState = "stopping" if stopping else "pid"
    self.control.actuators.accel = accel
    if pitch is not None:
      self.control.orientationNED = [0., pitch, 0.]
    reader = self.control.as_reader()
    for _ in range(4):  # one 25 Hz allocation spans four control frames of pitch filtering
      self.controller.update_pitch(reader)
    self.controller.update_ascm_longitudinal(reader, self.state, 0)
    return self.controller.axle_torque_cmd, self.controller.brake_accel_cmd

  def test_flicker_keeps_the_hold(self):
    # longcontrol's ramp is at -1.16 when shouldStop flickers off and the PID hands over -0.05, then up to +0.14
    self.assertEqual(self.allocate(-1.16, stopping=True), (-650., -1.16))
    self.assertTrue(self.controller.stop_hold_latched)
    for accel, expected in ((-0.05, -0.05), (0.02, 0.), (0.07, 0.), (0.10, 0.), (0.14, 0.), (0.10, 0.)):
      self.assertEqual(self.allocate(accel, stopping=False), (-650., expected))
      self.assertTrue(self.controller.stop_hold_latched)
      self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
    self.assertEqual(self.allocate(-0.02, stopping=True), (-650., -0.02))

  def test_release_returns_to_ordinary_allocation(self):
    self.allocate(-2.0, stopping=True)
    # below the creep floor the brake controller keeps the request and eases it
    gas, brake = self.allocate(0.32, stopping=False)
    self.assertFalse(self.controller.stop_hold_latched)
    self.assertEqual((gas, brake), (-650., 0.32))
    self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
    # above it the powertrain takes over
    gas, brake = self.allocate(1.0, stopping=False)
    self.assertEqual(self.controller.long_owner, LongOwner.POWERTRAIN)
    self.assertEqual(brake, 0.)
    self.assertGreater(gas, 0.)

  def test_downhill_release_stays_with_the_brakes(self):
    self.state = make_state(speed=0., minimum=8., standstill=True)
    for _ in range(50):  # settle the pitch filter on a steep descent
      self.allocate(-2.0, stopping=True, pitch=-math.radians(45.))
    gas, brake = self.allocate(0.5, stopping=False)
    self.assertFalse(self.controller.stop_hold_latched)
    self.assertEqual(self.controller.long_owner, LongOwner.BRAKE)
    self.assertEqual(gas, -650.)
    self.assertEqual(brake, 0.5)  # Gravity keeps brake ownership; EBCM receives the positive vehicle target.

  def test_hold_needs_a_stop_first(self):
    for accel in (0.1, -0.5, 0.2):
      self.allocate(accel, stopping=False)
      self.assertFalse(self.controller.stop_hold_latched)

  def test_inactive_clears_the_hold(self):
    self.allocate(-2.0, stopping=True)
    self.control.longActive = False
    self.controller.update(self.control.as_reader(), self.state, 0)
    self.assertFalse(self.controller.stop_hold_latched)
