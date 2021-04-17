from discord.ext.commands import (
    Converter, CommandNotFound, UserInputError, PartialEmojiConverter,
    PartialEmojiConversionFailure, MemberNotFound, UserNotFound,
    MemberConverter, UserConverter, BadArgument
)
import parsedatetime as pdt
from dateutil.relativedelta import relativedelta
from util import util
import aiohttp
import typing
import discord
import core
import re


SHORT_TIME = re.compile(
    "(?:(?P<years>[0-9])(?:years?|y|yrs?))?"
    "(?:(?P<months>[0-9]{1,2})(?:months?|mo))?"
    "(?:(?P<weeks>[0-9]{1,4})(?:weeks?|w|wks?))?"
    "(?:(?P<days>[0-9]{1,5})(?:days?|d))?"
    "(?:(?P<hours>[0-9]{1,5})(?:hours?|h|hrs?))?"
    "(?:(?P<minutes>[0-9]{1,5})(?:minutes?|m|mins?))?"
    "(?:(?P<seconds>[0-9]{1,5})(?:seconds?|s|secs?))?",
    re.VERBOSE
)


class CommandConverter(Converter):
    """ Converts a string into a command. I know `get_command` does this, however this will raise an error if it can't find the command.
        It also takes into consideration, permissions."""
    async def convert(self, ctx, arg):
        command = ctx.bot.get_command(arg.lower())
        if not command:
            raise CommandNotFound()
        return command


class CogConverter(Converter):
    async def convert(self, ctx, arg):
        arg = arg.title().replace(" ", "")
        cog = ctx.bot.get_cog(arg)
        if not arg:
            raise CommandNotFound()
        if type(arg).__name__ == "Jishaku":
            raise CommandNotFound()
        return cog


async def get_image(ctx, arg=None, png=True):
    def check_attachment(a):
        _supported = (
            (".png", ".jpg", ".jpeg", ".webp", ".gif")
            if not png else (".png", ".jpg", ".jpeg")
        )
        if not any(a.filename.endswith(suffix) for suffix in _supported):
            raise UserInputError("Unsupported file type.")
        max_filesize = 1024*1024*3  # 3 mb
        if a.size > max_filesize:
            raise UserInputError("Attachments must be under 3 megabytes.")
        max_width, max_height = 2048, 2048
        if a.width > max_width:
            raise UserInputError("Attachments must be under 2048 pixels in width.")
        if a.height > max_height:
            raise UserInputError("Attachments must be under 2048 pixels in height.")
        return True

    async def fallback():
        # in this fallback, we check for user avatar/replies
        if res := ctx.message.reference:
            if attachments := res.resolved.attachments:
                a = attachments[0]
                if check_attachment(a):
                    return await a.read()
        if not png:
            return await ctx.author.avatar_url.read()
        else:
            return await ctx.author.avatar_url_as(format="png").read()

    # attachments?
    if attach := ctx.message.attachments:
        a = attach[0]
        if check_attachment(a):
            return await a.read()

    if arg is not None:

        # emojis - is it an emoji?
        try:
            _emoji = await PartialEmojiConverter().convert(ctx, arg)
            if not png:
                return await _emoji.url.read()
            else:
                return await _emoji.url_as(format="png").read()
        except PartialEmojiConversionFailure:
            pass

        # is it a user? if so, get their avatar
        try:
            _user = await BetterMemberConverter().convert(ctx, arg)
            if not png:
                return await _user.avatar_url.read()
            else:
                return await _user.avatar_url_as(format="png").read()
        except (MemberNotFound, UserNotFound):
            pass

        # default emoji
        emoji = arg.replace("\U0000fe0f", "")
        try:
            uc_id = f'{ord(str(emoji)):x}'
            arg = f"https://twemoji.maxcdn.com/v/latest/72x72/{uc_id}.png"

            async with ctx.bot.session.get(arg) as response:
                if response.status == 200:
                    return await response.read()

        except:
            pass

        # finally, getting the image via url.
        try:
            async with ctx.bot.session.get(arg) as response:
                if response.status == 200:
                    return await response.read()
        except aiohttp.InvalidURL:
            pass

    # fallback
    return await fallback()


