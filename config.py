DISCORD_TOKEN = '<>'
PROMPT = '!tip'
COLDKEY_SECRET=b'<secret>'
MONGO_URI="mongodb+srv://<>"
BAL_PROMPT="(!balance)|(!bal)"
DEP_PROMPT="!deposit ([1-9][0-9]*|)((0|)\.[0-9]+)?"
WIT_PROMPT="!withdraw (5([A-z]|[0-9])+) ([1-9][0-9]*|)((0|)\.[0-9]+)?"
HELP_PROMPT="(!help)|(!h)"
MAINTAINER="@<>#<>"
DEP_ACTIVE_TIME=17200.0 # seconds
DEPOSIT_INTERVAL=60.0 # seconds
CHECK_ALL_INTERVAL=600.0 # seconds
SUBTENSOR_ENDPOINT="<>:9944"
TESTING=False
NUM_DEPOSIT_ADDRESSES=10
HELP_STR="To get your balance, type: `!balance` or `!bal`\n" + \
        "To deposit tao, type: `!deposit <amount>`\n" + \
        "To withdraw your tao, type: `!withdraw <address> <amount>`\n" + \
        f"For help, type: `!h` or `!help` or contact {MAINTAINER}\n"
