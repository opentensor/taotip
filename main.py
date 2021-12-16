import discord
import config
import tip

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
            print("Message: {message.content}")
            print("Author: {message.author}")
            print("Mentions: {message.mentions}")

    client.run(config.DISCORD_TOKEN)
    

# 274877908992
if __name__ == "__main__":
    main()