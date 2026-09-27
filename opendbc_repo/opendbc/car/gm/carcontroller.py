import math
import numpy as np
from opendbc.can import CANPacker
from opendbc.car import Bus, DT_CTRL, structs, ACCELERATION_DUE_TO_GRAVITY
from opendbc.car.lateral import apply_driver_steer_torque_limits
from opendbc.car.common.filter_simple import FirstOrderFilter
from opendbc.car.gm import gmcan
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.values import DBC, CanBus, CarControllerParams, CruiseButtons, LongOwner
from opendbc.car.interfaces import CarControllerBase

VisualAlert = structs.CarControl.HUDControl.VisualAlert
NetworkLocation = structs.CarParams.NetworkLocation
LongCtrlState = structs.CarControl.Actuators.LongControlState

# Camera cancels up to 0.1s after brake is pressed, ECM allows 0.5s
CAMERA_CANCEL_DELAY_FRAMES = 10
# Enforce a minimum interval between steering messages to avoid a fault
MIN_STEER_MSG_INTERVAL_MS = 15


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.start_time = 0.
    self.apply_torque_last = 0
    self.apply_gas = 0
    self.accel_request = 0.  # the acceleration request carried by whichever controller owns it, m/s^2
    self.brake_accel = 0.    # the EBCM's signed request, m/s^2: negative braking, positive releasing held braking
    self.last_steer_frame = 0
    self.last_button_frame = 0
    self.cancel_counter = 0

    self.lka_steering_cmd_counter = 0
    self.lka_icon_status_last = (False, False)

    self.params = CarControllerParams(self.CP)

    self.packer_pt = CANPacker(DBC[self.CP.carFingerprint][Bus.pt])
    self.packer_obj = CANPacker(DBC[self.CP.carFingerprint][Bus.radar])
    self.packer_ch = CANPacker(DBC[self.CP.carFingerprint][Bus.chassis])

    # two-owner longitudinal allocation (GMFlags.ASCM_LONG)
    self.owner = LongOwner.POWERTRAIN
    self.pitch = FirstOrderFilter(0., self.params.PITCH_FILTER_RC, DT_CTRL)
    # near-stop hold (see CarControllerParams): set when openpilot commits to a stop, cleared by launch intent
    self.stop_hold = False

  def update_pitch(self, CC):
    """Filter the device localizer's pitch (north-east-down frame: nose down is negative), the road grade the
    allocation compensates. Runs every control frame whether or not long control is active, so an engage starts
    from the current slope rather than the one at the last disengagement; a stale uphill estimate on a descent
    would hand a braking request to the powertrain as drive torque for the filter's settling time."""
    if len(CC.orientationNED) == 3:
      self.pitch.update(CC.orientationNED[1])

  def allocate_long(self, CC, CS, stopping):
    """Gas (Nm) and the EBCM's signed acceleration request (m/s^2): one acceleration request, given to either
    the powertrain, which converts it to torque, or the brake controller (see GMFlags.ASCM_LONG in values.py)."""
    p = self.params
    v = CS.out.vEgo
    accel = CC.actuators.accel

    # Near-stop hold: on from the stopping state, through any shouldStop flicker, until long control asks to go
    # (or goes inactive, see update). Releasing it just returns to the ordinary allocation below: the brake
    # controller keeps the request and eases it where gravity or creep already supply the acceleration, and the
    # powertrain takes it where more is needed.
    self.stop_hold = stopping or (self.stop_hold and accel <= p.LAUNCH_INTENT_ACCEL)

    # On a downhill gravity supplies part of the requested acceleration, so the actuators only need to produce
    # the rest (filtered pitch from update_pitch)
    net = accel + math.sin(self.pitch.x) * ACCELERATION_DUE_TO_GRAVITY

    # Compare required torque with the minimum available after releasing the brakes, including creep.
    t_ff = p.torque_ff(net, v)
    t_floor = p.powertrain_torque_floor(CS.axle_torque_min, CS.axle_torque_min_valid, v)
    a_floor = p.accel_from_torque(t_floor, v)
    # Preserve the acceleration hysteresis across the drive/regen efficiency change.
    t_entry = p.torque_ff(a_floor + p.BRAKE_ENTRY_MARGIN, v)
    t_release = p.torque_ff(a_floor + p.BRAKE_RELEASE_MARGIN, v)

    if self.stop_hold or t_ff < t_entry:
      self.owner = LongOwner.BRAKE
    elif t_ff > t_release:
      self.owner = LongOwner.POWERTRAIN

    self.accel_request = net
    if self.owner == LongOwner.POWERTRAIN:
      gas = float(np.clip(t_ff, p.MAX_ACC_REGEN, p.MAX_GAS))
      return gas, 0.

    # brake controller: gas pinned at max ACC regen, the whole net effort as the signed request. It may go
    # positive to release retained braking; the near-stop hold keeps it non-positive. Bounded to the panda's
    # envelope on both sides, so a bad axle-torque report cannot produce a frame the safety would drop, and
    # quantized to the field's 0.01 m/s^2 so what is reported is what is sent.
    target = min(net, 0.) if self.stop_hold else net
    request = math.floor(float(np.clip(target, p.EBCM_ACCEL_MIN, p.EBCM_ACCEL_MAX)) * 100. + 0.5) / 100.
    return p.MAX_ACC_REGEN, request

  def update(self, CC, CS, now_nanos):
    actuators = CC.actuators
    hud_control = CC.hudControl
    hud_alert = hud_control.visualAlert
    hud_v_cruise = hud_control.setSpeed
    if hud_v_cruise > 70:
      hud_v_cruise = 0

    self.update_pitch(CC)

    # Send CAN commands.
    can_sends = []

    # Steering (Active: 50Hz, inactive: 10Hz)
    steer_step = self.params.STEER_STEP if CC.latActive else self.params.INACTIVE_STEER_STEP

    if self.CP.networkLocation == NetworkLocation.fwdCamera:
      # Also send at 50Hz:
      # - on startup, first few msgs are blocked
      # - until we're in sync with camera so counters align when relay closes, preventing a fault.
      #   openpilot can subtly drift, so this is activated throughout a drive to stay synced
      out_of_sync = self.lka_steering_cmd_counter % 4 != (CS.cam_lka_steering_cmd_counter + 1) % 4
      if CS.loopback_lka_steering_cmd_ts_nanos == 0 or out_of_sync:
        steer_step = self.params.STEER_STEP

    self.lka_steering_cmd_counter += 1 if CS.loopback_lka_steering_cmd_updated else 0

    # Avoid GM EPS faults when transmitting messages too close together: skip this transmit if we
    # received the ASCMLKASteeringCmd loopback confirmation too recently
    last_lka_steer_msg_ms = (now_nanos - CS.loopback_lka_steering_cmd_ts_nanos) * 1e-6
    if (self.frame - self.last_steer_frame) >= steer_step and last_lka_steer_msg_ms > MIN_STEER_MSG_INTERVAL_MS:
      # Initialize ASCMLKASteeringCmd counter using the camera until we get a msg on the bus
      if CS.loopback_lka_steering_cmd_ts_nanos == 0:
        self.lka_steering_cmd_counter = CS.pt_lka_steering_cmd_counter + 1

      if CC.latActive:
        new_torque = int(round(actuators.torque * self.params.STEER_MAX))
        apply_torque = apply_driver_steer_torque_limits(new_torque, self.apply_torque_last, CS.out.steeringTorque, self.params)
      else:
        apply_torque = 0

      self.last_steer_frame = self.frame
      self.apply_torque_last = apply_torque
      idx = self.lka_steering_cmd_counter % 4
      can_sends.append(gmcan.create_steering_control(self.packer_pt, CanBus.POWERTRAIN, apply_torque, idx, CC.latActive))

    if self.CP.openpilotLongitudinalControl:
      # Gas/regen, brakes, and UI commands - all at 25Hz
      if self.frame % 4 == 0:
        stopping = actuators.longControlState == LongCtrlState.stopping
        if not CC.longActive:
          # ASCM sends max regen when not enabled
          self.apply_gas = self.params.INACTIVE_REGEN
          self.brake_accel = 0.
          self.accel_request = 0.
          self.owner = LongOwner.POWERTRAIN
          self.stop_hold = False
        elif self.params.ASCM_LONG:
          # two-owner allocation (see CarControllerParams)
          self.apply_gas, self.brake_accel = self.allocate_long(CC, CS, stopping)
        else:
          # platforms not yet confirmed on the two-owner allocation: the historical mapping, gas and brake at once
          self.accel_request = actuators.accel
          self.apply_gas = float(np.interp(actuators.accel, self.params.GAS_LOOKUP_BP, self.params.GAS_LOOKUP_V))
          self.brake_accel = float(np.interp(actuators.accel, self.params.BRAKE_LOOKUP_BP, self.params.BRAKE_LOOKUP_V))
          # Don't allow any gas above inactive regen while stopping
          # FIXME: brakes aren't applied immediately when enabling at a stop
          if stopping:
            self.apply_gas = self.params.INACTIVE_REGEN

        idx = (self.frame // 4) % 4

        at_full_stop = CC.longActive and CS.out.standstill
        # 0xB while the near-stop hold is on (GMFlags.ASCM_LONG); other platforms keep 0xA
        near_stop = CC.longActive and self.params.ASCM_LONG and self.stop_hold
        friction_brake_bus = CanBus.CHASSIS
        # GM Camera exceptions
        # TODO: can we always check the longControlState?
        if self.CP.networkLocation == NetworkLocation.fwdCamera:
          at_full_stop = at_full_stop and stopping
          friction_brake_bus = CanBus.POWERTRAIN

        # GasRegenCmdActive needs to be 1 to avoid cruise faults. It describes the ACC state, not actuation
        can_sends.append(gmcan.create_gas_regen_command(self.packer_pt, CanBus.POWERTRAIN, self.apply_gas, idx, CC.enabled, at_full_stop))
        brake_mode = gmcan.friction_brake_mode(self.brake_accel < 0., CC.enabled,
                                               CC.longActive and self.owner == LongOwner.BRAKE, near_stop, at_full_stop, self.CP)
        can_sends.append(gmcan.create_friction_brake_command(self.packer_ch, friction_brake_bus, self.brake_accel, idx, brake_mode))

        # Send dashboard UI commands (ACC status)
        send_fcw = hud_alert == VisualAlert.fcw
        can_sends.append(gmcan.create_acc_dashboard_command(self.packer_pt, CanBus.POWERTRAIN, CC.enabled,
                                                            hud_v_cruise * CV.MS_TO_KPH, hud_control, send_fcw))

      # Radar needs to know current speed and yaw rate (50hz),
      # and that ADAS is alive (10hz)
      if not self.CP.radarUnavailable:
        tt = self.frame * DT_CTRL
        time_and_headlights_step = 10
        if self.frame % time_and_headlights_step == 0:
          idx = (self.frame // time_and_headlights_step) % 4
          can_sends.append(gmcan.create_adas_time_status(CanBus.OBSTACLE, int((tt - self.start_time) * 60), idx))
          can_sends.append(gmcan.create_adas_headlights_status(self.packer_obj, CanBus.OBSTACLE))

        speed_and_accelerometer_step = 2
        if self.frame % speed_and_accelerometer_step == 0:
          idx = (self.frame // speed_and_accelerometer_step) % 4
          can_sends.append(gmcan.create_adas_steering_status(CanBus.OBSTACLE, idx))
          can_sends.append(gmcan.create_adas_accelerometer_speed_status(CanBus.OBSTACLE, abs(CS.out.vEgo), idx))

      if self.CP.networkLocation == NetworkLocation.gateway and self.frame % self.params.ADAS_KEEPALIVE_STEP == 0:
        can_sends += gmcan.create_adas_keepalive(CanBus.POWERTRAIN)

    else:
      # While car is braking, cancel button causes ECM to enter a soft disable state with a fault status.
      # A delayed cancellation allows camera to cancel and avoids a fault when user depresses brake quickly
      self.cancel_counter = self.cancel_counter + 1 if CC.cruiseControl.cancel else 0

      # Stock longitudinal, integrated at camera
      if (self.frame - self.last_button_frame) * DT_CTRL > 0.04:
        if self.cancel_counter > CAMERA_CANCEL_DELAY_FRAMES:
          self.last_button_frame = self.frame
          can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.CAMERA, CS.buttons_counter, CruiseButtons.CANCEL))

    if self.CP.networkLocation == NetworkLocation.fwdCamera:
      # Silence "Take Steering" alert sent by camera, forward PSCMStatus with HandsOffSWlDetectionStatus=1
      if self.frame % 10 == 0:
        can_sends.append(gmcan.create_pscm_status(self.packer_pt, CanBus.CAMERA, CS.pscm_status))

    new_actuators = actuators.as_builder()
    new_actuators.torque = self.apply_torque_last / self.params.STEER_MAX
    new_actuators.torqueOutputCan = self.apply_torque_last
    new_actuators.accel = self.accel_request
    new_actuators.gas = self.apply_gas
    new_actuators.brake = max(-self.brake_accel, 0.)

    self.frame += 1
    return new_actuators, can_sends
