from typing import Dict, List, Optional, Tuple, Union
import pymongo
from pymongo import ReturnDocument
import pymongo.results
from datetime import datetime, timedelta
import api
import config
from bittensor import Balance
from cryptography.fernet import Fernet
import asyncio

class Database:
    client: pymongo.MongoClient
    db = None

    def __init__(self, mongo_uri: str, testing: bool = False) -> None:
        self.client = pymongo.MongoClient(mongo_uri)
        database_str: str = "test" if testing else "prod"
        self.db = self.client[database_str]

    async def check_balance(self, name: str) -> Optional[float]:
        assert self.db is not None
        query: Dict = {
            "discord_user": name
        }

        projection: Dict = {
            "balance": True
        }

        doc: Dict = self.db.balances.find_one(query, projection=projection)
        if (doc is not None):
            balance_rao: int = doc["balance"]

            return Balance.from_rao(balance_rao).tao
            
        return Balance.from_rao(0).tao

    async def update_balance(self, name: str, amount: float) -> Optional[float]:
        assert self.db is not None
        query: Dict = {
            "discord_user": name
        }

        update: Dict = {
            "$add": {
                "balance": Balance.from_tao(amount).rao
            }
        }

        projection: Dict = {
            "balance": True
        }

        doc: Dict = await self.db.balances.find_one_and_update(
            query,
            update,
            projection=projection,
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        if (doc is not None):
            balance_rao: int = doc.balance
            return Balance.from_rao(balance_rao).tao
        return None

    async def record_tip(self, tip) -> None:
        assert self.db is not None
        new_doc: Dict = {
            "amount": Balance.from_tao(tip.amount).rao,
            "sender": tip.sender,
            "recipient": tip.recipient,
            "time": tip.time
        }
        
        # fail silently
        try:
            result: pymongo.results.InsertOneResult = await self.db.tips.insert_one(
                new_doc
            )
        except Exception as e:
            print(e)

    async def record_transaction(self, transaction) -> None:
        assert self.db is not None
        new_doc: Dict = {
            "amount": Balance.from_tao(transaction.amount).rao,
            "user": transaction.sender,
            "time": transaction.time
        }
        
        # fail silently
        try:
            result: pymongo.results.InsertOneResult = await self.db.transactions.insert_one(
                new_doc
            )
        except Exception as e:
            print(e, "db.record_transaction")

    async def get_withdraw_addresses(self) -> List[str]:
        assert self.db is not None
        query: Dict = {
            "locked": False,
            "$orderby": {
                "balance": -1
            }
        }

        addrs: List[Dict] = await self.db.addresses.find(query)
        return addrs

    async def lock_addr(self, address: Union[str, Dict]) -> bool:
        assert self.db is not None
        if not isinstance(address, str):
            address = address["address"]

        query: Dict = {
            "address": address
        }

        update: Dict = {"$set": {
            "locked": True
        }}

        try:
            # returns original
            doc: Dict = self.db.addresses.find_one_and_update(query, update, return_document=ReturnDocument.BEFORE)
            return doc is not None and (not doc["locked"]) # checks if locked before update happened
        except Exception as e:
            print(e, "db.lock_addr")
            return False

    async def unlock_addr(self, address: str) -> None:
        assert self.db is not None
        query: Dict = {
            "address": address
        }

        update: Dict = { "$set": {
            "locked": False
        }}

        try:
            await self.db.addresses.update_one(query, update)
        except Exception as e:
            print(e)

    async def set_lock_expiry(self, address: str, expiry: int) -> None:
        _query: Dict = {
            "address": address
        }

        update: Dict = {"$set": {
            "unlock": datetime.now() + datetime.timedelta(seconds=expiry)
        }}
        self.db.addresses.update_one(_query, update)
        return None

    async def get_deposit_addr(self, transaction) -> str:
        assert self.db is not None

        # check if already has an address
        # if so, increase time
        _doc: Dict = await self.db.addresses.find_one_and_update({
            "user": transaction.user.name
        }, {
            "unlock": datetime.now() + timedelta(seconds=config.DEP_ACTIVE_TIME),
        }, return_document=ReturnDocument.AFTER)
        if (_doc is not None):
            return _doc["address"]

        query: Dict = {
            "locked": False
        }

        doc: Dict = await self.db.addresses.find_one(query)

        while(not (await self.lock_addr(doc.address))):
            doc = self.db.addresses.find_one(query)
            await asyncio.sleep(1)
        
        # should've locked an address now
        # add unlock time
        _query: Dict = {
            "address": doc["address"],
            "$orderby": {
                "balance": -1
            }
        }

        update: Dict = {"$set": {
            "unlock": datetime.now() + timedelta(seconds=config.DEP_ACTIVE_TIME),
            "user": transaction.user
        }}

        self.db.addresses.update_one(_query, update)
        return doc["address"]

    async def remove_old_locks(self) -> None:
        assert self.db is not None
        query: Dict = {
            "$or": [
                { "unlock": 
                    {"$lte": datetime.now() }
                },
                { "unlock": None }
            ]
        }

        update: Dict = {
            "$set": {
                "unlock": None,
                "locked": False,
                "user": None
            }
        }

        result = self.db.addresses.update_many(query, update)
        return result.modified_count if result is not None else None

    async def create_new_addr(self) -> str:
        assert self.db is not None

        new_address: Address = await api.create_address()
        doc: Dict = {
            "address": new_address.address,
            "mnemonic": new_address.get_encrypted_mnemonic(),
            "locked": False,
            "unlock": None,
            "user": None,
            "balance": 0
        }

        try:
            result = await self.db.addresses.insert_one(doc)
            return new_address.address
        except Exception as e:
            print(e)
            return None
    
    async def get_address(self, addr: str) -> Dict:
        assert self.db is not None

        query: Dict = {
            "address": addr
        }

        try:
            doc: Dict = await self.db.addresses.find_one(query)
            addr = Address(doc["address"], doc["mnemonic"], config.COLDKEY_SECRET)
            return addr
        except Exception as e:
            print(e)
            return None

    async def get_all_addresses(self) -> List[str]:
        assert self.db is not None
        return list(self.db.addresses.find({}))

    async def get_all_addresses_with_lock(self) -> List[str]:
        assert self.db is not None

        query: Dict = {
            "locked": True
        }

        return self.db.addresses.find(query)

    async def update_addr_balance(self, addr: str, balance_rao: int) -> Tuple[int, str]:
        assert self.db is not None

        query: Dict = {
            "address": addr
        }

        update: Dict = {
            "$set": {"balance": balance_rao }
        }

        try:
            result: Dict = self.db.addresses.find_one_and_update(query, update)
            return balance_rao - result["balance"], result["user"]
        except Exception as e:
            print(e)
            return None

class Tip:
    time: datetime
    amount: float
    sender: str
    recipient: str

    def __init__(self, sender:str, recipient: str, amount: int, time: datetime = datetime.now()) -> None:
        self.amount = amount
        self.sender = sender
        self.recipient = recipient
        self.time = time

    def __str__(self) -> str:
        return f"{self.amount} tao"

    async def send(self, db: Database) -> bool:
        if (self.amount < 0):
            return False
        balance = await db.check_balance(self.sender)
        if (balance < self.amount):
            return False
        db.update_balance(self.sender, -self.amount)
        db.update_balance(self.recipient, self.amount)
        db.record_tip(self)
        return True

class Transaction:
    time: datetime
    amount: float
    user: str
    fee: float

    def __init__(self, user:str, amount: float, time: datetime = datetime.now()) -> None:
        self.amount = amount
        self.user = user
        self.time = time

    def __str__(self) -> str:
        return f"{self.amount} tao"

    async def withdraw(self, db: Database, coldkeyadd: str) -> float:
        if (self.amount < 0):
            raise "Amount invalid"

        if api.verify_coldkeyadd(coldkeyadd):
            raise "withdraw coldkeyadd invalid"

        # gets balance in tao (float)
        balance = db.check_balance(self.user)
        if (balance < self.amount):
            raise "Balance too low to withdraw"
        
        # get withdraw_addr to withdraw from
        try:
            withdraw_fee = await api.get_withdraw_fee()

            if (balance < self.amount + withdraw_fee):
                raise "Balance too low to withdraw"

            self.fee = withdraw_fee

            new_balance = await db.update_balance(self.user, -self.amount + -self.fee)
            await db.record_transaction(self)

            withdraw_addr, amounts = await api.find_withdraw_address(self)

        except Exception as e:
            print(e, "db.withdraw")
            raise "Withdraw error; Not enough tao in wallets"
        for addr, amount in zip(withdraw_addr, amounts):
            api_transaction = {
                "coldkeyadd": addr,
                "dest": coldkeyadd,
                "amount": amount # in tao for this addr
            }
            _transaction = await api.create_transaction(api_transaction)
            _signed_transaction = await api.sign_transaction(self, _transaction, addr)
            result = await api.send_transaction(_signed_transaction)
            if (not result):
                raise "Transaction failed"
            balance = await api.get_wallet_balance(addr)
            await db.update_addr_balance(addr, balance)

        return new_balance
    
    async def deposit(self, db: Database) -> float:
        if (self.amount < 0):
            raise "Amount invalid"
        new_balance = db.update_balance(self.user, self.amount)
        await db.record_transaction(self)
        return new_balance

class Address:
    address: str # the public coldkeyaddr
    mnemonic: str # mnemonic

    def __init__(self, address: str, mnemonic: bytes, key: bytes = None) -> None:
        self.address = address
        self.mnemonic = mnemonic
        if (key):
            self.mnemonic = self.__unencrypt(mnemonic, key)

    def get_encrypted_mnemonic(self) -> bytes:
        return self.__encrypt(self.mnemonic, config.COLDKEY_SECRET)

    @staticmethod
    def __unencrypt(mnemonic_encrypted: bytes, key: bytes) -> str:
        cipher_suite = Fernet(key)
        unciphered_text = (cipher_suite.decrypt(mnemonic_encrypted))
        return str(unciphered_text, "utf-8")

    @staticmethod
    def __encrypt(mnemonic: str, key: bytes) -> str:
        cipher_suite = Fernet(key)
        ciphered_text = cipher_suite.encrypt(bytes(mnemonic, "utf-8"))   #required to be bytes
        return ciphered_text
        