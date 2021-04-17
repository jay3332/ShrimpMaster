import core
import discord
import random as _random
from util.util import random


JOBS = {
    "high": {
        "scientist": {
            "keywords": (
                "reaction",
                "explosion",
                "test tube",
                "molecule",
                "laboratory",
                "science"
            )
        },
        "doctor": {
            "keywords": (
                "heartbeat",
                "medicine",
                "prescription",
                "surgery",
                "hospital",
                "doctor"
            )
        }
    },
    "medium": {
        "developer": {
            "keywords": (
                "python",
                "javascript",
                "typescript",
                "java",
                "program",
                "e"
            )
        },
        "chef": {

        },
        "youtuber": {

        }
    },
    "low": {
        "cashier": {

        },
        "janitor": {

        },
        "fast food worker": {

        }
    }
}


async def initiate_work_session(ctx):
    _job_choices = _random.sample(JOBS, k=3)

