# Volt ASCM nightly build — 2026-10-19

Base: commaai/openpilot nightly-chestnut at
`2eae8186d1d4913cda16163e7cf3bc14d1481824` (openpilot v0.11.3).

Patch sets 01-05 from `volt-patches` applied with `git am --directory=opendbc_repo`:
- Set 01: ASCM-inspired longitudinal control and its tests.
- Set 02: auto-resume from an ACC standstill.
- Set 03: ASCM interceptor harness.
- Set 04: Volt steer feedforward from the ASCM LKA tables, small ki, low-speed gain fit.
- Set 05: FW 2.0 query, PSCM 0x242 in ELM327 safety, Volt `FW_VERSIONS` (firmware fingerprinting).

Conflicts resolved against v0.11.3:
- `CarSpecs` no longer has `mass` (the vehicle model is per unit mass now); the Volt spec keeps the upstream
  line and adds the flags. The longitudinal model's own `MODEL_MASS` is unaffected.
- The GM safety TX lists are one message per line upstream; `GM_ASCM_INTERCEPTOR_TX_MSGS` follows that style.
- `test_elm327.py` gained `SAFETY_MODEL`; kept alongside `GM_DIAG_ADDRS`.

Validation:
- GM car tests 43 passed; car interfaces 255 passed; FW fingerprint 15 passed.
- GM safety 268 passed (24 skipped); signed brake safety 5 passed; ELM327 safety 8 passed (1 skipped).

Panda H7 and body firmware and bootstubs rebuilt from `panda/` against this branch's opendbc_repo with the debug key:

    PYTHONPATH=../opendbc_repo python3 -m SCons board/obj/bootstub.panda_h7.bin board/obj/bootstub.body_h7.bin \
      board/obj/panda_h7.bin.signed board/obj/body_h7.bin.signed

The bootstubs must be rebuilt too. Upstream v0.11.3 ships a RELEASE bootstub that only accepts comma's release
key (v0.11.2 shipped a DEBUG one), so with the upstream bootstub pandad's recovery flash leaves the panda stuck
in bootstub with the debug-signed app. Version marker DEV-7ddfa669-DEBUG,
bootstub.panda_h7.bin SHA256 c4519d1a4aa0f74034a42a55dde8125c50fc179b571092217c7c45932f98d22b,
panda_h7.bin.signed SHA256 fa40ce110ecd91fc780e9d661f64a3989ea6038fcbb72e692cfa3b656068cfba.

The v0.11.2 build is preserved on `volt-ascm-nightly-chestnut`. Not flashed or road-tested by the agent.
