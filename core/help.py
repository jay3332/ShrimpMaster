import core
import discord
import asyncio
from discord import utils
from discord.ext import commands, menus
from util.paginators import MenuPages
from util.util import duration_strf


class HelpMenu(MenuPages):
    def __init__(self, src):
        super().__init__(src)

    @menus.button("\N{WHITE QUESTION MARK ORNAMENT}", position=menus.Last(5))
    async def show_signature_help(self, _):
        embed = discord.Embed(color=core.COLOR, timestamp=self.ctx.now)
        embed.set_author(name=f"{self.bot.user.name} - Help", icon_url=self.bot.avatar)
        embed.set_footer(text=f"You were on page {self.current_page+1}.")

        for name, value in (
            ('<argument>', 'This is a required argument.'),
            ('[argument]', 'This is an optional argument.'),
            ('<A | B>', 'This means that this argument can either be A or B.'),
            ('[A | B]', 'Similar to the previous one, but the argument is optional.'),
            ('<\'argument\'>', 'This argument should be typed exactly as shown.'),
            ('<argument...>', 'You can use this argument multiple times.'),
            ('<argument=X>', 'This means that X is the default value for the argument if none is passed.')
        ):
            embed.add_field(name=f'`{name}`', value=value, inline=False)

        no_mention = discord.AllowedMentions.none()
        await self.ctx.maybe_edit(self.message, embed=embed, allowed_mentions=no_mention)

        async def go_back():
            await asyncio.sleep(45)
            await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back())


class HelpPageSource(menus.ListPageSource):
    def __init__(self, _help, _commands):
        super().__init__(sorted(_commands.keys(), key=lambda c: c.qualified_name), per_page=6)
        self.commands = _commands
        self.help_command = _help
        self.prefix = _help.clean_prefix

    @staticmethod
    def format_cog(_commands):
        future = '\u2002'.join(f"`{c}`" for c in _commands)
        return future[:1024]

    async def format_page(self, menu, cogs):
        opening_note = self.help_command.get_opening_note()
        embed = discord.Embed(color=core.COLOR, timestamp=menu.ctx.now, description=opening_note)
        embed.set_author(name=f"{menu.ctx.bot.user.name} - Help", icon_url=menu.ctx.bot.avatar)

        for cog in cogs:
            if self.help_command.cog_is_available(cog):
                _commands = self.commands.get(cog)
                if _commands:
                    qual_name = cog.qualified_name
                    command_count = len(_commands)
                    embed.add_field(
                        name=f'{core.HELP_EMOJIS.get(qual_name, "")} **{qual_name}** ({command_count:,} command{"s" if command_count!=1 else ""})',
                        value=self.format_cog(_commands),
                        inline=False
                    )

        embed.set_footer(text=f"Page {menu.current_page+1}/{self.get_max_pages()}")
        return embed


class CogHelpPageSource(menus.ListPageSource):
    def __init__(self, cog, _commands, *, help_command):
        super().__init__(entries=_commands, per_page=5)
        self.cog = cog
        self.help = help_command
        self.ctx = help_command.context
        self.title = f'Category: {self.cog.qualified_name}'
        self.description = f"{len(_commands)} command{'s' if len(_commands)!=1 else ''}\n" \
                           f"Use `{self.ctx.clean_prefix}help <command>` for help on a command."

    async def format_page(self, menu, _commands):
        embed = discord.Embed(title=self.title, description=self.description, color=core.COLOR, timestamp=self.ctx.now)

        for command in _commands:
            signature = self.help.get_command_signature(command)
            embed.add_field(name=signature, value=self.help.get_command_brief(command), inline=False)

        if (maximum := self.get_max_pages()) > 1:
            embed.set_footer(text=f"Page {menu.current_page+1}/{maximum}")

        return embed


class GroupHelpPageSource(menus.ListPageSource):
    def __init__(self, group, subcommands, help_command):
        super().__init__(entries=subcommands, per_page=6)
        self.group = group
        self.subcommands = subcommands
        self.help = help_command

    async def format_page(self, menu, subcommands):
        embed = self.help.get_base_command_embed(self.group)
        if len(subcommands) <= 0:
            return embed

        field = "\n".join(
            f'**{self.help.get_command_signature(c)}** - {self.help.get_command_brief(c)}'
            for c in subcommands
        )
        embed.add_field(name=f"Subcommands ({len(self.subcommands)})", value=field, inline=False)

        if (maximum := self.get_max_pages()) > 1:
            embed.set_footer(text=f"Page {menu.current_page+1}/{maximum}")
        return embed


