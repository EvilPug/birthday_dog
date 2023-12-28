import pandas as pd
from typing import List
from datetime import datetime
from telethon.sync import TelegramClient

import data
import config
from models import User
from logger import logging


def signin(bot_api_id: int, bot_api_hash: str) -> TelegramClient:
    client = TelegramClient('bot', bot_api_id, bot_api_hash)
    client.connect()
    if not client.is_user_authorized():
        client.send_code_request(config.BOT_PHONE)
        client.sign_in(config.BOT_PHONE, input('Введите код: '))

    return client


class FindBirthday:
    """
    Отвечает за поиск потенциальных именинников в списке пользователей
    """

    def __init__(self, user_list: List[User]):
        self.user_list = user_list
        self.birthday_users = []

        self.get_birthday_users()

    def get_birthday_users(self) -> List[User]:
        """
        Выполняет проверки на именинников

        :return: список именинников
        """
        logging.info('Ищем пользователей, у которых скоро день рождения')

        for user in self.user_list:
            try:
                if user.is_active:
                    assert self.check_birthday(user.birth_month, user.birth_day)
                    assert self.check_chat_not_created(user.tg_id)
                    self.birthday_users.append(user)
                else:
                    logging.info('Not Active User: {user}')
            except AssertionError:
                continue
        return self.birthday_users

    @staticmethod
    def check_birthday(birth_month: int, birth_day: int,
                       before=config.DAYS_BEFORE, after=config.DAYS_AFTER) -> bool:
        """
        Получает на вход день рождения и проверяет, должен ли существовать чат

        :param birth_day: Календарный день рождения пользователя.
        :param birth_month: Календарный месяц рождения пользователя.
        :param before: За сколько дней до дня рождения должен создаваться чат.
        :param after: Сколько дней после ДР должен существовать чат.
        Внимание: при повышении значения может появиться нехватка счетов для сбора.
        :return: True - если чат пора создавать, False - если нет.
        """

        today = pd.Timestamp(datetime.now())

        bdate = pd.Timestamp(today.year, birth_month, birth_day)
        chat_creation_date = bdate - pd.DateOffset(before)

        # Обработка дней рождения созадваемых в конце декабря на следующий год
        if chat_creation_date.year != today.year:
            bdate = pd.Timestamp(today.year+1, birth_month, birth_day)

        bday_interval = pd.Interval(bdate - pd.DateOffset(before), bdate + pd.DateOffset(after), closed='right')
        return True if today in bday_interval else False

    @staticmethod
    def check_chat_not_created(user_id: int):
        """
        Проверяет, есть ли созданные чаты для именинника

        :param user_id: tgid именинника.
        :return: True/False
        """
        chats = data.get_active_chats_for_user(user_id)
        return True if len(chats) == 0 else False


class ChatTools:

    def __init__(self, client: TelegramClient, chat_id: int):
        self.client = client
        self.dog_tg_id = self.client.get_me()

        self.users_in_db = data.get_active_users()
        self.users_in_db_ids = [x.tg_id for x in self.users_in_db]

        self.users_in_chat = [u for u in client.get_participants(chat_id, aggressive=True) if u.id != self.dog_tg_id]
        self.users_in_chat_ids = [x.id for x in self.users_in_chat]

    def find_db_users_not_in_chat(self) -> List[User]:
        """
        Находит пользователей, которые есть в БД, но отсутствуют в чате.

        :return: Список tg_id пользователей
        """
        not_in_chat_ids = list(set(self.users_in_db_ids).difference(self.users_in_chat_ids))
        users = [u for u in self.users_in_db if u.tg_id in not_in_chat_ids]
        logging.info(f'Найдены активные пользователи не состоящие в чате: {users}', )
        return users

    def find_chat_users_not_in_db(self) -> list:
        """
        Находит пользователей, которые есть в чате, но отсутствуют в БД.

        :return: Список tg_id пользователей
        """
        not_in_db_ids = list(set(self.users_in_chat_ids).difference(self.users_in_db_ids))
        users = [u for u in self.users_in_chat if u.id in not_in_db_ids]

        users_info = [(i.id, i.username, i.short_name, i.last_name) for i in users]
        logging.info(f'Найдены пользователи чата, не добавленные в БД: {users_info}', )
        return users

    def remove_users_from_db(self):
        """
        Удаляет из БД пользователей, которые покинули чат ЦПУ

        :return: None
        """

        users_to_remove = self.find_db_users_not_in_chat()
        for user in users_to_remove:

            try:
                data.deactivate_user(user.tg_id)

                # Оповещаем администраторов об удаленном пользователе
                for tg_id in config.ADMIN_IDS:
                    self.client.send_message(tg_id, f'Удален пользователь {user.short_name} {user.last_name}'
                                                    f', так как он покинул чат ЦПУ')

            except Exception as e:
                # Оповещаем администраторов об ошибке
                for tg_id in config.ADMIN_IDS:
                    self.client.send_message(tg_id,
                                             f'Не удалось удалить пользователя {user.short_name} {user.last_name}\n'
                                             f'Ошибка: {e}')

    def notify_about_new_users(self):
        """
        Уведомить администраторов о новых пользователях, чтобы они добавили их ФИО и ДР в БД

        :return: None
        """
        new_users = self.find_chat_users_not_in_db()

        for user in new_users:
            for tg_id in config.ADMIN_IDS:
                self.client.send_message(tg_id, f'Новый пользователь в чате: {user.short_name} {user.last_name}\n\n'
                                                f'Пожалуйста, добавьте его ФИО и ДР')
