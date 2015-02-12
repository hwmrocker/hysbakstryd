from bcrypt import hashpw, gensalt

__version__ = "0.0.2"


class WrongPassword(Exception):
    pass


class Game:

    def __init__(self, _old_game=None):
        self.user_to_passwords = {}
        self.user_to_game_clients = {}
        self.user_to_network_clients = {}
        self.network_to_user = {}
        self.version = __version__

        if _old_game is not None:
            self._init_from_old_game(_old_game)

    def _init_from_old_game(self, old_game):
        print("init from old game v{} to New v{}".format(old_game.version, self.version))
        self.user_to_passwords = old_game.user_to_passwords
        self.user_to_network_clients = old_game.user_to_network_clients
        self.network_to_user = old_game.network_to_user

        for username, old_game_client in old_game.user_to_game_clients.items():
            self.user_to_game_clients[username] = GameClient(username, _old_client=old_game_client)

    def inform_all(self, msg_type, data, from_id="__master__"):
        for net_client in self.user_to_network_clients.items():
            net_client.inform(msg_type, from_id, data)

    def register(self, network_client, username, password, **kw):
        print("register {}".format(username))
        # check or set password
        if username in self.user_to_passwords:
            hashed = self.user_to_passwords[username]
            if hashpw(bytes(password, "utf-8"), hashed) == hashed:
                print("old password correct")
                # yeah
            else:
                print("old password is different")
                raise WrongPassword()
        else:
            print("new password")

            self.user_to_passwords[username] = hashpw(bytes(password, "utf-8"), gensalt())

        if username not in self.user_to_game_clients:
            self.user_to_game_clients[username] = GameClient(username, **kw)

        self.user_to_network_clients[username] = network_client
        self.network_to_user[network_client] = username
        return self.user_to_game_clients[username]

    def unregister(self, network_client):
        username = self.network_to_user[network_client]
        self.user_to_game_clients[username].online = False
        del self.user_to_network_clients[username]
        del self.network_to_user[network_client]

    def pause(self):
        pass

    def resume(self):
        pass


class GameClient:

    def __init__(self, username, observer=False, _old_client=None, **kw):
        self.name = username
        self.online = True

        if _old_client is not None:
            self._init_from_old_client

    def _init_from_old_client(self, old_client):
        self.name = old_client.name
        self.online = old_client.online

    def do_shout(self, **foo):
        print(foo)
        return "RESHOUT", foo
