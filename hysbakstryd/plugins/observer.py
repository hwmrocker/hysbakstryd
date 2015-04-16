from ._plugin_base import Plugin


class ObserverPlugin(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_observe(self, client):
        return (), ('observe', 'started'), None
        # return (self.observe, ), ('observe', 'started'), None

    def do_get_state(self, client):
        """Get the state of your own client."""

        return (), ('state', client.vars), None

    def do_get_world_state(self, client):
        """Get the state of every client."""

        state = {c.vars['username']: c.vars for c in self.game.user_to_game_clients.values() if c.observer is False}
        state['__world__'] = self.game.world_state
        return (), ('WORLD_STATE', state), None

    def observe(self, client):
        self.game.user_to_network_client[client.username].inform(
            'game_state', {c.username: c.vars for c in self.game.user_to_game_clients.values()}
        )
