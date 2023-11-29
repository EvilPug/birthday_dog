from typing import List
from telethon.sync import TelegramClient

import data
import config
from models import User
from partymaker import PartyMaker
from partycleaner import PartyCleaner
from utils import FindBirthday, ChatTools, signin


def main(chat_users: List[User], client: TelegramClient):

    # Вычисляем именников
    fb = FindBirthday(chat_users)
    birthday_users = fb.birthday_users

    chat_id = config.MAIN_CHAT_ID

    # Удаляем устаревшие чаты
    pc = PartyCleaner(client)
    pc.clean_party()

    # В день должно создаваться не больше одного чата. Во избежание бана от телеграма
    bday_user = birthday_users[0]
    print('Bday User: ', bday_user)
    
    # Мероприятия по созданию чата
    pm = PartyMaker(client, chat_id, bday_user)
    pm.make_party()


if __name__ == '__main__':
    dog_client = signin(config.BOT_API_ID, config.BOT_API_HASH)

    with dog_client:

        ct = ChatTools(dog_client, config.MAIN_CHAT_ID)
        ct.find_db_users_not_in_chat()  # Ищем пользователей в БД, но не в чате
        ct.find_chat_users_not_in_db()  # Ищем пользователей в чате, но не в БД

        users = data.get_active_users()
        main(users, dog_client)
