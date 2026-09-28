# Volt ASCM nightly build — 2026-09-27

Base: commaai/openpilot nightly-chestnut at
`51d465f8da4afbe83003de02842f983cd002cb1e` (openpilot v0.11.2).

All four patch sets are now applied:
- Set 01: OEM-inspired brake control, including the command-builder refactor, brake-hold exit fix,
  signed brake output logging, and legacy count rounding. Applied in its original twelve-commit form;
  the updated consolidated functionality/test pair includes the grade-request correction described below.
- Set 02: automatic resume from the ECM ACC standstill state (`7dfc0fd3b`).
- Set 03: ASCM interceptor harness.
- Set 04: OEM-inspired steering feedforward and integrator (`c1959d39c`).

The Volt interface reports ASCM_LONG and ASCM_INTERCEPTOR enabled, autoResumeSng true, and steering
ki [0.01, 0.02] at [10, 41] m/s. Sets 02 and 04 were added on top of the existing validated branch;
its history was not reset or rewritten for this update.

Request/command naming refactor (2026-09-28):
- Explicit request/command names distinguish steering torque, axle torque and brake acceleration.
  Cached outputs and longitudinal state also use descriptive names; shared actuator fields are unchanged.
- Compared with the prior controller: identical 41,402 CAN messages and all actuator outputs over 22,400
  frames in 14 configurations. Owner/hold state and pitch also match exactly.
- Base patch tests: 39 passed, 54 subtests. Active GM tests: 43 passed, 71 subtests. Lint/diff checks passed.
- Set 01 is refreshed; sets 02 and 03 use the renamed fields and remain independently applicable.
  Set 04 and firmware are unchanged. Full patch application reproduces the active checkout.

Current grade-request correction:
- EBCM receives the vehicle-acceleration request, including the longitudinal I correction, without an added
  gravity term. Grade compensation remains in powertrain torque and ownership selection.
- Existing bounds, quantization, stop-hold and mode-selection rules remain in place.
- GM tests: 43 passed, 71 subtests passed. GM lint and diff formatting passed.
- Updated set 01 plus unchanged sets 02–04 apply cleanly to the nightly base and reproduce all 12 touched files.
- The corrected mapping has not yet been road-tested. No safety-source changes or firmware rebuild required.

Previous validation after adding sets 02 and 04:
- GM controller tests and all car interface tests: 296 passed, 60 subtests passed.
- GM lint and diff formatting passed.
- Auto-resume, platform flags, and steering gain schedule checked directly through the Volt interface.
- No changes to panda or opendbc safety sources relative to c712065b4; no firmware rebuild required.

Existing firmware validation from the sets 01+03 build:
- GM controllers, all car interfaces, GM safety and signed-brake safety: 540 passed, 131 skipped,
  460 subtests passed before adding the Python-only optional features.
- Panda H7 firmware built against the branch's safety headers using the development key.
  Embedded source revision: f98d0d44 (the safety/interceptor source state).
- Firmware signature, payload length, version marker, and embedded source revision verified previously;
  the signed firmware SHA256 is still f7c60122fa480c879e5df0ca1af34662e7a510a1fa6942088fa6654e00f243da.

The signed H7 firmware and tracked artifacts remain included. Upstream application prebuilts,
the prebuilt marker, bootstub, and signing keys are retained.

The validated manual-resume configuration is preserved at `backup/volt-ascm-manual-resume-20260927`
(c712065b4). Earlier pre-reset work remains at `backup/volt-ascm-before-clean-20260927`.
This update has not been pushed or flashed, and no new road test was performed by the agent.
