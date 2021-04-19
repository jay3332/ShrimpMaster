import discord
from discord.ext import menus
from jishaku.paginators import WrappedPaginator, PaginatorInterface


class MenuPages(menus.Menu):
    """A special type of Menu dedicated to pagination.

    Attributes
    ------------
    current_page: :class:`int`
        The current page that we are in. Zero-indexed
        between [0, :attr:`PageSource.max_pages`).
    """
    def __init__(self, source, **kwargs):
        self._source = source
        self.current_page = 0
        super().__init__(**kwargs)

    @property
    def source(self):
        """:class:`PageSource`: The source where the data comes from."""
        return self._source

    async def change_source(self, source):
        """|coro|

        Changes the :class:`PageSource` to a different one at runtime.

        Once the change has been set, the menu is moved to the first
        page of the new source if it was started. This effectively
        changes the :attr:`current_page` to 0.

        Raises
        --------
        TypeError
            A :class:`PageSource` was not passed.
        """

        if not isinstance(source, menus.PageSource):
            raise TypeError('Expected {0!r} not {1.__class__!r}.'.format(menus.PageSource, source))

        self._source = source
        self.current_page = 0
        if self.message is not None:
            await source._prepare_once()
            await self.show_page(0)

    def should_add_reactions(self):
        return self._source.is_paginating()

    async def _get_kwargs_from_page(self, page):
        value = await discord.utils.maybe_coroutine(self._source.format_page, self, page)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return { 'content': value, 'embed': None }
        elif isinstance(value, discord.Embed):
            return { 'embed': value, 'content': None }

    async def show_page(self, page_number):
        page = await self._source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        await self.message.edit(**kwargs)

    async def send_initial_message(self, ctx, channel):
        """|coro|

        The default implementation of :meth:`Menu.send_initial_message`
        for the interactive pagination session.

        This implementation shows the first page of the source.
        """
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        return await channel.send(**kwargs)

    async def start(self, ctx, *, channel=None, wait=False):
        await self._source._prepare_once()
        await super().start(ctx, channel=channel, wait=wait)

    async def show_checked_page(self, page_number):
        max_pages = self._source.get_max_pages()
        try:
            if max_pages is None or max_pages > page_number >= 0:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(page_number)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def show_current_page(self):
        if self._source.is_paginating():
            await self.show_page(self.current_page)

    def _skip_double_triangle_buttons(self):
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages <= 2

    @menus.button('\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f', position=menus.First(0), skip_if=_skip_double_triangle_buttons)
    async def go_to_first_page(self, _):
        """go to the first page"""
        await self.show_page(0)

    @menus.button('\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f', position=menus.First(1))
    async def go_to_previous_page(self, _):
        """go to the previous page"""
        await self.show_checked_page(self.current_page - 1)

    @menus.button('\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f', position=menus.Last(0))
    async def go_to_next_page(self, _):
        """go to the next page"""
        await self.show_checked_page(self.current_page + 1)

    @menus.button('\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f', position=menus.Last(1), skip_if=_skip_double_triangle_buttons)
    async def go_to_last_page(self, _):
        """go to the last page"""
        # The call here is safe because it's guarded by skip_if
        await self.show_page(self._source.get_max_pages() - 1)

    @menus.button('\N{BLACK SQUARE FOR STOP}\ufe0f', position=menus.Last(3))
    async def stop_pages(self, _):
        """stops the pagination session."""
        self.stop()

    @menus.button('\N{INPUT SYMBOL FOR NUMBERS}', position=menus.Last(2), skip_if=_skip_double_triangle_buttons)
    async def user_input(self, _):
        """ui"""
        original = await self.ctx.send("Which page would you like to go to?")
        response = await self.ctx.bot.wait_for("message", timeout=30, check=lambda m: m.author==self.ctx.author and m.channel==self.ctx.channel)
        if not response.content.isdigit():
            return await self.ctx.maybe_edit(original, "Not a valid page.")
        response_formatted = min(self._source.get_max_pages(), int(response.content))
        if response_formatted<1:
            return await self.ctx.maybe_edit(original, "Page must be positive.")
        await self.show_page(response_formatted-1)
        await self.ctx.maybe_delete(original)
        await self.ctx.maybe_delete(response)


class EmbedPageSource(menus.ListPageSource):

    def __init__(self, data, per_page, footer=None):
        super().__init__(data, per_page=per_page)
        self.max_page = self.get_max_pages()
        self.footer = footer

    async def format_page(self, menu, item):
        embed = item[0][0]
        embed.clear_fields()

        for field in item:
            embed.add_field(**field[1])

        if self.footer is not None:
            page_text = f"{menu.current_page+1}/{self.max_page}"
            embed.set_footer(text=self.footer.format(page=page_text))
        return embed


class NewlineFieldEmbedPageSource(menus.ListPageSource):

    def __init__(self, data, per_page, field_name, footer=None):
        super().__init__(data, per_page=per_page)
        self.max_page = self.get_max_pages()
        self.field_name = field_name
        self.footer = footer

    async def format_page(self, menu, item):
        embed = item[0][0]
        embed.clear_fields()
        embed.add_field(name=self.field_name, value="\n".join(i[1] for i in item))

        if self.footer is not None:
            page_text = f"{menu.current_page + 1}/{self.max_page}"
            embed.set_footer(text=self.footer.format(page=page_text))
        return embed


class NewlineEmbedPageSource(menus.ListPageSource):

    def __init__(self, data, per_page, footer=None, prefix="", suffix=""):
        super().__init__(data, per_page=per_page)
        self.max_page = self.get_max_pages()
        self.p, self.s = prefix, suffix
        self.footer = footer

    async def format_page(self, menu, item):
        embed = item[0][0]
        embed.description = self.p+("\n".join(i[1] for i in item))+self.s

        if self.footer is not None:
            page_text = f"{menu.current_page + 1}/{self.max_page}"
            embed.set_footer(text=self.footer.format(page=page_text))
        return embed


async def field_paginate(ctx, base_embed, field_kwargs, *, per_page=5, footer=None):

    field_kwargs = [(base_embed, f) for f in field_kwargs]
    menu = MenuPages(EmbedPageSource(field_kwargs, per_page=per_page, footer=footer))
    await menu.start(ctx)


async def newline_paginate_via_field(ctx, base_embed, lines, field_name="Field", *, per_page=10, footer=None):

    lines = [(base_embed, f) for f in lines]
    menu = MenuPages(NewlineFieldEmbedPageSource(lines, per_page=per_page, field_name=field_name, footer=footer))
    await menu.start(ctx)


async def newline_paginate(ctx, base_embed, lines, *, per_page=10, footer=None, prefix="", suffix=""):

    lines = [(base_embed, f) for f in lines]
    menu = MenuPages(NewlineEmbedPageSource(lines, per_page=per_page, footer=footer, prefix=prefix, suffix=suffix))
    await menu.start(ctx)


async def auto_paginate(ctx, text, prefix='```', suffix='```', max_size=2000, wrap_at=(' ', '\n')):
    paginator = WrappedPaginator(prefix=prefix, suffix=suffix, max_size=max_size, wrap_on=wrap_at)
    paginator.add_line(text)
    interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
    await interface.send_to(ctx)
    return interface.message
