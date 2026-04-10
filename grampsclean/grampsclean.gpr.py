from gramps.gen.plug._pluginreg import *
from gramps.gen.const import GRAMPS_LOCALE as glocale

_ = glocale.translation.gettext

MODULE_VERSION = "6.0"

register(
    TOOL,
    id="grampsclean",
    name=_("GrampsClean"),
    description=_("Data quality audit tools for kinship databases"),
    version="0.2.0",
    gramps_target_version=MODULE_VERSION,
    status=STABLE,
    fname="tool.py",
    authors=["GrampsClean"],
    authors_email=[""],
    category=TOOL_UTILS,
    toolclass="GrampsCleanTool",
    optionclass="GrampsCleanOptions",
    tool_modes=[TOOL_MODE_GUI],
)
