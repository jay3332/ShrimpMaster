import os
import core
import discord
from discord.ext import commands
from functools import partial


INVITE = '<:invite:833380353141768252>'


class Channels:
    NEW_GUILDS = 833377186244591616
    COMMAND_LOG = 833399473346445332
    WHITELIST = (414556245178056706,
                 691089753680117792)


class Logging(core.Cog):

    def __init__(self, bot):
        super().__init__(bot)
        self.getch_channel = partial(bot.getch, bot.get_channel, bot.fetch_channel)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id not in Channels.WHITELIST:
            return

        if str(payload.emoji) != INVITE:
            return

        entry = await self.client.db.fetchrow("SELECT * FROM guild_stats WHERE message_id=$1", payload.message_id)
        if not entry:
            return

        try:
            guild = self.client.get_guild(entry['guild_id'])
        except discord.NotFound:
            return

        try:
            channel = await self.getch_channel(Channels.NEW_GUILDS)
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        try:
            original_embed: discord.Embed = message.embeds[0]
        except IndexError:
            return
        if not guild.text_channels:
            return

        original_embed.remove_field(-1)
        try:
            invite = await guild.text_channels[0].create_invite()
            await self.client.db.execute("UPDATE guild_stats SET invite=$1 WHERE message_id=$2", str(invite), payload.message_id)
        except discord.Forbidden:
            invite = "No permissions"
        except discord.HTTPException:
            invite = "Request error (Most likely rate limited)"

        original_embed.add_field(name="Guild Invite Link", value=invite, inline=False)
        await message.edit(embed=original_embed)


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        channel = await self.getch_channel(Channels.NEW_GUILDS)

        embed = discord.Embed(color=core.COLOR, timestamp=self.client.now)
        embed.set_author(name="Joined a guild", icon_url=self.client.avatar)
        embed.set_thumbnail(url=guild.icon_url)

        embed.title = guild.name
        embed.description = f'ID: {guild.id}\n{guild.member_count:,} [cached] members'

        embed.add_field(name="Owner", value=(
            f"{guild.owner}\nID: {guild.owner.id}"
        ), inline=False)

        embed.add_field(name="Guild Invite Link", value=(
            "For privacy purposes, I don't create an invite link for every guild.\n"
            f"At your own risk, react with {INVITE} to create an invite for this guild."
        ), inline=False)

        guild_count = len(self.client.guilds)
        embed.set_footer(text=f"Guild Count: {guild_count}")

        message = await channel.send(embed=embed)
        await message.add_reaction(INVITE)

        await self.client.db.execute(
            "INSERT INTO guild_stats (guild_id, time_joined, guild_count, message_id) VALUES ($1, $2, $3, $4)",
            guild.id, self.client.now, guild_count, message.id
        )


    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        channel = await self.getch_channel(Channels.NEW_GUILDS)

        embed = discord.Embed(color=core.RED, timestamp=self.client.now)
        embed.set_author(name="Removed from a guild", icon_url=self.client.avatar)
        embed.set_thumbnail(url=guild.icon_url)

        embed.title = guild.name
        embed.description = f'ID: {guild.id}\n{guild.member_count:,} [cached] members'

        embed.add_field(name="Owner", value=(
            f"{guild.owner}\nID: {guild.owner.id}"
        ), inline=False)

        embed.add_field(name="Guild Invite Link", value=(
            "For privacy purposes, I don't create an invite link for every guild.\n"
            f"At your own risk, react with {INVITE} to create an invite for this guild."
        ), inline=False)

        guild_count = len(self.client.guilds)
        embed.set_footer(text=f"Guild Count: {guild_count}")

        message = await channel.send(embed=embed)
        await message.add_reaction(INVITE)

        await self.client.db.execute(
            "INSERT INTO guild_stats (guild_id, time_joined, guild_count, is_removal, message_id) VALUES ($1, $2, $3, $4, $5)",
            guild.id, self.client.now, guild_count, True, message.id
        )

    @commands.Cog.listener()
    async def on_command(self, ctx):
        webhook_url = os.environ['COMMAND_LOG_WEBHOOK_URL']
        webhook = discord.Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter(self.client.session))

        embed = discord.Embed(color=core.COLOR, timestamp=self.client.now)
        embed.description = ctx.message.content
        embed.set_author(name=ctx.author, icon_url=ctx.avatar)
        embed.add_field(name="Author", value=(
            f"{ctx.author}\n"
            f"ID: {ctx.author.id}"
        ), inline=False)
        embed.add_field(name="Channel", value=(
            f"{ctx.channel.name}\n"
            f"ID: {ctx.channel.id}"
        ), inline=False)
        if ctx.guild:
            embed.add_field(name="Guild", value=(
                f"{ctx.guild.name}\n"
                f"ID: {ctx.guild.id}"
            ))

        embed.set_footer(text=f"Message ID: {ctx.message.id}")
        jump_embed = discord.Embed(color=core.EMBED_COLOR, description=f"[Jump!]({ctx.message.jump_url})")

        await webhook.send(embeds=(embed, jump_embed))


def setup(client):
    client.add_cog(Logging(client))
