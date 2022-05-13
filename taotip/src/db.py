from datetime import datetime
from typing import Dict, Optional, List

import pymongo
import pymongo.results
from bittensor import Balance
from cryptography.fernet import Fernet


class Database:
    client: pymongo.MongoClient
    db = None
    api: 'api.API' = None

    def __init__(self, mongo_client, api: 'api.API', testing: bool = False) -> None:
        self.api = api
        self.client = mongo_client
        database_str: str = "test" if testing else "prod"
        self.db = self.client[database_str]

    async def check_balance(self, user_id: str) -> Balance:
        assert self.db is not None
        # Get the address for the user
        addr: Address = self.get_address_by_user(user_id)
        if addr is None:
            # No address found
            return Balance.from_rao(0)
        try:
            # Get the balance for the address
            balance: Balance = self.api.get_wallet_balance(addr.address)
            return balance
        except Exception as e:
            print(e)
            return Balance.from_rao(0)

    async def record_tip(self, tip) -> None:
        assert self.db is not None
        new_doc: Dict = {
            "amount": tip.amount.rao,
            "sender": tip.sender,
            "recipient": tip.recipient,
            "time": tip.time
        }
        
        # fail silently
        try:
            result: pymongo.results.InsertOneResult = self.db.tips.insert_one(
                new_doc
            )
        except Exception as e:
            print(e)

    async def record_transaction(self, transaction: 'Transaction') -> None:
        assert self.db is not None
        new_doc: Dict = {
            "amount": Balance.from_tao(transaction.amount).rao,
            "user": str(transaction.user),
            "time": transaction.time
        }
        
        # fail silently
        try:
            result: pymongo.results.InsertOneResult = self.db.transactions.insert_one(
                new_doc
            )
        except Exception as e:
            print(e, "db.record_transaction")

    async def get_deposit_addr(self, transaction: 'Transaction', key: bytes = None) -> Optional[str]:
        assert self.db is not None

        # check if already has an address
        _doc: Dict = self.db.addresses.find_one({
            "user": str(transaction.user)
        })

        if _doc is not None:
            return _doc["address"]
        elif key is not None: # create new address if key is provided
            # create new address
            new_addr: str = await self.create_new_address(key, transaction.user)
            if new_addr is not None:
                return new_addr
        return None

    async def create_new_address(self, key: bytes, user_id: str = None) -> str:
        assert self.db is not None

        new_address: Address = self.api.create_address(key=key)
        doc: Dict = {
            "address": new_address.address,
            "mnemonic": new_address.get_encrypted_mnemonic(),
            "user": None,
            "welcomed": False,
        }

        try:
            result = self.db.addresses.insert_one(doc)
            if user_id is not None:
                await self.add_deposit_address(user_id, new_address.address)
            return new_address.address
        except Exception as e:
            print(e)
            return None
    
    def get_address(self, addr: str, key: bytes) -> 'Address':
        assert self.db is not None

        query: Dict = {
            "address": addr
        }

        try:
            doc: Dict = self.db.addresses.find_one(query)
            addr = Address(doc["address"], doc["mnemonic"], key, decrypt=True)
            return addr
        except Exception as e:
            print(e)
            return None

    async def get_all_addresses(self) -> List[Dict]:
        assert self.db is not None

        query: Dict = {}

        try:
            doc: Dict = self.db.addresses.find(query)
            return doc
        except Exception as e:
            print(e)
            return []

    def get_address_by_user(self, user: str) -> Optional['Address']:
        assert self.db is not None

        query: Dict = {
            "user": str(user)
        }

        try:
            doc: Dict = self.db.addresses.find_one(query)
            addr = Address(doc["address"], doc["mnemonic"], None, decrypt=False)
            return addr
        except Exception as e:
            print(e)
            return None

    async def transfer(self, sender: str, recipient: str, amount: Balance, key: bytes) -> None:
        assert self.db is not None

        # check if already has an address
        sender_addr: Optional[Address] = self.get_address_by_user(sender)
        recipient_addr: Optional[Address] = self.get_address_by_user(recipient)
        
        if sender_addr is None:
            raise Exception("Sender address not found")
        if recipient_addr is None:
            # create new address
            recipient_addr_str = await self.create_new_address(key, recipient)
            recipient_addr = self.get_address_by_user(recipient)
            if recipient_addr is None:
                raise Exception("Recipient address not found. Cannot create new address")

        # check if sender has enough balance
        sender_balance: Balance = await self.check_balance(sender)
        ## Get transfer fee
        transfer_fee: Balance = await self.api.get_fee(sender_addr.address, recipient_addr.address, amount)
        if sender_balance < amount + transfer_fee:
            raise Exception("Sender does not have enough balance")
        
        # transfer
        try:
            call, signature_payload, paymentInfo = self.api.init_transaction( sender_addr.address, recipient_addr.address, amount )
            api_transaction = {
                'message': 'Signature Payload created',
                'signature_payload_hex': signature_payload.to_hex(),
                'paymentInfo': paymentInfo,
                'call': call,
            }
            
            transaction_: Transaction = Transaction( sender, amount.tao )
            await self.record_transaction(transaction_)
            _signed_transaction = await self.api.sign_transaction(self, api_transaction, sender_addr.address, key)
            result = self.api.send_transaction(_signed_transaction)
        except Exception as e:
            print(e)
            raise Exception("Failed to transfer")      

    async def add_deposit_address(self, user: str, addr: str) -> None:
        assert self.db is not None

        # check if address already has a user
        _doc: Dict = self.db.addresses.find_one({
            "address": addr
        })
        if _doc is not None:
            if _doc["user"] is not None:
                raise Exception("Address already has a user")
            else:
                # update user
                self.db.addresses.update_one({
                    "address": addr,
                }, {
                    "$set": {
                        "user": str(user)
                    }
                })
        else:
            raise Exception("Address not found")

    async def set_welcomed_user(self, user: str, welcomed: bool) -> None:
        assert self.db is not None

        try:
            self.db.addresses.update_one({
                "user": str(user)
            }, {
                "$set": {
                    "welcomed": welcomed
                }
            })
        except Exception as e:
            print(e)

    async def get_unwelcomed_users(self) -> List[str]:
        assert self.db is not None

        query: Dict = {
            "welcomed": False
        }

        try:
            doc: Dict = self.db.addresses.find(query)
            users: List[str] = [_doc["user"] for _doc in doc]
            return users
        except Exception as e:
            print(e)
            return []            

