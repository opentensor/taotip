import re
from . import config
from substrateinterface.utils.ss58 import is_valid_ss58_address
amount_check = re.compile(r'> (([1-9][0-9]*|0)(\.[0-9]*)?)\s*(' + config.CURRENCY + r'|)$')

def get_amount(message: str) -> float:
    """
    Returns the amount of tao in the message
    """
    try:
        groups = amount_check.search(message).groups()
        amount_str = groups[0]
    except AttributeError as e:
        raise ValueError('Invalid amount')
    return float(amount_str)

def get_coldkeyadd(message: str) -> str:
    address: str = message.split()[1]

    if not is_valid_ss58_address(address, 42):
        raise ValueError('Invalid address')

    return address