#include "preheat_switch.h"

namespace esphome::genvex_panel {

void PreheatSwitch::write_state(bool state) { this->parent_->set_preheat(state); }

}  // namespace esphome::genvex_panel
