#pragma once

#include "esphome/components/switch/switch.h"
#include "../genvex_panel.h"

namespace esphome::genvex_panel {

class PreheatSwitch final : public switch_::Switch, public Parented<GenvexPanel> {
 protected:
  void write_state(bool state) override;
};

}  // namespace esphome::genvex_panel
