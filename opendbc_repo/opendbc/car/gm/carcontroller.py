import math
import numpy as np
from opendbc.can import CANPacker
from opendbc.car import Bus, DT_CTRL, structs, ACCELERATION_DUE_TO_GRAVITY
from opendbc.car.lateral import apply_driver_steer_torque_limits
from opendbc.car.common.filter_simple import FirstOrderFilter
from opendbc.car.gm import gmcan
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.values import DBC, CanBus, CarControllerParams, CruiseButtons, GMFlags, LongOwner
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
    self.last_steer_torque_cmd = 0
    # Cached longitudinal outputs for reporting between 25 Hz command updates.
    self.axle_torque_cmd = 0
    self.reported_accel = 0.  # cached acceleration output for logging, m/s^2
    self.brake_accel_cmd = 0.  # the EBCM's signed request, m/s^2: negative braking, positive releasing held braking
    self.last_steer_frame = 0
    self.last_button_frame = 0
    self.cancel_counter = 0

    self.lka_steering_cmd_counter = 0
    self.lka_icon_status_last = (False, False)

    self.params = CarControllerParams(self.CP)

    # With an ASCM interceptor harness our commands enter on the ASCM's bus and the stock ASCM stays
    # alive, so we neither impersonate it to the radar and ADAS modules nor keep them alive ourselves.
    self.interceptor = bool(self.CP.flags & GMFlags.ASCM_INTERCEPTOR)
    self.cmd_bus = CanBus.OBSTACLE if self.interceptor else CanBus.POWERTRAIN

    self.packer_pt = CANPacker(DBC[self.CP.carFingerprint][Bus.pt])
    self.packer_obj = CANPacker(DBC[self.CP.carFingerprint][Bus.radar])
    self.packer_ch = CANPacker(DBC[self.CP.carFingerprint][Bus.chassis])

    # two-owner longitudinal allocation (GMFlags.ASCM_LONG)
    self.long_owner = LongOwner.POWERTRAIN
    self.pitch_filter = FirstOrderFilter(0., self.params.PITCH_FILTER_RC, DT_CTRL)
    # near-stop hold (see CarControllerParams): set when openpilot commits to a stop, cleared by launch intent
    self.stop_hold_latched = False

  def update_pitch(self, CC):
    """Filter the device localizer's pitch (north-east-down frame: nose down is negative), the road grade the
    allocation compensates. Runs every control frame whether or not long control is active, so an engage starts
    from the current slope rather than the one at the last disengagement; a stale uphill estimate on a descent
    would hand a braking request to the powertrain as drive torque for the filter's settling time."""
    if len(CC.orientationNED) == 3:
      self.pitch_filter.update(CC.orientationNED[1])

  def update_ascm_longitudinal(self, CC, CS, idx):
    """Build the gas/regen and brake commands using the ASCM-inspired allocation, at 25 Hz."""
    p = self.params
    v = CS.out.vEgo
    vehicle_accel_request = CC.actuators.accel
    stopping = CC.actuators.longControlState == LongCtrlState.stopping

    if not CC.longActive:
      axle_torque_cmd, brake_accel_cmd, grade_compensated_accel = p.INACTIVE_REGEN, 0., 0.
      self.long_owner = LongOwner.POWERTRAIN
      self.stop_hold_latched = False
    else:
      # Near-stop hold: on from the stopping state, through any shouldStop flicker, until long control asks to go
      # (or goes inactive). Releasing it just returns to the ordinary allocation below: the brake
      # controller keeps the request and eases it where gravity or creep already supply the acceleration, and the
      # powertrain takes it where more is needed.
      self.stop_hold_latched = stopping or (self.stop_hold_latched and vehicle_accel_request <= p.LAUNCH_INTENT_ACCEL)

      # Compensate gravity when calculating powertrain torque and selecting the owner.
      # The EBCM receives the vehicle acceleration target directly.
      grade_compensated_accel = vehicle_accel_request + math.sin(self.pitch_filter.x) * ACCELERATION_DUE_TO_GRAVITY

      # Compare required torque with the minimum available after releasing the brakes, including creep.
      axle_torque_request = p.torque_ff(grade_compensated_accel, v)
      axle_torque_floor = p.powertrain_torque_floor(CS.axle_torque_min, CS.axle_torque_min_valid, v)
      powertrain_accel_floor = p.accel_from_torque(axle_torque_floor, v)
      # Preserve the acceleration hysteresis across the drive/regen efficiency change.
      brake_entry_torque = p.torque_ff(powertrain_accel_floor + p.BRAKE_ENTRY_MARGIN, v)
      brake_release_torque = p.torque_ff(powertrain_accel_floor + p.BRAKE_RELEASE_MARGIN, v)

      if self.stop_hold_latched or axle_torque_request < brake_entry_torque:
        self.long_owner = LongOwner.BRAKE
      elif axle_torque_request > brake_release_torque:
        self.long_owner = LongOwner.POWERTRAIN

      if self.long_owner == LongOwner.POWERTRAIN:
        axle_torque_cmd = float(np.clip(axle_torque_request, p.MAX_ACC_REGEN, p.MAX_GAS))
        brake_accel_cmd = 0.
      else:
        # Request vehicle acceleration; the EBCM supplies the braking needed to achieve it.
        # Near-stop hold keeps the request non-positive. Clamp to the panda's envelope
        # and quantize to 0.01 m/s^2 so the reported value matches the transmitted request.
        brake_accel_request = min(vehicle_accel_request, 0.) if self.stop_hold_latched else vehicle_accel_request
        brake_accel_cmd = math.floor(float(np.clip(brake_accel_request, p.EBCM_ACCEL_MIN, p.EBCM_ACCEL_MAX)) * 100. + 0.5) / 100.
        axle_torque_cmd = p.MAX_ACC_REGEN

    at_full_stop = CC.longActive and CS.out.standstill
    # Brake hold ends with stop_hold_latched, allowing a brake-owned launch before the wheels move.
    # 0xB while the near-stop hold is on
    stopping_mode_requested = CC.longActive and self.stop_hold_latched
    friction_brake_bus = CanBus.OBSTACLE if self.interceptor else CanBus.CHASSIS
    # GM Camera exceptions
    # TODO: can we always check the longControlState?
    if self.CP.networkLocation == NetworkLocation.fwdCamera:
      at_full_stop = at_full_stop and stopping
      friction_brake_bus = CanBus.POWERTRAIN

    # GasRegenCmdActive needs to be 1 to avoid cruise faults. It describes the ACC state, not actuation
    gas_regen_active = CC.enabled
    if self.CP.autoResumeSng:
      # The ECM latches its ACC standstill state at a stop and holds it until the ACC request is
      # re-asserted. Once openpilot wants to move again (the near-stop hold released), drop
      # GasRegenCmdActive for the frames the ECM still reports standstill: it clears the latch and the car
      # pulls away without a driver resume. The standstill submode (0xD) is keyed on the same ECM state so
      # the brake hold is only released when the resume is actually under way. Whichever controller owns
      # the request then carries it: drive torque, or an eased brake request on a downhill.
      resume_from_stop = (CC.longActive and CS.cruise_standstill and not self.stop_hold_latched and
                          not CS.out.brakePressed)
      at_full_stop = CC.longActive and CS.cruise_standstill and not resume_from_stop
      if resume_from_stop:
        gas_regen_active = False

    brake_mode = gmcan.friction_brake_mode(
      brake_accel_cmd < 0., CC.enabled, CC.longActive and self.long_owner == LongOwner.BRAKE,
      stopping_mode_requested, at_full_stop and self.stop_hold_latched, self.CP)
    self.axle_torque_cmd = axle_torque_cmd
    self.brake_accel_cmd = brake_accel_cmd
    # Report the signed brake request after hold limiting, clipping, and CAN quantization.
    self.reported_accel = brake_accel_cmd if self.long_owner == LongOwner.BRAKE else grade_compensated_accel
    return [
      gmcan.create_gas_regen_command(self.packer_pt, self.cmd_bus, axle_torque_cmd, idx, gas_regen_active, at_full_stop),
      gmcan.create_friction_brake_command(self.packer_ch, friction_brake_bus, brake_accel_cmd, idx, brake_mode),
    ]

  def update_legacy_longitudinal(self, CC, CS, idx):
    """Build the gas/regen and brake commands using the existing lookup tables, at 25 Hz."""
    p = self.params
    vehicle_accel_request = CC.actuators.accel
    stopping = CC.actuators.longControlState == LongCtrlState.stopping

    if not CC.longActive:
      axle_torque_cmd, brake_accel_cmd, vehicle_accel_request = p.INACTIVE_REGEN, 0., 0.
    else:
      axle_torque_cmd = float(np.interp(vehicle_accel_request, p.GAS_LOOKUP_BP, p.GAS_LOOKUP_V))
      # Preserve upstream's count rounding before selecting the brake mode.
      brake_lookup_counts = [-100. * a for a in p.BRAKE_LOOKUP_V]
      brake_counts = int(round(np.interp(vehicle_accel_request, p.BRAKE_LOOKUP_BP, brake_lookup_counts)))
      brake_accel_cmd = -brake_counts / 100.
      # Don't allow any gas above inactive regen while stopping.
      # FIXME: brakes aren't applied immediately when enabling at a stop.
      if stopping:
        axle_torque_cmd = p.INACTIVE_REGEN

    at_full_stop = CC.longActive and CS.out.standstill
    friction_brake_bus = CanBus.OBSTACLE if self.interceptor else CanBus.CHASSIS
    if self.CP.networkLocation == NetworkLocation.fwdCamera:
      at_full_stop = at_full_stop and stopping
      friction_brake_bus = CanBus.POWERTRAIN

    gas_regen_active = CC.enabled
    if self.CP.autoResumeSng:
      # Preserve the existing resume behavior for a legacy configuration with auto-resume enabled.
      resume_from_stop = CC.longActive and CS.cruise_standstill and not CS.out.brakePressed
      at_full_stop = CC.longActive and CS.cruise_standstill and not resume_from_stop
      if resume_from_stop:
        gas_regen_active = False

    brake_mode = gmcan.friction_brake_mode(brake_accel_cmd < 0., CC.enabled, False, False, at_full_stop, self.CP)
    self.axle_torque_cmd, self.brake_accel_cmd, self.reported_accel = axle_torque_cmd, brake_accel_cmd, vehicle_accel_request
    return [
      gmcan.create_gas_regen_command(self.packer_pt, self.cmd_bus, axle_torque_cmd, idx, gas_regen_active, at_full_stop),
      gmcan.create_friction_brake_command(self.packer_ch, friction_brake_bus, brake_accel_cmd, idx, brake_mode),
    ]

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
        steer_torque_request = int(round(actuators.torque * self.params.STEER_MAX))
        steer_torque_cmd = apply_driver_steer_torque_limits(
          steer_torque_request, self.last_steer_torque_cmd, CS.out.steeringTorque, self.params)
      else:
        steer_torque_cmd = 0

      self.last_steer_frame = self.frame
      self.last_steer_torque_cmd = steer_torque_cmd
      idx = self.lka_steering_cmd_counter % 4
      can_sends.append(gmcan.create_steering_control(self.packer_pt, self.cmd_bus, steer_torque_cmd, idx, CC.latActive))

    if self.CP.openpilotLongitudinalControl:
      # Gas/regen, brakes, and UI commands - all at 25Hz
      if self.frame % 4 == 0:
        idx = (self.frame // 4) % 4
        if self.params.ASCM_LONG:
          can_sends.extend(self.update_ascm_longitudinal(CC, CS, idx))
        else:
          can_sends.extend(self.update_legacy_longitudinal(CC, CS, idx))

        # Send dashboard UI commands (ACC status)
        send_fcw = hud_alert == VisualAlert.fcw
        can_sends.append(gmcan.create_acc_dashboard_command(self.packer_pt, self.cmd_bus, CC.enabled,
                                                            hud_v_cruise * CV.MS_TO_KPH, hud_control, send_fcw))

      # Radar needs to know current speed and yaw rate (50hz),
      # and that ADAS is alive (10hz)
      if not self.CP.radarUnavailable and not self.interceptor:
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

      if self.CP.networkLocation == NetworkLocation.gateway and not self.interceptor and self.frame % self.params.ADAS_KEEPALIVE_STEP == 0:
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
    new_actuators.torque = self.last_steer_torque_cmd / self.params.STEER_MAX
    new_actuators.torqueOutputCan = self.last_steer_torque_cmd
    new_actuators.accel = self.reported_accel
    new_actuators.gas = self.axle_torque_cmd
    new_actuators.brake = max(-self.brake_accel_cmd, 0.)

    self.frame += 1
    return new_actuators, can_sends
