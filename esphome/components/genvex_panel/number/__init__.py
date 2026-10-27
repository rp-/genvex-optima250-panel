import esphome.codegen as cg
from esphome.components import number
import esphome.config_validation as cv
from esphome.const import (
    CONF_DISABLED_BY_DEFAULT,
    DEVICE_CLASS_TEMPERATURE,
    ENTITY_CATEGORY_CONFIG,
    UNIT_CELSIUS,
    UNIT_PERCENT,
)

from .. import CONF_GENVEX_PANEL_ID, GenvexPanel, genvex_ns

SetpointNumber = genvex_ns.class_("SetpointNumber", number.Number)
FanSpeedNumber = genvex_ns.class_("FanSpeedNumber", number.Number)

CONF_SETPOINT = "setpoint"
# service 10–15, in the order of writes 0x13–0x18
FAN_SPEEDS = [
    "supply_step1",
    "supply_step2",
    "supply_step3",
    "extract_step1",
    "extract_step2",
    "extract_step3",
]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_GENVEX_PANEL_ID): cv.use_id(GenvexPanel),
        cv.Optional(CONF_SETPOINT): number.number_schema(
            SetpointNumber,
            unit_of_measurement=UNIT_CELSIUS,
            device_class=DEVICE_CLASS_TEMPERATURE,
            icon="mdi:thermometer",
        ),
        **{
            # commissioning values (air balance): hidden in Home Assistant until enabled
            cv.Optional(key): number.number_schema(
                FanSpeedNumber,
                unit_of_measurement=UNIT_PERCENT,
                entity_category=ENTITY_CATEGORY_CONFIG,
                icon="mdi:fan",
            ).extend({cv.Optional(CONF_DISABLED_BY_DEFAULT, default=True): cv.boolean})
            for key in FAN_SPEEDS
        },
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_GENVEX_PANEL_ID])
    if conf := config.get(CONF_SETPOINT):
        n = await number.new_number(conf, min_value=15.0, max_value=30.0, step=0.5)
        await cg.register_parented(n, config[CONF_GENVEX_PANEL_ID])
        cg.add(hub.set_setpoint_number(n))
    for index, key in enumerate(FAN_SPEEDS):
        if conf := config.get(key):
            n = await number.new_number(conf, min_value=0, max_value=100, step=1)
            await cg.register_parented(n, config[CONF_GENVEX_PANEL_ID])
            cg.add(n.set_index(index))
            cg.add(hub.set_fan_speed_number(index, n))
