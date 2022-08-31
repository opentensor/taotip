from typing import Any, Dict, List, Optional, Tuple

import bittensor
from scalecodec.base import ScaleBytes
from scalecodec.types import GenericCall
from substrateinterface import Keypair
from tqdm import tqdm

from .config import Config
from .db import Address, Database, Transaction


class API:
    subtensor: bittensor.Subtensor = None
    network: str

    def __init__(self, config: Config, testing: bool=True) -> None:
        # Uses testnet if testing is true
        if testing:
            self.network = 'Nobunaga'
            self.subtensor = bittensor.subtensor(network="nobunaga")
        else:
            self.network = 'Nakamoto'
            self.subtensor = bittensor.subtensor(network="local", chain_endpoint=config.SUBTENSOR_ENDPOINT)

    def get_wallet_balance(self, coldkeyadd: str) -> bittensor.Balance:
        """
        Returns the balance of the given address.

        Args:
            coldkeyadd: The ss58 address to get the balance of.
        
        Returns:
            The balance of the given address: bittensor.Balance
        
        Raises:
            - Exception: If the address is invalid.
            - WebSocketException: If the connection to the Substrate node is lost.
        
        """
        with self.subtensor.substrate as substrate:
            if not substrate.is_valid_ss58_address(coldkeyadd):
                raise Exception('invalid coldkey address coldkeyadd')

        balance = self.subtensor.get_balance(address=coldkeyadd)
        return balance

    def send_transaction(self, transaction) -> Optional[Dict]:
        signature = transaction['signature']
        call = transaction['call']
        coldkeyadd = transaction['coldkeyadd']
        signature_payload_hex = transaction['signature_payload_hex']
        
        try:
            signature_payload = ScaleBytes(signature_payload_hex)
            response, balance = self.send_transaction_(call, signature_payload, coldkeyadd, signature)
            return {
                'message': 'Transaction sent',
                'response': response,
                'balance': balance
            }
        except(Exception) as e:
            print(e, "api.send_transaction")
            return None

    def send_transaction_(self, call: GenericCall, signature_payload: ScaleBytes, coldkeyadd: str, signature: str):        
        with self.subtensor.substrate as substrate:
            if not substrate.is_valid_ss58_address(coldkeyadd):
                raise Exception('invalid coldkey address coldkeyadd')
            
            pubkeypair: Keypair = Keypair(ss58_address=coldkeyadd)

            if not pubkeypair.verify(signature_payload, signature):
                raise Exception('invalid signature')

            extrinsic = substrate.create_signed_extrinsic(call=call, keypair=pubkeypair, signature=signature)
            response = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True, wait_for_finalization=False)
            response.process_events()
            if response.is_success:
                balance = self.get_wallet_balance(coldkeyadd)
                return response, balance
            else:
                raise Exception('transaction failed')

    async def create_transaction(self, transaction: Dict) -> Optional[Dict]:
        coldkeyadd = transaction["coldkeyadd"]
        amount = transaction["amount"]
        dest = transaction["dest"]

        if (not coldkeyadd):
            raise Exception('specify coldkeyadd')

        if (not amount or (not isinstance(amount, float) and not isinstance(amount, int) and not amount.isnumeric())):
            raise Exception('specify amount')

        if (not dest):
            raise Exception('specify destination address dest')

        # converts to balance given tao (float)
        if (isinstance(amount, float)):
            amount = bittensor.Balance.from_float(amount)
        else:
            amount = bittensor.Balance.from_float(float(amount))
        
        balance = self.get_wallet_balance(coldkeyadd)
        if (balance < amount):
            raise Exception('insufficient balance')
        try:
            call, signature_payload, paymentInfo = self.init_transaction(coldkeyadd, dest, amount)
            return {
                'message': 'Signature Payload created',
                'signature_payload_hex': signature_payload.to_hex(),
                'paymentInfo': paymentInfo,
                'call': call,
            }
        except(Exception) as e:
            print(e, "api.create_transaction")
            return None

    def init_transaction(self, coldkeyadd: str, dest: str, amount: bittensor.Balance) -> Tuple[GenericCall, ScaleBytes, Any]:
        with self.subtensor.substrate as substrate:
            if not substrate.is_valid_ss58_address(coldkeyadd):
                raise Exception('invalid coldkey address coldkeyadd')
            if not substrate.is_valid_ss58_address(dest):
                raise Exception('invalid destination address dest')

            call = substrate.compose_call(
                call_module='Balances',
                call_function='transfer',
                call_params={
                    'dest': dest, 
                    'value': amount.rao
                }
            )

            pubkeypair = Keypair(ss58_address=coldkeyadd)
            paymentInfo = substrate.get_payment_info(call, pubkeypair)
            # Retrieve nonce
            nonce = substrate.get_account_nonce(pubkeypair.ss58_address) or 0
            signature_payload = substrate.generate_signature_payload(call=call, nonce=nonce, era='00')

        return call, signature_payload, paymentInfo

    def verify_coldkeyadd(self, coldkeyadd: str) -> bool:
        with self.subtensor.substrate as substrate:
            is_valid = substrate.is_valid_ss58_address(coldkeyadd)
            return is_valid

    async def find_withdraw_address(self, _db: Database, transaction: Transaction, key: bytes) -> Tuple[Optional[str], bittensor.Balance]:
        """
        Finds valid withdraw addresses with available balance.
        """
        addr: Address = _db.get_address_by_user(transaction.user)
        if not addr:
            return None, 0.0

        withdraw_addr = addr.address
        balance: bittensor.Balance = self.get_wallet_balance(withdraw_addr)
        return withdraw_addr, balance
            
    async def sign_transaction(self, _db: Database, transaction: Dict, addr: str, key: bytes) -> Dict:
        doc: Address = _db.get_address(addr, key)
        if (not doc):
            raise Exception('address not found')
        mnemonic: str = doc.mnemonic
        keypair: Keypair = Keypair.create_from_mnemonic(mnemonic)
        signature_payload_hex: str = transaction['signature_payload_hex']
        signature = keypair.sign(signature_payload_hex)

        signed_transaction: Dict = {
            "signature": "0x" + signature.hex(),
            "call": transaction["call"],
            "coldkeyadd": addr,
            "signature_payload_hex": signature_payload_hex
        }
        return signed_transaction

    @staticmethod
    def create_address(key: bytes) -> Address:
        mnemonic = Keypair.generate_mnemonic(12)
        keypair = Keypair.create_from_mnemonic(mnemonic)
        address = keypair.ss58_address
        return Address(address, mnemonic, key)

    async def test_connection(self) -> bool:
        return self.subtensor.connect(failure=False)

    async def check_for_deposits(self, _db: Database) -> List[Transaction]:
        addrs: List[Address] = list(await _db.get_all_addresses_with_lock())
        new_transactions: List[Transaction] = []
        for addr in tqdm(addrs, desc="Checking Deposits..."):
            balance = self.get_wallet_balance(addr["address"])
            result = await _db.update_addr_balance(addr["address"], balance.rao)
            if result is None:
                print("Error checking deposits", addr["address"])
                continue
            change, user = result
            
            if (change > 0):
                new_transaction = Transaction(user, bittensor.Balance.from_rao(change).tao)
                # add transaction to db
                await new_transaction.deposit(_db)
                new_transactions.append(new_transaction)
        return new_transactions

    async def get_withdraw_fee(self, transaction: Dict) -> bittensor.Balance:
        fee = await self.get_fee(
            transaction["coldkeyadd"],
            transaction["dest"],
            bittensor.Balance.from_tao(transaction["amount"])
        )

        return fee

    async def get_fee(self, addr: str, dest: str, amount: bittensor.Balance) -> bittensor.Balance:
        _, _, paymentInfo = self.init_transaction(
            addr,
            dest,
            amount
        )

        fee_rao = paymentInfo["partialFee"]
        fee = bittensor.Balance.from_rao(fee_rao)
        return fee
