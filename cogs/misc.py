import core
import time
import typing
import discord
from discord.ext import commands
from util import util, paginators, converters


class Misc(core.Cog):

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
