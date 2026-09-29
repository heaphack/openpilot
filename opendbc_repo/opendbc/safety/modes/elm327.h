#pragma once

#include "opendbc/safety/declarations.h"
#include "opendbc/safety/modes/defaults.h"

static bool elm327_tx_hook(const CANPacket_t *msg) {
  const unsigned int GM_CAMERA_DIAG_ADDR = 0x24BU;
  // GM power steering control module (GMLAN physical diagnostic ID, response at 0x642). Fork-only: 0x242 is a
  // periodic message on BYD (DRIVE_STATE) and MG (RADAR_HSC2_FrP00), so this exception is not suitable upstream.
  const unsigned int GM_PSCM_DIAG_ADDR = 0x242U;
  const bool gm_diag_addr = (msg->addr == GM_CAMERA_DIAG_ADDR) || (msg->addr == GM_PSCM_DIAG_ADDR);

  bool tx = true;
  int len = GET_LEN(msg);

  // All ISO 15765-4 messages must be 8 bytes long
  if (len != 8) {
    tx = false;
  }

  // Check valid 29 bit send addresses for ISO 15765-4
  // Check valid 11 bit send addresses for ISO 15765-4
  if ((msg->addr != 0x18DB33F1U) && ((msg->addr & 0x1FFF00FFU) != 0x18DA00F1U) &&
      ((msg->addr & 0x1FFFFF00U) != 0x600U) && ((msg->addr & 0x1FFFFF00U) != 0x700U) &&
      !gm_diag_addr) {
    tx = false;
  }

  // GM camera and PSCM use non-standard diagnostic addresses, these have no control message address collisions
  if (gm_diag_addr && (len == 8)) {
    // Only allow known frame types for ISO 15765-2
    if ((msg->data[0] & 0xF0U) > 0x30U) {
      tx = false;
    }
  }
  return tx;
}

// If safety_param == 0, bus 1 is multiplexed to the OBD-II port
const safety_hooks elm327_hooks = {
  .init = nooutput_init,
  .rx = default_rx_hook,
  .tx = elm327_tx_hook,
};
