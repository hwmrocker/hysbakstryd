import asyncio
import msgpack
import logging
import logging.config
import yaml


class NetworkClient:

    reader = None
    writer = None
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
        logging.info('Connecting...')
        try:
            reader, writer = yield from asyncio.open_connection(self.host, self.port)
            asyncio.async(self.create_input())
            self.reader = reader
            self.writer = writer
            self.send_msg(dict(type="connect", username=username, password=password))
            self.sockname = writer.get_extra_info('sockname')
            unpacker = msgpack.Unpacker(encoding='utf-8')
            while not reader.at_eof():
                pack = yield from reader.read(1024)
                unpacker.feed(pack)
                for msg in unpacker:
                    self.inform(*msg)
            logging.info('The server closed the connection')
            self.writer = None
        except ConnectionRefusedError as e:
            logging.info('Connection refused: {}'.format(e))
        finally:
            logging.info("close ...")
            self.close()

    @asyncio.coroutine
    def create_input(self):
        def watch_stdin():
            msg = input()
            return msg
        while True:
            mainloop = asyncio.get_event_loop()
            future = mainloop.run_in_executor(None, watch_stdin)
            input_message = yield from future
            if input_message == 'close()' or not self.writer:
                self.close()
                break
            elif input_message:
                self.keyboardinput(input_message)

    def keyboardinput(self, input_message):
        pass


class HWM(NetworkClient):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.map = []
        self.ignore_list = []

    def inform(self, msg_type, from_id, data):
        logging.info("got from {}: {}, {}".format(from_id, msg_type, data))
        try:
            handler = getattr(self, "handle_{}".format(msg_type))
            ret = handler(data)
            logging.info("{}: {}, {}".format(from_id, msg_type, ret))

        except AttributeError:
            logging.error("{}({}): {}".format(from_id, msg_type, data))
            if msg_type not in self.ignore_list:
                self.ignore_list.append(msg_type)
                logging.warning("No handler for '{}'".format(msg_type))

    def handle_ERR(self, data):
        logging.error(data)

    def handle_TRACEBACK(self, data):
        logging.error(data)

    def handle_RESHOUT(self, data):
        logging.info(data)

    def handle_WELCOME(self, data):
        import time
        # time.sleep(1)
        self.send_msg(dict(type="set_level", level=5))
        self.send_msg(dict(type="set_direction", direction="up"))
        time.sleep(2)
        self.send_msg(dict(type="set_level", level=1))
        self.send_msg(dict(type="set_level", level=4))

    def handle_LEVELS(self, data):
        pass

    def keyboardinput(self, msg):
        # foo = ['MovementPhase1', 'ShoutPlugin', 'HelpPlugin']
        if len(msg) > 1:
            self.send_msg(dict(type="help_command", command=msg))
        else:
            self.send_msg(dict(type="help_command"))
        # self.send_msg(dict(type="shout", msg=msg))


def readshit():
    shit = input()
    c.keyboardinput(shit)


def load_config():
    import yaml
    try:
        with open("config.yaml") as fh:
            return yaml.load(fh.read())
    except FileNotFoundError:
        logging.info("Meh, keine config.yaml gefunden")
        return {}
    except:
        logging.info("Meh, config.yaml gefunden, kann aber nicht geladen werden, wird ignoriert.")
        return {}


def setup_logging():
    with open("logger.conf.yaml") as fh:
        config = yaml.load(fh)
    logging.config.dictConfig(config)


if __name__ == "__main__":
    import sys
    setup_logging()
    loop = asyncio.get_event_loop()
    default_args = {
        "host": "localhost",
        "port": "8001",
    }
    default_args.update(load_config())
    if len(sys.argv) >= 2:
        default_args["username"] = sys.argv[1]
    if len(sys.argv) >= 3:
        default_args["password"] = sys.argv[2]

    c = HWM(**default_args)
    try:
        loop.add_reader(sys.stdin.fileno(), readshit)
        loop.run_until_complete(c.connect(**default_args))
    finally:
        loop.close()
