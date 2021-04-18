from util.util import random, Loading, duration_strf
from util.path import route
from discord.ext.commands import Converter
import discord
import core
import asyncio


SELL_DIVIDEND = 3.5


class Types:
    TOOL = "Tool"
    COLLECTABLE = "Collectable"
    UNOBTAINABLE = "Unobtainable"
    POWERUP = "Power-up"
    CRATE = "Crate"
    FISH = "Fish"


class Item:
    def __init__(self, **data):
        self.id = data.get("id")
        self.name = data.get("name")
        self.plural = data.get("plural", None if not self.name else self.name+'s')
        self.emoji = data.get("emoji", '').strip()
        self.brief = data.get("brief", desc := data.get("description"))
        self.description = desc or "No description provided."
        self.price = data.get("price", 0)
        self.sell = int(self.price/SELL_DIVIDEND)
        self.usable = data.get("usable", data.get("useable", True))
        self.useable = self.usable  # alias because i commonly misspell usable
        self.buyable = data.get("buyable", True)
        self.sellable = data.get("sellable", True)
        self.giftable = data.get("giftable", True)
        self.dispose = data.get("dispose", True)  # whether or not to discard when used
        self.use_multiple = data.get("use_multiple", True)
        self.type = data.get("type", "Unknown")
        self.usage = data.get("usage")  # usage callback
        self.default = data.get("default", 0)  # starting amount, should usually never be used
        self.remover = data.get("remover")

        # round (trunc*) the price AFTERWARDS
        self.price = int(self.price)

    def __str__(self):
        if self.emoji == '':
            return self.name
        return f'{self.emoji} {self.name}'

    @property
    def plural_str(self):
        if self.emoji == '':
            return self.plural
        return f'{self.emoji} {self.plural}'

    def quantitize(self, quantity):
        if quantity == 1:
            name = f"an " if any(self.name.startswith(vowel) for vowel in "aeiou") else "a "
            name += f"**{self!s}**"
        else:
            name = f"{quantity:,} **{self.plural_str}**"
        return name

    def callback(self, func):
        # deco as a shortcut
        self.usage = func
        return func

    def remove(self, func):
        # deco as a shortcut
        self.remover = func
        return func


def Fish(**kwargs):
    """ Wrapper for Item that multiplies the sell value by 3.5, and makes it of type fish """
    kwargs["price"] *= SELL_DIVIDEND
    kwargs.update({
        "usable": kwargs.get("usable", False),
        "buyable": False,
        "type": Types.FISH
    })
    return Item(**kwargs)


class ItemUsageError(Exception):
    pass


class ItemUsageFailure(Exception):
    pass


class ItemRemovalFailure(Exception):
    pass


