from dataclasses import dataclass, field
from enum import Enum, IntEnum, IntFlag

import numpy as np

from opendbc.car import Bus, PlatformConfig, DbcDict, Platforms, CarSpecs
from opendbc.car.structs import CarParams
from opendbc.car.docs_definitions import CarDocs, CarFootnote, CarHarness, CarParts, Column
from opendbc.car.fw_query_definitions import FwQueryConfig, Request, StdQueries

Ecu = CarParams.Ecu


class CarControllerParams:
  STEER_MAX = 300  # GM limit is 3Nm. Used by carcontroller to generate LKA output
  STEER_STEP = 3  # Active control frames per command (~33hz)
  INACTIVE_STEER_STEP = 10  # Inactive control frames per command (10hz)
  STEER_DELTA_UP = 10  # Delta rates require review due to observed EPS weakness
  STEER_DELTA_DOWN = 15
  STEER_DRIVER_ALLOWANCE = 65
  STEER_DRIVER_MULTIPLIER = 4
  STEER_DRIVER_FACTOR = 100

  # Heartbeat for dash "Service Adaptive Cruise" and "Service Front Camera"
  ADAS_KEEPALIVE_STEP = 100
  CAMERA_KEEPALIVE_STEP = 100

  # Allow small margin below -3.5 m/s^2 from ISO 15622:2018 since we
  # perform the closed loop control, and might need some
  # to apply some more braking if we're on a downhill slope.
  # Our controller should still keep the 2 second average above
  # -3.5 m/s^2 as per planner limits
  ACCEL_MAX = 2.  # m/s^2
  ACCEL_MIN = -4.  # m/s^2

  # ---- GMFlags.ASCM_LONG: two-owner longitudinal allocation ----
  # EBCMFrictionBrakeCmd carries signed acceleration. The legacy tables request powertrain torque and
  # braking together; this allocator assigns the request to one owner (LongOwner):
  #   POWERTRAIN: vehicle-model axle torque, with the EBCM in its platform-specific idle mode.
  #   BRAKE:      axle torque at the negative safety limit; the EBCM receives vehicle acceleration and
  #               blends regen and friction to meet it.
  # Ownership compares grade-compensated acceleration with the predicted powertrain minimum after brake
  # release, including released creep, with hysteresis. A zero EBCM request keeps acceleration control
  # enabled; it does not command zero or constant pressure. Positive requests can ease retained braking.
  # The creep fit and vehicle-model parameters are for the Volt; other platforms require validation.

  # Grade estimate: filtered localizer pitch; smoothing does not separate suspension motion from road slope.
  PITCH_FILTER_RC = 0.5           # s

  # ---- near-stop hold (FrictionBrakeMode 0xB) ----
  # openpilot's shouldStop is the model's raw acceleration output crossing +0.1 m/s^2 below 0.3 m/s, with no
  # hysteresis, and at a crawl it flickers for 50-500 ms. Following that flicker out of the stopping state
  # released the brakes: in 0xA the EBCM lets the pressure go on any reduction of the request at a stop, the
  # ECM's own standstill hold (0xD) is still 1.2-1.7 s away, and creep rolls the car. So once openpilot commits
  # to a stop the brake controller holds the near-stop submode, which brings the car to a stop and keeps it
  # there whatever the numeric request does, until long control asks for clearly more than the flicker ever
  # does. The flickers seen so far peak at +0.14 m/s^2; real launches pass this within ~0.3 s.
  LAUNCH_INTENT_ACCEL = 0.3       # m/s^2

  # EBCMFrictionBrakeCmd is a signed acceleration request in m/s^2 (0.01 per count). These mirror the panda's
  # [-400, +200] count envelope: a positive request only releases braking the EBCM already holds.
  EBCM_ACCEL_SAFETY_MIN = -4.
  EBCM_ACCEL_SAFETY_MAX = 2.

  def __init__(self, CP):
    # Axle torque command safety limits (Nm), shared by both allocation paths.
    if CP.carFingerprint in (CAMERA_ACC_CAR | SDGM_CAR):
      self.AXLE_TORQUE_SAFETY_MAX = 1346.0
      self.AXLE_TORQUE_SAFETY_MIN = -540.0
      self.LONG_INACTIVE_AXLE_TORQUE = -500.0
      # Camera ACC vehicles have no regen while enabled.
      # Camera transitions to AXLE_TORQUE_SAFETY_MIN from zero gas and uses friction brakes instantly
      legacy_brake_blend_accel = 0.

    else:
      self.AXLE_TORQUE_SAFETY_MAX = 1018.0  # Safety limit, not ACC max. Stock ACC >2042 from standstill.
      self.AXLE_TORQUE_SAFETY_MIN = -650.0  # Max ACC regen is slightly less than max paddle regen
      self.LONG_INACTIVE_AXLE_TORQUE = -650.0
      # ICE has much less engine braking force compared to regen in EVs,
      # lower threshold removes some braking deadzone
      legacy_brake_blend_accel = -1. if CP.carFingerprint in EV_CAR else -0.1

    # Legacy mapping: acceleration breakpoints (m/s²) to axle torque (Nm).
    # Below legacy_brake_blend_accel, torque stays at its minimum and the brake lookup adds braking.
    self.LEGACY_AXLE_TORQUE_BP = [legacy_brake_blend_accel, 0., self.ACCEL_MAX]
    self.LEGACY_AXLE_TORQUE_V = [self.AXLE_TORQUE_SAFETY_MIN, 0., self.AXLE_TORQUE_SAFETY_MAX]

    # The EBCM request as a function of the planner's acceleration, in the field's own units (m/s^2). This is
    # the mapping openpilot has always sent these platforms, written when the field was read as a brake
    # pressure (400 counts at ACCEL_MIN): it asks the EBCM for less than the planner's deceleration and adds
    # regen on the gas path at the same time. Retained unchanged until each platform is confirmed on the
    # two-owner allocation, which sends the planner's acceleration itself.
    self.LEGACY_BRAKE_ACCEL_BP = [self.ACCEL_MIN, legacy_brake_blend_accel]
    self.LEGACY_BRAKE_ACCEL_V = [self.EBCM_ACCEL_SAFETY_MIN, 0.]

    # two-owner allocation above instead of the lookups
    self.ASCM_LONG = bool(CP.flags & GMFlags.ASCM_LONG)
    if CP.carFingerprint == CAR.CHEVROLET_VOLT:
      # Volt vehicle model: road-load force plus mass * acceleration, converted to axle torque.
      self.MODEL_MASS = 1776.                 # kg, includes a typical load on top of the curb weight
      self.ROLLING_RESISTANCE_ACCEL = 0.0785   # m/s^2, coefficient 0.008 x g
      self.AERO_DRAG_FACTOR = 0.25            # N / (m/s)^2
      self.TIRE_RADIUS = 0.3234               # m, effective radius (2032 mm rolling circumference / 2 pi)
      self.DRIVETRAIN_EFFICIENCY = 0.88       # divide for drive torque, multiply for regen

      # Owner hysteresis around the predicted powertrain minimum, m/s^2.
      self.BRAKE_ENTRY_ACCEL_MARGIN = -0.1
      self.BRAKE_RELEASE_ACCEL_MARGIN = 0.2

      # Released-creep fit to actual Volt axle torque: speed in m/s, torque in Nm.
      self.CREEP_TORQUE_BP = [0., 1.44]
      self.CREEP_TORQUE_V = [323., 0.]
      # Fade back to the live limit before the table ends, avoiding a jump into negative regen.
      self.CREEP_FADE_BP = [1.10, 1.44]
    elif self.ASCM_LONG:
      raise ValueError(f"ASCM longitudinal calibration missing for {CP.carFingerprint}")

  # ---- vehicle-model helpers ----
  def accel_to_axle_torque(self, accel, v_ego):
    """Convert grade-compensated acceleration (m/s²) to axle torque (Nm), including road loads and efficiency."""
    t = (self.MODEL_MASS * (accel + self.ROLLING_RESISTANCE_ACCEL) + self.AERO_DRAG_FACTOR * v_ego * v_ego) * self.TIRE_RADIUS
    return t / self.DRIVETRAIN_EFFICIENCY if t > 0 else t * self.DRIVETRAIN_EFFICIENCY

  def axle_torque_to_accel(self, torque, v_ego):
    """Convert axle torque (Nm) to acceleration (m/s²), excluding road grade; inverse of accel_to_axle_torque."""
    t = torque * self.DRIVETRAIN_EFFICIENCY if torque > 0 else torque / self.DRIVETRAIN_EFFICIENCY
    return (t / self.TIRE_RADIUS - self.AERO_DRAG_FACTOR * v_ego * v_ego) / self.MODEL_MASS - self.ROLLING_RESISTANCE_ACCEL

  def predict_minimum_powertrain_accel(self, axle_torque_min, valid, v_ego):
    """Predict minimum powertrain acceleration after brake release, excluding road grade, in m/s².
    The live torque report can fall near zero during hold.
    An invalid report counts as no regen available (0 Nm): the brake controller then carries every braking
    request and the EBCM blends in whatever regen there is, rather than the allocator crediting the powertrain
    with braking it cannot see. The creep table still applies below the creep speed."""
    reported = max(axle_torque_min, self.AXLE_TORQUE_SAFETY_MIN) if valid else 0.
    creep = float(np.interp(v_ego, self.CREEP_TORQUE_BP, self.CREEP_TORQUE_V))
    if creep <= 0.:
      return self.axle_torque_to_accel(reported, v_ego)
    blend = float(np.interp(v_ego, self.CREEP_FADE_BP, [1., 0.]))
    blend = blend * blend * (3. - 2. * blend)
    minimum_torque = reported + blend * max(creep - reported, 0.)
    return self.axle_torque_to_accel(minimum_torque, v_ego)


