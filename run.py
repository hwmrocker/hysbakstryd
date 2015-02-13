#!/usr/bin/env python3
import asyncio
import logging
import logging.config
import yaml
from hysbakstryd.network import Server


def setup_logging():
    with open("logger.conf.yaml") as fh:
        config = yaml.load(fh)
    logging.config.dictConfig(config)


def main(args):
    setup_logging()
    loop = asyncio.get_event_loop()

    server = Server(loop)
    try:
        loop.run_until_complete(server.run_server())
        loop.run_forever()
    except KeyboardInterrupt:
        server.running = False
    finally:
        loop.close()

if __name__ == "__main__":

    main({})
