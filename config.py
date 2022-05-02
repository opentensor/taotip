DISCORD_TOKEN = ''
CURRENCY = r'tao|t|tau|Tao|Tau|𝜏'
PROMPT = '!tip'
MONGO_URI="mongodb://taotip:prod_pass@mongodb_container:27017/prod?retryWrites=true&w=majority"
MONGO_URI_TEST="mongodb://taotip:taotip@mongodb_container:27017/test?retryWrites=true&w=majority"
BAL_PROMPT="(!balance)|(!bal)"
DEP_PROMPT=f"!deposit ([1-9][0-9]*|0)(\.|\.[0-9]+)?\s*({CURRENCY}|)?"
WIT_PROMPT=f"!withdraw (5([A-z]|[0-9])+)\s+([1-9][0-9]*|0)(\.|\.[0-9]+)?\s*({CURRENCY}|)?"
HELP_PROMPT="(!help)|(!h)"
MAINTAINER="@#"
DEP_ACTIVE_TIME=600.0 # seconds
DEPOSIT_INTERVAL=24.0 # seconds
CHECK_ALL_INTERVAL=300.0 # seconds
SUBTENSOR_ENDPOINT="<>:9944"
TESTING=True
NUM_DEPOSIT_ADDRESSES=10
HELP_STR="To get your balance, type: `!balance` or `!bal`\n" + \
        "To deposit tao, type: `!deposit <amount>`\n" + \
        "To withdraw your tao, type: `!withdraw <address> <amount>`\n" + \
        f"For help, type: `!h` or `!help` or contact {MAINTAINER}\n"
