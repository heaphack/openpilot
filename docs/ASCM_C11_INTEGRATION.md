# Volt ASCM own-v1 integration on c11 transport

Original branch base: `nightly-chestnut-10-19-26`, `203b977c79df4bd83a999f6c31644f2b72437524`.
Latest nightly update: `ascm-c11-integration-hewers-lateral-11-5-26` incorporates
`commaai/openpilot:nightly-chestnut` at `836afe1bce0c053a8e0a5c12c03f18def75c6a5f`
(November 6, 2026). See the update notes below for packaging and validation.
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

## Hewers lateral controller port

Branch `ascm-c11-integration-hewers-lateral` starts at
`ascm-c11-integration` commit `6b2b6ab1849227fd58bf97689402539ff15616c1`.
The lateral changes are selectively ported from hewers' work:

- `hewers/openpilot`, branch `lateral`, commit
  `ad1e224a3c905b5f29b4abe505b8b62126281243`: `LatControlSteer`, controlsd
  selection/yaw input/limiting feedback, parameter keys, tuning tool and tests.
- Its pinned `hewers/opendbc` commit
  `cd56ad1b4cbec8e8403b03d573f907141db5dd71`: only the Volt changes in
  `gm/interface.py` and `gm/values.py`. The submodule's unrelated upstream
  changes and safety refactors are not part of this port.

The 2017–18 Volt now uses hewers' steering-column feedforward with lateral
acceleration feedback and yaw-rate correction. The selected source's gains and
column model are preserved, including KI 0.15 and slope gain 0.7. Volt CarParams
select torque tuning, steering ratio 16.5, the GM baseline steering delay 0.1 s,
and the fitted nonlinear baseline torque curve/offset. The previous Volt PID
feedforward is removed. Other cars retain their existing controller selection.

`LateralTorqueBaseline` defaults to false. Setting it true before controlsd starts
selects hewers' torque baseline, not the previous angle PID. `LateralDriverModel`
also defaults to false; when enabled before controlsd starts, the column controller
uses his optional driver-torque model. `LateralTune` supports his bounded live
adjustments via `python openpilot/tools/lateral_tune.py`; changes blend over two
seconds and clear at manager startup or the offroad transition. These settings
have no new UI controls. Persistent baseline/driver-model settings survive those
transitions. The controller reports `torqueState` with hewers' version markers.

ASCM ownership/forwarding supervision, command buses/counters, steering torque
and rate limits, longitudinal allocation, pedal behavior and auto resume are
retained. Steering remains at the existing 30 ms active cadence in both source
trees. Hewers' 0.03 s limiter-feedback tolerance is preserved; its source comment
about every-other-frame transmission does not describe the pinned sender.
Physical response through the patched ASCM still needs vehicle validation.

The tracked `prebuilt` marker is retained and the ARM64 parameter library is
rebuilt with the three new tuning keys. The first port commit incorrectly removed
the marker: this release checkout omits ONNX model sources, so a full startup
build fails. See the packaging correction below. Panda safety source and existing
firmware artifacts are unchanged.

Local validation:

- GM and all car-interface tests: **328 passed, 109 subtests passed**.
- Compiled GM and diagnostic safety tests: **290 passed, 145 skipped,
  466 subtests passed**.
- Hewers lateral tests, new integration coverage, ASCM application tests and
  native parameter tests: **49 passed, 13 subtests passed**. Coverage includes
  actual controlsd initialization/selection, parameter persistence/clearing,
  torque-state publication, nonzero controller output through the ASCM sender
  and compiled Panda checks, and sender withdrawal on lost ASCM readiness.
- Ruff and `git diff --check` pass.

Host validation used a newly compiled x86 parameter library with these keys and
the existing host IPC extension, without replacing tracked ARM binaries. The
runner substitutes the calibration/model process imports with their actual
constants (MIN_SPEED_FILTER and LAT_SMOOTH_SECONDS); the tested controller,
parameter storage, schemas, sender and safety code are real. Test support is in
`/tmp/hewers-lateral-tests-7zvo208q/`. Full device builds/startup, closed-loop
vehicle performance and physical ASCM steering response were not validated.
No deployment, flashing or vehicle operation was performed.

### Prebuilt packaging correction — 2026-11-04

The device reported a full-build failure because
`openpilot/selfdrive/modeld/models/dmonitoring_model.onnx` is absent. This release
checkout carries compiled models, not their ONNX sources. Removing `prebuilt`
in `86eb522ab` was incorrect for that packaging. The accompanying PWD warning
was not the fatal error.

Restore the empty `prebuilt` marker and replace only
`openpilot/common/libparams_c.so` with an ARM64 build of the existing source plus
hewers' registered keys. Startup again uses the shipped binaries and compiled
models. No SCons workaround, model download, new lateral logic, or Panda change
is introduced. The old parameter library alone would reject the new key names.

