import random
import unittest

from ..src.validate import (is_balance_check, is_deposit,
                            is_deposit_or_withdraw, is_help, is_valid_format,
                            is_withdraw)


class TestValidate(unittest.TestCase):
    def test_is_valid_tip(self):
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
