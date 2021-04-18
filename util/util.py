import asyncio
import functools
import re
import math
import time
import collections
import random as _random
from core import constants


class Timer:
    def __init__(self):
        self._start = None
        self._end = None

    def start(self):
        self._start = time.perf_counter()

    def stop(self):
        self._end = time.perf_counter()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __int__(self):
        return round(self.time)

    def __float__(self):
        return self.time

    def __str__(self):
        return str(self.time)

    def __repr__(self):
        return f"<Timer time={self.time}>"

    @property
    def time(self):
        if self._end is None:
            raise ValueError("Timer has not been ended.")
        return self._end - self._start


class Loading:
    def __init__(self, ctx, message='Loading...'):
        self.ctx = ctx
        self._ = None
        self.__ = message

    async def __aenter__(self):
        self._ = await self.ctx.send(f"{constants.LOADING} {self.__}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.ctx.maybe_delete(self._)


def get_invite_link(client, perms):
    return f"https://discord.com/oauth2/authorize?client_id={client.user.id}&scope=bot&permissions={perms}"


def surround(item):
    if not isinstance(item, (list, tuple)):
        item = (item,)
    return item


def duration_strf_abbv(seconds):
    if seconds <= 0: return '0s'
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    mo, d = divmod(d, 30)
    y, mo = divmod(mo, 12)

    if int(s) == s:
        s = int(s)

    if y > 100: return ">100y"

    y, mo, d, h, m = round(y), round(mo), round(d), round(h), round(m)
    return f'{f"{y}y " if y != 0 else ""}{f"{mo}mo " if mo != 0 else ""}{f"{d}d " if d != 0 else ""}{f"{h}h " if h != 0 else ""}' \
           f'{f"{m}m " if m != 0 else ""}{f"{s}s" if s != 0 else ""}'.strip()


def duration_strf(seconds, depth=3):
    force_round = False
    if seconds <= 0: return '0 seconds'
    if seconds >= 60:
        force_round = True
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    mo, d = divmod(d, 30)
    y, mo = divmod(mo, 12)

    if int(s) == s or force_round:
        s = int(s)

    if y > 100: return ">100 years"

    y, mo, d, h, m = round(y), round(mo), round(d), round(h), round(m)
    l = ((y, 'year'), (mo, 'month'), (d, 'day'), (h, 'hour'), (m, 'minute'), (s, 'second'))

    as_list = [f"{c[0]} {c[1]}{'s' if c[0] != 1 else ''}" for c in l if c[0] > 0]
    return human_readable(as_list[0:(depth if depth < len(as_list) else len(as_list))])


def prec_duration_strf(seconds):
    def rnd(i):
        return round(i, 2) if i >= 10 else round(i, 3)

    if seconds > 0.001:
        return f"{rnd(seconds * 1000)} ms"
    if seconds > 0.000001:
        return f"{rnd(seconds * 1000000)} μs"
    if seconds > 0.000000001:
        return f"{rnd(seconds * 1000000000)} ns"
    if seconds > 0.000000000001:
        return f"{rnd(seconds * 1000000000000)} ps"
    return "<1 ps"


def human_readable(iterable):
    if len(iterable) <= 2:
        return " and ".join(iterable)
    return ", ".join(iterable[:-1]) + f", and {iterable[-1]}"


async def get_shrimp_ranking(db, user):
    # might remove if the bot gets too popular (in which it won't)
    rank = await db.fetch('SELECT user_id, RANK () OVER (ORDER BY shrimp + vault DESC) rank FROM users')
    rank = list(filter(lambda r: r['user_id'] == user.id, rank))
    if len(rank) <= 0:
        return "Unranked"
    return "Rank #{:,}".format(rank[0]['rank'])


def random(minimum=None, maximum=None):
    # random.randint but with improvements
    _sys_random = _random.SystemRandom()
    if (not minimum) and (not maximum):
        return _sys_random.random()
    if not maximum:
        minimum, maximum = 0, minimum
    if minimum == maximum:
        return minimum
    if isinstance(minimum, int) and isinstance(maximum, int):
        return _sys_random.randint(minimum, maximum)
    return _sys_random.uniform(minimum, maximum)


choice = _random.choice


def get_daily_benefit(days):
    return int((math.sqrt(days) * 50) + (days // 10) * 50)


def get_daily_golden_chance(days):
    return (min(days/200, 0.67)+0.005)/1.7


def get_weekly_benefit(weeks):
    return int((math.sqrt(weeks) * 400) + (weeks // 10) * 500)


def get_weekly_golden_chance(weeks):
    return (min(weeks/46, 0.85)+0.005)/1.7


def get_number(s, integer=True):
    s = s.lower().replace(",", "").replace("+", "").strip()
    if s == "":
        raise ValueError()

    if s.endswith("k"):
        s = str(float(s.rstrip("k"))*1000)
    elif s.endswith("m"):
        s = str(float(s.rstrip("m"))*1000000)
    elif s.endswith("b"):
        s = str(float(s.rstrip("b"))*1000000000)
    elif s.endswith("t"):
        s = str(float(s.rstrip("t"))*1000000000000)

    if re.match(r"\de\d+", s):
        num, exp = s.split("e")
        num, exp = float(num),  round(float(exp))
        s = float(f"{num}e{exp}") if exp<24 else 1e24
    s = float(s)
    return s if not integer else round(s)


def strip_codeblocks(argument):
    if not argument.startswith('`'):
        return argument

    # keep a small buffer of the last chars we've seen
    last = collections.deque(maxlen=3)
    backticks = 0
    in_language = False
    in_code = False
    language = []
    code = []

    for char in argument:
        if char == '`' and not in_code and not in_language:
            backticks += 1
        if last and last[-1] == '`' and char != '`' or in_code and ''.join(last) != '`' * backticks:
            in_code = True
            code.append(char)
        if char == '\n':
            in_language = False
            in_code = True

        elif ''.join(last) == '`' * 3 and char != '`':
            in_language = True
            language.append(char)
        elif in_language:
            language.append(char)

        last.append(char)

    if not code and not language:
        code[:] = last

    return ''.join(code[len(language):-backticks])


def escape_markdown(s):
    return (
        s
        .replace("\\", "\\\\")
        .replace("*", "\\*")
        .replace("_", "\\_")
        .replace("`", "\\`")
        .replace("|", "\\|")
        .replace("~", "\\~")
        .replace("<", "\\<")
        .replace(":", "\\:")
        .replace("@", "\\@")
    )


def in_executor(loop=None):
    loop = loop or asyncio.get_event_loop()

    def inner_function(func):
        @functools.wraps(func)
        def function(*args, **kwargs):
            partial = functools.partial(func, *args, **kwargs)
            return loop.run_in_executor(None, partial)
        return function
    return inner_function


def progress_bar(
    start_empty: str,
    start_filled: str,
    middle_empty: str,
    middle_filled: str,
    end_empty: str,
    end_filled: str,
    ratio: float = 0.5,
    length: int = 10,
    method: any = round
):
    amount_filled = method(ratio*length)
    return "".join(
        start_filled
        if i == 0
        else end_filled
        if i == length - 1
        else middle_filled
        for i in range(amount_filled)
    ) + "".join(
        start_empty
        if i == 0
        else end_empty
        if i == length - 1
        else middle_empty
        for i in range(amount_filled, length)
    )


def get_amount(_all, minimum, maximum, arg):
    """
    Supports all/max, half, n/n fractions, and percentages.
    (and actual numbers ofc)
    """

    arg = arg.lower().strip()

    if arg in ("all", "max", "a", "m"):
        _amount = round(_all)

    elif arg in ("half", "h"):
        _amount = round(_all/2)

    elif arg.endswith("%"):
        _percent = arg.rstrip('%')
        try:
            _percent = float(_percent)/100
        except (TypeError, ValueError):
            raise NotAnInteger()
        else:
            _amount = round(_all*_percent)

    elif re.match(r"[0-9.]+/[0-9.]+", arg):
        try:
            _numerator, _denominator = [float(_) for _ in arg.split("/")]
        except (ValueError, TypeError):
            raise NotAnInteger()
        else:
            if _denominator == 0:
                raise ZeroDivisionError()
            _amount = round(_all*(_numerator/_denominator))

    else:
        try:
            _amount = get_number(arg)
        except (ValueError, ZeroDivisionError, TimeoutError, IndexError, KeyError):
            raise NotAnInteger()

    if _amount > _all:
        raise NotEnough()

    if _amount <= 0:
        raise NotAnInteger()

    if minimum <= _amount <= maximum:
        return _amount

    elif _amount > maximum:
        return maximum

    raise PastMinimum()


class NotAnInteger(Exception):
    pass


class NotEnough(Exception):
    pass


class PastMinimum(Exception):
    pass

