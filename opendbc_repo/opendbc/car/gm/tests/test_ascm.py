import itertools
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from opendbc.can import CANPacker
from opendbc.car.gm import gmcan
from opendbc.car.gm.ascm import AscmSupervisor, decode, Owner
from opendbc.car.gm.tests.test_volt_longitudinal import make_controller, make_state, make_control
from opendbc.car.gm.values import CAR, AccState


def report(cpu, seq, owner=Owner.OPENPILOT, generation=1, available=True, forwarding_permitted=None, counts=None):
  counts = counts or (seq, seq, seq)
  if forwarding_permitted is None:
    forwarding_permitted = owner == Owner.OPENPILOT and available
  return bytes([0x20 | owner | (4 if available else 0) | (8 if forwarding_permitted else 0), seq,
                0x11 if cpu == 1 else 0xF1, 0 if cpu == 1 else 0xF0,
                counts[0], counts[1] if cpu == 1 else 0, counts[2] if cpu == 1 else 0, generation])


def feed(supervisor, seq, now, **kwargs):
  supervisor.receive(0x37D, report(1, seq, **kwargs), 1, now)
  supervisor.receive(0x37C, report(2, seq, **kwargs), 2, now)


def button(kind, pressed=True):
  return SimpleNamespace(type=kind, pressed=pressed)


