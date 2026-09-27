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
  # The lookup tables below treat EBCMFrictionBrakeCmd as a brake pressure. It is a signed acceleration
  # request, and the EBCM blends regen and friction itself to meet it. With the flag set, the acceleration
  # request is given to one of two owners (LongOwner) instead of both lookups at once:
  #   POWERTRAIN: GasRegenCmd = vehicle-model feedforward T(a, v) below, EBCM idle (FrictionBrakeMode 0x1)
  #   BRAKE:      GasRegenCmd = fixed max ACC regen (-650 Nm), EBCM gets the whole request as a signed
  #               0.01 m/s^2 acceleration with the brake path active (mode 0xA)
  # The brake controller takes the request when the net effort (after grade) drops below the minimum axle
  # torque available after brake release (0x1C5 AxleTorqueMin plus a Volt creep estimate) and hands it
  # back with hysteresis. While it owns the request, a zero request holds the
  # pressure already applied, so the request may go slightly positive to release it. Confirmed on the Volt;
  # 0x1C5 is a Global A powertrain message present on every GM platform, so other ASCM cars are expected to
  # work once the vehicle-model constants below are set for them.
  #
  # Feedforward: T[Nm] = (M*(a + G_CRR) + CD*v^2) * R, then x(1/EFF) for drive torque, xEFF for regen.
  FF_MASS = 1776.          # kg, fixed; includes a typical load on top of the curb weight
  FF_G_CRR = 0.0785        # m/s^2, rolling resistance as an acceleration (coefficient 0.008 x g)
  FF_CD = 0.25             # N per (m/s)^2, aerodynamic drag
  FF_R = 0.3234            # m, effective tire radius (2032 mm rolling circumference / 2 pi)
  FF_EFF = 0.88            # drivetrain efficiency: divide for drive torque, multiply for regen

  # Owner hysteresis band around the estimated powertrain floor, m/s^2: enter the brake path a little below what the
  # powertrain can deliver, release only once the request is clearly above it.
  BRAKE_ENTRY_MARGIN = -0.1
  BRAKE_RELEASE_MARGIN = 0.2

  # Released-creep estimate for the Volt, fitted to actual axle torque. Speed in m/s, torque in Nm.
  CREEP_TORQUE_BP = [0., 1.44]
  # Fade the model back to the live limit before the table ends, avoiding a jump into negative regen.
  CREEP_FADE_BP = [1.10, 1.44]

  # Grade: the device localizer's pitch, smoothed so brake dive and squat do not read as road slope
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
  EBCM_ACCEL_MIN = -4.
  EBCM_ACCEL_MAX = 2.

  def __init__(self, CP):
    # Gas/brake lookups (platforms without GMFlags.ASCM_LONG)
    if CP.carFingerprint in (CAMERA_ACC_CAR | SDGM_CAR):
      self.MAX_GAS = 1346.0
      self.MAX_ACC_REGEN = -540.0
      self.INACTIVE_REGEN = -500.0
      # Camera ACC vehicles have no regen while enabled.
      # Camera transitions to MAX_ACC_REGEN from zero gas and uses friction brakes instantly
      max_regen_acceleration = 0.

    else:
      self.MAX_GAS = 1018.0  # Safety limit, not ACC max. Stock ACC >2042 from standstill.
      self.MAX_ACC_REGEN = -650.0  # Max ACC regen is slightly less than max paddle regen
      self.INACTIVE_REGEN = -650.0
      # ICE has much less engine braking force compared to regen in EVs,
      # lower threshold removes some braking deadzone
      max_regen_acceleration = -1. if CP.carFingerprint in EV_CAR else -0.1

    self.GAS_LOOKUP_BP = [max_regen_acceleration, 0., self.ACCEL_MAX]
    self.GAS_LOOKUP_V = [self.MAX_ACC_REGEN, 0., self.MAX_GAS]

    # The EBCM request as a function of the planner's acceleration, in the field's own units (m/s^2). This is
    # the mapping openpilot has always sent these platforms, written when the field was read as a brake
    # pressure (400 counts at ACCEL_MIN): it asks the EBCM for less than the planner's deceleration and adds
    # regen on the gas path at the same time. Retained unchanged until each platform is confirmed on the
    # two-owner allocation, which sends the planner's acceleration itself.
    self.BRAKE_LOOKUP_BP = [self.ACCEL_MIN, max_regen_acceleration]
    self.BRAKE_LOOKUP_V = [self.EBCM_ACCEL_MIN, 0.]

    # two-owner allocation above instead of the lookups
    self.ASCM_LONG = bool(CP.flags & GMFlags.ASCM_LONG)
    self.CREEP_TORQUE_V = [323., 0.] if CP.carFingerprint == CAR.CHEVROLET_VOLT else [0., 0.]

  # ---- vehicle-model helpers ----
  def torque_ff(self, accel, v_ego):
    """Axle torque (Nm) needed for an accel target: mass, rolling resistance and drag, then drivetrain efficiency."""
    t = (self.FF_MASS * (accel + self.FF_G_CRR) + self.FF_CD * v_ego * v_ego) * self.FF_R
    return t / self.FF_EFF if t > 0 else t * self.FF_EFF

  def accel_from_torque(self, torque, v_ego):
    """Inverse of torque_ff."""
    t = torque * self.FF_EFF if torque > 0 else torque / self.FF_EFF
    return (t / self.FF_R - self.FF_CD * v_ego * v_ego) / self.FF_MASS - self.FF_G_CRR

  def powertrain_torque_floor(self, axle_torque_min, valid, v_ego):
    """Estimate minimum axle torque after brake release; the live report can fall near zero during hold.
    An invalid report counts as no regen available (0 Nm): the brake controller then carries every braking
    request and the EBCM blends in whatever regen there is, rather than the allocator crediting the powertrain
    with braking it cannot see. The creep table still applies below the creep speed."""
    reported = max(axle_torque_min, self.MAX_ACC_REGEN) if valid else 0.
    creep = float(np.interp(v_ego, self.CREEP_TORQUE_BP, self.CREEP_TORQUE_V))
    if creep <= 0.:
      return reported
    blend = float(np.interp(v_ego, self.CREEP_FADE_BP, [1., 0.]))
    blend = blend * blend * (3. - 2. * blend)
    return reported + blend * max(creep - reported, 0.)


