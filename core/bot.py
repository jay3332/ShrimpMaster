import os
import re
import dotenv
import asyncio
import inspect
import asyncpg
import mystbin
import discord
import aiohttp
import datetime
import platform

from json import dumps
from util.timers import BotTimerManager
from util.util import duration_strf
from util.path import route
# from .help import ShrimpMasterHelpCommand
from . import database, constants, handler
from discord.ext import commands

dotenv.load_dotenv()


def get_prefix(client, message):
    async def wrapper():
        fallback = os.urandom(32).hex()

        _prefixes = await client.db.get("guilds", message.guild, "prefixes")
        _prefixes = _prefixes or ["s."]

        # regex compiling for case insensitivity
        comp = re.compile("^(" + "|".join(map(re.escape, _prefixes)) + ").*", flags=re.I)
        match = comp.match(message.content)

        if match is not None: return match.group(1)
        return commands.when_mentioned_or(fallback)(client, message)

    return client.loop.create_task(wrapper())


class Gist:
    def __init__(self, session):
        self._ = session

    async def post(self, content, filename="post.py", *, description=None):

        _gist = os.getenv("GIST")
        _payload = {"files": {filename: {"content": content}}}
        if description is not None:
            _payload["description"] = description
        async with self._.post(
            "https://api.github.com/gists", data=dumps(_payload),
            headers={'Authorization': f'token {_gist}'}
        ) as r:
            _j = await r.json()
            return _j.get('html_url', _j)


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.suppress_reply = False
        self.db = self.bot.db

    @property
    def now(self):
        return self.bot.now

    @property
    def unix(self):
        return self.bot.unix

    @property
    def avatar(self):
        return self.author.avatar_url

    @property
    def clean_prefix(self):
        user = self.me if self.guild else self.bot.user
        pattern = re.compile(r"<@!?%s>" % user.id)
        return pattern.sub("@%s" % user.display_name.replace('\\', r'\\'), self.prefix)

    async def cd(self):
        _cd = getattr(self.command, "cooldown", (0, 0))[0]
        await self.bot.db.set_cooldown(self.command.qualified_name, self.author, self.unix+_cd)

    async def check_cd(self):
        _cd = await self.bot.db.get_cooldown(self.command.qualified_name, self.author)
        if self.unix >= _cd:
            return True
        retry_after = _cd - self.unix
        embed = discord.Embed(color=constants.ERROR_COLOR)
        embed.set_author(name="Slow down!", icon_url=self.avatar)
        embed.description = "This command is on a cooldown."
        embed.add_field(name="Please wait", value=duration_strf(round(retry_after, 1)), inline=False)
        embed.add_field(name="Default cooldown", value=(
            f"Default: {duration_strf(round(self.command.cooldown[0], 1))}\n"
            f"Premium: {duration_strf(round(self.command.cooldown[1], 1))}"
        ))
        await self.send(embed=embed, embed_perms=True)
        return False

    async def send(self, content: any = None, **kwargs):
        if not (_perms:=self.channel.permissions_for(self.me)).send_messages:
            try:
                await self.author.send("I can't send any messages in that channel. "
                                       "Please give me sufficient permissions to do so.")
            except discord.Forbidden:
                pass
            return
        reply = kwargs.pop("reply", True)
        require_embed_perms = kwargs.pop("embed_perms", False)
        if require_embed_perms and not _perms.embed_links:
            kwargs = {}
            content = "Oops! I need **Embed Links** permission to work properly. " \
                      "Please tell a server admin to grant me that permission."
        if isinstance(content, discord.Embed):
            kwargs['embed'] = content
            content = None
        if isinstance(content, discord.File):
            kwargs['file'] = content
            content = None
        if reply and _perms.read_message_history and not self.suppress_reply:
            try:
                return await self.message.reply(content, **kwargs)
            except (discord.HTTPException, discord.NotFound):
                return await super().send(content, **kwargs)
        return await super().send(content, **kwargs)

    async def confirm(self, text, delete_after=False, timeout=60):

        permissions = self.me.permissions_in(self.channel)
        external = permissions.external_emojis
        reactions = permissions.add_reactions

        if reactions:

            r_yes = constants.CHECK if external else "✅"
            r_no = constants.CROSS if external else "❌"

            r_all = (r_yes, r_no)

            original = await self.send(text)
            await original.add_reaction(r_yes)
            await original.add_reaction(r_no)

            try: response = str((await self.bot.wait_for(
                "reaction_add", timeout=timeout, check=(
                    lambda r, u: str(r.emoji) in r_all
                    and r.message.id==original.id
                    and u.id==self.author.id
                )
            ))[0].emoji)

            except asyncio.TimeoutError:
                return False

            if delete_after:
                await self.maybe_delete(original)

            return response==r_yes

        else:

            original = await self.send(text+"\nType `yes` or `no` in chat.")
            yes = ("yes", "y", "sure", "yeah")

            try: response = (await self.bot.wait_for(
                "message", timeout=timeout, check=(
                    lambda msg: msg.content is not None
                    and msg.author.id==self.author.id
                    and msg.channel.id==self.channel.id
                )
            )).content.lower()
            except asyncio.TimeoutError:
                return False

            if delete_after: await self.maybe_delete(original)
            return response in yes

    async def maybe_edit(self, message, content=None, **kwargs):
        try:
            await message.edit(content=content, **kwargs)
        except (AttributeError, discord.NotFound):
            if (not message) or message.channel == self.channel:
                return await self.send(content, **kwargs)
            await message.channel.send(content, **kwargs)

    async def maybe_delete(self, message, *args, **kwargs):
        try:
            await message.delete(*args, **kwargs)
        except (AttributeError, discord.NotFound, discord.Forbidden):
            pass


