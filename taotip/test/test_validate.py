import random
import unittest
from types import SimpleNamespace
from cryptography.fernet import Fernet

from ..src.config import Config
from ..src.validate import Validator

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
class TestValidate(unittest.TestCase):
    validator: Validator

    def setUp(self):
        self.validator = Validator(mock_config)

    def test_is_valid_tip(self):
        is_valid_format = self.validator.is_valid_format
        test_str_plain = "!tip <@!274877908992> 100"
        self.assertTrue(is_valid_format(test_str_plain))
        test_str_plain_no_space = "!tip <@!274877908992>100"
        self.assertFalse(is_valid_format(test_str_plain_no_space))
        test_str_tao = "!tip <@!274877908992> 1 tao"
        self.assertTrue(is_valid_format(test_str_tao))
        test_str_tao = "!tip <@!274877908992> 1 tao"
        self.assertTrue(is_valid_format(test_str_tao))
        test_str_tao_no_space = "!tip <@!274877908992>1tao"
        self.assertFalse(is_valid_format(test_str_tao_no_space))
        test_str_tao_no_space = "!tip <@!274877908992>1tao"
        self.assertFalse(is_valid_format(test_str_tao_no_space))
        test_str_random_usr = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 1"
        self.assertTrue(is_valid_format(test_str_random_usr))
        test_str_float = "!tip <@!274877908992> 1.5"
        self.assertTrue(is_valid_format(test_str_float))
        test_str_float_no_decimal = "!tip <@!274877908992> 1."
        self.assertTrue(is_valid_format(test_str_float_no_decimal))
    
    def test_is_valid_deposit(self):
        is_deposit = self.validator.is_deposit
        test_str_dep: str = '!deposit'
        self.assertTrue(is_deposit(test_str_dep))
        test_str_dep_add_tao: str = '!deposit tao'
        self.assertFalse(is_deposit(test_str_dep_add_tao))
        test_str_dep_not_withdraw: str = '!withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1.0 tao'
        self.assertFalse(is_deposit(test_str_dep_not_withdraw))
        test_str_dep_not_withdraw_no_tao: str = '!withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1.0'
        self.assertFalse(is_deposit(test_str_dep_not_withdraw_no_tao))
        test_str_dep_not_tip = '!tip <@!274877908992> 100'
        self.assertFalse(is_deposit(test_str_dep_not_tip))
        test_str_dep_not_balance = '!balance'
        self.assertFalse(is_deposit(test_str_dep_not_balance))
        test_str_dep_not_help = '!help'
        self.assertFalse(is_deposit(test_str_dep_not_help))

    def test_is_valid_withdraw(self):
        is_withdraw = self.validator.is_withdraw
        test_str_withdraw: str = '!withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1.0 tao'
        self.assertTrue(is_withdraw(test_str_withdraw))
        test_str_withdraw_no_tao: str = '!withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1.0'
        self.assertTrue(is_withdraw(test_str_withdraw_no_tao))
        test_str_withdraw_no_space: str = '!withdraw5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY1.0'
        self.assertFalse(is_withdraw(test_str_withdraw_no_space))
        test_str_withdraw_int: str = '!withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1'
        self.assertTrue(is_withdraw(test_str_withdraw_int))
        test_str_withdraw_int_tao: str = '!withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1 tao'
        self.assertTrue(is_withdraw(test_str_withdraw_int_tao))

    def test_is_valid_balance(self):
        is_balance_check = self.validator.is_balance_check
        test_str_balance: str = '!balance'
        self.assertTrue(is_balance_check(test_str_balance))
        test_str_bal: str = '!bal'
        self.assertTrue(is_balance_check(test_str_bal))
        test_str_balance_not_deposit: str = '!deposit'
        self.assertFalse(is_balance_check(test_str_balance_not_deposit))
        test_str_balance_not_withdraw: str = '!withdraw'
        self.assertFalse(is_balance_check(test_str_balance_not_withdraw))
        test_str_balance_not_help: str = '!help'
        self.assertFalse(is_balance_check(test_str_balance_not_help))
        test_str_balance_not_tip: str = '!tip'
        self.assertFalse(is_balance_check(test_str_balance_not_tip))

    def test_is_valid_help(self):
        is_help = self.validator.is_help
        test_str_help: str = '!help'
        self.assertTrue(is_help(test_str_help))
        test_str_h : str = '!h'
        self.assertTrue(is_help(test_str_h))
        test_str_help_not_deposit: str = '!deposit'
        self.assertFalse(is_help(test_str_help_not_deposit))
        test_str_help_not_withdraw: str = '!withdraw'
        self.assertFalse(is_help(test_str_help_not_withdraw))
        test_str_help_not_balance: str = '!balance'
        self.assertFalse(is_help(test_str_help_not_balance))
        test_str_help_not_tip: str = '!tip'
        self.assertFalse(is_help(test_str_help_not_tip))
        test_str_help_not_wrong: str = '!helpasdasd'
        self.assertFalse(is_help(test_str_help_not_wrong))

    def test_is_valid_deposit_or_withdraw(self):
        is_deposit_or_withdraw = self.validator.is_deposit_or_withdraw
        test_str_dep: str = '!deposit'
        self.assertTrue(is_deposit_or_withdraw(test_str_dep))
        test_str_dep_add_tao: str = '!deposit tao'
        self.assertFalse(is_deposit_or_withdraw(test_str_dep_add_tao))
        test_str_dep_not_tip = '!tip <@!274877908992> 100'
        self.assertFalse(is_deposit_or_withdraw(test_str_dep_not_tip))
        test_str_dep_not_balance = '!balance'
        self.assertFalse(is_deposit_or_withdraw(test_str_dep_not_balance))
        test_str_dep_not_help = '!help'
        self.assertFalse(is_deposit_or_withdraw(test_str_dep_not_help))

        test_str_withdraw: str = '!withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1.0 tao'
        self.assertTrue(is_deposit_or_withdraw(test_str_withdraw))
        test_str_withdraw_no_tao: str = '!withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1.0'
        self.assertTrue(is_deposit_or_withdraw(test_str_withdraw_no_tao))
        test_str_withdraw_no_space: str = '!withdraw5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY1.0'
        self.assertFalse(is_deposit_or_withdraw(test_str_withdraw_no_space))
        test_str_withdraw_int: str = '!withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1'
        self.assertTrue(is_deposit_or_withdraw(test_str_withdraw_int))
        test_str_withdraw_int_tao: str = '!withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1 tao'
        self.assertTrue(is_deposit_or_withdraw(test_str_withdraw_int_tao))

        test_str_dep_and_wtihdraw: str = '!deposit 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1.0 tao !withdraw 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY 1.0 tao'
        self.assertFalse(is_deposit_or_withdraw(test_str_dep_and_wtihdraw))
