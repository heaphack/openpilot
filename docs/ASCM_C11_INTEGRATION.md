# Volt ASCM dev-v7-c11 integration

Branch base: `nightly-chestnut-10-19-26`, `203b977c79df4bd83a999f6c31644f2b72437524`.
Contract: `ASCM/shadow_180_dev/OPENPILOT_C11_INTEGRATION_HANDOFF.txt`, prepared 2026-10-29.
This is an offline implementation, not a hardware release or authorization for live testing.

## Configuration and transport

The Volt platform explicitly selects `GMFlags.ASCM_C11`, together with the existing
`ASCM_INTERCEPTOR` and `ASCM_LONG` flags. Panda receives `GMSafetyFlags.ASCM_C11` (16).
There is no status-based autodetection: c10 and c11 share the same payload version.
Other GM configurations retain their prior routing and longitudinal allocation.
The OEM 25-bit 0x2CB checksum correction applies to all senders of that message.

This configuration requires the paired dev-v7-c11 images:

- MPU1 SHA256: `8c69f8dbd3226a89a2c5bf4c0fda012473b71c9a9f116f097080b2c806aa223e`
- MPU2 SHA256: `815c3f97e1ca0fbbaf02624d3f6905059a7d8c0ed96daaa018c62f52c25497c5`

Assumed physical mapping: PT=0, object=1, chassis=2. Verify the installed harness.
The four permitted Panda transmissions are object 0x180/DLC4, 0x2CB/DLC8,
0x37F/DLC5, and 0x370/DLC6. Brake uses the unchanged 0x315 payload/checksum.
The ASCM transmits to the actuator networks. c11 permits no direct PT/chassis
commands or replacement-ASCM ADAS keepalives. Steering advances from the last
observed own object-bus TX loopback (bus 129), starting at counter 0 and retrying
that counter until a loopback arrives. Received PT commands cannot seed it.

Inactive/release commands continue during startup, OEM ownership, disengagement,
and faults. Passive/dashcam mode sends none. Inactive UI is `010000000100`, gas
is -650 Nm with active/stop clear, brake is mode 1 with zero request, and steering
has zero torque and active clear. Gas/brake run at 25 Hz; steering uses the
existing 30 ms active and 100 ms inactive schedule. The first steering release keeps the active cadence to
avoid triggering the firmware's 60 ms active-input timeout on disengagement.

## Ownership and fault handling

`opendbc/car/gm/ascm.py` directly decodes exact-length raw frames, binding MPU1
0x37D to object and MPU2 0x37C to chassis. Raw parsing deliberately avoids CANParser
freshness semantics that would refresh on duplicate sequences. Legacy 0x37E,
wrong buses, and invalid payload schemas cannot establish readiness. Panda H7's
receive path rejects extended, remote, and CAN-FD variants of these IDs in c11
mode before the flags are lost in host serialization.

Three advancing reports per processor establish qualification. All four completion
counters must independently advance; the first report is only a baseline.
Ownership and selection generation must agree, both processors must be available,
and every input mode must be LIVE. Low-byte generation is not a reboot nonce.
Modulo wrap is supported within the observation deadlines; backward/implausible
sequence changes, counter resets, gaps, faults, and reset edges discard qualification.
Last raw local reports and a host diagnostic reason are logged in CarState's
`ascmMpu1`, `ascmMpu2`, and `ascmStatus` fields.

A fresh SET press stores at most 750 ms of driver intent, with its release required
before enabling to match Panda. RESUME uses its rising edge. While selection moves
from UNSELECTED to OPENPILOT, temporary owner disagreement holds commands inactive.
Both OPENPILOT reports are required before the pending intent produces buttonEnable.
Cancel, pedals, main/ignition disable, lost readiness, generation/reset changes,
or expiry discard the pending request. Readiness recovery never generates intent.

OEM ownership inhibits openpilot and displays a cruise-main-cycle explanation.
The host never synthesizes OFF, SET, RESUME, or LKA button messages. The firmware
retains OEM LKA suppression/restoration policy; status does not expose OEM LKA state.

