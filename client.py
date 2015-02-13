import asyncio
import msgpack


class NetworkClient:

    reader = None
    writer = None
    sockname = None

    def __init__(self, host='127.0.0.1', port=8001):
        super().__init__()
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    def send_msg(self, msg):
        print("send: {}".format(msg))
        pack = msgpack.packb(msg)
        self.writer.write(pack)

    def close(self):
        if self.writer:
            self.writer.write_eof()

    def inform(self, *msg):
        print(msg)

    @asyncio.coroutine
    def connect(self, username="hwm", password="foobar2"):
        print('Connecting...')
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
            print('The server closed the connection')
            self.writer = None
        except ConnectionRefusedError as e:
            print('Connection refused: {}'.format(e))
        finally:
            print("close ...")
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
        try:
            handler = getattr(self, "handle_{}".format(msg_type))
            ret = handler(data)
            print("{}: {}, {}".format(from_id, msg_type, ret))

        except AttributeError:
            if msg_type not in self.ignore_list:
                self.ignore_list.append(msg_type)
                print("No handler for {}".format(msg_type))

    def handle_ERR(self, data):
        print(data)

    def handle_TRACEBACK(self, data):
        print(data)

    def handle_RESHOUT(self, data):
        print(data)

    def keyboardinput(self, msg):
        self.send_msg(dict(type="shout", msg=msg))


def readshit():
    shit = input()
    c.keyboardinput(shit)

if __name__ == "__main__":
    import sys

    c = HWM()
    loop = asyncio.get_event_loop()
    try:
        loop.add_reader(sys.stdin.fileno(), readshit)
        loop.run_until_complete(c.connect(sys.argv[1], sys.argv[2]))
    finally:
        loop.close()
