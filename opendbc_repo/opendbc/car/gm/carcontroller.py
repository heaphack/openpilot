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
    self.apply_torque_last = 0
    self.apply_gas = 0
    self.apply_brake = 0
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
    self.owner = LongOwner.POWERTRAIN
    self.pitch = FirstOrderFilter(0., self.params.PITCH_FILTER_RC, 4 * DT_CTRL)  # allocate_long runs at 25 Hz

  def allocate_long(self, CC, CS, stopping):
    """Gas (Nm) and brake (counts): give the accel request to either the powertrain or the brake controller
    (see GMFlags.ASCM_LONG in values.py)."""
    p = self.params
    v = CS.out.vEgo

    # Grade from the device localizer (north-east-down frame: nose down is negative). On a downhill gravity supplies part
    # of the requested acceleration, so the actuators only need to produce the rest.
    if len(CC.orientationNED) == 3:
      self.pitch.update(CC.orientationNED[1])
    net = CC.actuators.accel + math.sin(self.pitch.x) * ACCELERATION_DUE_TO_GRAVITY

    # regen the gas/regen path can deliver right now, from the powertrain's reported limit (0x1C5)
    t_min = CS.axle_torque_min if CS.axle_torque_min_valid else p.MAX_ACC_REGEN
    a_regen = p.regen_accel_available(t_min, v)

    # owner select with hysteresis; the brake controller keeps the request through a stop
    if stopping or net < a_regen + p.BRAKE_ENTRY_MARGIN:
      self.owner = LongOwner.BRAKE
    elif net > a_regen + p.BRAKE_RELEASE_MARGIN:
      self.owner = LongOwner.POWERTRAIN

    if self.owner == LongOwner.POWERTRAIN:
      # physics feedforward on the gas/regen path, brake controller idle
      gas = float(np.clip(p.torque_ff(net, v), p.MAX_ACC_REGEN, p.MAX_GAS))
      return gas, 0

    # brake controller: gas pinned at max ACC regen, the whole net effort as a signed request. It may go
    # positive to release retained braking; stopping and standstill keep it non-positive.
    target = min(net, 0.) if stopping or CS.out.standstill or CS.cruise_standstill else net
    brake = int(round(-max(target, p.ACCEL_MIN) * p.BRAKE_COUNTS_PER_MPS2))
    return p.MAX_ACC_REGEN, min(brake, p.MAX_BRAKE)

  def update(self, CC, CS, now_nanos):
    actuators = CC.actuators
    hud_control = CC.hudControl
    hud_alert = hud_control.visualAlert
    hud_v_cruise = hud_control.setSpeed
    if hud_v_cruise > 70:
      hud_v_cruise = 0

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
      can_sends.append(gmcan.create_steering_control(self.packer_pt, self.cmd_bus, apply_torque, idx, CC.latActive))

    if self.CP.openpilotLongitudinalControl:
      # Gas/regen, brakes, and UI commands - all at 25Hz
      if self.frame % 4 == 0:
        stopping = actuators.longControlState == LongCtrlState.stopping
        if not CC.longActive:
          # ASCM sends max regen when not enabled
          self.apply_gas = self.params.INACTIVE_REGEN
          self.apply_brake = 0
          self.owner = LongOwner.POWERTRAIN
        elif self.params.ASCM_LONG:
          # two-owner allocation (see CarControllerParams)
          self.apply_gas, self.apply_brake = self.allocate_long(CC, CS, stopping)
        else:
          self.apply_gas = float(np.interp(actuators.accel, self.params.GAS_LOOKUP_BP, self.params.GAS_LOOKUP_V))
          self.apply_brake = int(round(np.interp(actuators.accel, self.params.BRAKE_LOOKUP_BP, self.params.BRAKE_LOOKUP_V)))
          # Don't allow any gas above inactive regen while stopping
          # FIXME: brakes aren't applied immediately when enabling at a stop
          if stopping:
            self.apply_gas = self.params.INACTIVE_REGEN

        idx = (self.frame // 4) % 4

        at_full_stop = CC.longActive and CS.out.standstill
        near_stop = CC.longActive and (abs(CS.out.vEgo) < self.params.NEAR_STOP_BRAKE_PHASE)
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
          # re-asserted. Once openpilot wants to move again (drive torque requested, no brake request, not
          # stopping), drop GasRegenCmdActive for the frames the ECM still reports standstill: it clears the
          # latch and the car pulls away without a driver resume. The standstill submode (0xD) is keyed on
          # the same ECM state so the brake hold is only released when the resume is actually under way.
          resume_from_stop = (CC.longActive and CS.cruise_standstill and not stopping and
                              not CS.out.brakePressed and self.apply_gas >= 0. and self.apply_brake == 0)
          at_full_stop = CC.longActive and CS.cruise_standstill and not resume_from_stop
          if resume_from_stop:
            gas_regen_active = False

        can_sends.append(gmcan.create_gas_regen_command(self.packer_pt, self.cmd_bus, self.apply_gas, idx,
                                                       gas_regen_active, at_full_stop))
        can_sends.append(gmcan.create_friction_brake_command(self.packer_ch, friction_brake_bus, self.apply_brake,
                                                             idx, CC.enabled, near_stop, at_full_stop, self.CP,
                                                             brake_active=CC.longActive and self.owner == LongOwner.BRAKE))

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
    new_actuators.torque = self.apply_torque_last / self.params.STEER_MAX
    new_actuators.torqueOutputCan = self.apply_torque_last
    new_actuators.gas = self.apply_gas
    new_actuators.brake = self.apply_brake

    self.frame += 1
    return new_actuators, can_sends
