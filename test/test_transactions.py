import random
from types import SimpleNamespace
from typing import Dict
from unittest.mock import MagicMock

import bittensor
from cryptography.fernet import Fernet
from scalecodec.base import ScaleBytes
from substrateinterface import Keypair

from ..src import api, db
from .test_db import DBTestCase

"""
Test depositing funds while mocking the blockchain. 
Tests DB functions and some API functions.
"""
class TestDeposit(DBTestCase):
    def test_deposit_with_zero_balance(self):
        # Create new user with zero balance
        pass

    def test_deposit_with_nonzero_balance(self):
        pass

    def test_deposit_with_no_balance_doc(self):
        # New user would have no balance doc in db
        pass

    def test_deposit_outside_expiry(self):
        pass

    def test_deposit_with_expiry(self):
        pass

    def test_deposit_no_addresses(self):
        pass

    def test_check_for_deposits(self):
        pass

    def test_check_for_deposits_with_no_addresses(self):
        pass

    def test_check_for_deposits_with_no_deposits(self):
        pass

"""
Test withdrawing funds while mocking the blockchain. 
Tests DB functions and some API functions.
"""
class TestWithdraw(DBTestCase):
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
        balance: float = await self._db.check_balance(user)
        self.assertEqual(balance, 0)

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
        balance: float = await self._db.check_balance(user)
        self.assertEqual(balance, bal.tao)

        # Attempt to withdraw        
        coldkeyadd: str = '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY'
        
        ## Create Transaction
        transaction: db.Transaction = db.Transaction(str(user), amount)
        with self.assertRaises(db.WithdrawException):
            await transaction.withdraw(self._db, coldkeyadd, key_bytes)
        
        # Check that balance is unchanged
        balance: float = await self._db.check_balance(user)
        self.assertEqual(balance, bal.tao)

    async def test_withdraw_with_no_balance_doc(self):
        user: int = random.randint(0, 1000000)
        # Insert address doc into db        
        key_bytes: bytes = Fernet.generate_key() # doens't matter because it should stop before it gets here
        ## Create tip bot address
        addr: str = await self._db.create_new_addr(key_bytes) 
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
        balance: float = await self._db.check_balance(str(user))
        self.assertEqual(balance, bal.tao)

    async def test_sign_transaction(self):
        key_bytes: bytes = Fernet.generate_key()
        # Create address on db 
        addr: str = await self._db.create_new_addr(key_bytes)        
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
        self._api.subtensor.get_balance = MagicMock(return_value=addr_bal)

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
        balance: float = await self._db.check_balance(user)
        self.assertEqual(balance, user_bal.tao)

        # Create address on db
        addr: str = await self._db.create_new_addr(key_bytes)
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
        self._api.subtensor.get_balance = MagicMock(side_effect=[
            addr_balance, addr_balance, expected_addr_balance
        ])
        # Setup mock send transaction
        mock_response: SimpleNamespace = SimpleNamespace(
            process_events=MagicMock(return_value=None),
            is_success=True
        )
        self._api.subtensor.substrate.submit_extrinsic = MagicMock(return_value=mock_response)

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
        balance: float = await self._db.check_balance(user)
        self.assertEqual(balance, expected_balance.tao)

        # Check that addr balance is in db
        addr_db: Dict = self._db.db.addresses.find_one({'address': addr})
        self.assertEqual(addr_db['balance'], expected_addr_balance.rao)
