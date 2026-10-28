#pragma once

#include <array>

#include "esphome/components/uart/uart.h"
#include "esphome/core/component.h"
#include "esphome/core/helpers.h"
#include "esphome/core/preferences.h"

#ifdef USE_SENSOR
#include "esphome/components/sensor/sensor.h"
#endif
#ifdef USE_BINARY_SENSOR
#include "esphome/components/binary_sensor/binary_sensor.h"
#endif
#ifdef USE_NUMBER
#include "esphome/components/number/number.h"
#endif
#ifdef USE_SWITCH
#include "esphome/components/switch/switch.h"
#endif

namespace esphome::genvex_panel {

// Fan speeds (service 10–15): supply step 1–3, then extract step 1–3, written to 0x13–0x18.
static constexpr uint8_t FAN_SPEED_COUNT = 6;

// Larger jumps between two cycles (raw, 10 K) need confirmation by the next cycle: the two
// bytes of a temperature are read separately, so a word crossing a 256 boundary in between
// reads ±25.6 K off once.
static constexpr uint16_t TEMP_MAX_JUMP = 100;

// Fan mode as offered to the user (fan entity: off, speed 1–3, preset "Boost"). OFF is the
// panel's calendar "H0", BOOST its "step 4" (step 3 at 100 %).
enum FanMode : uint8_t { FAN_OFF = 0, FAN_STEP1 = 1, FAN_STEP2 = 2, FAN_STEP3 = 3, FAN_BOOST = 4 };

#ifdef USE_FAN
class GenvexFan;
#endif

// One entry of the panel's poll cycle (see docs/protocol.md).
struct CycleItem {
  bool read;    // true: request "a b" (read), false: write to address a
  uint8_t a;    // 0x01/0x02 for reads, write address otherwise
  uint8_t b;    // read register (reads only)
  uint8_t tag;  // expected first reply byte
};

// Bus master replacing the ES950 panel on the ES960 panel link (terminals 21/22).
class GenvexPanel : public Component, public uart::UARTDevice {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  // configuration (called from generated code)
  void set_boot_delay(uint32_t ms) { this->boot_delay_ = ms; }
  void set_boost_duration(uint32_t ms) { this->boost_duration_ = ms; }
  void set_room_offset(float offset) { this->room_offset_ = offset; }
  void set_room_fallback(float celsius) { this->room_fallback_ = celsius; }
  void set_write_value(uint8_t addr, uint8_t value) { this->values_[addr] = value; }
  void set_default_fan_step(uint8_t step) { this->fan_mode_ = static_cast<FanMode>(step); }
  void set_default_setpoint(float celsius) { this->setpoint_raw_ = setpoint_to_raw(celsius); }
  void set_default_preheat(bool on) { this->preheat_ = on; }

#ifdef USE_SENSOR
  void set_room_sensor(sensor::Sensor *s) { this->room_sensor_ = s; }
  void set_supply_temperature_sensor(sensor::Sensor *s) { this->supply_temperature_ = s; }
  void set_outdoor_temperature_sensor(sensor::Sensor *s) { this->outdoor_temperature_ = s; }
  void set_exhaust_temperature_sensor(sensor::Sensor *s) { this->exhaust_temperature_ = s; }
  void set_extract_temperature_sensor(sensor::Sensor *s) { this->extract_temperature_ = s; }
  void set_supply_fan_sensor(sensor::Sensor *s) { this->supply_fan_ = s; }
  void set_extract_fan_sensor(sensor::Sensor *s) { this->extract_fan_ = s; }
  void set_bypass_damper_sensor(sensor::Sensor *s) { this->bypass_damper_ = s; }
#endif
#ifdef USE_BINARY_SENSOR
  void set_running_binary_sensor(binary_sensor::BinarySensor *s) { this->running_ = s; }
  void set_link_binary_sensor(binary_sensor::BinarySensor *s) { this->link_ = s; }
  void set_bypass_binary_sensor(binary_sensor::BinarySensor *s) { this->bypass_ = s; }
#endif
#ifdef USE_FAN
  void set_fan(GenvexFan *f) { this->fan_ = f; }
#endif
#ifdef USE_NUMBER
  void set_setpoint_number(number::Number *n) { this->setpoint_number_ = n; }
  void set_fan_speed_number(uint8_t index, number::Number *n) { this->fan_speed_numbers_[index] = n; }
#endif
#ifdef USE_SWITCH
  void set_preheat_switch(switch_::Switch *s) { this->preheat_switch_ = s; }
#endif

