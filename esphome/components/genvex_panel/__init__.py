"""Genvex Optima 250 panel replacement: bus master on the ES960 panel link (21/22)."""

import esphome.codegen as cg
from esphome.components import sensor, uart
import esphome.config_validation as cv
from esphome.const import CONF_ID

CODEOWNERS = []
DEPENDENCIES = ["uart"]
AUTO_LOAD = ["sensor"]

CONF_GENVEX_PANEL_ID = "genvex_panel_id"
CONF_ROOM_TEMPERATURE = "room_temperature"
CONF_ROOM_TEMPERATURE_FALLBACK = "room_temperature_fallback"
CONF_ROOM_TEMPERATURE_OFFSET = "room_temperature_offset"
CONF_BOOT_DELAY = "boot_delay"
CONF_BOOST_DURATION = "boost_duration"
CONF_FAN_SPEEDS = "fan_speeds"
CONF_SUPPLY = "supply"
CONF_EXTRACT = "extract"
CONF_DEFAULTS = "defaults"
CONF_FAN_STEP = "fan_step"
CONF_SETPOINT = "setpoint"
CONF_PREHEAT = "preheat"
CONF_SERVICE = "service"
CONF_T2_ADJUSTMENT = "t2_adjustment"
CONF_PREHEAT_TEMPERATURE = "preheat_temperature"
CONF_BYPASS_MAX = "bypass_max"
CONF_FROST_REDUCTION = "frost_reduction"
CONF_WATER_FROST_TEMPERATURE = "water_frost_temperature"
CONF_BYPASS_MIN_OUTDOOR = "bypass_min_outdoor"
CONF_RAW_WRITES = "raw_writes"

genvex_ns = cg.esphome_ns.namespace("genvex_panel")
GenvexPanel = genvex_ns.class_("GenvexPanel", cg.Component, uart.UARTDevice)

# Write addresses the panel sends and their values on the reference unit (docs/field-map.md).
# Only these addresses can ever be written.
WRITE_DEFAULTS = {
    0x05: 0x69, 0x06: 0xFF, 0x07: 0xFF, 0x08: 0xFF, 0x09: 0xFF, 0x0A: 0xFF, 0x0B: 50,
    0x0C: 0xFF, 0x0D: 0xFF, 0x0E: 0xFF, 0x0F: 0xFF, 0x10: 0, 0x11: 20, 0x12: 0xFF,
    0x13: 45, 0x14: 60, 0x15: 90, 0x16: 45, 0x17: 60, 0x18: 85,
    0x41: 0, 0x42: 1, 0x43: 1, 0x44: 0, 0x45: 0xFF, 0x46: 2, 0x47: 0xB7, 0x48: 0xFF,
    0x49: 1, 0x4A: 100, 0x4B: 0, 0x4C: 50, 0x4D: 20, 0x4E: 20, 0x4F: 3,
    0x50: 0xFF, 0x51: 0xFF, 0x52: 0xFF, 0x53: 4, 0x54: 0xFF, 0x55: 0, 0x56: 0,
}  # fmt: skip

# Addresses the component computes itself; they cannot be overridden in raw_writes.
MANAGED = {0x05, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x42, 0x43, 0x47, 0x49,
           0x0B, 0x11, 0x4A, 0x4C, 0x4D, 0x53}  # fmt: skip


def _percent_list(value):
    value = cv.ensure_list(cv.int_range(min=0, max=100))(value)
    if len(value) != 3:
        raise cv.Invalid("exactly three values (step 1, 2, 3) are required")
    return value


def _raw_writes(value):
    value = cv.Schema({cv.hex_uint8_t: cv.hex_uint8_t})(value)
    for addr in value:
        if addr not in WRITE_DEFAULTS:
            raise cv.Invalid(f"0x{addr:02X} is not an address the panel writes")
        if addr in MANAGED:
            raise cv.Invalid(f"0x{addr:02X} is set through a named option, not raw_writes")
    return value


def _celsius(lo, hi):
    return cv.All(cv.float_, cv.Range(min=lo, max=hi))


FAN_SPEEDS_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_SUPPLY): _percent_list,
        cv.Required(CONF_EXTRACT): _percent_list,
    }
)

