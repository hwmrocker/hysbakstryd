from ._plugin_base import Plugin, logger


class ServerObserverPlugin(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger.getChild("ServerObserverPlugin")

    def take(self, client, event_name, *args, **kwargs):
        if client is None:
            self.logger.debug("EVENT: {}".format(event_name))
        else:
            self.logger.debug("EVENT: {}: {}".format(client.name, event_name))
