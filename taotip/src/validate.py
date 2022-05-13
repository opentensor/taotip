import re

from .config import Config


class Validator:
    """
    Class to validate messages
    """
    def __init__(self, config: Config):
        self.check = re.compile(r'^' + config.PROMPT + r'\s+<@!?[0-9]+?>\s+([0-9]+(|\.[0-9]*))\s*(' + config.CURRENCY + r'|)$')
        self.bal_check = re.compile(r'^(' + config.BAL_PROMPT + r')$')
        self.with_check = re.compile(r'^(' + config.WIT_PROMPT + r')$')
        self.dep_check = re.compile(r'^(' + config.DEP_PROMPT + r'$)')
        self.help_check = re.compile(r'^(' + config.HELP_PROMPT + r')$')

    def is_valid_format(self, message: str) -> bool:
        """
        Checks if the message is in the correct format for a tip
        """
        return bool(self.check.fullmatch(message))

    def is_balance_check(self, message: str) -> bool:
        """
        Checks if the message is to check a balance
        """
        return bool(self.bal_check.search(message))

    def is_deposit_or_withdraw(self, message: str) -> bool:
        return self.is_deposit(message) or self.is_withdraw(message)

    def is_deposit(self, message: str) -> bool:
        return bool(self.dep_check.search(message))

    def is_withdraw(self, message: str) -> bool:
        return bool(self.with_check.search(message))

    def is_help(self, message: str) -> bool:
        return bool(self.help_check.search(message))
