# Volt ASCM own-v1 integration on c11 transport

Branch base: `nightly-chestnut-10-19-26`, `203b977c79df4bd83a999f6c31644f2b72437524`.
Current contract: `ASCM/shadow_180_dev/OWNERSHIP_FORWARDING_V1_HANDOFF.txt` and
`protocol/status_v2_ownership/DECODING.txt` in that directory. These supersede the
engagement-latch and status-bit semantics in the original
`OPENPILOT_C11_INTEGRATION_HANDOFF.txt` (2026-10-29); command transport is unchanged.
This is an offline implementation, not a hardware release or authorization for live testing.

## Configuration and transport

The Volt platform explicitly selects `GMFlags.ASCM_C11`, together with the existing
`ASCM_INTERCEPTOR` and `ASCM_LONG` flags. Panda receives `GMSafetyFlags.ASCM_C11` (16).
There is no status-based autodetection: c10, c11 and own-v1 share the same payload version.
Other GM configurations retain their prior routing and longitudinal allocation.
The OEM 25-bit 0x2CB checksum correction applies to all senders of that message.

This configuration now requires the complete paired `own-v1-monitor` selection:
`ASCM/shadow_180_dev/firmware/own-v1-monitor/firmware-selection.json`.

- MPU1 SHA256: `bf675645264ce885dff751c6e37ed86032e3c4ef2f87bec91711f68a8ac051cd`
- MPU2 SHA256: `79122bb7176197a814bfee94b173e9355433c0746a03930b72db50fcbea84df5`

The old c11 images are no longer a compatible target: they withhold permission
until active commands arrive and clear their engagement latch during the resume
pulse. The host now requires permission before active commands. Record both ASCM
image identities with validation runs; protocol version 2 cannot identify them.

Assumed physical mapping: PT=0, object=1, chassis=2. Verify the installed harness.
The four permitted Panda transmissions are object 0x180/DLC4, 0x2CB/DLC8,
0x37F/DLC5, and 0x370/DLC6. Brake uses the unchanged 0x315 payload/checksum.
The ASCM transmits to the actuator networks. c11 permits no direct PT/chassis
commands or replacement-ASCM ADAS keepalives. Steering advances from the last
observed own object-bus TX loopback (bus 129), starting at counter 0 and retrying
that counter until a loopback arrives. Received PT commands cannot seed it. Gas
and brake likewise use independent successful object-bus TX echoes; rejected attempts (bus 193) never advance
their counters. The next attempt uses current command values, so a rejection
followed by disengagement produces an inactive/release packet at the missing
counter rather than retrying an old active request.

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
wrong buses, and invalid payload schemas cannot establish readiness. As explicitly
chosen by the user, live framing follows the existing GM Global A assumption:
standard Classical CAN data frames. There is no c11-specific Panda receive filter.
The host interface does not expose framing flags, so it cannot independently
verify this assumption; optional offline decoder flag checks are not live checks.

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
Both OPENPILOT reports and their forwarding permissions are required before the
pending intent produces buttonEnable. Permission alone never creates driver intent.
Cancel, pedals, main/ignition disable, lost readiness, generation/reset changes,
or expiry discard the pending request. Readiness recovery never generates intent.

OEM ownership inhibits openpilot and displays a cruise-main-cycle explanation.
The host never synthesizes OFF, SET, RESUME, or LKA button messages. own-v1 suppresses
OEM LKA throughout OPENPILOT ownership, including disengagement and resume. After
ownership resets, the firmware requires a fresh LKA release/press to restore OEM
eligibility. Status does not expose OEM LKA state.

The controller independently checks authorization at send time. A fault disables
both lateral and longitudinal requests, including release during braking/standstill.
Recovery while controls remains enabled cannot reactivate commands. Byte 0 bit 3
is decoded as `forwarding_permitted`, independent of command-active flags. Both
processors must grant permission before the first active command and retain it
throughout the session. Permission withdrawal invalidates qualification and the
controller's authorization epoch, even if it recovers within one CAN batch. The
old active-confirmation timer is removed; status/output freshness deadlines remain.
Alerts immediately disable
the openpilot state machine on lost authorization. Pedals are not classified as
ASCM faults: brake/regen retain normal driver disengagement; gas temporarily
overrides longitudinal actuation while session ACCActive, UI-active and eligible
steering remain enabled. Gas immediately selects inactive axle torque, clears
stop/hold requests and releases braking, even before controlsd processes the
pedal sample. Release resumes longitudinal control only within that same healthy
session. A real fault during override still disables both axes and requires a
new engagement. Pedals continue to inhibit new pending SET/RESUME requests.