class LongOwner(IntEnum):
  POWERTRAIN = 0   # GasRegenCmd carries the request (drive or regen), EBCM idle
  BRAKE = 1        # GasRegenCmd pinned at max regen, EBCM carries the signed request


class GMFlags(IntFlag):
  # Detected flags
  HAS_BSM = 1  # blind spot monitoring

  # Static flags
  # Two-owner longitudinal allocation: a vehicle-model torque feedforward to the powertrain, a signed
  # acceleration request to the EBCM, and the handoff between them driven by the powertrain's reported
  # minimum axle torque (0x1C5). See CarControllerParams. Set per platform once confirmed on that car.
  ASCM_LONG = 2


class GMSafetyFlags(IntFlag):
  HW_CAM = 1
  HW_CAM_LONG = 2
  EV = 4


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
    flags=GMFlags.ASCM_LONG,
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

GM_RX_OFFSET = 0x400

FW_QUERY_CONFIG = FwQueryConfig(
  fw_version_regex=br"[\x00-\xff]+",
  requests=[request for req in GM_FW_REQUESTS for request in [
    Request(
      [StdQueries.SHORT_TESTER_PRESENT_REQUEST, req],
      [StdQueries.SHORT_TESTER_PRESENT_RESPONSE, GM_FW_RESPONSE + bytes([req[-1]])],
      rx_offset=GM_RX_OFFSET,
      bus=0,
      logging=True,
    ),
  ]],
  extra_ecus=[(Ecu.fwdCamera, 0x24b, None)],
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
