from ._plugin_base import Plugin


class MovementPhase1(Plugin):

    # MOVEMENT RATE FOR AN ELEVATOR IN EACH GAME TICK
    RATE = 1  # levels per second

    MOVEMENT_PER_TICK = 0.1

    MAX_FLOOR = 9
    MIN_FLOOR = 0

    # how long does an elevator wait when the door is opened?
    WAITING_TIME = 10  # ticks
    """
    Movement mechanism.

    Put your name in `client.movement_paused_by` (a set) to stop the elevator from
    moving.

    Will emit these events:
     * `(moving, 'up'/'down')` when movement starts
     * `(at_level, x)` when entering level x (pause movement and 'snap' to a level if you
       want to stop there)
     * `(movement_open, level)` when door opened
     * `(movement_closed, level)` when door closed
     * `(movement_paused, )` when movement begins to be paused
     * `(movement_unpaused, )` when movement ends to be paused
     * `(stopped, )`, when the direction was set to 'halt'
    """

    def connect(self, client):
        v = client.vars
        v['levels'] = []
        v['level'] = 0.
        v['direction'] = 'halt'
        v['door'] = 'closed'
        v['movement_paused'] = False
        client.was_paused = True

    def at_movement_stopped(self, client, by=None, *args, **kwargs):
        # TODO: movement can be blocked by individual plugins
        self.client.vars['movement_paused'] = True

    def at_movement_started(self, client, by=None, *args, **kwargs):
        # TODO: remove only the one "by" that unblocks the movement
        self.client.vars['movement_paused'] = False

    # states
    def moving(self, client):
        c = client
        if client.vars['movement_paused']:
            if not client.was_paused:
                client.was_paused = True
                self.emit(client, 'movement_paused')
            return True
        else:
            if client.was_paused:
                client.was_paused = False
                self.emit(client, 'movement_unpaused')

        if client.vars['direction'] == 'halt':
            return True

        intlevel = round(c.vars['level'])
        if abs(c.vars['level'] - intlevel) > self.MOVEMENT_PER_TICK:
            intlevel = None

        if intlevel in c.vars['levels']:
            c.vars['level'] = intlevel
            c.vars['levels'].remove(intlevel)
            c.vars['_stopped_at'] = c.game.time
            return self.open_door
        else:
            if c.vars['direction'] == 'down':
                if c.vars['level'] <= self.MIN_FLOOR:
                    c.vars['level'] = self.MIN_FLOOR
                    return self._halt(c)
                else:
                    c.vars['level'] -= self.MOVEMENT_PER_TICK

            elif c.vars['direction'] == 'up':
                if c.vars['level'] >= self.MAX_FLOOR:
                    c.vars['level'] = self.MAX_FLOOR
                    return self._halt(c)
                else:
                    c.vars['level'] += self.MOVEMENT_PER_TICK

        print("  {} moved to {}".format(c.vars['username'], c.vars['level']))
        return True

    def open_door(self, c):
        """
        open door and wait
        """

        # can the user close the doors themselves? Should we guard against that?
        c.vars['door'] = 'open'
        c.movement_paused = False
        self.emit(c, "movement_open", c.vars['level'])
        return self.wait_for_people

    def wait_for_people(self, c):
        """
        Wait for the appropriate time until the doors close again
        """
        if c.vars['_stopped_at'] + self.WAITING_TIME >= c.game.time:
            return True

        return self.close_door

    def close_door(self, c):
        """
        close the, and check if and where to move
        """

        # can the user close the doors themselves? Should we guard against that?
        c.vars['door'] = 'closed'
        self.emit(c, "movement_closed", c.vars['level'])

        # This should rarely be the case, but we should check it
        if c.vars['level'] in c.vars['levels']:
            c.vars['levels'].remove(c.vars['level'])

        if not c.vars['levels']:
            return self._halt(c)

        if c.vars['direction'] == 'up' and all((l < c.vars['level'] for l in c.vars['levels'])):
            c.vars['direction'] = 'down'
        if c.vars['direction'] == 'down' and all((l > c.vars['level'] for l in c.vars['levels'])):
            c.vars['direction'] = 'up'
        return self._check_moving(c)

    # state _helper functions (this function returns suggested new states)

    def _check_moving(self, client):
        if client.vars['levels'] and client.vars['direction'] != "halt":
            client.movement_paused = False
            self.emit(client, 'moving', (client.vars['direction'], ))
            return self.moving
        return False

    def _halt(self, client):
        client.vars['direction'] = "halt"
        self.emit(client, 'stopped')
        return False

    # event listeners
    # no event listeners

    # commands
    def do_set_direction(self, client, direction=None):
        assert direction in ("up", "down", "halt")
        client.vars['direction'] = direction
        if direction == 'halt':
            self._halt(client)
        else:
            self._check_moving(client)
        return (self.moving, ), None, ("DIRECTION", client.vars['direction'])

    def do_set_level(self, client, level=None):
        assert 0 <= level < 10
        if level not in client.vars['levels']:
            client.vars['levels'].append(level)
            self._check_moving(client)
        return (self.moving, ), None,  ("LEVELS", client.vars['levels'])

    def do_reset_levels(self, client):
        client.var['levels'] = []
        return (), None, ("LEVELS", [])
