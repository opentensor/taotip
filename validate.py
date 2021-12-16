import re
from config import PROMPT
check = re.compile(r'^!tip <@![0-9]+?> ([0-9]+(|\.[0-9]*))( tao| tau|)$')

def is_valid_format(message: str) -> bool:
    """
    Checks if the message is in the correct format for a tip
    """
    return bool(check.search(message))