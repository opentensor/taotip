import asyncio
import copy
import random
from types import SimpleNamespace
from typing import Coroutine
from callee import Contains
from unittest.mock import MagicMock, patch, AsyncMock
from cryptography.fernet import Fernet

import bittensor
import discord

from ..src import event_handlers as main, config
from .test_db import DBTestCase

def async_mock(return_value):
    f = asyncio.Future()
    f.set_result(return_value)
    return f

mock_config_: SimpleNamespace = SimpleNamespace(
    DISCORD_TOKEN = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-', k=59)),
    CURRENCY = r'tao|t|tau|Tao|Tau|𝜏',
    PROMPT = '!tip',
    BOT_ID = ''.join(random.choices([str(x) for x in range(0,9)], k=18)),
    COLDKEY_SECRET=Fernet.generate_key(),
    MONGO_URI="mongodb://taotip:pass_prod@mongodb:27017/prod?retryWrites=true&w=majority",
    MONGO_URI_TEST="mongodb://taotip:pass_test@mongodb:27017/test?retryWrites=true&w=majority",
    BAL_PROMPT="!balance|!bal",
    DEP_PROMPT=f"!deposit",
    WIT_PROMPT=f"!withdraw (5([A-z]|[0-9])+)\s+([1-9][0-9]*|0)(\.|\.[0-9]+)?\s*(<currency>|)?",
    HELP_PROMPT="!help|!h",
    MAINTAINER="@#",
    DEP_ACTIVE_TIME=600.0, # seconds
    DEPOSIT_INTERVAL=24.0, # seconds
    CHECK_ALL_INTERVAL=300.0, # seconds
    SUBTENSOR_ENDPOINT="fakeSubtensorAddr",
    TESTING=True,
    NUM_DEPOSIT_ADDRESSES=10,
    HELP_STR="To get your balance, type: `!balance` or `!bal`\n" + \
            "To deposit tao, type: `!deposit <amount>`\n" + \
            "To withdraw your tao, type: `!withdraw <address> <amount>`\n" + \
            f"For help, type: `!h` or `!help` or contact <maintainer>\n"
)
mock_config_.HELP_STR = mock_config_.HELP_STR.replace('<maintainer>', mock_config_.MAINTAINER)
mock_config_.WIT_PROMPT = mock_config_.WIT_PROMPT.replace('<currency>', mock_config_.CURRENCY)



