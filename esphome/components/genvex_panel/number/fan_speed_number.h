#pragma once

#include "esphome/components/number/number.h"
#include "../genvex_panel.h"

namespace esphome::genvex_panel {

// Fan speed of one step (service 10–15); index 0–2 supply step 1–3, 3–5 extract step 1–3.
class FanSpeedNumber final : public number::Number, public Parented<GenvexPanel> {
 public:
  void set_index(uint8_t index) { this->index_ = index; }

 protected:
  void control(float value) override;

  uint8_t index_{0};
};

}  // namespace esphome::genvex_panel
