import sys
import time
from typing import List
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import DeleteChannelRequest, GetChannelsRequest
from telethon.errors.rpcerrorlist import ChannelPrivateError
from telethon.tl.types import PeerChannel

import data
import config
from models import Chat
from logger import logging
from utils import signin, FindBirthday


class PartyCleaner:
    """
    Ищет чаты, которые необходимо удалить по прошествию дня рождения
    """

    def __init__(self, client):
        self.client: TelegramClient = client
        self.active_chats = data.get_active_chats()

        logging.info('Инициализирован класс PartyCleaner')

    def delete_channel(self, channel_id) -> None:
        """
        Удаляет указанный канал в телеграме

        :param channel_id: id канала
        :return: None
        """
        try:
            channel = self.client.get_entity(PeerChannel(channel_id))
            self.client(DeleteChannelRequest(channel_id))
            logging.info(f'Удален канал в телеграме {channel.title}')
        except ChannelPrivateError:
            logging.info('Похоже, что канал в телеграме был удален вручную')

    def send_channel_notification(self, channel_id) -> None:
        """
        Отправляет уведомление о том, что канал скоро будет удален

        :param channel_id: id канала
        :return: None
        """
        channel = self.client.get_entity(channel_id)
        self.client.send_message(channel_id,
                                 "Внимание!\n"
                                 "Ссылка для сбора более не активна! Просьба не отправлять по ней деньги.")
        logging.info(f'В чат канала {channel.title} отправлено предупреждение об удалении')

    def get_channels_to_clean(self) -> List[Chat]:
        """
        Получает список чатов, которые устарели

        :return: список экземпляров чатов
        """

        chats_to_clean = []
        for chat in self.active_chats:
            bdayer = data.get_chat_bdayer(chat.chat_id)
            in_birthday_interval = FindBirthday.check_birthday(bdayer.birth_month, bdayer.birth_day)

            if not in_birthday_interval:
                chats_to_clean.append(chat)
        return chats_to_clean

    def clean_party(self) -> None:
        """
        Вызывает все методы для уборки после ДР
        """
        channels_to_clean = self.get_channels_to_clean()

        if len(channels_to_clean) == 0:
            logging.info('Нет чатов для очистки')
            return

        for channel in channels_to_clean:
            self.delete_channel(channel.chat_id)
            data.deactivate_chat(channel.chat_id)

            chat_info = self.client.get_entity(channel.chat_id)
            logging.info(f'Деактивирован канал в БД {chat_info.title}')
            time.sleep(10)
        return


if __name__ == '__main__':
    dog_client = signin(config.BOT_API_ID, config.BOT_API_HASH)

    with dog_client:
        pc = PartyCleaner(dog_client)
        pc.clean_party()

    sys.exit(0)
