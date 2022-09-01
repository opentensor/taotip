import copy
import random
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import bittensor
import interactions
from callee import Contains
from cryptography.fernet import Fernet

from taotip.src import config, db
from taotip.src import event_handlers as main
from taotip.test.test_db import DBTestCase

mock_config_: SimpleNamespace = SimpleNamespace(
    DISCORD_TOKEN = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-', k=59)),
    CURRENCY = r'tao|t|tau|Tao|Tau|𝜏',
    PROMPT = '!tip',
    BOT_ID = ''.join(random.choices([str(x) for x in range(0,9)], k=18)),
    COLDKEY_SECRET=Fernet.generate_key(),
    MONGO_URI="mongodb://taotip:pass_prod@mongodb:27017/prod?retryWrites=true&w=majority",
    MONGO_URI_TEST="mongodb://taotip:pass_test@mongodb:27017/test?retryWrites=true&w=majority",
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


class TestMain(DBTestCase):
    mock_config: config.Config

    def setUp(self):
        self.mock_config = config.Config(mock_config_)

    async def test_do_balance_check(self):
        bal: bittensor.Balance = bittensor.Balance.from_rao(random.randint(1, 10000000))
        user: int = random.randint(1, 10000000)
        bot_id: str = str(user + 1) # not the same as user

        # Insert user balance into db
        self._db.db.balances.insert_one({
            'discord_user': user,
            'balance': bal.rao
        })   

        mock_user = MagicMock(
            spec=interactions.User,
            id=user,
            bot=False,  
        )

        mock_ctx = MagicMock(
            spec=interactions.CommandContext,
            author=SimpleNamespace(
                id=user,
                bot=False,
                user=mock_user,
            ),
            channel=MagicMock(
                spec=interactions.Channel,
                type=interactions.ChannelType.DM, # checking balance in DM
            ),
            send=AsyncMock(
                return_value=None
            ),
            application_id=bot_id,
        )

        with patch.object(self._db, 'check_balance', return_value=bal) as mock_check_balance:
            await main.do_balance_check(self.mock_config, self._db, mock_ctx, mock_user)
            mock_check_balance.assert_called_once_with(user)

    async def test_do_deposit(self):
        user_id: int = random.randint(1, 10000000)
        user: str = str(user_id)
        bot_id: str = str(user_id + 1) # not the same as user


        mock_send = AsyncMock(
            return_value=None
        )

        mock_user = MagicMock(
            spec=interactions.User,
            id=user,
            bot=False,  
        )

        mock_ctx = MagicMock(
            spec=interactions.CommandContext,
            author=SimpleNamespace(
                id=user,
                bot=False,
                user=mock_user,
            ),
            channel=MagicMock(
                spec=interactions.Channel,
                type=interactions.ChannelType.DM, # checking balance in DM
            ),
            send=mock_send,
            application_id=bot_id,
        )

        mock_addr_: db.Address = self._api.create_address(self.mock_config.COLDKEY_SECRET)
        mock_addr = mock_addr_.address
        dep_str_mock_1 = f"Please deposit to {mock_addr}."

        mock_config = copy.deepcopy(self.mock_config)
        mock_config.DEP_PROMPT = '!deposit'

        with patch.object(self._db, 'get_deposit_addr', return_value=mock_addr) as mock_get_dep_addr:
            await main.do_deposit(self.mock_config, self._db, mock_ctx, mock_user)
        
            mock_get_dep_addr.assert_called_once()
            # Sends message about fees, then sends message about deposit address
            mock_send.assert_has_calls([call(unittest.mock.ANY), call(Contains(dep_str_mock_1))])

    async def test_do_withdraw(self):
        user_id: int = random.randint(1, 10000000)
        user: str = str(user_id)
        bot_id: str = str(user_id + 1) # not the same as user

        withd_addr = self._api.create_address(self.mock_config.COLDKEY_SECRET)
        amount: bittensor.Balance = bittensor.Balance.from_rao(random.randint(1, 10000000))

        mock_send = AsyncMock(
            return_value=None
        )

        mock_user = MagicMock(
            spec=interactions.User,
            id=user,
            bot=False,  
        )

        mock_ctx = MagicMock(
            spec=interactions.CommandContext,
            author=SimpleNamespace(
                id=user,
                bot=False,
                user=mock_user,
            ),
            channel=MagicMock(
                spec=interactions.Channel,
                type=interactions.ChannelType.DM, # checking balance in DM
            ),
            send=mock_send,
            application_id=bot_id,
        )

        mock_config = copy.deepcopy(self.mock_config)
        mock_new_balance = bittensor.Balance.from_rao(random.randint(1, 2) * amount.rao) - amount

        with patch.object(db.Transaction, 'withdraw', return_value=mock_new_balance.tao) as mock_withdraw:
            await main.do_withdraw(mock_config, self._db, mock_ctx, mock_user, withd_addr.address, amount)

            mock_withdraw.assert_called_once_with(self._db, withd_addr.address, mock_config.COLDKEY_SECRET)
            mock_send.assert_awaited_once_with(Contains(f'Your new balance is: {mock_new_balance.tao} tao'))

    async def test_tip_user(self):
        user: int = random.randint(1, 10000000)
        bot_id: int = user + 1 # not the same as user
        recipient: int = user + 2 # not the same as user or bot_id
        amount: bittensor.Balance = bittensor.Balance.from_rao(random.randint(1, 10000000))

        mock_send = AsyncMock(
            return_value=None
        )
        mock_user_send = AsyncMock(
            return_value=None
        )

        mock_user = MagicMock(
            spec=interactions.User,
            id=user,
            bot=False,  
            send=mock_user_send
        )

        mock_sender = MagicMock(
            spec=interactions.Member,
            id=user,
            bot=False,
            user=mock_user,
        )

        mock_ctx = MagicMock(
            spec=interactions.CommandContext,
            author=SimpleNamespace(
                id=user,
                bot=False,
                user=mock_user,
                send=mock_send,
            ),
            channel=MagicMock(
                spec=interactions.Channel,
                type=interactions.ChannelType.DM, # checking balance in DM
            ),
            application_id=bot_id,
        )

        mock_recipient = MagicMock(
            spec=interactions.User,
            id=recipient,
            bot=False,
        )

        mock_tip_send = AsyncMock(
            return_value=True # successful tip
        )
        mock_tip = SimpleNamespace(
            send=mock_tip_send
        )

        mock_client = MagicMock(
            spec=interactions.Client,
            get=AsyncMock(
                return_value=mock_sender,
            ),
        )
            

        with patch.object(db.Tip, '__new__', return_value=mock_tip) as mock_tip_new:
            await main.tip_user(self.mock_config, self._db, mock_client, mock_ctx, mock_user, mock_recipient, amount)
            mock_tip_new.assert_called_once_with(db.Tip, user, recipient, amount)
            mock_tip_send.assert_called_once() # Someone tipped someone...
            
            mock_user_send.assert_not_called() # no error message
    