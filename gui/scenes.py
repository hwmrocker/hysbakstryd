import pygameui as ui
import logging


class LoadingScene(ui.Scene):

    def __init__(self):
        super(LoadingScene, self).__init__()

        label = ui.label.Label(self.frame, "Loading ...")
        self.add_child(label)


class PersonCounterView(ui.View):

    def __init__(self, idx):
        frame = ui.Rect(0, 0, 60, 60)
        frame.bottom = 620 - idx * 60
        super().__init__(frame)
        self._idx = idx
        self.up_label = ui.Label(ui.Rect(5, 7, 55, 20), "00", halign=ui.label.LEFT)
        self.add_child(self.up_label)
        self.down_label = ui.Label(ui.Rect(5, 33, 55, 20), "00", halign=ui.label.LEFT)
        self.add_child(self.down_label)
        self.level_indicator = ui.Label(ui.Rect(0, 0, 60, 60), str(idx), halign=ui.label.LEFT)
        self.add_child(self.level_indicator)

        self.up = 0
        self.down = 10

    @property
    def up(self):
        return int(self.up_label.text[2:])

    @up.setter
    def up(self, value):
        self.up_label.text = "A {}".format(value)

    @property
    def down(self):
        return self.down_label.text

    @down.setter
    def down(self, value):
        self.down_label.text = "v {}".format(value)

    def update_counters(self, up, down):
        if len(up) != self.up:
            self.up = len(up)
        if len(down) != self.down:
            self.down = len(down)

    def stylize(self):
        super().stylize()
        self.background_color = [200, 200, 200] if self._idx % 2 else [250, 250, 250]
        for child in self.children:
            child.background_color = [0, 0, 0, 0]
        self.level_indicator.text_color = [100, 100, 100, 10]


class PassengerView(ui.View):

    def __init__(self, idx):
        # car size = 100, 60
        col = idx % 2
        row = idx // 2
        frame = ui.Rect(50 * col, 30 * row, 50, 30)
        super().__init__(frame)
        self.to_level_label = ui.Label(ui.Rect(5, 7, 55, 20), "00", halign=ui.label.LEFT)
        self.add_child(self.to_level_label)

    def update_passenger(self, passenger):
        self.to_level_label.text = str(passenger["wants_to"])

    def clear_passenger(self):
        self.to_level_label.text = ""


class Car(ui.View):
    def __init__(self, frame):
        super().__init__(frame)
        self.stylize()
        self.passengers = {}
        for idx in range(4):
            p = PassengerView(idx)
            self.add_child(p)
            self.passengers[idx] = p

    def stylize(self):
        super().stylize()
        for child in self.children:
            child.background_color = [0, 0, 0, 0]
        self.background_color = [166, 104, 41]

    def update_passengers(self, passengers):
        idx = -1
        for idx, p in enumerate(passengers):
            if idx >= 4:
                logging.error("maximum 4 passengers")
                logging.error(passengers)
                import sys
                sys.exit()
            else:
                self.passengers[idx].update_passenger(p)
        for i in range(idx + 1, 4):
            self.passengers[i].clear_passenger()


class PlayerView(ui.View):

    def __init__(self, idx):
        frame = ui.Rect(60+105*idx, 0, 100, 700)
        super().__init__(frame)
        self.name_label = ui.label.Label(ui.Rect(0, 0, 100, 20), "User %s" % idx)
        self.add_child(self.name_label)
        self.level_label = ui.label.Label(ui.Rect(0, 620, 100, 20), "Level %s" % idx)
        self.add_child(self.level_label)
        self.transported_label = ui.label.Label(ui.Rect(0, 640, 100, 20), "transported")
        self.add_child(self.transported_label)
        self.car = Car(ui.Rect(0, frame.height-20-60, 100, 60))
        self.add_child(self.car)
        self.hidden = True
        self._level = 0
        self._transported = 0

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        self._level = value
        self.level_label.text = "Level {:.1f}".format(value)
        self.car.frame.bottom = (620) - value * 60

    @property
    def transported(self):
        return self._transported

    @transported.setter
    def transported(self, value):
        self._transported = value
        self.transported_label.text = "{}".format(value)

    def update_user_state(self, data):
        self.hidden = False
        username = data["username"][:7]
        if self.name_label.text != username:
            self.name_label.text = username
        self.level = data["level"]
        self.transported = data["people_transported"]
        self.car.update_passengers(data["on_board"])


class MapScene(ui.Scene):

    def __init__(self, map=None):
        super().__init__()
        self.user = {}
        self.counters = {}
        self.name2idx = {}
        self.label = {}
        self.next_id = 0
        for i in range(8):
            pv = PlayerView(i)
            self.add_child(pv)
            self.user[i] = pv
        for i in range(10):
            person_counter = PersonCounterView(i)
            self.add_child(person_counter)
            self.counters[i] = person_counter
        self.stylize()

    def update_player(self, player):
        return
        if player.name not in self.user:
            pass
        self.user[player.name] = player
        self.label[player['id']].text = "%s %s %.2f" % (player['id'], player['username'], player['level'])

    def update_world_state(self, state):
        for username, user_state in state.items():
            if username == "__world__":
                up = user_state['waiting_up']
                down = user_state['waiting_down']
                for i in range(10):
                    self.counters[i].update_counters(up.get(i, []), down.get(i, []))
                return
            if username not in self.name2idx:
                user_id = self.next_id
                self.name2idx[username] = user_id
                self.next_id += 1
            else:
                user_id = self.name2idx[username]
            user_state['id'] = user_id
            self.user[user_id].update_user_state(user_state)
