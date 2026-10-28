import esphome.codegen as cg
from esphome.components import fan
import esphome.config_validation as cv
from esphome.const import ICON_FAN

from .. import CONF_GENVEX_PANEL_ID, GenvexPanel, genvex_ns

GenvexFan = genvex_ns.class_("GenvexFan", fan.Fan)

CONF_VENTILATION = "ventilation"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_GENVEX_PANEL_ID): cv.use_id(GenvexPanel),
        # the hub keeps the fan mode in flash itself
        cv.Optional(CONF_VENTILATION): fan.fan_schema(
            GenvexFan, icon=ICON_FAN, default_restore_mode="NO_RESTORE"
        ),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_GENVEX_PANEL_ID])
    if conf := config.get(CONF_VENTILATION):
        f = await fan.new_fan(conf)
        await cg.register_parented(f, config[CONF_GENVEX_PANEL_ID])
        cg.add(hub.set_fan(f))
