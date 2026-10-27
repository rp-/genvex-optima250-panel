#include "fan_mode_select.h"

namespace esphome::genvex_panel {

void FanModeSelect::control(size_t index) {
  // options: "Off", "Step 1", "Step 2", "Step 3", "Boost"
  this->parent_->set_fan_mode(static_cast<FanMode>(index));
}

}  // namespace esphome::genvex_panel
