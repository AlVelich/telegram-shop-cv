import os
from dotenv import load_dotenv
import json

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
YOUR_SECRET_KEY = os.getenv('YOUR_SECRET_KEY')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
GAMES = json.loads(os.getenv('GAMES'))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment")
if not YOUR_SECRET_KEY:
    raise ValueError("YOUR_SECRET_KEY is not set in the environment")
if not DB_USER or not DB_PASSWORD or not DB_NAME or not DB_HOST or not DB_PORT:
    raise ValueError("Database configuration is not set in the environment")
if not GAMES:
    raise ValueError("GAMES is not set in the environment")
