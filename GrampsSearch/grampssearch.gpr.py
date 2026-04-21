from gramps.gen.plug._pluginreg import *
from gramps.gen.const import GRAMPS_LOCALE as glocale

_ = glocale.translation.gettext

MODULE_VERSION = "6.0"

register(
    TOOL,
    id="grampssearch",
    name=_("GrampsSearch"),
    description=_("Find missing genealogical data from Dutch archive APIs and merge into the local database"),
    version="0.1.0",
    gramps_target_version=MODULE_VERSION,
    status=STABLE,
    fname="tool.py",
    authors=["Lieuwe Jongsma"],
    authors_email=["lieuwe89@gmail.com"],
    help_url="https://github.com/lieuwejongsma/grampssearch",
    category=TOOL_UTILS,
    toolclass="GrampsSearchTool",
    optionclass="GrampsSearchOptions",
    tool_modes=[TOOL_MODE_GUI],
)
