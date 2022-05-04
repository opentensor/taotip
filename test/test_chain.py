import random
from types import SimpleNamespace
from typing import Dict
from unittest.mock import MagicMock

import bittensor
from cryptography.fernet import Fernet

from ..src import api, db
from .test_db import DBTestCase

"""
Testing all the chain functions in the api.py file.
Mocks the blockchain and the database.
"""
class TestSendTransaction(DBTestCase):
    _api: api.API
    _db: db.Database
    
    def test_send_transaction(self):
        pass

    def test_check_balance(self):
        pass

    def test_check_balance_with_invalid_address(self):
        pass

    def test_check_balance_after_transaction(self):
        pass
