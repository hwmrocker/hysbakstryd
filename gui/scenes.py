import pygameui as ui
import logging


class LoadingScene(ui.Scene):

    def __init__(self):
        super(LoadingScene, self).__init__()

        label = ui.label.Label(self.frame, "Loading ...")
        self.add_child(label)


class Car(ui.View):
    def __init__(self, frame):
        super().__init__(frame)
        self.stylize()

    def stylize(self):
        super().stylize()
        self.background_color = [0, 0, 0]


class PlayerView(ui.View):

    def __init__(self, idx):
        frame = ui.Rect(60+105*idx, 0, 100, 640)
        super().__init__(frame)
        self.name_label = ui.label.Label(ui.Rect(0, 0, 100, 20), "User %s" % idx)
        self.add_child(self.name_label)
        self.level_label = ui.label.Label(ui.Rect(0, frame.height-20, 100, 20), "Level %s" % idx)
        self.add_child(self.level_label)
        self.car = Car(ui.Rect(0, frame.height-20-60, 100, 60))
        self.add_child(self.car)
        self.hidden = True

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        self._level = value
        self.level_label.text = "Level %.1f" % value
        self.car.frame.bottom = (self.frame.height - 20) - value * 60

    def update_user_state(self, data):
        self.hidden = False
        username = data["username"][:7]
        if self.name_label.text != username:
            self.name_label.text = username
        self.level = data["level"]


class MapScene(ui.Scene):

    def __init__(self, map=None):
        super().__init__()
        # map = Map(ui.Rect(10, 10, 490, 490))
        # self.map = map
        # self.map.on_update_player.connect(self.update_player)
        # self.add_child(self.map)
        self.user = {}
        self.name2idx = {}
        self.label = {}
        self.next_id = 0
        for i in range(8):
            pv = PlayerView(i)
            # pv.background_color = [0, 0, 0] if i % 2 else [50, 50, 50]
            self.add_child(pv)
            self.user[i] = pv
            # pv.layout()
        # self.shadowed = True
        self.stylize()
        # id_to_frame = {
        #         "1": (0, 500, 250, 30),
        #         "2": (250, 500, 250, 30),
        #         "3": (0, 530, 250, 30),
        #         "4": (250, 530, 250, 30),
        #         "5": (0, 560, 250, 30),
        #         "6": (250, 560, 250, 30),
        #         "7": (0, 590, 250, 30),
        #         "8": (250, 590, 250, 30),
        #     }
        # for id, frame in id_to_frame.items():
        #     self.label[id] = ui.label.Label(ui.Rect(*id_to_frame[id]), "foo %s" % id)
        #     self.add_child(self.label[id])

    def update(self, dt):
        # for player in self.user.values():
        #     self.label[player['id']].text = "%s %s %.2f" % (player['id'], player['username'], player['level'])
        super(MapScene, self).update(dt)

    def update_player(self, player):
        return
        if player.name not in self.user:
            pass
        self.user[player.name] = player
        self.label[player['id']].text = "%s %s %.2f" % (player['id'], player['username'], player['level'])

    def update_world_state(self, state):
        for username, user_state in state.items():
            if username not in self.name2idx:
                user_id = self.next_id
                self.name2idx[username] = user_id
                self.next_id += 1
            else:
                user_id = self.name2idx[username]
            user_state['id'] = user_id
            self.user[user_id].update_user_state(user_state)
