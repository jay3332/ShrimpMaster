import discord
import core
import math
from typing import Optional
from util import converters, nets, paginators, items, util
from discord.ext import commands


class Transactions(core.Cog):

    @core.command(
        name="withdraw",
        aliases=("wd", "w", "with"),
        usage="<amount>",
        description="Withdraw shrimp from your vault.",
        cooldown=(5, 3)
    )
    async def _withdraw(self, ctx, *, amount: converters.VaultTransaction("withdraw")):

        await ctx.bot.db.add("users", "vault", ctx.author, -amount)
        await ctx.bot.db.add("users", "shrimp", ctx.author, amount)
        await ctx.send(f"{core.WITHDRAW} {core.VAULT} Withdrew **{core.SHRIMP} {amount:,} shrimp** from your vault.")

    @core.command(
        name="deposit",
        aliases=("dep", "dp"),
        usage="<amount>",
        description="Deposit shrimp into your vault.",
        cooldown=(5, 3)
    )
    async def _deposit(self, ctx, *, amount: converters.VaultTransaction("deposit")):
        await ctx.bot.db.add("users", "vault", ctx.author, amount)
        await ctx.bot.db.add("users", "shrimp", ctx.author, -amount)
        await ctx.send(f"{core.DEPOSIT} {core.VAULT} Deposited **{core.SHRIMP} {amount:,} shrimp** into your vault.")

    @core.group(
        name="net",
        usage="[ <net> | shop | buy <net> | equip <net> | unequip ]",
        description="View, shop for, buy, equip, and/or unequip your nets.",
        invoke_without_command=True
    )
    async def _net(self, ctx, *, net: Optional[nets.NetConverter] = None):
        await ctx.invoke(self._net_view, net=net)


    @_net.command(
        name="view",
        aliases=("info", "i", "v"),
        usage="<net>",
        description="View information on a specific net. Allows lookup by both ID and name.",
        cooldown=(2, 0)
    )
    async def _net_view(self, ctx, *, net: Optional[nets.NetConverter] = None):
        await ctx.cd()

        # default to the user's equipped net
        _equipped = await ctx.db.get("users", ctx.author, "net")
        net = net or nets.get_net(_equipped)

        _flags_of = await ctx.db.get("users", ctx.author, "nets")
        _has_net = nets.has_net(_flags_of, net)

        # get the emoji url
        if net.emoji == '':
            _url = "https://invalid-url.com"
        elif net.id == "hand":
            _url = "https://twemoji.maxcdn.com/v/latest/72x72/270b.png"
        else:
            try:
                _partial_emoji = await commands.PartialEmojiConverter().convert(ctx, net.emoji)
                _url = _partial_emoji.url
            except (commands.ConversionError, commands.PartialEmojiConversionFailure):
                _url = ""

        _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        _embed.title = net.name
        _embed.description = net.description
        _embed.add_field(name="Information", value=(
            f"Price: **{core.SHRIMP} {net.price:,} shrimp**\n"
            f"Level Unlocked: **Level {net.level_requirement:,}**\n"
            f"Equipped: **{_equipped == net.id}**"
        ), inline=False)
        _embed.add_field(name="Catch Stats", value=(
            f"Catch Amount: **{core.SHRIMP} {net.catch_amount!s}**\n"
            f"Catch Fail Chance: **{round(net.fail_chance*100, 1)}%**\n"
            f"Golden Shrimp Chance: **{round(net.golden_chance*100, 1)}%**\n"
            f"Golden Shrimp Amount: **{net.golden_amount!s}**"
        ))
        _embed.set_thumbnail(url=_url)
        await ctx.send(_embed, embed_perms=True)

    @_net.command(
        name="shop",
        aliases=("s", "store", "sh"),
        description="View all possible nets you can buy. This sends a paginator, no need to provide page arguments.",
        cooldown=(5, 2)
    )
    async def _net_shop(self, ctx: core.Context):
        await ctx.cd()
        _level = await ctx.db.get("users", ctx.author, 'level')
        _owned = await ctx.db.get("users", ctx.author, "nets")
        _fields = [{
            'name': f"{_net} (" + (
                "Owned)" if nets.has_net(_owned, _net)
                else "🔒 Locked)" if _level < _net.level_requirement
                else f"{core.SHRIMP} {_net.price:,})"
            ),
            'value': _net.description,
            'inline': False
        } for _net in nets.Nets.all()]

        _embed = discord.Embed(color=core.COLOR, title="Net Shop", timestamp=ctx.now)
        _embed.description = f"To buy a net, use `{ctx.clean_prefix}net buy <net>`"
        await paginators.field_paginate(ctx, _embed, _fields, footer="Page {page}")

    @_net.command(
        name="buy",
        aliases=("b", "purchase", "pch"),
        usage="<net>",
        description="Buy/purchase a net. Note that you cannot sell nets, so think twice before making a purchase.",
        cooldown=(10, 4)
    )
    async def _net_buy(self, ctx, *, net: nets.NetConverter):
        await ctx.cd()

        _level = await ctx.db.get("users", ctx.author, "level")
        if net.level_requirement > _level:
            return await ctx.send(f"You're too inexperienced to use this net! Come back when you're **Level {net.level_requirement:,}**.")

        _owned = await ctx.db.get("users", ctx.author, "nets")
        if nets.has_net(_owned, net):
            return await ctx.send("You already own this net.")

        _balance = await ctx.db.get("users", ctx.author, "shrimp")
        if _balance < net.price:
            _diff = net.price-_balance
            return await ctx.send(f"You can't afford this net. Come back when you get {core.SHRIMP} **{_diff:,} more shrimp**.")

        await ctx.db.add("users", "shrimp", ctx.author, -net.price)
        await ctx.db.set("users", "nets", ctx.author, _owned | net.flag)

        _embed = discord.Embed(color=core.GREEN)
        _embed.description = f"{core.CHECK} Successfully bought **{net}**."
        await ctx.db.add_xp(ctx.author, util.random(5, 20))
        await ctx.send(f"💡 Equip your net using `{ctx.clean_prefix}net equip {net.id}`", embed=_embed, embed_perms=True)

    @_net.command(
        name="equip",
        aliases=("eq", "e", "use"),
        usage="<net>",
        description="Equip a net. You must own this net first.",
        cooldown=(5, 3)
    )
    async def _net_equip(self, ctx, *, net: nets.NetConverter):
        await ctx.cd()

        _owned = await ctx.db.get("users", ctx.author, "nets")
        if not nets.has_net(_owned, net):
            return await ctx.send("You don't own this net.")

        await ctx.db.add_xp(ctx.author, util.random(1, 2))
        await ctx.db.set("users", "net", ctx.author, net.id)
        await ctx.send(f"Successfully equipped **{net}**.")

    @_net.command(
        name="unequip",
        aliases=("ueq", "ue", "unuse"),
        description="Unequip your current net.",
        cooldown=(5, 3)
    )
    async def _net_unequip(self, ctx):
        await ctx.cd()

        await ctx.db.set("users", "net", ctx.author, "hand")
        await ctx.send("Successfully unequipped your net.")

    @core.command(
        name="shop",
        aliases=("store", "item", "sh", "iteminfo", "ii"),
        usage="[item]",
        brief="View the current item shop, or view information on an item.",
        description=(
            "View the current items in the shop, or view information on one. "
            "Providing a page number is not necessary, as I send a paginator."
        ),
        cooldown=(3, 1),
        examples=(
            "shop",
            "shop clover"
        )
    )
    async def _shop(self, ctx, *, item: items.ItemConverter = None):
        await ctx.cd()
        if not item:
            # If no item was provided, let's just send the shop
            _buyable_items = [_ for _ in items.Items.all() if _.buyable]
            _items = sorted(_buyable_items, key=lambda _: _.price)

            _fields = [{
                "name": f"{_item!s} ({core.SHRIMP} {_item.price:,} shrimp)",
                "value": _item.brief,
                "inline": False
            } for _item in _items]

            _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
            _embed.title = f"{core.SHRIMP}  Item Shop"
            _embed.description = f"Buy an item using `{ctx.clean_prefix}buy <item>`.\n" \
                                 f"View information on an item using `{ctx.clean_prefix}shop <item>`."

            return await paginators.field_paginate(ctx, _embed, _fields, footer="Page {page}")

        try:
            _emoji = await commands.PartialEmojiConverter().convert(ctx, item.emoji)
            _emoji = _emoji.url
        except commands.PartialEmojiConversionFailure:
            try:
                _emoji = item.emoji.replace("\U0000fe0f", "")
                uc_id = f'{ord(str(_emoji)):x}'
                _emoji = f"https://twemoji.maxcdn.com/v/latest/72x72/{uc_id}.png"
            except (TypeError, ValueError):
                _emoji = ""

        _embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        _embed.title = item.name
        _embed.description = item.description
        _embed.set_thumbnail(url=_emoji)
        _embed.set_footer(text=f"Type: {item.type}")
        _embed.add_field(name="General", value=(
            f"Name: {item.name}\n"
            f"ID: {item.id}\n"
            f"Type: {item.type}"
        ))
        _embed.add_field(name="\u200b", value="\u200b")  # empty field
        _embed.add_field(name="Pricing", value=(
            f"Buy: {core.SHRIMP} {item.price:,} shrimp\n"
            f"Sell: {core.SHRIMP} {item.sell:,} shrimp"
        ))
        _owned = await ctx.db.get("items", ctx.author, item.id)
        _embed.add_field(name="Flexibility", value=(
            f"Buyable: {item.buyable}\n"
            f"Sellable: {item.sellable}\n"
            f"Usable: {item.usable}\n"
            f"Giftable: {item.giftable}"
        ))
        _embed.add_field(name="\u200b", value="\u200b")  # empty field
        _embed.add_field(name="Statistics", value=(
            f"Owned: {_owned:,}\n"
            f"Buy worth: {core.SHRIMP} {_owned*item.price:,} shrimp\n"
            f"Sell worth: {core.SHRIMP} {_owned*item.sell:,} shrimp"
        ))
        await ctx.db.add_xp(ctx.author, 1)
        await ctx.send(embed=_embed)

    @core.command(
        name="remove",
        aliases=("removeitem", "dispose", "ri"),
        usage="<item>",
        description="Removes an active item.",
        cooldown=(5, 2)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    async def _remove(self, ctx, *, item: items.ItemConverter):
        if not item.remover:
            return await ctx.send("That item can't be removed.")
        try:
            await items.remove_item(ctx, item)
        except items.ItemRemovalFailure:
            return
        else:
            await ctx.db.add_xp(ctx.author, util.random(2, 4))
            await ctx.cd()


    @core.command(
        name="use",
        aliases=("u", "useitem"),
        usage="<item> [quantity=1]",
        description="Use an item. Some items can be used in bulk.",
        cooldown=(5, 2)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    async def _use(self, ctx, *, query):

        item: Optional[items.Item] = None
        quantity = "1"
        if _item := items.query_item(query):
            item = _item
        elif len(split := query.split(' ')) > 1:  # We split then rejoin, except leave out the last index
            _item, quantity = " ".join(split[:-1]), split[-1]
            if _item := items.query_item(_item):
                item = _item
            if not item:
                _item, quantity = " ".join(split[1:]), split[0]
                if _item := items.query_item(_item):
                    item = _item
        if not item:
            return await ctx.send(f"Item \"{query}\" not found.")

        if not item.usable:
            return await ctx.send("This item is not usable.")
        if not item.usage:
            return await ctx.send(
                "That item should be usable, however I don't know how to use it. "
                "Maybe this item is a work in progress?"
            )

        _maximum = await ctx.db.get("items", ctx.author, item.id)
        if _maximum <= 0:
            return await ctx.send("You don't own that item - can't really use something you don't have.")
        try:
            quantity = util.get_amount(_maximum, 1, _maximum, quantity)
        except util.PastMinimum:
            return await ctx.send("You must use at least 1 of that item.")
        except util.NotAnInteger:
            return await ctx.send("Please provide a positive integer as your quantity.")
        except util.NotEnough:
            return await ctx.send("You don't have that many of that item.")
        except ZeroDivisionError:
            return await ctx.send("C'mon, really? You can't divide by zero, you should know better.")

        await ctx.cd()

        if not item.use_multiple:
            quantity = 1
        if quantity <= 0:
            return await ctx.send("Quantity must be greater than 0.")
        if quantity > (owned := await ctx.db.get("items", ctx.author, item.id)):
            if quantity == 1 or owned <= 0:
                return await ctx.send("You don't own that item.")
            return await ctx.send(f"You only own {owned:,} out of the requested {quantity:,} items.")

        args = (ctx, item)
        if item.use_multiple:
            args = (ctx, item, quantity)

        try:
            await items.use_item(item.usage, *args)
        except items.ItemUsageFailure:
            return
        else:
            if item.dispose:
                await ctx.db.add("items", item.id, ctx.author, -quantity)
        await ctx.db.add_xp(ctx.author, util.random(2, 4))


    @core.command(
        name="buy",
        aliases=("b", "purchase"),
        usage="<item> [quantity=1]",
        brief="Buy an item.",
        description=(
            "Buy an item. You can provide arguments such as "
            "\"all\", \"half\", fractions, numbers, or percentages to "
            "buy in bulk."
        ),
        cooldown=(4, 2),
        examples=(
            "buy clover",
            "buy clover 4",
            "buy clover all"
        )
    )
    async def _buy(self, ctx, *, query):
        _use_after = False
        _temp_split = query.split()
        if _temp_split[-1].lower() == "--use-after":
            _use_after = True
            query = ' '.join(query.split()[:-1])

        item: Optional[items.Item] = None
        quantity = "1"
        if _item := items.query_item(query):
            item = _item
        elif len(split := query.split()) > 1:  # We split then rejoin, except leave out the last index
            _item, quantity = " ".join(split[:-1]), split[-1]
            if _item := items.query_item(_item):
                item = _item
            if not item:
                _item, quantity = " ".join(split[1:]), split[0]
                if _item := items.query_item(_item):
                    item = _item
        if not item:
            return await ctx.send(f"Item \"{query}\" not found.")

        if not item.buyable:
            return await ctx.send("This item is currently not buyable.")

        _shrimp = await ctx.db.get("users", ctx.author, "shrimp")
        _maximum = math.floor(_shrimp/item.price)

        try:
            quantity = util.get_amount(_maximum, 1, _maximum, quantity)
        except util.PastMinimum:
            return await ctx.send("You must buy at least 1 item.")
        except util.NotAnInteger:
            return await ctx.send("Please provide a positive integer as your quantity.")
        except util.NotEnough:
            return await ctx.send("You don't have enough shrimp to make this purchase.")
        except ZeroDivisionError:
            return await ctx.send("C'mon, really? You can't divide by zero, you should know better.")

        price = quantity * item.price
        if _shrimp < price or quantity <= 0:
            return await ctx.send("You don't have enough shrimp to make this purchase.")

        await ctx.cd()
        await ctx.db.add("users", "shrimp", ctx.author, -price)
        await ctx.db.add("items", item.id, ctx.author, quantity)

        if quantity == 1:
            name = f"an " if any(item.name.startswith(vowel) for vowel in "aeiou") else "a "
            name += f"**{item}**"
        else:
            name = f"{quantity:,} **{item.plural_str}**"

        _embed = discord.Embed(color=core.GREEN, timestamp=ctx.now)
        _embed.set_author(name="Purchase Successful!", icon_url=ctx.avatar)
        _embed.description = f"You bought {name} and paid {core.SHRIMP} **{price:,} shrimp**."
        await ctx.db.add_xp(ctx.author, util.random(1, 4))
        await ctx.send(embed=_embed)

        if _use_after:
            await ctx.invoke(self._use, query=f"{item.id} {quantity}")

    @core.command(
        name="sell",
        alias="se",
        usage="<item> [quantity=1]",
        brief="Sell an item.",
        description=(
            "Sell an item. Items must be sellable, and you must own it."
        ),
        cooldown=(4, 2)
    )
    async def _sell(self, ctx, *, query):

        item: Optional[items.Item] = None
        quantity = "1"
        if _item := items.query_item(query):
            item = _item
        elif len(split := query.split(' ')) > 1:  # We split then rejoin, except leave out the last index
            _item, quantity = " ".join(split[:-1]), split[-1]
            if _item := items.query_item(_item):
                item = _item
            if not item:
                _item, quantity = " ".join(split[1:]), split[0]
                if _item := items.query_item(_item):
                    item = _item
        if not item:
            return await ctx.send(f"Item \"{query}\" not found.")

        if not item.sellable:
            return await ctx.send("This item is currently not sellable.")

        _maximum = await ctx.db.get("items", ctx.author, item.id)
        if _maximum <= 0:
            return await ctx.send("You don't own that item - can't really sell something that you can't have.")
        try:
            quantity = util.get_amount(_maximum, 1, _maximum, quantity)
        except util.PastMinimum:
            return await ctx.send("You must sell at least 1 item.")
        except util.NotAnInteger:
            return await ctx.send("Please provide a positive integer as your quantity.")
        except util.NotEnough:
            return await ctx.send("You don't have that many of that item.")
        except ZeroDivisionError:
            return await ctx.send("C'mon, really? You can't divide by zero, you should know better.")

        await ctx.cd()
        profit = item.sell * quantity
        await ctx.db.add("items", item.id, ctx.author, -quantity)
        await ctx.db.add("users", "shrimp", ctx.author, profit)

        if quantity == 1:
            name = f"an " if any(item.name.startswith(vowel) for vowel in "aeiou") else "a "
            name += f"**{item}**"
        else:
            name = f"{quantity:,} **{item.plural_str}**"

        _embed = discord.Embed(color=core.GREEN, timestamp=ctx.now)
        _embed.set_author(name="Sold!", icon_url=ctx.avatar)
        _embed.description = f"You sold {name} for {core.SHRIMP} **{profit:,} shrimp**."
        await ctx.db.add_xp(ctx.author, util.random(2, 4))
        await ctx.send(embed=_embed)

    @core.command(
        name="sellall",
        aliases=("sellbulk", "bulksell", "sall"),
        usage="<items...>",
        brief="Sell an item.",
        description=(
            "Sell multiple items. Items must be sellable, and you must own it. "
            "Note that this sells ALL of each item."
        ),
        cooldown=(10, 6)
    )
    async def _sellall(self, ctx, *_items: items.ItemConverter):
        if len(_items) <= 0:
            return await ctx.send("Please provide items to sell.")

        for item in _items:
            if not item.sellable:
                return await ctx.send(f"**{item.plural_str}** are not sellable.")

        total = 0
        lines = []
        await ctx.cd()
        for item in _items:
            quantity = await ctx.db.get("items", ctx.author, item.id)
            if quantity <= 0:
                continue
            total += (sell_price := quantity * item.sell)
            await ctx.db.set("items", item.id, ctx.author, 0)
            lines.append(f"Sold {item.quantitize(quantity)} for {core.SHRIMP} **{sell_price:,} shrimp**")

        if len(lines) <= 0:
            return await ctx.send("Out of the items you supplied, you had none of any of them.")

        await ctx.db.add("users", "shrimp", ctx.author, total)
        _embed = discord.Embed(color=core.GREEN, timestamp=ctx.now)
        _embed.description = f"Total: {core.SHRIMP} **{total:,} shrimp**"
        _embed.set_author(name="Sold!", icon_url=ctx.avatar)

        await paginators.newline_paginate_via_field(ctx, _embed, lines, "Details")


    @core.command(
        name="resetcooldown",
        aliases=("rcd", "bypasscooldown"),
        usage="<cooldown>",
        description="Use your shrimp to reset a command's cooldown!",
        cooldown=(60*30, 60*20)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    async def _resetcooldown(self, ctx, *, command: converters.CommandConverter()):
        if command.name in ("daily", "weekly", "cooldowns"):
            return await ctx.send("You cannot reset the cooldown on that command.")

        _cooldown = await ctx.db.get_cooldown(command.qualified_name, ctx.author)
        _retry_after = _cooldown - ctx.unix

        if _retry_after <= 0:
            return await ctx.send("That command isn't even on cooldown!")
        if _retry_after > 60*30:
            return await ctx.send("Cooldowns higher than 30 minutes cannot be reset.")

        _price = round(_retry_after*100)
        _message = f"Do you want to pay {core.SHRIMP} **{_price:,}** to reset your cooldown of **{util.duration_strf(round(_retry_after))}**?"

        if await ctx.confirm(_message, delete_after=True, timeout=min(_retry_after, 30)):
            await ctx.cd()
            await ctx.db.add("users", "shrimp", ctx.author, -_price)
            await ctx.db.set("cooldowns", command.qualified_name, ctx.author, 0)
            await ctx.send(f"Cooldown reset. (You paid {core.SHRIMP} **{_price:,}**)")
        else:
            await ctx.send("Cancelled.")


def setup(client):
    cog = Transactions(client)
    client.add_cog(cog)
