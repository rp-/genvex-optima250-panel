#pragma once

#include "esphome/components/number/number.h"
#include "../genvex_panel.h"

namespace esphome::genvex_panel {

class SetpointNumber final : public number::Number, public Parented<GenvexPanel> {
 protected:
  void control(float value) override;
};

}  // namespace esphome::genvex_panel