class TestC11Supervisor(unittest.TestCase):
  def setUp(self):
    self.s = AscmSupervisor()

  def qualify(self, **kwargs):
    for seq in range(3):
      feed(self.s, seq, 1. + seq * .04, **kwargs)

  def test_pinned_vectors(self):
    vectors = json.loads((Path(__file__).parent / 'ascm_c11_vectors.json').read_text())
    for v in vectors['valid']:
      r = decode(v['identifier'], bytes.fromhex(v['payload']), {'object': 1, 'chassis': 2}[v['network']])
      self.assertEqual(r.owner.name.lower(), v['expected']['owner'])
      # Bit 3 keeps its wire position; own-v1 changes it to session permission.
      self.assertEqual(r.forwarding_permitted, v['expected']['active'])
      self.assertEqual(r.reasons, tuple(v['expected']['reasons'][key] for key in (('steering', 'longitudinal') if v['identifier'] == 0x37D else ('brake',))))

    for v in vectors['invalid'] + vectors['transport_invalid']:
      with self.assertRaises(ValueError):
        decode(v['identifier'], bytes.fromhex(v['payload']), {'pt': 0, 'object': 1, 'chassis': 2}[v['network']],
               extended=v.get('extended', False), remote=v.get('remote', False))

  def test_qualification_and_wrap(self):
    for seq, now in ((254, 1.), (255, 1.04), (0, 1.08)):
      feed(self.s, seq, now)
      self.assertEqual(self.s.permitted(now), seq == 0)

  def test_transport_and_schema(self):
    valid = report(2, 1)
    for addr, bus in ((0x37E, 1), (0x37C, 1), (0x37D, 2)):
      with self.assertRaises(ValueError):
        decode(addr, valid, bus)
    for kwargs in ({'extended': True}, {'remote': True}):
      with self.assertRaises(ValueError):
        decode(0x37C, valid, 2, **kwargs)
    for offset, value in ((0, 0x36), (0, 0x27), (0, 0x2C), (0, 0x25), (2, 0xF3), (3, 0xF5), (5, 1), (6, 1)):
      bad = bytearray(valid)
      bad[offset] = value
      with self.assertRaises(ValueError):
        decode(0x37C, bad, 2)
    for size in (0, 7, 9):
      with self.assertRaises(ValueError):
        decode(0x37C, bytes(size), 2)

  def test_duplicate_does_not_refresh(self):
    self.qualify()
    feed(self.s, 2, 1.22)
    self.assertFalse(self.s.permitted(1.25))
    feed(self.s, 3, 1.26)
    self.assertFalse(self.s.permitted(1.26))

  def test_each_output_has_own_deadline(self):
    for index in range(4):
      self.s = AscmSupervisor()
      self.qualify()
      for seq in range(3, 10):
        now = 1. + seq * .04
        for cpu, addr, bus in ((1, 0x37D, 1), (2, 0x37C, 2)):
          counts = [seq] * 3
          if cpu == 1 and index < 3:
            counts[index] = 2
          elif cpu == 2 and index == 3:
            counts[0] = 2
          self.s.receive(addr, report(cpu, seq, counts=counts), bus, now)
        permitted = self.s.permitted(now)
      self.assertFalse(permitted, index)

  def test_either_processor_missing_faulted_or_restarted(self):
    for cpu, addr, bus in ((1, 0x37D, 1), (2, 0x37C, 2)):
      self.s = AscmSupervisor()
      self.qualify()
      self.s.receive(addr, report(cpu, 3, generation=2), bus, 1.12)
      self.assertFalse(self.s.permitted(1.12))
      self.qualify()
      self.s.receive(addr, report(cpu, 3, available=False), bus, 1.12)
      self.assertFalse(self.s.permitted(1.12))
      self.qualify()
      self.s.receive(addr, report(cpu, 8), bus, 1.32)
      self.assertFalse(self.s.permitted(1.32))

  def test_first_set_press_release_handshake(self):
    self.qualify(owner=Owner.UNSELECTED)
    self.assertFalse(self.s.driver_request(1.08, [button('decelCruise')], True))
    self.s.receive(0x37D, report(1, 3), 1, 1.12)
    self.assertFalse(self.s.driver_request(1.12, [button('decelCruise', False)], True))
    self.s.receive(0x37C, report(2, 3), 2, 1.13)
    self.assertTrue(self.s.driver_request(1.13, [], True))
    self.assertFalse(self.s.driver_request(1.14, [], True))

  def test_press_during_selection_disagreement_is_retained(self):
    for first_cpu in (1, 2):
      for kind in ('decelCruise', 'accelCruise'):
        with self.subTest(first_cpu=first_cpu, kind=kind):
          self.s = AscmSupervisor()
          self.qualify(owner=Owner.UNSELECTED)
          addr, bus = (0x37D, 1) if first_cpu == 1 else (0x37C, 2)
          self.s.receive(addr, report(first_cpu, 3), bus, 1.12)
          self.assertFalse(self.s.driver_request(1.12, [button(kind)], True))
          self.assertIsNotNone(self.s.pending_until)
          self.assertFalse(self.s.permitted(1.12))
          feed(self.s, 4, 1.16)
          events = [button(kind, False)] if kind == 'decelCruise' else []
          self.assertTrue(self.s.driver_request(1.16, events, True))
          self.assertFalse(self.s.driver_request(1.16, [], True))

  def test_disagreement_intent_requires_health_and_matching_generation(self):
    for cause in ('oem', 'generation', 'unavailable', 'stale', 'pedal'):
      with self.subTest(cause=cause):
        self.s = AscmSupervisor()
        self.qualify(owner=Owner.UNSELECTED)
        self.s.receive(0x37D, report(1, 3), 1, 1.12)
        if cause == 'oem':
          self.s.receive(0x37C, report(2, 3, owner=Owner.OEM, available=False), 2, 1.12)
        elif cause == 'generation':
          self.s.receive(0x37C, report(2, 3, generation=2), 2, 1.12)
        elif cause == 'unavailable':
          self.s.receive(0x37C, report(2, 3, available=False), 2, 1.12)
        now = 1.4 if cause == 'stale' else 1.12
        self.assertFalse(self.s.driver_request(now, [button('decelCruise')], cause != 'pedal'))
        self.assertIsNone(self.s.pending_until)

  def test_pending_cancel_pedal_timeout_reset_and_unavailability(self):
    for cause in ('cancel', 'pedal', 'timeout', 'reset', 'unavailable'):
      self.s = AscmSupervisor()
      self.qualify(owner=Owner.UNSELECTED)
      self.s.receive(0x37D, report(1, 3), 1, 1.09)
      self.s.driver_request(1.09, [button('decelCruise')], True)
      self.assertIsNotNone(self.s.pending_until)
      if cause == 'reset':
        feed(self.s, 3, 1.12, generation=2)
      elif cause == 'unavailable':
        feed(self.s, 3, 1.12, available=False)
      elif cause == 'timeout':
        for seq in range(3, 24):
          self.s.receive(0x37D, report(1, seq), 1, 1. + seq * .04)
          self.s.receive(0x37C, report(2, seq, owner=Owner.UNSELECTED), 2, 1. + seq * .04)
      self.s.driver_request(1.92 if cause == 'timeout' else 1.12,
                            [button('cancel')] if cause == 'cancel' else [], cause != 'pedal')
      for seq in range(24, 27):
        feed(self.s, seq, 2. + (seq - 24) * .04)
      self.assertFalse(self.s.driver_request(2.08, [button('decelCruise', False)], True), cause)

  def test_oem_and_recovery_never_enable(self):
    self.qualify(owner=Owner.OEM, available=False)
    self.assertTrue(self.s.oem_owned)
    self.assertFalse(self.s.driver_request(1.08, [button('accelCruise')], True))
    for seq in range(3, 6):
      feed(self.s, seq, 1. + seq * .04)
    self.assertFalse(self.s.driver_request(1.2, [], True))
    self.assertTrue(self.s.driver_request(1.2, [button('accelCruise')], True))

  def test_both_permissions_required_before_entry(self):
    self.qualify(forwarding_permitted=False)
    self.assertTrue(self.s.healthy(1.08))
    self.assertFalse(self.s.driver_request(1.08, [button('accelCruise')], True))
    self.s.receive(0x37D, report(1, 3), 1, 1.12)
    self.assertFalse(self.s.driver_request(1.12, [], True))
    # A duplicate may not grant permission, even when its bit has changed.
    self.s.receive(0x37C, report(2, 2), 2, 1.12)
    self.assertFalse(self.s.permitted(1.12))
    self.s.receive(0x37C, report(2, 3), 2, 1.13)
    self.assertTrue(self.s.driver_request(1.13, [], True))

  def test_permission_does_not_create_driver_intent(self):
    self.qualify()
    for seq in range(3, 12):
      now = 1. + seq * .04
      feed(self.s, seq, now)
      self.assertTrue(self.s.permitted(now))
      self.assertFalse(self.s.driver_request(now, [], True))

  def test_either_permission_loss_invalidates_pending_intent(self):
    for cpu, address, bus in ((1, 0x37D, 1), (2, 0x37C, 2)):
      with self.subTest(cpu=cpu):
        self.s = AscmSupervisor()
        self.qualify()
        epoch = self.s.epoch
        self.assertFalse(self.s.driver_request(1.08, [button('decelCruise')], True))
        self.s.receive(address, report(cpu, 3, forwarding_permitted=False), bus, 1.12)
        self.assertGreater(self.s.epoch, epoch)
        self.assertFalse(self.s.permitted(1.12))
        for seq in range(4, 7):
          feed(self.s, seq, 1. + seq * .04)
        self.assertTrue(self.s.permitted(1.24))
        self.assertFalse(self.s.driver_request(1.24, [button('decelCruise', False)], True))


