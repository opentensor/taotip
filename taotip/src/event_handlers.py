from string import Template
from typing import Dict, List, Tuple, Optional, Union

import pymongo
from bittensor import Balance
from tqdm import tqdm
from websocket import WebSocketException
import interactions

from . import api, config
from .db import Database, DepositException, FeeException, Tip, Transaction, WithdrawException


class DeltaTemplate(Template):
    delimiter = "%"


def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    d["H"], rem = divmod(tdelta.seconds, 3600)
    d["M"], d["S"] = divmod(rem, 60)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)

async def is_in_DM(ctx: interactions.CommandContext) -> bool:
    return (await ctx.get_channel()).type == interactions.ChannelType.DM

async def on_ready_(client: interactions.Client, config: config.Config) -> Tuple[api.API, Database]:
    try:
        _api = api.API(config, testing=config.TESTING)
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


async def check_enough_tao( config: config.Config, _db: Database, ctx: interactions.context._Context, sender: interactions.User, amount: Balance) -> bool:
    balance: Balance = await _db.check_balance(sender.id)
    is_not_DM: bool = not await is_in_DM(ctx)

    if (balance < amount):
        await ctx.send(f"You don't have enough tao to tip {amount.tao} tao", ephemeral=is_not_DM)
        return False
    return True


async def tip_user( config: config.Config, _db: Database, ctx: interactions.context._Context, sender: interactions.User, recipient: interactions.User, amount: Balance) -> None:
    is_not_DM: bool = not await is_in_DM(ctx)

    t = Tip(sender.id, recipient.id, amount)
    try:
        result = await t.send(_db, config.COLDKEY_SECRET)
    except FeeException as e:
        await ctx.channel.send(f"You do not have enough balance to tip {amount.tao} tao with fee {e.fee.tao}", ephemeral=is_not_DM)
        await ctx.message.delete()
        return

    if (result):
        print(f"{sender} tipped {recipient} {amount.tao} tao")
        await ctx.send(f"{sender.mention} tipped {recipient.mention} {amount.tao} tao")
    else:
        print(f"{sender} tried to tip {recipient} {amount.tao} tao but failed")
        await ctx.channel.send(f"You tried to tip {recipient.mention} {amount.tao} tao but it failed", ephemeral=is_not_DM)
        await ctx.message.delete()


async def do_withdraw( config: config.Config, _db: Database, ctx: interactions.CommandContext, user: interactions.User, ss58_address: str, amount: Balance):
    is_not_DM: bool = not await is_in_DM(ctx)

    t = Transaction(user.id, amount)
    new_balance: int = None

    # must be withdraw
    try:
        new_balance = await t.withdraw(_db, ss58_address, config.COLDKEY_SECRET)
        await ctx.send(f"Withdrawal successful.\nYour new balance is: {new_balance} tao", ephemeral=is_not_DM)
    except WithdrawException as e:
        await ctx.send(f"{e}", ephemeral=is_not_DM)
        return
    except Exception as e:
        print(e, "main withdraw")
        await ctx.send("Error making withdraw. Please contact " + config.MAINTAINER, ephemeral=is_not_DM)

    if (t):
        print(f"{user} withdrew {amount} tao: {new_balance}")
    else:
        print(f"{user} tried to withdraw {amount} tao but failed")


async def do_deposit( config: config.Config, _db: Database, ctx: interactions.CommandContext, user: interactions.User ):
    is_not_DM: bool = not await is_in_DM(ctx)

    t = Transaction(user.id)
    new_balance: int = None

    try:
        await ctx.send(f"Remember, withdrawals have a network transfer fee!", ephemeral=is_not_DM)
        deposit_addr = await _db.get_deposit_addr(t)
        if (deposit_addr is None):
            await ctx.send(f"You don't have a deposit address yet. One will be created for you.", ephemeral=is_not_DM)
            deposit_addr = await _db.get_deposit_addr(t, config.COLDKEY_SECRET)
        await ctx.send(f"Please deposit to {deposit_addr}.\nThis address is linked to your discord account.\nOnly you will be able to withdraw from it.", ephemeral=is_not_DM)
    except DepositException as e:
        await ctx.send(f"Error: {e}", ephemeral=is_not_DM)
        return
    except Exception as e:
        print(e, "main.on_message")
        await ctx.send("No deposit addresses available.", ephemeral=is_not_DM)

    
    if (t):
        print(f"{user} deposited tao: {new_balance}")
    else:
        print(f"{user} tried to deposit tao but failed")

async def do_balance_check(config: config.Config, _db: Database, ctx: interactions.CommandContext, user: interactions.User ):
    balance: Balance = await _db.check_balance(user.id)
    is_not_DM: bool = not await is_in_DM(ctx)

    # if ctx is a guild channel, balance is ephemeral
    await ctx.send(f"Your balance is {balance.tao} tao", ephemeral=is_not_DM)

async def welcome_new_users( _db: Database, client: interactions.Client, config: config.Config):
    if (_db is None):
        return

    await client.wait_until_ready()

    users: List[str] = await _db.get_unwelcomed_users()
    for user in tqdm(users, "Welcoming new users..."):
        discord_user: interactions.Member = await interactions.get(client, interactions.Member, object_id=user, parent_id=config.BITTENSOR_DISCORD_SERVER)

        if (discord_user is None):
            print(f"{user} is not a valid discord user in the guild")
            continue
        try:
            await discord_user.send(f"""Welcome! You can deposit or withdraw tao using the following commands:\n{config.HELP_STR}
            \nPlease backup your mnemonic on the following website: {config.EXPORT_URL}""")
            await _db.set_welcomed_user(user, True)
        except Exception as e:
            print(e)
            print("Can't send welcome message to user...")
        