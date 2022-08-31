import asyncio
import interactions

from src import api, event_handlers
from src.config import main_config as config, Config
from src.db import Database

def main() -> None:
    print("Running Tao Tip...")


    bot = interactions.Client(token=config.DISCORD_TOKEN)

    @bot.event
    async def on_ready():
        _db: Database = None
        _api: api.API = None
        _api, _db = await event_handlers.on_ready_(bot, config)

        if _api is None or _db is None:
            print("Failed to initialize\nRetrying in 5s...")
            await asyncio.sleep(5) # wait 5 seconds
            await on_ready()
            return

        # add all commands
        event_handlers.init_commands(bot, config, _db)
        # add to client loop
        bot._loop.create_task(welcome_new_users(_db, bot, config))

    async def welcome_new_users(_db: Database, client: interactions.Client, config: Config):
        while True:
            await event_handlers.welcome_new_users(_db, client, config)
            # sleep until next check
            await asyncio.sleep(config.NEW_USER_CHECK_INTERVAL)

    bot.start()
    
if __name__ == "__main__":
    main()
