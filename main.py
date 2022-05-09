import discord

from src import api, event_handlers
from src.config import main_config as config
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
        await event_handlers.on_ready_(_db, _api, client, config)
        # add to client loop
        client.loop.create_task(lambda _db: event_handlers.lock_all_addresses_and_wait(_db, config))
        client.loop.create_task(lambda client, _db, _api: event_handlers.check_deposit_and_wait(_db, _api, client, config))

    @client.event
    async def on_message(message: discord.Message):
        global _db
        global _api
        await event_handlers.on_message_(_db, _api, client, message, config)

    client.run(config.DISCORD_TOKEN)
    
if __name__ == "__main__":
    main()
