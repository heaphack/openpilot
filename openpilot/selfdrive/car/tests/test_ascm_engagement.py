"""Exercise controlsd's real cruise flags through the GM c11 command sender."""
import math
from types import SimpleNamespace
from unittest.mock import Mock
import unittest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.ascm import AscmSupervisor
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_ascm import feed, report
from opendbc.car.gm.tests.test_volt_longitudinal import make_control, make_state
from opendbc.car.gm.values import CAR, DBC, LongOwner
from openpilot.cereal import log
from openpilot.selfdrive.car.car_events import CarEvents
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.controls.lib.latcontrol_steer import LatControlSteer
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.selfdrive.selfdrived.state import StateMachine
from openpilot.selfdrive.selfdrived.events import ET


class Subscriptions(dict):
  valid = {'driverAssistance': False}
  logMonoTime = {'longitudinalPlan': 0, 'modelV2': 0}


class TestC11ControlPipeline(unittest.TestCase):
  def setUp(self):
    self.cp = CarInterface.get_params(CAR.CHEVROLET_VOLT, gen_empty_fingerprint(), [], False, False, False)
    self.controller = CarController(DBC[CAR.CHEVROLET_VOLT], self.cp)
    self.state = make_state(speed=10.)
    self.state.out.canValid = True
    self.state.out.ascmReady = True
    self.state.out.gearShifter = 'drive'
    self.state.out.cruiseState.available = True
    self.state.ascm = AscmSupervisor()
    for seq in range(3):
      feed(self.state.ascm, seq, (1_000_000_000 + 40_000_000 * seq) * 1e-9)
    self.control = make_control()
    self.control.latActive = True

    # Bypass process/socket initialization; publish() and message schemas remain real.
    self.controls = Controls.__new__(Controls)
    self.controls.CP = self.cp
    self.controls.LaC = LatControlSteer(self.cp, CarInterface(self.cp), .01)
    self.controls.curvature = self.controls.desired_curvature = 0.
    self.controls.calibrated_pose = None
    self.controls.pm = Mock()
    self.controls.LoC = SimpleNamespace(long_control_state=structs.CarControl.Actuators.LongControlState.pid,
                                       pid=SimpleNamespace(p=0., i=0., f=0.))
    self.controls.sm = Subscriptions({
      'carState': self.state.out,
      'carOutput': SimpleNamespace(actuatorsOutput=structs.CarControl.Actuators()),
      'longitudinalPlan': SimpleNamespace(shouldStop=False, hasLead=False),
      'selfdriveState': log.SelfdriveState(state='enabled', enabled=True, active=True),
      'driverMonitoringState': SimpleNamespace(noResponseForceDecel=False),
    })
    self.seq = 2

  def step(self, forwarding_permitted=True):
    now_nanos = 1_000_000_000 + 40_000_000 * self.seq
    if self.seq > 2:
      feed(self.state.ascm, self.seq, now_nanos * 1e-9, forwarding_permitted=forwarding_permitted)
    self.controls.publish(self.control, log.ControlsState.LateralTorqueState())
    self.controller.frame = self.seq * 4
    _, messages = self.controller.update(self.control.as_reader(), self.state, now_nanos)
    # Model successful TX loopback. ASCM reports below are fixtures, not an ECU simulation.
    for address, data, _bus in messages:
      if address == 0x2CB:
        self.state.ascm_next_counters[address] = ((data[0] >> 6) + 1) % 4
      elif address == 0x37F:
        self.state.ascm_next_counters[address] = ((data[4] & 3) + 1) % 4
      elif address == 0x180:
        self.state.loopback_lka_steering_cmd_updated = True
        self.state.loopback_lka_steering_cmd_counter = (data[0] >> 4) & 3
        self.state.loopback_lka_steering_cmd_ts_nanos = now_nanos
    self.seq += 1
    return {m[0]: m[1] for m in messages}

  def test_ecu_cruise_feedback_keeps_commands_active(self):
    self.assertFalse(self.cp.pcmCruise)
    # The drive transitioned OFF -> ON -> OFF while openpilot stayed enabled.
    # Keep ON across several status reports, then test both edges.
    for cruise_enabled in (False, True, True, True, True, True, False, True):
      self.state.out.cruiseState.enabled = cruise_enabled
      messages = self.step()
      self.assertEqual(self.control.cruiseControl.cancel, cruise_enabled)
      self.assertTrue(messages[0x2CB][0] & 1)
      self.assertTrue(messages[0x180][0] & 8)
      self.assertTrue(messages[0x370][2] & 0x80)

  def test_physical_cancel_still_disables_both_axes(self):
    self.assertTrue(self.step()[0x2CB][0] & 1)
    self.state.out.cruiseState.enabled = True
    self.state.out.buttonEvents = [structs.CarState.ButtonEvent(type='cancel', pressed=True)]
    events = CarEvents(self.cp).update(self.state.out, self.state.out, self.control)
    machine = StateMachine()
    machine.state = log.SelfdriveState.OpenpilotState.enabled
    machine.update(events)
    self.assertEqual(machine.state, log.SelfdriveState.OpenpilotState.disabled)
    self.control.enabled = self.control.latActive = self.control.longActive = False
    messages = self.step()
    self.assertTrue(self.control.cruiseControl.cancel)
    self.assertFalse(messages[0x2CB][0] & 1)
    self.assertFalse(messages[0x180][0] & 8)
    self.assertEqual(messages[0x37F][:2], bytes.fromhex('1000'))

  def test_brake_and_regen_use_normal_driver_disable(self):
    for pedal in ('brakePressed', 'regenBraking'):
      with self.subTest(pedal=pedal):
        self.setUp()
        self.assertTrue(self.step()[0x2CB][0] & 1)
        previous = self.state.out.as_reader().as_builder()
        setattr(self.state.out, pedal, True)
        events = CarEvents(self.cp).update(self.state.out, previous, self.control)
        # selfdrived adds this for the rising brake/regen edge.
        events.add(log.OnroadEvent.EventName.pedalPressed)
        self.assertNotIn(log.OnroadEvent.EventName.ascmUnavailable, events.names)
        machine = StateMachine()
        machine.state = log.SelfdriveState.OpenpilotState.enabled
        machine.update(events)
        self.assertEqual(machine.state, log.SelfdriveState.OpenpilotState.disabled)
        self.assertIn(ET.USER_DISABLE, machine.current_alert_types)
        self.assertNotIn(ET.IMMEDIATE_DISABLE, machine.current_alert_types)
        # Even before controlsd processes that disable, the final sender gate releases.
        messages = self.step()
        self.assertFalse(messages[0x2CB][0] & 1)
        self.assertFalse(messages[0x180][0] & 8)
        self.assertEqual(messages[0x37F][:2], bytes.fromhex('1000'))

  def test_gas_override_retains_steering_and_session_then_resumes(self):
    self.control.actuators.accel = 1.
    self.assertTrue(self.step()[0x2CB][0] & 1)
    machine = StateMachine()
    machine.state = log.SelfdriveState.OpenpilotState.enabled
    # Stay overridden across several permission reports. ACCActive never drops.
    for _ in range(6):
      self.state.out.gasPressed = True
      events = CarEvents(self.cp).update(self.state.out, self.state.out, self.control)
      machine.update(events)
      self.assertEqual(machine.state, log.SelfdriveState.OpenpilotState.overriding)
      self.assertNotIn(log.OnroadEvent.EventName.ascmUnavailable, events.names)
      # Leave the incoming longActive true to exercise immediate pedal handling
      # before controlsd's next update; normal controlsd will set it false.
      messages = self.step()
      self.assertTrue(messages[0x180][0] & 8)
      self.assertTrue(messages[0x2CB][0] & 1)
      self.assertEqual(messages[0x2CB][1:4], bytes.fromhex('42abe0'))
      self.assertEqual(messages[0x37F][:2], bytes.fromhex('1000'))
      self.assertTrue(messages[0x370][2] & 0x80)
    self.state.out.gasPressed = False
    events = CarEvents(self.cp).update(self.state.out, self.state.out, self.control)
    machine.update(events)
    self.assertEqual(machine.state, log.SelfdriveState.OpenpilotState.enabled)
    self.assertTrue(self.step()[0x2CB][0] & 1)
    self.assertGreater(self.controller.axle_torque_cmd, -650.)

  def test_fault_during_gas_override_still_disables(self):
    self.assertTrue(self.step()[0x2CB][0] & 1)
    self.state.out.gasPressed = True
    self.assertTrue(self.step()[0x2CB][0] & 1)
    self.state.out.ascmReady = False
    events = CarEvents(self.cp).update(self.state.out, self.state.out, self.control)
    machine = StateMachine()
    machine.state = log.SelfdriveState.OpenpilotState.overriding
    machine.update(events)
    self.assertEqual(machine.state, log.SelfdriveState.OpenpilotState.disabled)
    self.assertIn(ET.IMMEDIATE_DISABLE, machine.current_alert_types)
    self.assertFalse(self.step()[0x2CB][0] & 1)
    self.state.out.ascmReady = True
    self.state.out.gasPressed = False
    self.assertFalse(self.step()[0x2CB][0] & 1)  # Recovery alone never rearms.

  def test_gas_override_releases_standstill_hold_without_cancelling(self):
    self.state.out.standstill = True
    self.state.cruise_standstill = True
    self.state.out.vEgo = 0.
    self.control.actuators.accel = -2.
    self.control.actuators.longControlState = 'stopping'
    self.assertEqual(self.step()[0x37F][0] >> 4, 0xD)
    self.state.out.gasPressed = True
    messages = self.step()
    self.assertTrue(messages[0x2CB][0] & 1)
    self.assertEqual(messages[0x2CB][1:4], bytes.fromhex('42abe0'))  # Inactive torque, stop bits clear.
    self.assertEqual(messages[0x37F][:2], bytes.fromhex('1000'))
    self.assertTrue(messages[0x370][2] & 0x80)
    self.assertTrue(self.controller.c11_engaged)

  def test_auto_resume_hold_launch_and_ecm_rearm_through_panda(self):
    from opendbc.safety.tests.libsafety.libsafety_py import libsafety, make_CANPacket

    for pitch, target, owner, brake_mode in ((0., 1., LongOwner.POWERTRAIN, 1),
                                            (-math.atan(.10), .5, LongOwner.BRAKE, 0xA)):
      with self.subTest(owner=owner):
        self.setUp()
        self.assertTrue(self.cp.autoResumeSng)
        safety_config = self.cp.safetyConfigs[0]
        libsafety.set_safety_hooks(safety_config.safetyModel.raw, safety_config.safetyParam)
        libsafety.init_tests()
        libsafety.set_controls_allowed(True)
        self.state.out.vEgo = 0.
        self.state.out.standstill = self.state.cruise_standstill = True
        self.state.out.cruiseState.enabled = True
        # CarState keeps the ECM latch internally but does not request manual resume.
        self.state.out.cruiseState.standstill = False
        self.control.orientationNED = [0., pitch, 0.]
        self.controller.pitch_filter.x = pitch
        self.controls.LoC = LongControl(self.cp)
        self.controls.LoC.last_output_accel = -2.

        def command(should_stop, accel):
          self.controls.sm['longitudinalPlan'].shouldStop = should_stop
          self.control.actuators.accel = float(self.controls.LoC.update(True, self.state.out, accel, should_stop, (-4., 2.)))
          self.control.actuators.longControlState = self.controls.LoC.long_control_state
          messages = self.step()
          for address, data in messages.items():
            self.assertTrue(libsafety.safety_tx_hook(make_CANPacket(address, 1, data)), hex(address))
          self.assertTrue(messages[0x180][0] & 8)
          self.assertTrue(messages[0x370][2] & 0x80)
          self.assertTrue(self.controller.c11_engaged)
          self.assertTrue(self.state.ascm.permitted((1_000_000_000 + (self.seq - 1) * 40_000_000) * 1e-9))
          self.assertFalse(self.control.cruiseControl.resume)  # No synthesized RESUME button.
          return messages

        messages = command(True, -2.)
        self.assertTrue(messages[0x2CB][0] & 1)
        self.assertEqual(messages[0x2CB][1] & 0x20, 0x20)  # ACCFullStopActive.
        self.assertEqual(messages[0x37F][0] >> 4, 0xD)
        # Brief plan flicker below launch intent must not release the stop hold.
        messages = command(False, .1)
        self.assertTrue(messages[0x2CB][0] & 1)
        self.assertEqual(messages[0x37F][0] >> 4, 0xD)
        for _ in range(6):
          messages = command(False, target)
          self.assertFalse(messages[0x2CB][0] & 1)
          self.assertEqual(messages[0x2CB][1] & 0x20, 0)
          self.assertEqual(messages[0x37F][0] >> 4, brake_mode)
          self.assertEqual(self.controller.long_owner, owner)
        # The ECM acknowledges the pulse before wheel speed necessarily rises.
        self.state.cruise_standstill = False
        messages = command(False, target)
        self.assertTrue(messages[0x2CB][0] & 1)
        self.assertEqual(messages[0x2CB][1] & 0x20, 0)
        self.assertEqual(messages[0x37F][0] >> 4, brake_mode)

  def test_interrupting_auto_resume_with_pedals_cancel_or_permission_loss(self):
    for interruption in ('gas', 'brake', 'regen', 'cancel', 'mpu1', 'mpu2'):
      with self.subTest(interruption=interruption):
        self.setUp()
        self.state.out.vEgo = 0.
        self.state.out.standstill = self.state.cruise_standstill = True
        self.control.actuators.longControlState = 'stopping'
        self.control.actuators.accel = -2.
        self.assertEqual(self.step()[0x37F][0] >> 4, 0xD)
        self.control.actuators.longControlState = 'pid'
        self.control.actuators.accel = 1.
        self.assertFalse(self.step()[0x2CB][0] & 1)

        if interruption in ('mpu1', 'mpu2'):
          cpu = 1 if interruption == 'mpu1' else 2
          self.state.ascm.receive(0x37D if cpu == 1 else 0x37C,
                                  report(cpu, self.seq, forwarding_permitted=False), cpu,
                                  (1_000_000_000 + 40_000_000 * self.seq) * 1e-9)
        elif interruption == 'cancel':
          self.control.enabled = self.control.latActive = self.control.longActive = False
        else:
          setattr(self.state.out, {'gas': 'gasPressed', 'brake': 'brakePressed', 'regen': 'regenBraking'}[interruption], True)
        messages = self.step()
        gas_override = interruption == 'gas'
        self.assertEqual(bool(messages[0x180][0] & 8), gas_override)
        self.assertEqual(bool(messages[0x370][2] & 0x80), gas_override)
        self.assertEqual(bool(messages[0x2CB][0] & 1), gas_override)
        self.assertEqual(messages[0x2CB][1:4], bytes.fromhex('42abe0'))
        self.assertEqual(messages[0x37F][:2], bytes.fromhex('1000'))
        for pedal in ('gasPressed', 'brakePressed', 'regenBraking'):
          setattr(self.state.out, pedal, False)
        for _ in range(4):
          messages.update(self.step())  # Inactive steering runs at the slower 100 ms cadence.
        self.assertEqual(self.controller.c11_engaged, gas_override)
        self.assertEqual(bool(messages[0x180][0] & 8), gas_override)
        if gas_override:
          self.assertFalse(messages[0x2CB][0] & 1)  # Resume pulse continues within the same session.
          self.assertGreater(self.controller.axle_torque_cmd, -650.)
        else:
          self.assertEqual(messages[0x37F][:2], bytes.fromhex('1000'))
