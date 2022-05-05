import argparse
import asyncio
import base64
from hashlib import sha3_256
from typing import List

import pymongo
from tqdm import tqdm
from websocket import WebSocketException

from src import api, config, db
config = config.main_config

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--passphrase", help="Secret passphrase", required=False, default=None)
parser.add_argument("-s", "--secret", help="Secret bytes", required=False, default=None)
parser.add_argument("-n", "--number", help="Number of addresses to generate", required=False, default=10)
parser.add_argument("-d", "--database", help="Database URI", required=True)

async def generate(mongo_uri) -> None:
    try:
        _api = api.API(testing=config.TESTING)
    except WebSocketException as e:
        print(e)
        print("Failed to connect to Substrate node. Exiting...")
        exit(1)
    # Connect to the database
    try:
        _db = db.Database(pymongo.MonogoClient(mongo_uri), _api, config.TESTING)
        addrs: List[str] = list(await _db.get_all_addresses())
        num_addresses = len(addrs)
        if num_addresses < config.NUM_DEPOSIT_ADDRESSES:
            for _ in tqdm(range(config.NUM_DEPOSIT_ADDRESSES - num_addresses), desc="Creating addresses..."):
                print(await _db.create_new_addr(config.COLDKEY_SECRET))
    except Exception as e:
        print(e)
        print("Can't connect to db") 
        exit(1)
    

if __name__ == "__main__":
    # get the database secret from cli
    args = parser.parse_args()
    if (args.passphrase is not None):
        passphrase: str = args.passphrase
        # encode the passphrase as utf-8
        passphrase_bytes = passphrase.encode("utf-8")
        # hash the passphrase with sha3_256 for 32 byte key
        bytes_to_encode = sha3_256(passphrase_bytes).digest()
        key = base64.urlsafe_b64encode(bytes_to_encode)        
    elif (args.secret is not None):
        key = args.secret.encode("utf-8")
    else:
        # throw an error if no passphrase or secret is given
        raise Exception("No passphrase or secret given")

    # Connect to the database
    if (args.database is not None):
        MONGO_URI=f"mongodb://taotip:prod_pass@{args.database}:27017/prod?retryWrites=true&w=majority"
        MONGO_URI_TEST=f"mongodb://taotip:taotip@{args.database}:27017/test?retryWrites=true&w=majority"
    mongo_uri = MONGO_URI_TEST if config.TESTING else MONGO_URI

    asyncio.run(generate(mongo_uri))
    
    