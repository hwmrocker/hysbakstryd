

import logging
logger = logging.getLogger("game")


class Plugin:
    """
    Plugin base class, derive from this to create new plugins for hysbakstryd.

    All methods whose name start with do_ will be registered as client commands that can
    be sent data. Each command should return a set of methods to be added to the client
    state. Each state method will be called in each tick until it returns a non-True
    value, at
    which point it will be removed from the client's states.

    Additionally, the Plugin `tick` method will be called each tick with a set of all
    clients and can perform time-based or global processing at that point.

    # TODO: more documentation and show examples
    """

    def connect(self, client):
        """
        makes a connection or whatever
        

        """
        
        pass

    def emit(self, client, event_name, *args, **kwargs):
        """
        Call this method when you want to emit an event (to all other plugins).
        """
        self.game.emit(client, event_name, *args, **kwargs)

        # TODO: implement

    def take(self, client, event_name, *args, **kwargs):
        """
        This function is called when some plugin emits an event. It tries to look up the function
        with the name `'at_' + event_name` and calls it if present.
        """
        # events
        event_f = getattr(self, "at_" + event_name, None)
        if event_f:
            event_f(client, *args, **kwargs)

    def initialize(self, game):
        """
        Called once when the game starts or the game reinitializes.

        Overwrite this with your own implementation to do stuff at game start/reload,but
        don't forget to call super.
        """
        self.game = game

    def tick(self, time, clients):
        """
        Called every game tick with all currently registered clients.

        Return a set of states that will be added to the client states. Each client state
        is a function on the plugin that will be called each tick.
        """
        pass

    
