# Volt ASCM nightly build — 2026-09-27

Base: commaai/openpilot nightly-chestnut at
`51d465f8da4afbe83003de02842f983cd002cb1e` (openpilot v0.11.2).

All four patch sets are now applied:
- Set 01: OEM-inspired brake control, including the command-builder refactor, brake-hold exit fix,
  signed brake output logging, and legacy count rounding. Applied in its original twelve-commit form;
  the consolidated functionality/test pair produces identical code.
- Set 02: automatic resume from the ECM ACC standstill state (`7dfc0fd3b`).
- Set 03: ASCM interceptor harness.
- Set 04: OEM-inspired steering feedforward and integrator (`c1959d39c`).

The Volt interface reports ASCM_LONG and ASCM_INTERCEPTOR enabled, autoResumeSng true, and steering
ki [0.01, 0.02] at [10, 41] m/s. Sets 02 and 04 were added on top of the existing validated branch;
its history was not reset or rewritten for this update.

Current validation after adding sets 02 and 04:
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
