import re
amount_check = re.compile(r'(([1-9][0-9]*|0)(\.[0-9]*))')

def get_amount(message: str) -> float:
    """
    Returns the amount of tao in the message
    """
    amount_str = amount_check.search(message).groups()[0]
    return float(amount_str)

def get_coldkeyadd(message: str) -> str:
    return message.split()[1]