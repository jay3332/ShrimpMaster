import core
import discord
from discord import utils
from discord.ext import commands
from util import paginators


class ShrimpMasterHelpCommand(commands.MinimalHelpCommand):
    """ ShrimpMaster's help command.
        This has currently been dropped (in favor of manual help command) - will be revised in discord.py 2.0.
                                   ^ why? because discord-flags is shitty and it breaks this,
                                     there is an easy but messy fix that i don't like.
                                     discord.py 2.0 should have support for flags, however
    """

    def get_command_signature(self, command):
        return f"{self.clean_prefix}{command.qualified_name} {getattr(command, 'usage', '') or ''}"

    @staticmethod
    def cog_is_available(cog):
        return cog.qualified_name not in ('Admin', 'Jishaku')

    def get_cogs(self):
        _cogs = list(self.context.bot.cogs.values())
        return [_ for _ in _cogs if self.cog_is_available(_)]

    async def send_bot_help(self, mapping):
        # Let's just list the cogs and it's commands
        embed = discord.Embed(color=core.COLOR, timestamp=self.context.now)

        embed.description = (
            "**Welcome to ShrimpMaster!**\n"
            "Get help on a specific category by running `{0}help <category>`.\n"
            "You can even get help on a single command by running `{0}help <command>`!\n\n"
            "[**Support Server**]({1}) • [**Bot Invite**]({2})"
        ).format(
            self.clean_prefix,
            core.SUPPORT_SERVER,
            utils.oauth_url(
                self.context.bot.user.id,
                core.RECOMMENDED_PERMISSIONS,
                self.context.guild
            )
        )