class LongOwner(IntEnum):
  POWERTRAIN = 0   # AxleTorqueCmd carries the request (drive or regen), EBCM idle
  BRAKE = 1        # AxleTorqueCmd pinned at max regen, EBCM carries the signed request


class GMFlags(IntFlag):
  # Detected flags
  HAS_BSM = 1  # blind spot monitoring

  # Static flags
  # Two-owner longitudinal allocation: a vehicle-model torque feedforward to the powertrain, a signed
  # acceleration request to the EBCM, and the handoff between them driven by the powertrain's reported
  # minimum axle torque (0x1C5). See CarControllerParams. Set per platform once confirmed on that car.
  ASCM_LONG = 2
  # The car keeps its stock ASCM and openpilot sits between the ASCM and the rest of the car on the ASCM's
  # own bus (an interceptor harness) instead of replacing the ASCM at the OBD-II gateway. openpilot's
  # commands enter on the obstacle bus, the ASCM keeps the radar and ADAS modules alive itself, and the
  # loopback of our own commands appears on that bus. Describes the harness, not the car.
  ASCM_INTERCEPTOR = 4


class GMSafetyFlags(IntFlag):
  HW_CAM = 1
  HW_CAM_LONG = 2
  EV = 4
  ASCM_INTERCEPTOR = 8


