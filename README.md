# Invite
 [Invite the bot to your server!](https://discord.com/api/oauth2/authorize?client_id=323594922584440832&permissions=274877975616&scope=bot)

# Run Yourself
## Requirements
- docker
- a mongodb server
- a discord developer account
- a [subtensor](https://github.com/opentensor/subtensor/) node

## Setup
Clone the repo  
`git clone https://github.com/camfairchild/taotip/`  
Enter the directory  
`cd taotip/`  
Now fill in the config.py with your info.  
Build the services  
`./build.sh && ./build_export-service.sh`
Docker compose up  
`docker-compose up -d`

## Generating a secret for DB encryption
Before using the tip bot, you must generate a secret for encrypting the wallet mnemonics on the database.
You can generate a key using the below:  
`python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())"`  
