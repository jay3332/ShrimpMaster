import core
import time
import typing
import discord
from discord.ext import commands
from util import util, paginators, converters


class Misc(core.Cog):

    @core.command(
        name="help",
        aliases=("commands", "cmds", "h"),
        bot_perms=("Send Messages", "Embed Links", "Add Reactions"),
        usage="[command]",
        brief="View the help page for this bot.",
        cooldown=(5, 1),
        description=(
            "Need help? Use this command to view a summary of all"
            " command categories and their commands. You can specify a"
            " specific command to get help on, or specify a specific category"
            " to get help on."
        ),
        examples=(
            "help",
            "help shrimp",
            "help stats"
        )
    )
    @core.check(bot_perms=("view_channel", "send_messages", "embed_links", "add_reactions"))
    async def _help(self, ctx: core.Context, *, command: typing.Union[converters.CommandConverter, converters.CogConverter] = None):
        """ Builds a help command. Inspired by MinimalHelpCommand"""

        await ctx.cd()
        embed = discord.Embed(color=core.COLOR)
        prefix = ctx.clean_prefix
        embed.set_author(name="ShrimpMaster - Help", icon_url=ctx.bot.avatar)
        embed.timestamp = ctx.now

        async def predicate(cmd):
            if cmd.hidden:
                return False
            """try:
                return await cmd.can_run(ctx)
            except commands.CommandError:
                return False"""
            return True

        if not command:

            embed.description = (
                "**Welcome to ShrimpMaster!**\n"
                "Get help on a specific category by running `{0}help <category>`.\n"
                "You can even get help on a single command by running `{0}help <command>`!\n\n"
                "[**Support Server**]({1}) • [**Bot Invite**]({2})"
            ).format(prefix, core.SUPPORT_SERVER, util.get_invite_link(ctx.bot, core.RECOMMENDED_PERMISSIONS))

            fields = []
            # get a list of cogs and their commands

            cogs = dict(ctx.bot.cogs)
            for cog in cogs:
                if cog == "Jishaku":
                    continue
                cmds = [cmd.name for cmd in cogs[cog].get_commands() if await predicate(cmd)]
                if len(cmds) <= 0:
                    continue
                cmds = sorted(cmds)
                emoji = core.HELP_EMOJIS.get(cog, "")
                fields.append({
                    "name": f"{emoji} {cog} ({len(cmds)} command{'s' if len(cmds)!=1 else ''})",
                    "value": " ".join(f'`{cmd}`' for cmd in cmds),
                    "inline": False
                })

            await paginators.field_paginate(ctx, embed, fields, footer="Page {page}", per_page=9)

        elif isinstance(command, (core.Cog, commands.Cog)):

            _cmds = [c for c in command.get_commands() if await predicate(c)]
            if len(_cmds) <= 0:
                return await ctx.send("Whoops! No commands in this category.")
            embed.title = f"Category: {type(command).__name__}"
            embed.description = f"Get info on a specific command by doing `{prefix}help <command>`."
            cmds = [{
                "name": f"{prefix}{cmd.qualified_name} {getattr(cmd, 'usage', '') or ''}",
                "value": cmd.brief if len(cmd.brief)<100 else cmd.brief[:98]+"...",
                "inline": False
            } for cmd in sorted(_cmds, key=lambda c: c.name)]

            await paginators.field_paginate(ctx, embed, cmds, footer="Page {page}")

        elif isinstance(command, (core.Command, commands.Command, core.Group, commands.Group)):

            embed.title = f'{prefix}{command.qualified_name} {command.usage or ""}'.strip()
            embed.description = getattr(command, "description", "No description provided.")

            _aliases = [command.name, *command.aliases]
            embed.add_field(name="Aliases", value=", ".join(f'`{alias}`' for alias in _aliases), inline=False)
            embed.add_field(name="Permissions", value=(
                f"You: {', '.join(getattr(command, 'perms', []) or ['None'])}\n"
                f"Me: {', '.join(getattr(command, 'bot_perms', []) or ['None'])}"
            ), inline=False)

            _cooldown = getattr(command, "cooldown", (0, 0))
            if tuple(_cooldown) == (0, 0):
                _cd_text = "None"
            else:
                _cd_text = (
                    f"Default Cooldown: {util.duration_strf(_cooldown[0])}\n"
                    f"Premium Cooldown: {util.duration_strf(_cooldown[1])}"
                )
            embed.add_field(name="Cooldown", value=_cd_text)

            _examples = getattr(command, "examples", ["No examples provided."]) or ["No examples provided."]
            embed.add_field(name="Examples", value="\n".join(_examples))

            if isinstance(command, (core.Group, commands.Group)):
                cmds = [cmd for cmd in command.commands if await predicate(cmd)]
                if len(cmds) > 0:
                    lines = [
                        f"**{cmd.qualified_name}** - {cmd.brief or cmd.description}"
                        for cmd in sorted(cmds, key=lambda c: c.name)
                    ]
                    embed.add_field(name="Subcommands", value="\n".join(lines), inline=False)
            # noinspection PyTypeChecker
            await ctx.send(embed)

        else:

            await ctx.send("toes (how did you manage to get this)")


    @core.command(
        name="ping",
        aliases=("latency", "pong"),
        bot_perms=("Send Messages", "Embed Links"),
        brief="A command to see whether I'm working or not.",
        description=(
            "Used to test whether I work or not, or how slow I take to respond. "
            "Measures websocket latency, typing latency, and database latency. "
            "Round-trip is the sum of those latencies."
        ),
        cooldown=(2, 0.5),
        examples=("ping",)
    )
    @core.check(bot_perms=("view_channel", "send_messages", "embed_links"))
    async def _ping(self, ctx):

        await ctx.cd()

        # websocket ping (pretty easy since discord.py has it built-in)
        websocket = util.prec_duration_strf(_ws:=ctx.bot.latency)

        with util.Timer() as big_timer:

            # database ping (select 1)
            _start = time.perf_counter()
            with util.Timer() as timer:
                await ctx.bot.db.fetch("select 1")
            database_s = util.prec_duration_strf(timer.time)

            # database ping (select *)
            with util.Timer() as timer:
                await ctx.bot.db.fetch("select * from users")
            database = util.prec_duration_strf(timer.time)

            # typing ping
            with util.Timer() as timer:
                original = await ctx.send(f"{core.LOADING} Pinging...")
            _typing = util.prec_duration_strf(timer.time)

        # round trip
        round_trip = util.prec_duration_strf(big_timer.time + _ws)

        # format embed
        embed = discord.Embed(color=core.COLOR)
        embed.description = "Don't worry about what's below unless you really care."
        embed.set_author(name="Latency", icon_url=ctx.bot.avatar)
        embed.timestamp = ctx.now

        embed.add_field(name="Websocket", value=websocket)
        embed.add_field(name="​", value="​")  # blank field
        embed.add_field(name="Typing", value=_typing)

        embed.add_field(name="Database (SELECT 1)", value=database_s)
        embed.add_field(name="​", value="​")  # blank field
        embed.add_field(name="Database (SELECT *)", value=database)

        embed.add_field(name="Round Trip", value=round_trip)

        await ctx.maybe_edit(original, "", embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @core.command(
        name="invite",
        alias="link",
        bot_perms=("Send Messages", "Embed Links"),
        description="Retrieve the invite link for the bot.",
        cooldown=(3, 0)
    )
    @core.check(bot_perms=("send_messages", "embed_links"))
    async def _invite(self, ctx):
        await ctx.cd()
        embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        embed.title = "ShrimpMaster Invite Links"
        embed.description = "Wanna add me to your server?"
        embed.add_field(name="Invite Links", value=(
            f"[**Invite ShrimpMaster to your server**]({util.get_invite_link(ctx.bot, 8)})\n"
            f"[**Join the Support Server**]({core.SUPPORT_SERVER})"
        ))

        embed.set_thumbnail(url=ctx.bot.user.avatar_url)
        await ctx.send(embed=embed)

    @core.command(
        name="uptime",
        alias="upt",
        description="View the bot's current uptime.",
        cooldown=1
    )
    async def _uptime(self, ctx):
        await ctx.cd()
        delta = (ctx.now - ctx.bot.up_since).total_seconds()
        await ctx.send(f"⏲  I have been online for **{util.duration_strf(delta)}**.")


    @core.command(
        name="about",
        aliases=("info", "botinfo", "information"),
        description="View information about the bot.",
        cooldown=2
    )
    async def _about(self, ctx):
        owner = await ctx.bot.getch_user(ctx.bot.owner_id)
        if not owner:
            return await ctx.send("Invalid owner.")

        _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        _embed.set_author(name=owner, icon_url=owner.avatar_url)
        await ctx.send(embed=_embed)


    @core.command(
        name="commandusage",
        aliases=("cmdusage", "cu"),
        description="View how frequently my commands are used.",
        cooldown=5
    )
    async def _commandusage(self, ctx):
        await ctx.cd()

        lines = [
            f"**{command}**  -  {usage:,}"
            for command, usage in sorted(ctx.bot.command_usage.items(), key=lambda i: i[1], reverse=True)
        ]

        _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        _embed.title = "Command Usage"
        _embed.description = "Command usage since my last startup."
        _embed.description += f"\nTotal: **{ctx.bot.handler.commands_handled:,}**"
        await paginators.newline_paginate_via_field(ctx, _embed, lines, "Breakdown", footer="Page {page}")


def setup(client):
    cog = Misc(client)
    client.add_cog(cog)
