import asyncio
import datetime
import discord
import asyncpg
from humanize import naturaltime
from json import loads, dumps


class Timer:
    __slots__ = ('args', 'kwargs', 'event', 'id', 'created_at', 'expires', 'manager', 'finished')

    def __init__(self, record, manager):
        self.id = record['id']
        self.manager = manager
        self.finished = False

        self.event = record['event']
        self.created_at = record['created']
        self.expires = record['expires']

        extra = loads(record['extra'])
        self.args = extra.get('args', [])
        self.kwargs = extra.get('kwargs', {})

    async def end(self):
        """ Ends a timer early """
        await self.manager.call_timer(self)

    @classmethod
    def partial(cls, manager, *, expires, created, event, args, kwargs):
        pseudo = {
            'id': None,
            'extra': dumps({'args': args, 'kwargs': kwargs}),
            'event': event,
            'created': created,
            'expires': expires
        }
        return cls(pseudo, manager)

    def __eq__(self, other):
        try:
            return self.id == other.id
        except AttributeError:
            return False

    def __hash__(self):
        return hash(self.id)

    @property
    def human_delta(self):
        return naturaltime(self.created_at, when=datetime.datetime.utcnow())

    def __repr__(self):
        return f'<Timer created={self.created_at} expires={self.expires} event={self.event}>'


class BotTimerManager:
    def __init__(self, client):
        self.db = client.db.pool
        self.client = client
        self._buffer = None
        self._cached = asyncio.Event(loop=client.loop)
        self.timer_task = client.loop.create_task(self.dispatch_timers())

    async def get_timer(self, days=7):
        record = await self.db.fetchrow(
            "SELECT * FROM timers WHERE expires < (CURRENT_DATE + $1::interval) ORDER BY expires LIMIT 1;",
            datetime.timedelta(days=days)
        )
        return Timer(record, self) if record else None

    async def wait_for_timers(self, days=7):
        timer = await self.get_timer(days=days)
        if timer is not None:
            self._cached.set()
            return timer

        self._cached.clear()
        self._buffer = None
        await self._cached.wait()
        return await self.get_timer(days=days)

    async def initialize_finished_timer(self, timer):
        if not timer.finished:
            self.client.dispatch(f"{timer.event}_timer_complete", timer)
            timer.finished = True

    async def call_timer(self, timer):
        await self.db.execute("DELETE FROM timers WHERE id=$1", timer.id)
        await self.initialize_finished_timer(timer)

    async def dispatch_timers(self):
        try:
            while not self.client.is_closed():
                timer = self._buffer = await self.wait_for_timers(days=40)
                now = datetime.datetime.utcnow()

                if timer.expires >= now:
                    to_sleep = (timer.expires - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                await self.call_timer(timer)
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self.timer_task.cancel()
            self.timer_task = self.client.loop.create_task(self.dispatch_timers())

    async def dispatch_short_timer(self, seconds, timer):
        await asyncio.sleep(seconds)
        await self.initialize_finished_timer(timer)

    async def create_timer(self, when, event, *args, **kwargs):
        try:
            now = kwargs.pop('created')
        except KeyError:
            now = datetime.datetime.utcnow()

        timer = Timer.partial(self, event=event, args=args, kwargs=kwargs, expires=when, created=now)
        delta = (when - now).total_seconds()
        if delta <= 30:
            self.client.loop.create_task(self.dispatch_short_timer(delta, timer))
            return timer

        row = await self.db.fetchrow(
            "INSERT INTO timers (event, extra, expires, created) VALUES ($1, $2, $3, $4) RETURNING id;",
            event, dumps({'args': args, 'kwargs': kwargs}), when, now
        )
        timer.id = row[0]

        if delta <= (86400 * 40):
            self._cached.set()

        if self._buffer and when < self._buffer.expires:
            self.timer_task.cancel()
            self.timer_task = self.client.loop.create_task(self.dispatch_timers())

        return timer
