# Copyright (C) @Wolfy004
# Channel: https://t.me/Wolfy004

from os import getenv
from time import time
from dotenv import load_dotenv

try:
    load_dotenv("config.env")
except:
    pass

if getenv("BOT_TOKEN"):
    if not getenv("BOT_TOKEN").count(":") == 1:
        print("Error: BOT_TOKEN must be in format '123456:abcdefghijklmnopqrstuvwxyz'")
        exit(1)

    if (
        not getenv("SESSION_STRING")
        or getenv("SESSION_STRING") == "xxxxxxxxxxxxxxxxxxxxxxx"
    ):
        print("Error: SESSION_STRING must be set with a valid string")
        exit(1)


# Pyrogram setup
class PyroConf(object):
    API_ID = int(getenv("API_ID", "9813287"))
    API_HASH = getenv("API_HASH", "b5de20c46fb8f2e1b4aa393dea1ffe03")
    BOT_TOKEN = getenv("8035218066:AAHNY7-DBy5NB1p3AkKn0hIGHHpgaOk6xDU")
    SESSION_STRING = getenv("BQCVvScAYA94rc11vGFR23oycpOumWiIbFg8brudPMcJbuQNybNO87FVlsptxV5OMSAyastDYI6R59QmsY48Bk5F6aGtDA8FvhBq72bP2JeHhU1rhivdaB3_QyAstPJntQmZph81aeHTqVcISDnBLbgqx4tTDach6cKaBXQ-xEmgCtre5MWB1VPGsjrlsi-I84g5TU0cDqLV-cv-V9Y1NUtl9RBj4vozZGYbZy0v_NOC6BkOfc0sY4QgbNYD9huRxNMgqA7ZQYjXbfWnL_sDpy97qNDptdAVzGknsH-56gWEDo_1IBeDkkp9vzyqiswNKNsWoubUwMNOvi3yVGP2x8GMUc39XQAAAAGzRo5JAA")
    OWNER_ID = int(getenv("OWNER_ID", "7302712905")) if getenv("OWNER_ID") else None
    BOT_START_TIME = time()