The controller independently checks authorization at send time. A fault disables
both lateral and longitudinal requests, including release during braking/standstill.
Recovery while controls remains enabled cannot reactivate commands. After active
entry, both processors must report active forwarding within 160 ms; that bit is
not required before sending the first active command. Alerts immediately disable
the openpilot state machine on lost authorization.

c11 disables the legacy automatic-resume ACCActive pulse: it clears the firmware's
engagement latch. ACC standstill is reported to the normal resume-required path;
physical driver resume is required. The powertrain-versus-brake allocator remains
separate from OEM-versus-OPENPILOT ownership. Actual stop/hold/physical-resume/launch
behavior still requires a paired ASCM bench test, then separately authorized vehicle
validation. No alternate firmware rearm policy is assumed.

## Timing and validation limits

Provisional host deadlines are 160 ms per status stream, 220 ms for steering output
progress, and 160 ms each for gas, UI, and brake output progress. One advancing output
cannot extend another deadline. Qualification uses monotonic CAN receipt timestamps;
the live controller also checks monotonic time at transmission. These deadlines are
chosen to leave margin below the provisional 500 ms total target, not to claim it is
proven. A host stall detected at 220 ms, up to 10 ms host scheduling, up to 100 ms
inactive steering scheduling, and up to 120 ms firmware peer withdrawal would consume
450 ms before additional unmeasured transport/output latency. Independent fault paths
overlap; those arithmetic allowances are not measured worst-case execution times.
The firmware's reported sub-184-ms emulator command-loss result is separate evidence.

Required external validation remains: actual harness buses, object TX loopback at
startup and dropped TX, chassis status delivery, full paired-firmware first engagement,
OEM-first/late boot/OEM LKA operation, physical resume, bus-off/congestion/output stalls,
one-MPU resets, and end-to-end actuator withdrawal. Matching generation bytes cannot
reliably detect every reboot. Buffered old CAN traffic cannot be proven current from
these sequence fields alone. No live CAN, flashing, or driving was performed.
Future policy review: whether faults should clear only on ignition/power cycling.

The regression suite includes the pinned c11 vectors, all four OEM checksum vectors
and boundary arithmetic, decoder schema/transport rejection, independent deadlines,
wrap and recovery, SET handoff, real CarInterface parsing, continuous inactive traffic,
passive mode, own-loopback counter behavior, controller recovery gating, legacy GM
allocation, and compiled Panda safety limits/modes/allowlisting.

Run from the repository root with its Python dependencies installed:

```sh
PYTHONPATH=opendbc_repo python -m pytest -q opendbc_repo/opendbc/car/gm/tests \
  opendbc_repo/opendbc/car/tests/test_car_interfaces.py \
  opendbc_repo/opendbc/safety/tests/test_gm.py opendbc_repo/opendbc/safety/tests/test_elm327.py
```

Panda build, from `panda/` with `arm-none-eabi-gcc` on PATH:

```sh
PYTHONPATH=../opendbc_repo python -m SCons -j4 board/obj/bootstub.panda_h7.bin \
  board/obj/bootstub.body_h7.bin board/obj/panda_h7.bin.signed board/obj/body_h7.bin.signed
```

These are debug-signed applications and debug bootstubs, as required by this fork's
existing build. The paired ASCM firmware is external and is not flashed by this build.

### Local validation on 2026-10-29

- GM car, GM Panda safety, and diagnostic safety: 352 passed, 145 skipped;
  the skips include abstract safety classes and inapplicable inherited checks.
- All car-interface regressions: 255 passed.
- Four additional alert/state-machine/control-producer tests passed with the real
  CarEvents, StateMachine, card.controls_update, and schema implementations. This
  checkout lacks the host `libparams_c.so`: the local test runner substituted only
  the unused Params import and calibration speed constant. Native Params and the
  full application startup were not validated by those tests. On a fully built
  checkout run `python -m pytest openpilot/selfdrive/car/tests/test_ascm_events.py`.
- Changed Python files pass Ruff; `git diff --check` passes.
- Both H7 applications and debug bootstubs build with warnings treated as errors.

If carControl stops publishing after initialization, card continues c11 input
streams using an empty/inactive CarControl. This cannot cover termination of card
or Panda itself; those failures rely on ASCM input timeout and require end-to-end
fault-injection validation.
