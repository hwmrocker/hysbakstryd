import pygameui as ui


class LoadingScene(ui.Scene):

    def __init__(self):
        super(LoadingScene, self).__init__()

        label = ui.label.Label(self.frame, "Loading ...")
        self.add_child(label)


class MapScene(ui.Scene):

    def __init__(self, map=None):
        super(MapScene, self).__init__()
        # map = Map(ui.Rect(10, 10, 490, 490))
        # self.map = map
        # self.map.on_update_player.connect(self.update_player)
        # self.add_child(self.map)
        self.user = {}
        self.label = {}
        self.next_id = 1
        id_to_frame = {
                "1": (0, 500, 250, 30),
                "2": (250, 500, 250, 30),
                "3": (0, 530, 250, 30),
                "4": (250, 530, 250, 30),
                "5": (0, 560, 250, 30),
                "6": (250, 560, 250, 30),
                "7": (0, 590, 250, 30),
                "8": (250, 590, 250, 30),
            }
        for id, frame in id_to_frame.items():
            self.label[id] = ui.label.Label(ui.Rect(*id_to_frame[id]), "foo %s" % id)
            self.add_child(self.label[id])

    def update(self, dt):
        for player in self.user.values():
            self.label[player['id']].text = "%s %s %.2f" % (player['id'], player['username'], player['level'])
        super(MapScene, self).update(dt)

    def update_player(self, player):
        if player.name not in self.user:
            pass
        self.user[player.name] = player
        self.label[player['id']].text = "%s %s %.2f" % (player['id'], player['username'], player['level'])

    def update_world_state(self, state):
        for username, user_state in state.items():
            if username not in self.user:
                user_id = str(self.next_id)
                self.next_id += 1
            else:
                user_id = self.user[username]['id']
            user_state['id'] = user_id
            self.user[username] = user_state
