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
    do_observe.allow_inactive = True

    def do_observe_stop(self, client):
        """Stop observing the game."""
        client.continue_observing = False

        return (), ('observe', 'stopping'), None
    do_observe_stop.allow_inactive = True

    def do_get_state(self, client):
        """Get the state of your own client."""

        return (), ('state', client.vars), None

    def do_get_world_state(self, client):
        """Get the state of every client."""

        state = {c.vars['username']: c.vars for c in self.game.active_clients}
        state['__world__'] = self.game.world_state
        return (), ('WORLD_STATE', state), None
    do_get_world_state.allow_inactive = True

    def observe(self, client):
        if self.game.time % client.observation_interval == 0:
            game_state = {c.vars['username']: c.vars for c in self.game.active_clients}
            game_state['__world__'] = self.game.world_state
            self.game.user_to_network_clients[client.name].inform(
                'game_state', game_state
            )

        return client.continue_observing
