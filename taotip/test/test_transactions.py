import random
from types import SimpleNamespace
from typing import Dict, List, Set
from unittest.mock import MagicMock, patch

import bittensor
from cryptography.fernet import Fernet
from more_itertools import side_effect
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

    async def test_get_deposit_address(self):
        key_bytes: bytes = Fernet.generate_key()
        user: str = str(random.randint(0, 1000000))
        # Create a new address for the user
        new_address: str = await self._db.create_new_address(key_bytes, user)

        # Form transaction
        transaction: db.Transaction = db.Transaction(
            user,
            bittensor.Balance.from_float(random.random() * 10000 + 2.0).tao
        )
        # Get address for user
        address: str = await self._db.get_deposit_addr(transaction)
        self.assertEqual(address, new_address)

    async def test_get_deposit_address_not_in_db(self):
        key_bytes: bytes = Fernet.generate_key()
        user: str = str(random.randint(0, 1000000))
        # User is not yet in DB

        # Form transaction
        transaction: db.Transaction = db.Transaction(
            user,
            bittensor.Balance.from_float(random.random() * 10000 + 2.0).tao
        )
        # Get address for user
        address: str = await self._db.get_deposit_addr(transaction, key_bytes)
        self.assertIsNotNone(address)
        

class TestWithdraw(DBTestCase):
    """ Test withdrawing funds while mocking the blockchain. 
    Tests DB functions and some API functions.
    """

    _api: api.API
    _db: db.Database

    async def test_withdraw_with_zero_balance(self):
        key_bytes: bytes = Fernet.generate_key()
        user: int = random.randint(0, 1000000)

        # Create a new address for the user
        new_address: str = await self._db.create_new_address(key_bytes, user)

        # User now in db. Should have 0 balance on chain

        # Attempt to withdraw
        amount: float = random.random() * 10000 + 2
        coldkeyadd: str = '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY'
        ## Create Transaction
        transaction: db.Transaction = db.Transaction(str(user), amount)
        with self.assertRaises(db.WithdrawException):
            with patch.object(self._api, 'get_wallet_balance', return_value=bittensor.Balance.from_rao(0)): # 0 balance
                await transaction.withdraw(self._db, coldkeyadd, key_bytes)
        
        # Check that balance is still 0
        balance: bittensor.Balance = await self._db.check_balance(user)
        self.assertEqual(balance.tao, 0)

    async def test_withdraw_with_nonzero_balance_not_enough(self):   
        key_bytes: bytes = Fernet.generate_key()
        user: int = random.randint(0, 1000000)

        
        amount: float = random.random() * 10000 + 2
        key_bytes: bytes = Fernet.generate_key() 

        # More than transaction fee, but not enough to cover transaction
        bal: bittensor.Balance = bittensor.Balance.from_float(1.0)
        
        # Create a new address for the user
        new_address: str = await self._db.create_new_address(key_bytes, user)

        # Mock balance check on chain
        with patch.object(self._api, 'get_wallet_balance', return_value=bal):
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

    async def test_withdraw_with_no_user_address(self):
        user: int = random.randint(0, 1000000)
        # Insert address doc into db        
        key_bytes: bytes = Fernet.generate_key() # doesn't matter because it should stop before it gets here
        
        # User is not in db

        ## Amount to withdraw
        amount: float = random.random() * 10000 + 2 

        # Check that balance is 0; should be because user is not in db
        balance: bittensor.Balance = await self._db.check_balance(user)
        self.assertEqual(balance.tao, 0)

        # Attempt to withdraw        
        ## User destination address
        coldkeyadd: str = '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY'
        ## Create Transaction
        transaction: db.Transaction = db.Transaction(str(user), amount)
        with self.assertRaises(db.WithdrawException):
            await transaction.withdraw(self._db, coldkeyadd, key_bytes)
        
        # Check that balance is still 0
        balance: bittensor.Balance = await self._db.check_balance(user)
        self.assertEqual(balance.tao, 0)

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
        
        coldkeyadd: str = '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY'

        # Create a new address for the user
        new_address: str = await self._db.create_new_address(key_bytes, user)

        ## Create Transaction
        transaction: db.Transaction = db.Transaction(user, amount)
        api_transaction = {
            "coldkeyadd": new_address,
            "dest": coldkeyadd,
            "amount": amount # in tao for this addr
        }

        # User now in db. Should have 0 balance on chain
        # Expected user_bal after withdrawal        
        expected_balance: bittensor.Balance = user_bal - (await self._api.get_withdraw_fee(api_transaction)) - bittensor.Balance.from_float(amount)

        ## Mock balance check on chain
        with patch.object(self._api, 'get_wallet_balance', side_effect=[
            user_bal, user_bal, user_bal, expected_balance, expected_balance
        ]):
            # Check balance using mock chain
            balance: bittensor.Balance = await self._db.check_balance(user)
            self.assertEqual(balance, user_bal)

            # Check new address is in db
            addr_db: Dict = self._db.db.addresses.find_one({'address': new_address})
            self.assertEqual(addr_db['user'], user)

            # Setup mock send transaction
            mock_response: SimpleNamespace = SimpleNamespace(
                process_events=MagicMock(return_value=None),
                is_success=True
            )
            with patch('substrateinterface.SubstrateInterface.submit_extrinsic', MagicMock(return_value=mock_response)):
                # Attempt to withdraw

                new_balance: float = await transaction.withdraw(self._db, coldkeyadd, key_bytes)
                new_balance = bittensor.Balance.from_float(new_balance)
                
                # Check that new balance on chain matches expected balance
                self.assertEqual(new_balance, expected_balance)

                # Check that balance on chain matches expected balance
                balance: bittensor.Balance = await self._db.check_balance(user)
                self.assertEqual(balance, expected_balance)
