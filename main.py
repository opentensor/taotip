import asyncio
import datetime
from time import strftime
from typing import Dict, List

import discord
import pymongo
import pytz
from bittensor import Balance
from tqdm import tqdm
from websocket import WebSocketException

from src import api, config, parse, validate
from src.db import (Database, DepositException, Tip, Transaction,
                    WithdrawException)

_db: Database = None
_api: api.API = None

from string import Template


class DeltaTemplate(Template):
    delimiter = "%"

def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    d["H"], rem = divmod(tdelta.seconds, 3600)
    d["M"], d["S"] = divmod(rem, 60)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)

def main() -> None:
    print("Running Tao Tip...")
    client = discord.Client() 

    @client.event
    async def on_ready():
        global _db
        global _api
        try:
            _api = api.API(testing=config.TESTING)
        except WebSocketException as e:
            print(e)
            print("Failed to connect to Substrate node. Exiting...")
            await client.close()     
            return

        print('We have logged in as {0.user}'.format(client))
        if (not (await _api.test_connection())):
            print("Error: Can't connect to subtensor node")
            await client.close()
            return
        print(f"Connected to Bittensor ({_api.network})!")

        try:
            mongo_uri = config.MONGO_URI_TEST if config.TESTING else config.MONGO_URI
            _db = Database(pymongo.MongoClient(mongo_uri), _api, config.TESTING)
            addrs: List[str] = list(await _db.get_all_addresses())
            num_addresses = len(addrs)
            if num_addresses < config.NUM_DEPOSIT_ADDRESSES:
                for _ in tqdm(range(config.NUM_DEPOSIT_ADDRESSES - num_addresses), desc="Creating addresses..."):
                    print(await _db.create_new_addr(config.COLDKEY_SECRET))
        except Exception as e:
            print(e)
            print("Can't connect to db")
            await client.close()     
            return

        balance = Balance(0.0)
        addrs: List[Dict] = list(await _db.get_all_addresses())
        for addr in tqdm(addrs, "Checking Balances..."):
            _balance = _api.get_wallet_balance(addr["address"])
            balance += _balance

        print(f"Wallet Balance: {balance}")

        # lock all addresses
        addrs: List[str] = await _db.get_all_addresses()
        for addr in addrs:
            await _db.lock_addr(addr)
        
        # add to client loop
        client.loop.create_task(lock_all_addresses())
        client.loop.create_task(check_deposit())
        
    async def lock_all_addresses():
        global _db
        assert _db is not None
        while True:
            # lock all addresses
            addrs: List[str] = await _db.get_all_addresses()
            for addr in tqdm(addrs, desc="Locking all addresses..."):
                if (await _db.lock_addr(addr)):
                    await _db.set_lock_expiry(addr, 1)

            await asyncio.sleep(config.CHECK_ALL_INTERVAL)
        
    @client.event
    async def on_message(message: discord.Message):
        assert _db is not None
        channel: discord.channel.TextChannel = message.channel
        if message.author == client.user:
            return

        if message.content.startswith(config.PROMPT):
            if (len(message.mentions) == 1 and message.mentions[0] != message.author):
                if ((message.mentions[0].bot or message.mentions[0].id == config.BOT_ID) and not config.TESTING):
                    await channel.send(f"{message.author.mention} You can't tip bots!")
                    return
                if(validate.is_valid_format(message.content)):
                    sender = message.author
                    amount = parse.get_amount(message.content)
                    recipient = message.mentions[0]
                    if ((await client.fetch_user(recipient.id)) is None):
                        await channel.send(f"{message.author.mention} {recipient.mention} is not a valid user!")
                        return
                    t = Tip(sender.id, recipient.id, amount)

                    if (await t.send(_db)):
                        print(f"{sender} tipped {recipient} {amount} tao")
                        await channel.send(f"{sender.mention} tipped {recipient.mention} {amount} tao")
                    else:
                        print(f"{sender} tried to tip {recipient} {amount} tao but failed")
                        await channel.send(f"{sender.mention} tried to tip {recipient.mention} {amount} tao but failed")

        elif isinstance(channel, discord.channel.DMChannel):
            # might be deposit, withdraw, help, or balance check
            user: discord.Member = message.author
            if (validate.is_help(message.content)):
                await channel.send(config.HELP_STR)
            elif (validate.is_balance_check(message.content)):
                balance = await _db.check_balance(user.id)
                
                await channel.send(f"Your balance is {balance} tao")
            elif (validate.is_deposit_or_withdraw(message.content)):
                try:
                    amount = parse.get_amount(message.content)
                except Exception as e:
                    await channel.send(f"Incorrect format.\n" + config.HELP_STR)
                    return
                
                t = Transaction(user.id, amount)
                new_balance: int = None

                if (validate.is_deposit(message.content)):
                    try:
                        await channel.send(f"Remember, withdrawals have a network transfer fee!")
                        deposit_addr = await _db.get_deposit_addr(t)
                        expiry = _db.get_lock_expiry(deposit_addr)
                        expiry_delta: datetime.timedelta = expiry - datetime.datetime.now()
                        expiry_delta = strfdelta(expiry_delta, "%M minutes and %S seconds")
                        expiry = expiry.astimezone(pytz.timezone("EST"))
                        expiry_readable = expiry.strftime('%Y-%m-%d %H:%M:%S %Z')
                        await channel.send(f"Please deposit to {deposit_addr}.\nThis address will be active for another {expiry_delta} until {expiry_readable}.\n")
                    except DepositException as e:
                        await channel.send(f"Error: {e}")
                        return
                    except Exception as e:
                        print(e, "main.on_message")
                        await channel.send("No deposit addresses available.")
                else:
                    # must be withdraw
                    coldkeyadd = parse.get_coldkeyadd(message.content)
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

    async def check_deposit():
        if client is None:
            return

        global _db
        assert _db is not None
        global _api
        assert _api is not None

        while True:
            # check for deposits
            try:
                deposits: List[Transaction] = await _api.check_for_deposits(_db)
            except WebSocketException as e:
                print(e)
                await asyncio.sleep(config.CHECK_ALL_INTERVAL)
                continue

            if (len(deposits) > 0):
                for deposit in tqdm(deposits, desc="Depositing..."):
                    if deposit.amount > 0.0:
                        try:
                            user = await client.fetch_user(deposit.user)
                        except Exception as e:
                            print(e, "main.check_deposit", "fetch_user", deposit.user)
                        if user is not None:
                            new_balance = await _db.check_balance(deposit.user)
                            await user.send(f"Success! Deposited {deposit.amount} tao.\nYour balance is: {new_balance} tao.")
            print("Done Check")
            print("Removing old locks from deposit addresses...")
            # remove old locks
            await _db.remove_old_locks()
            print("Done.")
            # done, await for time
            await asyncio.sleep(config.DEPOSIT_INTERVAL)

    client.run(config.DISCORD_TOKEN)
    
if __name__ == "__main__":
    main()
