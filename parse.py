def get_amount(message: str) -> float:
    """
    Returns the amount of tau in the message
    """
    return float(message.split()[2])