"""config.py - reads the MySQL login details from the .env file."""

import os
from dotenv import load_dotenv

load_dotenv()   # copies the lines of .env into environment variables

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "smart_canteen"),
}
