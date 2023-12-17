import os
from typing import List
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine

if not load_dotenv():
    raise Exception('.env file not found! Please create it in src folder!')


# Переменные, связанные с БД
DB_HOST: str = os.environ.get('DB_HOST')
DB_PORT: int = int(os.environ.get('DB_PORT'))
DB_USER: str = os.environ.get('DB_USER')
DB_PASS: str = os.environ.get('DB_PASS')
DB_NAME: str = os.environ.get('DB_NAME')

# Переменные, связанные с ботом (https://my.telegram.org/auth)
BOT_API_ID: int = int(os.environ.get('BOT_API_ID'))
BOT_API_HASH: str = os.environ.get('BOT_API_HASH')
BOT_PHONE: str = os.environ.get('BOT_PHONE')

# tg id администраторов бота
ADMIN_IDS: List[int] = [int(x) for x in os.environ.get('ADMIN_IDS').split(',')]

# id основного чата с пользователями
MAIN_CHAT_ID: int = int(os.environ.get('MAIN_CHAT_ID'))

# За сколько дней до ДР должен создаваться чат
DAYS_BEFORE: int = int(os.environ.get('DAYS_BEFORE', 7))

# Сколько дней после ДР чат должен существовать
DAYS_AFTER: int = int(os.environ.get('DAYS_AFTER', 2))

engine: Engine = create_engine(f'mariadb+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