class Tip:
    time: datetime = None
    amount: Balance = None
    sender: str = None
    recipient: str = None

    def __init__(self, sender:str, recipient: str, amount: Balance, time: datetime = datetime.now()) -> None:
        self.amount = amount
        self.sender = sender
        self.recipient = recipient
        self.time = time

    def __str__(self) -> str:
        return f"{self.sender} -> {self.recipient} ({self.amount.tao}) tao"

    async def send(self, db: Database, key: bytes) -> bool:
        if (self.amount.rao < 0 or self.sender == self.recipient):
            return False
        balance: Balance = await db.check_balance(self.sender)
        if (balance < self.amount):
            return False
        await db.transfer(self.sender, self.recipient, self.amount, key)
        await db.record_tip(self)
        return True

class WithdrawException(Exception):
    def __init__(self, address: str, amount: int, reason: str) -> None:
        super().__init__(f"{address} {amount} {reason}")
        self.address = address
        self.amount = amount
        self.reason = reason

class DepositException(Exception):
    def __init__(self, address: str, amount: int, reason: str) -> None:
        super().__init__(f"{address} {amount} {reason}")
        self.address = address
        self.amount = amount
        self.reason = reason
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

    async def withdraw(self, db: Database, coldkeyadd: str, key) -> float:
        if (self.amount < 0):
            raise ValueError("Amount must be positive")

        if not db.api.verify_coldkeyadd(coldkeyadd):
            raise WithdrawException(coldkeyadd, self.amount, "withdraw coldkeyadd invalid")

        balance: Balance
        withdraw_addr, balance = await db.api.find_withdraw_address(db, self, key)

        if withdraw_addr is None:
            raise WithdrawException(coldkeyadd, self.amount, "user address not found")

        if (balance.tao < self.amount):
            raise WithdrawException(coldkeyadd, self.amount, f"Balance {balance.tao} too low to withdraw {self.amount}")        

        api_transaction = {
            "coldkeyadd": withdraw_addr,
            "dest": coldkeyadd,
            "amount": self.amount # in tao for this addr
        }

        withdraw_fee: Balance = await db.api.get_withdraw_fee(api_transaction)

        if (balance.tao < self.amount + withdraw_fee.tao):
            raise WithdrawException(coldkeyadd, self.amount, f"Balance {balance.tao} too low to withdraw {self.amount} for fee: {withdraw_fee.tao} tao")
        self.fee = withdraw_fee.tao

        await db.record_transaction(self)

        _transaction = await db.api.create_transaction(api_transaction)
        _signed_transaction = await db.api.sign_transaction(db, _transaction, withdraw_addr, key)
        result = db.api.send_transaction(_signed_transaction)
        if (not result):
            raise Exception("Transaction failed", 4)
        balance: 'Balance' = result['balance']

        return balance.tao
    
    async def deposit(self, db: Database, key: bytes) -> float:
        # Get wallet balance
        addr: Address = await db.get_deposit_addr(self)
        if (addr is None):
            raise DepositException(self.user, self.amount, "No address found")
        balance: Balance = await db.api.get_wallet_balance(addr.address)
        self.amount = balance.tao # Set amount to new balance
        await db.record_transaction(self)
        return balance.tao

class Address:
    address: str # the public coldkeyaddr
    mnemonic: str # mnemonic

    def __init__(self, address: str, mnemonic: bytes, key: bytes, decrypt: bool = False) -> None:
        self.address = address
        self.mnemonic = mnemonic        
        self.key = key
        if (decrypt):
            self.mnemonic = self.__unencrypt(mnemonic, key)

    def get_encrypted_mnemonic(self) -> bytes:
        return self.__encrypt(self.mnemonic, self.key)

    @staticmethod
    def __unencrypt(mnemonic_encrypted: bytes, key: bytes) -> str:
        cipher_suite = Fernet(key)
        unciphered_text = cipher_suite.decrypt(mnemonic_encrypted)
        return str(unciphered_text, "utf-8")

    @staticmethod
    def __encrypt(mnemonic: str, key: bytes) -> str:
        cipher_suite = Fernet(key)
        ciphered_text = cipher_suite.encrypt(bytes(mnemonic, "utf-8"))   #required to be bytes
        return ciphered_text
        