The replacement is built from source revision `86eb522ab` using GCC 12.4 for
AArch64, C++17, `-D__COMMA_HARDWARE__`, `-mcpu=cortex-a57`, and warnings treated
as errors. JSON11 and ZeroMQ are statically linked from the pinned ARM64
`comma-deps` post103 wheels. Cap'n Proto 1.0.1.post103 supplies headers.
The highest GLIBC and GLIBCXX symbol versions remain 2.38 and 3.4.30, respectively,
matching the prior library's requirements. No host x86 library is shipped.
Library SHA256: `7de293ba8669e6e9b5452809c54e70c61e872151d16cce892097f880413318cc`.

Both the previous and new ARM64 libraries were loaded and exercised under
QEMU AArch64. Existing key names, types and defaults match exactly; the only
additions are `LateralDriverModel` (BOOL), `LateralTorqueBaseline` (BOOL), and
`LateralTune` (JSON). Blocking read/write, persistent boolean retention, and
clearing the JSON setting on manager startup and offroad transitions pass.
This checks the actual shipped ARM64 artifact, not just a host rebuild.

Build commands, compiler/dependency/source hashes, ARM smoke-test source/binary,
outputs and replacement library are saved in
`~/volt_logs/hewers_lateral_build_2026-11-04/`. See `manifest.json` for the exact
artifact SHA256 and build inputs. No device startup or vehicle behavior is
claimed validated by the emulator, and no device was flashed or modified here.

## Nightly update — 2026-11-06

Branch `ascm-c11-integration-hewers-lateral-11-5-26` starts from the working
integration at `1da16d25a` and incorporates the latest fetched nightly,
`836afe1bce0c053a8e0a5c12c03f18def75c6a5f`, published November 6 at 09:06:26 UTC.
The branch name retains the requested November 5 suffix. Nightly releases have
unrelated flattened histories, so the merge used `git merge-tree --write-tree`
with the original release `2eae8186d1d4913cda16163e7cf3bc14d1481824` as its explicit
base. Source merge `a0a40df1c48581b5d9f55fea31afcc8703c5ca77` records both parents;
the following packaging commit supplies matching custom binaries.

All upstream changes are incorporated, including the AGNOS requirement change
from 19.9 to 20.3, the new native messaging implementation, model artifacts,
longitudinal planner updates, and Panda self-tests/safety bookkeeping changes.
The ASCM supervisor, GM controller, pedal handling, auto resume, hewers lateral
controller and controlsd integration are byte-identical to the working branch.
The existing custom GM safety changes remain; upstream's const RX-check arrays
and shared RX state are retained.

Upstream now assigns event 105 to `startupCruiseCanceled`, colliding with the
previous custom ASCM event. Preserve upstream 105 and assign `ascmUnavailable`
to 106 and `ascmOemOwned` to 107. Existing tests load the merged schema and exercise
both ASCM alert paths. Historical logs from the previous branch must be decoded
with that branch's schema: its ASCM events used 105/106.

The empty `prebuilt` marker remains. The ARM64 parameter library is rebuilt from
the merged source with upstream's current key flags and Unix-datagram logging,
plus the three lateral tuning keys. Both Panda H7 and body firmware and debug
bootstubs are rebuilt with the pinned GCC 13.2.1 toolchain. The firmware uses the
new upstream CRC32 trailer and has version `DEV-a0a40df1-DEBUG`; signatures and
CRC32 values were verified locally. No ASCM firmware change is part of this update.

Selected artifact SHA256 values:

- `openpilot/common/libparams_c.so`:
  `47da73162c1431765b289cdb4617db30edc4da225d1deb660f05c23a2aeb46fb`
- `panda/board/obj/panda_h7.bin.signed`:
  `e57cef5f420e187303efeb7232e7c2dfa25e898a4c4747537e924a7e68011e00`
- `panda/board/obj/bootstub.panda_h7.bin`:
  `72a2575da264a385a79456d0fef59c9e82191a2d099976e5ba7f21533a57db2f`

Validation:

- GM, car-interface, fingerprinting, GM/signed-brake/ELM327 safety tests:
  **638 passed, 293 skipped, 8,572 subtests passed**.
- Lateral controller, ASCM application/integration and parameter tests:
  **49 passed, 13 subtests passed**.
- Actual packaged ARM64 parameter library under QEMU: latest upstream key names,
  types and defaults preserved, exactly the three lateral keys added; read/write,
  boolean persistence and temporary-tune clearing passed.
- Custom Python Ruff checks, shell syntax and the custom diff's whitespace checks
  passed. Upstream generated-file whitespace is preserved as fetched.

