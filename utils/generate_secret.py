import base64
import os
import argparse
from hashlib import sha3_256

from cryptography.fernet import Fernet

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--passphrase", help="Secret passphrase", required=False, default=None)

if __name__ == "__main__":
    # generate a new, random, secret
    ## key = Fernet.generate_key()
    args = parser.parse_args()
    if (args.passphrase is not None):
        passphrase: str = args.passphrase
        # encode the passphrase as utf-8
        passphrase_bytes = passphrase.encode("utf-8")
        # hash the passphrase with sha3_256 for 32 byte key
        bytes_to_encode = sha3_256(passphrase_bytes).digest()        
    else:
        # if no passphrase is provided, use random input
        bytes_to_encode = os.urandom(32)
    
    key = base64.urlsafe_b64encode(bytes_to_encode)
    print(key)