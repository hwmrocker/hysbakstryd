from bcrypt import hashpw, gensalt
import gc
__version__ = "0.0.4"


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
            self.user_to_game_clients[username] = GameClient(username, self, _old_client=old_game_client)

        old_game.user_to_game_clients = {}
        print(gc.collect())

    def inform_all(self, msg_type, data, from_id="__master__"):
        for net_client in self.user_to_network_clients.values():
            net_client.inform(msg_type, data, from_id=from_id)

    def register(self, network_client, username, password, **kw):
        print("register {}".format(username))
        # check or set password
        if username in self.user_to_passwords:
            hashed = self.user_to_passwords[username]
            if hashpw(bytes(password, "utf-8"), hashed) == hashed:
                print("old password correct")
                # yeah
                pass
            else:
                print("old password is different")
                raise WrongPassword()
        else:
            print("new password")
            pass

            self.user_to_passwords[username] = hashpw(bytes(password, "utf-8"), gensalt())

        if username not in self.user_to_game_clients:
            self.user_to_game_clients[username] = GameClient(username, self, **kw)
        else:
            self.user_to_game_clients[username].online = True
            try:
                self.unregister(self.user_to_network_clients[username])
            except:
                print("unregister bei relogin ging nicht")

        self.user_to_network_clients[username] = network_client
        self.network_to_user[network_client] = username
        return self.user_to_game_clients[username]

    def unregister(self, network_client):
        print("bye {}".format(network_client))
        username = self.network_to_user[network_client]
        self.user_to_game_clients[username].online = False
        del self.user_to_network_clients[username]
        del self.network_to_user[network_client]

    def pause(self):
        pass

    def resume(self):
        pass


class GameClient:

    def __init__(self, username, game, observer=False, _old_client=None, **kw):
        self.name = username
        self.game = game
        self.online = True
        self.level = 0
        self.levels = set([])
        self.direction = "halt"
        if _old_client is not None:
            self._init_from_old_client(_old_client)

    def _init_from_old_client(self, old_client):
        print("renew client, {}".format(self.name))
        self.__dict__.update(old_client.__dict__)

    def do_shout(self, **foo):
        # print(self.name, foo)
        return "RESHOUT", foo

    def do_set_level(self, level, **kw):
        assert 0 <= level < 10
        self.levels.add(level)
        # print("{} set level {}, current active levels = {}".format(self.name, level, self.levels))

    def do_reset_level(self, **kw):
        self.levels = set([])

    def do_open_door(self, direction, **kw):
        assert direction in ("up", "down")
        self.direction = direction

    def do_close_door(self, **kw):
        pass

    def do_set_direction(self, direction, **kw):
        assert direction in ("up", "down", "halt")
        self.direction = direction
        print("{} set direction to {}".format(self.name, direction))
