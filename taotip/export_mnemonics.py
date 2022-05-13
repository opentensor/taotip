from src.config import Config, main_config
from pymongo import MongoClient
from cryptography.fernet import Fernet

if __name__ == "__main__":
    cipher_suite = Fernet(main_config.COLDKEY_SECRET)
    try:
        client = MongoClient(main_config.MONGO_URI_TEST.replace('@mongodb', '@localhost'))
        db = client.test
        addresses = db.addresses.find({})
        for address in addresses:        
            print(address['address'])
            enc_mnemonic = address['mnemonic']
            print(enc_mnemonic)
            unciphered_mnemonic = cipher_suite.decrypt(enc_mnemonic)
            unciphered_mnemonic = str(unciphered_mnemonic, "utf-8")
            print(unciphered_mnemonic)
    except Exception as e:
        print(e)
        exit(1)
        


