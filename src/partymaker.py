import sys
import time
import random
from telethon.tl import types
from typing import List, Tuple
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest, EditPhotoRequest

import data
import config
from models import User
from logger import logging
from utils import signin, FindBirthday


class PartyMaker:
    """
    Отвечает за создание чата для именинника, добавление и приглашение участников
    """

    def __init__(self, client: TelegramClient, main_chat_id: int, bdayer: User):

        self.client: TelegramClient = client
        self.chat_users: List[User] = data.get_active_users()
        self.bdayer: User = bdayer
        self.bday_str: str = self.convert_birthday(bdayer.birth_day, bdayer.birth_month)

        self.chat = None
        self.channel = None
        self.invite_link: str = ''

        self.successfully_added: List[User] = []
        self.successfully_invited: List[User] = []
        self.to_sleep: int = 5  # Обязательно нужно спать между вызовами API, иначе телеграм может забанить аккаунт
        self.sleep_minmax: Tuple[int, int] = (4, 10)

        # Обязательные вызовы API
        client.get_me()
        client.get_dialogs()
        client.get_participants(main_chat_id, aggressive=True)

        logging.info('Инициализирован класс PartyMaker')

    @staticmethod
    def convert_birthday(day: int, month: int) -> str:
        """
        Конвертирует месяц и день в строку (для отображения в названии чата)

        :param day: день рождения пользователя
        :param month: месяц рождения пользователя
        :return: строка даты рождения через точку
        """

        month = str(month)
        day = str(day)

        if len(month) == 1:
            month = '0' + month
        if len(day) == 1:
            day = '0' + day

        return f'{day}.{month}'

    def create_channel_for_bdayer(self, log_to_db=True) -> int:
        """
        Создает чат канального типа для именинника и вызывает функцию log_chat_creation, которая записывает данные в БД.
        Параметр megagroup установлен на True, чтобы новые пользователи могли видеть историю сообщений.

        :return: id созданного чата
        """
        try:

            chat_title = f'ДР {self.bdayer.short_name} {self.bdayer.last_name} {self.bday_str}'
            new_channel = self.client(CreateChannelRequest(title=chat_title,
                                                           about="",
                                                           megagroup=True))

            self.channel = new_channel.chats[0]
            self.invite_link = self.client(ExportChatInviteRequest(self.channel.id)).link

            logging.info(f'Создан канал {chat_title}. ID: {self.channel.id}. Ссылка: {self.invite_link}')

            # Добавляем запись о создании чата в БД
            if log_to_db:
                data.log_chat_creation(self.channel.id, self.invite_link, self.bdayer.tg_id)
                logging.info('Данные со создании чата записаны в БД')

            return self.channel

        except Exception as e:
            exit_msg = f'Не удалось создать чат. Ошибка: {e}'
            logging.info(exit_msg)
            sys.exit(exit_msg)
        finally:
            time.sleep(self.to_sleep)

    def edit_channel_photo(self) -> None:
        """
        Меняет аватарку чата

        :return: None
        """

        file = self.client.upload_file('birthday_pic.png')
        self.client(EditPhotoRequest(self.channel.id, types.InputChatUploadedPhoto(file)))

    def send_introduction_to_channel(self, fake_link=False) -> None:
        """
        Отправляет приветственное сообщение в чат

        :return: None
        """
        try:
            if fake_link:
                money_link = 'test'
            else:
                money_link = data.get_account_link(self.channel.id)

            intro_msg = self.client.send_message(self.channel.id,
                                                 f"Всем привет! {self.bdayer.short_name} {self.bdayer.last_name} "
                                                 f"отмечает день рождения {self.bday_str}!\n\n"
                                                 "Собираем денюжку по ссылке: "
                                                 f"{money_link}\n\n"
                                                 f"P.S. просьба переводить денюжку только по ссылке"
                                                 )
            logging.info(f'В чат отправлено введение')

            # Закрепляем сообщение
            try:
                self.client.pin_message(self.channel.id, intro_msg, notify=True)

            except Exception as e:
                logging.info(f'Не удалось закрепить сообщение! Ошибка: {e}')

            time.sleep(random.uniform(*self.sleep_minmax))
            self.client.send_message(self.channel.id,
                                     f"Приглашать пользователей в чат можно по ссылке: {self.invite_link}"
                                     )
        except Exception as e:
            logging.info(f'Не удалось отправить сообщение в чат! Ошибка: {e}')

        finally:
            # Имитируем пользователя
            time.sleep(random.uniform(*self.sleep_minmax))

    def send_unable_message(self, user: User) -> None:
        """
        Отправляет сообщение пользователю, которого не удалось добавить в чат. Сообщение содержит ссылку-приглашение.

        :param user: Сущность User
        :return: None
        """

        try:
            self.client.send_message(user.tg_id,
                                     "Привет! Не получилось отравить тебе приглашение, "
                                     "потому что меня нет у тебя в контактах \U0001F622\n"
                                     f"{self.bdayer.short_name} {self.bdayer.last_name} "
                                     f"отмечает день рождения {self.bday_str}!\n\n"
                                     f"Пожалуйста, вступи в группу по ссылке:\n {self.invite_link} \n\n"
                                     "P.S. Чтобы в будущем все было окей - можешь добавить меня "
                                     "в контакты или изменить настройки приватности\n"
                                     )
            self.successfully_invited.append(user)
            logging.info(f'Пользователю {user.first_name} {user.last_name} отправлено приглашение в чат')

        except Exception as e:
            logging.info(f'Не удалось отправить приглашение пользователю. {user} Ошибка: {e}')

        finally:
            time.sleep(self.to_sleep)

    def make_invite_list(self) -> List[User]:
        """
        Создает список пользователей, которых нужно пригласить в чат (исключая именинника)

        :return: список пользователей
        """
        invite_list = []
        for user in self.chat_users:
            if user.is_active:
                if user.tg_id != self.bdayer.tg_id:
                    invite_list.append(user)

        return invite_list

    def invite_admins(self) -> None:
        """
        Добавляет пользователей в чат, если позволяют их настройки приватности.
        Если добавить пользователя не удалось, ему отправляется ссылка с приглашением в личные сообщения

        :return: None
        """

        for admin_id in config.ADMIN_IDS:
            if admin_id != self.bdayer.tg_id:
                try:
                    self.client(InviteToChannelRequest(self.channel.id, [admin_id]))
                    logging.info(f'Успешно добавлен админ. tgid: {admin_id}')

                except Exception as e:
                    logging.info(e, f'Не удалось пригласить админа. tgid: {admin_id}')

                finally:
                    time.sleep(self.to_sleep)

    def grant_channel_admin_rights(self) -> None:
        """
        Выдает права администратора чата

        :return: None
        """
        for admin_id in config.ADMIN_IDS:
            if admin_id != self.bdayer.tg_id:
                self.client.edit_admin(self.channel.id, admin_id, is_admin=True, anonymous=False, title='друг собаки')
                logging.info(f'Пользователю {admin_id} выданы права администратора')

    def invite_users_to_channel(self, send_invites=True) -> None:
        """
        Добавляет пользователей в чат, если позволяют их настройки приватности.
        Если добавить пользователя не удалось, ему отправляется ссылка с приглашением в личные сообщения

        :type send_invites: Флаг, указывающий на то, отправляются ли пользователям приглашения
        :return: None
        """

        invite_list = self.make_invite_list()
        for num, user in enumerate(invite_list, start=1):

            try:

                self.client(InviteToChannelRequest(self.channel.id, [user.tg_id]))
                self.successfully_added.append(user)
                logging.info(f'Успешно добавлен {user.first_name} {user.tg_id} {num}/{len(invite_list)}')

            # TODO: Обработать FloodWaitError и UserChannelsTooMuchError
            except Exception as e:
                logging.info(e, f'Не удалось пригласить пользователя {user.first_name}. tgid: {user.tg_id}')
                if send_invites:
                    self.send_unable_message(user)

            finally:
                data.log_added_invited(self.channel.id, len(self.successfully_added), len(self.successfully_invited))
                time.sleep(random.uniform(*self.sleep_minmax))

    def make_party(self) -> None:
        self.create_channel_for_bdayer()
        self.edit_channel_photo()
        self.invite_admins()
        self.grant_channel_admin_rights()

        time.sleep(10)
        self.invite_users_to_channel()
        self.send_introduction_to_channel()


if __name__ == '__main__':
    dog_client = signin(config.BOT_API_ID, config.BOT_API_HASH)

    with dog_client:
        chat_id = config.MAIN_CHAT_ID
        users = data.get_active_users()

        fb = FindBirthday(users)
        birthday_users = fb.birthday_users

        bday_user = birthday_users[0]
        print('Bday User: ', bday_user)

        pm = PartyMaker(dog_client, chat_id, bday_user)
        pm.make_party()

    sys.exit(0)