class NotNumber(Converter):
    def __init__(self, is_float=False):
        self._ = is_float

    async def convert(self, ctx, argument):
        _method = float if self._ else int
        try:
            return _method(argument)
        except ValueError:
            raise UserInputError()


class BetterMemberConverter(Converter):
    async def convert(self, ctx, argument):
        """
        This will raise MemberNotFound if the member is not found.
        """
        try:
            return await MemberConverter().convert(ctx, argument)
        except MemberNotFound:
            # Let's try a utils.find:
            def check(member):
                return (
                    member.name.lower() == argument.lower() or
                    member.display_name.lower() == argument.lower() or
                    str(member).lower() == argument.lower() or
                    str(member.id) == argument
                )
            if found := discord.utils.find(check, ctx.guild.members):
                return found
            raise MemberNotFound(argument)


class BetterUserConverter(Converter):
    async def convert(self, ctx, argument):
        """
        This will take into account members if a guild exists.
        Raises UserNotFound if the user is not found.
        """
        if ctx.guild:
            try:
                return await BetterMemberConverter().convert(ctx, argument)
            except MemberNotFound:
                pass

        try:
            return await UserConverter().convert(ctx, argument)
        except UserNotFound:
            def check(user):
                return (
                    user.name.lower() == argument.lower() or
                    str(user).lower() == argument.lower() or
                    str(user.id) == argument
                )
            if found := discord.utils.find(check, ctx.bot.users):
                return found
            raise UserNotFound(argument)


def CasinoBet(minimum=100, maximum=500000):

    class _Wrapper(Converter, int):
        async def convert(self, ctx, arg):
            _all = await ctx.bot.db.get("users", ctx.author, "shrimp")

            try:
                amount = util.get_amount(_all, minimum, maximum, arg)
            except util.NotAnInteger:
                await ctx.send("Bet amount must be a positive integer.")
                raise
            except util.NotEnough:
                await ctx.send("You don't have that many shrimp.")
                raise
            except util.PastMinimum:
                await ctx.send(f"The minimum bet for this command is {core.SHRIMP} **{minimum:,} Shrimp**.")
                raise
            except ZeroDivisionError:
                await ctx.send("C'mon, really? You can't divide by zero, you should know better.")
                raise
            else:
                return amount

    return _Wrapper


def Investment(minimum=500, maximum=50000000):

    class _Wrapper(Converter, int):
        async def convert(self, ctx, arg):
            _all = await ctx.bot.db.get("users", ctx.author, "shrimp")

            try:
                amount = util.get_amount(_all, minimum, maximum, arg)
            except util.NotAnInteger:
                await ctx.send("Investment amount must be a positive integer.")
                raise
            except util.NotEnough:
                await ctx.send("You don't have that many shrimp.")
                raise
            except util.PastMinimum:
                await ctx.send(f"The minimum investment is {core.SHRIMP} **{minimum:,} Shrimp**.")
                raise
            except ZeroDivisionError:
                await ctx.send("C'mon, really? You can't divide by zero, you should know better.")
                raise
            else:
                return amount

    return _Wrapper


def VaultTransaction(method):

    class _Wrapper(Converter, int):
        async def convert(self, ctx, arg):
            _vault = await ctx.bot.db.get("users", ctx.author, "vault")
            _all = (
                await ctx.bot.db.get("users", ctx.author, "shrimp")
                if method == "deposit" else _vault
            )
            _max = (
                await ctx.bot.db.sum("users", ctx.author, "vault_space", "expanded_vault_space") - _vault
                if method == "deposit" else await ctx.bot.db.get("users", ctx.author, "vault")
            )
            if _max <= 0:
                await ctx.send(
                    "Your vault is full!"
                    if method == "deposit" else
                    "You don't have any shrimp in your vault."
                )
                raise util.NotAnInteger()

            try:
                amount = util.get_amount(_all, 0, _max, arg)
                if amount <= 0:
                    raise util.NotAnInteger()
            except util.NotAnInteger:
                await ctx.send(f"{method.title()} amount must be a positive integer.")
                raise
            except util.NotEnough:
                await ctx.send(
                    "You don't have that many shrimp."
                    if method == "deposit" else
                    "You don't have that many shrimp in your vault."
                )
                raise
            except ZeroDivisionError:
                await ctx.send("C'mon, really? You can't divide by zero, you should know better.")
                raise
            else:
                return amount

    return _Wrapper


