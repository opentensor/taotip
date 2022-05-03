import mongomock
import unittest
from ..src import api, db, config


class TestAddressLock(unittest.TestCase):
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

    async def test_address_lock_locked_in_function(self):
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


