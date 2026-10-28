#include "genvex_fan.h"

namespace esphome::genvex_panel {

static const char *const PRESET_BOOST = "Boost";

GenvexFan::GenvexFan() {
  this->set_supported_preset_modes({PRESET_BOOST});
  this->speed = FAN_STEP1;  // "turn on" from off resumes this step; nonzero, so FanCall does not pick 100 %
}

fan::FanTraits GenvexFan::get_traits() {
  fan::FanTraits traits(false, true, false, FAN_STEP3);
  this->wire_preset_modes_(traits);
  return traits;
}

void GenvexFan::control(const fan::FanCall &call) {
  FanMode mode = this->parent_->get_fan_mode();
  auto state = call.get_state();
  auto speed = call.get_speed();  // already clamped to 1–3
  if (state.has_value() && !*state) {
    mode = FAN_OFF;
  } else if (call.has_preset_mode()) {
    mode = FAN_BOOST;  // the only preset
  } else if (speed.has_value()) {
    mode = static_cast<FanMode>(*speed);
  } else if (state.has_value() && mode == FAN_OFF) {
    mode = static_cast<FanMode>(this->speed);  // last step before off
  }
  this->parent_->set_fan_mode(mode);
}

void GenvexFan::publish_mode(FanMode mode) {
  this->state = mode != FAN_OFF;
  // off and boost keep the last step, so "turn on" and the end of boost show it again
  if (mode >= FAN_STEP1 && mode <= FAN_STEP3)
    this->speed = mode;
  if (mode == FAN_BOOST) {
    this->set_preset_mode_(PRESET_BOOST);
  } else {
    this->clear_preset_mode_();
  }
  this->publish_state();
}

}  // namespace esphome::genvex_panel
