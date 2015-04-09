import logging
import traceback

from bcrypt import hashpw, gensalt
from collections import defaultdict
# import gc

__version__ = "0.0.5"
logger = logging.getLogger("game")


class WrongPassword(Exception):
    pass


# duration of one game tick
TICK_TIME = 0.1  # seconds


class Game:

    def __init__(self, _old_game=None):
        logger.info("New game instanciated")
        self.user_to_passwords = {}
        self.game_clients = set()
        self.user_to_game_clients = {}
        self.user_to_network_clients = {}
        self.network_to_user = {}
        self.future_events = defaultdict(list)
        self.time = 0
        self._pause = False
        self.version = __version__

        # as soon as the call order is important, we need to change self.plugins to a list
        self.plugins = set()
        self.command_map = {}

        self.register_plugins()

        if _old_game is not None:
            self._init_from_old_game(_old_game)

    def _init_from_old_game(self, old_game):
        logger.info("init from old game v{} to New v{}".format(old_game.version, self.version))
        old_game_dict = old_game.__dict__
        old_user_to_game_clients = old_game_dict.pop("user_to_game_clients")
        for username, old_game_client in old_user_to_game_clients.items():
            self.user_to_game_clients[username] = GameClient(username, self, _old_client=old_game_client)

        old_game.user_to_game_clients = {}

        # self.__dict__.update is not ok, because we might want to delete some keys
        for key in self.__dict__.keys():
            if key in old_game_dict:
                self.__dict__[key] = old_game_dict[key]

    def inform_all(self, msg_type, data, from_id="__master__", clients=None):
        if clients is None:
            clients = self.user_to_network_clients.values()
        for net_client in clients:
            net_client.inform(msg_type, data, from_id=from_id)

    def register(self, network_client, username, password, **kw):
        logger.info("register {}".format(username))
        # check or set password
        if username in self.user_to_passwords:
            hashed = self.user_to_passwords[username]
            if hashpw(bytes(password, "utf-8"), hashed) == hashed:
                logger.info("old password correct")
                # yeah
                pass
            else:
                logger.warning("old password is different")
                raise WrongPassword()
        else:
            logger.info("new password")
            pass

            self.user_to_passwords[username] = hashpw(bytes(password, "utf-8"), gensalt())

        if username not in self.user_to_game_clients:
            self.user_to_game_clients[username] = GameClient(username, self, **kw)
        else:
            self.user_to_game_clients[username].online = True
            try:
                self.unregister(self.user_to_network_clients[username])
                # TODO: WHY?!?
            except:
                logger.info("unregister bei relogin ging nicht")

        self.game_clients.add(self.user_to_game_clients[username])
        self.user_to_network_clients[username] = network_client
        self.network_to_user[network_client] = username

        for p in self.plugins:
            p.connect(self.user_to_game_clients[username])

        self.inform_all("WELCOME", username)

        return self.user_to_game_clients[username]

    def unregister(self, network_client):
        logger.info("bye {}".format(network_client))
        username = self.network_to_user[network_client]
        self.user_to_game_clients[username].online = False
        self.game_clients.remove(self.user_to_game_clients[username])
        del self.user_to_network_clients[username]
        del self.network_to_user[network_client]

    def pause(self):
        self._pause = True

    def resume(self):
        logger.info('resuming')
        self._pause = False

    def register_plugins(self):
        from .plugins import plugins

        for p in plugins:
            self.register_plugin(p())

    def register_plugin(self, plugin):
        # register commands
        for command_method_name in [m for m in dir(plugin) if m.startswith('do_') and callable(getattr(plugin, m))]:
            self.command_map[command_method_name[3:]] = getattr(plugin, command_method_name)

        self.plugins.add(plugin)
        plugin.initialize(self)

    def emit(self, client, event_name, *args, **kwargs):
        for plugin in self.plugins:
            try:
                plugin.take(client, event_name, *args, **kwargs)
            except Exception:
                logger.error("Plugin {} fucked up take".format(plugin.__class__.__name__))
                logger.error(traceback.format_exc())

    def handle(self, client, msg_type, msg_data):
        if msg_type not in self.command_map:
            logger.error("command not found: {} (from {})".format(
                msg_type, client.name
            ))
            print(msg_type, self.command_map.keys())
            self.user_to_network_clients[client.vars['username']].inform(
                'command_not_found',
                {'msg': 'HE! Du Sackgesicht! Es gibt den Befehl "{}" nicht!'.format(msg_type)}
            )
            raise AttributeError

        ret = self.command_map[msg_type](client, **msg_data)

        if ret:
            try:
                add_states, direct, broadcast = ret

                for new_state in add_states:
                    client.states.add(new_state)

                if direct:
                    self.user_to_network_clients[client.name].inform(*direct)

                if broadcast:
                    b_msg_type, b_rest = broadcast
                    logger.debug("send: {} {}".format(b_msg_type, b_rest))
                    self.inform_all(*broadcast, from_id=client.name)

            except ValueError:
                logger.warning('command {}({}) did not return correct format: {}'.format(
                    msg_type, repr(msg_data),
                    repr(ret),
                ))
                logger.info("it should return (add_states, direct, broadcast)")

    def tick(self):
        if self._pause:
            return

        self.time += 1

        for c in self.game_clients:
            # unfortunatelly we need to try-except every sate
            # if one plugin fail, other should still be executed
            new_states = set()
            for state_f in c.states:
                try:
                    ret = state_f(c)
                    if ret is True:
                        new_states.add(state_f)
                    elif callable(ret):
                        new_states.add(ret)
                    elif ret:
                        for new_state in ret:
                            if callable(new_state):
                                new_states.add(new_state)
                            else:
                                logger.warning("new_state {} is not callable".format(new_state))
                except Exception:
                    logger.error("State {} raised an exception".format(state_f.__name__))
                    logger.error(traceback.format_exc())
            c.states = new_states

        for p in self.plugins:
            try:
                p.tick(self.time, self.game_clients)
            except Exception:
                logger.info("Plugin {} tick failed ".format(p.__class__.__name__))
                logger.error(traceback.format_exc())