class TestC11Commands(unittest.TestCase):
  def setUp(self):
    self.packer = CANPacker('gm_global_a_powertrain_generated')

  def test_checksum_vectors_and_boundaries(self):
    for torque, idx, active, expected in ((-6, 0, True, '0142c00000bd4000'),
                                         (-6.125, 3, True, 'c142bfff00bd3ffe'),
                                         (-6, 0, False, '0042c00001bd4000'),
                                         (43001.875, 3, True, 'c147ffff00b7fffe')):
      self.assertEqual(gmcan.create_acc_powertrain_command(self.packer, 1, torque, idx, active, False)[1].hex(), expected)
    for idx, active, stop, high, low in itertools.product(range(4), (False, True), (False, True), (0, 1, 255, 256, 2047), (0, 1, 253, 254, 255)):
      torque = ((high << 8) | low) * .125 - 22534
      d = gmcan.create_acc_powertrain_command(self.packer, 1, torque, idx, active, stop)[1]
      protected = ((d[0] & 1) << 24) | int.from_bytes(d[1:4], 'big')
      checksum = ((d[4] & 1) << 24) | int.from_bytes(d[5:8], 'big')
      self.assertEqual((protected + (d[0] >> 6) + checksum) & 0x1FFFFFF, 0)

  def test_inactive_streams_and_passive(self):
    controller = make_controller(flags=CAR.CHEVROLET_VOLT.config.flags)
    state, control = make_state(), make_control()
    state.ascm = AscmSupervisor()
    control.latActive = True
    sent = []
    for frame in range(101):
      _, messages = controller.update(control.as_reader(), state, int((1 + frame * .01) * 1e9))
      sent.extend(messages)
      for m in messages:
        self.assertEqual(m[2], 1)
        if m[0] == 0x180:
          self.assertEqual(bytes([m[1][0] & 0xCF, m[1][1]]), b'\0\0')
          state.loopback_lka_steering_cmd_counter = (m[1][0] >> 4) & 3
          state.loopback_lka_steering_cmd_ts_nanos = int((1 + frame * .01) * 1e9)
          state.loopback_lka_steering_cmd_updated = True
        elif m[0] == 0x2CB:
          self.assertEqual(bytes([m[1][0] & 0x3F]) + m[1][1:4], bytes.fromhex('0042abe0'))
          state.ascm_next_counters[0x2CB] = ((m[1][0] >> 6) + 1) % 4
        elif m[0] == 0x37F:
          self.assertEqual(m[1][:2], bytes.fromhex('1000'))
          state.ascm_next_counters[0x37F] = ((m[1][4] & 3) + 1) % 4
          self.assertEqual((int.from_bytes(m[1][:2], 'big') + int.from_bytes(m[1][2:4], 'big') + (m[1][4] & 3)) & 0xFFFF, 0)
        elif m[0] == 0x370:
          self.assertEqual(m[1].hex(), '010000000100')
        else:
          self.fail(hex(m[0]))
    self.assertEqual({m[0] for m in sent}, {0x180, 0x2CB, 0x37F, 0x370})
    for addr, byte, shift in ((0x180, 0, 4), (0x2CB, 0, 6), (0x37F, 4, 0)):
      counters = [(m[1][byte] >> shift) & 3 for m in sent if m[0] == addr]
      self.assertGreaterEqual(len(counters), 10)
      self.assertTrue(all((b - a) % 4 == 1 for a, b in zip(counters, counters[1:], strict=False)))
    controller.CP.passive = True
    self.assertEqual(controller.update(control.as_reader(), state, 3_000_000_000)[1], [])

  def test_brake_remap_payload_unchanged(self):
    packer = CANPacker('gm_global_a_chassis')
    for idx, mode, accel in itertools.product(range(4), (1, 10, 11, 13), (-4, -.01, 0, 2)):
      old = gmcan.create_friction_brake_command(packer, 2, accel, idx, mode)
      new = gmcan.create_friction_brake_command(packer, 1, accel, idx, mode, c11=True)
      self.assertEqual(new[1], old[1])
      self.assertEqual((new[0], new[2]), (0x37F, 1))

  def test_acc_active_resume_pulse_for_both_allocators(self):
    controller = make_controller(flags=CAR.CHEVROLET_VOLT.config.flags, auto_resume=True)
    state, control = make_state(standstill=True, cruise_standstill=True), make_control()
    control.actuators.accel = 1.
    for allocator in (controller.update_ascm_longitudinal, controller.update_legacy_longitudinal):
      self.assertFalse(allocator(control.as_reader(), state, 0)[0][1][0] & 1)
      state.cruise_standstill = False
      self.assertTrue(allocator(control.as_reader(), state, 1)[0][1][0] & 1)
      state.cruise_standstill = True


