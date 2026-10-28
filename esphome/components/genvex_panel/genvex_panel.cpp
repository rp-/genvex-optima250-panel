#include "genvex_panel.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>

#include "esphome/core/hal.h"
#include "esphome/core/log.h"

#ifdef USE_FAN
#include "fan/genvex_fan.h"
#endif

namespace esphome::genvex_panel {

static const char *const TAG = "genvex_panel";

// Timing as measured on the original panel.
static constexpr uint32_t READ_SPACING_MS = 250;  // item start to next item start
static constexpr uint32_t WRITE_SPACING_MS = 225;
static constexpr uint32_t REPEAT_GAP_MS = 25;  // second copy of a read
static constexpr uint32_t COMMIT_GAP_MS = 20;  // "02 05" after a write
static constexpr uint32_t REPLY_WAIT_MS = 15;  // reply is complete ~2.5 ms after the request
static constexpr uint16_t LINK_LOST_AFTER = 6;  // consecutive failed transactions

static constexpr uint8_t ADDR_SETPOINT = 0x05;
static constexpr uint8_t ADDR_FAN_SPEED = 0x13;  // first of the six fan speed writes
static constexpr uint8_t ADDR_SUPPLY_STEP3 = 0x15;
static constexpr uint8_t ADDR_EXTRACT_STEP3 = 0x18;
static constexpr uint8_t ADDR_FAN_STEP_A = 0x42;
static constexpr uint8_t ADDR_FAN_STEP_B = 0x43;
static constexpr uint8_t FAN_STEP_OFF = 4;  // written to 42/43 for "H0"; the board stops after ~2 min
static const char *const FAN_MODE_NAMES[] = {"off", "step 1", "step 2", "step 3", "boost"};
static constexpr uint8_t ADDR_ROOM_TEMP = 0x47;
static constexpr uint8_t ADDR_PREHEAT = 0x49;

#define R(b, tag) \
  { true, (uint8_t) ((b) >> 8), (uint8_t) ((b) &0xFF), (tag) }
#define W(addr, tag) \
  { false, (addr), 0, (tag) }

// Read requests the panel sends at power-up.
static const CycleItem BOOT_ITEMS[] = {R(0x0204, 0xEC), R(0x0116, 0x97), R(0x0115, 0x98), R(0x0117, 0x94)};

// The panel's full poll cycle, in the original order (≈ 16 s).
static const CycleItem CYCLE[] = {
    R(0x0101, 0xFF), R(0x0102, 0xFE), R(0x0103, 0xFD), R(0x0104, 0xFC), R(0x0105, 0xFB), R(0x0106, 0xFA),
    R(0x0107, 0xF9), R(0x0108, 0xF8), R(0x0109, 0xF7), R(0x010A, 0xF6), R(0x010B, 0xF5), R(0x010C, 0xF4),
    R(0x010D, 0xF3), R(0x010E, 0xF2), R(0x010F, 0xF1), R(0x0110, 0xF0), R(0x0201, 0xEF), R(0x0202, 0xEE),
    R(0x0203, 0xED), R(0x0204, 0xEC),  //
    W(0x05, 0xEB),   W(0x06, 0xEA),   W(0x07, 0xE9),   W(0x08, 0xE8),   W(0x09, 0xE7),   W(0x0A, 0xE6),
    W(0x0B, 0xE5),   W(0x0C, 0xE4),   W(0x0D, 0xE3),   W(0x0E, 0xE2),   W(0x0F, 0xE1),   W(0x10, 0xE0),
    W(0x11, 0xDF),   W(0x12, 0xDE),   W(0x13, 0xDD),   W(0x14, 0xDC),   W(0x15, 0xDB),   W(0x16, 0xDA),
    W(0x17, 0xD9),   W(0x18, 0xD8),   W(0x41, 0xAF),   W(0x42, 0xAE),   W(0x43, 0xAD),   W(0x44, 0xAC),
    W(0x45, 0xAB),   W(0x46, 0xAA),   W(0x47, 0xA9),  //
    R(0x0111, 0xA8), R(0x0112, 0xA7), W(0x48, 0xA6),   R(0x0113, 0xA5), R(0x0114, 0xA4),  //
    W(0x49, 0xA3),   W(0x4A, 0xA2),   W(0x4B, 0xA1),   W(0x4C, 0xA0),   W(0x4D, 0x9F),   W(0x4E, 0x9E),
    W(0x4F, 0x9D),   W(0x50, 0x9C),   W(0x51, 0x9B),   W(0x52, 0x9A),   W(0x53, 0x99),  //
    R(0x0115, 0x98), W(0x54, 0x98),   W(0x55, 0x96),   W(0x56, 0x95),   R(0x0117, 0x94),
};

#undef R
#undef W

static constexpr size_t BOOT_LEN = sizeof(BOOT_ITEMS) / sizeof(BOOT_ITEMS[0]);
static constexpr size_t CYCLE_LEN = sizeof(CYCLE) / sizeof(CYCLE[0]);

struct PersistedState {
  uint8_t fan_step;
  uint8_t setpoint_raw;
  uint8_t preheat;
};

struct PersistedFanSpeeds {
  uint8_t percent[FAN_SPEED_COUNT];
};

uint8_t GenvexPanel::setpoint_to_raw(float celsius) {
  return static_cast<uint8_t>(clamp(lroundf((celsius - 10.0f) * 10.0f), 0L, 255L));
}

void GenvexPanel::setup() {
  this->pref_ = global_preferences->make_preference<PersistedState>(fnv1_hash("genvex_panel_state"));
  PersistedState state{};
  if (this->pref_.load(&state) && state.fan_step <= FAN_STEP3) {
    this->fan_mode_ = static_cast<FanMode>(state.fan_step);
    this->setpoint_raw_ = state.setpoint_raw;
    this->preheat_ = state.preheat != 0;
  }
  this->before_boost_ = this->fan_mode_;
  this->load_fan_speeds_();
  this->publish_controls_();
#ifdef USE_BINARY_SENSOR
  if (this->link_ != nullptr)
    this->link_->publish_state(false);
#endif
  this->high_freq_.start();
  this->phase_start_ = millis();
}

void GenvexPanel::dump_config() {
  ESP_LOGCONFIG(TAG,
                "Genvex panel link:\n"
                "  Boot delay: %" PRIu32 " ms\n"
                "  Boost duration: %" PRIu32 " s\n"
                "  Fan step: %u, setpoint raw: 0x%02X, preheat: %s\n"
                "  Fan speeds: supply %u/%u/%u %%, extract %u/%u/%u %%",
                this->boot_delay_, this->boost_duration_ / 1000, this->fan_mode_, this->setpoint_raw_,
                YESNO(this->preheat_), this->values_[0x13], this->values_[0x14], this->values_[0x15],
                this->values_[0x16], this->values_[0x17], this->values_[0x18]);
}

uint8_t GenvexPanel::value_for_(uint8_t addr) const {
  const bool boost = this->fan_mode_ == FAN_BOOST;
  switch (addr) {
    case ADDR_SETPOINT:
      return this->setpoint_raw_;
    case ADDR_FAN_STEP_A:
    case ADDR_FAN_STEP_B:
      if (this->fan_mode_ == FAN_OFF)
        return FAN_STEP_OFF;
      return boost ? FAN_STEP3 : this->fan_mode_;
    case ADDR_SUPPLY_STEP3:
    case ADDR_EXTRACT_STEP3:
      return boost ? 100 : this->values_[addr];
    case ADDR_PREHEAT:
      return this->preheat_ ? 1 : 0;
    case ADDR_ROOM_TEMP: {
      float celsius = this->room_fallback_;
#ifdef USE_SENSOR
      if (this->room_sensor_ != nullptr && this->room_sensor_->has_state() &&
          !std::isnan(this->room_sensor_->get_state()))
        celsius = this->room_sensor_->get_state();
#endif
      return static_cast<uint8_t>(clamp(lroundf(this->room_offset_ - celsius * 10.0f), 0L, 255L));
    }
    default:
      return this->values_[addr];
  }
}

void GenvexPanel::send_(uint8_t a, uint8_t b) {
  // discard anything unexpected before a new request
  uint8_t junk;
  while (this->available() > 0)
    this->read_byte(&junk);
  const uint8_t frame[2] = {a, b};
  this->write_array(frame, 2);
}

uint8_t GenvexPanel::receive_(uint8_t *buf) {
  uint8_t n = 0;
  while (this->available() > 0) {
    uint8_t byte;
    this->read_byte(&byte);
    if (n < 2)
      buf[n] = byte;
    n++;
  }
  return n;
}

void GenvexPanel::loop() {
  const uint32_t now = millis();

  // boost ends after the configured duration, like the panel's service 17
  if (this->fan_mode_ == FAN_BOOST && now - this->boost_start_ >= this->boost_duration_) {
    ESP_LOGI(TAG, "Boost finished, back to %s", FAN_MODE_NAMES[this->before_boost_]);
    this->fan_mode_ = this->before_boost_;
    this->publish_controls_();
  }

  if (this->phase_ == Phase::BOOT_PAUSE) {
    if (now - this->phase_start_ < this->boot_delay_)
      return;
    this->phase_ = Phase::CYCLE;
    this->index_ = 0;
    this->step_ = Step::SEND;
    this->item_start_ = now;
  }

  const bool boot = this->phase_ == Phase::BOOT_READS;
  const CycleItem &item = boot ? BOOT_ITEMS[this->index_] : CYCLE[this->index_];

  switch (this->step_) {
    case Step::SEND:
      if (now - this->item_start_ < (item.read ? READ_SPACING_MS : WRITE_SPACING_MS) && this->transactions_ > 0)
        return;
      this->item_start_ = now;
      if (item.read) {
        this->send_(item.a, item.b);
      } else {
        this->sent_value_ = this->value_for_(item.a);
        this->send_(item.a, this->sent_value_);
      }
      this->step_ = Step::SECOND;
      return;

    case Step::SECOND:
      if (now - this->item_start_ < (item.read ? REPEAT_GAP_MS : COMMIT_GAP_MS))
        return;
      this->reply1_len_ = this->receive_(this->reply1_);
      if (item.read) {
        this->send_(item.a, item.b);  // the panel sends every read twice
      } else {
        this->send_(0x02, 0x05);  // "commit", never answered
      }
      this->step_ = Step::EVALUATE;
      return;

    case Step::EVALUATE:
      if (now - this->item_start_ < (item.read ? REPEAT_GAP_MS : COMMIT_GAP_MS) + REPLY_WAIT_MS)
        return;
      this->reply2_len_ = this->receive_(this->reply2_);
      this->evaluate_(item, this->sent_value_);
      this->step_ = Step::SEND;
      this->index_++;
      if (boot && this->index_ >= BOOT_LEN) {
        this->phase_ = Phase::BOOT_PAUSE;
        this->phase_start_ = now;
      } else if (!boot && this->index_ >= CYCLE_LEN) {
        this->index_ = 0;
      }
      return;
  }
}

// While the link is down, individual failures are only logged at verbose level.
#define LOG_FAILURE(...) \
  do { \
    if (this->link_ok_) { \
      ESP_LOGW(TAG, __VA_ARGS__); \
    } else { \
      ESP_LOGV(TAG, __VA_ARGS__); \
    } \
  } while (0)

void GenvexPanel::evaluate_(const CycleItem &item, uint8_t sent_value) {
  this->transactions_++;
  if (this->reply1_len_ != 2) {
    LOG_FAILURE("%02X %02X: no valid reply (%u bytes)", item.a, item.read ? item.b : sent_value,
                this->reply1_len_);
    this->record_result_(false);
    return;
  }
  if (this->reply1_[0] != item.tag) {
    LOG_FAILURE("%02X %02X: unexpected tag %02X (expected %02X)", item.a, item.read ? item.b : sent_value,
                this->reply1_[0], item.tag);
    this->record_result_(false);
    return;
  }
  if (!item.read) {
    const bool ok = this->reply1_[1] == sent_value;
    if (!ok)
      LOG_FAILURE("write %02X %02X: echo %02X", item.a, sent_value, this->reply1_[1]);
    ESP_LOGV(TAG, "W %02X %02X -> %02X %02X", item.a, sent_value, this->reply1_[0], this->reply1_[1]);
    this->record_result_(ok);
    return;
  }
  // reads: both copies must agree before a value is used
  if (this->reply2_len_ != 2 || this->reply2_[0] != this->reply1_[0] || this->reply2_[1] != this->reply1_[1]) {
    LOG_FAILURE("%02X %02X: copies differ", item.a, item.b);
    this->record_result_(false);
    return;
  }
  ESP_LOGV(TAG, "R %02X %02X -> %02X %02X", item.a, item.b, this->reply1_[0], this->reply1_[1]);
  this->record_result_(true);
  this->decode_read_(item.a, item.b, this->reply1_[1]);
}

#undef LOG_FAILURE

void GenvexPanel::record_result_(bool ok) {
  if (ok) {
    this->errors_in_row_ = 0;
  } else {
    this->failures_++;
    if (this->errors_in_row_ < UINT16_MAX)
      this->errors_in_row_++;
  }
  // up after the first good transaction, down after LINK_LOST_AFTER failures in a row
  bool link_ok = this->link_ok_;
  if (ok) {
    link_ok = true;
  } else if (this->errors_in_row_ >= LINK_LOST_AFTER) {
    link_ok = false;
  }
  const bool first_loss = !link_ok && this->errors_in_row_ == LINK_LOST_AFTER && !this->link_reported_;
  if (link_ok == this->link_ok_ && !first_loss)
    return;
  this->link_ok_ = link_ok;
  this->link_reported_ = true;
  if (link_ok) {
    ESP_LOGI(TAG, "Link to the main board OK");
  } else {
    ESP_LOGE(TAG, "Link to the main board lost (%u failed transactions in a row)", this->errors_in_row_);
  }
#ifdef USE_BINARY_SENSOR
  if (this->link_ != nullptr)
    this->link_->publish_state(link_ok);
#endif
}

void GenvexPanel::decode_read_(uint8_t a, uint8_t b, uint8_t value) {
  if (a == 0x01 && b >= 0x01 && b <= 0x10) {
    // temperatures: big-endian 16-bit words, high byte at odd register
    if (b % 2 == 1) {
      this->temp_hi_[b] = value;
      return;
    }
#ifdef USE_SENSOR
    const uint16_t raw = (static_cast<uint16_t>(this->temp_hi_[b - 1]) << 8) | value;
    const uint8_t word = b / 2;
    const uint16_t bit = 1U << word;
    if ((this->temp_valid_ & bit) && raw != this->temp_pending_[word] &&
        std::abs(static_cast<int>(raw) - static_cast<int>(this->temp_raw_[word])) > TEMP_MAX_JUMP) {
      ESP_LOGD(TAG, "temperature %02X/%02X: %u -> %u, waiting for confirmation", b - 1, b,
               static_cast<unsigned>(this->temp_raw_[word]), static_cast<unsigned>(raw));
      this->temp_pending_[word] = raw;
      return;
    }
    this->temp_raw_[word] = raw;
    this->temp_pending_[word] = raw;
    this->temp_valid_ |= bit;
    const float celsius = (static_cast<float>(raw) - 300.0f) / 10.0f;
    sensor::Sensor *target = nullptr;
    switch (b) {
      case 0x02:
        target = this->supply_temperature_;
        break;
      case 0x04:
        target = this->outdoor_temperature_;
        break;
      case 0x06:
        target = this->exhaust_temperature_;
        break;
      case 0x0C:
        target = this->extract_temperature_;
        break;
      default:
        break;
    }
    if (target != nullptr)
      target->publish_state(celsius);
#endif
    return;
  }
#ifdef USE_SENSOR
  if (a == 0x01 && b == 0x13 && this->supply_fan_ != nullptr)
    this->supply_fan_->publish_state(value);
  if (a == 0x01 && b == 0x14 && this->extract_fan_ != nullptr)
    this->extract_fan_->publish_state(value);
  if (a == 0x02 && b == 0x03 && this->bypass_damper_ != nullptr)
    this->bypass_damper_->publish_state(roundf(value * 1000.0f / 255.0f) / 10.0f);
#endif
#ifdef USE_BINARY_SENSOR
  if (a == 0x02 && b == 0x01 && this->running_ != nullptr)
    this->running_->publish_state((value & 0x10) != 0);
  if (a == 0x02 && b == 0x04 && this->bypass_ != nullptr)
    this->bypass_->publish_state((value & 0x02) != 0);
#endif
  // status and not yet decoded registers: log every change
  if (b < 0x18) {
    const uint8_t bank = a - 1;
    const uint32_t bit = 1UL << b;
    if (!(this->status_seen_[bank] & bit)) {
      ESP_LOGD(TAG, "register %02X %02X = %02X", a, b, value);
    } else if (this->status_last_[bank][b] != value) {
      ESP_LOGD(TAG, "register %02X %02X: %02X -> %02X", a, b, this->status_last_[bank][b], value);
    }
    this->status_last_[bank][b] = value;
    this->status_seen_[bank] |= bit;
  }
}

void GenvexPanel::set_fan_mode(FanMode mode) {
  if (mode == FAN_BOOST) {
    if (this->fan_mode_ != FAN_BOOST)
      this->before_boost_ = this->fan_mode_;
    this->boost_start_ = millis();
  }
  this->fan_mode_ = mode;
  ESP_LOGI(TAG, "Fan mode -> %s", FAN_MODE_NAMES[mode]);
  this->save_();
  this->publish_controls_();
}

void GenvexPanel::set_setpoint(float celsius) {
  this->setpoint_raw_ = setpoint_to_raw(celsius);
  ESP_LOGI(TAG, "Setpoint -> %.1f °C", celsius);
  this->save_();
  this->publish_controls_();
}

void GenvexPanel::set_preheat(bool on) {
  this->preheat_ = on;
  ESP_LOGI(TAG, "Preheater -> %s", ONOFF(on));
  this->save_();
  this->publish_controls_();
}

void GenvexPanel::set_fan_speed(uint8_t index, uint8_t percent) {
  if (index >= FAN_SPEED_COUNT)
    return;
  this->values_[ADDR_FAN_SPEED + index] = percent;
  ESP_LOGI(TAG, "%s fan step %u -> %u %%", index < 3 ? "Supply" : "Extract", index % 3 + 1, percent);
  PersistedFanSpeeds speeds;
  for (uint8_t i = 0; i < FAN_SPEED_COUNT; i++)
    speeds.percent[i] = this->values_[ADDR_FAN_SPEED + i];
  this->fan_pref_.save(&speeds);
  this->publish_controls_();
}

void GenvexPanel::load_fan_speeds_() {
#ifdef USE_NUMBER
  bool adjustable = false;
  for (auto *n : this->fan_speed_numbers_)
    adjustable |= n != nullptr;
  if (!adjustable)
    return;  // without the entities the YAML values always apply
  // The key includes the YAML values: changing fan_speeds in the YAML discards values set from HA.
  uint32_t key = fnv1_hash("genvex_panel_fan_speeds");
  for (uint8_t i = 0; i < FAN_SPEED_COUNT; i++)
    key = (key ^ this->values_[ADDR_FAN_SPEED + i]) * 16777619UL;
  this->fan_pref_ = global_preferences->make_preference<PersistedFanSpeeds>(key);
  PersistedFanSpeeds speeds{};
  if (this->fan_pref_.load(&speeds)) {
    for (uint8_t i = 0; i < FAN_SPEED_COUNT; i++)
      this->values_[ADDR_FAN_SPEED + i] = std::min<uint8_t>(speeds.percent[i], 100);
  }
#endif
}

void GenvexPanel::save_() {
  // boost is never persisted: after a reboot the unit returns to the normal step
  PersistedState state{static_cast<uint8_t>(this->fan_mode_ == FAN_BOOST ? this->before_boost_ : this->fan_mode_),
                       this->setpoint_raw_, static_cast<uint8_t>(this->preheat_ ? 1 : 0)};
  this->pref_.save(&state);
}

void GenvexPanel::publish_controls_() {
#ifdef USE_FAN
  if (this->fan_ != nullptr)
    this->fan_->publish_mode(this->fan_mode_);
#endif
#ifdef USE_NUMBER
  if (this->setpoint_number_ != nullptr)
    this->setpoint_number_->publish_state(10.0f + this->setpoint_raw_ / 10.0f);
  for (uint8_t i = 0; i < FAN_SPEED_COUNT; i++) {
    if (this->fan_speed_numbers_[i] != nullptr)
      this->fan_speed_numbers_[i]->publish_state(this->values_[ADDR_FAN_SPEED + i]);
  }
#endif
#ifdef USE_SWITCH
  if (this->preheat_switch_ != nullptr)
    this->preheat_switch_->publish_state(this->preheat_);
#endif
}

}  // namespace esphome::genvex_panel
