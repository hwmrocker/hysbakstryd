#!/usr/bin/env python3
import asyncio

from hysbakstryd.network import Server


def main(args):
    loop = asyncio.get_event_loop()

    server = Server(loop)
    try:
        loop.run_until_complete(server.run_server())
        loop.run_forever()
    finally:
        loop.close()

if __name__ == "__main__":
    main({})
