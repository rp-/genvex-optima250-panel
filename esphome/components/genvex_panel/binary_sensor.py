import esphome.codegen as cg
from esphome.components import binary_sensor
import esphome.config_validation as cv
from esphome.const import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_OPENING,
    DEVICE_CLASS_RUNNING,
    ENTITY_CATEGORY_DIAGNOSTIC,
)

from . import CONF_GENVEX_PANEL_ID, GenvexPanel

CONF_RUNNING = "running"
CONF_LINK = "link"
CONF_BYPASS = "bypass"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_GENVEX_PANEL_ID): cv.use_id(GenvexPanel),
        cv.Optional(CONF_RUNNING): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_RUNNING,
        ),
        cv.Optional(CONF_LINK): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_CONNECTIVITY,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ),
        cv.Optional(CONF_BYPASS): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_OPENING,
            icon="mdi:valve",
        ),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_GENVEX_PANEL_ID])
    if conf := config.get(CONF_RUNNING):
        cg.add(hub.set_running_binary_sensor(await binary_sensor.new_binary_sensor(conf)))
    if conf := config.get(CONF_LINK):
        cg.add(hub.set_link_binary_sensor(await binary_sensor.new_binary_sensor(conf)))
    if conf := config.get(CONF_BYPASS):
        cg.add(hub.set_bypass_binary_sensor(await binary_sensor.new_binary_sensor(conf)))
