import asyncio
import interactions

from typing import List, Union

from bittensor import Balance

from src import api, event_handlers
from src.config import main_config as config, Config
from src.db import Database


_db: Database = None
_api: api.API = None

def main() -> None:
    print("Running Tao Tip...")

    bot = interactions.Client(
        token=config.DISCORD_TOKEN,
        intents=interactions.Intents.DIRECT_MESSAGE_REACTIONS
        | interactions.Intents.DIRECT_MESSAGES
        | interactions.Intents.GUILD_MEMBERS
    )

    bot = interactions.Client(token=config.DISCORD_TOKEN)
    
    async def init():
        _api, _db = await event_handlers.on_ready_(bot, config)

        if _api is None or _db is None:
            print("Failed to initialize\nRetrying in 5s...")
            await asyncio.sleep(5)  # wait 5 seconds
            await init()
            return
        else:
            print("Initialized!")

        @bot.event
        async def on_start():
            # add to client loop
            bot._loop.create_task(welcome_new_users(_db, bot, config))

        @bot.command(
            name="help",
            description="Show help",
        )
        async def help(ctx: interactions.CommandContext):
            await ctx.send(config.HELP_STR, ephemeral=True)


        @bot.user_command(
            name="Tip User",
        )
        async def tip_user_command(ctx: interactions.CommandContext) -> None:
            """
            Tip a user
            """
            modal = interactions.Modal(
                title="tip user",
                custom_id="tip_user_form",
                components=[
                    interactions.TextInput(
                        label="Recipient",
                        custom_id="recipient",
                        required=True,
                        value=str(ctx.target.user.id),
                        style=interactions.TextStyleType.SHORT,
                        disabled=True,
                    ),
                    interactions.TextInput(
                        label="Amount",
                        custom_id="amount",
                        placeholder="0 TAO",
                        required=True,
                        value="0",
                        style=interactions.TextStyleType.SHORT,
                    ),
                ],
            )

            await ctx.popup(modal)

        @bot.modal("tip_user_form")
        async def tip_user_modal_response(ctx: interactions.CommandContext, recipient: str, amount: str):
            """
            Handle the tip user modal response
            """
            try:
                amount = float(amount)
            except ValueError:
                await ctx.send(f"Invalid amount: {amount} . Should be numeric", ephemeral=True)
                return interactions.StopCommand()

            if amount <= 0.0:
                await ctx.send(f"Invalid amount: {amount} . Must be >= 0.0 tao", ephemeral=True)
                return interactions.StopCommand()
            try:
                guild: interactions.Guild = await ctx.get_guild()
                recipient: interactions.Member = await guild.get_member(int(recipient))
            except ValueError:
                await ctx.send("Invalid recipient", ephemeral=True)
                return interactions.StopCommand()
            
            await event_handlers.tip_user(config, _db, ctx, ctx.user, recipient.user, Balance.from_tao(amount))

        @bot.command(
            name="tip",
            description="Tip a user with TAO",
            dm_permission=False, # only allow in guild, not DMs
            options = [
                interactions.Option(
                    name="recipient",
                    description="The user to tip",
                    type=interactions.OptionType.USER,
                    required=True,
                ),
                interactions.Option(
                    name="amount",
                    description="How much TAO to tip",
                    type=interactions.OptionType.NUMBER,
                    required=True,
                ),
            ],
        )
        @interactions.autodefer(5)
        async def tip(ctx: interactions.CommandContext, recipient: interactions.Member, amount: Union[float, int]):
            sender: interactions.User = ctx.user
            recipient: interactions.User = recipient.user
            if (recipient == sender):
                await ctx.send("You can't tip yourself!", ephemeral=True)
                return interactions.StopCommand()

            if (recipient.bot  and not config.TESTING):
                await ctx.send(f"You can't tip bots!", ephemeral=True)
                return interactions.StopCommand()

            amount: Balance = Balance.from_tao(amount)

            if (amount <= 0.0):
                await ctx.send("Invalid amount", ephemeral=True)
                return interactions.StopCommand()

            # check if sender has enough TAO
            if not (await event_handlers.check_enough_tao(config, _db, ctx, sender, amount)):
                return interactions.StopCommand()

            # ask for confirmation
            send_tip_button = interactions.Button(
                style=interactions.ButtonStyle.SUCCESS,
                label="Send",
                custom_id="send_tip",
            )

            cancel_button = interactions.Button(
                style=interactions.ButtonStyle.DANGER,
                label="Cancel",
                custom_id="cancel_tip",
            )

            row = interactions.ActionRow.new(send_tip_button, cancel_button)

            # ask for confirmation to send tip
            await ctx.send("Are you sure you want to tip {} to {}?".format(amount, recipient.mention), components=row, ephemeral=True)

        @bot.component("send_tip")
        async def button_response(ctx: interactions.ComponentContext):
            sender = ctx.user
            recipient_id = ctx.message.content[29:].split(" to ")[1].replace('?', '').replace('<@', '').replace('>', '')
            recipient = await interactions.get(bot, interactions.User, object_id=recipient_id)
            # get the float amount from the string
            amount_str = ctx.message.content.split("Are you sure you want to tip ")[1].split(" to ")[0][1:]
            amount = Balance.from_tao(float(amount_str))
            await event_handlers.tip_user(config, _db, ctx, sender, recipient, amount)
            return interactions.StopCommand()

        @bot.component("cancel_tip")
        async def cancel_response(ctx: interactions.ComponentContext):
            await ctx.send("Tip cancelled", ephemeral=True)

        @bot.command(
            name="balance",
            description="Check your balance",
        )
        async def balance(ctx: interactions.CommandContext):
            await event_handlers.do_balance_check(config, _db, ctx, ctx.user)
        
        @bot.command(
            name="deposit",
            description="Deposit TAO to your tip wallet",
        )
        async def deposit(ctx: interactions.CommandContext):
            await event_handlers.do_deposit(config, _db, ctx, ctx.user)

        @bot.command(
            name="withdraw",
            description="Withdraw TAO from your tip wallet",
            options=[
                interactions.Option(
                    name="ss58_address",
                    description="The address to withdraw to",
                    type=interactions.OptionType.STRING,
                    required=True,
                ),
                interactions.Option(
                    name="amount",
                    description="How much TAO to withdraw",
                    type=interactions.OptionType.NUMBER,
                    required=True,
                ),
            ]
        )
        async def withdraw(ctx: interactions.CommandContext, ss58_address: str, amount: Union[float, int]):
            await event_handlers.do_withdraw(config, _db, ctx, ctx.user, ss58_address, Balance.from_tao(amount))

    async def welcome_new_users(
        _db: Database, client: interactions.Client, config: Config
    ):
        while True:
            await event_handlers.welcome_new_users(_db, client, config)
            # sleep until next check
            await asyncio.sleep(config.NEW_USER_CHECK_INTERVAL)

    bot._loop.create_task(init())
    bot.start()

if __name__ == "__main__":
    main()