  // control (called by the entities)
  void set_fan_mode(FanMode mode);
  FanMode get_fan_mode() const { return this->fan_mode_; }
  void set_setpoint(float celsius);
  void set_preheat(bool on);
  void set_fan_speed(uint8_t index, uint8_t percent);

  static uint8_t setpoint_to_raw(float celsius);

 protected:
  enum class Phase : uint8_t { BOOT_READS, BOOT_PAUSE, CYCLE };
  enum class Step : uint8_t { SEND, SECOND, EVALUATE };

  uint8_t value_for_(uint8_t addr) const;
  void send_(uint8_t a, uint8_t b);
  uint8_t receive_(uint8_t *buf);
  void evaluate_(const CycleItem &item, uint8_t sent_value);
  void decode_read_(uint8_t a, uint8_t b, uint8_t value);
  void record_result_(bool ok);
  void save_();
  void load_fan_speeds_();
  void publish_controls_();

  // protocol state
  Phase phase_{Phase::BOOT_READS};
  Step step_{Step::SEND};
  size_t index_{0};
  uint32_t item_start_{0};
  uint32_t phase_start_{0};
  uint8_t sent_value_{0};
  uint8_t reply1_[2]{};
  uint8_t reply1_len_{0};
  uint8_t reply2_[2]{};
  uint8_t reply2_len_{0};
  uint8_t temp_hi_[17]{};
  uint16_t temp_raw_[9]{};      // last accepted word per temperature (index = register / 2)
  uint16_t temp_pending_[9]{};  // jump waiting for confirmation
  uint16_t temp_valid_{0};
  uint8_t status_last_[2][0x18]{};  // last value per non-temperature read, banks 01/02
  uint32_t status_seen_[2]{};
  uint16_t errors_in_row_{0};
  uint32_t transactions_{0};
  uint32_t failures_{0};
  bool link_ok_{false};
  bool link_reported_{false};
  HighFrequencyLoopRequester high_freq_;

  // configuration / settings
  uint32_t boot_delay_{2000};
  uint32_t boost_duration_{60 * 60 * 1000};
  float room_offset_{443.0f};
  float room_fallback_{21.0f};
  std::array<uint8_t, 256> values_{};
  FanMode fan_mode_{FAN_STEP1};
  FanMode before_boost_{FAN_STEP1};
  uint32_t boost_start_{0};
  uint8_t setpoint_raw_{105};
  bool preheat_{true};
  ESPPreferenceObject pref_;
  ESPPreferenceObject fan_pref_;

#ifdef USE_SENSOR
  sensor::Sensor *room_sensor_{nullptr};
  sensor::Sensor *supply_temperature_{nullptr};
  sensor::Sensor *outdoor_temperature_{nullptr};
  sensor::Sensor *exhaust_temperature_{nullptr};
  sensor::Sensor *extract_temperature_{nullptr};
  sensor::Sensor *supply_fan_{nullptr};
  sensor::Sensor *extract_fan_{nullptr};
  sensor::Sensor *bypass_damper_{nullptr};
#endif
#ifdef USE_BINARY_SENSOR
  binary_sensor::BinarySensor *running_{nullptr};
  binary_sensor::BinarySensor *link_{nullptr};
  binary_sensor::BinarySensor *bypass_{nullptr};
#endif
#ifdef USE_FAN
  GenvexFan *fan_{nullptr};
#endif
#ifdef USE_NUMBER
  number::Number *setpoint_number_{nullptr};
  number::Number *fan_speed_numbers_[FAN_SPEED_COUNT]{};
#endif
#ifdef USE_SWITCH
  switch_::Switch *preheat_switch_{nullptr};
#endif
};

}  // namespace esphome::genvex_panel
