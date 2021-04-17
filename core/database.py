import datetime
import math

import asyncpg
import typing
import random
from core import constants
from util import items


async def setup(db):

    await db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id bigint unique,
        level integer not null default 0,
        xp bigint not null default 0,
        shrimp bigint not null default 0,
        golden_shrimp bigint not null default 0,
        daily_streak integer not null default 0,
        weekly_streak integer not null default 0,
        last_daily bigint not null default 0,
        last_weekly bigint not null default 0,
        net text not null default 'hand',
        multiplier double precision not null default 1,
        xp_multiplier double precision not null default 1,
        vault bigint not null default 0,
        vault_space bigint not null default 100,
        expanded_vault_space bigint not null default 0,
        nets bigint not null default 1,
        locked boolean not null default false,
        mod boolean not null default false
    );
    CREATE TABLE IF NOT EXISTS premium (
        user_id bigint unique,
        expires bigint not null default 0,
        last_renewal bigint not null default 0
    );
    CREATE TABLE IF NOT EXISTS blacklists (
        user_id bigint unique,
        moderator_id bigint,
        reason text not null default 'No reason provided.',
        expires bigint not null default 0
    );
    CREATE TABLE IF NOT EXISTS cooldowns (
        user_id bigint unique
    );
    CREATE TABLE IF NOT EXISTS items (
        user_id bigint unique
    );
    CREATE TABLE IF NOT EXISTS guilds (
        guild_id bigint unique,
        prefixes text[] not null default array ['s.']
    );
    CREATE TABLE IF NOT EXISTS timers (
        id SERIAL,
        created timestamp,
        expires timestamp,
        extra text not null default '{}',
        event text
    );
    CREATE TABLE IF NOT EXISTS shortcuts (
        user_id bigint,
        name text,
        aliases text[] not null default array[]::text[],
        command text
    );
    CREATE TABLE IF NOT EXISTS factories (
        user_id bigint,
        is_active boolean not null default false,
        shrimp_per_minute bigint not null default 50,
        capacity bigint not null default 1000,
        golden_shrimp bigint not null default 0,
        golden_chance_per_minute double precision not null default 0.000125,
        golden_capacity bigint not null default 10,
        last_claim bigint not null default 0,
        spm_upgrade_price bigint not null default 1000,
        capacity_upgrade_price bigint not null default 1500,
        gcpm_upgrade_price bigint not null default 3000,
        golden_capacity_upgrade_price bigint not null default 5000
    );
    CREATE TABLE IF NOT EXISTS notifications (
        user_id bigint,
        brief text not null default 'Unknown',
        description text not null default 'No description provided.',
        dealt_at bigint
    ); /*
    CREATE TABLE IF NOT EXISTS stocks (
        created_at bigint,
        shrimp bigint not null default 100,
        id SERIAL
    );
    CREATE TABLE IF NOT EXISTS shares (
        user_id bigint,
        id bigint,
        share_value bigint,
        shares bigint not null default 0  
    ); */
    """)

    await db.execute("alter table users add column if not exists shrimp bigint not null default 0;"
                     "alter table users add column if not exists golden_shrimp bigint not null default 0;"
                     "alter table users add column if not exists net text not null default 'hand';"
                     "alter table users add column if not exists daily_streak integer not null default 0;"
                     "alter table users add column if not exists weekly_streak integer not null default 0;"
                     "alter table users add column if not exists last_daily bigint not null default 0;"
                     "alter table users add column if not exists last_weekly bigint not null default 0;"
                     "alter table users add column if not exists multiplier double precision not null default 1;"
                     "alter table users add column if not exists xp_multiplier double precision not null default 1;"
                     "alter table users add column if not exists vault bigint not null default 0;"
                     "alter table users add column if not exists vault_space bigint not null default 100;"
                     "alter table users add column if not exists expanded_vault_space bigint not null default 0;"
                     "alter table users add column if not exists nets bigint not null default 1;"
                     "alter table users add column if not exists locked boolean not null default false;"
                     "alter table users add column if not exists mod boolean not null default false;")

    await items.add_items_into_database(db)


class DatabaseManager:
    def __init__(self, db, bot):
        self._shortcuts_loaded = False
        self.shortcut_cache = {}
        self.cache = {}
        self.calls = []
        self.pool = db
        self.bot = bot

    def update_cache(self, table, _id, column, new):
        self.cache.update({table: self.route(table) or {}})
        self.cache[table].update({_id: self.route(table, _id) or {}})
        self.cache[table][_id][column] = new

    def overwrite_cache_entry(self, table, _id, new):
        self.cache.update({table: self.route(table) or {}})
        self.cache[table].update({_id: new})

    def route(self, *directions):
        """ Take a tuple like ('guilds', 1234, 'prefixes') and
            convert that into something like cache.get('guilds', {}).get(1234, {}).get('prefixes')

            Very similar to self.get, but it does not fetch from db if not found
        """
        final = self.cache
        for direction in directions:
            final = final.get(direction, {})

        return final or None

    async def execute(self, query, *args, **kwargs):
        self.calls.append({
            "method": "EXECUTE",
            "query": query
        })
        return await self.pool.execute(query, *args, **kwargs)

    async def fetch(self, query, *args, **kwargs):
        self.calls.append({
            "method": "FETCH",
            "query": query
        })
        return await self.pool.fetch(query, *args, **kwargs)

    async def fetchrow(self, query, *args, **kwargs):
        self.calls.append({
            "method": "FETCHROW",
            "query": query
        })
        return await self.pool.fetchrow(query, *args, **kwargs)

    async def fetch_data(self, table, user, column=None):
        _pointer = "guild" if user.__class__.__name__ == "Guild" else "user"

        get_query = 'SELECT * FROM "{0}" WHERE "{1}_id"=$1'.format(table, _pointer)
        query = 'INSERT INTO "{0}" ("{1}_id") VALUES ($1) ON CONFLICT DO NOTHING'.format(table, _pointer)
        got = await self.fetchrow(get_query, user.id)

        if not got:
            await self.execute(query, user.id)
            got = await self.fetchrow(get_query, user.id)
        if not column:
            # Update the cache because it clearly doesn't have it
            self.overwrite_cache_entry(table, user.id, dict(got))
            return got
        res = got[column]
        self.update_cache(table, user.id, column, res)
        return res

    async def get(self, table, user, column=None):
        if route := self.route(table, user.id, column):
            return route  # If it's already stored in the cache, get that instead

        return await self.fetch_data(table, user, column)


    async def sum(self, table, user, *columns):
        _total = 0
        for col in columns:
            _amount = await self.get(table, user, col)
            _total += _amount
        return _total


    async def add(self, table, column, user, amount: typing.Union[int, float]):
        await self.get(table, user)
        _pointer = "user" if user.__class__.__name__ in ('User', 'Member', 'Object') else "guild"
        query = 'UPDATE "{0}" SET "{1}"="{1}"+$1 WHERE "{2}_id"=$2'.format(table, column, _pointer)
        try:
            self.cache[table][user.id][column] += amount
        except KeyError:
            await self.fetch_data(table, user, column)  # Updates the cache
        return await self.execute(query, amount, user.id)

    async def set(self, table, column, user, value):
        await self.get(table, user)
        _pointer = "user" if user.__class__.__name__ in ('User', 'Member', 'Object') else "guild"
        query = 'UPDATE "{0}" SET "{1}"=$1 WHERE "{2}_id"=$2'.format(table, column, _pointer)
        self.cache[table][user.id][column] = value
        return await self.execute(query, value, user.id)

    # --- HELPER METHODS ---
    """ These wrap around normal methods for ease of use. """

    async def notify(self, user, brief, description):
        epoch = datetime.datetime.utcfromtimestamp(0)
        unix = (datetime.datetime.utcnow() - epoch).total_seconds()
        await self.execute("INSERT INTO notifications (user_id, brief, description, dealt_at) VALUES ($1, $2, $3, $4)",
                           user.id, brief, description, unix)

    async def load_shortcuts(self):
        self._shortcuts_loaded = True
        shortcuts = await self.fetch("SELECT * FROM shortcuts")
        for entry in shortcuts:
            self.shortcut_cache.update({entry['user_id']: self.shortcut_cache.get(entry['user_id'], [])})
            self.shortcut_cache[entry['user_id']].append(dict(entry))
        return self.shortcut_cache

    async def get_shortcut(self, user, shortcut):
        if not self._shortcuts_loaded:
            await self.load_shortcuts()

        shortcut = shortcut.lower()
        for sc in self.shortcut_cache.get(user.id, []):
            if (
                sc["name"] == shortcut or
                shortcut in sc["aliases"] or
                shortcut.startswith(sc["name"]+' ') or
                any(
                    shortcut.startswith(alias+' ')
                    for alias in sc["aliases"]
                )
            ):
                return sc["command"]
        return None

    async def add_shortcut(self, user, shortcut, command):
        self.shortcut_cache.update({user.id: self.shortcut_cache.get(user.id, [])})
        self.shortcut_cache[user.id].append({
            "name": shortcut,
            "command": command,
            "aliases": []
        })

        await self.execute("INSERT INTO shortcuts (user_id, name, command) VALUES ($1, $2, $3);", user.id, shortcut, command)

    async def get_level(self, user):
        _ = await self.get("users", user)
        return _["level"], _["xp"]

    async def add_xp(self, user, xp):
        xp = math.ceil(xp * await self.get('users', user, "xp_multiplier"))
        await self.add("users", "xp", user, xp)
        await self.add("users", "vault_space", user, xp)
        _level, _xp = await self.get_level(user)
        _requirement = constants.LEVEL_FORMULA(_level)

        if _xp > _requirement:
            while _xp > _requirement:
                await self.add("users", "xp", user, -_requirement)
                await self.add("users", "level", user, 1)
                _level, _xp = await self.get_level(user)
                _requirement = constants.LEVEL_FORMULA(_level)
                await self.process_level_up(user, _level)

        return _level, _xp


    async def process_level_up(self, user, new):
        await self.notify(user, "You leveled up!", f"You leveled up to **Level {new:,}**. Congrats!")

        _experienced_id = 830270492346679297
        _shrimpmaster_id = 825861299674152960

        guild = self.bot.get_guild(_shrimpmaster_id)
        role = guild.get_role(_experienced_id)

        member = guild.get_member(user.id)
        if not member:
            return

        if new >= 50:
            if role not in member.roles:
                await member.add_roles(role)
        else:
            if role in member.roles:
                await member.remove_roles(role)


    async def set_cooldown(self, name, user, value):
        name = name.replace(" ", "_").replace("-", "_")

        await self.execute("create table if not exists cooldowns (user_id bigint not null default 0);")
        await self.execute(f"alter table cooldowns add column if not exists \"{name}\" bigint not null default 0;")

        await self.get("cooldowns", user)
        await self.set("cooldowns", name, user, round((value-1500000000)*1000))

    async def get_cooldown(self, name, user):
        name = name.replace(" ", "_").replace("-", "_")
        await self.execute("create table if not exists cooldowns (user_id bigint not null default 0);")

        try:
            res = await self.fetchrow(f"select user_id, cooldowns.{name} from cooldowns where user_id=$1", user.id)
        except (asyncpg.UndefinedTableError, asyncpg.UndefinedColumnError):
            return 0
        else:
            if not res:
                return 0
            return res.get(name, 0)/1000 + 1500000000

    async def get_blacklist_info(self, ctx):
        if blacklist := await self.fetchrow(f"select * from blacklists where user_id=$1", ctx.author.id):
            _is_blacklisted = blacklist["expires"] > ctx.unix or blacklist["expires"] == 1
            return {
                "blacklisted": _is_blacklisted,
                "offender": ctx.author,
                "moderator": await ctx.bot.getch_user(blacklist["moderator_id"]),
                "reason": blacklist["reason"]
            }
        return None

    async def is_blacklisted(self, user, unix):
        if blacklist := await self.fetchrow(f"select expires from blacklists where user_id=$1", user.id):
            return blacklist["expires"] > unix or blacklist["expires"] == 1
        return False

    async def die(self, user, reason="Unknown causes"):
        """
        Makes a user dead.
        Unless they have a lifesaver, they will lose all of their shrimp and a random item in their inventory.
        TODO: Notifications

        :param user: The user to "kill"
        :param reason: The reason of death
        :return: void
        """
        # If they have a lifesaver, let's just return
        if await self.get("items", user, "lifesaver") > 0:
            await self.notify(user, "You almost died!", "You almost died, but you had a lifesaver in your inventory. Reason: %s" % reason)
            await self.add("items", "lifesaver", user, -1)
            return reason

        # Remove shrimp
        old = await self.get("users", user, "shrimp")
        await self.set("users", "shrimp", user, 0)

        # Select items, if at least one exists, choose a random one and remove them
        _chosen = None
        _items = await self.fetchrow("SELECT * FROM items WHERE user_id=$1", user.id)
        old_item = 0
        if items:
            filtered = {k: v for k, v in _items.items() if v > 0 and k != 'user_id'}
            if filtered:
                _chosen = random.choice(list(filtered.keys()))
                old_item = filtered[_chosen]
                await self.set("items", _chosen, user, 0)

        await self.notify(user, "You died!", f"{reason} You lost {constants.SHRIMP} **{old:,} shrimp**."
                          if not _chosen else f"{reason} You lost {constants.SHRIMP} **{old:,} shrimp** and "
                                              f"**{items.get_item(_chosen).quantitize(old_item)}**.")
        return reason


    async def get_factory_info(self, user, unix):
        data = await self.get("factories", user)
        if not data['is_active']:
            return {
                "shrimp": 0,
                "time_passed": 0,
                "minutes_passed": 0,
                "time_until_full": 0,
                "capacity_left": 0,
                **data
            }

        time_passed = unix - data['last_claim']
        minutes_passed = time_passed/60

        _raw_shrimp_profit = int(data['shrimp_per_minute']*minutes_passed)
        shrimp_profit = min(_raw_shrimp_profit, data['capacity'])

        capacity_left = data['capacity'] - shrimp_profit
        minutes_until_full = capacity_left / data['shrimp_per_minute']
        seconds_until_full = minutes_until_full*60

        return {
            "shrimp": shrimp_profit,
            "time_passed": time_passed,
            "minutes_passed": minutes_passed,
            "time_until_full": seconds_until_full,
            "capacity_left": capacity_left,
            **data
        }
