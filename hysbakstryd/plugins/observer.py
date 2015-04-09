
from .plugin import Plugin


class ObserverPlugin(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_observe(self, client):
        return (self.observe, ), ('observe', 'started'), None

    def do_get_state(self, client):
        """Get the state of your own client."""

        return (), ('state', client.vars), None

    def do_get_world_state(self, client):
        """Get the state of every client."""

        state = {c.vars['username']: c.vars for c in self.game.user_to_game_clients.values()}
        return (), ('state', state), None

    def observe(self, client):
        self.game.username_to_network_client[client.username].inform(
            'game_state', {c.username: c.vars for c in self.game.user_to_game_clients.values()}
        )