Volt auto resume is enabled with openpilot longitudinal control. The ECM standstill
latch remains available to the controller but does not force the longitudinal
planner to wait for a physical RESUME. The ASCM allocator keeps brake hold until
launch intent clears its stop latch, then drops ACCActive while the ECM still
reports standstill. It restores ACCActive once the ECM leaves standstill. UI and
eligible steering remain active throughout; own-v1 permission remains independent.
The existing pulse is also restored for the legacy allocator when auto resume is
configured. The powertrain-versus-brake allocator remains separate from firmware
ownership. Actual stop/hold/resume/launch behavior still requires paired ASCM bench
and vehicle validation; host tests do not establish physical actuator acceptance.

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
OEM-first/late boot/OEM LKA operation, automatic resume, bus-off/congestion/output stalls,
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

### Rebuilt Panda artifacts

Source revision: `bcb8a8803`; version marker: `DEV-bcb8a880-DEBUG`.
SHA256 of the tracked outputs:

```text
f6205b789633a8637158dc8936b7cd8776209ea4863acb0d2d4a669246b0f437  bootstub.panda_h7.bin
eb4140d2bf3b41a7a7f96d74aa59b69f19854cb280c1c368cea1e0d6b8fbb25d  bootstub.body_h7.bin
2b9aa20b622142fe888bda7ec4c3a02e252c110746895b978826e3e536920588  panda_h7.bin.signed
063b9c0dc382d09077c697c699057502b0349e7a19701156f0d30c3abddfb2b1  body_h7.bin.signed
```

## Drive regression fixes — 2026-10-31

The drive on source revision `f5d909c11` exposed two host integration defects.
`controlsd` legitimately asserts `cruiseControl.cancel` when the ECU reports cruise
active and `pcmCruise=false`, even while openpilot remains enabled. Treating that
stock-PCM request as a c11 disengagement interrupted ACCActive and cleared the
ASCM engagement latch. Clearing the flag then incorrectly rearmed the sender.

The c11 sender now ignores the stock-PCM cancel flag for session authorization.
Physical CANCEL still disables the openpilot state machine. Readiness/epoch faults
and real disengagement release both axes. The rearm edge tracks actual
`CarControl.enabled`, so clearing stock cancel cannot rearm an interrupted
session while enabled stays true. The initial fix also treated longitudinal
override as a session disable; the minimum-integration update below corrects that.
The active-confirmation watchdog and all safety limits/deadlines are unchanged.

A SET/RESUME press can now establish bounded pending intent while healthy peers
report UNSELECTED/OPENPILOT during selection. Freshness, qualification, matching
generation, independent output progress, and the existing 750 ms expiry remain
required. Both owners must agree on OPENPILOT before activation; SET still requires
release. Cancel, pedal disable, reset, timeout, or loss of readiness clears intent.
This also covers the case where an ASCM processor sees SET before the host does.

Validation:

- New supervisor/controller regressions reproduce the failures on the old code
  and pass after the fix, including rejection of synthetic rearm edges.
- The real `Controls.publish()` method is exercised through the GM controller:
  ECU cruise ON/OFF changes the stock-cancel flag without interrupting active
  commands. Separate checks cover physical CANCEL and pedal-disable event handling.
- Broad GM car, all car-interface, GM safety and diagnostic safety checks:
  614 passed, 145 skipped, plus 567 passing subtests.
- Seven application-path tests pass, with three pedal subtests. As with the
  original host-only validation, native Params and unrelated model/calibration
  process imports were substituted; the real publish/event/state/controller
  implementations ran. No full application startup is claimed.
- Offline probes at the first synthetic cancellation of all 11 recorded
  engagements preserve ACCActive with this fix and withdraw it with the original
  controller. The first-SET reproduction now enables on release after agreement.
  These probes use recorded status/timing, not a closed-loop physical replay.
  Results are saved under `~/volt_logs/ascm_unavailable_2026-10-31/fix_validation/`.

For that earlier stock-cancel/first-SET fix, only host Python and tests changed;
its existing Panda artifacts remained applicable. The later minimum-integration
update below does require rebuilt Panda firmware. No deployment,
flashing, live CAN transmission, or vehicle test was performed.


## Minimum integration and pedal compatibility — 2026-10-31

Relative to `nightly-chestnut-10-19-26`, Panda firmware source changes are now
limited to `opendbc/safety/modes/gm.h`: a c11 configuration flag, its four-command
object-bus TX allowlist, and applying the existing brake numeric safety checks to
object `0x37F`. The CAN driver is identical to nightly. The additional c11 checks
on active/hold/UI flags and command framing have been removed as requested.
Baseline GM pedal detection, controls permission, numerical actuation limits,
and steering rate/driver-torque checks are unchanged. `ACCActive` is still
forbidden after actual disengagement but is allowed with inactive torque during
a gas override while the session remains enabled.

