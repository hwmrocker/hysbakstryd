from ._plugin_base import Plugin, logger


class ShoutPlugin(Plugin):

    """A simple plugin that lets each user send messages to all connected clients.

    There is only a single command, `shout`, which accepts any number of keyword
    arguments and echoes all of them to all players.
    """

    def __init__(self):
        self.logger = logger.getChild("ShoutPlugin")

    def do_shout(self, client, **foo):
        """
        Repeat the sent message to all connected clients.
        """
        self.logger.debug("{}: {}".format(client.name, foo))
        return (), None, ("RESHOUT", foo)
