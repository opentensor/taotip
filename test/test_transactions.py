import random
from types import SimpleNamespace
from typing import Dict, List, Set
from unittest.mock import MagicMock, patch

import bittensor
from cryptography.fernet import Fernet
from scalecodec.base import ScaleBytes
from substrateinterface import Keypair

from ..src import api, db
from ..src.config import Config
from .test_db import DBTestCase

mock_config_: SimpleNamespace = SimpleNamespace(
    DISCORD_TOKEN = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-', k=59)),
    CURRENCY = r'tao|t|tau|Tao|Tau|𝜏',
    PROMPT = '!tip',
    BOT_ID = ''.join(random.choices([str(x) for x in range(0,9)], k=18)),
    COLDKEY_SECRET=Fernet.generate_key(),
    MONGO_URI="mongodb://taotip:pass_prod@mongodb:27017/prod?retryWrites=true&w=majority",
    MONGO_URI_TEST="mongodb://taotip:pass_test@mongodb:27017/test?retryWrites=true&w=majority",
    BAL_PROMPT="!balance|!bal",
    DEP_PROMPT=f"!deposit",
    WIT_PROMPT=f"!withdraw (5([A-z]|[0-9])+)\s+([1-9][0-9]*|0)(\.|\.[0-9]+)?\s*(<currency>|)?",
    HELP_PROMPT="!help|!h",
    MAINTAINER="@#",
    DEP_ACTIVE_TIME=600.0, # seconds
    DEPOSIT_INTERVAL=24.0, # seconds
    CHECK_ALL_INTERVAL=300.0, # seconds
    SUBTENSOR_ENDPOINT="fakeSubtensorAddr",
    TESTING=True,
    NUM_DEPOSIT_ADDRESSES=10,
    HELP_STR="To get your balance, type: `!balance` or `!bal`\n" + \
            "To deposit tao, type: `!deposit <amount>`\n" + \
            "To withdraw your tao, type: `!withdraw <address> <amount>`\n" + \
            f"For help, type: `!h` or `!help` or contact <maintainer>\n"
)
mock_config_.HELP_STR = mock_config_.HELP_STR.replace('<maintainer>', mock_config_.MAINTAINER)
mock_config_.WIT_PROMPT = mock_config_.WIT_PROMPT.replace('<currency>', mock_config_.CURRENCY)

mock_config = Config(mock_config_)