class TestC11Integration(unittest.TestCase):
  def test_pedal_input_does_not_change_ascm_health(self):
    from unittest.mock import patch
    from opendbc.car import Bus, gen_empty_fingerprint
    from opendbc.car.gm.interface import CarInterface

    fields = {'ECMEngineStatus': {'CruiseMainOn': True}, 'BCMGeneralPlatformStatus': {'SystemPowerMode': 2},
              'ASCMSteeringButton': {'ACCButtons': 1}, 'HPCMAxleTorqueLimits': {'AxleTorqueMin': -650}}
    for message, signal in (('AcceleratorPedal2', 'AcceleratorPedal2'), ('ECMAcceleratorPos', 'BrakePedalPos'),
                            ('EBCMRegenPaddle', 'RegenPaddle')):
      with self.subTest(pedal=signal):
        cp = CarInterface.get_params(CAR.CHEVROLET_VOLT, gen_empty_fingerprint(), [], False, False, False)
        ci = CarInterface(cp)
        packer = CANPacker('gm_global_a_powertrain_generated')
        with patch('opendbc.car.gm.interface.time.monotonic', return_value=1.):
          ci.update([])
        for seq in range(8):
          now = (1_000_000_000 + seq * 40_000_000) * 1e-9
          values = {name: dict(v) for name, v in fields.items()}
          if seq == 6:
            values[message] = {signal: 8 if signal == 'BrakePedalPos' else 1}
            values['ASCMSteeringButton']['ACCButtons'] = 2  # Do not grant a new RESUME with a pedal held.
          messages = [packer.make_can_msg(s.name, 0, values.get(s.name, {})) for s in ci.can_parsers[Bus.pt].message_states.values()]
          messages += [(0x37D, report(1, seq), 1), (0x37C, report(2, seq), 2)]
          with patch('opendbc.car.gm.interface.time.monotonic', return_value=now):
            ret = ci.update([(int(now * 1e9), messages)])
          if seq >= 5:
            self.assertTrue(ret.canValid and ret.ascmReady)
            self.assertEqual(ret.ascmStatus, 'Ready')
            self.assertFalse(ret.buttonEnable)
            self.assertIsNone(ci.CS.ascm.pending_until)

  def test_longitudinal_counters_follow_independent_successful_echoes(self):
    from unittest.mock import patch
    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.gm.interface import CarInterface

    for rejected in ((0x2CB,), (0x37F,), (0x2CB, 0x37F)):
      with self.subTest(rejected=rejected):
        cp = CarInterface.get_params(CAR.CHEVROLET_VOLT, gen_empty_fingerprint(), [], False, False, False)
        ci = CarInterface(cp)
        controller = make_controller(flags=cp.flags)
        control = make_control()
        control.enabled = control.longActive = False

        def receive(messages, now, ci=ci):
          with patch('opendbc.car.gm.interface.time.monotonic', return_value=now * 1e-9):
            ci.update([(now, messages)])

        receive([], 1_000_000_000)
        last_success = {0x2CB: 3, 0x37F: 3}
        for seq in range(8):
          now = 1_000_000_000 + seq * 40_000_000
          controller.frame = seq * 4
          _, messages = controller.update(control.as_reader(), ci.CS, now)
          echoes = []
          for addr, data, _bus in messages:
            if addr not in last_success:
              continue
            counter = data[0] >> 6 if addr == 0x2CB else data[4] & 3
            self.assertEqual(counter, (last_success[addr] + 1) % 4)
            if seq in (2, 3) and addr in rejected:
              # Rejected attempts and actuator-network traffic cannot advance it.
              echoes.extend([(addr, data, 193), (addr, data, 0), (addr, data, 2)])
            else:
              last_success[addr] = counter
              echoes.append((addr, data, 129))
          receive(echoes, now + 10_000_000)
        self.assertEqual(ci.CS.ascm_next_counters, {addr: (count + 1) % 4 for addr, count in last_success.items()})

  def test_interface_status_binding_and_driver_handshake(self):
    from unittest.mock import patch
    from opendbc.car import Bus, gen_empty_fingerprint
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.values import GMSafetyFlags

    cp = CarInterface.get_params(CAR.CHEVROLET_VOLT, gen_empty_fingerprint(), [], False, False, False)
    self.assertTrue(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_C11)
    self.assertTrue(cp.autoResumeSng)
    ci = CarInterface(cp)
    with patch('opendbc.car.gm.interface.time.monotonic', return_value=1.):
      ci.update([])  # register the signals the dynamic parser consumes
    packer = CANPacker('gm_global_a_powertrain_generated')

    def update(seq, buttons=1, owner=Owner.UNSELECTED, main=True, run=True, peer_owner=None):
      now = int((1. + seq * .04) * 1e9) * 1e-9
      fields = {'ECMEngineStatus': {'CruiseMainOn': main}, 'BCMGeneralPlatformStatus': {'SystemPowerMode': 2 if run else 0},
                'ASCMSteeringButton': {'ACCButtons': buttons}, 'HPCMAxleTorqueLimits': {'AxleTorqueMin': -650},
                'AcceleratorPedal2': {'CruiseState': AccState.STANDSTILL}}
      messages = [packer.make_can_msg(st.name, 0, fields.get(st.name, {})) for st in ci.can_parsers[Bus.pt].message_states.values()]
      messages += [(0x37D, report(1, seq, owner=owner), 1), (0x37C, report(2, seq, owner=owner if peer_owner is None else peer_owner), 2)]
      with patch('opendbc.car.gm.interface.time.monotonic', return_value=now):
        return ci.update([(int(now * 1e9), messages)])

    for seq in range(6):
      ret = update(seq)
    self.assertTrue(ret.canValid)
    self.assertFalse(ret.ascmReady)
    self.assertFalse(update(6, buttons=3, owner=Owner.OPENPILOT, peer_owner=Owner.UNSELECTED).buttonEnable)
    ret = update(7, owner=Owner.OPENPILOT)
    self.assertTrue(ret.buttonEnable, (ret.to_dict(), ci.CS.ascm.__dict__))
    self.assertTrue(ret.ascmReady)
    self.assertTrue(ci.CS.cruise_standstill)
    self.assertFalse(ret.cruiseState.standstill)  # Let longcontrol launch without a driver RESUME.
    self.assertFalse(update(8, owner=Owner.OPENPILOT).buttonEnable)
    self.assertFalse(update(9, owner=Owner.OPENPILOT, main=False).ascmReady)
    self.assertFalse(update(10, owner=Owner.OPENPILOT, run=False).ascmReady)
    self.assertFalse(update(11, owner=Owner.OPENPILOT).buttonEnable)

  def test_fault_recovery_needs_new_enabled_edge(self):
    controller = make_controller(flags=CAR.CHEVROLET_VOLT.config.flags)
    state, control = make_state(), make_control()
    state.ascm = AscmSupervisor()
    state.out.ascmReady = True
    control.latActive = True
    for seq in range(3):
      feed(state.ascm, seq, 1. + seq * .04)
    controller.frame = 12
    _, messages = controller.update(control.as_reader(), state, 1_080_000_000)
    self.assertTrue(next(m[1][0] & 1 for m in messages if m[0] == 0x2CB))
    self.assertTrue(controller.c11_engaged)
    state.ascm.receive(0x37C, b'bad', 2, 1.09)
    controller.update(control.as_reader(), state, 1_090_000_000)
    self.assertFalse(controller.c11_engaged)
    for seq in range(3, 6):
      feed(state.ascm, seq, 1. + seq * .04)
    controller.update(control.as_reader(), state, 1_200_000_000)
    self.assertFalse(controller.c11_engaged)
    control.enabled = False
    controller.update(control.as_reader(), state, 1_210_000_000)
    control.enabled = True
    controller.update(control.as_reader(), state, 1_220_000_000)
    self.assertTrue(controller.c11_engaged)

  def test_steering_counter_uses_own_last_loopback_and_retries_dropped_tx(self):
    controller = make_controller(flags=CAR.CHEVROLET_VOLT.config.flags)
    state, control = make_state(), make_control()
    state.ascm = AscmSupervisor()
    state.pt_lka_steering_cmd_counter = 2
    emitted = []
    for frame in (10, 20, 30):
      controller.frame = frame
      _, messages = controller.update(control.as_reader(), state, int((1 + frame * .01) * 1e9))
      emitted.append(next((m[1][0] >> 4) & 3 for m in messages if m[0] == 0x180))
    self.assertEqual(emitted, [0, 0, 0])
    state.loopback_lka_steering_cmd_updated = True
    state.loopback_lka_steering_cmd_counter = 3
    state.loopback_lka_steering_cmd_ts_nanos = 1_300_000_000
    controller.frame = 40
    _, messages = controller.update(control.as_reader(), state, 1_400_000_000)
    self.assertEqual(next((m[1][0] >> 4) & 3 for m in messages if m[0] == 0x180), 0)

  def test_first_steering_release_precedes_active_input_timeout(self):
    controller = make_controller(flags=CAR.CHEVROLET_VOLT.config.flags)
    state, control = make_state(), make_control()
    state.ascm = AscmSupervisor()
    state.out.ascmReady = True
    control.latActive = True
    for seq in range(3):
      feed(state.ascm, seq, 1. + seq * .04)
    controller.frame = 12
    _, messages = controller.update(control.as_reader(), state, 1_080_000_000)
    steer = next(m for m in messages if m[0] == 0x180)
    self.assertTrue(steer[1][0] & 8)
    state.loopback_lka_steering_cmd_updated = True
    state.loopback_lka_steering_cmd_counter = (steer[1][0] >> 4) & 3
    state.loopback_lka_steering_cmd_ts_nanos = 1_080_000_000
    control.enabled = False
    controller.frame = 15
    _, messages = controller.update(control.as_reader(), state, 1_110_000_000)
    steer = next(m for m in messages if m[0] == 0x180)
    self.assertFalse(steer[1][0] & 8)


