from types import SimpleNamespace

class Config: 
        """
        General configuration parent class
        """
        DISCORD_TOKEN: str
        CURRENCY: str
        BOT_ID: str
        COLDKEY_SECRET: bytes
        MONGO_URI: str
        MONGO_URI_TEST: str
        MAINTAINER: str
        DEP_ACTIVE_TIME: float
        DEPOSIT_INTERVAL: float
        CHECK_ALL_INTERVAL: float
        SUBTENSOR_ENDPOINT: str
        TESTING: bool
        NUM_DEPOSIT_ADDRESSES: int
        HELP_STR: str
        NEW_USER_CHECK_INTERVAL: int
        EXPORT_URL: str
        BITTENSOR_DISCORD_SERVER: int
        def __init__(self, *args):
            if len(args) == 1:
                    if isinstance(args[0], SimpleNamespace):
                        self.__dict__ = args[0].__dict__
                    elif isinstance(args[0], dict):
                        self.__dict__ = args[0]
                    else:
                        raise TypeError(f'Expected SimpleNamespace or dict, got {type(args[0])}')
            elif len(args) == 0:
                pass
            else:
                raise TypeError(f'Expected SimpleNamespace or dict, got {type(args[0])}')

main_config_ = SimpleNamespace(
        DISCORD_TOKEN = '',
        CURRENCY = r'tao|t|tau|Tao|Tau|𝜏',
        BOT_ID = '',
        COLDKEY_SECRET=b'',
        MONGO_URI="mongodb://taotip:prod_pass@mongodb:27017/prod?retryWrites=true&w=majority",
        MONGO_URI_TEST="mongodb://taotip:test_pass@localhost:27017/test?retryWrites=true&w=majority",
        MAINTAINER="<@!>", # discord handle
        DEP_ACTIVE_TIME=600.0, # seconds
        DEPOSIT_INTERVAL=24.0, # seconds
        CHECK_ALL_INTERVAL=300.0, # seconds
        SUBTENSOR_ENDPOINT="<subtensor-ip>:9944",
        TESTING=True,
        HELP_STR="To get your balance, type: `/balance`\n" + \
                "To deposit tao, type: `/deposit`\n" + \
                "To withdraw your tao, type: `/withdraw <address> <amount>`\n" + \
                f"For help, type: `/help` or contact <maintainer>",
        NEW_USER_CHECK_INTERVAL=60.0, # seconds
        EXPORT_URL="https://taotip.opentensor.ai/",
        BITTENSOR_DISCORD_SERVER=0,
)
main_config_.HELP_STR = main_config_.HELP_STR.replace('<maintainer>', main_config_.MAINTAINER)

main_config = Config(main_config_)
