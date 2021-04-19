import core
import typing
import discord
from discord.ext import commands
from util import image
from util.converters import get_image
from util.util import Loading


class Image(core.Cog):

    @core.command(
        name="magik",
        aliases=("magick", "magic", "mgk"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[intensity] [url | image]",
        description="Apply a magik effect to an image. Intensity defaults to 2.",
        examples=(
            "magik",
            "magik @User",
            "magik 10",
            "magik @User 10"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _magik(self, ctx, intensity: typing.Optional[typing.Union[int, float]] = 2, *, query=None):
        if intensity > 100:
            return await ctx.send("Intensity should be under 100.")
        if intensity <= 0:
            return await ctx.send("Intensity should be positive.")

        await ctx.cd()

        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer, _mode = await ctx.bot.loop.run_in_executor(None, image.magik, _image, intensity)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_magik.{_mode}")
        )

    @core.command(
        name="petpet",
        aliases=("patpat", "pats"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[intensity] [url | image]",
        description="Apply a petpet effect to an image. Intensity (\"squish factor\") defaults to 0.",
        examples=(
            "petpet",
            "petpet @User",
            "petpet 1.3",
            "petpet @User 1.3"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _petpet(self, ctx, intensity: typing.Optional[typing.Union[int, float]] = 0, *, query=None):
        if intensity > 10:
            return await ctx.send("Intensity should be under 10.")
        if intensity < 0:
            return await ctx.send("Intensity should not be negative.")

        await ctx.cd()

        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.petpet, _image, intensity/5)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_petpet.gif")
        )

    @core.command(
        name="spin",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Apply a spinning effect to an image.",
        examples=(
            "spin",
            "spin @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _spin(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.spin, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_spin.gif")
        )

    @core.command(
        name="shake",
        alias="earthquake",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[intensity] [url | image]",
        description="Apply a shaking effect to an image. Intensity defaults to 10.",
        examples=(
            "shake",
            "shake @User",
            "shake 16",
            "shake @User 16"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _shake(self, ctx, intensity: typing.Optional[int] = 10, *, query=None):
        if intensity > 100:
            return await ctx.send("Intensity should be under 100.")
        if intensity <= 0:
            return await ctx.send("Intensity should be positive.")

        await ctx.cd()

        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.shake, _image, intensity)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_shake.gif")
        )

    @core.command(
        name="circular",
        aliases=("circle", "circlecrop"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Crops an image into a circle.",
        examples=(
                "circular",
                "circular @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _circular(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer, _format = await ctx.bot.loop.run_in_executor(None, image.circular, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_circular.{_format}")
        )


    @core.command(
        name="pixelate",
        aliases=("pixel", "pix"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Pixelates an image.",
        examples=(
                "pixelate",
                "pixelate @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _pixelate(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer, _format = await ctx.bot.loop.run_in_executor(None, image.pixelate, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_pixelate.{_format}")
        )

    @core.command(
        name="invert",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Inverts an image.",
        examples=(
                "invert",
                "invert @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _invert(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer, _format = await ctx.bot.loop.run_in_executor(None, image.invert, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_invert.{_format}")
        )

    @core.command(
        name="breathe",
        aliases=("breath", "floating"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Adds a breathing effect to an image.",
        examples=(
                "breathe",
                "breathe @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _breathe(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.breathe, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_breathe.gif")
        )

    @core.command(
        name="bounce",
        aliases=("bouncy", "bouncing"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Adds a bouncing effect to an image.",
        examples=(
                "bounce",
                "bounce @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _bounce(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.bounce, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_bounce.gif")
        )


    @core.command(
        name="revolve",
        aliases=("revolving", "gyrate"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Adds a revolving effect to an image.",
        examples=(
                "revolve",
                "revolve @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _revolve(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.revolve, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_revolve.gif")
        )

    @core.command(
        name="bonk",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="bonk",
        examples=(
                "bonk",
                "bonk @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _bonk(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.bonk, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_bonk.gif")
        )

    @core.command(
        name="fade",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Fade away an image.",
        examples=(
                "fade",
                "fade @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _fade(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.fade, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_fade.gif")
        )

    @core.command(
        name="huerotate",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Rotate over hues of an image.",
        examples=(
                "huerotate",
                "huerotate @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _huerotate(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.huerotate, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_huerotate.gif")
        )

    @core.command(
        name="stretch",
        alias="wide",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Apply a stretching effect to an image.",
        examples=(
                "stretch",
                "stretch @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _stretch(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.stretch, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_stretch.gif")
        )

    @core.command(
        name="disco",
        alias="flashy",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Apply a disco effect to an image.",
        examples=(
                "disco",
                "disco @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _disco(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.disco, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_disco.gif")
        )
        
    @core.command(
        name="sepia",
        alias="brown",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Apply a sepia effect to an image.",
        examples=(
                "sepia",
                "sepia @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _sepia(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer, _ = await ctx.bot.loop.run_in_executor(None, image.sepia, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, "ShrimpMaster_sepia.png")
        )

    @core.command(
        name="grayscale",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Apply a grayscale effect to an image.",
        examples=(
                "grayscale",
                "grayscale @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _grayscale(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer, _ = await ctx.bot.loop.run_in_executor(None, image.grayscale, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_grayscale.png")
        )

    @core.command(
        name="swirl",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[degrees=240] [url | image]",
        description="Apply a swirl effect to an image.",
        examples=(
            "swirl",
            "swirl @User",
            "swirl 90 @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _swirl(self, ctx, intensity: typing.Optional[int] = 240, *, query=None):
        if intensity > 100000:
            return await ctx.send("Intensity/swirl degree should be under 100000.")
        if intensity <= 0:
            return await ctx.send("Intensity should be positive.")

        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer, _ = await ctx.bot.loop.run_in_executor(None, image.swirl, _image, intensity)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_swirl.png")
        )

    @core.command(
        name="solarize",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Solarize an image.",
        examples=(
                "solarize",
                "solarize @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _solarize(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer, _ = await ctx.bot.loop.run_in_executor(None, image.solarize, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_solarize.png")
        )

    @core.command(
        name="type",
        bot_perms=("Send Messages", "Attach Files"),
        usage="<text>",
        description="Type out text..?",
        examples=(
                "type hello",
                "type one two three four"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _type(self, ctx, *, message: commands.clean_content(fix_channel_mentions=True)):
        await ctx.cd()
        async with Loading(ctx):
            _buffer = await ctx.bot.loop.run_in_executor(None, image.type_, message)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_type.gif")
        )

    @core.command(
        name="shiny",
        alias="shine",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Makes an image shiny.",
        examples=(
                "shine",
                "shine @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _shine(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.shine, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_shine.gif")
        )

    @core.command(
        name="explosion",
        aliases=("boom", "explode"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Explode an image or gif.",
        examples=(
                "explode",
                "explode @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _explode(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.explosion, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_explosion.gif")
        )

    @core.command(
        name="posterize",
        bot_perms=("Send Messages", "Attach Files"),
        usage="[intensity=2] [url | image]",
        description="Posterize an image.",
        examples=(
                "posterize",
                "posterize @User",
                "posterize 3"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _posterize(self, ctx, intensity: typing.Optional[int] = 2, *, query=None):
        if intensity > 10:
            return await ctx.send("Intensity must be under 10.")
        if intensity <= 0:
            return await ctx.send("Intensity must be positive.")
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query)
            _buffer, _ = await ctx.bot.loop.run_in_executor(None, image.posterize, _image, intensity)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_posterize.png")
        )

    @core.command(
        name="speed",
        aliases=("speedup", "fast"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[speed=2.0] [url | image]",
        description="Speeds up an image.",
        examples=(
                "speed",
                "speed @User",
                "speed 3"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _speed(self, ctx, factor: typing.Optional[typing.Union[int, float]] = 2, *, query=None):
        if factor > 24:
            return await ctx.send("Speed factor must be under 24.")
        if factor < 1/24:
            return await ctx.send("Speed factor must be over 1/24.")
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.speed, _image, factor)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_speed.gif")
        )

    @core.command(
        name="seek",
        aliases=("getframe", "static"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[frame-index=1] [url | image]",
        description="Extract a frame from a GIF.",
        examples=(
                "seek",
                "seek @User",
                "seek 2"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _seek(self, ctx, index: typing.Optional[int] = 1, *, query=None):
        if index <= 0:
            return await ctx.send("Index must be positive.")
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.seek, _image, index-1)
            if not _buffer:
                return await ctx.send("Could not seek to that index.")
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_frame{index}.png")
        )

    @core.command(
        name="reverse",
        aliases=("rewind", "rev"),
        bot_perms=("Send Messages", "Attach Files"),
        usage="[url | image]",
        description="Reverses a GIF.",
        examples=(
            "reverse",
            "reverse @User"
        ),
        cooldown=(15, 8)
    )
    @commands.max_concurrency(1, commands.BucketType.user)
    @core.check(bot_perms=("send_messages", "attach_files"))
    async def _seek(self, ctx, *, query=None):
        await ctx.cd()
        async with Loading(ctx):
            _image = await get_image(ctx, query, png=False)
            _buffer = await ctx.bot.loop.run_in_executor(None, image.reverse_, _image)
        await ctx.send(
            content=f"{core.CHECK} Image result for **{ctx.author.name}**",
            file=discord.File(_buffer, f"ShrimpMaster_reversed.gif")
        )



def setup(client):
    cog = Image(client)
    client.add_cog(cog)
