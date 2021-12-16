import discord
import config
import tip
import validate
import parse

def main() -> None:
    print("Running Tau Tip...")
    client = discord.Client()

    @client.event
    async def on_ready():
        print('We have logged in as {0.user}'.format(client))

    @client.event
    async def on_message(message: discord.Message):
        if message.author == client.user:
            return

        if message.content.startswith(config.PROMPT):
            if (len(message.mentions) == 1 and message.mentions[0] != message.author):
                if(validate.is_valid_format(message.content)):
                    sender = message.author
                    amount = parse.get_amount(message.content)
                    recipient = message.mentions[0]
                    t = tip.Tip(sender, recipient, amount)

                    if (t.send()):
                        print(f"{sender} tipped {recipient} {amount} tau")
                    else:
                        print(f"{sender} tried to tip {recipient} {amount} tau but failed")

    client.run(config.DISCORD_TOKEN)
    
if __name__ == "__main__":
    main()