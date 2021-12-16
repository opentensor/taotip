class Tip:
    amount: float
    sender: str
    recipient: str

    def __init__(self, sender:str, recipient: str, amount: int) -> None:
        self.amount = amount
        self.sender = sender
        self.recipient = recipient

    def __str__(self) -> str:
        return f"{self.amount} tau"

    def send(self) -> bool:
        if (self.amount < 0):
            return False
        
        return True