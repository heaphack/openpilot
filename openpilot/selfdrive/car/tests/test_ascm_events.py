import unittest

from opendbc.car import structs
from opendbc.car.gm.values import CAR, GMFlags
from openpilot.cereal import log
from openpilot.selfdrive.car.car_events import CarEvents
from openpilot.selfdrive.selfdrived.events import ET, EVENTS
from openpilot.selfdrive.selfdrived.state import StateMachine


class TestAscmEvents(unittest.TestCase):
  def test_authorization_loss_disables_every_engaged_state(self):
    cp = structs.CarParams(brand='gm', carFingerprint=CAR.CHEVROLET_VOLT, flags=int(GMFlags.ASCM_C11), openpilotLongitudinalControl=True)
    cs = structs.CarState(ascmReady=False, canValid=True, gearShifter='drive', vEgo=20.)
    cs.cruiseState.available = True
    for oem in (False, True):
      cs.ascmOemOwned = oem
      event_name = log.OnroadEvent.EventName.ascmOemOwned if oem else log.OnroadEvent.EventName.ascmUnavailable
      events = CarEvents(cp).update(cs, cs, structs.CarControl())
      self.assertIn(event_name, events.names)
      self.assertTrue(events.contains(ET.IMMEDIATE_DISABLE))
      for state in ('enabled', 'preEnabled', 'softDisabling', 'overriding'):
        machine = StateMachine()
        machine.state = getattr(log.SelfdriveState.OpenpilotState, state)
        machine.update(events)
        self.assertEqual(machine.state, log.SelfdriveState.OpenpilotState.disabled)
      self.assertIn(ET.NO_ENTRY, EVENTS[event_name])
    self.assertIn(ET.PERMANENT, EVENTS[log.OnroadEvent.EventName.ascmOemOwned])

  def test_readiness_does_not_generate_engagement(self):
    cp = structs.CarParams(brand='gm', carFingerprint=CAR.CHEVROLET_VOLT, flags=int(GMFlags.ASCM_C11))
    cs = structs.CarState(ascmReady=True, canValid=True, gearShifter='drive', vEgo=20.)
    cs.cruiseState.available = True
    events = CarEvents(cp).update(cs, cs, structs.CarControl())
    self.assertFalse(events.contains(ET.ENABLE))
    cs.buttonEnable = True
    events = CarEvents(cp).update(cs, cs, structs.CarControl())
    self.assertTrue(events.contains(ET.ENABLE))

  def test_non_c11_does_not_require_status(self):
    cp = structs.CarParams(brand='gm', carFingerprint=CAR.CHEVROLET_VOLT)
    cs = structs.CarState(canValid=True)
    events = CarEvents(cp).update(cs, cs, structs.CarControl())
    self.assertNotIn(log.OnroadEvent.EventName.ascmUnavailable, events.names)

  def test_missing_controls_producer_sends_inactive_c11(self):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from openpilot.selfdrive.car.card import Car

    card = Car.__new__(Car)
    card.CP = structs.CarParams(brand='gm', flags=int(GMFlags.ASCM_C11))
    card.initialized_prev = True
    card.sm = SimpleNamespace(all_alive=lambda services: False)
    card.CI = SimpleNamespace(apply=Mock(return_value=(structs.CarControl.Actuators(), [])))
    card.pm = Mock()
    cc = structs.CarControl(enabled=True, latActive=True, longActive=True)
    card.controls_update(structs.CarState(canValid=True), cc)
    sent_control = card.CI.apply.call_args.args[0]
    self.assertFalse(sent_control.enabled or sent_control.latActive or sent_control.longActive)
    card.CP.flags = 0
    card.CI.apply.reset_mock()
    card.controls_update(structs.CarState(canValid=True), cc)
    card.CI.apply.assert_not_called()
