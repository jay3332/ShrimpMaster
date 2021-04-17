import core
import random
import discord
import asyncio
from util import util, converters
from util.blackjack import Blackjack
from discord.ext import flags, commands


class RouletteBetConverter(converters.Converter):
    async def convert(self, ctx, argument):
        argument = argument.lower()
        if argument in ("red", "black", "r", "b", "green", "g", "odd", "even", "o", "e"):
            if len(argument) == 1:
                argument = {
                    "r": "red",
                    "b": "black",
                    "g": "green",
                    "o": "odd",
                    "e": "even"
                }[argument]
            return argument
        elif argument.isdigit() and 0 <= int(argument) <= 36:
            return int(argument)
        elif argument in ("high", "low", "h", "l"):
            return (1, 18) if argument.startswith("l") else (19, 36)
        await ctx.send(
            "Invalid roulette bet.\n"
            "You can choose a color (`red/black/green`), "
            "an exact number (`0 to 36`), `odd/even`, or `high`/`low`."
        )

        raise


class Casino(core.Cog):

    @core.command(
        name="roll",
        aliases=("bet", "gamble", "r"),
        bot_perms=("Send Messages", "Embed Links"),
        usage="<amount>",
        brief="Basic dice roll gamble. If you roll higher than the bot, you win.",
        description=(
            "Basic dice roll gamble. We each roll a pair of dice, whoever "
            "gets the higher sum wins! Your gambling multiplier adds on "
            "to the winning number."
        ),
        cooldown=(10, 5),
        examples=(
            "roll 10000",
            "roll all"
        )
    )
    @flags.add_flag("--rig", "--rigged", default=False, action='store_true')
    async def _roll(self, ctx, amount: converters.CasinoBet(), **options):
        await ctx.cd()

        _rigged = options.get("rig", options.get("rigged", False))
        if not await ctx.bot.is_owner(ctx.author):
            _rigged = False

        if not _rigged:
            rolls = random.choices(_range:=range(1, 7), k=2)
            my_rolls = random.choices(_range, k=2)
        else:
            rolls = (6, 6)
            my_rolls = (1, 1)

        winner = sum(rolls) > sum(my_rolls)
        draw = sum(rolls) == sum(my_rolls)

        def _format_rolls(r):
            return f"{core.DICE[r[0]]} {core.DICE[r[1]]}"

        embed = discord.Embed(timestamp=ctx.now)
        embed.set_author(name=f"{ctx.author.name}'s Gambling session", icon_url=ctx.avatar)

        if winner:
            _base_multiplier = util.random(.5, .95)
            profit = round(amount * _base_multiplier)
            await ctx.bot.db.add("users", "shrimp", ctx.author, profit)
            new = await ctx.bot.db.get("users", ctx.author, "shrimp")

            embed.colour = core.GREEN
            embed.add_field(name="Winner!", value=(
                f"You won {core.SHRIMP} **{profit:,} shrimp**. ({round(_base_multiplier*100)}%)\n"
                f"You now have {core.SHRIMP} **{new:,} shrimp**."
            ), inline=False)
        elif draw:
            embed.colour = core.YELLOW
            embed.add_field(name="Draw!", value=(
                f"Our sums are the same. Try again later..?"
            ), inline=False)
        else:
            await ctx.bot.db.add("users", "shrimp", ctx.author, -amount)
            new = await ctx.bot.db.get("users", ctx.author, "shrimp")

            embed.colour = core.RED
            embed.add_field(name="Loser!", value=(
                f"You lost {core.SHRIMP} **{amount:,} shrimp.**\n"
                f"You now have {core.SHRIMP} **{new:,} shrimp**."
            ), inline=False)

        embed.add_field(name=ctx.author.name + f" ({sum(rolls)})", value=_format_rolls(rolls))
        embed.add_field(name=ctx.bot.user.name + f" ({sum(my_rolls)})", value=_format_rolls(my_rolls))

        _ = await ctx.send(f"{core.LOADING} Rolling your dice... (Bet: {amount:,})", embed_perms=True)
        await asyncio.sleep(util.random(2., 4.))

        await ctx.maybe_edit(_, content="", embed=embed, allowed_mentions=discord.AllowedMentions.none())
        await ctx.bot.db.add_xp(ctx.author, util.random(2, 4))

    @core.group(
        name="slots",
        aliases=("slot", "sl"),
        bot_perms=("Send Messages", "Embed Links"),
        usage="<amount>",
        brief="Take a shot at the slot machine!",
        description=(
            "Take a shot at the slot machine! "
            "Different combinations have different multipliers. "
            "Your gambling multiplier will add on to that multiplier."
        ),
        cooldown=(15, 5),
        examples=(
            "slots 1000",
            "slots all"
        ),
        invoke_without_command=True
    )
    @core.check(bot_perms=("send_messages", "embed_links"))
    @flags.add_flag("--rig", "--rigged", default=False, action='store_true')
    async def _slots(self, ctx, amount: converters.CasinoBet(maximum=100000), **options):
        await ctx.cd()

        _rigged = options.get("rig", options.get("rigged", False))
        if not await ctx.bot.is_owner(ctx.author):
            _rigged = False

        _slots = random.choices(core.SLOTS, k=3) if not _rigged else ("f", "f", "f")
        _combo = "".join(sorted(_slots))
        _base_multiplier = 0

        sorted_keys = sorted(list(core.SLOTS_MULTIS), key=lambda k: len(k))
        for combo in sorted_keys:
            if combo in _combo:
                _base_multiplier = core.SLOTS_MULTIS[combo]

        emojis = " ".join(core.SLOTS_EMOJIS[_] for _ in _slots)
        emojis = f"**»** {emojis} **«**"

        embed = discord.Embed(timestamp=ctx.now, description=emojis)
        embed.set_author(name=f"{ctx.author.name}'s Slot Machine", icon_url=ctx.avatar)

        if _base_multiplier > 0:
            profit = round(amount*_base_multiplier)
            await ctx.bot.db.add("users", "shrimp", ctx.author, profit)

            embed.colour = core.GREEN
            _field_name = "Winner!"
            if _combo == 'ggg':
                _field_name = "**JACKPOT!!!**"
            elif _combo == "fff":
                _field_name = "**MEGA JACKPOT!!!!**"

            new = await ctx.bot.db.get("users", ctx.author, "shrimp")

            embed.add_field(name=_field_name, value=(
                f"You won {core.SHRIMP} **{profit:,} shrimp**. ({round(_base_multiplier*100):,}%)\n"
                f"You now have {core.SHRIMP} **{new:,} shrimp**."
            ))
        else:
            await ctx.bot.db.add("users", "shrimp", ctx.author, -amount)
            new = await ctx.bot.db.get("users", ctx.author, "shrimp")

            embed.colour = core.RED
            embed.add_field(name="Loser!", value=(
                f"You lost {core.SHRIMP} **{amount:,} shrimp**.\n"
                f"You now have {core.SHRIMP} **{new:,} shrimp**."
            ))

        _before_embed = discord.Embed(color=core.EMBED_COLOR, description=emojis)
        original = await ctx.send(f"{core.LOADING} Spinning the slot machine... (Bet: {amount:,})")

        await asyncio.sleep(util.random(1.5, 2.5))
        await ctx.maybe_edit(original, "", embed=_before_embed, allowed_mentions=discord.AllowedMentions.none())

        await asyncio.sleep(util.random(.5, 1.2))
        await ctx.maybe_edit(original, "", embed=embed, allowed_mentions=discord.AllowedMentions.none())

        await ctx.bot.db.add_xp(ctx.author, util.random(2, 4))

    @_slots.command(
        name="table",
        aliases=("t", "combos", "combinations", "info"),
        description="View all possible slot combinations.",
        cooldown=(2, 1)
    )
    async def _slots_table(self, ctx):
        _combos = core.SLOTS_MULTIS
        _emojis = core.SLOTS_EMOJIS

        def emoji_combo(key):
            return ' '.join(_emojis[k] for k in list(key))

        return await ctx.send("\n".join(
            f"**`{round(v*100):,}%`**  -  {emoji_combo(k)}"
            for k, v in _combos.items()
        ))

    @core.command(
        name="roulette",
        aliases=("rl", "roullete", "roullette"),
        bot_perms=("Send Messages", "Embed Links"),
        usage="<bet> <amount>",
        brief="Play a game roulette!",
        description=(
                "Play a game of roulette. Bet can be a color `red/black/green`, "
                "an exact number (0 to 36), `odd/even`, or `high`/`low`. Broad bets (color/high/low/odd/even) will win 100%, "
                "exact number bets will win 1500%, and landing on green (0) will win 3000%."
        ),
        cooldown=(20, 10),
        examples=(
                "roulette black 1000",
                "roulette 30 all"
        )
    )
    @core.check(bot_perms=("send_messages", "embed_links"))
    async def roulette(self, ctx, bet: RouletteBetConverter(), amount: converters.CasinoBet(maximum=200000)):
        await ctx.cd()
        color = random.choice(("red", "black"))
        value = random.randint(1, 36)
        if util.random() < 1/36:
            color, value = "green", 0

        won = False
        if isinstance(bet, str):
            if bet in ("red", "black", "green"):
                won = color == bet
            else:
                modulo_check = 1 if bet=='odd' else 0
                won = value % 2 == modulo_check
        elif isinstance(bet, int):
            won = value == bet
        elif isinstance(bet, tuple):
            won = bet[0] <= value <= bet[1]

        text = f"{core.ROULETTE_EMOJIS[color]} {color.title()} {value}"

        embed = discord.Embed(timestamp=ctx.now)
        embed.set_author(name=f"{ctx.author.name} - Roulette", icon_url=ctx.avatar)
        embed.add_field(name="Landed on", value=text, inline=False)

        if won:
            embed.colour = core.GREEN
            _field_title = "You won!"
            if color == "green":
                _field_title = "Roulette!"

            _base_multiplier = 1
            if color == "green":
                _base_multiplier = 30
            elif isinstance(bet, int):
                _base_multiplier = 15

            profit = round(amount * _base_multiplier)
            await ctx.db.add("users", "shrimp", ctx.author, profit)
            new = await ctx.bot.db.get("users", ctx.author, "shrimp")

            embed.add_field(name=_field_title, value=(
                f"You won {core.SHRIMP} **{profit:,} shrimp**.\n"
                f"You now have {core.SHRIMP} **{new:,} shrimp**."
            ))
        else:
            embed.colour = core.RED
            _field_title = "You lost!"

            await ctx.db.add("users", "shrimp", ctx.author, -amount)
            new = await ctx.bot.db.get("users", ctx.author, "shrimp")

            embed.add_field(name=_field_title, value=(
                f"You lost {core.SHRIMP} **{amount:,} shrimp**.\n"
                f"You now have {core.SHRIMP} **{new:,} shrimp**."
            ))

        _before_embed = discord.Embed(color=core.EMBED_COLOR, description=text)
        original = await ctx.send(f"{core.LOADING} Spinning the roulette wheel... (Bet amount: {amount:,})")

        await asyncio.sleep(util.random(1.5, 2.5))
        await ctx.maybe_edit(original, "", embed=_before_embed, allowed_mentions=discord.AllowedMentions.none())

        await asyncio.sleep(util.random(.5, 1.2))
        await ctx.maybe_edit(original, f"Your bet: {bet}", embed=embed, allowed_mentions=discord.AllowedMentions.none())

        await ctx.bot.db.add_xp(ctx.author, util.random(2, 5))


    @core.command(
        name="blackjack",
        aliases=("bj", '21'),
        bot_perms=("Send Messages", "Embed Links", "Add Reactions"),
        usage="<amount>",
        brief="Play a game of blackjack with me!",
        description=(
            "Play a game of blackjack with ShrimpMaster. "
            "Make sure you know how to play blackjack before using this command."
        ),
        cooldown=(7, 3),
        examples=(
            "blackjack 1000",
            "blackjack all"
        )
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "embed_links", "add_reactions"))
    async def _blackjack(self, ctx, *, amount: converters.CasinoBet(200, 200000)):
        await ctx.cd()
        await ctx.bot.db.add_xp(ctx.author, util.random(2, 4))

        _game = Blackjack(ctx, amount)
        await _game.start()


def setup(client):
    cog = Casino(client)
    client.add_cog(cog)