from .plugins.plugin import Plugin
from .plugins.movement import MovementPhase1
    


class GameClient:

    def __init__(self, username, game, observer=False, _old_client=None, **kw):
        self.name = username
        self.game = game
        self.online = True

        self.vars = {'username': username}

        self.states = set()
        self.level = 0
        self.levels = set()
        self.direction = "halt"
        self.door = "closed"

        self._stopped_at = None

        # We want a new log file for each client
        self.logger = logger.getChild("GameClient({})".format(self.name))
        if not self.logger.handlers:
            # we just want to add the unique filehandler if it is not present yet
            fh = logging.FileHandler(filename="logs/GameClient_{}.log".format(self.name))
            fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(fh)
        self.logger.info("hello client, {}".format(self.name))

        if _old_client is not None:
            self._init_from_old_client(_old_client)

    def _init_from_old_client(self, old_client):
        self.logger.info("renew client, {}".format(self.name))
        # self.__dict__.update is not ok, because we might want to delete some keys
        for key in self.__dict__.keys():
            if key in old_client.__dict__:
                self.__dict__[key] = old_client.__dict__[key]

    # def do_reset_level(self, **kw):
    #     self.levels = set()
    #     return "LEVELS", self.levels

    # def dont_do_open_door(self, direction, **kw):
    #     assert direction in ("up", "down", "halt")
    #     self._stopped_
    #     self.direction = direction
    #     self.door = "open"
    #     return "DOOR", self.door

    # def dont_do_close_door(self, **kw):
    #     self.door = "closed"
    #     return "DOOR", self.door

    # def do_get_state(self, **kw):
    #     return "STATUS", {'position': self.level, 'direction': self.direction, 'passengers': [], 'door': self.door, 'levels': list(self.levels)}
