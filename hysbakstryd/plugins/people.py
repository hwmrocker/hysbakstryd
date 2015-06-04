"""
The people plugin!

Will make new People! HAHA!
"""

import random
from . import Plugin, logger

import config


class PeoplePlugin(Plugin):

    def connect(self, client):
        v = client.vars
        v['on_board'] = []
        v['people_transported'] = 0

    def initialize(self, game):
        super().initialize(game)

        self._person_wants_to = {}

        game.world_state['waiting_up'] = {i: [] for i in range(10)}
        game.world_state['waiting_down'] = {i: [] for i in range(10)}
        game.world_state['people_transported'] = 0

    def at_movement_open(self, client, level):
        """Client stopped in level `level`, so check whether people want to get on."""

        v = client.vars
        disembarking = [p for p in v['on_board'] if p['wants_to'] == level]
        self.emit(client, 'people_disembark', disembarking)
        logger.info("disembarking: {}".format(disembarking))
        on_board = [p for p in v['on_board'] if p['wants_to'] != level]
        v['people_transported'] += len(disembarking)
        self.game.world_state['people_transported'] += len(disembarking)

        if v['direction'] == 'up':
            waiting_here = self.game.world_state['waiting_up'][level]
        else:
            waiting_here = self.game.world_state['waiting_down'][level]

        # We want maximum 4 people
        while len(on_board) < 4 and waiting_here:
            p = waiting_here.pop(0)
            if p in self._person_wants_to:
                p['wants_to'] = self._person_wants_to[p]
                del self._person_wants_to[p]
            else:
                # this is just a guard against a restarted server and shouldn't happen
                logger.warn('  person not found in _wants_to: {}'.format(p))
                if p['direction'] == 'up':
                    p['wants_to'] = random.randint(level + 1, 9)
                else:
                    p['wants_to'] = random.randint(0, level - 1)

            v['_resume_at'] += 3   # each boarding person takes 3 ticks to enter
            on_board.append(p)
            self.emit(client, 'person_boards', p)
            logger.info("getting on board", p)

        v['on_board'] = on_board

    @staticmethod
    def make_person_appear_with_model(p, entry_dist, go_to_dist):
        """Randomly make a person appear according to entry_dist, go_to_dist."""

        if random.random() > p:
            return False, -100, -100

        def choose_by_dist(dist):
            s = 0
            sum_dist = []
            for p in dist:
                s += p
                sum_dist.append(s)

            r = random.random()
            i = 0
            while r > sum_dist[i]:
                i += 1
            return i

        from_floor = choose_by_dist(entry_dist)
        to_floor = choose_by_dist(go_to_dist)
        while to_floor == from_floor:
            to_floor = choose_by_dist(go_to_dist)

        return True, from_floor, to_floor

    @staticmethod
    def appear_mode1():
        """Make people appear like in the morning: strong probability for entering at
        level 0, mainly going up."""

        p = 0.7
        entry_dist = [0.91] + [0.01] * 9
        go_to_dist = [0.1] * 10

        return PeoplePlugin.make_person_appear_with_model(p, entry_dist, go_to_dist)

    @staticmethod
    def appear_mode2():
        """Make people appear like during the day: strong movement inside the building,
        little to the outside.
        """

        p = 0.3
        entry_dist = [0.1] * 10
        go_to_dist = [0.1] * 10

        return PeoplePlugin.make_person_appear_with_model(p, entry_dist, go_to_dist)

    @staticmethod
    def appear_mode3():
        """Make people appear like in the evening: strong outwards movement, little else."""

        p = 0.7
        entry_dist = [0.1] * 10
        go_to_dist = [0.91] + [0.01] * 9

        return PeoplePlugin.make_person_appear_with_model(p, entry_dist, go_to_dist)

    @staticmethod
    def appear_mode4():
        """Make people appear like in the night: little movement in all directions."""

        p = 0.05
        entry_dist = [0.1] * 10
        go_to_dist = [0.1] * 10

        return PeoplePlugin.make_person_appear_with_model(p, entry_dist, go_to_dist)

    def sample_modes(self, time_of_day):
        """Sample the separate LERPs for the four modes for the given time of day.

        Return value are four floats that indicate the part of each sample function of
        the total, and as such the sum over the return value is always 1.
        Except if not 0 <= x <= 1, then you'll get None.
        """

        # support values for our lerp basis -- make sure that the y values add up to 1
        support_points = [
            (0,    0, 0, 0, 1),
            (0.3,  0, 0, 0, 1),  # ~  7:30
            (0.33, 1, 0, 0, 0),  # ~  8:00
            (0.40, 1, 0, 0, 0),  # ~  9:30
            (0.42, 0, 1, 0, 0),  # ~ 10:00
            # (0.5,  0, 1, 0, 0),  #   12:00  not necessary
            (0.73, 0, 1, 0, 0),  # ~ 17:30
            (0.75, 0, 0, 1, 0),  #   18:00
            (0.78, 0, 0, 1, 0),  #   18:45
            (0.82, 0, 0, 0, 1),  # ~ 19:30
            (1,    0, 0, 0, 1),
        ]
        # yes, these numbers mean that more people flow into the building than out of it
        # DEAL WITH IT!
        ranges = []
        last_val = support_points[0]
        for cur_val in support_points[1:]:
            # great fun:
            ranges.append(tuple(
                (last_val[i], cur_val[i]) for i in range(5)
            ))
            last_val = cur_val

        for xs, y0s, y1s, y2s, y3s in ranges:
            if xs[0] <= time_of_day <= xs[1]:   # both sides are inclusive because the values are the same at the ends anyway
                # now interpolate between the endpoints
                t = (time_of_day - xs[0]) / (xs[1] - xs[0])
                # four times:
                return(
                    (1 - t) * y0s[0] + t * y0s[1],
                    (1 - t) * y1s[0] + t * y1s[1],
                    (1 - t) * y2s[0] + t * y2s[1],
                    (1 - t) * y3s[0] + t * y3s[1],
                )

        return None

    def sample_combined(self, time_of_day):
        """
        Sample the combined mode function as defined in the table and return a person (or not).
        """
        y0, y1, y2, y3 = self.sample_modes(time_of_day)
        px = random.random()
        ys = [y0, y0 + y1, y0 + y1 + y2, y0 + y1 + y2 + y3]
        modes = [PeoplePlugin.appear_mode1, PeoplePlugin.appear_mode2, PeoplePlugin.appear_mode3, PeoplePlugin.appear_mode4]

        for y, mode in zip(ys, modes):
            if px < y:
                return mode()

    def tick(self, time, clients):
        """Generate new people if necessary. NEW PEOPLE, HAHAHAHA!"""

        # the number of new people appearing
        num_p = len(clients) * config.plugins.people.people_appear_per_elevator_shaft

        while random.random() < num_p:
            num_p -= 1
            levels_with_space = [l for l in range(10)
                if ((len(self.game.world_state['waiting_up'][l]) +
                     len(self.game.world_state['waiting_down'][l])) < config.plugins.people.max_people_waiting_per_level)]
            # only spawn new people if there is enough room in the lobby
            if not levels_with_space:
                break

            generated, appears_in, wants_to = sample_combined(self.time_of_day(time))

            # https://www-genesis.destatis.de/genesis/online/data?operation=abruftabelleBearbeiten&levelindex=2&levelid=1433444898972&auswahloperation=abruftabelleAuspraegungAuswaehlen&auswahlverzeichnis=ordnungsstruktur&auswahlziel=werteabruf&selectionname=12612-0001&auswahltext=&werteabruf=Werteabruf
            if random.random() < 349820 / 682069:
                p_type = 'm'
            else:
                p_type = 'f'

            # https://www-genesis.destatis.de/genesis/online/data?operation=abruftabelleBearbeiten&levelindex=2&levelid=1433445078151&auswahloperation=abruftabelleAuspraegungAuswaehlen&auswahlverzeichnis=ordnungsstruktur&auswahlziel=werteabruf&selectionname=12111-0002&auswahltext=&werteabruf=Werteabruf
            # 1 984 523 + 2 025 183 + 6 795 585 + 2 329 061 = 7 018 352
            if random.random() < 7018352 / 80219695:
                p_type += '_child'

            if random.random() < 0.001:
                p_type = 'dog'

            person = {
                'direction': 'up' if wants_to > appears_in else 'down',
                'appeared_time': time,
                'type': p_type
            }

            self._person_wants_to[person] = wants_to

            if person['direction'] == 'up':
                self.game.world_state['waiting_up'][appears_in].append(person)
            else:
                self.game.world_state['waiting_down'][appears_in].append(person)
            self.emit(None, 'person appeared', person)



def test_generate():

    p = PeoplePlugin()

    # print(p.sample_combined(0.5))

    import math
    def time_from_frac(x):
        min_frac, hour = math.modf(x * 24)
        return '{:2d}:{:02d}'.format(
            int(hour),
            int(min_frac * 60),
        )

    ct = 0
    in_ = 0
    out_ = 0

    for i in range(1440):
        x = i / 1440
        appeared, from_, to_ = p.sample_combined(x)
        if appeared:
            ct += 1
            if from_ == 0:
                in_ += 1
            elif to_ == 0:
                out_ += 1
            print('{}: {} -> {}'.format(time_from_frac(x), from_, to_))
        else:
            print(time_from_frac(x))

    print('generated: {}\n  in:  {}\n  out: {}'.format(ct, in_, out_))
