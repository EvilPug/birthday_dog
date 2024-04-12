import random
import sys
import time
from typing import List, Tuple

from telethon.sync import TelegramClient
from telethon.tl import types
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    InviteToChannelRequest,
    EditPhotoRequest,
)
from telethon.tl.functions.messages import ExportChatInviteRequest

import config
import data
from logger import logging
from models import User
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
        self.invite_link: str = ""

        self.successfully_added: List[User] = []
        self.successfully_invited: List[User] = []
        self.to_sleep: int = (
            5  # Обязательно нужно спать между вызовами API, иначе телеграм может забанить аккаунт
        )
        self.sleep_minmax: Tuple[int, int] = (4, 10)

        # Обязательные вызовы API
        client.get_me()
        client.get_dialogs()
        client.get_participants(main_chat_id, aggressive=True)

        logging.info("Инициализирован класс PartyMaker")

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
            month = "0" + month
        if len(day) == 1:
            day = "0" + day

        return f"{day}.{month}"

    def create_channel_for_bdayer(self, log_to_db=True) -> int:
        """
        Создает чат канального типа для именинника и вызывает функцию log_chat_creation, которая записывает данные в БД.
        Параметр megagroup установлен на True, чтобы новые пользователи могли видеть историю сообщений.

        :return: id созданного чата
        """
        try:

            chat_title = (
                f"ДР {self.bdayer.short_name} {self.bdayer.last_name} {self.bday_str}"
            )
            new_channel = self.client(
                CreateChannelRequest(title=chat_title, about="", megagroup=True)
            )

            self.channel = new_channel.chats[0]
            self.invite_link = self.client(
                ExportChatInviteRequest(self.channel.id)
            ).link

            logging.info(
                f"Создан канал {chat_title}. ID: {self.channel.id}. Ссылка: {self.invite_link}"
            )

            # Добавляем запись о создании чата в БД
            if log_to_db:
                data.log_chat_creation(
                    self.channel.id, self.invite_link, self.bdayer.tg_id
                )
                logging.info("Данные со создании чата записаны в БД")

            return self.channel

        except Exception as e:
            exit_msg = f"Не удалось создать чат. Ошибка: {e}"
            logging.info(exit_msg)
            sys.exit(exit_msg)
        finally:
            time.sleep(self.to_sleep)

    def edit_channel_photo(self) -> None:
        """
        Меняет аватарку чата

        :return: None
        """

        file = self.client.upload_file("birthday_pic.png")
        self.client(
            EditPhotoRequest(self.channel.id, types.InputChatUploadedPhoto(file))
        )

    def send_introduction_to_channel(self, fake_link=False) -> None:
        """
        Отправляет приветственное сообщение в чат

        :return: None
        """
        try:
            if fake_link:
                money_link = "test"
            else:
                money_link = data.get_account_link(self.channel.id)

            intro_text = (
                f"Всем привет! {self.bdayer.short_name} {self.bdayer.last_name}"
                f"отмечает день рождения {self.bday_str}!\n\n"
                f"Собираем денюжку по ссылке: {money_link}\n\n"
                "Если у вас проблемы с переводом по ссылке,"
                "можно перевести по номеру карты:\n"
                f"{config.CARD_NUMBER}\n"
                "(Обязательно указывайте именинника в комментариях к платежу)"
            )

            intro_msg = self.client.send_message(self.channel.id, intro_text)

            # Закрепляем сообщение
            try:
                self.client.pin_message(self.channel.id, intro_msg, notify=True)

            except Exception as e:
                logging.info(f"Не удалось закрепить сообщение! Ошибка: {e}")

            time.sleep(random.uniform(*self.sleep_minmax))
            self.client.send_message(
                self.channel.id,
                f"Приглашать пользователей в чат "
                f"можно по ссылке: {self.invite_link}",
            )
            logging.info("В чат отправлено введение")
        except Exception as e:
            logging.info(f"Не удалось отправить сообщение в чат! Ошибка: {e}")

        finally:
            # Имитируем пользователя
            time.sleep(random.uniform(*self.sleep_minmax))

    def send_unable_message(self, user: User) -> None:
        """
        Отправляет сообщение пользователю, которого не удалось добавить в чат. Сообщение содержит ссылку-приглашение.

        :param user: Сущность User
        :return: None
        """

        unable_message = (
            "Привет! Не получилось отравить тебе приглашение, "
            "потому что меня нет у тебя в контактах \U0001F622\n"
            f"{self.bdayer.short_name} {self.bdayer.last_name} "
            f"отмечает день рождения {self.bday_str}!\n\n"
            f"Пожалуйста, вступи в группу по ссылке:\n {self.invite_link} \n\n"
            "P.S. Чтобы в будущем все было окей - можешь добавить меня "
            "в контакты или изменить настройки приватности\n"
        )

        try:
            self.client.send_message(user.tg_id, unable_message)
            self.successfully_invited.append(user)
            logging.info(
                f"Пользователю {user.short_name} {user.last_name} отправлено приглашение в чат"
            )

        except Exception as e:
            logging.info(
                f"Не удалось отправить приглашение пользователю. {user} Ошибка: {e}"
            )

        finally:
            time.sleep(self.to_sleep)

    def make_invite_list(self) -> List[User]:
        """
        Создает список пользователей, которых нужно пригласить в чат (исключая именинника)

        :return: список пользователей
        """

        logging.info("Формируем список пользователей, которых необходимо пригласить.")

        invite_list = []
        for user in self.chat_users:
            if user.is_active:
                if user.tg_id != self.bdayer.tg_id:
                    if user.tg_id not in config.ADMIN_IDS:
                        invite_list.append(user)

        logging.info(
            f"Список сформирован. Количество приглашенных (исколючая админов): {len(invite_list)}"
        )
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
                    logging.info(f"Успешно добавлен админ. tgid: {admin_id}")

                except Exception as e:
                    logging.info(f"{e}. Не удалось пригласить админа. tgid: {admin_id}")

                finally:
                    time.sleep(self.to_sleep)

    def grant_channel_admin_rights(self) -> None:
        """
        Выдает права администратора чата

        :return: None
        """
        for admin_id in config.ADMIN_IDS:
            if admin_id != self.bdayer.tg_id:
                self.client.edit_admin(
                    self.channel.id,
                    admin_id,
                    is_admin=True,
                    anonymous=False,
                    title="друг собаки",
                )
                logging.info(f"Пользователю {admin_id} выданы права администратора")

    def invite_users_to_channel(self, send_invites=False) -> None:
        """
        Добавляет пользователей в чат, если позволяют их настройки приватности.
        Если добавить пользователя не удалось, ему отправляется ссылка с приглашением в ЛС

        :type send_invites: Флаг, указывающий на то, отправляются ли пользователям приглашения
        :return: None
        """

        invite_list = self.make_invite_list()
        for num, user in enumerate(invite_list, start=1):

            try:

                self.client(InviteToChannelRequest(self.channel.id, [user.tg_id]))
                self.successfully_added.append(user)
                logging.info(
                    f"Успешно добавлен {user.short_name} {user.tg_id} {num}/{len(invite_list)}"
                )

            # TODO: Обработать FloodWaitError и UserChannelsTooMuchError
            except Exception as e:
                logging.info(
                    f"{e}. Не удалось пригласить пользователя {user.short_name}. tgid: {user.tg_id}"
                )

                if send_invites:
                    self.send_unable_message(user)

            finally:
                data.log_added_invited(
                    self.channel.id,
                    len(self.successfully_added),
                    len(self.successfully_invited),
                )
                time.sleep(random.uniform(*self.sleep_minmax))

    def make_party(self) -> None:
        self.create_channel_for_bdayer()
        self.edit_channel_photo()
        self.invite_admins()
        self.grant_channel_admin_rights()

        time.sleep(10)
        self.invite_users_to_channel()
        self.send_introduction_to_channel()


if __name__ == "__main__":
    dog_client = signin(config.BOT_API_ID, config.BOT_API_HASH)

    with dog_client:
        chat_id = config.MAIN_CHAT_ID
        users = data.get_active_users()

        fb = FindBirthday(users)
        birthday_users = fb.birthday_users

        if len(birthday_users) != 0:
            bday_user: User = birthday_users[0]
            logging.info(f"Именинник: {bday_user}")

            pm = PartyMaker(dog_client, chat_id, bday_user)
            pm.make_party()
        else:
            logging.info("Нет именинников!")

    sys.exit(0)
