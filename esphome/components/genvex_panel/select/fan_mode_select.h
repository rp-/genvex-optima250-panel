#pragma once

#include "esphome/components/select/select.h"
#include "../genvex_panel.h"

namespace esphome::genvex_panel {

class FanModeSelect final : public select::Select, public Parented<GenvexPanel> {
 protected:
  void control(size_t index) override;
};

}  // namespace esphome::genvex_panel
