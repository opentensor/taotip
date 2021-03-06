import asyncio
import copy
import random
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Coroutine
from unittest.mock import AsyncMock, MagicMock, call, patch

import bittensor
import discord
from callee import Contains
from cryptography.fernet import Fernet

from ..src import config, db
from ..src import event_handlers as main
from .test_db import DBTestCase

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
        with patch.object(self._db, 'check_balance', return_value=bal) as mock_check_balance:
            await main.on_message_(self._db, mock_client, mock_message, mock_config)
            mock_check_balance.assert_called_once_with(user)


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
        with patch.object(self._db, 'check_balance', return_value=bal) as mock_check_balance:
            await main.on_message_(self._db, mock_client, mock_message, mock_config)
            mock_check_balance.assert_called_once_with(user)

    async def test_deposit(self):
        user_id: int = random.randint(1, 10000000)
        user: str = str(user_id)
        bot_id: str = str(user_id + 1) # not the same as user

        input_str_dep = '!deposit'

        mock_send = AsyncMock(
            return_value=None
        )
        mock_message = SimpleNamespace(
            content=input_str_dep,
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

        mock_addr_: db.Address = self._api.create_address(self.mock_config.COLDKEY_SECRET)
        mock_addr = mock_addr_.address
        dep_str_mock_1 = f"Please deposit to {mock_addr}."

        mock_config = copy.deepcopy(self.mock_config)
        mock_config.DEP_PROMPT = '!deposit'

        with patch.object(self._db, 'get_deposit_addr', return_value=mock_addr) as mock_get_dep_addr:
            await main.on_message_(self._db, mock_client, mock_message, mock_config)

            mock_get_dep_addr.assert_called_once()
            # Sends message about fees, then sends message about deposit address
            mock_send.assert_has_calls([call(unittest.mock.ANY), call(Contains(dep_str_mock_1))])

    async def test_withdraw(self):
        user_id: int = random.randint(1, 10000000)
        user: str = str(user_id)
        bot_id: str = str(user_id + 1) # not the same as user

        withd_addr = self._api.create_address(self.mock_config.COLDKEY_SECRET)
        amount: bittensor.Balance = bittensor.Balance.from_rao(random.randint(1, 10000000))
        input_str_withd = f'!withdraw {withd_addr.address} {amount.tao} tao'

        mock_send = AsyncMock(
            return_value=None
        )
        mock_message = SimpleNamespace(
            content=input_str_withd,
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
        mock_new_balance = bittensor.Balance.from_rao(random.randint(1, 2) * amount.rao) - amount

        with patch.object(db.Transaction, 'withdraw', return_value=mock_new_balance.tao) as mock_withdraw:
            await main.on_message_(self._db, mock_client, mock_message, mock_config)

            mock_withdraw.assert_called_once_with(self._db, withd_addr.address, mock_config.COLDKEY_SECRET)
            mock_send.assert_awaited_once_with(Contains(f'Your new balance is: {mock_new_balance.tao} tao'))

    async def test_tip(self):
        user: int = random.randint(1, 10000000)
        bot_id: int = user + 1 # not the same as user
        recipient: int = user + 2 # not the same as user or bot_id
        amount: bittensor.Balance = bittensor.Balance.from_rao(random.randint(1, 10000000))
        input_str_tip = f'!tip <@!{recipient}> {amount.tao}'

        mock_send = AsyncMock(
            return_value=None
        )
        mock_message = SimpleNamespace(
            content=input_str_tip,
            author=MagicMock(
                id=user,
                mention='<@!{}>'.format(user),
                spec=discord.Member
            ),
            channel=MagicMock(
                spec=discord.channel.TextChannel,
                send=mock_send
            ),
            mentions=[MagicMock(
                spec=discord.Member,
                bot=False,
                id=recipient,
                mention='<@!{}>'.format(recipient)
            )]
        )
        mock_client = MagicMock(
            spec=discord.Client,
            fetch_user=AsyncMock(
                return_value=MagicMock(
                    id=user,
                    bot=False,
                    mention='<@!{}>'.format(user),
                    spec=discord.Member
                ),
            ),
            user=SimpleNamespace(
                id=bot_id,
                bot=True,
            )
        )

        mock_tip_send = AsyncMock(
            return_value=None
        )
        mock_tip = SimpleNamespace(
            send=mock_tip_send
        )

        mock_config = copy.deepcopy(self.mock_config)             
        mock_config.PROMPT = '!tip'
        with patch.object(db.Tip, '__new__', return_value=mock_tip) as mock_tip_new:
            await main.on_message_(self._db, mock_client, mock_message, mock_config)
            mock_tip_new.assert_called_once_with(db.Tip, user, recipient, amount)
            mock_tip_send.assert_called_once() # Someone tipped someone...

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
    
    async def test_on_ready(self):
        # TODO: test everything is ready after on_ready
        self.assert_(False)
    