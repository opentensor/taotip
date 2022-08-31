import random
from types import SimpleNamespace
from typing import Dict
from unittest.mock import MagicMock,patch
from callee import Contains

import bittensor
from cryptography.fernet import Fernet

from taotip.src import api, db
from taotip.test.test_db import DBTestCase

"""
Testing all the chain functions in the api.py file.
Mocks the blockchain and the database.
"""
class TestChainWithMock(DBTestCase):
    _api: api.API
    _db: db.Database
    
    async def test_send_transaction(self):
        mock_response: SimpleNamespace = SimpleNamespace(
                process_events=MagicMock(return_value=None),
                is_success=True
        )
        amount: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 2)
        with patch('substrateinterface.SubstrateInterface.query', return_value=SimpleNamespace(
            value = {
                'data': {
                    'free': amount.rao,
                }
            }
        )):
            with patch('substrateinterface.SubstrateInterface.submit_extrinsic', return_value=mock_response):
                key_bytes = Fernet.generate_key()
                addr: str = await self._db.create_new_address(key_bytes) 
                dest_addr: db.Address = self._api.create_address(Fernet.generate_key())
                
                api_transaction = {
                    "coldkeyadd": addr,
                    "dest": dest_addr.address,
                    "amount": amount.tao # in tao for this addr
                }
                _transaction = await self._api.create_transaction(api_transaction)
                _signed_transaction = await self._api.sign_transaction(self._db, _transaction, addr, key_bytes)
                result = self._api.send_transaction(_signed_transaction)
                self.assertEqual(result['message'], "Transaction sent")
                self.assertEqual(result['response'], mock_response)
            
    def test_check_balance(self):
        key_bytes = Fernet.generate_key()
        addr: db.Address = self._api.create_address(key_bytes)
        bal: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 2)
        with patch('substrateinterface.SubstrateInterface.query', return_value=SimpleNamespace(
            value = {
                'data': {
                    'free': bal.rao,
                }
            }
        )):
            self.assertEqual(self._api.get_wallet_balance(addr.address), bal)

    def test_check_balance_with_invalid_address(self):
        key_bytes = Fernet.generate_key()
        bal: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 2)
        with patch('substrateinterface.SubstrateInterface.query', return_value=SimpleNamespace(
            value = {
                'data': {
                    'free': bal.rao,
                }
            }
        )):
            with self.assertRaises(Exception) as e:
                self._api.get_wallet_balance(
                    coldkeyadd="totallyinvalidaddress"
                )
            self.assertEqual("invalid coldkey address coldkeyadd", str(e.exception))

    async def test_get_fee(self):
        key_bytes = Fernet.generate_key()
        addr: str = await self._db.create_new_address(key_bytes) 
        dest_addr: db.Address = self._api.create_address(Fernet.generate_key())
        amount: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 2)
        
        api_transaction = {
            "coldkeyadd": addr,
            "dest": dest_addr.address,
            "amount": amount.tao # in tao for this addr
        }
        _, _, paymentinfo = self._api.init_transaction(
            addr, dest_addr.address, amount
        )
        fee: bittensor.Balance = await self._api.get_fee(addr, dest_addr.address, amount)

        self.assertAlmostEqual(paymentinfo['partialFee'], fee.rao)

class TestChainWithoutMock(DBTestCase):
    _api: api.API
    _db: db.Database
    
    async def test_send_transaction_fail(self):
        amount: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 2)
        
        key_bytes = Fernet.generate_key()
        addr: str = await self._db.create_new_address(key_bytes) 
        dest_addr: db.Address = self._api.create_address(Fernet.generate_key())
        
        call, signature_payload, paymentInfo = self._api.init_transaction(addr, dest_addr.address, amount)
        _transaction = {
                'message': 'Signature Payload created',
                'signature_payload_hex': signature_payload.to_hex(),
                'paymentInfo': paymentInfo,
                'call': call,
        }
        _signed_transaction = await self._api.sign_transaction(self._db, _transaction, addr, key_bytes)
        
        result = self._api.send_transaction(_signed_transaction)
        self.assertIsNone(result) # failure to send because of balance

    async def test_send_transaction_fail_no_balance(self):
        amount: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 2)
        
        key_bytes = Fernet.generate_key()
        addr: str = await self._db.create_new_address(key_bytes) 
        dest_addr: db.Address = self._api.create_address(Fernet.generate_key())


        api_transaction = {
            "coldkeyadd": addr,
            "dest": dest_addr.address,
            "amount": amount.tao # in tao for this addr
        }

        with self.assertRaises(Exception) as e:
            _transaction = await self._api.create_transaction(api_transaction)
        self.assertAlmostEqual(str(e.exception), "insufficient balance") # failure to create because of balance check
            
    def test_check_balance(self):
        key_bytes = Fernet.generate_key()
        # Create new address
        addr: db.Address = self._api.create_address(key_bytes)
        # Get balance; New address should have balance of 0
        self.assertEqual(self._api.get_wallet_balance(addr.address), bittensor.Balance.from_rao(0))

    def test_check_balance_with_invalid_address(self):
        with self.assertRaises(Exception) as e:
            self._api.get_wallet_balance(
                coldkeyadd="totallyinvalidaddress"
            )
        self.assertEqual("invalid coldkey address coldkeyadd", str(e.exception))

    async def test_get_fee(self):
        key_bytes = Fernet.generate_key()
        addr: str = await self._db.create_new_address(key_bytes) 
        dest_addr: db.Address = self._api.create_address(Fernet.generate_key())
        amount: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 2)

        _, _, paymentinfo = self._api.init_transaction(
            addr, dest_addr.address, amount
        )
        fee: bittensor.Balance = await self._api.get_fee(addr, dest_addr.address, amount)

        self.assertAlmostEqual(paymentinfo['partialFee'], fee.rao)
