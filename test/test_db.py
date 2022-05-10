import random
from unittest.mock import MagicMock
import bittensor
import mongomock
import unittest
import asyncio
from cryptography.fernet import Fernet
from more_itertools import side_effect
from ..src import api, db, parse
from ..src.db import Address, Tip

class DBTestCase(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls._api: api.API = api.API(testing=True)
        cls._db: db.Database = db.Database(mongomock.MongoClient(), cls._api, True)

    def tearDown(self) -> None:
        self._db.db.addresses.drop()
        self._db.db.transactions.drop()
        self._db.db.balances.drop()
        self._db.db.tips.drop()

class TestAddressEncrypt(DBTestCase):
    async def test_encrypt(self):
        key_bytes = Fernet.generate_key()
        addr: Address = self._api.create_address(key_bytes)
        mnemonic_to_bytes: bytes = bytes(addr.mnemonic, 'utf-8')
        enc_mnemonic: bytes = addr.get_encrypted_mnemonic()
        self.assertNotEqual(mnemonic_to_bytes.hex(), enc_mnemonic.hex())

    async def test_decrypt(self):
        key_bytes = Fernet.generate_key()
        addr: Address = self._api.create_address(key_bytes)
        enc_mnemonic: bytes = addr.get_encrypted_mnemonic()

        dec_addr: Address = Address(addr.address, enc_mnemonic, key_bytes, decrypt=True)
        self.assertEqual(dec_addr.mnemonic, addr.mnemonic)

    async def test_decrypt_wrong_key(self):
        key_bytes = Fernet.generate_key()
        addr: Address = self._api.create_address(key_bytes)
        enc_mnemonic: bytes = addr.get_encrypted_mnemonic()
        
        wrong_key_bytes = Fernet.generate_key()
        # Raises error if wrong key
        self.assertRaises(Exception, Address, addr.address, enc_mnemonic, wrong_key_bytes, decrypt=True)

    async def test_get_encrypted_mnemonic_from_db(self):
        key_bytes = Fernet.generate_key()
        addr: 'db.Address' = self._api.create_address(key_bytes)
        # Put address in db
        self._db.db.addresses.insert_one({
            'address': addr.address,
            'mnemonic': addr.get_encrypted_mnemonic(),
            'locked': False
        })

        # Get address from db, should be decrypted
        addr_from_db = self._db.get_address(addr.address, key=key_bytes)
        keypair = bittensor.Keypair.create_from_mnemonic(addr_from_db.mnemonic)
        self.assertEqual(addr.address, keypair.ss58_address)


    async def test_get_encrypted_mnemonic_from_db_wrong_key(self):
        key_bytes = Fernet.generate_key()
        addr: 'db.Address' = self._api.create_address(key_bytes)
        # Put address in db
        self._db.db.addresses.insert_one({
            'address': addr.address,
            'mnemonic': addr.get_encrypted_mnemonic(),
            'locked': False
        })

        wrong_key_bytes = Fernet.generate_key() 
        # Get address from db, should be decrypted
        addr_from_db = self._db.get_address(addr.address, key=wrong_key_bytes)
        self.assertIsNone(addr_from_db) # Should be None because wrong key

    async def test_create_address_get_encrypted_mnemonic_from_db(self):
        key_bytes = Fernet.generate_key()
        addr: str = await self._db.create_new_address(key_bytes)

        # Get address from db, should be encrypted
        encrypted_addr = self._db.db.addresses.find_one({'address': addr})
        self.assertIsNotNone(encrypted_addr)
        self.assertIsNotNone(encrypted_addr['mnemonic'])
        self.assertIsInstance(encrypted_addr['mnemonic'], bytes)

        encrypted_mnemonic = encrypted_addr['mnemonic']
        
        # Get address from db, should be decrypted
        addr_from_db = self._db.get_address(addr, key=key_bytes)
        self.assertNotEqual(bytes(addr_from_db.mnemonic, 'utf-8'), encrypted_mnemonic)

        # Decrypt mnemonic
        dec_addr: Address = Address(addr, encrypted_mnemonic, key_bytes, decrypt=True)
        self.assertEqual(dec_addr.mnemonic, addr_from_db.mnemonic)

    async def test_decrypt_on_db(self):
        key_bytes = Fernet.generate_key()
        addr: 'db.Address' = self._api.create_address(key_bytes)
        self._db.db.addresses.insert_one({
            'address': addr.address,
            'mnemonic': addr.mnemonic,
            'encrypted_mnemonic': addr.get_encrypted_mnemonic()
        })
        self.assertEqual(self._db.db.addresses.find_one({'address': addr.address})['mnemonic'], addr.mnemonic)        

class TestAddressCreate(DBTestCase):
    async def test_create_address(self):
        key_bytes: bytes = Fernet.generate_key()
        addr: str = await self._db.create_new_address(key=key_bytes)
        self.assertIsNotNone(addr)
        self.assertTrue(parse.is_valid_ss58_address(addr, 42)) #bittensor ss58 format

        # Check if address is in db
        enc_address: Address = self._db.db.addresses.find_one({'address': addr})
        self.assertEqual(enc_address['address'], addr)
        # Check if mnemonic can be decrypted
        unenc_address: Address = self._db.get_address(addr, key=key_bytes)
        mnemonic: str = unenc_address.mnemonic
        self.assertIsNotNone(mnemonic)
        unenc_mnemonic: str = Address(addr, enc_address['mnemonic'], key_bytes, decrypt=True).mnemonic
        self.assertEqual(unenc_mnemonic, mnemonic)

class TestTips(DBTestCase):
    async def test_tip_create(self):
        # Create user with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount = bittensor.Balance.from_float(random.random() * 1000 + 1.0) # Random float between 1 and 1001

        tip: Tip = Tip(sender, recipient, amount)
        self.assertEqual(tip.sender, sender)
        self.assertEqual(tip.recipient, recipient)
        self.assertEqual(tip.amount, amount)

        self.assertEqual(str(tip), f'{sender} -> {recipient} ({amount.tao}) tao')

        # Insert tip in db
        await self._db.record_tip(tip)

        # Check if tip is in db
        tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
        self.assertEqual(tip_from_db['sender'], sender)
        self.assertEqual(tip_from_db['recipient'], recipient)
        self.assertEqual(
            bittensor.Balance.from_rao(tip_from_db['amount']),
            amount
        )
        ## Timestamp on mongo loses some precision
        self.assertAlmostEqual(tip_from_db['time'].timestamp(), tip.time.timestamp(), delta=0.001)

    async def test_tip_sent(self):
        key: bytes = Fernet.generate_key()
        # Create user with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 1.0) # Random float between 1 and 1001
        bal: bittensor.Balance = bittensor.Balance.from_rao(random.randint(0, 100000000000)) + amount
        # Insert user in db
        addr_str: str = await self._db.create_new_address(key, sender)

        addr_str_recipient: str = await self._db.create_new_address(key, recipient)
        
        # Mock balance check on chain
        with unittest.mock.patch.object(self._api.subtensor, 'get_balance', 
            side_effect=[bal, bal, bal, bal - amount, bal - amount]):
            # Check balance
            self.assertEqual(await self._db.check_balance(sender), bal)
            # Tip user
            tip: Tip = Tip(sender, recipient, amount)

            # Mock tip sent on chain
            with unittest.mock.patch.object(self._api.subtensor.substrate, 'submit_extrinsic', return_value=MagicMock(
                process_events=MagicMock(
                    return_value=MagicMock()
                ),
                is_success=True # Mock success
            )):
                ## Send tip
                await tip.send(self._db, key)

                # Check balance
                balance_new_expected: bittensor.Balance = bal - amount
                self.assertEqual(await self._db.check_balance(sender), balance_new_expected)    

                # Check if tip is in db
                tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
                self.assertEqual(tip_from_db['sender'], sender)
                self.assertEqual(tip_from_db['recipient'], recipient)
                self.assertEqual(
                    bittensor.Balance.from_rao(tip_from_db['amount']),
                    amount
                )
                ## Timestamp on mongo loses some precision
                self.assertAlmostEqual(tip_from_db['time'].timestamp(), tip.time.timestamp(), delta=0.001)

    async def test_tip_not_enough_balance(self):
        key: bytes = Fernet.generate_key()
        # Create sender with balance
        sender = random.randint(0, 1000000)
        recipient = sender + 1
        amount: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 2)
        bal: int = amount.rao - random.randint(1, 100)
        bal = bal if bal > 0 else 1 # Ensure balance is positive
        bal: bittensor.Balance = bittensor.Balance.from_rao(bal)

        # Insert user in db
        addr_str: str = await self._db.create_new_address(key, sender)
        
        addr_str_recipient: str = await self._db.create_new_address(key, recipient)
        
        # Mock balance check on chain
        with unittest.mock.patch.object(self._api.subtensor, 'get_balance', 
            side_effect=[bal, bal, bal, bittensor.Balance.from_rao(0)]):

            # Check balance
            self.assertEqual(await self._db.check_balance(sender), bal)
            # Tip user
            tip: Tip = Tip(sender, recipient, amount)

            # Mock tip sent on chain
            with unittest.mock.patch.object(self._api.subtensor.substrate, 'submit_extrinsic', return_value=MagicMock(
                process_events=MagicMock(
                    return_value=MagicMock()
                ),
                is_success=True # Mock success
            )):
                ## Send tip
                await tip.send(self._db, key)

                # Tip should fail

                # Check balance of sender
                balance_new_expected_sender: bittensor.Balance = bal # Balance should not change
                self.assertEqual(await self._db.check_balance(sender), balance_new_expected_sender)

                # Check balance of recipient. Should be unchanged
                balance_new_expected_rec: bittensor.Balance = bittensor.Balance.from_rao(0) # new balance should still be 0
                self.assertEqual(await self._db.check_balance(recipient), balance_new_expected_rec)    

                # Check if tip is in db
                tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
                self.assertIsNone(tip_from_db)

    async def test_tip_no_balance(self):
        key: bytes = Fernet.generate_key()
        # Create sender with balance
        sender = random.randint(0, 1000000)
        recipient = sender + 1
        amount: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 2)
        bal: bittensor.Balance = bittensor.Balance.from_rao(0) # No balance

        # Insert user in db
        addr_str: str = await self._db.create_new_address(key, sender)
        
        addr_str_recipient: str = await self._db.create_new_address(key, recipient)
        
        # Mock balance check on chain
        with unittest.mock.patch.object(self._api.subtensor, 'get_balance', 
            side_effect=[bal, bal, bal, bittensor.Balance.from_rao(0)]):

            # Check balance
            self.assertEqual(await self._db.check_balance(sender), bal)
            # Tip user
            tip: Tip = Tip(sender, recipient, amount)

            # Mock tip sent on chain
            with unittest.mock.patch.object(self._api.subtensor.substrate, 'submit_extrinsic', return_value=MagicMock(
                process_events=MagicMock(
                    return_value=MagicMock()
                ),
                is_success=True # Mock success
            )):
                ## Send tip
                await tip.send(self._db, key)

                # Tip should fail

                # Check balance of sender
                balance_new_expected_sender: bittensor.Balance = bal # Balance should not change
                self.assertEqual(await self._db.check_balance(sender), balance_new_expected_sender)

                # Check balance of recipient. Should be unchanged
                balance_new_expected_rec: bittensor.Balance = bittensor.Balance.from_rao(0) # new balance should still be 0
                self.assertEqual(await self._db.check_balance(recipient), balance_new_expected_rec)    

                # Check if tip is in db
                tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
                self.assertIsNone(tip_from_db)

    async def test_tip_no_sender_in_db(self):
        key: bytes = Fernet.generate_key()
        # Create sender with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 2)
        bal: bittensor.Balance = bittensor.Balance.from_rao(0) # No balance for non-existent sender

        # Insert recipient in db, no sender
        
        addr_str_recipient: str = await self._db.create_new_address(key, recipient)
        
        # Mock balance check on chain
        with unittest.mock.patch.object(self._api.subtensor, 'get_balance', 
            side_effect=[bal, bal, bal, bittensor.Balance.from_rao(0)]):

            # Check balance
            self.assertEqual(await self._db.check_balance(sender), bal)
            # Tip user
            tip: Tip = Tip(sender, recipient, amount)

            # Mock tip sent on chain
            with unittest.mock.patch.object(self._api.subtensor.substrate, 'submit_extrinsic', return_value=MagicMock(
                process_events=MagicMock(
                    return_value=MagicMock()
                ),
                is_success=True # Mock success
            )):
                ## Send tip
                await tip.send(self._db, key)

                # Tip should fail

                # Check balance of sender
                balance_new_expected_sender: bittensor.Balance = bal # Balance should not change
                self.assertEqual(await self._db.check_balance(sender), balance_new_expected_sender)

                # Check balance of recipient. Should be unchanged
                balance_new_expected_rec: bittensor.Balance = bittensor.Balance.from_rao(0) # new balance should still be 0
                self.assertEqual(await self._db.check_balance(recipient), balance_new_expected_rec)    

                # Check if tip is in db
                tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
                self.assertIsNone(tip_from_db)

    async def test_tip_no_recipient_in_db(self):
        key: bytes = Fernet.generate_key()
        # Create user with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount: bittensor.Balance = bittensor.Balance.from_float(random.random() * 1000 + 1.0) # Random float between 1 and 1001
        bal: bittensor.Balance = bittensor.Balance.from_rao(random.randint(0, 100000000000)) + amount
        # Insert user in db
        addr_str: str = await self._db.create_new_address(key, sender)
        
        # Recipient does not exist in db
        
        # Mock balance check on chain
        with unittest.mock.patch.object(self._api.subtensor, 'get_balance', 
            side_effect=[bal, bal, bal, bal - amount, bal - amount]):
            # Check balance
            self.assertEqual(await self._db.check_balance(sender), bal)
            # Tip user
            tip: Tip = Tip(sender, recipient, amount)

            # Mock tip sent on chain
            with unittest.mock.patch.object(self._api.subtensor.substrate, 'submit_extrinsic', return_value=MagicMock(
                process_events=MagicMock(
                    return_value=MagicMock()
                ),
                is_success=True # Mock success
            )):
                ## Send tip
                await tip.send(self._db, key)

                # Check balance
                balance_new_expected: bittensor.Balance = bal - amount
                self.assertEqual(await self._db.check_balance(sender), balance_new_expected)    

                # Check if tip is in db
                tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
                self.assertEqual(tip_from_db['sender'], sender)
                self.assertEqual(tip_from_db['recipient'], recipient)
                self.assertEqual(
                    bittensor.Balance.from_rao(tip_from_db['amount']),
                    amount
                )
                ## Timestamp on mongo loses some precision
                self.assertAlmostEqual(tip_from_db['time'].timestamp(), tip.time.timestamp(), delta=0.001)
