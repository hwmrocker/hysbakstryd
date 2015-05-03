from ._plugin_base import Plugin


class ObserverPlugin(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_observe(self, client, interval=1):
        """Start observing the game. You will be given the state of everything all the time.

        ALL! THE! TIME!
        Set the `interval` parameter to only receive state messages every n ticks.
        Stop observing with a `observe_stop` command.
        """
        # return (), ('observe', 'started'), None
        client.continue_observing = True
        client.observation_interval = interval
        return (self.observe, ), ('observe', 'started'), None

    def do_observe_stop(self, client):
        """Stop observing the game."""
        client.continue_observing = False

        return (), ('observe', 'stopping'), None

    def do_get_state(self, client):
        """Get the state of your own client."""

        return (), ('state', client.vars), None

    def do_get_world_state(self, client):
        """Get the state of every client."""

        state = {c.vars['username']: c.vars for c in self.game.user_to_game_clients.values() if c.observer is False}
        state['__world__'] = self.game.world_state
        return (), ('WORLD_STATE', state), None

    def observe(self, client):
        if self.game.time % client.observation_interval == 0:
            self.game.user_to_network_clients[client.vars['username']].inform(
                'game_state', {c.vars['username']: c.vars for c in self.game.user_to_game_clients.values()}
            )

        return client.continue_observing
