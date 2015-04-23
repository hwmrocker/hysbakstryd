import asyncio
import msgpack
import traceback
import os
import logging
import zeroconf

# we cannot use from .game import Game because we need to be able to reload it
import hysbakstryd.game

from importlib import reload

TICK_TIME = 0.1


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
        self.logger = logging

    def inform(self, msg_type, msg_data, from_id="__master__"):
        try:
            self.writer.write(msgpack.packb((msg_type, from_id, msg_data)))
        except:
            self.logger.error(traceback.format_exc())
            self.inform = lambda *x, **xa: None

    def privacy_complaint_msg(self, msg):
        msg_copy = msg.copy()
        if "password" in msg_copy:
            msg_copy["password"] = "****"
        return msg_copy

    def handle_msg(self, msg):
        self.logger.debug("handle {}".format(self.privacy_complaint_msg(msg)))
        try:
            msg_type = msg["type"]
            msg_data = msg.copy()
            msg_data.pop("type")
        except KeyError:
            self.logger.info("msg was not valid because it didn't contain a type key, it was rejected")
            self.inform("ERR", "messages should be a dict and contain a type {'type': 'a_string'}")
            return

        for key in msg_data.keys():
            if not isinstance(key, str):
                self.logger.info("msg was not valid, it was rejected because a key was not of type str")
                self.inform("ERR", "message keys should only be strings {'type': 'foo', 'bar': 'ok', 42: 'not ok'}")
                return

        if self.state == "pause":
            self.buffer_msg(msg)
        elif self.state == "pending" and msg_type == "connect":
            self.logger.info("connecting")
            # TODO we should put a try catch around the registering
            self.game_client = self.game.register(self, **msg_data)
            self.logger = self.game_client.logger
            self.state = "connected"
            self.logger.info("connected")
        elif self.state == "connected":
            try:
                self.game.handle(self.game_client, msg_type, msg_data)
            except AttributeError:
                error = "The function ({}) you are calling is not available".format(msg_type)

                traceback.print_exc()

                self.logger.warning(error)
                self.inform("ERR", error)
            except Exception as e:
                error = 'Error while calling {}: {}'.format(msg_type, e)
                traceback_data = traceback.format_exc()

                self.logger.error(error)
                self.logger.error(traceback_data)

                self.inform("ERR", error)
                self.inform("TRACEBACK", traceback_data)

    def buffer_msg(self, msg):
        self.msg_buffer.append(msg)

    def pause(self):
        self.logger.info("pause client")
        self._state, self.state = self.state, "pause"

    def resume(self):
        assert self.state == "pause"
        self.logger.info("resume client")

        self.state, self._state = self._state, None

        if self.msg_buffer:
            self.logger.info("flush buffer")
        # flush the buffer
        while (self.msg_buffer):
            msg = self.msg_buffer.pop(0)
            self.handle_msg(msg)

    def bye(self):
        self.inform = lambda *x, **xa: None
        try:
            self.game.unregister(self)
        except:
            # TODO check if this is always an error, maybe we should fix this in game.unregister and
            # not catch it here
            self.logger.error("unregister game failed")
            raise


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
        self.game = hysbakstryd.game.Game()
        self.running = True
        self.loop = loop
        self.zeroconf_announce()
        asyncio.async(self.ticker())

    def zeroconf_announce(self):
        """
        This registers a Zeroconf service.

        Type: _hysbakstryd._tcp.
        Name: Server._hysbakstryd._.tcp.
        """
        info = zeroconf.ServiceInfo("_hysbakstryd._tcp.", "Server._hysbakstryd._tcp.", port=self.port)
        zc = zeroconf.Zeroconf()
        zc.register_service(info)

    @asyncio.coroutine
    def check_for_new_game(self):
        directory = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(directory, "game.py")

        old_mtime = os.stat(file_path).st_mtime

        while self.running:
            new_mtime = os.stat(file_path).st_mtime
            if new_mtime != old_mtime:
                logging.info("reload")
                self.pause_all_clients()
                self.game.pause()
                # actually reload game
                reload(hysbakstryd.game)
                _game = hysbakstryd.game.Game(_old_game=self.game)
                self.game = _game
                self.game.resume()
                self.resume_all_clients()
                old_mtime = new_mtime

            yield from asyncio.sleep(1)

    @asyncio.coroutine
    def run_server(self):
        try:
            self.server = yield from asyncio.start_server(
                self.client_connected,
                self.host, self.port
            )
            logging.info('Running server on {}:{}'.format(self.host, self.port))
            print('Running server on {}:{}'.format(self.host, self.port))
            asyncio.async(self.check_for_new_game())
        except OSError:
            logging.error('Cannot bind to this port! Is the server already running?')

    @asyncio.coroutine
    def ticker(self):
        while self.running:
            self.loop.call_soon(self.game.tick)
            yield from asyncio.sleep(TICK_TIME)
        logger.error('TICKER STOPS')

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
        logging.info("hallo {}".format(peername))
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
                logging.info('Connection Reset: {}'.format(e))
                new_client.bye()
                del self.clients[peername]
                return
            except Exception as e:
                error = 'ERROR: {}'.format(e)
                traceback_data = traceback.format_exc()
                logging.critical(error)
                logging.critical("This error should be catched in the client, not here")
                logging.critical(traceback_data)

                self.send_to_client(peername, "ERR", error)
                self.send_to_client(peername, "TRACEBACK", traceback_data)

                new_client.writer.write_eof()
                new_client.bye()
                del self.clients[peername]
                return

    def close(self):
        self.send_to_all_clients("BYE", [])
        self.close_all_clients()
