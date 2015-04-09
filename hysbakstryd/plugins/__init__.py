"""All game plugins that are available for the hysbakstryd game."""


import os
import importlib

from .plugin import Plugin

plugins = []
__plugin_set = set()

for file_ in os.listdir(os.path.dirname(os.path.abspath(__file__))):
    fileext = os.path.splitext(file_)[1].replace(".","").lower()
    filename = os.path.splitext(file_)[0]
    if not filename.startswith('__') and fileext == "py":
        newmod = importlib.import_module(__loader__.name + "." + filename)
        for content in [n for n in dir(newmod) if not n.startswith('__')]:
            c = getattr(newmod, content)
            if type(c) == type and issubclass(c, Plugin) and c not in __plugin_set:
                __plugin_set.add(c)
                plugins.append(c)
