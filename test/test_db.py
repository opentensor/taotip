import imp
import random
import bittensor
import mongomock
import unittest
import asyncio
import pytest
from cryptography.fernet import Fernet
from ..src import api, db, parse
from ..src.db import Address

class DBTestCase(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls._api = api.API(testing=True)
        cls._db = db.Database(mongomock.MongoClient(), cls._api, True)

    def tearDown(self) -> None:
        self._db.db.addresses.drop()
        self._db.db.transactions.drop()
        self._db.db.accounts.drop()
        self._db.db.balances.drop()
        self._db.db.tips.drop()
        
class TestAddressLock(DBTestCase):
    async def test_address_lock_already_locked(self):
        # Create locked address in db
        self._db.db.addresses.insert_one({
            'address': '5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx',
            'locked': True
        })

        # Check if can acquire lock
        self.assertFalse(await self._db.lock_addr('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx'))

    async def test_address_lock_not_locked(self):
        # Create unlocked address in db   
        self._db.db.addresses.insert_one({
            'address': '5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx',
            'locked': False
        })

        # Check if can acquire lock
        self.assertTrue(await self._db.lock_addr('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx'))

    async def test_address_lock_locked_during_test(self):
        # Create unlocked address in db
        self._db.db.addresses.insert_one({
            'address': '5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx',
            'locked': False
        })

        # Should acquire lock
        self.assertTrue(await self._db.lock_addr('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx'))

        # Should not acquire lock
        self.assertFalse(await self._db.lock_addr('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx'))

    async def test_address_lock_locked_with_expiry(self):
        # Create locked address in db
        self._db.db.addresses.insert_one({
            'address': '5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx',
            'locked': True
        })

        # Set lock expiry
        ## 3 seconds
        await self._db.set_lock_expiry('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx', 3)
    
        # Should acquire lock. Lock expires in 3 seconds
        self.assertFalse(await self._db.lock_addr('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx'))

        # Wait for lock to expire, 4 seconds
        await asyncio.sleep(4)

        unlocked: int = await self._db.remove_old_locks()
        self.assertEqual(unlocked, 1)

        # Should acquire lock, lock has expired
        self.assertTrue(await self._db.lock_addr('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx'))

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
        addr: str = await self._db.create_new_addr(key_bytes)

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

class TestBalanceChange(DBTestCase):
    async def test_check_balance(self):
        # Create user with balance
        user_id = random.randint(0, 1000000)
        bal = random.randint(0, 1000000)
        self._db.db.balances.insert_one({
            'discord_user': user_id,
            'balance': bal
        })

        # Check balance
        self.assertEqual(await self._db.check_balance(user_id), bittensor.Balance.from_rao(bal).tao)
    
    async def test_update_balance(self):
        # Create user with balance
        user_id = random.randint(0, 1000000)
        bal = random.randint(0, 1000000)
        self._db.db.balances.insert_one({
            'discord_user': user_id,
            'balance': bal
        })

        # Check balance
        self.assertEqual(await self._db.check_balance(user_id), bittensor.Balance.from_rao(bal).tao)
        # Update balance
        update_amount = random.random() * 1000 # Random float between 0 and 1000
        bal_new: bittensor.Balance = bittensor.Balance.from_rao(bal) + bittensor.Balance.from_float(update_amount)
        await self._db.update_balance(user_id, update_amount)
        self.assertEqual(await self._db.check_balance(user_id), bal_new.tao)

class TestAddressCreate(DBTestCase):
    async def test_create_address(self):
        key_bytes: bytes = Fernet.generate_key()
        addr: str = await self._db.create_new_addr(key=key_bytes)
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