Host changes retain the OEM checksum correction, both status supervisors,
ownership handshake, inactive streams and genuine-fault release/rearm rules.
Driver override is separated from ASCM health, and gas/brake counters follow
independent successful transmissions. This addresses both the misleading alerts
and the subsequent counter discontinuities seen in the two follow-up drives.

Validation of this update:

- GM car, all car interfaces, GM Panda safety and diagnostic safety:
  **615 passed, 145 skipped, 573 passing subtests**.
- Application event/publish/controller paths: **10 passed, 2 passing subtests**,
  including gas override/resume, releasing standstill hold, normal brake/regen
  disengagement and a genuine ASCM fault during gas override. The same host IPC
  extension and unused process-import substitutions described above were used.
- **608 compiled TX safety decisions match the nightly baseline** with the brake
  ID mapped from `0x315` to `0x37F`. Coverage includes enabled/disabled and gas
  states, request limits, brake modes, steering-active and UI-active fields.
  This is behavioral parity evidence, not new physical validation of every mode.
- The two recorded rejection incidents yield consecutive release counters for
  all three affected streams: drive cb gas `3 -> 0`; drive cc gas and brake
  `1 -> 2`. The old release counters were `1` and `3`, respectively. Generated
  inactive/release payload checksums validate. This is a replay of TX-return
  inputs through the host counter path, not a closed-loop vehicle simulation.
- Ruff and `git diff --check` pass.

Offline comparison/replay scripts and results are in
`~/volt_logs/ascm_pedal_overrides_2026-10-31/minimum_fix_validation/`.
Both H7 applications and debug bootstubs were rebuilt for this update; no ASCM
firmware change is included. No deployment, flashing or vehicle validation has been performed.
At this revision, automatic standstill resume remained disabled for the old c11
firmware. The own-v1 update below supersedes that restriction.

### Panda artifacts for the minimum integration

Source commit: `3cc5a68dce65e32f72cc38f2597d47455cecc005`.
Version: `DEV-3cc5a68d-DEBUG`. Both application debug signatures and embedded
versions were verified against the debug public key and source revision.
Build completed with warnings treated as errors; no device was flashed.

```text
1651af170344703b67a91496be227d7cf3110ee36a9e104fa2da68076b3310b7  panda_h7.bin.signed
1298ca435d7fcd2ed3ec9a3b595dff6ab6bdf1692a2e6d400f242789903fc440  body_h7.bin.signed
96bbb72e326da109bd26f86435ea16cf1e425fac3cc463fdc7f77da6a36cc157  bootstub.panda_h7.bin
b18cf11c08357075bbce13e36b72ad9c4051848b85d21780dc000906814396dc  bootstub.body_h7.bin
```

### own-v1 automatic resume update — 2026-11-04

Restored the Volt auto-resume configuration and both allocator pulse paths for
the paired own-v1 firmware. The supervisor now requires both forwarding bits
before entry and invalidates the session on either bit's withdrawal. Permission
does not imply engagement, create driver intent, or bypass cancellation. The
existing gas override, brake/regen disengagement, command counters, numerical
safety limits and status/output deadlines are retained. No Panda source or
firmware artifact change is required; the preceding Panda build remains current.

Validation:

- GM controller/interface and compiled GM/diagnostic safety suites: **618 passed,
  145 skipped, 575 subtests passed**.
- Application-path suite: **12 passed, 10 subtests passed**, using the real
  LongControl, controlsd publish path, GM sender, and compiled Panda TX hook for
  the stop/hold/launch sequence. Powertrain and downhill brake-controlled launches
  retain steering/UI, clear full-stop during the pulse, and restore ACCActive
  when the ECM standstill fixture clears. Pedals, CANCEL, and either processor's
  permission loss during a pulse retain their override/disengagement behavior.
- Supervisor tests cover permission before first entry, duplicate rejection,
  pending intent cancellation, and permission loss/requalification between
  controller ticks without automatic re-engagement.
- Ruff and `git diff --check` pass.

The application tests use the same host IPC extension and unused process-import
substitutions described above. Status/ECM reports and TX echoes are test fixtures;
these tests do not execute ASCM firmware or prove the physical ECM response to
the pulse. Full application startup, paired ASCM bench testing and vehicle
validation remain outstanding. No firmware was flashed or code deployed.
