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

    def tick(self, time, clients):
        """Generate new people if necessary. NEW PEOPLE, HAHAHAHA!"""

        # the probability for new people appearing
        p = len(clients) * config.plugins.people.people_appear_per_elevator_shaft

        # TODO: make everything parametric so we can simulate *REAL* people!
        while random.random() > p:
            levels_with_space = [l for l in range(10)
                if ((len(self.game.world_state['waiting_up'][l]) +
                     len(self.game.world_state['waiting_down'][l])) < config.plugins.people.max_people_waiting_per_level)]
            # only spawn new people if there is enough room in the lobby
            if not levels_with_space:
                break
            appears_in = random.choice(levels_with_space)
            wants_to = random.randint(0, 9)
            while appears_in == wants_to:
                wants_to = random.randint(0, 9)
                
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
