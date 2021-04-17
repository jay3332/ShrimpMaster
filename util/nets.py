from .util import random as _random
from discord.ext.commands import Converter
from typing import Optional


class Range:
    def __init__(self, bounds, maybe_maximum=None):
        if maybe_maximum:
            bounds = (bounds, maybe_maximum)

        self.min = bounds[0]
        self.max = bounds[1]

    @property
    def range(self):
        return self.max - self.min

    def random(self):
        return _random(self.min, self.max)

    def has(self, amount):
        return self.min <= amount <= self.max

    def __contains__(self, item):
        return self.has(item)

    def __str__(self):
        if self.min != self.max:
            return f'{self.min:,} - {self.max:,}'
        return f'{self.min:,}'

    def __repr__(self):
        return f'Range({self.min}, {self.max})'


class Net:
    def __init__(self, **data):
        self.id = data.get("id")  # for db purposes
        self.name = data.get("name", "Unknown")
        self.description = data.get("description", "No description")
        self.level_requirement = data.get("level", 0)
        self.price = data.get("price", 0)
        self.emoji = data.get("emoji", "").strip()
        self.flag = data.get("flag", 0)

        # catch stats
        self.catch_amount = Range(data.get("amount", (0, 0)))
        self.fail_chance = data.get("fail", 0.)
        self.golden_chance = data.get("golden", 0.)
        self.golden_amount = Range(data.get("golden_amount", (0, 0)))

    def __str__(self):
        if self.emoji == '':
            return self.name
        return f'{self.emoji} {self.name}'


class Nets:
    none = Net(
        id="hand",
        name="Hand",
        emoji="✋",
        description="You don't have a net, so you use your hands.",
        level=0,
        price=0,
        amount=(2, 50),
        fail=0.3,
        golden=0,
        golden_amount=(0, 0),
        flag=1 << 0
    )
    plastic = Net(
        id="plastic",
        name='Plastic Net',
        description="Being lightweight, durable, and better than a basic net, I'd say a plastic net is pretty good.",
        emoji='',
        level=2,
        price=1250,
        amount=(12, 115),
        fail=0.28,
        golden=0.00075,
        golden_amount=(1, 1),
        flag=1 << 1
    )
    large = Net(
        id='large',
        name='Large Net',
        description='These nets can hold a lot more shrimp than the previous ones.',
        emoji='',
        level=5,
        price=3400,
        amount=(50, 175),
        fail=0.275,
        golden=0.001,
        golden_amount=(1, 1),
        flag=1 << 2
    )
    polished = Net(
        id='polished',
        name='Polished Net',
        description='A polished and shiny net.',
        emoji='',
        level=8,
        price=6600,
        amount=(80, 235),
        fail=0.27,
        golden=0.0015,
        golden_amount=(1, 1),
        flag=1 << 3
    )
    metal = Net(
        id='metal',
        name="Metal Net",
        description="This net is extremely durable. Maybe because it's made out of metal. Prone to rusting.",
        emoji='',
        level=14,
        price=15200,
        amount=(120, 300),
        fail=0.26,
        golden=0.0025,
        golden_amount=(1, 2),
        flag=1 << 4
    )
    electric = Net(
        id="electric",
        name="Electric Net",
        description="Ignore the fact that electricity does not go well with water.",
        emoji='',
        level=20,
        price=39500,
        amount=(160, 430),
        fail=0.25,
        golden=0.003,
        golden_amount=(1, 2),
        flag=1 << 5
    )
    titanium = Net(
        id="titanium",
        name="Titanium Net",
        description="This net is made out of pure titanium.",
        emoji='',
        level=34,
        price=69100,
        amount=(240, 665),
        fail=0.24,
        golden=0.005,
        golden_amount=(1, 3),
        flag=1 << 6
    )
    tungsten = Net(
        id="tungsten",
        name="Tungsten Net",
        description="This net is made out a tungsten, a pretty dense metal.",
        emoji='',
        level=51,
        price=104500,
        amount=(370, 820),
        fail=0.23,
        golden=0.0065,
        golden_amount=(1, 3),
        flag=1 << 7
    )
    radioactive = Net(
        id="radioactive",
        name="Radioactive Net",
        description="Radioactive??!?!",
        emoji='',
        level=75,
        price=234500,
        amount=(500, 1150),
        fail=0.21,
        golden=0.008,
        golden_amount=(1, 3),
        flag=1 << 8
    )
    plasma = Net(
        id="plasma",
        name="Plasma Net",
        description="This net is made from plasma.",
        emoji='',
        level=104,
        price=575000,
        amount=(765, 1450),
        fail=0.2,
        golden=0.0095,
        golden_amount=(1, 4),
        flag=1 << 9
    )

    @classmethod
    def all(cls) -> list:
        return sorted([
            getattr(cls, attr)
            for attr in dir(cls)
            if isinstance(getattr(cls, attr), Net)
        ], key=lambda _: _.flag)


def get_net(net_id) -> Optional[Net]:
    for _net in Nets.all():
        if _net.id == net_id:
            return _net
    return None


def query_net(name) -> Optional[Net]:
    name = name.lower()

    _by_id = get_net(name)
    if _by_id:
        return _by_id

    for _net in Nets.all():
        _name = _net.name.lower()
        _id = _net.id.lower()
        if _name == name:
            return _net
        elif len(name) > 3 and (name in _name or name in _id):
            return _net
    return None


def has_net(flag_value, net) -> bool:
    return (flag_value & net.flag) == net.flag


def list_nets(flag_value) -> list:
    return [net for net in Nets.all() if has_net(flag_value, net)]


class NetNotFound(Exception):
    pass


class NetConverter(Converter, Net):
    async def convert(self, ctx, argument):
        _net = query_net(argument)
        if not _net:
            raise NetNotFound(f'Net with name "{_net}" not found.')
        return _net
