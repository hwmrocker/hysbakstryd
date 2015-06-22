from ._plugin_base import Plugin, logger

import config


class ServerObserverPlugin(Plugin):
    """Plugin for showing all events that happen on the server.

    Enable or disable it through the game settings.

    Use these settings:
      observe_events: True/False -- whether to show event logs or not (ie. global enable/disable for this plugin)
      show_args: True/False -- whether to display args/kwargs as well when logging events
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger.getChild("ServerObserverPlugin")

    def take_empty(self, *args, **kwargs):
        return

    def take_without_args(self, client, event_name, *args, **kwargs):
        if client is None:
            self.logger.info("EVENT: {}".format(event_name))
        else:
            self.logger.info("EVENT: {}: {}".format(client.name, event_name))

    def take_with_args(self, client, event_name, *args, **kwargs):
        if client is None:
            self.logger.info("EVENT: {} ({}, {})".format(event_name, args, kwargs))
        else:
            self.logger.info("EVENT: {}: {} ({}, {})".format(client.name, event_name, args, kwargs))

    if config.plugins.server_observer.observe_events:
        if config.plugins.server_observer.with_args:
            logger.info('ServerObserver enabled with args')
            take = take_with_args
        else:
            logger.info('ServerObserver enabled without args')
            take = take_without_args
    else:
        logger.info('ServerObserver disabled')
        take = take_empty
