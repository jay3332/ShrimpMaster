import typing
from discord.ext import commands, flags


def command(name, *, alias=None, aliases=(), perms: typing.Union[str, list, tuple] = "None", bot_perms: typing.Union[str, list, tuple] = "Send Messages", usage=None,
            description="No description provided.", brief=None, examples=None, cooldown=0, hidden=False, disabled=False, **kwargs):
    if alias is not None:
        aliases = [alias]

    if isinstance(perms, str):
        perms = [perms]
    if isinstance(bot_perms, str):
        bot_perms = [bot_perms]

    if isinstance(cooldown, (int, float)):
        cooldown = [cooldown, cooldown]

    return commands.command(
        name=name,
        cls=Command,
        aliases=aliases,
        perms=perms,
        bot_perms=bot_perms,
        usage=usage,
        description=description,
        brief=brief or description,
        examples=examples or [],
        cooldown=cooldown,
        hidden=hidden,
        disabled=disabled,
        **kwargs
    )


def group(name, *, alias=None, aliases=(), perms: typing.Union[str, list, tuple] = "None", bot_perms: typing.Union[str, list, tuple] = "Send Messages",  usage=None,
          description="No description provided.", brief=None, examples=None,
          invoke_without_command=False, cooldown=0, hidden=False, disabled=False, **kwargs):
    if alias is not None:
        aliases = [alias]

    if isinstance(perms, str):
        perms = [perms]
    if isinstance(bot_perms, str):
        bot_perms = [bot_perms]

    if isinstance(cooldown, (int, float)):
        cooldown = [cooldown, cooldown]

    return commands.group(
        name=name,
        cls=Group,
        aliases=aliases,
        perms=perms,
        bot_perms=bot_perms,
        usage=usage,
        description=description,
        brief=brief or description,
        examples=examples or [],
        invoke_without_command=invoke_without_command,
        cooldown=cooldown,
        hidden=hidden,
        disabled=disabled,
        **kwargs
    )


def check(perms: typing.Union[list, tuple] = (), bot_perms: typing.Union[list, tuple] = ("view_channel", "send_messages"), *other_checks):
    perms = {k: True for k in perms}
    bot_perms = {k: True for k in bot_perms}

    return commands.check_any(
        commands.has_permissions(**perms),
        commands.bot_has_permissions(**bot_perms),
        *[commands.check(ch) for ch in other_checks]
    )


class Command(flags.FlagCommand):
    def __init__(self, callback, name, *, aliases, brief, description, usage, perms, bot_perms, examples, cooldown, hidden, disabled, **kwargs):
        super().__init__(callback, name=name, aliases=aliases, brief=brief, description=description, usage=usage, hidden=hidden, **kwargs)
        self.perms = perms
        self.bot_perms = bot_perms
        self.examples = examples
        self.cooldown = cooldown
        self.disabled = disabled


class Group(flags.FlagGroup):
    def __init__(self, callback, name, *, aliases, brief, description, usage, perms, bot_perms, examples, cooldown, hidden, disabled, **kwargs):
        super().__init__(callback, name=name, aliases=aliases, brief=brief, description=description, usage=usage, hidden=hidden,
                         case_insensitive=True, **kwargs)
        self.perms = perms
        self.bot_perms = bot_perms
        self.examples = examples
        self.cooldown = cooldown
        self.disabled = disabled

    def command(self, *args, **kwargs):

        def wrapper(func):
            kwargs.setdefault('parent', self)
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return wrapper

    def group(self, *args, **kwargs):

        def wrapper(func):
            kwargs.setdefault('parent', self)
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return wrapper


class Cog(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Cog loaded: {type(self).__name__}")