class Footnote(Enum):
  SETUP = CarFootnote(
    "See more setup details for <a href=\"https://github.com/commaai/openpilot/wiki/gm\" target=\"_blank\">GM</a>.",
    Column.MAKE, setup_note=True)


@dataclass
class GMCarDocs(CarDocs):
  package: str = "Adaptive Cruise Control (ACC)"

  def init_make(self, CP: CarParams):
    if CP.networkLocation == CarParams.NetworkLocation.fwdCamera:
      if CP.carFingerprint in SDGM_CAR:
        self.car_parts = CarParts.common([CarHarness.gmsdgm])
      else:
        self.car_parts = CarParts.common([CarHarness.gm])
    else:
      self.footnotes.insert(0, Footnote.SETUP)
      self.car_parts = CarParts.common([CarHarness.obd_ii])


@dataclass(frozen=True, kw_only=True)
class GMCarSpecs(CarSpecs):
  tireStiffnessFactor: float = 0.444  # not optimized yet


@dataclass
class GMPlatformConfig(PlatformConfig):
  dbc_dict: DbcDict = field(default_factory=lambda: {
    Bus.pt: 'gm_global_a_powertrain_generated',
    Bus.radar: 'gm_global_a_object',
    Bus.chassis: 'gm_global_a_chassis',
  })


