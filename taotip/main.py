import asyncio
import discord

from src import api, event_handlers
from src.config import main_config as config, Config
from src.db import Database

_db: Database = None
_api: api.API = None


def main() -> None:
    print("Running Tao Tip...")
    client: discord.Client = discord.Client() 

    @client.event
    async def on_ready():
        global _db
        global _api
        _api, _db = await event_handlers.on_ready_(client, config)

        if _api is None or _db is None:
            print("Failed to initialize\nRetrying in 5s...")
            await asyncio.sleep(5) # wait 5 seconds
            await on_ready()
            return
        # add to client loop
        client.loop.create_task(welcome_new_users(_db, client, config))

    @client.event
    async def on_message(message: discord.Message):
        global _db
        global _api
        await event_handlers.on_message_(_db, client, message, config)

    async def welcome_new_users(_db: Database, client: discord.Client, config: Config):
        await event_handlers.welcome_new_users(_db, client, config)
        # sleep until next check
        await asyncio.sleep(config.NEW_USER_CHECK_INTERVAL)

    client.run(config.DISCORD_TOKEN)
    
if __name__ == "__main__":
    main()
