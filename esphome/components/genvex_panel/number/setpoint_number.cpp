#include "setpoint_number.h"

namespace esphome::genvex_panel {

void SetpointNumber::control(float value) { this->parent_->set_setpoint(value); }

}  // namespace esphome::genvex_panel
