"""
The people plugin!

Will make new People! HAHA!
"""

import random
from . import Plugin, logger


class PeoplePlugin(Plugin):

    def connect(self, client):
        v = client.vars
        v['on_board'] = []
        v['people_transported'] = 0

    def initialize(self, game):
        super().initialize(game)

        game.world_state['waiting_up'] = {i: [] for i in range(10)}
        game.world_state['waiting_down'] = {i: [] for i in range(10)}
        game.world_state['people_transported'] = 0

    def at_movement_open(self, client, level):
        """Client stopped in level `level`, so check whether people want to get on."""

        v = client.vars
        disembarking = [p for p in v['on_board'] if p['wants_to'] == level]
        self.emit(client, 'people_disembark', disembarking)
        logger.info("disembarking:", disembarking)
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
            if p['direction'] == 'up':
                p['wants_to'] = random.randint(level + 1, 9)
            else:
                p['wants_to'] = random.randint(0, level - 1)
            v['_resume_at'] += 3
            on_board.append(p)
            self.emit(client, 'person_boards', p)
            logger.info("getting on board", p)

        v['on_board'] = on_board

    def tick(self, time, clients):
        """Generate new people if necessary. NEW PEOPLE, HAHAHAHA!"""

        p = 0.5  # the probability for new people appearing
        max_people_per_level = 20

        # TODO: make everything parametric so we can simulate *REAL* people!
        while random.random() > p:
            levels_with_space = [l for l in range(10)
                if ((len(self.game.world_state['waiting_up'][l]) +
                    len(self.game.world_state['waiting_down'][l])) < max_people_per_level)]
            # only spawn new people if there is enough room in the lobby
            if not levels_with_space:
                break
            appears_in = random.choice(levels_with_space)
            wants_to = random.randint(0, 9)
            while appears_in == wants_to:
                wants_to = random.randint(0, 9)

            p_type = random.choice(['m', 'f', 'm_child', 'f_child'])

            if random.random() < 0.001:
                p_type = 'dog'

            person = {
                'direction': 'up' if wants_to > appears_in else 'down',
                'appeared_time': time,
                'type': p_type
            }

            if person['direction'] == 'up':
                self.game.world_state['waiting_up'][appears_in].append(person)
            else:
                self.game.world_state['waiting_down'][appears_in].append(person)
            self.emit(None, 'person appeared', person)
