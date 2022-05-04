from random import random
import bittensor
import mongomock
from ..src import api, db

from .test_db import DBTestCase

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

class TestWithdraw(DBTestCase):
    def test_withdraw_with_zero_balance(self):
        pass

    def test_withdraw_with_nonzero_balance(self):   
        pass

    def test_withdraw_with_no_balance_doc(self):
        pass

    def test_withdraw_no_addresses(self):
        pass

    def test_sign_transaction(self):
        pass