SERVICE_SCHEMA = cv.Schema(
    {
        # values of the reference unit; check your panel's service menu
        # service 16: the panel's −3.0 compensates its self-heating; 0.0 for an external sensor
        cv.Optional(CONF_T2_ADJUSTMENT, default=0.0): _celsius(-5.0, 5.0),  # service 16
        cv.Optional(CONF_PREHEAT_TEMPERATURE, default=-5.0): _celsius(-15.0, 0.0),  # 20
        cv.Optional(CONF_BYPASS_MAX, default=2.0): _celsius(0.0, 10.0),  # 21
        cv.Optional(CONF_FROST_REDUCTION, default=5.0): _celsius(0.0, 15.0),  # 24
        cv.Optional(CONF_WATER_FROST_TEMPERATURE, default=5.0): _celsius(0.0, 15.0),  # 26
        cv.Optional(CONF_BYPASS_MIN_OUTDOOR, default=4): cv.int_range(min=0, max=25),  # 29
    }
)

DEFAULTS_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_FAN_STEP, default=1): cv.int_range(min=1, max=3),
        cv.Optional(CONF_SETPOINT, default=20.5): _celsius(15.0, 30.0),
        cv.Optional(CONF_PREHEAT, default=True): cv.boolean,
    }
)

CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(GenvexPanel),
            cv.Required(CONF_FAN_SPEEDS): FAN_SPEEDS_SCHEMA,
            cv.Optional(CONF_SERVICE, default={}): SERVICE_SCHEMA,
            cv.Optional(CONF_DEFAULTS, default={}): DEFAULTS_SCHEMA,
            cv.Optional(CONF_ROOM_TEMPERATURE): cv.use_id(sensor.Sensor),
            cv.Optional(CONF_ROOM_TEMPERATURE_FALLBACK, default=21.0): _celsius(5.0, 35.0),
            cv.Optional(CONF_ROOM_TEMPERATURE_OFFSET, default=443.0): cv.float_,
            cv.Optional(CONF_BOOT_DELAY, default="2s"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_BOOST_DURATION, default="60min"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_RAW_WRITES, default={}): _raw_writes,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(uart.UART_DEVICE_SCHEMA)
)

FINAL_VALIDATE_SCHEMA = uart.final_validate_device_schema(
    "genvex_panel",
    baud_rate=19200,
    require_tx=True,
    require_rx=True,
    data_bits=8,
    parity="NONE",
    stop_bits=1,
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)

    values = dict(WRITE_DEFAULTS)
    supply = config[CONF_FAN_SPEEDS][CONF_SUPPLY]
    extract = config[CONF_FAN_SPEEDS][CONF_EXTRACT]
    values.update({0x13: supply[0], 0x14: supply[1], 0x15: supply[2]})
    values.update({0x16: extract[0], 0x17: extract[1], 0x18: extract[2]})
    service = config[CONF_SERVICE]
    values[0x4D] = round(service[CONF_T2_ADJUSTMENT] * 10 + 50)
    values[0x4A] = round(service[CONF_PREHEAT_TEMPERATURE] * 10 + 150)
    values[0x11] = round(service[CONF_BYPASS_MAX] * 10)
    values[0x0B] = round(service[CONF_FROST_REDUCTION] * 10)
    values[0x4C] = round(service[CONF_WATER_FROST_TEMPERATURE] * 10)
    values[0x53] = service[CONF_BYPASS_MIN_OUTDOOR]
    values.update(config[CONF_RAW_WRITES])
    for addr, val in sorted(values.items()):
        cg.add(var.set_write_value(addr, val))

    defaults = config[CONF_DEFAULTS]
    cg.add(var.set_default_fan_step(defaults[CONF_FAN_STEP]))
    cg.add(var.set_default_setpoint(defaults[CONF_SETPOINT]))
    cg.add(var.set_default_preheat(defaults[CONF_PREHEAT]))

    if CONF_ROOM_TEMPERATURE in config:
        cg.add(var.set_room_sensor(await cg.get_variable(config[CONF_ROOM_TEMPERATURE])))
    cg.add(var.set_room_fallback(config[CONF_ROOM_TEMPERATURE_FALLBACK]))
    cg.add(var.set_room_offset(config[CONF_ROOM_TEMPERATURE_OFFSET]))
    cg.add(var.set_boot_delay(config[CONF_BOOT_DELAY]))
    cg.add(var.set_boost_duration(config[CONF_BOOST_DURATION]))