Application tests use newly compiled host native messaging and parameter libraries
from the merged source. As before, unused calibration/model process imports are
substituted with their actual constants; controller, schema, messaging, sender and
safety behavior under test are real. These checks do not validate full device
startup, the AGNOS update, or on-road behavior. No device was flashed or modified.
Build commands, source/artifact hashes, QEMU output and test logs are saved in
`~/volt_logs/nightly_merge_2026-11-06/`, including `manifest.json`.

## Gold Volt steering limits — 2026-11-09

`gold-volt-11-5-26` starts from `ascm-c11-integration-hewers-lateral-11-5-26`
at `01b3e5794`. Patch set `06-volt-4nm-steering` is exported in
`~/github.com/heaphack/volt-patches/` for this flattened checkout.

- The Volt sender's maximum request is 400 CAN counts (4 Nm), with a matching
  Panda maximum selected by the new `GMSafetyFlags.VOLT_4NM` bit 32. Only the
  Volt interface selects it; existing GM configurations without this bit keep
  300 counts. The normal c11 Volt safety parameter is now 60 (4 | 8 | 16 | 32).
- Hewers' column model normalizes its physical torque output by 4 Nm, including
  its PID output budget. The optional baseline controller's normalized torque
  curve scales by 3/4 so its existing physical calibration remains the same.
  Raising the ceiling does not multiply unsaturated torque requests by 4/3.
- Volt `minSteerSpeed` is zero, removing its 7 mph cutoff and low-speed alert.
  GM only raises the low-speed alert for a positive minimum. This prevents a
  slightly negative filtered speed at a stop from producing "Below 0 mph".
  Shared controlsd standstill gating remains: steering is inactive at or below
  0.3 m/s or when CarState reports standstill. Initial engagement's separate
  minimum speed is unchanged.
- Torque slew limits (10 up / 15 down counts per message), real-time delta
  limit (128 counts), driver torque allowance/multiplier, cadence, ASCM
  authorization, pedal behavior and longitudinal logic are unchanged.

The tests exercise both directions through controlsd, the actual sender and
compiled Panda safety; raw CAN torque matches the 400-count normalization.
They cover low-speed activation and standstill inhibition, the 400/401 boundary,
returning to the 300-count configuration, driver/rate/disabled safety checks,
and physical torque equivalence below saturation. The saturation/anti-windup
fixture now includes adverse road roll so its request exceeds the 4 Nm ceiling.

This changes the requested openpilot/Panda envelope. It does not modify ASCM or
EPS firmware and does not establish physical EPS acceptance or performance at
4 Nm or low speed. Rebuilt Panda artifacts accompany the source patch on this
prebuilt branch; `prebuilt`, the parameter library and model files are retained.

Gold build validation:

- GM Panda safety, including the new 4 Nm variant: **317 passed, 142 skipped,
  532 subtests passed**.
- GM car tests, all car interfaces, firmware fingerprinting, signed-brake and
  diagnostic safety: **356 passed, 155 skipped, 8,106 subtests passed**.
- Lateral/ASCM application and parameter tests: **53 passed, 20 subtests passed**.
- Ruff and `git diff --check` passed. Host application tests use the saved native
  IPC/parameter libraries from the unchanged nightly base and the same limited
  process-import substitutions described above.

Panda and body apps/bootstubs were rebuilt with pinned GCC 13.2.1.post103 from
applied source commit `4fc1f23fcae4c8822922ce80b6e090e0fa26d636`, with version
`DEV-4fc1f23f-DEBUG`. Both app signatures, CRC32 footers and lengths were checked.
Panda app SHA256: `9e309dafceef7143736c37555963c5f2fef8875b3e578499522a915c7aee3eb6`.
Panda bootstub SHA256: `1798be00928bd3d3495ae8241b1203f9ce8942785632e58b31cfce43caeb4bc0`.
Build logs, test results and full artifact hashes are in
`~/volt_logs/gold_volt_2026-11-09/`. No device startup or vehicle testing was performed.

The follow-up zero-minimum alert guard is patch 0003 in set 06. Its regression
test reproduces speed-filter undershoot from packed wheel-speed CAN messages;
the previous code fails that test. All GM car tests pass with the guard:
**76 passed, 113 subtests passed**, including positive-minimum alert clearing
and temporary/permanent EPS fault reporting at zero speed. Ruff and whitespace
checks passed. This Python-only fix requires no Panda rebuild.

## Gold Volt 5 Nm steering limit — 2026-11-10

The follow-up to `a458a3623` raises the Volt's requested steering ceiling from
4 to 5 Nm in the sender, Panda safety and Hewers' column controller. The sender
uses 500 CAN counts; safety parameter bit 32 is now named `VOLT_5NM` and selects
500 counts in the matching rebuilt firmware. The complete c11 Volt parameter
remains 60. Other GM configurations retain their 300-count default.

