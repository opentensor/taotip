from string import Template
from typing import Dict, List, Tuple, Optional, Union

import pymongo
from bittensor import Balance
from tqdm import tqdm
from websocket import WebSocketException
import interactions

from . import api, config
from .db import Database, DepositException, Tip, Transaction, WithdrawException


class DeltaTemplate(Template):
    delimiter = "%"


def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    d["H"], rem = divmod(tdelta.seconds, 3600)
    d["M"], d["S"] = divmod(rem, 60)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


async def on_ready_(client: interactions.Client, config: config.Config) -> Tuple[api.API, Database]:
    try:
        _api = api.API(testing=config.TESTING)
    except WebSocketException as e:
        print(e)
        print("Failed to connect to Substrate node...")
        _api = None

    print('We have logged in as {}'.format(client.me.name))
    if (_api is None or not (await _api.test_connection())):
        print("Error: Can't connect to subtensor node...")
        _api = None
    print(f"Connected to Bittensor ({_api.network})!")

    try:
        mongo_uri = config.MONGO_URI_TEST if config.TESTING else config.MONGO_URI
        _db = Database(pymongo.MongoClient(mongo_uri), _api, config.TESTING)
    except Exception as e:
        print(e)
        print("Can't connect to db...")  
        _db = None

    if _db is not None:
        if _api is not None:
            balance = Balance(0.0)
            addrs: List[Dict] = list(await _db.get_all_addresses())
            for addr in tqdm(addrs, "Checking Balances..."):
                _balance = _api.get_wallet_balance(addr["address"])
                balance += _balance

            print(f"Wallet Balance: {balance}")
        
    return _api, _db  


async def tip_user( config: config.Config, _db: Database, ctx: interactions.context._Context, sender: interactions.User, recipient: interactions.User, amount: Balance) -> None:
    t = Tip(sender.id, recipient.id, amount)
    result = await t.send(_db, config.COLDKEY_SECRET)
    if (result):
        print(f"{sender} tipped {recipient} {amount.tao} tao")
        await ctx.send(f"{sender.mention} tipped {recipient.mention} {amount.tao} tao")
    else:
        print(f"{sender} tried to tip {recipient} {amount.tao} tao but failed")
        await sender.send(f"You tried to tip {recipient.mention} {amount.tao} tao but it failed")


async def do_withdraw( config: config.Config, _db: Database, ctx: interactions.CommandContext, user: interactions.User, ss58_address: str, amount: Balance):
    t = Transaction(user.id, amount)
    new_balance: int = None

    # must be withdraw
    try:
        new_balance = await t.withdraw(_db, ss58_address, config.COLDKEY_SECRET)
        await ctx.send(f"Withdrawal successful.\nYour new balance is: {new_balance} tao")
    except WithdrawException as e:
        await ctx.send(f"{e}")
        return
    except Exception as e:
        print(e, "main withdraw")
        await ctx.send("Error making withdraw. Please contact " + config.MAINTAINER)

    if (t):
        print(f"{user} withdrew {amount} tao: {new_balance}")
    else:
        print(f"{user} tried to withdraw {amount} tao but failed")


async def do_deposit( config: config.Config, _db: Database, ctx: interactions.CommandContext, user: interactions.User ):

    t = Transaction(user.id)
    new_balance: int = None

    try:
        await ctx.send(f"Remember, withdrawals have a network transfer fee!")
        deposit_addr = await _db.get_deposit_addr(t)
        if (deposit_addr is None):
            await ctx.send(f"You don't have a deposit address yet. One will be created for you.")
            deposit_addr = await _db.get_deposit_addr(t, config.COLDKEY_SECRET)
        await ctx.send(f"Please deposit to {deposit_addr}.\nThis address is linked to your discord account.\nOnly you will be able to withdraw from it.")
    except DepositException as e:
        await ctx.send(f"Error: {e}")
        return
    except Exception as e:
        print(e, "main.on_message")
        await ctx.send("No deposit addresses available.")

    
    if (t):
        print(f"{user} deposited tao: {new_balance}")
    else:
        print(f"{user} tried to deposit tao but failed")

async def do_balance_check(config: config.Config, _db: Database, ctx: interactions.CommandContext, user: interactions.User ):
    balance: Balance = await _db.check_balance(user.id)
    is_not_DM: bool = (ctx.channel.type != interactions.ChannelType.DM)

    # if ctx is a guild channel, balance is ephemeral
    await ctx.send(f"Your balance is {balance.tao} tao", ephemeral=is_not_DM)


def init_commands(bot: interactions.Client, config: 'config.Config', _db: Database):
    @bot.user_command(
        name="tip",
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
        if not amount.isnumeric():
            await ctx.send("Invalid amount")
            return
        amount = float(amount)
        if amount <= 0.0:
            await ctx.send("Invalid amount")
            return
        
        guild: interactions.Guild = await ctx.get_guild()
        recipient: interactions.Member = await guild.get_member(int(recipient))
        
        await tip_user(config, _db, ctx, ctx.author, recipient.user, Balance.from_tao(amount))

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
    async def tip(ctx: interactions.CommandContext, recipient: interactions.User, amount: Union[float, int]):
        sender: interactions.Member = ctx.author
        if (recipient == sender):
            await ctx.send("You can't tip yourself!")
            return

        if (recipient.bot and not config.TESTING):
            await sender.send(f"You can't tip bots!")
            return

        amount: Balance = Balance.from_tao(amount)
        guild: interactions.Guild = await ctx.get_guild()

        result: List[interactions.Member] = await guild.search_members(recipient.id, limit=1)
        if (len(result) == 0):
            await ctx.send(f"{recipient} is not in this server!")
            return

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

        @bot.component("send_tip")
        async def button_response(ctx: interactions.ComponentContext):
            await tip_user(config, _db, ctx, sender, recipient, amount)

        @bot.component("cancel_tip")
        async def cancel_response(ctx):
            return 

        # ask for confirmation to send tip
        await ctx.send("Are you sure you want to tip {} tao to {}?".format(amount, recipient.mention), components=row)

    @bot.command(
        name="help",
        description="Show help",
    )
    async def help(ctx: interactions.CommandContext):
        await ctx.author.send(config.HELP_STR, ephemeral=True)

    @bot.command(
        name="balance",
        description="Check your balance",
        scope=config.BITTENSOR_DISCORD_SERVER,
    )
    async def balance(ctx: interactions.CommandContext):
        await do_balance_check(config, _db, ctx, ctx.author.user)
    
    @bot.command(
        name="deposit",
        description="Deposit TAO to your tip wallet",
    )
    async def deposit(ctx: interactions.CommandContext):
        await do_deposit(config, _db, ctx, ctx.author.user)

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
        await do_withdraw(config, _db, ctx, ctx.author.user, ss58_address, Balance.from_tao(amount))

async def welcome_new_users( _db: Database, client: interactions.Client, config: config.Config):
    if (_db is None):
        return

    users: List[str] = await _db.get_unwelcomed_users()
    for user in tqdm(users, "Welcoming new users..."):
        discord_user: interactions.Member = await client.get(
            client, interactions.User, parent_id=config.BITTENSOR_DISCORD_SERVER, object_id=int(user)
        )
        try:
            await discord_user.send(f"""Welcome! You can deposit or withdraw tao using the following commands:\n{config.HELP_STR}
            \nPlease backup your mnemonic on the following website: {config.EXPORT_URL}""")
            await _db.set_welcomed_user(user, True)
        except Exception as e:
            print(e)
            print("Can't send welcome message to user...")
        