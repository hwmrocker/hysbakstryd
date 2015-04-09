from .plugin import Plugin, logger




class ServerObserverPlugin(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger.getChild("ServerObserverPlugin")

    def take(self, client, event_name, *args, **kwargs):
        self.logger.debug("EVENT: {}: {}".format(client.name, event_name))
    

