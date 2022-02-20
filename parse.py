def get_amount(message: str) -> float:
    """
    Returns the amount of tao in the message
    """
    return float(message.split()[2])

def get_coldkeyadd(message: str) -> str:
    return message.split()[1]