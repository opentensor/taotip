from typing import Dict, List
import discord
import config
import validate
import parse
import api
from db import Tip, Transaction, Database
import datetime
import asyncio

def main() -> None:
    _db: Database = None
    print("Running Tau Tip...")
    client = discord.Client()

    @client.event
    async def on_ready():
        print('We have logged in as {0.user}'.format(client))
        if (not (await api.test_connection())):
            print("Error: Can't connect to subtensor node")
            await client.close()
            return
        print("Connected to Bittensor!")

        try:
            _db = Database(config.MONGO_URI)
            for _ in range(10):
                print(await _db.create_new_addr())
        except Exception as e:
            print(e)
            print("Can't connect to db")
            await client.close()     
            return   

        
        exit(0)

        balance = 0
        addrs: List[Dict] = _db.get_all_addresses()
        for addr in addrs:
            _balance = await _db.check_balance(addr.address)
            balance += _balance

        print(f"Wallet Balance: {balance}")
        


    @client.event
    async def on_message(message: discord.Message):
        assert _db is not None

        if message.author == client.user:
            return

        if message.content.startswith(config.PROMPT):
            channel: discord.channel.TextChannel = message.channel
            if (len(message.mentions) == 1 and message.mentions[0] != message.author):
                if(validate.is_valid_format(message.content)):
                    sender = message.author
                    amount = parse.get_amount(message.content)
                    recipient = message.mentions[0]
                    t = Tip(sender.id, recipient.id, amount)

                    if (t.send(_db)):
                        print(f"{sender} tipped {recipient} {amount} tau")
                        channel.send(f"{sender.nick} tipped {recipient.nick} {amount} tau")
                    else:
                        print(f"{sender} tried to tip {recipient} {amount} tau but failed")
            elif type(channel) is discord.channel.DMChannel:
                # might be deposit, withdraw, help, or balance check
                user: discord.Member = message.author
                if (validate.is_help(message.content)):
                    channel.send(config.HELP_STR)
                elif (validate.is_balance_check(message.content)):
                    balance = await _db.check_balance(user.name)
                    
                    channel.send(f"Your balance is {balance} tau")
                elif (validate.is_deposit_or_withdraw(message.content)):
                    amount = parse.get_amount(message.content)
                    
                    t = Transaction(user.name, amount)
                    new_balance: int = None

                    if (validate.is_deposit(message.content)):
                        try:
                            deposit_addr = await _db.get_deposit_addr(t)
                            channel.send(f"Please deposit to {deposit_addr}. This address will be active for {datetime.timedelta(seconds=config.DEP_ACTIVE_TIME)}.")
                        except Exception as e:
                            print(e)
                            channel.send("No deposit addresses available.")
                    else:
                        # must be withdraw
                        coldkeyadd = parse.get_coldkeyadd(message.content)
                        try:
                            new_balance = await t.withdraw(_db, coldkeyadd)
                        except Exception as e:
                            print(e)
                            channel.send("Error making withdraw. Please contact " + config.MAINTAINER)

                    if (t):
                        print(f"{user} modified balance by {amount} tau: {new_balance}")
                    else:
                        print(f"{user} tried to modify balance by {amount} tau but failed")
                else:
                    channel.send(config.HELP_STR)


    @asyncio.coroutine
    def check_deposit():
        return
        assert _db is not None
        while True:
            print("Checking for new deposits...")
            # check for deposits
            deposits: List[Transaction] = api.check_for_deposits()
            for deposit in deposits:
                deposit.deposit(_db)
            print("Removing old locks from deposit addresses...")
            # remove old locks
            _db.remove_old_locks()
            # done, yeild for time
            yield from asyncio.sleep(config.DEPOSIT_INTERVAL)

    # add to client loop
    client.loop.create_task(check_deposit())

    client.run(config.DISCORD_TOKEN)
    
if __name__ == "__main__":
    main()