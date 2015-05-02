import asyncio
import uuid
from autobahn.websocket.http import HttpException
import msgpack
import traceback
import os
import logging
import zeroconf
import platform

from autobahn.asyncio.websocket import WebSocketServerProtocol

# we cannot use from .game import Game because we need to be able to reload it
import hysbakstryd.game

from importlib import reload

TICK_TIME = 0.1


class ClientProtocol:
    """An interface for defining a client for the game.

    This will usually be networked clients, but can be anything you want.
    """

    # ##################################################################################################################
    # interface methods -- implement these to make a working client!

    def inform(self, msg_type, msg_data, from_id="__master__"):
        """Inform this client about something that happened."""
        ...

    # conversely: call self.handle_msg(msg) for messages that the client received

    def close(self):
        """Close the connection for this client."""
        ...

    # ##################################################################################################################
    # inner workings -- you should probably not change these functions

    def __init__(self):
        self.game_client = None
        self.game_client_state = "pending"
        self._game_client_state = None      # state buffer for pausing a client
        self.game = None        # make sure that this is set immediately after initialization!!
        self.msg_buffer = []
        self.logger = logging

    def privacy_complaint_msg(self, msg):
        """Mask passwords in a message."""
        try:
            msg_copy = msg.copy()
            if "password" in msg_copy:
                msg_copy["password"] = "****"
            return msg_copy
        except Exception:
            # didn't work, so probably didn't contain any passwords anyway
            return msg

    def buffer_msg(self, msg):
        self.msg_buffer.append(msg)

    def flush(self):
        while self.msg_buffer:
            msg = self.msg_buffer.pop(0)
            self.handle_msg(msg)

    def pause(self):
        self.logger.info("pausing client")
        self._game_client_state, self.game_client_state = self.game_client_state, "pause"

    def resume(self):
        assert self.game_client_state == "pause"
        self.logger.info("resuming client")

        self.game_client_state, self._game_client_state = self._game_client_state, None

        if self.msg_buffer:
            self.logger.info("flushing message buffer with {} messages".format(len(self.msg_buffer)))
            self.flush()

    def bye(self):
        self.inform = lambda *x, **xa: None    # blind the inform function because it won't work at this point anyway
        try:
            self.game.unregister(self)
        except:
            # TODO check if this is always an error, maybe we should fix this in game.unregister and
            # not catch it here
            self.logger.error("unregister game failed")
            raise

    def handle_msg(self, msg):
        """Handle a sent message: decoding, deciding and calling the necessary game transitions."""
        self.logger.debug("handling {}".format(self.privacy_complaint_msg(msg)))
        try:
            msg_type = msg["type"]
            msg_data = msg.copy()
            msg_data.pop("type")
        except KeyError:
            self.logger.info("msg was not valid because it didn't contain a type key, it was rejected")
            self.inform("ERR", "invalid message format: messages should be a dict and contain a type {'type': 'a_string'}")
            return
        except:
            self.logger.info("could not handle msg because it was not very valid")
            self.inform("ERR", "invalid message: messages must be msgpack-encoded dictionaries")
            return

        # TODO: is this check necessary?!
        for key in msg_data.keys():
            if not isinstance(key, str):
                self.logger.info("msg was not valid, it was rejected because a key was not of type str")
                self.inform("ERR", "message keys should only be strings {'type': 'foo', 'bar': 'ok', 42: 'not ok'}")
                return

        if self.game_client_state == "pause":
            self.buffer_msg(msg)
        elif self.game_client_state == "pending" and msg_type == "connect":
            self.logger.info("connecting")
            # TODO we should put a try catch around the registering
            self.game_client = self.game.register(self, **msg_data)
            self.logger = self.game_client.logger
            self.game_client_state = "connected"
            self.logger.info("connected")
        elif self.game_client_state == "connected":
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


class NetworkClient(ClientProtocol):

    def __init__(self, reader, writer):
        super().__init__()

        self.reader = reader
        self.writer = writer

    def inform(self, msg_type, msg_data, from_id="__master__"):
        try:
            self.writer.write(msgpack.packb((msg_type, from_id, msg_data)))
        except:
            self.logger.error(traceback.format_exc())
            self.inform = lambda *x, **xa: None

    def close(self):
        self.writer.write_eof()


class WebsocketClient(WebSocketServerProtocol, ClientProtocol):
    """A client that connects through a websocket."""

    # please set this to the currently running server instance, otherwise we won't know where to connect to
    # and will drop all connections immediately...
    SERVER = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.peer_name = uuid.uuid4()
        self.logger = logging
        self.unpacker = msgpack.Unpacker(encoding='utf-8')

    def inform(self, msg_type, msg_data, from_id="__master__"):
        payload = msgpack.packb(msgpack.packb((msg_type, from_id, msg_data)))
        self.sendMessage(payload=payload, isBinary=True)
        # TODO: exceptions?!

    def close(self):
        self.sendClose(reason="Game stopped")

    def onConnect(self, request):
        if WebsocketClient.SERVER is None:
            self.logger.critical("SERVER variable not set, cannot connect to game")
            raise HttpException('Game server not reachable')

        return None  # accept without conditions

    def onOpen(self):
        self.logger.info("hallo on WS: {}".format(self.peer))
        WebsocketClient.SERVER.register_client(self, self.peer)

    def onMessage(self, payload, isBinary):
        if not isBinary:
            self.logger.warning("received non-binary message from client {}".format(self.peer))
            self.sendMessage("sent messages must be binary and msgpack-encoded")
        else:
            # TODO: is this necessary? not really...
            self.unpacker.feed(payload)
            for msg in self.unpacker:
                self.handle_msg(msg)

    def onClose(self, wasClean, code, reason):
        self.logger.info('disconnected, code: {}, reason: {}'.format(code, reason))
        self.game_client_state = 'disconnected'


########################################################################################################################
# actual web connection handling and stuff!


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
        info = zeroconf.ServiceInfo("_hysbakstryd._tcp.", "Server._hysbakstryd._tcp.", port=self.port, properties=b"Server for Hysbakstryd", server=platform.node())
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
        logging.error('TICKER STOPS')

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
            client.close()

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
        new_client = NetworkClient(reader, writer)
        self.register_client(new_client, peername)

        # should this not be part of the client?!
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
                logging.critical("This error should be caught in the client, not here")
                logging.critical(traceback_data)

                err_msg = """Your message was invalid and could not be handled.
The error that appeared during the handling of your message was: {}""".format(error)
                
                self.send_to_client(peername, "ERR", err_msg)
                self.send_to_client(peername, "TRACEBACK", traceback_data)

                new_client.writer.write_eof()
                new_client.bye()
                del self.clients[peername]
                return

    def register_client(self, client, peer_name):
        """Register a client, ie. an object that conforms to ClientProtocol."""
        logging.info("registering: {}".format(peer_name))
        self.clients[peer_name] = client
        client.game = self.game

    def close(self):
        self.send_to_all_clients("BYE", [])
        self.close_all_clients()


