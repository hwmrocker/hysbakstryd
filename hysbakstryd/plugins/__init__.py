"""All game plugins that are available for the hysbakstryd game."""


import os
import importlib

from ._plugin_base import Plugin, logger

plugins = []

# we do not want to have the base plugin in our plugin list
__plugin_set = {Plugin}

# iterate over all files in the same directory
for file_ in os.listdir(os.path.dirname(os.path.abspath(__file__))):
    filename, fileext = os.path.splitext(file_)
    # we ignore files that doesn't contain plugins itself
    if not filename.startswith('_') and fileext.lower() == ".py":
        try:
            newmod = importlib.import_module(__loader__.name + "." + filename)

            # get all possible plugin names
            for plugin_name in [n for n in dir(newmod) if not n.startswith('_') and n[0].isupper() and not n.isupper()]:
                klass = getattr(newmod, plugin_name)
                if type(klass) == type and issubclass(klass, Plugin) and klass not in __plugin_set:
                    logger.info("load {}".format(plugin_name))
                    __plugin_set.add(klass)
                    plugins.append(klass)
        except ImportError:
            logger.error("could not import {}".format(filename))
