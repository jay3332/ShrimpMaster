import math
import core
import typing
import discord
from discord.ext import flags
from util import converters, util, nets, paginators, items


class Stats(core.Cog):

    @core.command(
        name="shrimp",
        aliases=("s", "balance", "bal", "shrimps", "rank"),
        bot_perms=("Send Messages", "Embed Links"),
        usage="[user]",
        cooldown=(3, 1),
        brief="View how many shrimp you have.",
        description=(
            "View how many shrimp you have. You can"
            " supply a user to view their shrimp balance."
        ),
        examples=(
            "shrimp",
            "shrimp @Wumpus",
            "shrimp 414556245178056706"
        )
    )
    @core.check(bot_perms=("view_channel", "send_messages", "embed_links"))
    async def _shrimp(self, ctx, *, user: typing.Optional[converters.BetterMemberConverter] = None):

        await ctx.cd()
        user = user or ctx.author
        embed = discord.Embed(color=core.COLOR)
        embed.set_author(name=str(user), icon_url=user.avatar_url)

        data = await ctx.bot.db.get("users", user)
        _total_space = await ctx.bot.db.sum("users", user, "vault_space", "expanded_vault_space")
        _vault_ratio = data['vault'] / _total_space
        _percent = math.floor(_vault_ratio*1000)/10
        if math.floor(_percent) == _percent:
            _percent = math.floor(_percent)
        embed.add_field(name=f"{core.SHRIMP} Shrimp", value=f"{data['shrimp']:,}")
        embed.add_field(name=f"{core.GOLDEN_SHRIMP} Golden Shrimp", value=f"{data['golden_shrimp']:,}")
        embed.add_field(name=f"{core.VAULT} Shrimp Vault ({_percent}%)", value=(
            f"{core.SHRIMP} {data['vault']:,} shrimp / {_total_space:,}\n"
            f"{util.progress_bar(**core.PROGRESS_BAR, ratio=_vault_ratio, length=7)}"
        ), inline=False)
        if await ctx.db.get("factories", user, "is_active"):
            factory = await ctx.db.get_factory_info(user, ctx.unix)
            _percent = factory["shrimp"] / factory["capacity"]
            _until_full = (
                util.duration_strf(round(factory['time_until_full']), 1)+" until full"
                if factory['time_until_full']>0 else "Factory is full!"
            )
            embed.add_field(name=f"{core.FACTORY} ShrimpFactory™ ({_percent*100:.2f}%)", value=(
                f"{core.SHRIMP} {factory['shrimp']:,} / {factory['capacity']:,}\n"
                f"{core.GOLDEN_SHRIMP} {factory['golden_shrimp']:,} / {factory['golden_capacity']:,}\n"
                f"{_until_full}\n{util.progress_bar(**core.PROGRESS_BAR, ratio=_percent, length=7)}"
            ))

        rank = await util.get_shrimp_ranking(ctx.bot.db.pool, user)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=rank)
        embed.timestamp = ctx.now
        await ctx.send(embed)
        await ctx.bot.db.add_xp(ctx.author, 1)

    @core.command(
        name="level",
        aliases=("lvl", "lv", 'l'),
        bot_perms=("Send Messages", "Embed Links"),
        brief="View your current level.",
        description=(
            "View your current level and experience. "
            "As you level up, your global multiplier increases, "
            "and so does your profile rank. You will also unlock nets."
        ),
        examples=(
            "level",
            "level @Person"
        ),
        usage="[user]",
        cooldown=(3, 1)
    )
    @core.check(bot_perms=("view_channel", "send_messages", "embed_links"))
    async def _level(self, ctx, *, user: typing.Optional[converters.BetterMemberConverter] = None):

        await ctx.cd()
        user = user or ctx.author

        embed = discord.Embed(timestamp=ctx.now, color=core.COLOR)
        embed.set_author(name=str(user), icon_url=user.avatar_url)

        _level, _xp = await ctx.bot.db.get_level(user)
        _multiplier = -1 + await ctx.db.get("users", user, "xp_multiplier")
        _req = core.LEVEL_FORMULA(_level)
        _percent = round((_ratio:=_xp/_req)*100, 1)
        _bar = util.progress_bar(**core.PROGRESS_BAR, ratio=_ratio, length=8)

        if _multiplier > 0:
            embed.add_field(
                name="XP Multiplier",
                value=f"{_multiplier*100:.2f}%",
                inline=False
            )
        embed.add_field(name=f"Level {_level:,}", value=f"{_xp:,}/{_req:,} XP ({_percent}%)\n\n{_bar}")

        await ctx.send(embed, embed_perms=True)
        await ctx.bot.db.add_xp(ctx.author, 1)


    @core.command(
        name="leaderboard",
        aliases=("top", "lb", "rich"),
        bot_perms=("Send Messages", "Embed Links"),
        brief="View the people in your server with the most shrimp.",
        description=(
            "View the people in your server with the most shrimp. "
            "Can be switched to a global leaderboard by adding the `--global` flag."
        ),
        examples=(
            "leaderboard",
            "leaderboard --global"
        ),
        cooldown=(5, 1)
    )
    @flags.add_flag("--global", "--g", action="store_true", default=False)
    @flags.add_flag("--large", "--l", action="store_true", default=False)
    @flags.add_flag("--vault", "--v", action="store_true", default=False)
    @flags.add_flag("--pocket", "--p", action="store_true", default=False)
    @core.check(bot_perms=("view_channel", "send_messages", "embed_links"))
    async def _leaderboard(self, ctx, **options):
        await ctx.cd()
        __v = options.get("vault", options.get("v")) or False
        __p = options.get("pocket", options.get("p")) or False

        _q = (
            "select user_id, shrimp total from users where shrimp > 0 order by total desc" if __p else
            "select user_id, vault total from users where vault > 0 order by total desc" if __v else
            "select user_id, shrimp + vault total from users where shrimp + vault > 0 order by total desc"
        )

        _global = options.get("global", options.get("g")) or False
        _large = options.get("large", options.get("l")) or False
        _global_data = await ctx.bot.db.fetch(_q)
        if not _global:
            _guild_ids = [_.id for _ in ctx.guild.members if not _.bot]
            data = [_ for _ in _global_data if _["user_id"] in _guild_ids]
        else:
            data = _global_data

        lines = []
        for i, info in enumerate(data, start=1):
            _user = await ctx.bot.getch_user(info["user_id"])
            if _user is not None:
                _user = util.escape_markdown(str(_user))
            if info["user_id"] == ctx.author.id:
                lines.append(f"**{i}.**  {core.SHRIMP} **{info['total']:,}** ➜ **{_user}**")
                continue

            lines.append(f"**{i}.**  {core.SHRIMP} **{info['total']:,}** ➜ {_user}")

        _author_name = "Global Shrimp Leaderboard" if _global else f"Shrimp Leaderboard for {ctx.guild.name}"

        per_page = 25 if _large else 10
        embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        embed.set_author(name=_author_name, icon_url=discord.Embed.Empty if _global else ctx.guild.icon_url)

        await ctx.bot.db.add_xp(ctx.author, 1)
        await paginators.newline_paginate(ctx, embed, lines, per_page=per_page, footer="Page {page}")

    @core.command(
        name="nets",
        alias="n",
        bot_perms=("Send Messages", "Embed Links"),
        usage="[user]",
        description="View a summary of all your nets.",
        cooldown=(5, 3),
        examples=(
            "nets",
            "nets @Friend"
        )
    )
    @core.check(bot_perms=("send_messages", "embed_links"))
    async def _nets(self, ctx, *, user: typing.Optional[converters.BetterMemberConverter] = None):
        await ctx.cd()
        user = user or ctx.author

        _net_flags = await ctx.db.get("users", user, "nets")
        _equipped = await ctx.db.get("users", user, "net")
        all_nets = nets.list_nets(_net_flags)

        listed = [
            f"**{net}** ({core.SHRIMP} {net.price:,})" + (
                "  **`[Equipped]`**" if net.id == _equipped else ''
            ) for net in sorted(
                all_nets, key=lambda net: net.price
            )
        ]

        _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        _embed.set_author(name=f"Nets: {user}", icon_url=ctx.avatar)
        _total_nets = len(nets.Nets.all())

        await paginators.newline_paginate(
            ctx, _embed, listed, per_page=15, footer="Page {page}",
            prefix=f"Nets owned: {len(listed):,}/{_total_nets:,}\n\n"
        )

    @core.command(
        name="inventory",
        aliases=("inv", "i", "items", "backpack"),
        usage="[user]",
        brief="View your current inventory of items.",
        description="View all of your items in your inventory. No need to provide a page number, as it will send a paginator.",
        cooldown=(5, 3),
        examples=(
            "inventory",
            "inventory @User"
        )
    )
    async def _inventory(self, ctx, *, user: typing.Optional[converters.BetterMemberConverter] = None):
        await ctx.cd()
        user = user or ctx.author

        _items = dict(await ctx.db.get("items", user))
        _items.pop("user_id")

        _items = list(_items.items())

        _fields = (
            [{
                "name": f"{(item := items.get_item(_id))!s} — {quantity:,}",
                "value": f"Worth {core.SHRIMP} **{item.sell*quantity:,} shrimp**",
                "inline": False
            } for _id, quantity in _items if quantity > 0]
            if (_unique := sum(v > 0 for k, v in _items)) > 0 else
            [{
                "name": "No items!",
                "value": (
                    "You currently don't have any items."
                    if user == ctx.author else
                    "This users doesn't have any items."
                )
            }]
        )

        _total = sum(quantity for _, quantity in _items)
        _worth = sum(
            items.get_item(_id).sell * quantity
            for _id, quantity in _items
        )

        _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        _embed.description = f"{_total:,} total items, {_unique:,} unique.\n" \
                             f"Inventory worth: {core.SHRIMP} **{_worth:,} shrimp**"
        _embed.set_author(name=f"{user.name}'s Inventory", icon_url=user.avatar_url)

        await paginators.field_paginate(ctx, _embed, _fields, footer="Page {page}")

    @core.command(
        name="cooldowns",
        aliases=("cds", "cd"),
        description="View your current command cooldowns.",
        cooldown=(10, 5)
    )
    async def _cooldowns(self, ctx):
        cooldowns = [
            (
                command.qualified_name,
                await ctx.db.get_cooldown(command.qualified_name, ctx.author) - ctx.unix
            )
            for command in ctx.bot.commands
        ]
        lines = [
            f"**{name}** - {util.duration_strf_abbv(int(retry_after))}"
            for name, retry_after in sorted(cooldowns, key=lambda cd: cd[1], reverse=True)
            if retry_after>0
        ]
        await ctx.cd()
        if len(lines) <= 0:
            lines = ["No cooldowns!"]
        _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        _embed.set_author(name=f"Cooldowns for {ctx.author.name}", icon_url=ctx.avatar)
        await paginators.newline_paginate(ctx, _embed, lines, footer="Page {page}")

    @core.group(
        name="notifications",
        aliases=("notification", "notif", "notifs", "ntf"),
        description="View your current notifications",
        invoke_without_command=True,
        cooldown=(3, 2)
    )
    async def _notifications(self, ctx):
        fetched = await ctx.db.fetch("SELECT * FROM notifications WHERE user_id=$1", ctx.author.id)
        fields = (
            [{
                "name": f"**{i:,}.** {util.duration_strf(round(ctx.unix-notification['dealt_at']))} ago",
                "value": f"**{notification['brief']}**\n" + (
                    notification['description']
                    if len(notification['description'])<64 else
                    notification['description'][:63]+"..."
                ),
                "inline": False
            } for i, notification in enumerate(
                sorted(fetched, key=lambda notif: notif['dealt_at'], reverse=True),
                start=1
            )]
            if len(fetched)>0 else [{
                "name": "No notifications",
                "value": "You have no notifications."
            }]
        )

        _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        _embed.set_author(name=f"{ctx.author.name}'s Notifications", icon_url=ctx.avatar)
        _embed.description = (
            f"View a notification: `{ctx.clean_prefix}notif view <index>`\n"
            f"Clear notifications: `{ctx.clean_prefix}notif clear`"
        )
        await paginators.field_paginate(ctx, _embed, fields, footer="Page {page}")

    @_notifications.command(
        name="clear",
        description="Clear your notifications."
    )
    async def _notifs_clear(self, ctx):
        await ctx.db.execute("DELETE FROM notifications WHERE user_id=$1", ctx.author.id)
        await ctx.send("Notifications cleared.")


def setup(client):
    cog = Stats(client)
    client.add_cog(cog)
