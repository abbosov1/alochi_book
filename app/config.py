import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_PHONE = os.getenv("ADMIN_PHONE")
WORKER_IDS = list(map(int, os.getenv("WORKER_IDS", "").split(",")))