Hewers' normalization, PID output budget, feedforward logging and command-limit
detection all use the 5 Nm model maximum. Its physical torque response below
saturation is preserved. The optional baseline's coefficients use 3/5 scaling;
its inverse lookup extends to ±7 m/s² so it covers both full-scale torque limits
without changing the physical calibration. Regression tests cover that inverse
mapping and compare Hewers' unsaturated physical output against the 4 Nm version.

The zero minimum steering speed and positive-minimum warning guard remain.
Slew limits, driver override, ASCM session handling, longitudinal behavior and
standstill inhibition are unchanged. No ASCM or EPS firmware is modified.

Validation covers ±500 counts through controlsd, the sender and compiled Panda,
rejection at ±501, resetting to the default 300-count safety configuration,
normal torque/rate/driver/disengagement checks, baseline selection, tune blending
and saturation anti-windup. The anti-windup test uses a stronger synthetic road
roll to exceed the new ceiling; tune-blending checks use physical Nm units.

The source and matching Panda apps/bootstubs are exported as patch set
`07-volt-5nm-steering` in `~/github.com/heaphack/volt-patches/`, applied after set
06. Use the source and packaged firmware together: bit 32 selected 4 Nm in the
previous firmware. Keep `prebuilt` for this release checkout. Local validation
artifacts are in `~/volt_logs/gold_volt_5nm_2026-11-10/`. This change establishes
software limits, not physical EPS acceptance of 5 Nm; no vehicle test was run.

5 Nm build validation:

- GM Panda safety: **317 passed, 142 skipped, 532 subtests passed**.
- GM car/interface/fingerprint and signed-brake/diagnostic safety:
  **359 passed, 155 skipped, 8,110 subtests passed**.
- Lateral controller, ASCM application/integration and torque-buffer tests:
  **41 passed, 20 subtests passed**.
- Ruff and whitespace checks passed. Host application tests use the same native
  IPC/parameter libraries and limited process-import substitutions documented above.

Both Panda and body apps/bootstubs were rebuilt with GCC 13.2.1 from source
commit `faaccec12c6fbe8f8c138521c7e966bbd9b1336d`, with firmware version
`DEV-faaccec1-DEBUG`. Both debug RSA signatures, CRC32 footers, length fields,
embedded versions and ELF-to-binary correspondence were verified. Artifact
hashes and reproducible verification are recorded in the local manifest and
`verify_firmware.py`. The packaged parameter library and model files are unchanged.

## Gold Volt 6 Nm steering limit — 2026-11-13

The follow-up to `575230ae7` raises the same Volt steering limits from 5 to 6 Nm:
the sender uses 600 CAN counts, Panda accepts up to 600 with safety bit 32
(`VOLT_6NM`), and Hewers' model maximum is 6 Nm. The complete c11 Volt safety
parameter remains 60; other GM configurations retain their 300-count default.
Hewers' normalization, PID budget, feedforward logging and command-limit detection
derive from that maximum. Unsaturated physical torque is preserved against the
5 Nm controller.

The optional baseline coefficients use 3/6 normalization with the same physical
torque curve. Its inverse lookup extends to ±9 m/s² to cover both full-scale
torque limits; this does not change planner acceleration limits. Regression
tests cover the full inverse mapping, ±600 through controlsd/sender/Panda,
rejection at ±601, reset to the default limit, and saturation anti-windup using
a stronger synthetic road-roll input.

The zero-speed warning guard, standstill inhibition, steering slew/driver limits,
ASCM supervision and longitudinal behavior are retained. The source and rebuilt
Panda firmware must be used together: previous bit-32 firmware limits to 5 Nm.
No ASCM/EPS firmware changes are included. Keep `prebuilt`; model files and the
parameter library are retained.

Patch set `08-volt-6nm-steering` in `~/github.com/heaphack/volt-patches/` follows
set 07. Local test/build evidence is in `~/volt_logs/gold_volt_6nm_2026-11-13/`.
This changes software limits; physical EPS acceptance at 6 Nm and device startup
have not been tested.

6 Nm validation: **317 GM safety tests passed** (142 skipped, 532 subtests),
**359 GM car/interface/fingerprint and diagnostic/signed-brake tests passed**
(155 skipped, 8,110 subtests), and **41 application tests passed** (20 subtests).
Ruff and whitespace checks passed. Application tests use the saved native host
IPC/parameter libraries and the same unused-process import substitutions as the
5 Nm validation.

Both Panda and body apps/bootstubs were rebuilt with GCC 13.2.1 from source
commit `b1da44a92be9ea45956855e912e3cd8e4676d4de`, firmware version
`DEV-b1da44a9-DEBUG`. Both debug RSA signatures, CRC32 footers, length fields,
embedded versions and ELF-to-binary correspondence were verified. Source and
artifact hashes are recorded in the local manifest alongside the verification
script. No device was flashed or vehicle-tested during this work.
