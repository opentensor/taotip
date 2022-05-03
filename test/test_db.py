from binascii import hexlify
from random import random
import bittensor
import mongomock
import unittest
from ..src import api, db, config

class DBTestCase(unittest.TestCase):
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
        self.assertTrue(await self._db.unlock_addr('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx'))

        # Should not acquire lock
        self.assertFalse(await self._db.unlock_addr('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx'))

    async def test_address_lock_locked_with_expiry(self):
        # Create locked address in db
        self._db.db.addresses.insert_one({
            'address': '5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx',
            'locked': True
        })

        # Set lock expiry
        ## 5 seconds
        await self._db.set_lock_expiry('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx', 5)
    
        # Should acquire lock. Lock expires in 5 seconds
        self.assertFalse(await self._db.unlock_addr('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx'))

        # Wait for lock to expire, 6 seconds
        await self._api.sleep(6)

        # Should acquire lock, lock has expired
        self.assertTrue(await self._db.unlock_addr('5DkpHw4sL5ZD9FQ8Z5Z5xX3z8bwZKXzQXx'))


class TestAddressEncrypt(DBTestCase):
    async def test_encrypt(self):
        key = '0x' + '0' * 64
        key_bytes = bytes.fromhex(key)
        addr: db.Address = self._api.create_address(key_bytes)
        mnemonic_to_bytes: bytes = bytes(addr.mnemonic, 'utf-8')
        enc_mnemonic: bytes = addr.get_encrypted_mnemonic()
        self.assertNotEqual(mnemonic_to_bytes.hex(), enc_mnemonic.hex())

    async def test_decrypt(self):
        key = '0x' + '0' * 64
        key_bytes = bytes.fromhex(key)
        addr: db.Address = self._api.create_address(key_bytes)
        enc_mnemonic: bytes = addr.get_encrypted_mnemonic()
        dec_mnemonic: str = addr.__unencrypt(enc_mnemonic, key_bytes)
        self.assertEqual(dec_mnemonic, addr.mnemonic)

    async def test_decrypt_wrong_key(self):
        key = '0x' + '0' * 64
        key_bytes = bytes.fromhex(key)
        addr: db.Address = self._api.create_address(key_bytes)
        enc_mnemonic: bytes = addr.get_encrypted_mnemonic()
        key_bytes = bytes.fromhex('0x' + '1' * 64)
        dec_mnemonic: str = addr.__unencrypt(enc_mnemonic, key_bytes)
        self.assertNotEqual(dec_mnemonic, addr.mnemonic)

    async def test_get_encrypted_mnemonic_from_db(self):
        key = '0x' + '0' * 64
        key_bytes = bytes.fromhex(key)
        addr: db.Address = self._api.create_address(key_bytes)
        # Put address in db
        self._db.db.addresses.insert_one({
            'address': addr.address,
            'mnemonic': addr.get_encrypted_mnemonic(),
            'locked': False
        })

        # Get address from db, should be decrypted
        addr_from_db = await self._db.get_address(addr.address, key=key_bytes)
        self.assertEqual(addr_from_db.mnemonic, addr.mnemonic)

    async def test_get_encrypted_mnemonic_from_db_wrong_key(self):
        key = '0x' + '0' * 64
        key_bytes = bytes.fromhex(key)
        addr: db.Address = self._api.create_address(key_bytes)
        # Put address in db
        self._db.db.addresses.insert_one({
            'address': addr.address,
            'mnemonic': addr.get_encrypted_mnemonic(),
            'locked': False
        })

        # Get address from db, should be decrypted
        addr_from_db = await self._db.get_address(addr.address, key=bytes.fromhex('0x' + '1' * 64))
        self.assertNotEqual(addr_from_db.mnemonic, addr.mnemonic)

    async def test_create_address_get_encrypted_mnemonic_from_db(self):
        key = '0x' + '0' * 64
        key_bytes = bytes.fromhex(key)
        addr: str = await self._db.create_new_addr()

        # Get address from db, should be encrypted
        encrypted_addr = self._db.db.addresses.find_one({'address': addr})
        self.assertIsNotNone(encrypted_addr)
        self.assertIsNotNone(encrypted_addr['mnemonic'])
        self.assertIsInstance(encrypted_addr['mnemonic'], bytes)

        encrypted_mnemonic = encrypted_addr['mnemonic']
        
        # Get address from db, should be decrypted
        addr_from_db = await self._db.get_address(addr.address, key=key_bytes)
        self.assertNotEqual(bytes(addr_from_db.mnemonic, 'utf-8'), encrypted_mnemonic)

        # Decrypt mnemonic
        dec_mnemonic = addr_from_db.__unencrypt(encrypted_mnemonic, key_bytes)
        self.assertEqual(dec_mnemonic, addr_from_db.mnemonic)

    async def test_decrypt_on_db(self):
        key = '0x' + '0' * 64
        key_bytes = bytes.fromhex(key)
        addr: db.Address = self._api.create_address(key_bytes)
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
            'discord_use': user_id,
            'balance': bal
        })

        # Check balance
        self.assertEqual(await self._db.check_balance(user_id), bal)
    
    async def test_update_balance(self):
        # Create user with balance
        user_id = random.randint(0, 1000000)
        bal = random.randint(0, 1000000)
        self._db.db.balances.insert_one({
            'discord_use': user_id,
            'balance': bal
        })

        # Check balance
        self.assertEqual(await self._db.check_balance(user_id), bal)
        # Update balance
        update_amount = random.random() * 1000 # Random float between 0 and 1000
        bal_new: bittensor.Balance = bittensor.Balance.from_rao(bal) + bittensor.Balance.from_float(update_amount)
        await self._db.update_balance(user_id, update_amount)
        self.assertEqual(await self._db.check_balance(user_id), bal_new.to_rao())
