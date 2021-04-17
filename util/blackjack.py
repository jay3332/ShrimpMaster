import random
import discord
import asyncio
import core

VALUES = {
    'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
    '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10
}
SUITS = list("dcsh")
SUIT_EMOJIS = list("♦♣♠♥")

HIT = "🇭"
STAND = "🇸"
END = "🇪"


class PlayerDeck:
    def __init__(self, flipped=False):
        self.cards = []
        self.flipped = flipped

    def flip(self):
        self.flipped = not self.flipped

    def add(self, card):
        self.cards.append(card)
        return card

    def add_multiple(self, *cards):
        self.cards.extend(cards)
        return cards

    @property
    def natural(self):
        if len(self.cards) < 2:
            return False

        if self.cards[0].worth(0) == 10 and self.cards[1].value == "A":
            return True

        return self.cards[1].worth(0) == 10 and self.cards[0].value == "A"

    @property
    def worth(self):
        _total = 0
        for card in sorted(self.cards, key=lambda c: c.value != "A"):
            _total += card.worth(_total)
        return _total

    @property
    def text(self):
        if not self.flipped:
            return " ".join(f"`{card}`" for card in self.cards)
        return " ".join(f"`{card}`" if self.cards.index(card)==0 else "`?`" for card in self.cards)


class Deck:
    def __init__(self):
        self.cards = [Card(suit, value) for value in VALUES for suit in SUITS]
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop(0)

    def draw_multiple(self, k):
        return [self.draw() for _ in range(k)]


class Card:
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def __str__(self):
        return f"{SUIT_EMOJIS[SUITS.index(self.suit)]} {self.value}"

    def worth(self, total):
        if self.value != "A" or total >= 11:
            return VALUES[self.value]
        if total > 21:
            return 1
        return 11


class Blackjack:

    def __init__(self, ctx, bet):
        self.ctx = ctx
        self.bet = bet
        self.player = ctx.author
        self.client = ctx.bot
        self.message = None
        self.deck = Deck()
        self.user_deck = PlayerDeck()
        self.bot_deck = PlayerDeck(True)
        self._timed_out = False

    def _setup(self):
        self.user_deck.add_multiple(*self.deck.draw_multiple(2))
        self.bot_deck.add_multiple(*self.deck.draw_multiple(2))

    @property
    def _base_embed(self):
        _embed = discord.Embed(timestamp=self.ctx.now)
        _embed.set_author(name=f"Blackjack: {self.player.name}", icon_url=self.ctx.avatar)

        _embed.add_field(name=self.player.name, value=self.user_deck.text + f"\nValue: {self.user_deck.worth}")
        if not self.bot_deck.flipped:
            _embed.add_field(name=self.client.user.name, value=self.bot_deck.text + f"\nValue: {self.bot_deck.worth}")
        else:
            _embed.add_field(name=self.client.user.name, value=self.bot_deck.text + f"\nValue: ?")
        return _embed

    @property
    def embed(self):
        _embed = self._base_embed
        _embed.colour = core.COLOR
        _embed.set_footer(text=f"Cards left: {len(self.deck.cards)}")
        _embed.description = (
            f"React with the following:\n"
            f"{HIT} hit\n"
            f"{STAND} stand\n"
            f"{END} end"
        )
        return _embed

    async def start(self):
        self._setup()
        _bj = await self._detect_blackjack()
        if not _bj:
            self.message = await self.ctx.send(self.embed)
            await self.message.add_reactions(HIT, STAND, END)
            await self._listen()


    async def _detect_blackjack(self):
        _w = self.winner("h")
        if _w[1] == "bj":
            await self._process_move(*_w)
            return True
        return False


    async def update(self):
        await self.ctx.maybe_edit(
            self.message, embed=self.embed,
            allowed_mentions=discord.AllowedMentions.none()
        )


    async def _listen(self):
        while True:
            try:
                reaction, user = await self.client.wait_for_multiple("reaction_add", "reaction_remove", timeout=30, check=lambda r, u: (
                    r.message.id == self.message.id and u.id == self.player.id and str(r.emoji) in (STAND, HIT, END)
                ))
            except asyncio.TimeoutError:
                self._timed_out = True
                await self._process_move(2, "to")
                break
            else:
                _emoji = str(reaction.emoji)

                if _emoji == HIT:
                    self.user_deck.add(self.deck.draw())
                elif _emoji == STAND:
                    if self.bot_deck.worth<=16:
                        while self.bot_deck.worth<=16:
                            self.bot_deck.add(self.deck.draw())

                _winner = self.winner(_emoji)
                if _winner[0] == -1:
                    await self.update()
                else:
                    await self._process_move(*_winner)
                    break


    async def _process_move(self, winner, action):
        _field_kwargs = {"name": ["Draw!", "You won!", "You lost!", None][winner]}

        _brief: str = ""
        if action == "e":
            _brief = "You ended the game."

        if action == "bj":
            _brief = "**Blackjack!**"

        if action == "bu":
            _brief = [
                "We both bust!",
                "Bot bust!",
                "You bust!",
                None
            ][winner]

        if action == "hi":
            _brief = [
                "We got equal value!",
                "Your cards were worth more than mine.",
                "My cards were worth more than yours.",
                None
            ][winner]

        if action == "to":
            _brief = "Session timed out."

        _desc = [
            None,
            "You won",
            "You lost",
            None
        ][winner]

        self.bot_deck.flip()
        await self._process_transaction(winner)
        if winner == 0:
            _desc = f"{_brief}\nWe tied. Maybe try again..?"
        else:
            _now = await self.client.db.get("users", self.player, "shrimp")
            _desc = f"{_brief}\n{_desc} {core.SHRIMP} **{self.bet:,} shrimp**.\n" \
                    f"You now have {core.SHRIMP} **{_now:,} shrimp**."
        _field_kwargs.update({
            "value": _desc,
            "inline": False
        })

        _embed = self._base_embed
        _embed.colour = [
            core.YELLOW,
            core.GREEN,
            core.RED,
            None
        ][winner]

        _embed.insert_field_at(0, **_field_kwargs)
        _embed.set_footer(text=f"Next card: {self.deck.cards[0]}")
        await self.ctx.maybe_edit(
            self.message, embed=_embed,
            allowed_mentions=discord.AllowedMentions.none()
        )


    async def _process_transaction(self, winner):
        _multiplier = [0, 1, -1, None][winner]
        await self.client.db.add("users", "shrimp", self.player, self.bet*_multiplier)


    def winner(self, move):
        # -1: no win | 0: tie | 1: user | 2: bot
        # bj: Blackjack/Natural | bu: Bust | hi: Higher | e: User-Ended

        if move==END:
            return 2, "e"

        if self._timed_out:
            return 2, "to"

        # naturals
        if self.user_deck.natural:
            return 1, "bj"
        elif self.bot_deck.natural:
            return 2, "bj"

        _user_bust = self.user_deck.worth>21
        _bot_bust = self.bot_deck.worth>21

        if _user_bust and _bot_bust:
            return 0, "bu"
        elif _user_bust:
            return 2, "bu"
        elif _bot_bust:
            return 1, "bu"

        if move==STAND:
            _user = self.user_deck.worth
            _bot = self.bot_deck.worth

            if _user>_bot:
                return 1, "hi"
            elif _bot>_user:
                return 2, "hi"
            elif _user==_bot:
                return 0, "hi"

        return -1, "nw"
