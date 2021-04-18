import core
import discord
import asyncio
from util import util, converters, nets, items
from discord.ext import commands, flags


class Profit(core.Cog):

    @core.command(
        name="daily",
        alias="d",
        bot_perms=("Send Messages", "Embed Links"),
        brief="Claim your daily dose of shrimp.",
        description=(
            "Claim your daily dose of shrimp. "
            "Having a high daily streak means more shrimp and a higher chance"
            " to get a golden one."
        ),
        cooldown=86400,
        examples=("daily",)
    )
    @core.check(bot_perms=("send_messages", "embed_links"))
    async def _daily(self, ctx):

        await ctx.cd()
        _last_daily = await ctx.bot.db.get("users", ctx.author, "last_daily")

        embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        embed.set_author(name=f"Daily reward: {ctx.author}", icon_url=ctx.avatar)

        if ctx.unix-_last_daily <= 86400*1.5:
            await ctx.bot.db.add("users", "daily_streak", ctx.author, 1)
        else:
            await ctx.bot.db.set("users", "daily_streak", ctx.author, 0)

        _streak = await ctx.bot.db.get("users", ctx.author, "daily_streak")
        streak_benefit = util.get_daily_benefit(_streak) or 0

        profit = core.BASE_DAILY_PROFIT + streak_benefit
        await ctx.bot.db.add("users", "shrimp", ctx.author, profit)

        golden_chance = util.get_daily_golden_chance(_streak) or 0
        if util.random()<golden_chance:
            embed.add_field(name="You struck gold!", value=f"Nice job, you got a {core.GOLDEN_SHRIMP} Golden Shrimp today!")
            await ctx.bot.db.add("users", "golden_shrimp", ctx.author, 1)

        if _streak>0 or streak_benefit>0:
            embed.add_field(name="Daily Streak Benefit", value=f"Current streak: {_streak:,}\nExtra shrimp gained: {streak_benefit:,}", inline=False)

        await ctx.bot.db.set("users", "last_daily", ctx.author, ctx.unix)
        embed.description = f"Here's your daily reward of {core.SHRIMP} {profit:,} Shrimp. Enjoy!"
        await ctx.send(embed=embed, embed_perms=True)
        await ctx.bot.db.add_xp(ctx.author, util.random(2, 10))

    @core.command(
        name="weekly",
        alias="wk",
        bot_perms=("Send Messages", "Embed Links"),
        brief="Claim your weekly dose of shrimp.",
        description=(
            "Claim your weekly dose of shrimp. "
            "Having a high weekly streak means more shrimp and a higher chance"
            " to get a golden one."
        ),
        cooldown=86400*7,
        examples=("weekly",)
    )
    @core.check(bot_perms=("send_messages", "embed_links"))
    async def _weekly(self, ctx):

        await ctx.cd()
        _last_weekly = await ctx.bot.db.get("users", ctx.author, "last_weekly")

        embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        embed.set_author(name=f"Weekly reward: {ctx.author}", icon_url=ctx.avatar)

        if ctx.unix - _last_weekly <= 86400 * 8:  # why x8? because 7 days is a week, plus an extra day to keep the streak
            await ctx.bot.db.add("users", "weekly_streak", ctx.author, 1)
        else:
            await ctx.bot.db.set("users", "weekly_streak", ctx.author, 0)

        _streak = await ctx.bot.db.get("users", ctx.author, "weekly_streak")
        streak_benefit = util.get_weekly_benefit(_streak) or 0

        profit = core.BASE_WEEKLY_PROFIT + streak_benefit
        await ctx.bot.db.add("users", "shrimp", ctx.author, profit)

        golden_chance = util.get_weekly_golden_chance(_streak) or 0
        if util.random() < golden_chance:
            embed.add_field(name="You struck gold!",
                            value=f"Nice job, you got a {core.GOLDEN_SHRIMP} Golden Shrimp this week!")
            await ctx.bot.db.add("users", "golden_shrimp", ctx.author, 1)

        if _streak > 0 or streak_benefit > 0:
            embed.add_field(name="Weekly Streak Benefit",
                            value=f"Current streak: {_streak:,}\nExtra shrimp gained: {streak_benefit:,}", inline=False)

        await ctx.bot.db.set("users", "last_weekly", ctx.author, ctx.unix)
        embed.description = f"Here's your weekly reward of {core.SHRIMP} {profit:,} Shrimp. Enjoy!"
        await ctx.send(embed=embed, embed_perms=True)
        await ctx.bot.db.add_xp(ctx.author, util.random(5, 24))


    @core.command(
        name="catch",
        alias="c",
        bot_perms=("Send Messages", "Embed Links"),
        brief="Go into the sea and catch some shrimp!",
        description=(
            "Go into the sea and catch some shrimp. "
            "You'll catch more shrimp with a better net."
        ),
        cooldown=(40, 30),
        examples=("catch",)
    )
    @core.check(bot_perms=("send_messages", "embed_links"))
    async def _catch(self, ctx):

        await ctx.cd()
        embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        embed.set_author(name=str(ctx.author), icon_url=ctx.avatar)

        data = await ctx.bot.db.get("users", ctx.author)
        net = nets.get_net(data["net"])
        profit = net.catch_amount.random()

        _description = f'You use your {net.emoji} **{net.name}**.'
        if data['net'] == "none":
            _description = "You don't own a net yet, so you catch shrimp with your bare hands."

        if util.random()<net.fail_chance:
            embed.description="You didn't catch any shrimp. Sucks to be you."

        else:
            lines = []
            await ctx.bot.db.add("users", "shrimp", ctx.author, profit)

            if util.random()<net.golden_chance:
                golden_profit = net.golden_amount.random()
                lines.append(f"{core.GOLDEN_SHRIMP} Golden Shrimp: {golden_profit:,}")
                await ctx.bot.db.add("users", "golden_shrimp", ctx.author, golden_profit)

            lines.append(f"{core.SHRIMP} Shrimp: {profit:,}")
            embed.add_field(name="You caught", value="\n".join(lines))
            embed.description = _description

        _ = await ctx.send(f"{core.LOADING} Catching your shrimp...", embed_perms=True)
        await asyncio.sleep(util.random(2., 4.))

        await ctx.maybe_edit(_, "", embed=embed, allowed_mentions=discord.AllowedMentions.none())
        await ctx.bot.db.add_xp(ctx.author, util.random(5, 10))

    @core.command(
        name="crime",
        alias="illegal",
        brief="Commit a crime... but be careful.",
        description=(
            "Commit a crime to earn some shrimp, "
            "but be careful... You can get fined, "
            "or even die!"
        ),
        cooldown=(45, 30)
    )
    async def _crime(self, ctx):
        await ctx.cd()
        _ = await ctx.send(f"{core.LOADING} Commiting your crime...")
        if (outcome := util.random()) < 0.55:
            profit = util.random(100, 500)
            crime_message = util.choice(ctx.bot.crime_messages['good'])
            await ctx.db.add("users", "shrimp", ctx.author, profit)
            message = crime_message.format(f"{core.SHRIMP} **{profit} shrimp**")
        elif outcome < 0.9:
            fine = util.random(100, 500)
            crime_message = util.choice(ctx.bot.crime_messages['bad'])
            if await ctx.db.get("users", ctx.author, "shrimp") < fine:
                await ctx.db.die(ctx.author, "You died while commiting a crime.")
                crime_message += "\nSince you didn't have enough shrimp to pay the fine, you died instead."
            else:
                await ctx.db.add("users", "shrimp", ctx.author, -fine)
            message = crime_message.format(f"{core.SHRIMP} **{fine} shrimp**")
        else:
            message = util.choice(ctx.bot.crime_messages['die'])
            await ctx.db.die(ctx.author, "You died while commiting a crime.")

        await asyncio.sleep(util.random(2., 4.))
        await ctx.maybe_edit(_, message, allowed_mentions=discord.AllowedMentions.none())


    @core.command(
        name="invest",
        aliases=("in", "iv"),
        brief="Invest your shrimp into more shrimp..?",
        description=(
            "Use your shrimp to invest into even more shrimp. "
            "Be careful, you may fail your investment and lose your invested shrimp."
        ),
        cooldown=(60, 40),
        usage="<amount>",
        bot_perms=("Send Messages", "Embed Links")
    )
    @core.check(bot_perms=("send_messages", "embed_links"))
    @flags.add_flag("--rig", action="store_true", default=False)
    async def _invest(self, ctx, amount: converters.Investment(), **options):
        _multiplier = 0
        await ctx.cd()
        await ctx.bot.db.add_xp(ctx.author, util.random(5, 12))
        await ctx.bot.db.add("users", "shrimp", ctx.author, -amount)

        _rig = False
        if await ctx.bot.is_owner(ctx.author):
            _rig = options.get("rig", False)

        def _embed(_c=core.COLOR):
            __embed = discord.Embed(timestamp=ctx.now, color=_c)
            __embed.set_author(name=f"{ctx.author.name}'s Shrimp Investment", icon_url=ctx.avatar)
            return __embed

        _ = await ctx.send(f"{core.LOADING}")
        for __ in range(5):
            if util.random()>(
                .15 if not _rig else 0
            ):
                _multiplier += util.random(.14, .28)

                embed = _embed()
                embed.description = f"{core.LOADING} Investing..."
                embed.add_field(name="Earnings", value=(
                    f"{round(_multiplier * 100, 1):,}%\n"
                    f"({core.SHRIMP} {round(amount * _multiplier):,} shrimp)"
                ), inline=False)
                embed.add_field(name="Total Return", value=f"{core.SHRIMP} {round(amount * (1 + _multiplier)):,} shrimp")
                await ctx.maybe_edit(_, content="", embed=embed, allowed_mentions=discord.AllowedMentions.none())
            else:
                embed = _embed(core.RED)
                embed.description = "You failed to invest your shrimp properly."
                return await ctx.maybe_edit(_, content="", embed=embed, allowed_mentions=discord.AllowedMentions.none())
            await asyncio.sleep(2)

        _profit = round(amount * (1 + _multiplier))
        await ctx.bot.db.add("users", "shrimp", ctx.author, _profit)

        embed = _embed(core.GREEN)
        embed.description = f"Success! Your investment was successful."
        embed.add_field(name="Earnings", value=(
            f"{round(_multiplier * 100, 1):,}%\n"
            f"({core.SHRIMP} {round(amount * _multiplier):,} shrimp)"
        ), inline=False)
        embed.add_field(name="Total Return", value=f"{core.SHRIMP} {_profit:,} shrimp")
        await ctx.maybe_edit(_, content="", embed=embed, allowed_mentions=discord.AllowedMentions.none())


    @core.command(
        name="dive",
        alias="dv",
        brief="Take a dive into the sea to catch some shrimp!",
        description=(
            "Tired of using your net? Take a dive "
            "into the sea to catch some shrimp. Be careful though, "
            "as you might drown and lose your shrimp!"
        ),
        cooldown=(45, 25),
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    async def _dive(self, ctx):
        _ = await ctx.send(f"{core.LOADING} Attempting to dive into the sea...")
        await asyncio.sleep(util.random(1., 3.))
        if util.random() < 0.15:
            await ctx.cd()
            return await ctx.maybe_edit(
                _, content="Unlucky, you failed to dive.",
                allowed_mentions=discord.AllowedMentions.none()
            )
        profit = util.random(5, 30)
        await ctx.maybe_edit(_, content=f"You start off with {core.SHRIMP} **{profit} shrimp**.\n"
                                        f"Do you want to leave with this much, or do you want to dive deeper?\n"
                                        f"leave - `l`  |  dive - `d`",
                             allowed_mentions=discord.AllowedMentions.none())

        while True:
            try:
                _response = await ctx.bot.wait_for("message", timeout=20, check=lambda msg: (
                    msg.author.id == ctx.author.id and msg.channel.id == ctx.channel.id
                    and msg.content.lower() in ("leave", "l", "dive", "d")
                ))
            except asyncio.TimeoutError:
                await ctx.cd()
                return await ctx.send("Looks like you didn't respond, so you quit the dive. (You earned nothing)")
            _response = _response.content.lower()[0]
            if _response == "l":
                break

            if util.random()<0.52:
                profit += (gain := util.random(15, 45))
                await ctx.send(f"You dive deeper and collect another {core.SHRIMP} **{gain} shrimp**.\n"
                               f"You have now collected a total of **{core.SHRIMP} {profit:,} shrimp**.\n"
                               f"Do you want to leave now, or dive deeper?\n"
                               f"leave - `l`  |  dive - `d`")
                continue

            await ctx.cd()
            return await ctx.send(
                "You drowned. Although I revived you, "
                "I couldn't revive the shrimp you collected and therefore you earned nothing."
            )

        await ctx.cd()
        if util.random()<0.1:
            return await ctx.send("Too bad so sad, someone stole your shrimp, maybe because they were too hungry.")
        await ctx.bot.db.add_xp(ctx.author, util.random(2, 5))
        await ctx.bot.db.add("users", "shrimp", ctx.author, profit)
        await ctx.send(f"You leave with a total of {core.SHRIMP} **{profit:,} shrimp**. Congrats!")

    @staticmethod
    async def _do_fish_like(ctx, loading_message, other_loading_message, possible, no_fish_message, verb, field_verb, **options):
        await ctx.cd()
        _no_edit = False
        _iter = util.random(4, 6)
        if await ctx.bot.is_owner(ctx.author):
            _no_edit = options.get("no_edit", False)
            _iter = options.get("iter", _iter)
            if _iter == 0:
                _iter = util.random(4, 6)
        _no_mention = discord.AllowedMentions.none()
        _ = await ctx.send(loading_message)
        if not _no_edit:
            await asyncio.sleep(util.random(0.8, 2.))
            await ctx.maybe_edit(_, other_loading_message, allowed_mentions=_no_mention)
            await asyncio.sleep(util.random(2., 4.))

        fish = possible
        collected = {}

        def _render_text():
            if res := "\n".join(
                    f"{_fish} (x{collected.get(_fish, 0)})"
                    for _fish in list(fish) if _fish in list(collected) and _fish
            ):
                return res
            return "Nothing."

        _embed = discord.Embed(description=no_fish_message)
        for __ in range(_iter):
            _chosen = None
            _rand = util.random()
            for _item, chance in reversed(fish.items()):
                if _rand < chance:
                    _chosen = _item
                    break

            if _chosen is not None:
                collected.update({_chosen: collected.get(_chosen, 0) + 1})
                _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
                _embed.set_author(name=f"{ctx.author.name}: {verb}", icon_url=ctx.avatar)
                _embed.description = f"Sell worth: {core.SHRIMP} **{sum(i.sell * collected[i] for i in list(collected)):,}**"
                _embed.add_field(name=field_verb, value=_render_text())

                await ctx.db.add("items", _chosen.id, ctx.author, 1)
                if not _no_edit:
                    await ctx.maybe_edit(_, "", embed=_embed, allowed_mentions=_no_mention)
                    await asyncio.sleep(util.random(1., 1.3))

        _embed.colour = core.GREEN if collected else core.RED
        await ctx.db.add_xp(ctx.author, util.random(12, 20))
        await ctx.maybe_edit(_, "", embed=_embed, allowed_mentions=_no_mention)


    @core.command(
        name="fish",
        aliases=("cast", "fishingpole"),
        brief="Fish for fish, and sell them for shrimp.",
        description="Fish for fish - and sell them for shrimp. Because shrimp are clearly better than fish.",
        cooldown=(35, 25)
    )
    @flags.add_flag("--no-edit", action="store_true", default=False)
    @flags.add_flag("--iter", type=int, default=0)
    @commands.max_concurrency(1, commands.BucketType.user)
    @items.has_item(items.Items.fishing_pole)
    async def _fish(self, ctx, **options):
        """
        TODO: Implement foreign items
        TODO: Add loss of fishing pole, and a better implementation of "You caught no fish at all"
        """
        await self._do_fish_like(
            ctx,
            f"{core.LOADING} Casting your fishing pole...",
            f"{core.LOADING} Fishing for fish...",
            {
                None: 1,
                items.Items.fish: 0.7,
                items.Items.angel_fish: 0.45,
                items.Items.blow_fish: 0.25,
                items.Items.crab: 0.15,
                items.Items.lobster: 0.075,
                items.Items.dolphin: 0.03,
                items.Items.shark: 0.015,
                items.Items.lock: 0.01,
                items.Items.octopus: 0.004,
                items.Items.whale: 0.0015,
                items.Items.vibe_fish: 0.00025
            },
            "You caught no fish. Loser.",
            "Fishing",
            "Caught",
            **options
        )


    @core.command(
        name="steal",
        aliases=("rob", "ripoff"),
        usage="<user>",
        brief="Steal shrimp from others.",
        description="Desperate for shrimp? Look no further, this command is used to steal from others. Sneaky.",
        examples=("steal @Victim",),
        cooldown=(90, 60)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    async def _steal(self, ctx, *, user: converters.BetterMemberConverter()):
        """
        TODO: A small minigame at the beginning before robbing
        TODO: Add a chance for locks to fail.
        TODO: Notifications system
        """
        if await ctx.db.get("items", user, "cannot_steal") >= 1:
            return await ctx.send("You can't steal from that user.")

        if user == ctx.author:
            return await ctx.send("Sounds kinda cringe to steal from yourself")
        if user.bot:
            return await ctx.send("You can't steal from bots.")
        if (_user_shrimp := await ctx.db.get("users", user, "shrimp")) < 250:
            return await ctx.send(f"You can only rob from people with at least {core.SHRIMP} **250 shrimp**.")
        if (_author_shrimp := await ctx.db.get("users", ctx.author, "shrimp")) < 250:
            return await ctx.send(f"You need at least {core.SHRIMP} **250 shrimp** to steal from others.")

        await ctx.cd()
        shield_active = ctx.unix <= await ctx.db.get("users", user, "shield_active")

        if await ctx.db.get("users", user, "locked"):
            fine = max(250, round(util.random(.3, .75)*_author_shrimp))
            await ctx.db.set("users", "locked", user, False)
            await ctx.db.add("users", "shrimp", ctx.author, -fine)
            await ctx.db.notify(user, "Someone tried to rob you!", f"**{ctx.author.name}** ({ctx.author.mention}) tried to rob you in **{ctx.guild.name}**, but you had a padlock active.")
            return await ctx.send(f"That user has a lock active. Your rob failed and you lost {core.SHRIMP} **{fine:,} shrimp**.")

        _ = await ctx.send(f"{core.LOADING} Robbing {user.name}...")
        _rob_success_rate = core.BASE_ROB_SUCCESS
        if shield_active: _rob_success_rate /= 2
        if util.random() < _rob_success_rate:
            _percent = util.random(.2, .7)
            if shield_active: _percent /= 2
            _amount = int(_user_shrimp*_percent)
            await ctx.db.add("users", "shrimp", ctx.author, _amount)
            await ctx.db.add("users", "shrimp", user, -_amount)
            await ctx.db.notify(user, "You have been robbed!", f"**{ctx.author.name}** ({ctx.author.mention}) robbed {core.SHRIMP} **{_amount:,}** from you in **{ctx.guild.name}**!")
            message = f"You stole {core.SHRIMP} **{_amount:,} shrimp** ({round(_percent*100)}%) from **{user.name}**. Too bad for them."

        else:
            _percent = util.random(.2, .65)
            _fine = int(_author_shrimp*_percent)
            await ctx.db.add("users", "shrimp", ctx.author, -_fine)
            await ctx.db.add("users", "shrimp", user, _fine)
            await ctx.db.notify(user, "Someone tried to rob you!", f"**{ctx.author.name}** ({ctx.author.mention}) tried to rob you in **{ctx.guild.name}**, but got caught.")
            message = f"You were caught trying to steal shrimp from {user.name} and paid {core.SHRIMP} **{_fine:,} shrimp** to them. Lmao."

        await asyncio.sleep(util.random(1.5, 3.))
        await ctx.maybe_edit(_, message, allowed_mentions=discord.AllowedMentions.none())


def setup(client):
    cog = Profit(client)
    client.add_cog(cog)