@dataclass
class GMASCMPlatformConfig(GMPlatformConfig):
  def init(self):
    # ASCM is supported, but due to a janky install and hardware configuration, we are not showing in the car docs
    self.car_docs = []


@dataclass
class GMSDGMPlatformConfig(GMPlatformConfig):
  def init(self):
    # Don't show in docs until the harness is sold. See https://github.com/commaai/openpilot/issues/32471
    self.car_docs = []


class CAR(Platforms):
  HOLDEN_ASTRA = GMASCMPlatformConfig(
    [GMCarDocs("Holden Astra 2017")],
    GMCarSpecs(mass=1363, wheelbase=2.662, steerRatio=15.7, centerToFrontRatio=0.4),
  )
  CHEVROLET_VOLT = GMASCMPlatformConfig(
    [GMCarDocs("Chevrolet Volt 2017-18", min_enable_speed=0, video="https://youtu.be/QeMCN_4TFfQ")],
    GMCarSpecs(mass=1607, wheelbase=2.69, steerRatio=17.7, centerToFrontRatio=0.45, tireStiffnessFactor=0.469),
    flags=GMFlags.ASCM_LONG | GMFlags.ASCM_INTERCEPTOR,
  )
  CADILLAC_ATS = GMASCMPlatformConfig(
    [GMCarDocs("Cadillac ATS Premium Performance 2018")],
    GMCarSpecs(mass=1601, wheelbase=2.78, steerRatio=15.3),
  )
  CHEVROLET_MALIBU = GMASCMPlatformConfig(
    [GMCarDocs("Chevrolet Malibu Premier 2017")],
    GMCarSpecs(mass=1496, wheelbase=2.83, steerRatio=15.8, centerToFrontRatio=0.4),
  )
  GMC_ACADIA = GMASCMPlatformConfig(
    [GMCarDocs("GMC Acadia 2018", video="https://www.youtube.com/watch?v=0ZN6DdsBUZo")],
    GMCarSpecs(mass=1975, wheelbase=2.86, steerRatio=14.4, centerToFrontRatio=0.4),
  )
  BUICK_LACROSSE = GMASCMPlatformConfig(
    [GMCarDocs("Buick LaCrosse 2017-19", "Driver Confidence Package 2")],
    GMCarSpecs(mass=1712, wheelbase=2.91, steerRatio=15.8, centerToFrontRatio=0.4),
  )
  BUICK_REGAL = GMASCMPlatformConfig(
    [GMCarDocs("Buick Regal Essence 2018")],
    GMCarSpecs(mass=1714, wheelbase=2.83, steerRatio=14.4, centerToFrontRatio=0.4),
  )
  CADILLAC_ESCALADE = GMASCMPlatformConfig(
    [GMCarDocs("Cadillac Escalade 2017", "Driver Assist Package")],
    GMCarSpecs(mass=2564, wheelbase=2.95, steerRatio=17.3),
  )
  CADILLAC_ESCALADE_ESV = GMASCMPlatformConfig(
    [GMCarDocs("Cadillac Escalade ESV 2016", "Adaptive Cruise Control (ACC) & LKAS")],
    GMCarSpecs(mass=2739, wheelbase=3.302, steerRatio=17.3, tireStiffnessFactor=1.0),
  )
  CADILLAC_ESCALADE_ESV_2019 = GMASCMPlatformConfig(
    [GMCarDocs("Cadillac Escalade ESV 2019", "Adaptive Cruise Control (ACC) & LKAS")],
    CADILLAC_ESCALADE_ESV.specs,
  )
  CHEVROLET_BOLT_EUV = GMPlatformConfig(
    [
      GMCarDocs("Chevrolet Bolt EUV 2022-23", "Premier or Premier Redline Trim, without Super Cruise Package", video="https://youtu.be/xvwzGMUA210"),
      GMCarDocs("Chevrolet Bolt EV 2022-23", "2LT Trim with Adaptive Cruise Control Package"),
    ],
    GMCarSpecs(mass=1669, wheelbase=2.63779, steerRatio=16.8, centerToFrontRatio=0.4, tireStiffnessFactor=1.0),
  )
  CHEVROLET_SILVERADO = GMPlatformConfig(
    [
      GMCarDocs("Chevrolet Silverado 1500 2020-21", "Safety Package II"),
      GMCarDocs("GMC Sierra 1500 2020-21", "Driver Alert Package II", video="https://youtu.be/5HbNoBLzRwE"),
    ],
    GMCarSpecs(mass=2450, wheelbase=3.75, steerRatio=16.3, tireStiffnessFactor=1.0),
  )
  CHEVROLET_EQUINOX = GMPlatformConfig(
    [GMCarDocs("Chevrolet Equinox 2019-22")],
    GMCarSpecs(mass=1588, wheelbase=2.72, steerRatio=14.4, centerToFrontRatio=0.4),
  )
  CHEVROLET_TRAILBLAZER = GMPlatformConfig(
    [GMCarDocs("Chevrolet Trailblazer 2021-22")],
    GMCarSpecs(mass=1345, wheelbase=2.64, steerRatio=16.8, centerToFrontRatio=0.4, tireStiffnessFactor=1.0),
  )
  CADILLAC_XT4 = GMSDGMPlatformConfig(
    [GMCarDocs("Cadillac XT4 2023", "Driver Assist Package")],
    GMCarSpecs(mass=1660, wheelbase=2.78, steerRatio=14.4, centerToFrontRatio=0.4),
  )
  CHEVROLET_VOLT_2019 = GMSDGMPlatformConfig(
    [GMCarDocs("Chevrolet Volt 2019", "Adaptive Cruise Control (ACC) & LKAS")],
    GMCarSpecs(mass=1607, wheelbase=2.69, steerRatio=15.7, centerToFrontRatio=0.45),
  )
  CHEVROLET_TRAVERSE = GMSDGMPlatformConfig(
    [GMCarDocs("Chevrolet Traverse 2022-23", "RS, Premier, or High Country Trim")],
    GMCarSpecs(mass=1955, wheelbase=3.07, steerRatio=17.9, centerToFrontRatio=0.4),
  )
  GMC_YUKON = GMPlatformConfig(
    [GMCarDocs("GMC Yukon 2019-20", "Adaptive Cruise Control (ACC) & LKAS")],
    GMCarSpecs(mass=2490, wheelbase=2.94, steerRatio=17.3, centerToFrontRatio=0.5, tireStiffnessFactor=1.0),
  )


