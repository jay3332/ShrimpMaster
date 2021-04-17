import prettify_exceptions
from discord.ext import commands, flags
from util.util import escape_markdown
from util.nets import NetNotFound
from util.items import ItemNotFound
from mystbin import APIError

getattr(prettify_exceptions.Formatter, "_default_theme")["_ansi_enabled"] = False


class Handler:
    def __init__(self):
        self.commands_handled = 0
        self.errors_handled = 0

    def __repr__(self):
        return f'Handler(commands={self.commands_handled}, errors={self.errors_handled})'

    async def handle_error(self, ctx, error):
        self.errors_handled += 1
        if isinstance(error, (ItemNotFound, NetNotFound)):
            return await ctx.send(error)
        if isinstance(error, commands.CommandNotFound):
            return  # await ctx.send("stuff")
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"Missing required argument \"{error.param.name}\"")
        if isinstance(
            error, (
                commands.ConversionError,
                commands.NotOwner,
                commands.CheckAnyFailure,
                commands.CheckFailure
            )
        ):
            return
        if isinstance(error, commands.UserInputError):
            return await ctx.send(error)
        if isinstance(error, flags.ArgumentParsingError):
            return await ctx.send("Invalid flag signature.")
        if isinstance(error, commands.MaxConcurrencyReached):
            return await ctx.send("Another instance of this command is running.")

        _base = (type(error), error, error.__traceback__)

        _complete_traceback = "".join(prettify_exceptions.DefaultFormatter().format_exception(*_base))
        try:
            _myst = await ctx.bot.mystbin.post(_complete_traceback, syntax="python")
        except APIError:
            _myst = ""

        _error = '{0.__class__.__name__}: {0}'.format(error.original) if isinstance(error, commands.CommandInvokeError) else error
        _broad_traceback = escape_markdown(str(_error)[:1800])

        await ctx.send(f"Something has gone wrong while executing your command.\n{_broad_traceback}\n\n**<{_myst}>**")
        raise error


    async def handle_command(self, bot, message, context_class):
        _bypass = False
        _no_reply = False
        if message.author.bot: return
        if not message.guild: return

        _all_pf = _pf = await bot.get_prefix(message)
        if isinstance(_all_pf, list):
            _pf = _all_pf[0]

        _content = message.content
        for _possible_prefix in _all_pf:
            _content = _content.replace(_possible_prefix, "", 1)
        if found_shortcut := await bot.db.get_shortcut(message.author, _content.lstrip()):
            if message.content.startswith(_pf) or (
                message.content.startswith('<@{}> '.format(bot.user.id)) or
                message.content.startswith('<@!{}> '.format(bot.user.id))
            ):
                message.content = _pf + found_shortcut

        if "--no-cooldown" in message.content and await bot.is_owner(message.author):
            message.content = message.content.replace("--no-cooldown", "", 1).strip()
            _bypass = True

        if message.content.endswith(" --no-reply"):
            message.content = message.content[:-11]
            _no_reply = True
        elif message.content.endswith(" --nr"):
            message.content = message.content[:-5]
            _no_reply = True

        ctx = await bot.get_context(message, cls=context_class)

        if not ctx:
            return
        if not ctx.command:
            return
        if await ctx.db.is_blacklisted(ctx.author, ctx.unix):
            return

        await self.instantiate_command(ctx, bypass=_bypass, no_reply=_no_reply)

    async def instantiate_command(self, ctx, **kwargs):
        if getattr(ctx.command, "disabled", False) and not await ctx.bot.is_owner(ctx.author):
            return await ctx.send("This command is currently disabled or under maintenance. Please check back later!")
        if not kwargs.get("bypass") and not await ctx.check_cd():
            return
        if kwargs.get("no_reply"):
            ctx.suppress_reply = True

        ctx.bot.add_to_usage(ctx.command.qualified_name)
        self.commands_handled += 1
        await ctx.bot.invoke(ctx)
