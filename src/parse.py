import re
from . import config
from substrateinterface.utils import ss58
amount_check = re.compile(r'> (([1-9][0-9]*|0)(\.[0-9]*)?)\s*(' + config.CURRENCY + r'|)$')

def is_valid_ss58_address(addr: str, format: int) -> bool:
    try:
        ss58.is_valid_ss58_address(addr, format)
        return True
    except IndexError as e:
        return False

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