"""Exercise controlsd's real cruise flags through the GM c11 command sender."""
from types import SimpleNamespace
from unittest.mock import Mock
import unittest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.ascm import AscmSupervisor
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_ascm import feed
from opendbc.car.gm.tests.test_volt_longitudinal import make_control, make_state
from opendbc.car.gm.values import CAR, DBC
from openpilot.cereal import log
from openpilot.selfdrive.car.car_events import CarEvents
from openpilot.selfdrive.controls.controlsd import Controls
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

  def step(self, active=True):
    now_nanos = 1_000_000_000 + 40_000_000 * self.seq
    if self.seq > 2:
      feed(self.state.ascm, self.seq, now_nanos * 1e-9, active=active)
    self.controls.publish(self.control, log.ControlsState.LateralPIDState())
    self.controller.frame = self.seq * 4
    _, messages = self.controller.update(self.control.as_reader(), self.state, now_nanos)
    self.seq += 1
    return {m[0]: m[1] for m in messages}

  def test_ecu_cruise_feedback_keeps_commands_active(self):
    self.assertFalse(self.cp.pcmCruise)
    # The drive transitioned OFF -> ON -> OFF while openpilot stayed enabled.
    # Keep ON for longer than the confirmation timeout, then test both edges.
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
    # Exceed the confirmation timeout while overridden. ACCActive never drops.
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
