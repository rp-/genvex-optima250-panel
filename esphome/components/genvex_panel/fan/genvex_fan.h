#pragma once

#include "esphome/components/fan/fan.h"
#include "../genvex_panel.h"

namespace esphome::genvex_panel {

// Steps 1–3 are speeds 1–3, boost is the preset mode "Boost", off is off.
class GenvexFan final : public fan::Fan, public Parented<GenvexPanel> {
 public:
  GenvexFan();
  fan::FanTraits get_traits() override;
  void publish_mode(FanMode mode);

 protected:
  void control(const fan::FanCall &call) override;
};

}  // namespace esphome::genvex_panel