class ShrimpMasterHelpCommand(commands.HelpCommand):
    """ ShrimpMaster's help command. """

    def __init__(self, **options):
        super().__init__(command_attrs={
            "aliases": ("commands", "cmds", "h")
        }, **options)

    def get_opening_note(self):
        return (
            "**Welcome to ShrimpMaster!**\n"
            "[**Support Server**]({1}) • [**Bot Invite**]({2})\n"
            "Get help on a command category by running `{0}{3} <category>`.\n"
            "Get help on a specific command by running `{0}{3} <command>`."
        ).format(
            self.clean_prefix,
            core.SUPPORT_SERVER,
            utils.oauth_url(
                self.context.bot.user.id,
                discord.Permissions(core.RECOMMENDED_PERMISSIONS),
                self.context.guild
            ),
            self.invoked_with
        )

    def get_command_signature(self, command):
        return f"{self.clean_prefix}{command.qualified_name} {getattr(command, 'usage', '') or ''}"

    @staticmethod
    def get_command_description(command):
        return getattr(command, "description", getattr(command, "help", "This command is not documented."))

    def get_command_brief(self, command):
        return getattr(command, "brief", self.get_command_description(command))

    @staticmethod
    def cog_is_available(cog):
        return cog.qualified_name not in ('Admin', 'Jishaku')

    def get_cogs(self):
        _cogs = list(self.context.bot.cogs.values())
        return [_ for _ in _cogs if self.cog_is_available(_)]

    @staticmethod
    def remove_hidden_commands(_commands):
        return [c for c in _commands if not c.hidden]

    def get_base_command_embed(self, command):
        embed = discord.Embed(color=core.COLOR, timestamp=self.context.now)
        embed.set_author(name=f"{self.context.bot.user.name} - Help", icon_url=self.context.bot.avatar)

        embed.title = self.get_command_signature(command)
        embed.description = self.get_command_description(command)

        _aliases = "\u2002".join(f'`{alias}`' for alias in [command.name, *command.aliases])
        embed.add_field(name="Aliases", value=_aliases, inline=False)

        if isinstance(command, (core.Command, core.Group)):
            embed.add_field(name="Permissions", value=(
                f"You: {', '.join(getattr(command, 'perms', []) or ['None'])}\n"
                f"Me: {', '.join(getattr(command, 'bot_perms', []) or ['None'])}"
            ), inline=False)

            _cooldown = getattr(command, "cooldown", (0, 0))
            if tuple(_cooldown) == (0, 0):
                _cd_text = "None"
            else:
                _cd_text = (
                    f"Default Cooldown: {duration_strf(_cooldown[0])}\n"
                    f"Premium Cooldown: {duration_strf(_cooldown[1])}"
                )
            embed.add_field(name="Cooldown", value=_cd_text)

            _examples = getattr(command, "examples", ["No examples provided."]) or ["No examples provided."]
            embed.add_field(name="Examples", value="\n".join(_examples))

        return embed

    async def send_bot_help(self, mapping):
        parsed = {}
        for command in self.remove_hidden_commands(self.context.bot.commands):
            if command.cog is None:
                continue
            try:
                parsed[command.cog].append(command)
            except KeyError:
                parsed[command.cog] = [command]

        menu = HelpMenu(HelpPageSource(self, parsed))
        await menu.start(self.context)

    async def send_cog_help(self, cog):
        cmds = self.remove_hidden_commands(sorted(cog.get_commands(), key=lambda c: c.qualified_name))
        menu = HelpMenu(CogHelpPageSource(cog, cmds, help_command=self))
        await menu.start(self.context)

    async def send_group_help(self, group):
        cmds = self.remove_hidden_commands(group.commands)
        menu = HelpMenu(GroupHelpPageSource(group, cmds, self))
        await menu.start(self.context)

    async def send_command_help(self, command):
        await self.context.send(embed=self.get_base_command_embed(command))
