""" gui.py

a bomberman clone server.

Usage:

    gui.py
"""
import sys
import asyncio
import time
import pygameui as ui
# from docopt import docopt
from gui.scenes import LoadingScene, MapScene
import yaml
import logging
import logging.config
import traceback
import msgpack


class NetworkClient:

    sockname = None

    def __init__(self, host='127.0.0.1', port=8001, **kw):
        super().__init__()
        self.host = host
        self.port = int(port)

        self.reader = None
        self.writer = None

    def send_msg(self, msg):
        logging.info("send: {}".format(msg))
        pack = msgpack.packb(msg)
        self.writer.write(pack)

    def close(self):
        if self.writer:
            self.writer.write_eof()

    def inform(self, *msg):
        logging.info(msg)

    @asyncio.coroutine
    def connect(self, username, password, **kw):
        logging.info('Connecting.')
        try:
            logging.info('Connecting..')
            reader, writer = yield from asyncio.open_connection(self.host, self.port)
            logging.info('Connecting...')

            self.reader = reader
            self.writer = writer
            self.send_msg(dict(type="connect", username=username, password=password, observer=True))
            self.sockname = writer.get_extra_info('sockname')
            unpacker = msgpack.Unpacker(encoding='utf-8')
            logging.info("reader eof? {}".format(repr(reader.at_eof())))
            while not reader.at_eof():
                pack = yield from reader.read(1024)
                unpacker.feed(pack)
                for msg in unpacker:
                    self.inform(*msg)
            logging.info('The server closed the connection')
            self.writer = None
        except ConnectionRefusedError as e:
            logging.info('Connection refused: {}'.format(e))
        except Exception as e:
            logging.error("WTF did just happend?")
            logging.error(traceback.format_exc())
        except:
            logging.error("WTF did just happend? No subclass of Exception")
            logging.error(traceback.format_exc())

        finally:
            logging.info("close connection again...")
            self.close()

    def keyboardinput(self, input_message):
        pass


class Observer(NetworkClient):

    def __init__(self, map_scene=None, *args, **kw):
        super(Observer, self).__init__(*args, **kw)
        self.map = map_scene
        self.ignore_list = []
        self.logged_in = False
        self._world_state = {}
        # self.future = asyncio.Future()

    def tick(self):
        if not self.logged_in:
            return
        # if not self.future.done():
            # self.future.cancel()
        # self.future = asyncio.Future()
        self.send_msg(dict(type="get_world_state"))
        # return self.future

    def inform(self, msg_type, from_id, data):
        logging.info("{} send: {} {}".format(from_id, msg_type, data))
        try:
            handler = getattr(self, "handle_{}".format(msg_type))
        except AttributeError:
            logging.error("{}({}): {}".format(from_id, msg_type, data))
            if msg_type not in self.ignore_list:
                self.ignore_list.append(msg_type)
                logging.warning("No handler for '{}'".format(msg_type))
        else:
            try:
                ret = handler(data)
                logging.info("{}: {}, {}".format(from_id, msg_type, ret))
            except:
                logging.error("hanler {} died".format(msg_type))
                print(".../")

                logging.error(traceback.format_exc())
                print(".../.")

    def handle_ERR(self, data):
        logging.error(data)

    def handle_TRACEBACK(self, data):
        logging.error(data)

    def handle_RESHOUT(self, data):
        logging.info(data)

    def handle_WELCOME(self, data):
        if data != "observer":
            return
        self.logged_in = True
        # import time
        # time.sleep(1)
        # self.send_msg(dict(type="set_level", level=5))
        # self.send_msg(dict(type="set_direction", direction="up"))
        # time.sleep(2)
        # self.send_msg(dict(type="set_level", level=1))
        # self.send_msg(dict(type="set_level", level=4))

    def handle_WORLD_STATE(self, data):
        # self.future.set_result(data)
        print(".")
        self._world_state = data
        print("..")
        self.map.update_world_state(data)
        print("../")

    def handle_LEVELS(self, data):
        pass


@asyncio.coroutine
def main_loop(loop, observer):
    now = last = time.time()
    time_per_frame = 1 / 5
    # time_per_frame = 1 / 30

    while True:
        # 30 frames per second, considering computation/drawing time
        yield from asyncio.sleep(last + time_per_frame - now)
        last, now = now, time.time()
        dt = now - last
        _ = observer.tick()
        if ui.single_loop_run(dt*1000):
            return


def main(arguments):
    # init async and pygame
    loop = asyncio.get_event_loop()
    ui.init("hysbakstryd", (900, 700))

    # show loading scene
    ui.scene.push(LoadingScene())
    map_scene = MapScene()
    ui.scene.insert(0, map_scene)

    # from bomber.network import ClientStub
    # loop.call_soon(map_scene.map.player_register, ClientStub(None, None, map_scene.map))
    client = Observer(map_scene=map_scene, **arguments)
    asyncio.async(client.connect(**arguments))
    # show game ui
    ui.scene.pop()
    try:
        loop.run_until_complete(main_loop(loop, client))
    finally:
        loop.close()


def setup_logging():
    with open("logger.conf.yaml") as fh:
        config = yaml.load(fh)
    logging.config.dictConfig(config)


def load_config():
    import yaml
    try:
        with open("config_gui.yaml") as fh:
            return yaml.safe_load(fh.read())
    except FileNotFoundError:
        logging.info("Meh, keine config.yaml gefunden")
        return {}
    except:
        logging.info("Meh, config.yaml gefunden, kann aber nicht geladen werden, wird ignoriert.")
        return {}


if __name__ == "__main__":
    # arguments = docopt(__doc__, version='bomber 0.1')
    setup_logging()
    default_args = {
        "host": "localhost",
        "port": "8001",
    }
    default_args.update(load_config())
    if len(sys.argv) >= 2:
        default_args["username"] = sys.argv[1]
    if len(sys.argv) >= 3:
        default_args["password"] = sys.argv[2]

    main(default_args)
