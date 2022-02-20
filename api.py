import json
from re import sub
from typing import Any, Dict, List, Optional, Tuple
from scalecodec.base import ScaleBytes, ScaleType
from scalecodec.types import GenericCall
from db import Address, Database, Transaction
from substrateinterface import Keypair
import bittensor
import config
from tqdm import tqdm

async def get_wallet_balance(coldkeyadd: str) -> int:
    subtensor = bittensor.subtensor(chain_endpoint=config.SUBTENSOR_ENDPOINT)
    return subtensor.get_balance(address=coldkeyadd)

def send_transaction(transaction) -> Optional[Dict]:
    signature = transaction['signature']
    call_hex = transaction['call_hex']
    coldkeyadd = transaction['coldkeyadd']
    signature_payload_hex = transaction['signature_payload_hex']
    
    try:
        call = GenericCall(call_hex)
        signature_payload = ScaleBytes.from_hex(signature_payload_hex)
        response, balance = send_transaction_(call, signature_payload, coldkeyadd, signature)
        return {
            'message': 'Transaction sent',
            'response': response,
            'balance': balance
        }
    except(Exception) as e:
        print(e, "api.send_transaction")
        return None

def send_transaction_(call: GenericCall, signature_payload: ScaleBytes, coldkeyadd: str, signature: str):
    subtensor = bittensor.subtensor(chain_endpoint=config.SUBTENSOR_ENDPOINT)
    
    with subtensor.substrate as substrate:
        if not substrate.is_valid_ss58_address(coldkeyadd):
            raise Exception('invalid coldkey address coldkeyadd')
        
        pubkeypair: Keypair = Keypair(ss58_address=coldkeyadd)

        if not pubkeypair.verify(signature_payload, signature):
            raise Exception('invalid signature')

        extrinsic = substrate.create_signed_extrinsic(call, pubkeypair, signature=signature)
        response = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True, wait_for_finalization=True)
        response.process_events()
        if response.is_success():
            balance = get_wallet_balance(coldkeyadd)
            return response, balance
        else:
            raise Exception('transaction failed')

def create_transaction(transaction: Dict) -> Optional[Dict]:
    coldkeyadd = transaction["coldkeyadd"]
    amount = transaction["amount"]
    dest = transaction["dest"]

    if (not coldkeyadd):
        raise 'specify coldkeyadd'

    if (not amount or amount.isnumeric()):
        raise 'specify amount'

    if (not dest):
        raise 'specify destination address dest'

    # converts to balance given tao (float)
    amount = bittensor.Balance.from_float(float(amount))
    
    balance = get_wallet_balance(coldkeyadd)
    if (balance < amount):
        raise 'insufficient balance'
    try:
        call, signature_payload, paymentInfo = init_transaction(coldkeyadd, dest, amount)
        return {
            'message': 'Signature Payload created',
            'signature_payload_hex': signature_payload.to_hex(),
            'paymentInfo': paymentInfo,
            'call': call.data.to_hex(),
        }
    except(Exception) as e:
        print(e, "api.create_transaction")
        return None

def init_transaction(coldkeyadd: str, dest: str, amount: bittensor.Balance) -> Tuple[GenericCall, ScaleBytes, Any]:
    subtensor = bittensor.subtensor(chain_endpoint=config.SUBTENSOR_ENDPOINT)
    with subtensor.substrate as substrate:
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
        paytmentInfo = substrate.get_payment_info(call, pubkeypair)

        signature_payload = substrate.generate_signature_payload(call)

    return call, signature_payload, paytmentInfo

def verify_coldkeyadd(coldkeyadd: str) -> bool:
    subtensor = bittensor.subtensor(chain_endpoint=config.SUBTENSOR_ENDPOINT)
    with subtensor.substrate as substrate:
        return substrate.is_valid_ss58_address(coldkeyadd)

async def find_withdraw_address(_db: Database, transation: Transaction) -> Tuple[List[str], List[float]]:
    """
    Finds valid withdraw addresses with available balance.
    """
    final_addrs: List[str] = []
    final_amts: List[float] = []
    remaining_balance: float = transation.amount
    fee: float = transation.fee
    # get all possible withdraw addresses
    withdraw_addrs: List[str] = await _db.get_withdraw_addresses()
    for addr in withdraw_addrs:
        # lock addr
        if(await _db.lock_addr(addr)):
            balance_rao: int = await get_wallet_balance(addr)
            balance: float = bittensor.Balance.from_rao(balance_rao).tao
            if (balance > 0.0):
                
                amt: float = 0.0

                if (balance >= remaining_balance + fee):
                    amt = remaining_balance
                    remaining_balance = 0.0
                else:
                    amt = balance - fee
                    if amt <= 0.0:
                        continue
                
                remaining_balance -= amt
                final_addrs.append(addr)
                final_amts.append(amt)
                if (remaining_balance <= 0.0):
                    break

            await _db.unlock_addr(addr)
        else:
            # no lock
            continue
    else:
        raise "Could not find enough tao to withdraw"
    return final_addrs, final_amts
         
async def sign_transaction(_db: Database, transaction: Dict, addr: str) -> Dict:
    doc: Address = await _db.get_address(addr)
    mnemonic: str = doc.mnemonic
    keypair: Keypair = Keypair.create_from_mnemonic(mnemonic)
    signature_payload_hex: str = transaction['signature_payload_hex']
    signature = keypair.sign(signature_payload_hex)

    signed_transaction: Dict = {
        "signature": signature,
        "call_hex": transaction["call"],
        "coldkeyadd": addr,
        "signature_payload_hex": signature_payload_hex
    }
    return signed_transaction

async def create_address() -> Address:
    mnemonic = Keypair.generate_mnemonic(12)
    keypair = Keypair.create_from_mnemonic(mnemonic)
    address = keypair.ss58_address
    return Address(address, mnemonic)

async def test_connection() -> bool:
    subtensor = bittensor.subtensor(chain_endpoint=config.SUBTENSOR_ENDPOINT)
    return subtensor.connect(failure=False)

async def check_for_deposits(_db: Database) -> List[Transaction]:
    addrs: List[Address] = list(await _db.get_all_addresses_with_lock())
    new_transactions: List[Transaction] = []
    for addr in tqdm(addrs, desc="Checking Deposits..."):
        balance = await get_wallet_balance(addr["address"])
        result = await _db.update_addr_balance(addr["address"], balance.rao)
        if result is None:
            print("Error checking deposits")
            return []
        change, user = result
        
        if (change > 0):
            new_transaction = Transaction(user, change)
            new_transactions.append(new_transaction)
    return new_transactions

async def get_withdraw_fee() -> float:
    return 0.125