class Items:
    @classmethod
    def all(cls) -> list:
        return [
            getattr(cls, attr)
            for attr in dir(cls)
            if isinstance(getattr(cls, attr), Item)
        ]

    fishing_pole = Item(
        id="fishing_pole",
        name="Fishing Pole",
        emoji="<:fishing_pole:829828732645933096>",
        brief="Unlocks the `fish` command.",
        description="Unlocks the `fish` command - fish for fish; maybe even shrimp, and sell them for more shrimp.",
        dispose=False,
        use_multiple=False,
        price=9000,
        type=Types.TOOL
    )

    @fishing_pole.callback
    async def _use_fishing_pole(self, ctx, _):
        # let's just invoke the fish command
        ctx.command = ctx.bot.get_command("fish")
        await ctx.bot.handler.instantiate_command(ctx)

    clover = Item(
        id="clover",
        name="Clover",
        emoji="<:clover:829174085602508850>",
        brief="Increases luck in the casino.",
        description="Increases luck when using casino commands. This must be used in order to activate it.",
        use_multiple=False,
        price=15000,
        type=Types.POWERUP
    )

    @clover.callback
    async def _use_clover(self, ctx, _):
        async with Loading(ctx, "Using your clover..."):
            await asyncio.sleep(random(1.5, 3.))
        await ctx.send("idiot")


    @staticmethod
    async def _initiate_crate_callback(ctx, item, amount):
        _ = await ctx.send(
            core.LOADING + (
                f" Opening your {item}..."
                if amount == 1 else
                f" Opening {amount} {item.plural_str}..."
            )
        )

        return _, item.quantitize(amount)

    basic_crate = Item(
        id="basic_crate",
        name="Basic Crate",
        description="The most basic type of crate. Gives minimal prizes.",
        price=1050,
        buyable=False,
        type=Types.CRATE
    )

    @basic_crate.callback
    async def _use_basic_crate(self, ctx, item: Item, amount):
        _, name = await self._initiate_crate_callback(ctx, item, amount)

        await asyncio.sleep(random(1., 2.))

        _profit = 0
        _golden_profit = 0
        for _i in range(amount):
            _profit += random(95, 650)
            if random() < 0.002:
                _golden_profit += 1

        await ctx.bot.db.add("users", "shrimp", ctx.author, _profit)
        await ctx.bot.db.add("users", "golden_shrimp", ctx.author, _golden_profit)
        await ctx.maybe_edit(_, (
            f"Opened {name}\n"
            f"{core.SHRIMP} +{_profit:,} shrimp\n" + (
                f"{core.GOLDEN_SHRIMP} +{_golden_profit:,} golden shrimp"
                if _golden_profit > 0 else ''
            )
        ), allowed_mentions=discord.AllowedMentions.none())

    uncommon_crate = Item(
        id="uncommon_crate",
        name="Uncommon Crate",
        description="An uncommon crate. Can give XP.",
        price=round(2300*3.5),  # Will sell for 2,300
        buyable=False,
        type=Types.CRATE
    )

    @uncommon_crate.callback
    async def _use_uc_crate(self, ctx, item: Item, amount):
        _, name = await self._initiate_crate_callback(ctx, item, amount)

        await asyncio.sleep(random(1., 2.))

        _xp = 0
        _profit = 0
        _golden_profit = 0
        for _i in range(amount):
            _profit += random(460, 1750)
            if random() < 0.002:
                _golden_profit += 1
            if random() < 0.13:
                _xp += random(30, 80)

        await ctx.bot.db.add("users", "shrimp", ctx.author, _profit)
        await ctx.bot.db.add("users", "golden_shrimp", ctx.author, _golden_profit)
        await ctx.bot.db.add_xp(ctx.author, _xp)
        await ctx.maybe_edit(_, (
                f"Opened {name}\n"
                f"{core.SHRIMP} +{_profit:,} shrimp\n" + (
                    f"{core.GOLDEN_SHRIMP} +{_golden_profit:,} golden shrimp\n"
                    if _golden_profit > 0 else ''
                ) + (
                    f"{core.ARROW} +{_xp:,} XP"
                    if _xp > 0 else ''
                )
        ), allowed_mentions=discord.AllowedMentions.none())


    lock = Item(
        id="lock",
        name="Lock",
        emoji="<:lock:830154620483010571>",
        description="Use this to prevent others from robbing you.",
        price=5000,
        use_multiple=False,
        dispose=True,
        type=Types.TOOL
    )

    @lock.callback
    async def _use_lock(self, ctx, _):
        if await ctx.db.get("users", ctx.author, "locked"):
            await ctx.send("Your lock is already active.")
            raise ItemUsageFailure()

        await ctx.db.set("users", "locked", ctx.author, True)
        await ctx.send(f"{_.emoji} Your shrimp stash is now locked - but will break on the next attempted robbery on you.")

    @lock.remove
    async def _remove_lock(self, ctx, _):
        if not await ctx.db.get("users", ctx.author, "locked"):
            await ctx.send("You don't have a lock active.")
            raise ItemRemovalFailure()

        await ctx.db.set("users", "locked", ctx.author, False)
        await ctx.send("Removed your lock. Others can steal from you without problem now.")

    lifesaver = Item(
        id="lifesaver",
        name="Lifesaver",
        emoji="<:lifesaver:830489895310852107>",
        brief="Having these will save your life, if you ever die.",
        description="Having these will save your life, if you ever die. Will be consumed automatically, no usage is necessary.",
        price=15000,
        type=Types.POWERUP,
        usable=False
    )

    potion = Item(
        id="potion",
        name="Potion",
        emoji="<:potion:832384233896280104>",
        brief="Drink these for a small XP boost.",
        description="Drink these for a small XP boost. Be careful - you can die while drinking this potion!",
        price=30000,
        type=Types.POWERUP,
        use_multiple=False
    )

    @potion.callback
    async def _use_potion(self, ctx, item):
        no_mention = discord.AllowedMentions.none()
        _ = await ctx.send(f"{core.LOADING} Drinking your potion...")
        await asyncio.sleep(random(1., 2.4))
        if random() < 0.05:
            await ctx.db.die(ctx.author, _start_reason := "Your potion was actually poison, and you poisoned yourself.")
            return await ctx.maybe_edit(_, f"{_start_reason} You died.", allowed_mentions=no_mention)

        _gain = random(20, 50)
        await ctx.db.add_xp(ctx.author, _gain)
        await ctx.maybe_edit(_, f"{item.emoji} You drank your potion and gained **{_gain} XP**.")


    coffee = Item(
        id="coffee",
        name="Coffee",
        emoji="<:coffee:830252850860916767>",
        brief="Drink these to boost your XP multiplier.",
        description=(
            "Drink these to boost your XP multiplier. "
            "Be careful though - there's a chance that you'll drink too much coffee "
            "and overdose on caffeine... and die."
        ),
        price=16000,
        type=Types.POWERUP,
        use_multiple=False
    )

    @coffee.callback
    async def _use_coffee(self, ctx, item):
        no_mention = discord.AllowedMentions.none()
        _ = await ctx.send(f"{core.LOADING} Drinking your coffee...")
        await asyncio.sleep(random(1., 2.4))
        if random() < 0.12:
            await ctx.db.die(ctx.author, _start_reason := "You drank a little too much coffee today and overdosed on caffeine.")
            return await ctx.maybe_edit(_, f"{_start_reason} You died.", allowed_mentions=no_mention)
        _profit = random(.01, .06)
        await ctx.db.add("users", "xp_multiplier", ctx.author, _profit)
        await ctx.maybe_edit(_, (
            f"{item.emoji} **Drank a cup of coffee**\n"
            f"Gained a **{_profit*100:.2f}%** XP multiplier"
        ), allowed_mentions=no_mention)

    potato = Item(
        id="potato",
        name="Potato",
        plural="Potatoes",
        emoji="<:potato:831357273758105620>",
        description="Mmm... potatoes.",
        price=100,
        type=Types.COLLECTABLE,
        usable=False
    )

    shield = Item(
        id="shield",
        name="Shield",
        emoji="🛡",
        brief="Use these for more protection against robs.",
        description=(
            "When these shields are used (activated), for 2-4 hours, when "
            "people try robbing you, they will have a 50% higher chance of failing, and "
            "if they do manage to rob you, they will only get 50% of their payouts."
        ),
        price=215000,
        type=Types.POWERUP,
        use_multiple=False
    )

    @shield.callback
    async def _use_shield(self, ctx, sh: Item):
        if ctx.unix <= await ctx.db.get("users", ctx.author, "shield_active"):
            await ctx.send("Your shield is already active.")
            raise ItemUsageFailure()
        _ = await ctx.send(f"{sh.emoji} Using your shield...")
        await asyncio.sleep(hours := random(2., 4.))
        seconds = round(hours * 3600)
        from_now = ctx.unix + seconds
        await ctx.db.set("users", "shield_active", ctx.author, from_now)
        await ctx.maybe_edit(
            _, f"{sh.emoji} You activated your shield and will have extra protection "
               f"from robs for **{duration_strf(seconds, 2)}**.",
            allowed_mentions=discord.AllowedMentions.none()
        )

    @shield.remove
    async def _remove_shield(self, ctx, sh: Item):
        if ctx.unix > await ctx.db.get("users", ctx.author, "shield_active"):
            await ctx.send("You don't have an active shield.")
        await ctx.db.set("users", "shield_active", ctx.author, 0)
        await ctx.send(f"{sh.emoji} Successfully de-activated your shield.")


    fish = Fish(
        id="fish",
        name="Fish",
        plural="Fish",
        emoji="🐟",
        description="A normal fish. Very common in the ocean.",
        price=100
    )

    angel_fish = Fish(
        id="angel_fish",
        name="Angel Fish",
        plural="Angel Fish",
        emoji="🐠",
        description="An angel fish - quite large.",
        price=200
    )

    blow_fish = Fish(
        id="blow_fish",
        name="Blow Fish",
        plural="Blow Fish",
        emoji="🐡",
        description="Blow fish. Pufferfish inherit from this fish.",
        price=400
    )

    crab = Fish(
        id="crab",
        name="Crab",
        emoji="🦀",
        description="Snappity snap snap",
        price=600
    )

    lobster = Fish(
        id="lobster",
        name="Lobster",
        emoji="🦞",
        description="tasty...",
        price=850
    )

    dolphin = Fish(
        id="dolphin",
        name="Dolphin",
        emoji="🐬",
        description="Are dolphins fish?",
        price=1050
    )

    shark = Fish(
        id="shark",
        name="Shark",
        emoji="🦈",
        description="A pretty deadly \"fish\". I don't know if these are considered fish.",
        price=1300
    )

    octopus = Fish(
        id="octopus",
        name="Octopus",
        plural="Octopuses",
        emoji="🐙",
        description="Yes, it's octopuses, not octopi",
        price=2000
    )

    whale = Fish(
        id="whale",
        name="Whale",
        emoji="🐳",
        description="This is definitely not a fish. But, it's a whale, and that's all that matters.",
        price=3200
    )

    vibe_fish = Fish(
        id="vibe_fish",
        name="Vibe Fish",
        plural="Vibe Fish",
        emoji="<a:vibe_fish:829894243522707457>",
        description="<a:vibe_fish:829894243522707457>  ｖｉｂｅ",
        usable=True,
        dispose=False,
        use_multiple=False,
        price=7200
    )

    @vibe_fish.callback
    async def _use_vibe_fish(self, ctx, _):
        await ctx.send(_.emoji)

    amogus = Item(
        id="amogus",
        name="Amogus",
        plural="Amoguses",
        emoji="<:amogus:829532469879373845>",
        brief="Get out of my head.",
        description="I can't take this anymore, get out of my fucking head.",
        price=100000,
        type=Types.COLLECTABLE,
        use_multiple=False
    )

    @amogus.callback
    async def _use_amogus(self, ctx, _):
        _file = discord.File(route("assets", "sus.png"))
        await ctx.send(file=_file)

    fiji_water = Item(
        id="fiji_water",
        name="Fiji Water",
        emoji="<a:fijiwater:831209369432490074>",
        description="Rich people water™",
        price=256000,
        type=Types.COLLECTABLE,
        use_multiple=False,
        buyable=False
    )

    @fiji_water.callback
    async def _use_fiji_water(self, ctx, __):
        _ = await ctx.send(f"{core.LOADING} Drinking your Fiji™ Water...")
        await asyncio.sleep(random(2., 4.))
        await ctx.db.add("users", "xp_multiplier", ctx.author, profit := random(.5, .8))
        await ctx.maybe_edit(_, f"{__.emoji} Mmm, you drank your Fiji™ Water and gained a **{profit*100:.2f}%** XP Multiplier.",
                             allowed_mentions=discord.AllowedMentions.none())

    cannot_steal = Item(
        id="cannot_steal",
        name="Cannot-be-stolen-from",
        emoji="❌",
        description="Having this item means that you cannot be stolen from.",
        buyable=False,
        sellable=False,
        usable=False,
        giftable=False,
        type=Types.POWERUP
    )


