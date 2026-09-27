# Volt ASCM nightly build — 2026-09-27

Base: commaai/openpilot nightly-chestnut at
`51d465f8da4afbe83003de02842f983cd002cb1e` (openpilot v0.11.2),
fetched and verified against upstream on 2026-09-27.

Applied only these patch sets to a clean base:
- Set 01: all twelve OEM-inspired brake-control patches, including the command-builder refactor,
  brake-hold exit fix, signed brake output logging, and legacy count rounding.
- Set 03: ASCM interceptor harness.

Set 02 (auto-resume) and set 04 (OEM steering) are excluded. The Volt interface reports
ASCM_LONG and ASCM_INTERCEPTOR enabled, autoResumeSng false, and upstream steering ki [0.0].

Validation:
- GM controller tests, all car interface tests, GM safety and signed-brake safety:
  540 passed, 131 skipped, 460 subtests passed.
- GM controller and affected safety-test lint passed; git diff --check passed.
- Panda H7 firmware rebuilt against this branch's safety headers with the development key.
  Embedded source revision: f98d0d44 (the final patch commit).
- Firmware signature, payload length, version marker, and embedded source revision verified.
- Signed firmware SHA256: f7c60122fa480c879e5df0ca1af34662e7a510a1fa6942088fa6654e00f243da.

The signed H7 firmware and tracked build artifacts are included. Upstream application prebuilts,
the prebuilt marker, bootstub, and signing keys are retained.

The previous branch and tracked working-tree changes are preserved together at
`backup/volt-ascm-before-clean-20260927` (ec5081ae3bf2d48060997939859f6e023527e0c5).
The new branch history replaces the previous local history; it has not been pushed or flashed.
No road test was performed.
