"""own-v1 forwarding supervisor on c11 transport. Times are CAN monotonic seconds.

These host deadlines are provisional; they are not physical actuator latency bounds.
Live CAN format follows the existing GM Global A transport assumptions. The decoder
also accepts explicit framing flags for offline validation when they are available.
"""
from dataclasses import dataclass, field
from enum import IntEnum


class Owner(IntEnum):
  UNSELECTED = 0
  OEM = 1
  OPENPILOT = 2


STATUS_TIMEOUT = 0.160
OUTPUT_TIMEOUT = (0.220, 0.160, 0.160, 0.160)  # steering, gas, UI, brake
PENDING_TIMEOUT = 0.750


@dataclass(frozen=True)
class Report:
  owner: Owner
  available: bool
  forwarding_permitted: bool
  sequence: int
  generation: int
  modes: tuple[int, ...]
  reasons: tuple[int, ...]
  completed: tuple[int, ...]
  raw: bytes


def decode(address, data, bus, *, extended=False, remote=False):
  if extended or remote or (address, bus) not in ((0x37D, 1), (0x37C, 2)) or len(data) != 8:
    raise ValueError("c11 status transport")
  header, seq, modes, reasons, a, b, c, generation = data
  owner = header & 3
  available, forwarding_permitted = bool(header & 4), bool(header & 8)
  if header >> 4 != 2 or owner == 3 or (forwarding_permitted and owner != Owner.OPENPILOT) or (available and owner == Owner.OEM):
    raise ValueError("c11 status header")
  if address == 0x37D:
    mode, reason, completed = (modes >> 4, modes & 15), (reasons >> 4, reasons & 15), (a, b, c)
  else:
    if modes >> 4 != 15 or reasons >> 4 != 15 or b or c:
      raise ValueError("c11 brake status reserved fields")
    mode, reason, completed = (modes & 15,), (reasons & 15,), (a,)
  if any(v > 2 for v in mode) or any(v > 4 for v in reason):
    raise ValueError("c11 status mode/reason")
  return Report(Owner(owner), available, forwarding_permitted, seq, generation, mode, reason, completed, bytes(data))


@dataclass
class Stream:
  report: Report | None = None
  received: float = -1.
  count: int = 0
  progress: list[float | None] = field(default_factory=list)


class AscmSupervisor:
  def __init__(self):
    self.streams = [Stream(), Stream()]
    self.epoch = 0
    self.pending_until = None
    self.pending_epoch = 0
    self.set_released = False
    self.reason = "Waiting for both c11 status streams"

  def invalidate(self, reason):
    # Preserve the last local modes/reasons for diagnosis, but discard all qualification.
    for stream in self.streams:
      stream.count = 0
      stream.progress = [None] * len(stream.progress)
    self.epoch += 1
    self.pending_until = None
    self.reason = reason

  def receive(self, address, data, bus, now):
    if (address, bus) not in ((0x37D, 1), (0x37C, 2)):
      return  # wrong buses/legacy IDs cannot qualify or refresh either stream
    stream = self.streams[address == 0x37C]
    try:
      report = decode(address, data, bus)
    except ValueError:
      self.invalidate("Invalid c11 status")
      return
    old = stream.report
    deadlines = OUTPUT_TIMEOUT[:3] if address == 0x37D else OUTPUT_TIMEOUT[3:]
    if any(t is not None and now - t > deadline for t, deadline in zip(stream.progress, deadlines, strict=False)):
      self.invalidate("ASCM output observation gap")
    if old is not None:
      dt = now - stream.received
      if dt < 0 or dt > STATUS_TIMEOUT or report.generation != old.generation:
        self.invalidate("Status gap or selection generation changed")
      if report.sequence == old.sequence:
        return  # even a changed payload with a duplicate sequence is not trusted
      elif (report.sequence - old.sequence) % 256 > 8:
        self.invalidate("Status sequence restarted")
      if ((old.available and not report.available) or (old.owner == Owner.OPENPILOT and report.owner != old.owner) or
          (old.forwarding_permitted and not report.forwarding_permitted) or
          (all(m == 1 for m in old.modes) and any(m != 1 for m in report.modes))):
        self.invalidate("ASCM readiness withdrawn")
    if stream.count == 0:
      stream.progress = [None] * len(report.completed)
    else:
      for i, (before, after) in enumerate(zip(old.completed, report.completed, strict=True)):
        delta = (after - before) % 256
        if delta > 127:
          self.invalidate("Output counter restarted")
          break
        if delta:
          stream.progress[i] = now
    stream.report, stream.received = report, now
    stream.count += 1

  def healthy(self, now):
    for stream in self.streams:
      if stream.count and not 0 <= now - stream.received <= STATUS_TIMEOUT:
        self.invalidate("Missing or stale c11 status")
        return False
    if any(s.count < 3 for s in self.streams):
      return False
    reports = [s.report for s in self.streams]
    if reports[0].generation != reports[1].generation:
      self.reason = "ASCM selection generations disagree"
      return False
    if any(not r.available or any(m != 1 for m in r.modes) for r in reports):
      self.reason = "ASCM input or peer unavailable"
      return False
    progress = self.streams[0].progress + self.streams[1].progress
    if any(t is None for t in progress):
      self.reason = "Waiting for all four ASCM outputs"
      return False
    if any(not 0 <= now - t <= timeout for t, timeout in zip(progress, OUTPUT_TIMEOUT, strict=True)):
      self.invalidate("ASCM output stalled")
      return False
    return True

  def permitted(self, now):
    if not self.healthy(now):
      return False
    if any(s.report.owner != Owner.OPENPILOT for s in self.streams):
      self.reason = "Waiting for agreed OPENPILOT ownership"
      return False
    # own-v1 grants permission while commands are still inactive. It must remain
    # asserted across disengagement, pedal override and the ACCActive resume pulse.
    # It is authorization to forward commands, not confirmation of engagement.
    if not all(s.report.forwarding_permitted for s in self.streams):
      self.reason = "Waiting for both ASCM forwarding permissions"
      return False
    self.reason = "Ready"
    return True

  @property
  def oem_owned(self):
    return any(s.count and s.report.owner == Owner.OEM for s in self.streams)

  def driver_request(self, now, events, allowed):
    healthy = self.healthy(now)
    if not allowed or not healthy or self.oem_owned:
      self.pending_until = None
      return False
    for event in events:
      if event.type == "cancel":
        self.pending_until = None
        return False
      if event.type in ("accelCruise", "decelCruise") and event.pressed:
        # A physical press is the intent; SET must also be released for Panda.
        # The ASCM can process the press before the host, so either processor
        # may already report OPENPILOT while its peer is still UNSELECTED.
        # healthy() above requires fresh qualified inputs, output progress and
        # matching generations. Ownership must agree before permitted() grants
        # this request; disagreement here must not discard the physical press.
        if all(s.report.owner in (Owner.UNSELECTED, Owner.OPENPILOT) for s in self.streams):
          self.pending_until = now + PENDING_TIMEOUT
          self.pending_epoch = self.epoch
          self.set_released = event.type == "accelCruise"
      elif event.type == "decelCruise" and not event.pressed:
        self.set_released = True
    if self.pending_until is None:
      return False
    if now > self.pending_until or self.epoch != self.pending_epoch:
      self.pending_until = None
      return False
    if self.set_released and self.permitted(now):
      self.pending_until = None
      return True
    return False
