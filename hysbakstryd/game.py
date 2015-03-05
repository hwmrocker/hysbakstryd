import logging

from bcrypt import hashpw, gensalt
from collections import defaultdict
# import gc

__version__ = "0.0.4"
logger = logging.getLogger("game")


class WrongPassword(Exception):
    pass


class Game:

    # duration of one game tick
    TICK_TIME = 0.1  # seconds

    # MOVEMENT RATE FOR AN ELEVATOR IN EACH GAME TICK
    RATE = 1  # levels per second

    MOVEMENT_PER_TICK = RATE * TICK_TIME

    # how long does an elevator wait when the door is opened?
    WAITING_TIME = 10 # ticks

    # more game variables

    # person spawn rate
    # max person spawn floor

    MAX_FLOOR = 9
    MIN_FLOOR = 0

    def __init__(self, _old_game=None):
        logger.info("New game instanciated")
        self.user_to_passwords = {}
        self.user_to_game_clients = {}
        self.user_to_network_clients = {}
        self.network_to_user = {}
        self.future_events = defaultdict(list)
        self.time = 0
        self._pause = False
        self.version = __version__

        self.plugins = set()
        self.command_map = {}
        self.event_map = {}

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
        # print(gc.collect())

    def inform_all(self, msg_type, data, from_id="__master__"):
        for net_client in self.user_to_network_clients.values():
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
            except:
                logger.info("unregister bei relogin ging nicht")

        self.user_to_network_clients[username] = network_client
        self.network_to_user[network_client] = username
        return self.user_to_game_clients[username]

    def unregister(self, network_client):
        logger.info("bye {}".format(network_client))
        username = self.network_to_user[network_client]
        self.user_to_game_clients[username].online = False
        del self.user_to_network_clients[username]
        del self.network_to_user[network_client]

    def pause(self):
        self._pause = True

    def resume(self):
        logger.info('resuming')
        self._pause = False

    def move_client(self, c):
        if c.door == 'open':
            return

        intlevel = round(c.level)
        if abs(c.level - intlevel) > self.MOVEMENT_PER_TICK:
            intlevel = None

        if c.direction == 'down':
            if intlevel in c.levels:
                c.level = intlevel
                c.levels.remove(intlevel)
                c.door = 'open'
                c._stopped_at = self.time
                logger.debug('{} stopped at {}'.format(c.name, c.level))
            elif c.level <= self.MIN_FLOOR:
                c.direction = 'halt'
                c.level = self.MIN_FLOOR
            else:
                c.level -= self.MOVEMENT_PER_TICK
        elif c.direction == 'up':
            if intlevel in c.levels:
                c.level = intlevel
                c.levels.remove(intlevel)
                c.door = 'open'
                c._stopped_at = self.time
                logger.debug('{} stopped at {}'.format(c.name, c.level))
            elif c.level >= self.MAX_FLOOR:
                c.level = self.MAX_FLOOR
                c.direction = 'halt'
            else:
                c.level += self.MOVEMENT_PER_TICK

    def wait_for_door(self, c):
        """
        Wait for the appropriate time until the doors close again
        """

        # can the user close the doors themselves? Should we guard against that?

        if c.door == 'open' and c._stopped_at + self.WAITING_TIME <= self.time:
            c.door = 'closed'
            if c.level in c.levels:
                c.levels.remove(c.level)

            if not c.levels:
                c.direction = 'halt'

            if c.direction == 'up' and all((l < c.level for l in c.levels)):
                c.direction = 'down'
            if c.direction == 'down' and all((l > c.level for l in c.levels)):
                c.direction = 'up'

    def register_plugins(self):
        self.register_plugin(MovementPhase1())
        self.register_plugin(ShoutPlugin())
        # TODO: load plugins dynamically?!

        print(self.command_map)

    def register_plugin(self, plugin):
        # events
        for event_method_name in [m for m in dir(plugin) if m.startswith('at_') and callable(getattr(plugin, m))]:
            event_name = event_method_name[3:]
            self.event_map[event_name] = getattr(plugin, event_method_name)

        for command_method_name in [m for m in dir(plugin) if m.startswith('do_') and callable(getattr(plugin, m))]:
            self.command_map[command_method_name[3:]] = getattr(plugin, command_method_name)

        self.plugins.add(plugin)
        plugin.initialize(self)
        
                
    def emit(self, client, event_name, *args, **kwargs):
        if event_name in self.event_map:
            for c in self.clients:
                self.event_map[event_name](client, *args, **kwargs)
        else:
            return

    def handle(self, client, msg_type, msg_data):
        if msg_type not in self.command_map:
            print(msg_type, self.command_map.keys())
            raise AttributeError

        ret = self.command_map[msg_type](client, **msg_data)
        
        if ret:
            msg_type, *rest = ret
            logger.debug("send: {} {}".format(msg_type, rest))
            self.inform_all(msg_type, rest, from_id=client.name)


    def tick(self):
        if self._pause:
            return

        self.time += 1

        for c in self.user_to_game_clients.values():
            try:
                # movement of elevator boxes
                self.move_client(c)
                self.wait_for_door(c)
            except:
                import traceback
                debug.error(traceback.print_exc())
            # self.load_people(c)

        # generate waiting people

        
