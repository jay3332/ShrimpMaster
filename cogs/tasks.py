import core
from discord import Object
from discord.ext import tasks
from util.util import random


class Tasks(core.Cog):

    def start_tasks(self):
        self._factory.start()
        #  self._stock.start()

    @tasks.loop(minutes=1)
    async def _factory(self):
        """ This will add golden shrimp every minute or so """
        if not self.client.db:
            return

        if factories := self.client.db.route("factories"):
            for factory in factories.values():
                if factory["is_active"] and factory["golden_shrimp"] < factory["golden_capacity"]:
                    if random() < factory["golden_chance_per_minute"]:
                        await self.client.db.add("factories", "golden_shrimp", Object(id=factory["user_id"]), 1)

    @tasks.loop(minutes=1)
    async def _stock(self):
        """ This will update the stocks graph """
        if not self.client.db:
            return

        last = await self.client.db.fetchrow("SELECT * FROM stocks ORDER BY id DESC")
        if not last:
            last = {
                "shrimp": 100,
                "created_at": self.client.unix,
                "id": 0
            }
        await self.client.db.execute(
            "INSERT INTO stocks (shrimp, created_at) VALUES ($1, $2);"
            "DELETE FROM stocks WHERE id < $3",
            last['shrimp'] + random(-52, 50), self.client.unix,
            last['id'] - 100  # Delete stocks past 100 ticks
        )


def setup(client):
    cog = Tasks(client)
    client.add_cog(cog)
    cog.start_tasks()
