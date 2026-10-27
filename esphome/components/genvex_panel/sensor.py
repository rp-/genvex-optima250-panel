import esphome.codegen as cg
from esphome.components import sensor
import esphome.config_validation as cv
from esphome.const import (
    DEVICE_CLASS_TEMPERATURE,
    ICON_FAN,
    STATE_CLASS_MEASUREMENT,
    UNIT_CELSIUS,
    UNIT_PERCENT,
)

from . import CONF_GENVEX_PANEL_ID, GenvexPanel

TEMPERATURES = {
    "supply_temperature": "set_supply_temperature_sensor",  # T1
    "outdoor_temperature": "set_outdoor_temperature_sensor",  # T3
    "exhaust_temperature": "set_exhaust_temperature_sensor",  # T4
    "extract_temperature": "set_extract_temperature_sensor",  # T7
}
PERCENTAGES = {
    "supply_fan": ("set_supply_fan_sensor", ICON_FAN),
    "extract_fan": ("set_extract_fan_sensor", ICON_FAN),
    "bypass_damper": ("set_bypass_damper_sensor", "mdi:valve"),  # modulating damper only
}

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_GENVEX_PANEL_ID): cv.use_id(GenvexPanel),
        **{
            cv.Optional(key): sensor.sensor_schema(
                unit_of_measurement=UNIT_CELSIUS,
                accuracy_decimals=1,
                device_class=DEVICE_CLASS_TEMPERATURE,
                state_class=STATE_CLASS_MEASUREMENT,
            )
            for key in TEMPERATURES
        },
        **{
            cv.Optional(key): sensor.sensor_schema(
                unit_of_measurement=UNIT_PERCENT,
                accuracy_decimals=0,
                icon=icon,
                state_class=STATE_CLASS_MEASUREMENT,
            )
            for key, (_, icon) in PERCENTAGES.items()
        },
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_GENVEX_PANEL_ID])
    for key, setter in TEMPERATURES.items():
        if conf := config.get(key):
            cg.add(getattr(hub, setter)(await sensor.new_sensor(conf)))
    for key, (setter, _) in PERCENTAGES.items():
        if conf := config.get(key):
            cg.add(getattr(hub, setter)(await sensor.new_sensor(conf)))
