# Copyright (C) @Wolfy004
# Channel: https://t.me/Wolfy004

import os
from time import time
from dotenv import load_dotenv

load_dotenv("config.env")

class PyroConf:
    try:
        API_ID = int(os.getenv("API_ID", "0"))
    except ValueError:
        API_ID = 0
    
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    SESSION_STRING = os.getenv("SESSION_STRING", "")
    
    try:
        OWNER_ID = int(os.getenv("OWNER_ID", "0"))
    except ValueError:
        OWNER_ID = 0
    
    BOT_START_TIME = time()