class CruiseButtons:
  INIT = 0
  UNPRESS = 1
  RES_ACCEL = 2
  DECEL_SET = 3
  MAIN = 5
  CANCEL = 6


class AccState:
  OFF = 0
  ACTIVE = 1
  FAULTED = 3
  STANDSTILL = 4


class CanBus:
  POWERTRAIN = 0
  OBSTACLE = 1
  CAMERA = 2
  CHASSIS = 2
  LOOPBACK = 128
  DROPPED = 192


# In a Data Module, an identifier is a string used to recognize an object,
# either by itself or together with the identifiers of parent objects.
# Each returns a 4 byte hex representation of the decimal part number. `b"\x02\x8c\xf0'"` -> 42790951
GM_BOOT_SOFTWARE_PART_NUMER_REQUEST = b'\x1a\xc0'  # likely does not contain anything useful
GM_SOFTWARE_MODULE_1_REQUEST = b'\x1a\xc1'
GM_SOFTWARE_MODULE_2_REQUEST = b'\x1a\xc2'
GM_SOFTWARE_MODULE_3_REQUEST = b'\x1a\xc3'

# Part number of XML data file that is used to configure ECU
GM_XML_DATA_FILE_PART_NUMBER = b'\x1a\x9c'
GM_XML_CONFIG_COMPAT_ID = b'\x1a\x9b'  # used to know if XML file is compatible with the ECU software/hardware

# This DID is for identifying the part number that reflects the mix of hardware,
# software, and calibrations in the ECU when it first arrives at the vehicle assembly plant.
# If there's an Alpha Code, it's associated with this part number and stored in the DID $DB.
GM_END_MODEL_PART_NUMBER_REQUEST = b'\x1a\xcb'
GM_END_MODEL_PART_NUMBER_ALPHA_CODE_REQUEST = b'\x1a\xdb'
GM_BASE_MODEL_PART_NUMBER_REQUEST = b'\x1a\xcc'
GM_BASE_MODEL_PART_NUMBER_ALPHA_CODE_REQUEST = b'\x1a\xdc'
GM_FW_RESPONSE = b'\x5a'