def get_item(item_id):
    for _item in Items.all():
        if _item.id == item_id:
            return _item
    return


def query_item(query):
    query = query.lower().strip()
    if item := get_item(query):
        return item

    for item in Items.all():
        if item.name.lower() == query:
            return item
        elif item.id.lower() == query:
            # should've been addressed already but oh well
            return item
        elif len(query) >= 3 and (
            query in item.name.lower() or
            query in item.id.lower()
        ):
            return item
    return


ITEMS_INST = Items()


async def use_item(callback, *args):
    await callback(ITEMS_INST, *args)


async def remove_item(ctx, item):
    await item.remover(ITEMS_INST, ctx, item)


async def add_items_into_database(pool):
    """ We don't have to worry about SQL injections here """
    await pool.execute(";".join(f"ALTER TABLE items ADD COLUMN IF NOT EXISTS \"{_.id}\" bigint NOT NULL DEFAULT {_.default}" for _ in Items.all()))


def has_item(item: Item):
    """ A decorator for commands to check if the user has an item """
    async def _wrapper(ctx):
        if not (res := 0 < await ctx.db.get("items", ctx.author, item.id)):
            name = (f"an " if any(item.name.startswith(vowel) for vowel in "aeiou") else "a ") + f"**{item}**"
            await ctx.send(f"You need to own {name} in order to use this command." + (
                f" You can go buy one from the shop! (`{ctx.clean_prefix}shop`)" if item.buyable else ""
            ))
        return res

    return discord.ext.commands.check(_wrapper)


class ItemNotFound(Exception):
    pass


class ItemConverter(Converter, Item):
    async def convert(self, ctx, argument):
        if result := query_item(argument):
            return result
        raise ItemNotFound(f"Item \"{argument}\" not found.")
