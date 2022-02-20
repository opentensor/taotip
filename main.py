from typing import Dict, List
import discord
from numpy import isin
import config
import validate
import parse
import api
from db import Tip, Transaction, Database
import datetime
import asyncio
from bittensor import Balance
from tqdm import tqdm

_db: Database = None

def main() -> None:
    print("Running Tao Tip...")
    client = discord.Client() 

    @client.event
    async def on_ready():
        global _db
        print('We have logged in as {0.user}'.format(client))
        if (not (await api.test_connection())):
            print("Error: Can't connect to subtensor node")
            await client.close()
            return
        print("Connected to Bittensor!")

        try:
            _db = Database(config.MONGO_URI, config.TESTING)
            addrs: List[str] = list(await _db.get_all_addresses())
            num_addresses = len(addrs)
            if num_addresses < config.NUM_DEPOSIT_ADDRESSES:
                for _ in tqdm(range(config.NUM_DEPOSIT_ADDRESSES - num_addresses), desc="Creating addresses..."):
                    print(await _db.create_new_addr())
        except Exception as e:
            print(e)
            print("Can't connect to db")
            await client.close()     
            return

        balance = Balance(0.0)
        addrs: List[Dict] = list(await _db.get_all_addresses())
        for addr in tqdm(addrs, "Checking Balances..."):
            _balance = await api.get_wallet_balance(addr["address"])
            balance += _balance

        print(f"Wallet Balance: {balance}")

        # lock all addresses
        addrs: List[str] = await _db.get_all_addresses()
        for addr in addrs:
            await _db.lock_addr(addr)
        
        # add to client loop
        client.loop.create_task(lock_all_addresses())
        client.loop.create_task(check_deposit())
        
    @asyncio.coroutine
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
                if(validate.is_valid_format(message.content)):
                    sender = message.author
                    amount = parse.get_amount(message.content)
                    recipient = message.mentions[0]
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
                        await channel.send(f"Please deposit to {deposit_addr}. This address will be active for {datetime.timedelta(seconds=config.DEP_ACTIVE_TIME)}.")
                    except Exception as e:
                        print(e, "main.on_message")
                        await channel.send("No deposit addresses available.")
                else:
                    # must be withdraw
                    coldkeyadd = parse.get_coldkeyadd(message.content)
                    try:
                        new_balance = await t.withdraw(_db, coldkeyadd)
                    except Exception as e:
                        print(e, "main withdraw")
                        await channel.send("Error making withdraw. Please contact " + config.MAINTAINER)

                if (t):
                    print(f"{user} modified balance by {amount} tao: {new_balance}")
                else:
                    print(f"{user} tried to modify balance by {amount} tao but failed")
            else:
                await channel.send(config.HELP_STR)


    @asyncio.coroutine
    async def check_deposit():
        if client is None:
            return

        global _db
        assert _db is not None

        while True:
            # check for deposits
            deposits: List[Transaction] = await api.check_for_deposits(_db)
            if (len(deposits) > 0):
                for deposit in tqdm(deposits, desc="Depositing..."):
                    new_balance = await deposit.deposit(_db)
                    if deposit.amount > 0.0:
                        user = client.get_user(deposit.user)
                        if user is not None:
                            await user.send(f"Success! Deposited {deposit.amount} tao. Your balance is {new_balance} tao.")
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