GM_FW_REQUESTS = [
  GM_BOOT_SOFTWARE_PART_NUMER_REQUEST,
  GM_SOFTWARE_MODULE_1_REQUEST,
  GM_SOFTWARE_MODULE_2_REQUEST,
  GM_SOFTWARE_MODULE_3_REQUEST,
  GM_XML_DATA_FILE_PART_NUMBER,
  GM_XML_CONFIG_COMPAT_ID,
  GM_END_MODEL_PART_NUMBER_REQUEST,
  GM_END_MODEL_PART_NUMBER_ALPHA_CODE_REQUEST,
  GM_BASE_MODEL_PART_NUMBER_REQUEST,
  GM_BASE_MODEL_PART_NUMBER_ALPHA_CODE_REQUEST,
]

GM_RX_OFFSET = 0x400      # GMLAN physical diagnostic IDs 0x241-0x25F answer at request + 0x400
GM_OBD_RX_OFFSET = 0x8    # emissions-related modules at 0x7E0-0x7E7 answer at request + 0x8 (0x7E8-0x7EF)

# ECU types reached through each address range. The FW query sends a request only to ECUs whose
# type is whitelisted, so each range gets its own response offset without doubling the query time.
GM_GMLAN_ECUS = [Ecu.eps, Ecu.fwdCamera]
GM_OBD_ECUS = [Ecu.engine, Ecu.hybrid, Ecu.abs, Ecu.electricBrakeBooster]


def gm_fw_request(req: bytes, rx_offset: int, whitelist_ecus: list, logging: bool = True) -> Request:
  return Request(
    [StdQueries.SHORT_TESTER_PRESENT_REQUEST, req],
    [StdQueries.SHORT_TESTER_PRESENT_RESPONSE, GM_FW_RESPONSE + bytes([req[-1]])],
    whitelist_ecus=whitelist_ecus,
    rx_offset=rx_offset,
    bus=0,
    logging=logging,
  )


FW_QUERY_CONFIG = FwQueryConfig(
  fw_version_regex=br"[\x00-\xff]+",
  requests=[gm_fw_request(req, GM_RX_OFFSET, GM_GMLAN_ECUS) for req in GM_FW_REQUESTS] +
           [gm_fw_request(req, GM_OBD_RX_OFFSET, GM_OBD_ECUS) for req in GM_FW_REQUESTS],
  # Data collection only: responses from these ECUs are logged, not matched on.
  # Addresses and bus from the GDS2 VAT database (2017 Chevrolet Volt, GMLAN high speed bus).
  extra_ecus=[
    (Ecu.fwdCamera, 0x24b, None),             # FCM on camera-ACC cars; the ASCM on ASCM cars such as the Volt
    (Ecu.eps, 0x242, None),                   # Power Steering Control Module
    (Ecu.engine, 0x7e0, None),                # Engine Control Module
    (Ecu.hybrid, 0x7e1, None),                # Hybrid Powertrain Control Module
    (Ecu.abs, 0x7e5, None),                   # Electronic Brake Control Module
    (Ecu.electricBrakeBooster, 0x7e6, None),  # Brake Booster Control Module
  ],
)

# TODO: detect most of these sets live
EV_CAR = {CAR.CHEVROLET_VOLT, CAR.CHEVROLET_VOLT_2019, CAR.CHEVROLET_BOLT_EUV}

# We're integrated at the camera with VOACC on these cars (instead of ASCM w/ OBD-II harness)
CAMERA_ACC_CAR = {CAR.CHEVROLET_BOLT_EUV, CAR.CHEVROLET_SILVERADO, CAR.CHEVROLET_EQUINOX, CAR.CHEVROLET_TRAILBLAZER, CAR.GMC_YUKON}

# Alt ASCMActiveCruiseControlStatus
ALT_ACCS = {CAR.GMC_YUKON}

# We're integrated at the Safety Data Gateway Module on these cars
SDGM_CAR = {CAR.CADILLAC_XT4, CAR.CHEVROLET_VOLT_2019, CAR.CHEVROLET_TRAVERSE}

STEER_THRESHOLD = 1.0

DBC = CAR.create_dbc_map()
