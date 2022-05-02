import re
from .config import PROMPT, BAL_PROMPT, DEP_PROMPT, WIT_PROMPT, HELP_PROMPT, CURRENCY
check = re.compile(r'^' + PROMPT + r'\s+<@!?[0-9]+?>\s+([0-9]+(|\.[0-9]*))\s*(' + CURRENCY + r'|)$')
bal_check = re.compile(r'^' + BAL_PROMPT + r'$')
with_check = re.compile(r'^' + WIT_PROMPT + r'$')
dep_check = re.compile(r'^' + DEP_PROMPT + r'$')
help_check = re.compile(r'^' + HELP_PROMPT + r'$')

def is_valid_format(message: str) -> bool:
    """
    Checks if the message is in the correct format for a tip
    """
    return bool(check.search(message))

def is_balance_check(message: str) -> bool:
    """
    Checks if the message is to check a balance
    """
    return bool(bal_check.search(message))

def is_deposit_or_withdraw(message: str) -> bool:
    return is_deposit(message) or is_withdraw(message)

def is_deposit(message: str) -> bool:
    return bool(dep_check.search(message))

def is_withdraw(message: str) -> bool:
    return bool(with_check.search(message))

def is_help(message: str) -> bool:
    return bool(help_check.search(message))