class Plugin:
    """
    Main plugin class for Hysbakstrid.

    All methods whose name start with do_ will be registered as client commands that can
    be sent data. Each command should return a set of methods to be added to the client
    state. Each method will be called in each tick until it returns a non-True value, at
    which point it will be removed from the client's states.

    Additionally, the Plugin `tick` method will be called each tick with a set of all
    clients and can perform time-based or global processing at that point.
    """

    def emit(self, client, event_name, *args, **kwargs):
        """
        Call this method when you want to emit an event (to all other plugins).
        """

        # TODO: implement

    def initialize(self, game):
        """
        Called once when the game starts or the game reinitializes.
        """
        pass

    def tick(self, clients):
        """
        Called every game tick with all currently registered clients.

        Return a set of states that will be added to the client states. Each client state
        is a function on the plugin that will be called each tick.
        """
        pass

    


class MovementPhase1(Plugin):
    """
    Movement mechanism.

    Put your name in `client.movement_paused_by` (a set) to stop the elevator from
    moving.

    Will emit these events:
     * `(moving, 'up'/'down')` when movement starts
     * `(at_level, x)` when entering level x (pause movement and 'snap' to a level if you
       want to stop there)
     * `(movement_paused, )` when movement begins to be paused
     * `(movement_unpaused, )` when movement ends to be paused
     * `(stopped, )`, when the direction was set to 'halt'
    """

    def initialize(self, game):
        pass

    def connect(self, client):
        client.movement_paused = False
        client.levels = set()
        client.direction = 'halt'

    # states
    def moving(self, client):
        if client.movement_paused:
            if not client.was_paused:
                client.was_paused = True
                self.emit('movement paused')
            return
        else:
            if client.was_paused:
                client.was_paused = False
                self.emit('movement unpaused')

        print("client would move, probably")


    # event listeners
    # no event listeners
        
    # commands
        
    def do_set_direction(self, client, direction=None):
        assert direction in ("up", "down", "halt")
        client.direction = direction
        if direction == 'halt':
            self.emit('stopped')
        else:
            self.emit('moving', (direction, ))
        return (), ("DIRECTION", self.direction)

    def do_set_level(self, client, level=None):
        assert 0 <= level < 10
        client.levels.add(level)
        return (self.moving, ),  ("LEVELS", list(self.levels))
    
    def do_reset_levels(self, client):
        client.levels = set()
        return (), ("LEVELS", [])
        
class ShoutPlugin(Plugin):

    def __init__(self):
        self.logger = logger.getChild("ShoutPlugin")
    
    def do_shout(self, client, **foo):
        self.logger.debug("{}: {}".format(client.name, foo))
        return (), ("RESHOUT", foo)


    
class GameClient:

    def __init__(self, username, game, observer=False, _old_client=None, **kw):
        self.name = username
        self.game = game
        self.online = True
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

    def do_reset_level(self, **kw):
        self.levels = set()
        return "LEVELS", self.levels

    def dont_do_open_door(self, direction, **kw):
        assert direction in ("up", "down", "halt")
        self._stopped_
        self.direction = direction
        self.door = "open"
        return "DOOR", self.door

    def dont_do_close_door(self, **kw):
        self.door = "closed"
        return "DOOR", self.door

    def do_get_state(self, **kw):
        return "STATUS", {'position': self.level, 'direction': self.direction, 'passengers': [], 'door': self.door, 'levels': list(self.levels)}


