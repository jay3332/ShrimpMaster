SHRIMP = "<:shrimp:825862903487660032>"
GOLDEN_SHRIMP = "<:golden_shrimp:825862905030770718>"
LOADING = "<a:loading:825862907626913842>"
CHECK = "<:check:830871142985498675>"
CROSS = "<:cross:830871144650244156>"
VAULT = "<:vault:827552713294217256>"
FACTORY = "<:factory:831222233736937494>"
ARROW = "<:arrow:831333449562062908>"

DEPOSIT = "<:deposit:827562574123368509>"
WITHDRAW = "<:withdraw:827562573020266577>"

COLOR = 0xffaf87
ERROR_COLOR = 0x4287f5
EMBED_COLOR = 0x2f3136

GREEN = 0x5cff72
YELLOW = 0xffe95c
RED = 0xff6c5c

HELP_EMOJIS = {
    "Misc": "💢",
    "Stats": "📊",
    "Profit": "🍤",
    "Casino": "<:slots7:826467688142471189>",
    "Config": "⚙",
    "Transactions": VAULT,
    "Factories": FACTORY,
    "Image": "🖼",
    "Utility": "🔧"
}

SUPPORT_SERVER = "https://discord.gg/AHHuVhTYAj"
RECOMMENDED_PERMISSIONS = 104188993

MAX_SHORTCUTS = 20
BASE_DAILY_PROFIT = 500
BASE_WEEKLY_PROFIT = 2000
BASE_ROB_SUCCESS = 0.6

LEVEL_FORMULA = lambda level: round(50 * ((level + 1) ** 1.36) / 10) * 10

PROGRESS_BAR = {
    "start_empty": "<:leftempty:826935716712939581>",
    "start_filled": "<:leftfilled:826935716796694549>",
    "middle_empty": "<:middleempty:826935716659331183>",
    "middle_filled": "<:middlefilled:826935717140889621>",
    "end_empty": "<:rightempty:826935717061722132>",
    "end_filled": "<:rightfilled:826935716956471348>"
}

DICE = [None,
        "<:dice_1:826124033149763635>",
        "<:dice_2:826124034864447518>",
        "<:dice_3:826124036177788960>",
        "<:dice_4:826124039583825930>",
        "<:dice_5:826124041290121269>",
        "<:dice_6:826124043693457428>"]

SLOTS = ("s", "g", "7", "b", "d", "w", "r", "c", "f")

SLOTS_EMOJIS = {
    "s": SHRIMP,
    "g": GOLDEN_SHRIMP,
    "7": "<:slots7:826467688142471189>",
    "b": "<:slotsBell:826467684324868126>",
    "c": "<:slotsCherry:826467690586701884>",
    "d": "<:slotsDiamond:826467685218385931>",
    "r": "<:slotsGrape:826467689374810172>",
    "w": "<:slotsWatermelon:826467686531596290>",
    "f": "<a:fijiwater:831209369432490074>"
}

SLOTS_MULTIS = {
    "fff": 30,
    "ggg": 20,
    "sss": 15,
    "777": 15,
    "ddd": 10,
    "bbb": 10,
    "ccc": 7,
    "www": 7,
    "rrr": 7,
    "ff": 4,
    "gg": 3,
    "ss": 2.5,
    "77": 2.5,
    "dd": 2,
    "bb": 1.5,
    "cc": 1,
    "ww": 1,
    "rr": 1
}

ROULETTE_EMOJIS = {
    "red": "<:roulette_red:831928081794465812>",
    "green": "<:roulette_green:831928081588551732>",
    "black": "<:roulette_black:831928081865244672>"
}
