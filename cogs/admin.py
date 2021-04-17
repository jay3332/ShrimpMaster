import aiohttp
import core
import datetime
import discord
import tabulate
import importlib
import inspect
import dotenv
import json as _json
import os
from discord.ext import commands
from asyncio import TimeoutError
from typing import Union, Optional
from util import util, converters, paginators

dotenv.load_dotenv()


class Admin(core.Cog):

    async def cog_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)

    @core.command(
        name="source",
        alias="src",
        perms="Owner",
        usage="[command]",
        description="Exposes the source code of a given command.",
        hidden=True
    )
    @core.check(bot_perms=("send_messages",))
    async def _source(self, ctx, *, command=None):
        if not command:
            return await ctx.send('<https://github.com/jay3332/ShrimpMaster>')

        _lines = ctx.bot.get_source_lines(command.lower().replace(".", " "))
        if not _lines:
            return await ctx.send("Command not found.")

        full = "".join(_lines).replace("```", "`\N{ZERO WIDTH SPACE}"*3)
        if len(full) < 1980:
            return await ctx.send(f'```py\n{full}```')

        myst = await ctx.bot.mystbin.post(full, syntax="python")
        return await ctx.send(f"<{myst}>")

    @core.group(
        name="inspectsource",
        alias="isrc",
        perms="Owner",
        usage="[function]",
        description="Instead of a command, this will import a module and expose it's source code.",
        invoke_without_command=True,
        hidden=True
    )
    @core.check(bot_perms=("send_messages",))
    async def _inspectsource(self, ctx, *, module=None):
        if not module:
            return await ctx.send('<https://github.com/jay3332/ShrimpMaster>')

        try:
            _module = importlib.import_module(module)
        except (AttributeError, ImportError):
            return await ctx.send("Module not found.")
        except TypeError:
            return await ctx.send("That's a built-in module.")
        else:
            _source = inspect.getsource(_module).replace("```", "`\N{ZERO WIDTH SPACE}"*3)
            if len(_source) < 1980:
                return await ctx.send(f"```py\n{_source}```")

            _myst = await ctx.bot.mystbin.post(_source, syntax="python")
            await ctx.send(f"<{_myst}>")


    @_inspectsource.command(
        name="from",
        alias="f",
        perms="Owner",
        usage="[module] [function]",
        description="Function from module.",
        invoke_without_command=True,
        hidden=True
    )
    async def _inspectsource_from(self, ctx, module, *, func):
        try:
            _module = importlib.import_module(module)
            _module = getattr(_module, func)
            if not _module:
                raise AttributeError()
        except (AttributeError, ImportError):
            return await ctx.send("Module not found.")
        except TypeError:
            return await ctx.send("That's a built-in module.")
        else:
            _source = inspect.getsource(_module).replace("```", "`\N{ZERO WIDTH SPACE}"*3)
            if len(_source) < 1980:
                return await ctx.send(f"```py\n{_source}```")

            _myst = await ctx.bot.mystbin.post(_source, syntax="python")
            await ctx.send(f"<{_myst}>")

    @core.group(
        name="gist",
        perms="Owner",
        usage="[command]",
        description="Posts the source of a command to gist.",
        invoke_without_command=True,
        hidden=True
    )
    async def _gist(self, ctx, *, command=None):
        if not command:
            return await ctx.send('<https://github.com/jay3332/ShrimpMaster>')

        _lines = ctx.bot.get_source_lines(_:=command.lower().replace(".", " "))
        if not _lines:
            return await ctx.send("Command not found.")

        full = "".join(_lines)
        _url = await ctx.bot.gist.post(
            full, filename=f"{_.replace(' ', '-')}.py",
            description=f"ShrimpMaster source code. Posted by {ctx.author.name}"
        )
        return await ctx.send(f"{_url}")

    @_gist.group(
        name="-i",
        alias="--i",
        perms="Owner",
        usage="[module]",
        description="Posts the source of a module to gist.",
        invoke_without_command=True,
        hidden=True
    )
    async def _gist_inspect(self, ctx, *, module=None):
        if not module:
            return await ctx.send('<https://github.com/jay3332/ShrimpMaster>')

        try:
            _module = importlib.import_module(module)
        except (AttributeError, ImportError):
            return await ctx.send("Module not found.")
        except TypeError:
            return await ctx.send("That's a built-in module.")
        else:
            _source = inspect.getsource(_module)
            _url = await ctx.bot.gist.post(
                _source, filename=f"{module.replace(' ', '-').replace('.', '-')}.py",
                description=f"ShrimpMaster source code. Posted by {ctx.author.name}"
            )
            return await ctx.send(f"{_url}")

    @_gist_inspect.command(
        name="from",
        aliases=("-f", "--f"),
        perms="Owner",
        usage="[module...]",
        description="Posts the source of a module to gist.",
        hidden=True
    )
    async def _gist_inspect_from(self, ctx, module, *, func):
        try:
            _module = importlib.import_module(module)
            _module = getattr(_module, func)
            if not _module:
                raise AttributeError()
        except (AttributeError, ImportError):
            return await ctx.send("Module not found.")
        except TypeError:
            return await ctx.send("That's a built-in module.")
        else:
            _source = inspect.getsource(_module)
            _url = await ctx.bot.gist.post(
                _source, filename=f"{func.replace(' ', '-').replace('.', '-')}.py",
                description=f"ShrimpMaster source code. Posted by {ctx.author.name}"
            )
            return await ctx.send(f"{_url}")


    @core.group(
        name="database",
        alias="db",
        perms="Owner",
        usage="<subcommand> [values]",
        description="Database actions.",
        invoke_without_command=True,
        hidden=True
    )
    async def _database(self, ctx):
        await ctx.send(
            "Available database commands:\n"
            "`database [set|add] <table> <column> <user> <value>`\n"
            "`database [fetch|exec] <sql>`"
        )

    @_database.command(
        name="fetch",
        alias="sql",
        perms="Owner",
        usage="<sql>",
        description="Fetches entries from the database.",
        hidden=True
    )
    async def _database_fetch(self, ctx, *, query):

        with util.Timer() as timer:
            # noinspection PyBroadException
            try:
                fetched = await ctx.bot.db.pool.fetch(util.strip_codeblocks(query))
            except Exception as e:
                return await ctx.send(f"⚠\n```sql\n{e}```")
        query_time = util.prec_duration_strf(timer.time)

        if len(fetched) <= 0:
            return await ctx.send("Query returned nothing.")
        table_raw = tabulate.tabulate(fetched, headers="keys", tablefmt="fancy_grid")

        if len(table_raw)<1950 and not len(table_raw.split("\n")[0])>138:
            return await ctx.send(f"Query time: {query_time}\n```py\n{table_raw}```")

        _myst = await ctx.bot.mystbin.post(table_raw)
        await ctx.send(f"Query time: {query_time}\n\n<{_myst}>")

    @_database.command(
        name="execute",
        alias="exec",
        perms="Owner",
        usage="<sql>",
        description="Execute a query into the database.",
        hidden=True
    )
    async def _database_exec(self, ctx, *, query):
        with util.Timer() as timer:
            _query = await ctx.bot.db.pool.execute(util.strip_codeblocks(query))
        query_time = util.prec_duration_strf(timer.time)

        await ctx.send(f"Query time: {query_time}\n```sql\n{_query}```")

    @_database.command(
        name="set",
        alias="s",
        perms="Owner",
        usage="<table> <column> <user> <value>",
        description="Set a value in the database.",
        hidden=True
    )
    async def _database_set(self, ctx, table, column, user: Union[converters.BetterMemberConverter, converters.BetterUserConverter], value: Union[float, str]):
        await ctx.bot.db.set(table, column, user, value)
        await ctx.message.add_reaction("✅")

    @_database.command(
        name="add",
        alias="+",
        perms="Owner",
        usage="<table> <column> <user> <value>",
        description="Alter a value in the database.",
        hidden=True
    )
    async def _database_add(self, ctx, table, column, user: Union[converters.BetterMemberConverter, converters.BetterUserConverter], value: Union[float, int]):
        await ctx.bot.db.add(table, column, user, value)
        await ctx.message.add_reaction("✅")

    @_database.command(
        name="polls",
        aliases=("calls", "traffic"),
        perms="Owner",
        description="View recent queries from the database.",
        hidden=True
    )
    async def _database_polls(self, ctx):
        _data = ctx.db.calls
        _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        _embed.set_author(name="Database calls")
        _embed.description=f"Total: {len(_data):,}"
        lines = [
            f"[{buffer['method']}] {buffer['query'][:64]}"
            for buffer in reversed(_data)
        ]
        await paginators.newline_paginate_via_field(ctx, _embed, lines, "Specific", footer="Page {page}")

    @core.command(
        name="upload",
        alias="up",
        perms="Owner",
        description="Upload a file to jay.has-no-brain.sxcu",
        hidden=True
    )
    async def _upload(self, ctx, *, url=None):
        _bytes = None
        _text = "jay3332"
        if url is not None:
            try:
                async with ctx.bot.session.get(url) as response:
                    if response.status == 200:
                        _bytes = await response.read()
            except aiohttp.InvalidURL:
                _text = url
        if not _bytes:
            if len(ctx.message.attachments) > 0:
                _a = ctx.message.attachments[0]
                _bytes = await _a.read()
            elif len(a := ctx.message.reference.resolved.attachments) > 0:
                _a = a[0]
                _bytes = await _a.read()
            else:
                return await ctx.send("No image/file found.")

        _embed_props = {
            "color": "#59E3FF",
            "title": _text,
            "discord_hide_url": True,
            "description": "Uploaded at " + ctx.now.strftime('%#d %b %Y, %I:%M %p UTC')
        }

        async with ctx.bot.session.post("https://jay.has-no-bra.in/upload", data={
            "image": _bytes,
            "token": os.getenv('SXCU'),
            "og_properties": _json.dumps(_embed_props)
        }) as response:
            if response.status == 200:
                json = await response.json()
                await ctx.send(json.get("url", "None"))
            else:
                await ctx.send(f"Something wen't wrong. Code: {response.status}")


    @core.command(
        name="reload",
        alias="rc",
        perms="Owner",
        description="Reloads a category or all.",
        hidden=True
    )
    async def _reload(self, ctx, *extensions):
        if len(extensions) <= 0:
            extensions = list(ctx.bot.extensions.keys())

        _pointer = extensions[0] if len(extensions) == 1 else f"{len(extensions)} cogs"
        _ = await ctx.send(f"{core.LOADING} Reloading {_pointer}...")

        _successful = []
        _errors = {}
        with util.Timer() as timer:
            for extension in extensions:
                try:
                    ctx.bot.reload_extension(extension)
                except Exception as e:
                    _errors[extension] = e
                else:
                    _successful.append(extension)

        _time = util.prec_duration_strf(timer.time)

        _content: str
        _pointer = _successful[0] if len(_successful) == 1 else f"{len(_successful)} cogs"
        if _successful:
            _content = f"{core.CHECK} `[{_time}]` Successfully reloaded {_pointer}."
        else:
            _content = f"⚠ `[{_time}]` All cogs raised errors:"

        for ext, error in _errors.items():
            _content += f"\n**{ext}:**  {error}"

        await ctx.maybe_edit(_, content=_content, allowed_mentions=discord.AllowedMentions.none())


    @core.command(
        name="drop",
        perms="Owner",
        description="Drop shrimp because owner is generous",
        hidden=True
    )
    async def _drop(self, ctx, channel: Optional[discord.TextChannel] = None, *, amount: int):
        channel = channel or ctx.channel
        _ = await channel.send(f"The first person to react with {core.SHRIMP} will get **{amount:,} shrimp**!")
        await _.add_reaction(core.SHRIMP)

        try:
            __, winner = await ctx.bot.wait_for("reaction_add", timeout=30, check=lambda r, u: (
                r.message == _ and not u.bot and str(r.emoji) == core.SHRIMP
            ))
        except TimeoutError:
            return await ctx.maybe_edit(_, content="I timed-out.")
        else:
            await ctx.db.add("users", "shrimp", winner, amount)
            await ctx.maybe_edit(_, content=f"Congratulations to **{winner.name}** on winning {core.SHRIMP} **{amount:,} shrimp**.")


    @core.command(
        name="refresh",
        alias="ref",
        perms="Owner",
        description="Reloads all cogs and files in both core and util.",
        hidden=True
    )
    async def _refresh(self, ctx):
        _ = await ctx.send(f"{core.LOADING} Refreshing...")

        with util.Timer() as timer:
            for utility in os.listdir("./util"):
                if utility.endswith(".py"):
                    _name = importlib.import_module(f"util.{utility[:-3]}")
                    importlib.reload(_name)
            for core_feature in os.listdir("./core"):
                if core_feature.endswith(".py"):
                    _name = importlib.import_module(f"core.{core_feature[:-3]}")
                    importlib.reload(_name)
            for extension in os.listdir("./cogs"):
                if extension.endswith(".py"):
                    try:
                        ctx.bot.reload_extension(f"cogs.{extension[:-3]}")
                    except Exception as e:
                        await ctx.send(e)

        await ctx.maybe_edit(_, content=f"Done. {util.prec_duration_strf(timer.time)}", allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_unblacklist_timer_complete(self, timer):
        await self.client.dm(timer.kwargs.get("user"), "Your blacklist is over; you may use the bot normally now.")

    @core.command(
        name="blacklist",
        alias="bl",
        perms="Owner",
        description="Blacklists a user from the bot.",
        hidden=True
    )
    async def _blacklist(self, ctx, user: converters.BetterUserConverter(), duration: Optional[converters.TimeConverter] = None, *, reason: str = None):
        reason = reason or "No reason provided."
        if await ctx.db.is_blacklisted(user, ctx.unix):
            return await ctx.send("That user is already blacklisted.")

        new_time = ctx.unix + duration if duration else 1
        query = """
        INSERT INTO blacklists (user_id, moderator_id, expires, reason)
        VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO UPDATE SET
        user_id=$1, moderator_id=$2, expires=$3, reason=$4;
        """
        await ctx.db.execute(query, user.id, ctx.author.id, new_time, reason)
        try:
            await ctx.message.add_reaction("✅")
        except discord.Forbidden:
            pass
        await ctx.send(f"Blacklisted **{user.name}** for **{util.duration_strf(duration)}**. Reason: {reason}"
                       if duration else f"Blacklisted **{user.name}** forever. Reason: {reason}")
        await ctx.bot.dm(user, f"You have been blacklisted from ShrimpMaster. Reason: {reason}" if not duration else
                               f"You have been blacklisted from ShrimpMaster for **{util.duration_strf(duration)}**. Reason: {reason}")
        if duration:
            await ctx.bot.create_relative_timer(
                duration, "unblacklist", user=user
            )

    @core.command(
        name="unblacklist",
        alias="ubl",
        perms="Owner",
        description="Unblacklists a user from the bot.",
        hidden=True
    )
    async def _unblacklist(self, ctx, *, user: converters.BetterUserConverter()):
        await ctx.db.execute("DELETE FROM blacklists WHERE user_id=$1", user.id)
        await ctx.send(f"Unblacklisted **{user.name}**.")
        await ctx.bot.dm(user, f"You have been manually unblacklisted by a bot moderator.")


def setup(client):
    cog = Admin(client)
    client.add_cog(cog)
