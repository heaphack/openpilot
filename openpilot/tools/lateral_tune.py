#!/usr/bin/env python3
"""Live LatControlSteer tuning on a tuning drive. Sets the LateralTune param: controlsd reads it once a second and blends
the change in over TUNE_RAMP. The param is cleared when the car goes offroad, so every drive starts on the shipped values.

  lateral_tune.py                         what's set, against the shipped values and the allowed ranges
  lateral_tune.py kp_scale=1.25 Fc=0.4    set these, on top of what's set ("Fc=" drops one)
  lateral_tune.py --reset                 back to the shipped values
"""
import json
import sys
import time

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.latcontrol_steer import STEER_MODELS, TUNE_LIMITS, TUNE_RAMP, shipped_tune

ACK_TIMEOUT = 3.0  # s, controlsd reads the param once a second


def show(tune, shipped):
  print(f"{'knob':20s} {'set':>8s} {'shipped':>8s}  range")
  for k, (lo, hi) in TUNE_LIMITS.items():
    v = f"{tune[k]:8.3f}" if k in tune else f"{'-':>8s}"
    print(f"{k:20s} {v} {shipped[k]:8.3f}  {lo:g} .. {hi:g}")


def parse(args, tune):
  tune = dict(tune)
  for a in args:
    k, sep, v = a.partition('=')
    if not sep or k not in TUNE_LIMITS:
      sys.exit(f"unknown: {a!r} (knobs: {', '.join(TUNE_LIMITS)})")
    if v == '':
      tune.pop(k, None)
      continue
    try:
      x = float(v)
    except ValueError:
      sys.exit(f"{k}={v!r} isn't a number")
    lo, hi = TUNE_LIMITS[k]
    if not lo <= x <= hi:
      sys.exit(f"{k}={x:g} is outside {lo:g} .. {hi:g}")
    tune[k] = x
  return tune


def wait_ack(sock, tune):
  """what controlsd applied, from the event it logs for each tune it takes (cloudlog -> logMessage), or None"""
  end = time.monotonic() + ACK_TIMEOUT
  while time.monotonic() < end:
    m = messaging.recv_one(sock)
    if m is None:
      continue
    try:
      msg = json.loads(m.logMessage)['msg']
    except (ValueError, KeyError, TypeError):
      continue
    if isinstance(msg, dict) and msg.get('event') == 'lateral_tune' and msg.get('requested') == tune:
      return msg['applied']
  return None


def main():
  params = Params()
  shipped = shipped_tune(next(iter(STEER_MODELS.values())))  # the Volt's, the one car on LatControlSteer
  tune = params.get("LateralTune") or {}
  if len(sys.argv) == 1:
    show(tune, shipped)
    return

  tune = {} if sys.argv[1:] == ['--reset'] else parse(sys.argv[1:], tune)
  onroad = not params.get_bool("IsOffroad")
  sock = messaging.sub_sock('logMessage', timeout=100) if onroad else None
  if tune:
    params.put("LateralTune", tune, block=True)
  else:
    params.remove("LateralTune")
  show(tune, shipped)

  if not onroad:
    print("offroad: applies from the start of the next drive, until it ends")
    return
  applied = wait_ack(sock, tune)
  if applied is None:
    print(f"controlsd didn't confirm within {ACK_TIMEOUT:g} s")
    sys.exit(1)
  print(f"controlsd took it, blending in over {TUNE_RAMP:g} s: {applied or 'shipped values'}")


if __name__ == "__main__":
  main()
