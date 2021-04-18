import core
import discord
from discord.ext.commands import max_concurrency, BucketType
from util import converters
from util.util import progress_bar, duration_strf, random
from typing import Optional


max_con = max_concurrency(1, BucketType.user)


def cumulative(base, factor, quantity):
    numerator = base * (factor ** quantity - 1)
    return numerator/(factor-1)


class Factories(core.Cog):

    @core.group(
        name="factory",
        aliases=("fac", "f", "shrimpfactory"),
        description="View information on your ShrimpFactory.",
        invoke_without_command=True,
        cooldown=(4, 2),
        usage="[user]"
    )
    async def _factory(self, ctx, *, user: Optional[converters.BetterMemberConverter] = None):
        pf = ctx.clean_prefix

        await ctx.cd()
        user = user or ctx.author
        data = await ctx.db.get_factory_info(user, ctx.unix)
        if not data['is_active']:
            return await ctx.send(
                f"Your factory isn't active yet! Start it using **{pf}factory start**"
                if user == ctx.author else "That user's factory isn't active yet."
            )
        embed = discord.Embed(color=core.COLOR, timestamp=ctx.now)
        embed.set_author(name=f"{user.name}'s ShrimpFactory™", icon_url=user.avatar_url)
        _percent = data["shrimp"] / data["capacity"]

        _until_full = (
            duration_strf(round(data['time_until_full']), 2) + " until full"
            if data['time_until_full'] > 0 else "Factory is full!"
        )
        embed.description = (
            f"{core.SHRIMP} {data['shrimp']:,} shrimp / {data['capacity']:,} ({_percent*100:.2f}%)\n"
            f"{_until_full}\n{progress_bar(**core.PROGRESS_BAR, ratio=_percent, length=8)}"
        )
        embed.add_field(name="Stats", value=(
            f"Shrimp / minute: {core.SHRIMP} **{data['shrimp_per_minute']:,}**\n"
            f"Shrimp capacity: {core.SHRIMP} **{data['capacity']:,}**\n"
            f"Last claimed: **{duration_strf(round(data['time_passed']), 1)} ago**"
        ), inline=False)
        embed.add_field(name="Golden Shrimp", value=(
            f"Earnings: {core.GOLDEN_SHRIMP} **{data['golden_shrimp']:,}**\n"
            f"Golden shrimp capacity: {core.GOLDEN_SHRIMP} **{data['golden_capacity']:,}**\n"
            f"Golden shrimp chance / minute: {core.GOLDEN_SHRIMP} **{data['golden_chance_per_minute']*100:.2f}%**"
        ), inline=False)
        if user == ctx.author:
            embed.add_field(name="Upgrading", value=(
                f"Price to upgrade **shrimp/minute**: {core.SHRIMP} **{data['spm_upgrade_price']:,}**\n"
                f"Price to upgrade **shrimp capacity**: {core.SHRIMP} **{data['capacity_upgrade_price']:,}**\n\n"
                f"Price to upgrade **golden shrimp chance/minute**: {core.SHRIMP} **{data['gcpm_upgrade_price']:,}**\n"
                f"Price to upgrade **golden shrimp capacity**: {core.SHRIMP} **{data['golden_capacity_upgrade_price']:,}**"
            ), inline=False)
            embed.add_field(name="Need help?", value=f"More info about factories and their commands can be seen using **{pf}factory help**.")

        await ctx.send(embed=embed, embed_perms=True)

    @_factory.command(
        name="start",
        aliases=("activate", "s"),
        description="Start-up your factory to start earning some shrimp... without even doing anything?",
        cooldown=(10, 2)
    )
    async def _factory_start(self, ctx):
        if await ctx.db.get("factories", ctx.author, "is_active"):
            return await ctx.send(f"Your factory is already active. To stop it, use **{ctx.clean_prefix}factory stop**")

        if await ctx.db.get("users", ctx.author, "shrimp") < 1000:
            return await ctx.send(f"You don't have enough shrimp to purchase a factory. (Requires {core.SHRIMP} **1,000 shrimp**)")

        if await ctx.confirm(f"Would you like to start your factory for **{core.SHRIMP} 1,000 shrimp**?", timeout=30):
            await ctx.cd()
            await ctx.db.add("users", "shrimp", ctx.author, -1000)
            await ctx.db.set("factories", "is_active", ctx.author, True)
            await ctx.db.set("factories", "last_claim", ctx.author, ctx.unix)
            await ctx.send(f"All set! You can view stats on your factory using **{ctx.clean_prefix}factory**.")

        else:
            await ctx.send("Cancelled.")

    @_factory.command(
        name="help",
        aliases=("h", "?"),
        description="View help on ShrimpMaster's currency system.",
        cooldown=5
    )
    @max_con
    async def _factory_help(self, ctx):
        """
        TODO: Make this into an embed
        """
        await ctx.send(
            "**s.factory** - View your factory\n"
            "**s.factory claim** - Claim what your factory has generated\n"
            "**s.factory upgrade <stat> [quantity=1]** - Upgrade your factory\n"
            "**s.factory start** - Start your factory\n"
            "**s.factory stop** - Stop your factory\n\n"
            "**Upgrade stats**\n"
            "**spm** - Shrimp / minute\n"
            "**cap** - Capacity\n"
            "**gcpm** - Golden (shrimp) chance / minute\n"
            "**gcap** - Golden (shrimp) capacity\n\n"
            "**Note:** Unclaimed shrimp will be lost, so make sure you claim them before you upgrade."
        )


    @_factory.command(
        name="claim",
        aliases=("cl", "c"),
        description="Claim the shrimp and golden shrimp from your factory.",
        cooldown=(60, 30)
    )
    @max_con
    async def _factory_claim(self, ctx):
        data = await ctx.db.get_factory_info(ctx.author, ctx.unix)
        if not data['is_active']:
            return await ctx.send(f"Your factory isn't active yet! Start it using **{ctx.clean_prefix}factory start**")
        if data['shrimp'] <= 0 and data['golden_shrimp'] <= 0:
            return await ctx.send("You have nothing to claim.")
        if data['time_passed'] < 60:
            return await ctx.send("You claimed shrimp within the last minute. Slow down, wouldn't you?")
        await ctx.cd()

        await ctx.db.set("factories", "golden_shrimp", ctx.author, 0)
        await ctx.db.set("factories", "last_claim", ctx.author, ctx.unix)
        if random() < 0.03:
            return await ctx.send("You claimed your shrimp, but the shrimp was rotten. You had to throw it out.")

        await ctx.db.add("users", "shrimp", ctx.author, data['shrimp'])
        await ctx.db.add("users", "golden_shrimp", ctx.author, data['golden_shrimp'])

        lines = []
        if data['shrimp'] > 0:
            lines.append(f"{core.SHRIMP} **+{data['shrimp']:,}**")
        if data['golden_shrimp'] > 0:
            lines.append(f"{core.GOLDEN_SHRIMP} **+{data['golden_shrimp']:,}**")

        await ctx.send(f"{core.FACTORY} ShrimpFactory™ Claim\n"+'\n'.join(lines))

    @_factory.group(
        name="upgrade",
        aliases=("upg", "up", "update", "levelup", "+"),
        description="Upgrade one of your factory stats.",
        usage="<stat> [quantity=1]",
        invoke_without_command=True
    )
    @max_con
    async def _factory_upgrade(self, ctx):
        # Directly invoke the help command
        await ctx.invoke(self._factory_help)

    @_factory_upgrade.command(
        name="spm",
        description="Shrimp per minute",
        usage="[quantity=1]"
    )
    @max_con
    async def _upg_spm(self, ctx, quantity: Optional[int] = 1):
        if quantity <= 0:
            return await ctx.send("Quantity must be positive.")
        if quantity > 100:
            return await ctx.send("Only 100 upgrades can be bought at a time.")

        data = await ctx.db.get_factory_info(ctx.author, ctx.unix)
        if not data['is_active']:
            return await ctx.send(f"Your factory isn't active yet! Start it using **{ctx.clean_prefix}factory start**")

        price_increase_factor = 1.255
        upgrade_column_buffer = "shrimp_per_minute"
        database_column_buffer = "spm_upgrade_price"
        upgrade_price = round(cumulative(data[database_column_buffer], price_increase_factor, quantity))

        if await ctx.db.get("users", ctx.author, "shrimp") < upgrade_price:
            return await ctx.send(f"You can't afford to upgrade this statistic.\n"
                                  f"Price: {core.SHRIMP} **{upgrade_price:,}**")

        await ctx.db.add("users", "shrimp", ctx.author, -upgrade_price)
        await ctx.db.set("factories", "last_claim", ctx.author, ctx.unix)

        new = data[upgrade_column_buffer] * (upgrade_factor := 1.232)
        for _ in range(quantity-1):
            new *= upgrade_factor
        await ctx.db.set("factories", upgrade_column_buffer, ctx.author, new := round(new))

        new_upgrade_price = round(upgrade_price * price_increase_factor)
        await ctx.db.set("factories", database_column_buffer, ctx.author, new_upgrade_price)

        times_text = (
            f"Upgraded **Shrimp/minute**"
            if quantity==1 else
            f"Upgraded **Shrimp/minute** {quantity} times"
        )
        await ctx.send(
            f"{times_text}\n"
            f"**{data[upgrade_column_buffer]:,}** {core.ARROW} **{new:,}**\n"
            f"Paid {core.SHRIMP} **{upgrade_price:,} shrimp**"
        )

    @_factory_upgrade.command(
        name="cap",
        aliases=("max", "capacity"),
        description="Shrimp capacity",
        usage="[quantity=1]"
    )
    @max_con
    async def _upg_cap(self, ctx, quantity: Optional[int] = 1):
        if quantity <= 0:
            return await ctx.send("Quantity must be positive.")
        if quantity > 100:
            return await ctx.send("Only 100 upgrades can be bought at a time.")

        data = await ctx.db.get_factory_info(ctx.author, ctx.unix)
        if not data['is_active']:
            return await ctx.send(f"Your factory isn't active yet! Start it using **{ctx.clean_prefix}factory start**")

        price_increase_factor = 1.255
        upgrade_column_buffer = "capacity"
        database_column_buffer = "capacity_upgrade_price"
        upgrade_price = round(cumulative(data[database_column_buffer], price_increase_factor, quantity))

        if await ctx.db.get("users", ctx.author, "shrimp") < upgrade_price:
            return await ctx.send(f"You can't afford to upgrade this statistic.\n"
                                  f"Price: {core.SHRIMP} **{upgrade_price:,}**")

        await ctx.db.add("users", "shrimp", ctx.author, -upgrade_price)
        await ctx.db.set("factories", "last_claim", ctx.author, ctx.unix)

        new = data[upgrade_column_buffer] * (upgrade_factor := 1.232)
        for _ in range(quantity-1):
            new *= upgrade_factor
        await ctx.db.set("factories", upgrade_column_buffer, ctx.author, new := round(new))

        new_upgrade_price = round(upgrade_price * price_increase_factor)
        await ctx.db.set("factories", database_column_buffer, ctx.author, new_upgrade_price)

        times_text = (
            f"Upgraded **Shrimp capacity**"
            if quantity==1 else
            f"Upgraded **Shrimp capacity** {quantity} times"
        )
        await ctx.send(
            f"{times_text}\n"
            f"**{data[upgrade_column_buffer]:,}** {core.ARROW} **{new:,}**\n"
            f"Paid {core.SHRIMP} **{upgrade_price:,} shrimp**"
        )


def setup(client):
    client.add_cog(Factories(client))