class ShrimpMaster(commands.Bot):
    def __init__(self):
        _allowed_mentions = discord.AllowedMentions(users=True, replied_user=False, roles=False, everyone=False)
        _intents = discord.Intents.all()
        super().__init__(
            command_prefix=get_prefix,
            case_insensitive=True,
            allowed_mentions=_allowed_mentions,
            intents=_intents,
            help_command=None  # ShrimpMasterHelpCommand()
        )

        self.db = None
        self.timers = None
        self.command_usage = {}
        self.up_since = datetime.datetime.utcnow()
        self.handler = handler.Handler()
        self.session = aiohttp.ClientSession()
        self.mystbin = mystbin.Client()
        self.gist = Gist(self.session)
        self.crime_messages = {
            "good": [],
            "bad": [],
            "die": []
        }

        self._setup()

    def get_source_lines(self, command):
        command = self.get_command(command)
        if not command: return None

        return inspect.getsourcelines(command.callback.__code__)[0]

    async def _setup_database(self):
        _sys = platform.system()
        _database_password = os.getenv("PRIVATE_AUTH") \
            if _sys == "Windows" else os.getenv("DB_AUTH")

        _db = await asyncpg.create_pool(
            database="shrimp_master",
            user="postgres",
            password=_database_password,
            host="127.0.0.1"
        )
        self.db = database.DatabaseManager(_db, self)
        await database.setup(_db)

    def _setup_public_env(self):
        os.environ["NO_COLOR"] = "True"
        os.environ["JISHAKU_HIDE"] = "True"
        os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
        return self  # because pycharm is mean

    def _setup_custom_methods(self):
        async def add_reactions(message, *reactions):
            for reaction in reactions:
                await message.add_reaction(reaction)

        setattr(discord.Message, "add_reactions", add_reactions)
        self.create_timer = self.timers.create_timer
        return self

    def _setup_cogs(self):
        for file in os.listdir(route("cogs")):
            if file.endswith(".py"):
                self.load_extension(f"cogs.{file[:-3]}")
        self.load_extension("jishaku")

    def _load_crime_messages(self):
        with open(route("assets", "crime_messages.txt"), "r") as f:
            lines = f.readlines()
            for line in lines:
                key = {
                    "+": "good",
                    "-": "bad",
                    "!": "die"
                }[line[0]]
                self.crime_messages[key].append(line[2:].strip())

    def _setup(self):
        self._setup_public_env()
        self.loop.run_until_complete(self._setup_database())
        self.timers = BotTimerManager(self)
        self._setup_custom_methods()
        self._setup_cogs()
        self._load_crime_messages()

    @property
    def uptime(self):
        return (datetime.datetime.utcnow() - self.up_since).total_seconds()

    @property
    def avatar(self):
        return self.user.avatar_url

    @property
    def now(self):
        return datetime.datetime.utcnow()

    @property
    def unix(self):
        epoch = datetime.datetime.utcfromtimestamp(0)
        return (self.now - epoch).total_seconds()

    def reload_crime_messages(self):
        self.crime_messages = {
            "good": [],
            "bad": [],
            "die": []
        }
        self._load_crime_messages()
        return self.crime_messages

    async def create_relative_timer(self, seconds, *args, **kwargs):
        return await self.timers.create_timer(
            datetime.datetime.utcfromtimestamp(self.unix+seconds),
            *args, **kwargs
        )

    @staticmethod
    async def getch(get_method, fetch_method, _id):
        """ Combo of get_x and fetch_x """
        if not _id:
            return None

        try:
            _result = get_method(_id) or await fetch_method(_id)
        except (discord.HTTPException, discord.Forbidden, discord.NotFound):
            return None
        else:
            return _result

    async def getch_user(self, _id):
        """ Combo of get_user and fetch_user """
        if not _id:
            return None

        try:
            _result = self.get_user(_id) or await self.fetch_user(_id)
        except discord.NotFound:
            return None
        else:
            return _result

    def add_to_usage(self, name):
        if name not in self.command_usage:
            self.command_usage[name] = 0
        self.command_usage[name] += 1

    @staticmethod
    async def dm(user, *args, **kwargs):
        try:
            return await user.send(*args, **kwargs)
        except discord.Forbidden:
            pass

    async def process_commands(self, message):
        await self.handler.handle_command(self, message, Context)

    async def wait_for_multiple(self, *events, **kwargs):
        done, pending = await asyncio.wait([
            self.wait_for(event, **kwargs)
            for event in events
        ], return_when=asyncio.FIRST_COMPLETED)

        # noinspection PyBroadException
        _result: any = None
        _error:  any = None
        try:
            _result = done.pop().result()
        except Exception as e:
            _error = e

        for future in done:
            future.exception()
        for future in pending:
            future.cancel()

        if _error is not None:
            raise _error
        return _result

    async def on_message(self, message):
        if message.author.bot:
            return
        if message.content.strip() in (
            f"<@{self.user.id}>",
            f"<@!{self.user.id}>"
        ):
            prefix = await self.db.get("guilds", message.guild, "prefixes") or ['s.']
            prefix.sort(key=lambda pf: len(pf))
            await message.channel.send(f"Hey, my prefix is **`{prefix[0]}`**")
        await self.process_commands(message)

    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if payload.cached_message:
            return
        channel = await self.getch(self.get_channel, self.fetch_channel, payload.channel_id)
        try:
            message = discord.Message(state=self._get_state(), channel=channel, data=payload.data)
        except KeyError:
            return  # We could do API calls here but that would be abuse
        await self.on_message(message)

    async def on_message_edit(self, before, after):
        if before.content != after.content:
            await self.on_message(after)

    async def on_command_error(self, ctx, error):
        await self.handler.handle_error(ctx, error)

    async def send_message(self, channel_id, content, **kwargs):
        await self.http.send_message(channel_id, content, **kwargs)

    def run(self):
        token = os.getenv("TOKEN")
        super().run(token)
