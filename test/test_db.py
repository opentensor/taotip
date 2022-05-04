import imp
import random
import bittensor
import mongomock
import unittest
import asyncio
import pytest
from cryptography.fernet import Fernet
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

class TestTips(DBTestCase):
    async def test_tip_create(self):
        # Create user with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount = random.random() * 1000 + 1.0# Random float between 1 and 1001

        tip: Tip = Tip(sender, recipient, amount)
        self.assertEqual(tip.sender, sender)
        self.assertEqual(tip.recipient, recipient)
        self.assertEqual(tip.amount, amount)

        self.assertEqual(str(tip), f'{sender} -> {recipient} ({amount}) tao')

        # Insert tip in db
        await self._db.record_tip(tip)

        # Check if tip is in db
        tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
        self.assertEqual(tip_from_db['sender'], sender)
        self.assertEqual(tip_from_db['recipient'], recipient)
        self.assertEqual(
            bittensor.Balance.from_rao(tip_from_db['amount']),
            bittensor.Balance.from_float(amount)
        )
        ## Timestamp on mongo loses some precision
        self.assertAlmostEqual(tip_from_db['time'].timestamp(), tip.time.timestamp(), delta=0.001)

    async def test_tip_sent(self):
        # Create user with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount: float = random.random() * 1000 + 1.0 # Random float between 1 and 1001
        bal: int = random.randint(0, 100000000000) + bittensor.Balance.from_float(amount).rao
        # Insert user in db
        self._db.db.balances.insert_one({
            'discord_user': sender,
            'balance': bal
        })

        # Check balance
        self.assertEqual(await self._db.check_balance(sender), bittensor.Balance.from_rao(bal).tao)
        # Tip user
        tip: Tip = Tip(sender, recipient, amount)
        ## Send tip
        await tip.send(self._db)

        # Check balance
        balance_new_expected: bittensor.Balance = bittensor.Balance.from_rao(bal) - bittensor.Balance.from_float(amount)
        self.assertEqual(await self._db.check_balance(sender), balance_new_expected.tao)    

        # Check balance using db
        balance_db: int = self._db.db.balances.find_one({'discord_user': sender})['balance']
        self.assertEqual(balance_db, balance_new_expected.rao)

        # Check if tip is in db
        tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
        self.assertEqual(tip_from_db['sender'], sender)
        self.assertEqual(tip_from_db['recipient'], recipient)
        self.assertEqual(
            bittensor.Balance.from_rao(tip_from_db['amount']),
            bittensor.Balance.from_float(amount)
        )
        ## Timestamp on mongo loses some precision
        self.assertAlmostEqual(tip_from_db['time'].timestamp(), tip.time.timestamp(), delta=0.001)

    async def test_tip_received_no_recipient_balance(self):
        # Create sender with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount: float = random.random() * 1000 + 1
        bal: int = random.randint(0, 100000000000) + bittensor.Balance.from_float(amount).rao
        # Insert user in db
        self._db.db.balances.insert_one({
            'discord_user': sender,
            'balance': bal
        })

        # Check balance
        self.assertEqual(await self._db.check_balance(sender), bittensor.Balance.from_rao(bal).tao)
        # Tip user
        tip: Tip = Tip(sender, recipient, amount)
        ## Send tip
        await tip.send(self._db)

        # Check balance of recipient
        balance_new_expected: bittensor.Balance = bittensor.Balance.from_float(amount)
        self.assertEqual(await self._db.check_balance(recipient), balance_new_expected.tao)    

        # Check balance using db
        balance_db: int = self._db.db.balances.find_one({'discord_user': recipient})['balance']
        self.assertEqual(balance_db, balance_new_expected.rao)

        # Check if tip is in db
        tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
        self.assertEqual(tip_from_db['sender'], sender)
        self.assertEqual(tip_from_db['recipient'], recipient)
        self.assertEqual(
            bittensor.Balance.from_rao(tip_from_db['amount']),
            bittensor.Balance.from_float(amount)
        )
        ## Timestamp on mongo loses some precision
        self.assertAlmostEqual(tip_from_db['time'].timestamp(), tip.time.timestamp(), delta=0.001)

    async def test_tip_received_recipient_has_balance(self):
        # Create sender with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount: float = random.random() * 1000 + 1
        bal: int = random.randint(0, 100000000000) + bittensor.Balance.from_float(amount).rao
        # Insert user in db
        self._db.db.balances.insert_one({
            'discord_user': sender,
            'balance': bal
        })

        # Insert recipient with balance
        recipient_bal: int = random.randint(0, 100000000000)
        self._db.db.balances.insert_one({
            'discord_user': recipient,
            'balance': recipient_bal
        })

        # Check balance
        self.assertEqual(await self._db.check_balance(sender), bittensor.Balance.from_rao(bal).tao)
        self.assertEqual(await self._db.check_balance(recipient), bittensor.Balance.from_rao(recipient_bal).tao)
        # Tip user
        tip: Tip = Tip(sender, recipient, amount)
        ## Send tip
        await tip.send(self._db)

        # Check balance of recipient
        balance_new_expected: bittensor.Balance = bittensor.Balance.from_float(amount) + bittensor.Balance.from_rao(recipient_bal)
        self.assertEqual(await self._db.check_balance(recipient), balance_new_expected.tao)

        # Check balance using db
        balance_db: int = self._db.db.balances.find_one({'discord_user': recipient})['balance']
        self.assertEqual(balance_db, balance_new_expected.rao)

        # Check if tip is in db
        tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
        self.assertEqual(tip_from_db['sender'], sender)
        self.assertEqual(tip_from_db['recipient'], recipient)
        self.assertEqual(
            bittensor.Balance.from_rao(tip_from_db['amount']),
            bittensor.Balance.from_float(amount)
        )
        ## Timestamp on mongo loses some precision
        self.assertAlmostEqual(tip_from_db['time'].timestamp(), tip.time.timestamp(), delta=0.001)

    async def test_tip_not_enough_balance(self):
        # Create sender with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount: float = random.random() * 1000 + 2
        bal: int = bittensor.Balance.from_float(amount).rao - random.randint(1, 100)
        bal = bal if bal > 0 else 1 # Ensure balance is positive
        # Insert user in db
        self._db.db.balances.insert_one({
            'discord_user': sender,
            'balance': bal
        })

        # Insert recipient with balance
        recipient_bal: int = random.randint(0, 100000000000)
        self._db.db.balances.insert_one({
            'discord_user': recipient,
            'balance': recipient_bal
        })

        # Check balance
        self.assertEqual(await self._db.check_balance(sender), bittensor.Balance.from_rao(bal).tao)
        # Tip user
        tip: Tip = Tip(sender, recipient, amount)
        ## Send tip
        await tip.send(self._db)

        # Tip should fail

        # Check balance of sender
        balance_new_expected_sender: bittensor.Balance = bittensor.Balance.from_rao(bal)
        self.assertEqual(await self._db.check_balance(sender), balance_new_expected_sender.tao)
        
        # Check balance using db
        balance_db_sender: int = self._db.db.balances.find_one({'discord_user': sender})['balance']
        self.assertEqual(balance_db_sender, balance_new_expected_sender.rao)

        # Check balance of recipient. Should be unchanged
        balance_new_expected_rec: bittensor.Balance = bittensor.Balance.from_rao(recipient_bal)
        self.assertEqual(await self._db.check_balance(recipient), balance_new_expected_rec.tao)    

        # Check balance using db
        balance_db_rec: int = self._db.db.balances.find_one({'discord_user': recipient})['balance']
        self.assertEqual(balance_db_rec, balance_new_expected_rec.rao)

        # Check if tip is in db
        tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
        self.assertIsNone(tip_from_db)

    async def test_tip_no_balance(self):
        # Create sender with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount: float = random.random() * 1000 + 1
        bal: int = 0
        # Insert user in db
        self._db.db.balances.insert_one({
            'discord_user': sender,
            'balance': bal
        })

        # Insert recipient with balance
        recipient_bal: int = random.randint(0, 100000000000)
        self._db.db.balances.insert_one({
            'discord_user': recipient,
            'balance': recipient_bal
        })

        # Check balance
        self.assertEqual(await self._db.check_balance(sender), bittensor.Balance.from_rao(bal).tao)
        # Tip user
        tip: Tip = Tip(sender, recipient, amount)
        ## Send tip
        await tip.send(self._db)

        # Tip should fail

        # Check balance of sender
        balance_new_expected_sender: bittensor.Balance = bittensor.Balance.from_rao(bal)
        self.assertEqual(await self._db.check_balance(sender), balance_new_expected_sender.tao)
        
        # Check balance using db
        balance_db_sender: int = self._db.db.balances.find_one({'discord_user': sender})['balance']
        self.assertEqual(balance_db_sender, balance_new_expected_sender.rao)

        # Check balance of recipient. Should be unchanged
        balance_new_expected_rec: bittensor.Balance = bittensor.Balance.from_rao(recipient_bal)
        self.assertEqual(await self._db.check_balance(recipient), balance_new_expected_rec.tao)    

        # Check balance using db
        balance_db_rec: int = self._db.db.balances.find_one({'discord_user': recipient})['balance']
        self.assertEqual(balance_db_rec, balance_new_expected_rec.rao)

        # Check if tip is in db
        tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
        self.assertIsNone(tip_from_db)

    async def test_tip_no_sender_in_db(self):
        # Create sender with balance
        sender = random.randint(0, 1000000)
        recipient = random.randint(0, 1000000)
        amount: float = random.random() * 1000 + 1

        # Insert recipient with balance
        recipient_bal: int = random.randint(0, 100000000000)
        self._db.db.balances.insert_one({
            'discord_user': recipient,
            'balance': recipient_bal
        })

        # Tip user
        tip: Tip = Tip(sender, recipient, amount)
        ## Send tip
        await tip.send(self._db)

        # Tip should fail

        # Check balance of sender
        self.assertEqual(await self._db.check_balance(sender), 0.0)
        
        # Check balance using db
        db_sender: int = self._db.db.balances.find_one({'discord_user': sender})
        self.assertIsNone(db_sender, 'User should not be in db')

        # Check balance of recipient. Should be unchanged
        balance_new_expected_rec: bittensor.Balance = bittensor.Balance.from_rao(recipient_bal)
        self.assertEqual(await self._db.check_balance(recipient), balance_new_expected_rec.tao)    

        # Check balance using db
        balance_db_rec: int = self._db.db.balances.find_one({'discord_user': recipient})['balance']
        self.assertEqual(balance_db_rec, balance_new_expected_rec.rao)

        # Check if tip is in db
        tip_from_db: Tip = self._db.db.tips.find_one({'sender': sender, 'recipient': recipient})
        self.assertIsNone(tip_from_db, 'Tip should not be in db')
