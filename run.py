#!/usr/bin/env python3
import asyncio
import logging
import logging.config
import yaml
from hysbakstryd.network import Server, WebsocketClient
from autobahn.asyncio.websocket import WebSocketServerFactory


def setup_logging():
    with open("logger.conf.yaml") as fh:
        config = yaml.load(fh)
    logging.config.dictConfig(config)


def main_command(bind_address='0.0.0.0', port=8000, ws_port=9000):
    setup_logging()
    loop = asyncio.get_event_loop()

    server = Server(loop, host=bind_address, port=port)
    ws_server = WebSocketServerFactory("ws://{}:{}".format(bind_address, ws_port), debug=False)
    ws_server.protocol = WebsocketClient
    WebsocketClient.SERVER = server
    coroutine = loop.create_server(ws_server, bind_address, ws_port)
    
    try:
        loop.run_until_complete(server.run_server())
        loop.run_until_complete(coroutine)
        loop.run_forever()
    except KeyboardInterrupt:
        server.running = False
    finally:
        loop.close()

if __name__ == "__main__":
    import commandeer
    commandeer.cli(default_command='main')

