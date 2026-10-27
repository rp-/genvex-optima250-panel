import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv

from .. import CONF_GENVEX_PANEL_ID, GenvexPanel, genvex_ns

PreheatSwitch = genvex_ns.class_("PreheatSwitch", switch.Switch)

CONF_PREHEAT = "preheat"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_GENVEX_PANEL_ID): cv.use_id(GenvexPanel),
        cv.Optional(CONF_PREHEAT): switch.switch_schema(PreheatSwitch, icon="mdi:radiator"),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_GENVEX_PANEL_ID])
    if conf := config.get(CONF_PREHEAT):
        s = await switch.new_switch(conf)
        await cg.register_parented(s, config[CONF_GENVEX_PANEL_ID])
        cg.add(hub.set_preheat_switch(s))
