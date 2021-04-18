import traceback
import contextlib
import textwrap
import core
import discord
import util
import inspect
import asyncio
import aiohttp
import import_expression
from discord.ext import commands
from io import StringIO


class Scope:
    """
    A class to represent scopes.
    """

    def __init__(self, globals_: dict = None, locals_: dict = None):
        self.globals: dict = globals_ or {}
        self.locals: dict = locals_ or {}

    def clear_intersection(self, other_dict):
        for key, value in other_dict.items():
            if key in self.globals and self.globals[key] is value:
                del self.globals[key]
            if key in self.locals and self.locals[key] is value:
                del self.locals[key]

        return self

    def update(self, other):
        self.globals.update(other.globals)
        self.locals.update(other.locals)
        return self

    def update_globals(self, other: dict):
        self.globals.update(other)
        return self

    def update_locals(self, other: dict):
        self.locals.update(other)
        return self


class EvalManager:
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self._retain_scope = True
        self._scope = Scope()

    @property
    def scope(self):
        if self._retain_scope:
            return self._scope
        return Scope()

    def retain_scope(self):
        self._retain_scope = res = not self._retain_scope
        if res:
            self._scope = Scope()
        return res

    def get_env(self, ctx):
        return {
            "_": self._last_result,
            "ctx": ctx,
            "discord": discord,
            "commands": commands,
            "author": ctx.author,
            "client": ctx.bot,
            "bot": ctx.bot,
            "channel": ctx.channel,
            "guild": ctx.guild,
            "message": ctx.message,
            "msg": ctx.message,
            "reference": ctx.message.reference,
            "find": discord.utils.find,
            "get": discord.utils.get,
            "core": core,
            "util": util,
            "inspect": inspect,
            "source": inspect.getsource,
            "asyncio": asyncio,
            "aiohttp": aiohttp,
            "session": ctx.bot.session,
            "timers": ctx.bot.timers,
            "__scope": self._scope
        }

    async def evaluate(self, ctx, code):
        _env = self.get_env(ctx)
        _scope = self._scope
        _scope.update_globals(_env)

        block = "async def __evaluate_code():\n"
        block += textwrap.indent(code, "  ")  # 2 spaces because that's how discord does it

        async def _send_result(stdout_, result_):
            try:
                await ctx.message.add_reaction(core.CHECK)
            except discord.Forbidden:
                pass

            if res := stdout_.getvalue():
                return await ctx.send(res)

            if not result_:
                return

            if result_ == "":
                return await ctx.send("\u200b")

            self._last_result = result_

            if isinstance(result_, discord.Embed):
                return await ctx.send(embed=result_)

            if isinstance(result_, discord.File):
                return await ctx.send(file=result_)

            if isinstance(result_, (str, int)):
                return await ctx.send(result_)

            return await ctx.send(repr(result_))


        with StringIO() as stdout:
            try:
                import_expression.exec(block, _scope.globals, _scope.locals)
                with contextlib.redirect_stdout(stdout):
                    _function = _scope.locals['__evaluate_code']
                    _coro = _function()

                    if inspect.isasyncgenfunction(_function):
                        async for output in _coro:
                            await _send_result(stdout, output)
                        return

                    result = await _coro

                if out := await _send_result(stdout, result):
                    try:
                        await out.add_reaction(core.TRASH)
                    except discord.Forbidden:
                        pass
                    return out

            except Exception as error:
                try:
                    await ctx.message.add_reaction(core.CROSS)
                except discord.Forbidden:
                    pass

                _base = (type(error), error, error.__traceback__)
                _exception = ''.join(traceback.format_exception(*_base, limit=2))
                message = await ctx.send(f"```py\n{_exception}```"[:2000])
                await message.add_reaction(core.TRASH)