class TestDeposit(DBTestCase):
    """
    Test depositing funds while mocking the blockchain. 
    Tests DB functions and some API functions.
    """
    _api: api.API
    _db: db.Database

    async def test_deposit_with_zero_balance(self):
        # Create new user with zero balance
        user: int = random.randint(0, 1000000)
        amount_: float = random.random() * 1000 + 2.0
        amount_ = round(amount_, 6)
        amount: bittensor.Balance = bittensor.Balance.from_float(amount_)
        # Insert balance doc into db, with 0 balance
        self._db.db.balances.insert_one({
            'discord_user': user,
            'balance': 0
        })

        # Form transaction
        transaction: db.Transaction = db.Transaction(
            user=user,
            amount=amount.tao
        )

        # Deposit funds
        new_balance: float = await transaction.deposit(self._db)
        # Check balance
        balance: bittensor.Balance = await self._db.check_balance(user)
        self.assertEqual(balance, amount)
        self.assertEqual(new_balance, amount.tao)
        # Check balance in db
        balance_doc: Dict = self._db.db.balances.find_one({
            'discord_user': user
        })
        self.assertEqual(balance_doc['balance'], amount.rao)
        # Check balance in db
        # Check transaction doc
        transaction_doc: db.Transaction = self._db.db.transactions.find_one({
            'user': user
        })

        self.assertIsNotNone(transaction_doc)
        self.assertEqual(transaction_doc['user'], user)
        self.assertEqual(transaction_doc['amount'], amount.rao)  

    async def test_deposit_with_nonzero_balance(self):
        # Create new user with nonzero balance
        user: int = random.randint(0, 1000000)
        user_bal_: float = random.random() * 1000 + 2.0
        user_bal: bittensor.Balance = bittensor.Balance.from_float(user_bal_)
        amount_: float = random.random() * 1000 + 2.0
        amount: bittensor.Balance = bittensor.Balance.from_float(amount_)
        expected_bal = user_bal + amount
        # Insert balance doc into db, with 0 balance
        self._db.db.balances.insert_one({
            'discord_user': user,
            'balance': user_bal.rao
        })

        # Form transaction
        transaction: db.Transaction = db.Transaction(
            user=user,
            amount=amount.tao
        )

        # Deposit funds
        new_balance: float = await transaction.deposit(self._db)
        # Check balance
        balance: bittensor.Balance = await self._db.check_balance(user)
        self.assertEqual(balance, expected_bal)
        self.assertEqual(new_balance, expected_bal.tao)
        # Check balance in db
        balance_doc: Dict = self._db.db.balances.find_one({
            'discord_user': user
        })
        self.assertEqual(balance_doc['balance'], expected_bal.rao)
        # Check balance in db
        # Check transaction doc
        transaction_doc: db.Transaction = self._db.db.transactions.find_one({
            'user': user
        })

        self.assertIsNotNone(transaction_doc)
        self.assertEqual(transaction_doc['user'], user)
        self.assertEqual(transaction_doc['amount'], amount.rao)

    async def test_deposit_with_no_balance_doc(self):
        # New user would have no balance doc in db
        # Create new user with zero balance
        user: int = random.randint(0, 1000000)
        amount_: float = random.random() * 1000 + 2.0
        amount_ = round(amount_, 6)
        amount: bittensor.Balance = bittensor.Balance.from_float(amount_)

        # No balance doc in db

        # Form transaction
        transaction: db.Transaction = db.Transaction(
            user=user,
            amount=amount.tao
        )

        # Deposit funds
        new_balance: float = await transaction.deposit(self._db)
        # Check balance
        balance: bittensor.Balance = await self._db.check_balance(user)
        self.assertEqual(balance, amount)
        self.assertEqual(new_balance, amount.tao)
        # Check balance in db
        balance_doc: Dict = self._db.db.balances.find_one({
            'discord_user': user
        })
        self.assertEqual(balance_doc['balance'], amount.rao)
        # Check balance in db
        # Check transaction doc
        transaction_doc: db.Transaction = self._db.db.transactions.find_one({
            'user': user
        })

        self.assertIsNotNone(transaction_doc)
        self.assertEqual(transaction_doc['user'], user)
        self.assertEqual(transaction_doc['amount'], amount.rao)  

    def test_deposit_outside_expiry(self):
        # TODO: test depositing an amount after the expiry has ended
        ## Test more than one deposit after the expiry
        self.assert_(False)

    def test_deposit_with_expiry(self):
        # TODO: test depositing an amount before the expiry has ended
        ## Test more than one deposit during the time
        self.assert_(False)

    def test_deposit_no_addresses(self):
        # TODO: test depositing an amount with no deposit addresses in db
        self.assert_(False)

    async def test_check_for_deposits(self):
        key_bytes: bytes = Fernet.generate_key()
        # Check deposits with no deposits
        deposits: List[db.Transaction] = await self._api.check_for_deposits(self._db)
        self.assertEqual(deposits, [])

        # Create 3 addresses
        addresses: List[str] = []
        new_balances: Dict[str, bittensor.Balance] = {}
        for _ in range(3):
            addresses.append(await self._db.create_new_address(key_bytes))
            # Update address doc in db, with 0 balance
            self._db.db.addresses.update_one({
                'address': addresses[-1]
            }, {
                '$set': {
                    'balance': 0
                }
            })
            new_balances[addresses[-1]] = bittensor.Balance.from_float(random.random() * 1000 + 2.0)
        
        # Check deposits with no deposits
        deposits: List[db.Transaction] = await self._api.check_for_deposits(self._db)
        self.assertEqual(deposits, [])
    
        def mock_get_balance(address: str) -> bittensor.Balance:
            return new_balances[address]

        with patch('bittensor.Subtensor.get_balance', side_effect=mock_get_balance):
            # Simulate deposits
            users = [
                random.randint(0, 1000000),
                random.randint(0, 1000000),
                random.randint(0, 1000000)
            ]
            addrs_for_users: Dict[int, str] = {}
            for user in users:
                transaction: db.Transaction = db.Transaction(
                    user=user,
                    amount=new_balances[addresses[0]].tao
                )
                addr_for_user: str = await self._db.get_deposit_addr(transaction, mock_config)
                self.assertIsNotNone(addr_for_user)
                addrs_for_users[user] = addr_for_user

            # Check deposits
            deposits: List[db.Transaction] = await self._api.check_for_deposits(self._db)
            for deposit in deposits:
                self.assertIn(deposit.user, users)      
                addr_: str = addrs_for_users[deposit.user]          
                self.assertEqual(deposit.amount, new_balances[addr_].tao)

    def test_check_for_deposits_with_no_addresses(self):
        # TODO: test checking for deposits with no addresses in db
        self.assert_(False)

    def test_check_for_deposits_with_no_deposits(self):
        # TODO: test checking for deposits with no deposits made
        self.assert_(False)

    async def test_get_deposit_addresses(self):
        key_bytes: bytes = Fernet.generate_key()
        # Create a few new addresess
        addresses: Set[str] = set()
        for _ in range(0, 10):
            addr: str = await self._db.create_new_address(key_bytes)
            addresses.add(addr)

        # Get addresses
        ## Each address should be in the set
        ## Only one address per unique user
        seen_addr: Set[str] = set()
        users = set()
        for _ in range(0, 10):
            # Create new user
            user: int = random.randint(0, 1000000)
            while user in users:
                user = random.randint(0, 1000000)
            users.add(user)

            # Form transaction
            transaction: db.Transaction = db.Transaction(
                user=user,
                amount=0
            )
            deposit_addr: Set[str] = await self._db.get_deposit_addr(transaction, mock_config)
            seen_addr.add(deposit_addr)

        self.assertEqual(seen_addr, addresses)

