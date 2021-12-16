from ..validate import is_valid_format
import random

def test_is_valid_format():
    test_str_plain = "!tip <@!274877908992> 100"
    assert is_valid_format(test_str_plain)
    test_str_plain_no_space = "!tip <@!274877908992>100"
    assert not is_valid_format(test_str_plain_no_space)
    test_str_tao = "!tip <@!274877908992> 1 tao"
    assert is_valid_format(test_str_tao)
    test_str_tau = "!tip <@!274877908992> 1 tau"
    assert is_valid_format(test_str_tau)
    test_str_tao_no_space = "!tip <@!274877908992>1tao"
    assert not is_valid_format(test_str_tao_no_space)
    test_str_tau_no_space = "!tip <@!274877908992>1tau"
    assert not is_valid_format(test_str_tau_no_space)
    test_str_random_usr = f"!tip <@!{''.join([str(random.randint(0,9)) for _ in range(random.randint(0,18))])}> 1"
    assert is_valid_format(test_str_random_usr)
    test_str_float = "!tip <@!274877908992> 1.5"
    assert is_valid_format(test_str_float)
    test_str_float_no_decimal = "!tip <@!274877908992> 1."
    assert is_valid_format(test_str_float_no_decimal)
    

