"""
The people plugin!

Will make new People! HAHA!
"""

import random
from . import Plugin


class PeoplePlugin(Plugin):

    def connect(self, client):
        v = client.vars
        v['on_board'] = []

    def initialize(self, game):
        super().initialize(game)

        game.world_state['waiting_up'] = {i: [] for i in range(10)}
        game.world_state['waiting_down'] = {i: [] for i in range(10)}

    def at_movement_open(self, client, level):
        """Client stopped in level `level`, so check whether people want to get on."""

        v = client.vars
        disembarking = [p for p in v['on_board'] if p['wants_to'] == level]
        self.emit(client, 'people_disembark', disembarking)
        print("disembarking:", disembarking)
        on_board = [p for p in v['on_board'] if p['wants_to'] != level]

        if v['direction'] == 'up':
            waiting_here = self.game.world_state['waiting_up'][level]
        else:
            waiting_here = self.game.world_state['waiting_down'][level]

        while len(on_board) <= 4 and waiting_here:
            p = waiting_here.pop(0)
            if p['direction'] == 'up':
                p['wants_to'] = random.randint(level + 1, 9)
            else:
                p['wants_to'] = random.randint(0, level - 1)
            v['_resume_at'] += 3
            on_board.append(p)
            self.emit(client, 'person_boards', p)
            print("getting on board", p)

        v['on_board'] = on_board

    def tick(self, time, clients):
        """Generate new people if necessary. NEW PEOPLE, HAHAHAHA!"""

        p = 0.5  # the probability for new people appearing

        # TODO: make everything parametric so we can simulate *REAL* people!
        while random.random() > p:
            appears_in = random.randint(0, 9)

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
