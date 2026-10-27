#include "fan_speed_number.h"

#include <cmath>

namespace esphome::genvex_panel {

void FanSpeedNumber::control(float value) {
  this->parent_->set_fan_speed(this->index_, static_cast<uint8_t>(std::lround(value)));
}

}  // namespace esphome::genvex_panel
