import asyncio
import msgpack
import traceback
from .game import Game


class Client:

    def __init__(self, reader, writer, game):
        self.reader = reader
        self.writer = writer
        self.peername = None
        self.game_client = None
        self.state = "pending"
        self._state = None
        self.game = game
        self.msg_buffer = []

    def inform(self, msg_type, msg_data):
        try:
            self.writer.write(msgpack.packb((msg_type, msg_data)))
        except:
            self.inform = lambda *x, **xa: None

    def print_msg(self, msg):
        msg_copy = msg.copy()
        if "password" in msg_copy:
            msg_copy["password"] = "****"
        print("recv[{}]: {}".format(self.state, msg_copy))

    def handle_msg(self, msg):
        self.print_msg(msg)
        try:
            msg_type = msg["type"]
            msg_data = msg.copy()
            msg_data.pop("type")
        except KeyError:
            self.inform("ERR", "messages should be a dict and contain a type {'type': 'a_string'}")
            return

        if self.state == "pause":
            self.buffer_msg(msg)
        elif self.state == "pending" and msg_type == "connect":
            print("connecting")
            self.game_client = self.game.register(self, **msg_data)
            self.state = "connected"
        else:
            try:
                handler = getattr(self, "do_{}".format(msg_type), lambda **foo: None)
            except AttributeError:
                self.inform("ERR",
                    "The function ({}) you are calling is not available".format(msg_type))
            ret = handler(**msg_data)

            if ret:
                msg_type, *rest = ret
                self.game.inform_all(msg_type, rest, from_id=self.id)

    def buffer_msg(self, msg):
        self.msg_buffer.append(msg)

    def update_game(self, game):
        assert self.state == "pause"
        self.game = game

    def pause(self):
        self._state, self.state = self.state, "pause"

    def resume(self):
        assert self.state == "pause"
        self.state, self._state = self._state, None

        # flush the buffer
        while (self.msg_buffer):
            msg = self.msg_buffer.pop(0)
            self.handle_msg(msg)

    def bye(self):
        self.inform = lambda *x, **xa: None
        try:
            self.game.unregister(self)
        except:
            pass


class Server:
    """
    took the structure from
    https://github.com/Mionar/aiosimplechat
    it was MIT licenced
    """
    clients = {}
    server = None

    def __init__(self, loop, host='*', port=8001):
        self.host = host
        self.port = port
        self.clients = {}
        self.game = Game()

    @asyncio.coroutine
    def run_server(self):
        try:
            self.server = yield from asyncio.start_server(
                self.client_connected,
                self.host, self.port
            )
            print('Running server on {}:{}'.format(self.host, self.port))
        except OSError:
            print('Cannot bind to this port! Is the server already running?')

    def send_to_client(self, peername, msg_type, msg_args):
        client = self.clients[peername]
        client.inform(msg_type, msg_args)
        return

    def send_to_all_clients(self, msg_type, msg_args):
        for peername in self.clients.keys():
            self.send_to_client(peername, msg_type, msg_args)
        return

    def close_all_clients(self):
        for peername, client in self.clients.items():
            client.writer.write_eof()

    def pause_all_clients(self):
        for peername, client in self.clients.items():
            client.pause()

    def resume_all_clients(self):
        for peername, client in self.clients.items():
            client.resume()

    @asyncio.coroutine
    def client_connected(self, reader, writer):
        peername = writer.transport.get_extra_info('peername')
        print("hallo {}".format(peername))
        new_client = Client(reader, writer, self.game)
        self.clients[peername] = new_client
        unpacker = msgpack.Unpacker(encoding='utf-8')
        while not reader.at_eof():
            try:
                pack = yield from reader.read(1024)
                unpacker.feed(pack)
                for msg in unpacker:
                    new_client.handle_msg(msg)
            except ConnectionResetError as e:
                print('ERROR: {}'.format(e))
                traceback.print_exc()
                new_client.bye()
                del self.clients[peername]
                return
            except Exception as e:
                error = 'ERROR: {}'.format(e)
                print(error)
                traceback.print_exc()
                self.send_to_client(peername, "ERR", error)
                new_client.writer.write_eof()
                new_client.bye()
                del self.clients[peername]
                return

    def close(self):
        self.send_to_all_clients("bye\n")
        self.close_all_clients()
