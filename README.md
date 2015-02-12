# hysbakstryd

A multiplayer elevator battle game. The name is a combination of two africaans word, namely `hysbak` which stands for elevator and `stryd` that means battle.


## How to run the headless server

On Ubuntu / Linux Mint you need to install `libffi-dev` before you install bcrypt. Run the following commands:

```
sudo apt-get install libffi-dev
virtualenv env -p python3;
. env/bin/activate
pip install bcrypt msgpack-python
python run.py
```

## Packets

### Login

send 

```
{
    "type": "connect",       # str, required
    "username": "Hans",      # str, required
    "password": "gehaim",    # str, required
}
```

### Shout


```
{
    "type": "shout",         # str, required
    ... # all you want
}
```

returns 

```
 ("RESHOUT", "username", {... # all you want})
```


## Design choices

```
    +-------+                      +------------+
    | Game  |                      |            |
    |ClientA<-----------------+----+  Game      |
    +---+-^-+                 |    |  Instance  |
        | |                   |    |            |
        | |       +-------+   |    |            |
        | |       | Game  |   |    |            |
        | |       |ClientB<---+    |            |
        | |       +---+-^-+        +------^-----+
        | |           | |                 | Instanciate
        | |           | |                 |  / Reload
        | |           | |          +------+-----+
        | |           | |          |            |
        | |           | |          |  NetServer |
        | |           | |          |            |
        | |       +---v-+-+        +-+----------+
        | |       | Net   |          |
        | |       |ClientB<----------+
        | |       +-------+          |
    +---v-+-+                        |
    | Net   |                        |
    |ClientA<------------------------+
    +-------+
```

To make ``rapid`` development possible, I split the network communication part strictly from the game logic. After the `NetServer` (`hysbakstryd.network.Server`) is started, the `GameInstance` (`hysbakstryd.game.Game`) is spawend. After a scuccessfull `connect` to the server, a new `NetClient` (`hysbakstryd.network.Client`) is created, it will register to the game and a new `GameClient` is created. If the network connection from the client drops, it can reconnect with the same credentials to regain access to the coresponding game client. The client can disconnect / reconnect at any time without obstruct the server. At the same time, the network server is checking the filesystem if the code of the game (`hysbakstryd.game.py`) has changed, and will hot reload the code in a way that no connection will be dropped.

## License

This code is licensed under GNU GENERAL PUBLIC LICENSE Version 2. See `LICENSE` for further information.


## Misc.

Thanks [asciiflow][asciiflow] for their super easy, ascii chart generator.


[asciiflow]: http://asciiflow.com/