class TestC11Engagement(unittest.TestCase):
  def setUp(self):
    self.controller = make_controller(flags=CAR.CHEVROLET_VOLT.config.flags)
    self.state, self.control = make_state(), make_control()
    self.state.ascm = AscmSupervisor()
    self.state.out.ascmReady = True
    self.control.latActive = True
    for seq in range(3):
      feed(self.state.ascm, seq, (1_000_000_000 + seq * 40_000_000) * 1e-9)

  def step(self, seq, forwarding_permitted=True):
    now_nanos = 1_000_000_000 + seq * 40_000_000
    if seq > 2:
      feed(self.state.ascm, seq, now_nanos * 1e-9, forwarding_permitted=forwarding_permitted)
    self.controller.frame = seq * 4
    _, messages = self.controller.update(self.control.as_reader(), self.state, now_nanos)
    return bool(next(m[1][0] & 1 for m in messages if m[0] == 0x2CB))

  def test_stock_cancel_does_not_interrupt_active_commands(self):
    for seq, cancel in enumerate((False, True, True, False, True, False, True), start=2):
      self.control.cruiseControl.cancel = cancel
      self.assertTrue(self.step(seq))
      self.assertTrue(self.controller.c11_engaged)

  def test_longitudinal_override_preserves_engagement(self):
    self.assertTrue(self.step(2))
    self.control.longActive = False
    self.assertTrue(self.step(3))
    self.control.longActive = True
    self.assertTrue(self.step(4))
    # A complete session disengagement followed by a new enable can rearm.
    self.control.enabled = False
    self.assertFalse(self.step(5))
    self.control.enabled = True
    self.assertTrue(self.step(6))

  def test_cancel_flag_cannot_rearm_after_fault(self):
    self.assertTrue(self.step(2))
    self.state.out.ascmReady = False
    self.control.cruiseControl.cancel = True
    self.assertFalse(self.step(3))
    self.state.out.ascmReady = True
    self.control.cruiseControl.cancel = False
    self.assertFalse(self.step(4))

  def test_actual_disengagement_releases_despite_stock_cancel(self):
    self.assertTrue(self.step(2))
    self.control.enabled = False
    self.control.cruiseControl.cancel = True
    self.assertFalse(self.step(3))
    self.control.enabled = True
    self.assertTrue(self.step(4))

  def test_cancel_flag_cannot_bypass_forwarding_permission(self):
    self.assertTrue(self.step(2))
    for seq in range(3, 9):
      self.control.cruiseControl.cancel = bool(seq % 2)
      self.assertFalse(self.step(seq, forwarding_permitted=False))
    self.assertFalse(self.controller.c11_engaged)
    self.assertEqual(self.state.ascm.reason, 'Waiting for both ASCM forwarding permissions')

  def test_permission_recovers_between_control_ticks_without_rearming(self):
    self.assertTrue(self.step(2))
    # Even if permission loss and full requalification arrive in one CAN batch,
    # the epoch records that interruption and the enabled controller must release.
    feed(self.state.ascm, 3, 1.12, forwarding_permitted=False)
    for seq in range(4, 7):
      feed(self.state.ascm, seq, 1. + seq * .04)
    self.assertTrue(self.state.ascm.permitted(1.24))
    self.assertFalse(self.step(6))
    self.assertFalse(self.controller.c11_engaged)
