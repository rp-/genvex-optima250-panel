import esphome.codegen as cg
from esphome.components import select
import esphome.config_validation as cv
from esphome.const import ICON_FAN

from .. import CONF_GENVEX_PANEL_ID, GenvexPanel, genvex_ns

FanModeSelect = genvex_ns.class_("FanModeSelect", select.Select)

CONF_FAN_MODE = "fan_mode"
FAN_MODE_OPTIONS = ["Off", "Step 1", "Step 2", "Step 3", "Boost"]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_GENVEX_PANEL_ID): cv.use_id(GenvexPanel),
        cv.Optional(CONF_FAN_MODE): select.select_schema(FanModeSelect, icon=ICON_FAN),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_GENVEX_PANEL_ID])
    if conf := config.get(CONF_FAN_MODE):
        s = await select.new_select(conf, options=FAN_MODE_OPTIONS)
        await cg.register_parented(s, config[CONF_GENVEX_PANEL_ID])
        cg.add(hub.set_fan_mode_select(s))
