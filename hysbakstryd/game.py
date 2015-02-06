import asyncio
import msgpack
import traceback

from bcrypt import hashpw, gensalt


class WrongPassword(Exception):
    pass


class Game:

    def __init__(self):
        self.user_to_passwords = {}
        self.user_to_network_clients = {}
        self.network_to_game_clients = {}

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

        self.user_to_network_clients[username] = network_client
        self.network_to_game_clients[network_client] = GameClient(username, **kw)
        return self.network_to_game_clients[network_client]

    def unregister(self, network_client):
        del self.network_to_game_clients[network_client]


class GameClient:

    def __init__(self, username, observer=False, **kw):
        self.name = username