class TestWithdraw(DBTestCase):
    """ Test withdrawing funds while mocking the blockchain. 
    Tests DB functions and some API functions.
    """

    _api: api.API
    _db: db.Database

    async def test_withdraw_with_zero_balance(self):
        user: int = random.randint(0, 1000000)
        # Insert balance doc into db, with 0 balance
        self._db.db.balances.insert_one({
            'discord_user': user,
            'balance': 0
        })

        # Attempt to withdraw
        amount: float = random.random() * 10000 + 2
        coldkeyadd: str = '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY'
        key_bytes: bytes = Fernet.generate_key() # doens't matter because it should stop before it gets here
        ## Create Transaction
        transaction: db.Transaction = db.Transaction(str(user), amount)
        with self.assertRaises(db.WithdrawException):
            await transaction.withdraw(self._db, coldkeyadd, key_bytes)
        
        # Check that balance is still 0
        balance: bittensor.Balance = await self._db.check_balance(user)
        self.assertEqual(balance.tao, 0)

    async def test_withdraw_with_nonzero_balance_not_enough(self):   
        user: int = random.randint(0, 1000000)
        amount: float = random.random() * 10000 + 2
        key_bytes: bytes = Fernet.generate_key() # doens't matter because it should stop before it gets here 

        # More than transaction fee, but not enough to cover transaction
        bal: bittensor.Balance = bittensor.Balance.from_float(1.0)
        # Insert balance doc into db, with balance
        self._db.db.balances.insert_one({
            'discord_user': user,
            'balance': bal.rao
        })

        # Check that balance is in db
        balance: bittensor.Balance = await self._db.check_balance(user)
        self.assertEqual(balance, bal)

        # Attempt to withdraw        
        coldkeyadd: str = '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY'
        
        ## Create Transaction
        transaction: db.Transaction = db.Transaction(str(user), amount)
        with self.assertRaises(db.WithdrawException):
            await transaction.withdraw(self._db, coldkeyadd, key_bytes)
        
        # Check that balance is unchanged
        balance: bittensor.Balance = await self._db.check_balance(user)
        self.assertEqual(balance, bal)

    async def test_withdraw_with_no_balance_doc(self):
        user: int = random.randint(0, 1000000)
        # Insert address doc into db        
        key_bytes: bytes = Fernet.generate_key() # doens't matter because it should stop before it gets here
        ## Create tip bot address
        addr: str = await self._db.create_new_address(key_bytes) 
        ## Amount to withdraw
        amount: float = random.random() * 10000 + 2
        ## Tip bot address balance
        addr_bal: float = bittensor.Balance.from_float(amount + 20.0).rao
        ## Make tip bot address doc have positive balance
        self._db.db.addresses.update_one({
            'address': addr,
        }, {
            '$set': {
                'balance': addr_bal
            }
        })      

        # No balance doc in db

        # Attempt to withdraw        
        ## User destination address
        coldkeyadd: str = '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY'
        ## Create Transaction
        transaction: db.Transaction = db.Transaction(str(user), amount)
        with self.assertRaises(db.WithdrawException):
            await transaction.withdraw(self._db, coldkeyadd, key_bytes)
        
        # Check that balance is still not in db
        user_db: Dict = self._db.db.balances.find_one({'discord_user': user})
        self.assertIsNone(user_db)

        # Check that tip bot addr balance is unchanged
        addr_db: Dict = self._db.db.addresses.find_one({'address': addr})
        self.assertEqual(addr_db['balance'], addr_bal)

    async def test_withdraw_no_addresses(self):
        user: int = random.randint(0, 1000000)
        bal: bittensor.Balance = bittensor.Balance.from_float(random.random() * 10000 + 2.0)
        # Insert balance doc into db, with positive balance
        self._db.db.balances.insert_one({
            'discord_user': str(user),
            'balance': bal.rao
        })

        # No addresses in db

        # Attempt to withdraw
        amount: float = bal.tao - 1.0 # fee should be below 1.0 tao
        coldkeyadd: str = '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY'
        key_bytes: bytes = Fernet.generate_key() # doens't matter because it should stop before it gets here
        ## Create Transaction
        transaction: db.Transaction = db.Transaction(str(user), amount)

        # Should fail
        with self.assertRaises(db.WithdrawException) as e:
            await transaction.withdraw(self._db, coldkeyadd, key_bytes)
        
        # Verify right exception
        self.assertIn(e.exception.reason, 'No withdraw addresses found')
        
        # Check that balance is unchanged
        balance: bittensor.Balance = await self._db.check_balance(str(user))
        self.assertEqual(balance, bal)

    async def test_sign_transaction(self):
        key_bytes: bytes = Fernet.generate_key()
        # Create address on db 
        addr: str = await self._db.create_new_address(key_bytes)        
        amount: float = random.random() * 10000 + 2.0
        addr_bal: bittensor.Balance = bittensor.Balance.from_float(amount + 20.0)
        # Increase addr balance above amount to withdraw
        self._db.db.addresses.update_one({
            'address': addr,
        }, {
            '$set': {
                'balance': addr_bal.rao
            }
        })

        # Setup mock balance check
        with patch('bittensor.Subtensor.get_balance', return_value=addr_bal):
            # Create transaction
            transaction: Dict = {
                'coldkeyadd': addr,
                'amount': amount,
                'dest': '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY',
            }
            transaction: db.Transaction = await self._api.create_transaction(transaction)

            signed_transaction: Dict = await self._api.sign_transaction(self._db, transaction, addr, key=key_bytes)
            """{
                "signature": "0x" + signature.hex(),
                "call": transaction["call"],
                "coldkeyadd": addr,
                "signature_payload_hex": signature_payload_hex
            }"""
            key: Keypair = Keypair(ss58_address=addr)
            self.assertTrue(key.verify(
                ScaleBytes(signed_transaction['signature_payload_hex']),
                signed_transaction['signature']
            ))
            self.assertEqual(signed_transaction['coldkeyadd'], addr)

    async def test_withdraw_success(self):
        user: int = random.randint(0, 1000000)
        amount: float = random.random() * 10000 + 2
        key_bytes: bytes = Fernet.generate_key()
        user_bal: bittensor.Balance = bittensor.Balance.from_float(amount + 20.0)

        # Insert balance doc into db, with balance >= amount + fee
        self._db.db.balances.insert_one({
            'discord_user': user,
            'balance': user_bal.rao
        })

        # Check that balance is in db
        balance: bittensor.Balance = await self._db.check_balance(user)
        self.assertEqual(balance, user_bal)

        # Create address on db
        addr: str = await self._db.create_new_address(key_bytes)
        # Make the address have enough balance
        addr_balance: bittensor.Balance = bittensor.Balance.from_float(amount + 20.0)
        self._db.db.addresses.update_one({
            'address': addr,
        }, {
            '$set': {
                'balance': addr_balance.rao
            }
        })

        # Check addr balance is in db
        addr_db: Dict = self._db.db.addresses.find_one({'address': addr})
        self.assertEqual(addr_db['balance'], addr_balance.rao)

        # Check addr is not locked
        self.assertFalse(addr_db['locked'])

        # Expected addr_balance after withdrawal        
        expected_addr_balance: bittensor.Balance = addr_balance - bittensor.Balance.from_float(-(await self._api.get_withdraw_fee()) - amount)

        # Setup mock balance check
        ## Check for get withdraw addr, check for send, check for get after send
        with patch('bittensor.Subtensor.get_balance', side_effect=[
            addr_balance, addr_balance, expected_addr_balance
        ]):       
            # Setup mock send transaction
            mock_response: SimpleNamespace = SimpleNamespace(
                process_events=MagicMock(return_value=None),
                is_success=True
            )
            with patch('substrateinterface.SubstrateInterface.submit_extrinsic', MagicMock(return_value=mock_response)):
                # Attempt to withdraw
                coldkeyadd: str = '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY'
                ## Create Transaction
                transaction: db.Transaction = db.Transaction(user, amount)
                new_balance: float = await transaction.withdraw(self._db, coldkeyadd, key_bytes)
                new_balance = bittensor.Balance.from_float(new_balance)
                # Check that the balance is correct
                expected_balance: bittensor.Balance = user_bal - bittensor.Balance.from_float((await self._api.get_withdraw_fee()) + amount)
                self.assertEqual(new_balance, expected_balance)

                # Check that balance is in db
                balance: bittensor.Balance = await self._db.check_balance(user)
                self.assertEqual(balance, expected_balance)

                # Check that addr balance is in db
                addr_db: Dict = self._db.db.addresses.find_one({'address': addr})
                self.assertEqual(addr_db['balance'], expected_addr_balance.rao)