class TestMain(DBTestCase):
    mock_config: config.Config

    def setUp(self):
        self.mock_config = config.Config(mock_config_)

    async def test_bal(self):
        bal: bittensor.Balance = bittensor.Balance.from_rao(random.randint(1, 10000000))
        user: int = random.randint(1, 10000000)
        bot_id: int = user + 1 # not the same as user
        # Insert user balance into db
        self._db.db.balances.insert_one({
            'discord_user': user,
            'balance': bal.rao
        })   

        input_str_bal = '!bal'

        mock_send = AsyncMock(
            return_value=None
        )
        mock_message = SimpleNamespace(
            content=input_str_bal,
            author=SimpleNamespace(
                id=user
            ),
            channel=MagicMock(
                spec=discord.channel.DMChannel,
                send=mock_send
            )
        )
        mock_client = MagicMock(
            spec=discord.Client,
            fetch_user=MagicMock(
                return_value=SimpleNamespace(
                    id=user
                ),
                spec=discord.Member,
            ),
            user=SimpleNamespace(
                id=bot_id
            )
        )

        mock_config = copy.deepcopy(self.mock_config)
        mock_config.BAL_PROMPT = '!bal|!balance'
        await main.on_message_(self._db, mock_client, mock_message, mock_config)
        mock_send.assert_called_once_with(f'Your balance is {bal.tao} tao')

    async def test_balance(self):
        bal: bittensor.Balance = bittensor.Balance.from_rao(random.randint(1, 10000000))
        user: int = random.randint(1, 10000000)
        bot_id: int = user + 1 # not the same as user
        # Insert user balance into db
        self._db.db.balances.insert_one({
            'discord_user': user,
            'balance': bal.rao
        })   

        input_str_bal = '!balance'

        mock_send = AsyncMock(
            return_value=None
        )
        mock_message = SimpleNamespace(
            content=input_str_bal,
            author=SimpleNamespace(
                id=user
            ),
            channel=MagicMock(
                spec=discord.channel.DMChannel,
                send=mock_send
            )
        )
        mock_client = MagicMock(
            spec=discord.Client,
            fetch_user=MagicMock(
                return_value=SimpleNamespace(
                    id=user
                ),
                spec=discord.Member,
            ),
            user=SimpleNamespace(
                id=bot_id
            )
        )

        mock_config = copy.deepcopy(self.mock_config)
        mock_config.BAL_PROMPT = '!bal|!balance'
        await main.on_message_(self._db, mock_client, mock_message, mock_config)
        mock_send.assert_called_once_with(f'Your balance is {bal.tao} tao')

    async def test_deposit(self):
        # TODO: test deposit is called with correct args
        self.assert_(False)

    async def test_withdraw(self):
        # TODO: test withdraw is called with correct args
        self.assert_(False)

    async def test_tip(self):
        user: int = random.randint(1, 10000000)
        bot_id: int = user + 1 # not the same as user
        recipient: int = user + 2 # not the same as user or bot_id
        
        input_str_tip = '!tip <@!{}> 1'.format(recipient)

        mock_send = AsyncMock(
            return_value=None
        )
        mock_message = SimpleNamespace(
            content=input_str_tip,
            author=SimpleNamespace(
                id=user
            ),
            channel=MagicMock(
                spec=discord.channel.TextChannel,
                send=mock_send
            ),
            mentions=[MagicMock(
                spec=discord.Member,
                bot=False,
                id=recipient
            )]
        )
        mock_client = MagicMock(
            spec=discord.Client,
            fetch_user=AsyncMock(
                return_value=SimpleNamespace(
                    id=user,
                    bot=False
                ),
                spec=discord.Member,
                bot=False
            ),
            user=SimpleNamespace(
                id=bot_id
            )
        )

        mock_config = copy.deepcopy(self.mock_config)             
        mock_config.PROMPT = '!tip'

        await main.on_message_(self._db, mock_client, mock_message, mock_config)
        mock_send.assert_called_once_with(f'') # Someone tipped someone...

    async def test_help(self):
        user: int = random.randint(1, 10000000)
        bot_id: int = user + 1 # not the same as user

        input_str_help = '!help'

        mock_send = AsyncMock(
            return_value=None
        )
        mock_message = SimpleNamespace(
            content=input_str_help,
            author=SimpleNamespace(
                id=user
            ),
            channel=MagicMock(
                spec=discord.channel.DMChannel,
                send=mock_send
            )
        )
        mock_client = MagicMock(
            spec=discord.Client,
            fetch_user=MagicMock(
                return_value=SimpleNamespace(
                    id=user
                ),
                spec=discord.Member,
            ),
            user=SimpleNamespace(
                id=bot_id
            )
        )

        help_str_mock = "this is a fake help string"

        mock_config = copy.deepcopy(self.mock_config)
        mock_config.HELP_PROMPT = '!help'
        mock_config.HELP_STR = help_str_mock

        await main.on_message_(self._db, mock_client, mock_message, mock_config)
        mock_send.assert_called_once_with(help_str_mock)

    async def test_check_deposit(self):
        # TODO: test check_deposit is called properly
        self.assert_(False)
    
    async def test_lock_all_addresses(self):
        # TODO: test lock_addr is called properly
        self.assert_(False)

    async def test_on_ready(self):
        # TODO: test everything is ready after on_ready
        self.assert_(False)
    