class TimeConverter(Converter):
    async def convert(self, ctx, argument):
        if match := SHORT_TIME.fullmatch(argument):
            _total = 0
            for possible_group in (intervals := {
                "seconds": 1,
                "minutes": 60,
                "hours": 3600,
                "days": 86400,
                "weeks": 86400 * 7,
                "months": 86400 * 30,
                "years": 86400 * 365
            }):
                if group := match.group(possible_group):
                    try:
                        _value = float(group)
                    except ValueError:
                        raise
                    else:
                        _total += intervals[possible_group] * _value
            return _total
        raise BadArgument("Invalid time.")


class TimeParser(Converter):
    calendar = pdt.Calendar(version=pdt.VERSION_CONTEXT_STYLE)

    def __init__(self, converter=None, *, default=None):
        if isinstance(converter, type) and issubclass(converter, Converter):
            converter = converter()

        if converter is not None and not isinstance(converter, Converter):
            raise TypeError('commands.Converter subclass necessary.')

        self.converter = converter
        self.default = default

    async def check_constraints(self, ctx, now, remaining):
        if self.dt < now:
            raise BadArgument('This time is in the past.')

        if not remaining:
            if self.default is None:
                raise BadArgument('Missing argument after the time.')
            remaining = self.default

        if self.converter is not None:
            self.arg = await self.converter.convert(ctx, remaining)
        else:
            self.arg = remaining
        return self

    def copy(self):
        cls = self.__class__
        obj = cls.__new__(cls)
        obj.converter = self.converter
        obj.default = self.default
        return obj

    async def convert(self, ctx, argument):
        result = self.copy()
        try:
            calendar = self.calendar
            now = ctx.message.created_at

            try:
                regex_parsed = await TimeConverter().convert(ctx, argument)
                return await self.check_constraints(ctx, regex_parsed)
            except BadArgument:
                pass

            if argument.endswith('from now'):
                argument = argument[:-8].strip()

            if argument[0:6] in ('me to ', 'me in ', 'me at '):
                argument = argument[6:]

            invalid_message = "I couldn't parse a time or date from your argument. Maybe re-word?"
            elements = calendar.nlp(argument, sourceTime=now)
            if elements is None or len(elements) == 0:
                raise BadArgument(invalid_message)

            dt, status, begin, end, dt_string = elements[0]

            if not status.hasDateOrTime:
                raise BadArgument(invalid_message)

            if begin not in (0, 1) and end != len(argument):
                raise BadArgument(invalid_message)

            if not status.hasTime:
                dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

            if status.accuracy == pdt.pdtContext.ACU_HALFDAY:
                dt = dt.replace(day=now.day + 1)

            result.dt = dt
            remaining = None

            if begin in (0, 1):
                if begin == 1:
                    if argument[0] != '"':
                        raise BadArgument('Invalid quotes.')

                    if end >= len(argument) or argument[end] != '"':
                        raise BadArgument('Invalid quotes.')

                    remaining = argument[end + 1:].lstrip(' ,.!')
                else:
                    remaining = argument[end:].lstrip(' ,.!')
            elif len(argument) == end:
                remaining = argument[:begin].strip()

            return await result.check_constraints(ctx, now, remaining)
        except:
            raise



def flag(*names):

    class _Wrapper(Converter):
        async def convert(self, ctx, arg):
            if arg.lstrip('-') not in names:
                raise
            return True

    return typing.Optional[_Wrapper]
