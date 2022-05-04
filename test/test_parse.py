from ..src.parse import get_amount, get_coldkeyadd, is_valid_ss58_address
import random
import unittest
from substrateinterface.utils import ss58
from substrateinterface import Keypair

class TestGetAmount(unittest.TestCase):
    def test_get_amount(self):
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 100"
        self.assertEqual(get_amount(input), 100)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 1.5"
        self.assertEqual(get_amount(input), 1.5)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 1.5 tao"
        self.assertEqual(get_amount(input), 1.5)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 2.89 tau"
        self.assertEqual(get_amount(input), 2.89)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 1tao"
        self.assertEqual(get_amount(input), 1)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 10.0tau"
        self.assertEqual(get_amount(input), 10.0)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 8.23t"
        self.assertEqual(get_amount(input), 8.23)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 2 t"
        self.assertEqual(get_amount(input), 2)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 2.0𝜏"
        self.assertEqual(get_amount(input), 2.0)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 123123. Tao"
        self.assertEqual(get_amount(input), 123123.0)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 990 Tau"
        self.assertEqual(get_amount(input), 990)

        # Test with random numbers
        amount = random.randint(0, 100000)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> {amount} tao"
        self.assertEqual(get_amount(input), amount)
        amount = random.random() * 100000
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> {amount} tao"
        self.assertEqual(get_amount(input), amount)
    
    def test_get_amount_fail(self):
        # Test invalid input
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> at"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> at tao"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> tao 1.0"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> tau 89"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> Tau 2.92"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> Tau 90"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> tao"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> tao tao"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> tau tao"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> tao tau"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> tau Tau"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> tautao"
        self.assertRaises(ValueError, get_amount, input)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 1 taunot"
        self.assertRaises(ValueError, get_amount, input)

        # Test with random numbers
        amount = random.randint(0, 100000)
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> {amount} Taonot"
        self.assertRaises(ValueError, get_amount, input)
        amount = random.random() * 100000
        input: str = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> {amount} taonot"
        self.assertRaises(ValueError, get_amount, input)
        
class RandomColdkey():
    _ck: str

    @staticmethod
    def _get_new_coldkey() -> str:
        mnemonic: str = Keypair.generate_mnemonic(words=12)
        key: Keypair = Keypair.create_from_mnemonic(mnemonic, ss58_format=42)
        good_addr = key.ss58_address
        return good_addr

    def __str__(self):
        return self._ck

    def __eq__(self, __x: object) -> bool:
        return self._ck == __x
    
    def startswith(self, __x: str) -> bool:
        return self._ck.startswith(__x)

    def next(self):
        self._ck = self._get_new_coldkey()
        return self

    def rstrip(self) -> str:
        return self._ck.rstrip()

class RandomBadColdkey(RandomColdkey):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def _get_new_bad_coldkey() -> str:
        good_addr = RandomColdkey._get_new_coldkey()
        i = random.randint(0, len(good_addr))
        # Replace a random character with a random character
        bad_addr = good_addr[:i] + random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") + good_addr[i+1:]
        return bad_addr

    def next(self):
        self._ck = self._get_new_coldkey()
        return self
        
class TestGetColdkeyadd(unittest.TestCase):
    def test_get_coldkeyadd(self):
        # Test valid input
        ## Use constant coldkey
        ck: str = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
        ## Test with ints
        input: str = f"!withdraw {ck} {random.randint(0, 1000)} tao"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!deposit {ck} {random.randint(0, 1000)} tao"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.randint(0, 1000)} tau"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.randint(0, 1000)} Tau"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.randint(0, 1000)}t"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.randint(0, 1000)}t"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.randint(0, 1000)}𝜏"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.randint(0, 1000)}"
        self.assertEqual(get_coldkeyadd(input), ck)

        # Test with floats
        input: str = f"!withdraw {ck} {random.random() * 1000}t"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.random() * 1000}"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.random() * 1000}𝜏"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.random() * 1000} tao"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.random() * 1000} Tau"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.random() * 1000} Tao"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.random() * 1000}Tao"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck} {random.random() * 1000}tao"
        self.assertEqual(get_coldkeyadd(input), ck)

    def test_get_coldkeyadd_random_key(self):
        # Test valid input
        ## Use random coldkeys that are one digit off
        
        ## Test with ints
        ck = RandomColdkey()
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)} tao"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)} tao"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)} tau"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)} Tau"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)}t"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)}t"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)}𝜏"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)}"
        self.assertEqual(get_coldkeyadd(input), ck)

        # Test with floats
        input: str = f"!withdraw {ck.next()} {random.random() * 1000}t"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000}"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000}𝜏"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000} tao"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000} Tau"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000} Tao"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000}Tao"
        self.assertEqual(get_coldkeyadd(input), ck)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000}tao"
        self.assertEqual(get_coldkeyadd(input), ck)

    def test_get_coldkeyadd_random_bad_key(self):
        # Test valid input
        ## Use random coldkeys that are one digit off
        
        ## Test with ints
        ck = RandomBadColdkey()
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)} tao"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)} tao"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)} tau"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)} Tau"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)}t"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)}t"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)}𝜏"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.randint(0, 1000)}"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)

        # Test with floats
        input: str = f"!withdraw {ck.next()} {random.random() * 1000}t"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000}"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000}𝜏"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000} tao"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000} Tau"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000} Tao"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000}Tao"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)
        input: str = f"!withdraw {ck.next()} {random.random() * 1000}tao"
        if (not is_valid_ss58_address(ck, 42)):
            self.assertRaises(ValueError, get_coldkeyadd, input)

