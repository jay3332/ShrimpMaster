import core
import typing
import discord
from io import BytesIO
from util import converters, util, paginators
from humanize import naturaltime
from discord.ext import commands
from markdown import markdown as _md
from mystbin import APIError


def UserConverterOr(*valid_strings):
    class _Wrapper(converters.BetterUserConverter):
        async def convert(self, ctx, argument):
            if argument.lower() in valid_strings:
                return argument.lower()

            return await super().convert(ctx, argument)
    return _Wrapper


class Utility(core.Cog):

    @core.command(
        name="avatar",
        aliases=("av", "pfp", "logo", "icon"),
        usage="[user | 'server']",
        description="View someone's avatar.",
        examples=(
            "avatar",
            "avatar @User",
            "avatar server"
        ),
        cooldown=(3, 1)
    )
    async def _avatar(self, ctx, *, user: typing.Optional[UserConverterOr("server", "guild")]):
        await ctx.cd()
        user = user or ctx.author
        if isinstance(user, str):
            available_links = ['png', 'jpg', 'webp']
            if ctx.guild.is_icon_animated():
                available_links.append("gif")

            avatar_links = " **•** ".join(
                f"[**{_format.upper()}**]({ctx.guild.icon_url_as(format=_format)})"
                for _format in available_links
            )

            fp = BytesIO(await ctx.guild.icon_url.read())
            ext = "png" if not ctx.guild.is_icon_animated() else "gif"
            file = discord.File(fp, filename := f"{ctx.guild.id!s}.{ext}")

            embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
            embed.set_author(name=f"Server Icon for {ctx.guild.name}")
            embed.set_footer(text=f"Guild ID: {ctx.guild.id}")
            embed.set_image(url=f"attachment://{filename}")
            embed.description = avatar_links

            await ctx.send(embed=embed, file=file)

        elif isinstance(user, (discord.Member, discord.User)):

            available_links = ['png', 'jpg', 'webp']
            if user.is_avatar_animated():
                available_links.append("gif")

            avatar_links = " **•** ".join(
                f"[**{_format.upper()}**]({user.avatar_url_as(format=_format)})"
                for _format in available_links
            )

            fp = BytesIO(await user.avatar_url.read())
            ext = "png" if not user.is_avatar_animated() else "gif"
            file = discord.File(fp, filename := f"{user.id!s}.{ext}")

            color = core.COLOR
            if isinstance(user, discord.Member) and len(user.roles)>1:
                color = user.colour
            if color.value <= 0:
                color = core.COLOR
            embed = discord.Embed(color=color, timestamp=ctx.now)
            embed.set_author(name=f"Avatar for {user.name}")
            embed.set_footer(text=f"User ID: {user.id}")
            embed.set_image(url=f"attachment://{filename}")
            embed.description = avatar_links

            await ctx.send(embed=embed, file=file)

    @core.command(
        name="md2html",
        aliases=("markdowntohtml", "mdtohtml", "markdown2html"),
        description="Convert markdown to HTML... because why not?",
        usage="<markdown text>",
        cooldown=(3, 1)
    )
    async def _md2html(self, ctx, *, markdown):
        html = _md(markdown, extensions=['extra'])
        if len(html) < 1990:
            return await ctx.send(f"```html\n{html}```")
        try:
            myst = await ctx.bot.mystbin.post(html, syntax="html")
        except APIError:
            return await ctx.send("Data too large.")
        else:
            await ctx.send(f'<{myst}>')

    @core.command(
        name="remind",
        aliases=("rm", "remindme", "reminder"),
        description="Creates a reminder for you.",
        usage="<when> [what]",
        cooldown=(5, 2)
    )
    async def _remind(self, ctx, when: converters.TimeConverter, *, what):
        await ctx.bot.create_relative_timer(
            when, "reminder", ctx.channel.id, ctx.author.id, what, ctx.message.jump_url
        )
        await ctx.send(f"{util.choice(('Alright', 'Okay', 'Sure thing'))}, in {util.duration_strf(when)}: {what}")

    @commands.Cog.listener()
    async def on_reminder_timer_complete(self, timer):
        channel_id, user_id, what, jump_url = timer.args
        if channel := await self.client.getch(self.client.get_channel, self.client.fetch_channel, channel_id):
            try:
                await channel.send(f"<@{user_id}>, {naturaltime(timer.created_at, when=self.client.now)}: {what}\n\n{jump_url}")
            except (discord.HTTPException, discord.Forbidden):
                pass


def setup(client):
    client.add_cog(Utility(client))
