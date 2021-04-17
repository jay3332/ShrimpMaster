import core
import discord
from util import paginators


class Config(core.Cog):

    @core.group(
        name="shortcuts",
        aliases=("sc", "shortcut"),
        cooldown=(3, 2),
        description="View or modify your current shortcuts.",
        usage="[ add <shortcut> <command> | remove <shortcut> | clear | search ]",
        invoke_without_command=True
    )
    async def _shortcuts(self, ctx):
        shortcuts = await ctx.db.fetch("SELECT * FROM shortcuts WHERE user_id=$1", ctx.author.id)
        fields = ([{
            "name": shortcut["name"],
            "value": shortcut["command"][:1024],
            "inline": False
        } for shortcut in shortcuts] if len(shortcuts)>0 else [{
            "name": "No shortcuts!",
            "value": f"To create a shortcut, use `{ctx.clean_prefix}shortcuts add`"
        }])

        _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        _embed.set_author(name=f"{ctx.author.name}'s Shortcuts", icon_url=ctx.avatar)
        _embed.description = f"{len(shortcuts)}/{core.MAX_SHORTCUTS} shortcuts"
        await paginators.field_paginate(ctx, _embed, fields, footer="Page {page}")


    @_shortcuts.command(
        name="add",
        aliases=("make", "create", "+"),
        cooldown=(2, 1),
        description="Create a new shortcut.",
        usage="<shortcut> <command>",
        examples=(
            "shortcuts add coffee buy coffee --use-after",
            "shortcuts add \"some shortcut\" shop amogus --no-reply"
        )
    )
    async def _shortcuts_add(self, ctx, shortcut, *, command):
        if len(shortcut) > 64:
            return await ctx.send("Length of shortcut must be under 64 characters.")
        shortcut = shortcut.strip().lower()
        if len(shortcut) < 1:
            return await ctx.send("Shortcut name is required.")
        if ctx.bot.get_command(shortcut):
            return await ctx.send("Shortcut name must not be the name of an existing command.")
        shortcuts = ctx.db.shortcut_cache.get(ctx.author.id, [])
        if len(shortcuts) >= core.MAX_SHORTCUTS:
            return await ctx.send(f"You can only have up to **{core.MAX_SHORTCUTS:,}** shortcuts.")
        if any(sc["name"] == shortcut for sc in shortcuts):
            return await ctx.send("A shortcut with that name already exists.")

        await ctx.db.add_shortcut(ctx.author, shortcut, command)
        await ctx.send(f"Shortcut `{shortcut}` created.")


    @core.group(
        name="prefix",
        aliases=("pr", "prefixes"),
        cooldown=(0.5, 0.2),
        brief="View or modify prefixes.",
        description=(
            "View and/or modify your server's prefixes. "
            "You can have up to 20 prefixes at once."
        ),
        usage="prefix [add|remove|clear|set] [prefixes]",
        examples=(
            "prefix",
            "prefix add !",
            "prefix add \"hey, \"",
            "prefix add ! ? -",
            "prefix remove !",
            "prefix remove \"hey, \"",
            "prefix clear"
        ),
        bot_perms=("Send Messages", "Embed Links"),
        invoke_without_command=True
    )
    @core.check(bot_perms=('send_messages', 'embed_links'))
    async def _prefix(self, ctx):

        await ctx.cd()
        _prefixes = await ctx.bot.db.get("guilds", ctx.guild, "prefixes")
        embed = discord.Embed(
            color=core.COLOR,
            timestamp=ctx.now,
            title=f"{len(_prefixes)} prefix{'es' if len(_prefixes)!=1 else ''}",
            description="\n".join(_prefixes)
        )
        await ctx.send(embed)

    @_prefix.command(
        name="add",
        aliases=("create", "make", "a", "+"),
        cooldown=(1, 0.5),
        brief="Add prefixes.",
        description=(
            "Add prefixes to your server. "
            "You can add multiple prefixes at once by seperating them by space, "
            "and if your prefix has a space, surround it in quotes."
        ),
        usage="prefix add <...prefixes>",
        examples=(
            "prefix add !",
            "prefix add ! ? -",
            "prefix add \"hey, \"",
            "prefix add \"hey, \" ! ?"
        ),
        perms="Server Administrator"
    )
    @core.check(perms=("administrator",))
    async def _prefix_add(self, ctx, *prefixes):
        await ctx.cd()
        if len(prefixes) <= 0:
            return await ctx.send("Please give me prefixes to add.")

        _prefixes = await ctx.bot.db.get("guilds", ctx.guild, "prefixes")
        if len(prefixes) + len(_prefixes) > 20:
            return await ctx.send("You can only have a maximum of 20 prefixes.")

        if any(len(pf) > 32 for pf in prefixes):
            return await ctx.send("Lengths of prefixes must be under 32 characters.")

        _new = [*prefixes, *_prefixes]
        await ctx.bot.db.set("guilds", "prefixes", ctx.guild, _new)
        await ctx.send(f"Successfully added {len(prefixes)} prefix{'es' if len(prefixes)!=1 else ''}")


def setup(client):
    cog = Config(client)
    client.add_cog(cog)
