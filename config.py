"""
Configuration for Hysbakstryd server.
"""


class AttrDict(dict):
    """Access a dictionary like a dict OR like a class, and also act like a defaultdict with None as its factory.

    Nice little tool, taken from: http://stackoverflow.com/a/14620633
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__dict__ = self

    def __getattr__(self, item):
        try:
            return super().__getattribute__(item)
        except AttributeError:
            return None

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            return None

d = AttrDict

network = d({

})
        
game = d({
    'ticks_per_day': 120000,   # 20 real time minutes per game day, each hour is 50 seconds, 5000 ticks

})

game.ticks_per_hour = game.ticks_per_day / 24


# settings for plugins: if your plugin has settings, add an entry for your plugin here
plugins = d({
    
})

plugins.people = d({
    'people_appear_per_elevator_shaft': 0.1,
    'max_people_waiting_per_level': 20,
})


