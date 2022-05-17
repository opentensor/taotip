from string import Template
from typing import Dict, List, Tuple, Optional

import discord
import pymongo
from bittensor import Balance
from tqdm import tqdm
from websocket import WebSocketException

from . import api, parse, validate, config
from .db import Database, DepositException, Tip, Transaction, WithdrawException


class DeltaTemplate(Template):
    delimiter = "%"

def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    d["H"], rem = divmod(tdelta.seconds, 3600)
    d["M"], d["S"] = divmod(rem, 60)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)

async def on_ready_(client: discord.Client, config: config.Config) -> Tuple[api.API, Database]:
    try:
        _api = api.API(testing=config.TESTING)
    except WebSocketException as e:
        print(e)
        print("Failed to connect to Substrate node...")
        _api = None

    print('We have logged in as {0.user}'.format(client))
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

async def on_message_(_db: Database, client: discord.Client, message: discord.Message, config: config.Config):
    assert _db is not None

    validator = validate.Validator(config)
    parser: parse.Parser = parse.Parser(config)

    channel: discord.channel.TextChannel = message.channel
    if message.author.id == client.user.id:
        return

    if message.content.startswith(config.PROMPT):
        sender: discord.Member = message.author
        if (len(message.mentions) == 1 and message.mentions[0].id != sender.id):
            if ((message.mentions[0].bot or message.mentions[0].id == config.BOT_ID) and not config.TESTING):
                await sender.send(f"{message.author.mention} You can't tip bots!")
                return
            if(validator.is_valid_format(message.content)):
                amount: Balance = Balance.from_tao(parser.get_amount(message.content))
                recipient = message.mentions[0]
                recipient_user: Optional[discord.User] = await client.fetch_user(recipient.id)
                if (recipient_user is None):
                    await sender.send(f"{message.author.mention} {recipient.mention} is not a valid user!")
                    return
                t = Tip(sender.id, recipient.id, amount)
                result = await t.send(_db, config.COLDKEY_SECRET)
                if (result):
                    print(f"{sender} tipped {recipient} {amount.tao} tao")
                    await channel.send(f"{sender.mention} tipped {recipient.mention} {amount.tao} tao")
                else:
                    print(f"{sender} tried to tip {recipient} {amount.tao} tao but failed")
                    await sender.send(f"You tried to tip {recipient.mention} {amount.tao} tao but it failed")

    elif isinstance(channel, discord.channel.DMChannel):
        # might be deposit, withdraw, help, or balance check
        user: discord.Member = message.author
        if (validator.is_help(message.content)):
            await channel.send(config.HELP_STR)
        elif (validator.is_balance_check(message.content)):
            balance: Balance = await _db.check_balance(user.id)
            
            await channel.send(f"Your balance is {balance.tao} tao")
        elif (validator.is_deposit_or_withdraw(message.content)):
            amount: float
            if (validator.is_deposit(message.content)):
                amount = 0.0
            else:
                try:
                    amount = parser.get_amount(message.content)
                except Exception as e:
                    await channel.send(f"Incorrect format.\n" + config.HELP_STR)
                    return
            
            t = Transaction(user.id, amount)
            new_balance: int = None

            if (validator.is_deposit(message.content)):
                try:
                    await channel.send(f"Remember, withdrawals have a network transfer fee!")
                    deposit_addr = await _db.get_deposit_addr(t)
                    if (deposit_addr is None):
                        await channel.send(f"You don't have a deposit address yet. One will be created for you.")
                        deposit_addr = await _db.get_deposit_addr(t, config.COLDKEY_SECRET)
                    await channel.send(f"Please deposit to {deposit_addr}.\nThis address is linked to your discord account.\nOnly you will be able to withdraw from it.")
                except DepositException as e:
                    await channel.send(f"Error: {e}")
                    return
                except Exception as e:
                    print(e, "main.on_message")
                    await channel.send("No deposit addresses available.")
            else:
                # must be withdraw
                coldkeyadd = parser.get_coldkeyadd(message.content)
                try:
                    new_balance = await t.withdraw(_db, coldkeyadd, config.COLDKEY_SECRET)
                    await channel.send(f"Withdrawal successful.\nYour new balance is: {new_balance} tao")
                except WithdrawException as e:
                    await channel.send(f"{e}")
                    return
                except Exception as e:
                    print(e, "main withdraw")
                    await channel.send("Error making withdraw. Please contact " + config.MAINTAINER)

            if (t):
                print(f"{user} modified balance by {amount} tao: {new_balance}")
            else:
                print(f"{user} tried to modify balance by {amount} tao but failed")
        else:
            await channel.send(config.HELP_STR)

async def welcome_new_users( _db: Database, client: discord.Client, config: config.Config):
    if (_db is None):
        return

    users: List[str] = await _db.get_unwelcomed_users()
    for user in tqdm(users, "Welcoming new users..."):
        discord_user = await client.fetch_user(int(user))
        await discord_user.send(f"""Welcome! You can deposit or withdraw tao using the following commands:\n{config.HELP_STR}
        \nPlease backup your mnemonic on the following website: {config.EXPORT_URL}""")
        await _db.set_welcomed_user(user, True)

