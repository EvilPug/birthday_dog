from typing import List, Union
from sqlalchemy import select, exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import NoResultFound

from config import engine
from logger import logging
from models import User, Chat, Account


def make_session() -> sessionmaker:
    """
    Генератор сессий

    :return: неинициализированная сущность sessionmaker
    """
    return sessionmaker(engine)


def get_active_chats() -> List[Chat]:

    s = make_session()
    with s() as session:
        chats = session.query(Chat).filter(Chat.is_active == True).all()
        return chats


def deactivate_chat(chat_id) -> Chat:
    """
    Вызывается сразу после удаления чата ботом и отмечает его как неактивный.
    Очищает поле used_in в accounts и делает счет доступным для других чатов

    :param chat_id: id чата/канала
    :return: сущность Chat
    """

    s = make_session()
    with s() as session:
        chat = session.execute(select(Chat).filter_by(chat_id=chat_id)).scalar_one()
        chat.is_active = False

        try:
            account = session.execute(select(Account).filter_by(used_in=chat_id)).scalar_one()
            account.used_in = None

            session.commit()
            return chat

        except NoResultFound:
            return chat


def get_chat_bdayer(chat_id: int) -> Union[User, None]:
    """
    Получает на вход id чата и возвращает объект User - именинника, для которого чат был создан

    :param chat_id: id чата/канала
    :return: User-object именинника
    """

    s = make_session()
    with s() as session:
        chat = session.execute(select(Chat).filter_by(chat_id=chat_id)).first()
        if chat:
            user = session.execute(select(User).filter_by(tg_id=chat[0].bdayer_id)).first()
            if user:
                return user[0]

        return None


def get_active_chats_for_user(user_id) -> List[Chat]:
    """
    Проверяет, если активные чаты для пользователя

    :param user_id: id пользователя
    :return: список сущностей чатов
    """

    s = make_session()
    with s() as session:
        chats = session.query(Chat).filter(Chat.bdayer_id == user_id,
                                           Chat.is_active == True).all()

        return chats


def log_chat_creation(chat_id, invite_link, bdayer_id) -> Chat:

    """
    Добавляет в таблицу chats запись о созданном чате

    :param chat_id: id чата/канала
    :param invite_link: ссылка для приглашения пользователей
    :param bdayer_id: id именинника, для которого был создан чат
    :return: сущность Chat
    """

    s = make_session()
    with s() as session:

        chat = Chat(chat_id=chat_id, invite_link=invite_link, bdayer_id=bdayer_id)
        session.add(chat)
        session.commit()

        logging.info(f'Запись о создании чата добавлена в таблицу. Чат: {chat}')
        return chat


def log_added_invited(chat_id: int, added: int, invited: int) -> Chat:

    """
    Добавляет к существующей записи количество добавленных и приглашенных людей

    :param chat_id: id чата, для которого нужно записать статистику
    :param added: люди, добавленные в чат напрямую
    :param invited: люди, которым было выслано приглашение в чат в виде ссылки
    :return: сущность Chat
    """

    s = make_session()
    with s() as session:
        chat = session.execute(select(Chat).filter_by(chat_id=chat_id)).scalar_one()
        chat.users_added = added
        chat.users_invited = invited
        session.commit()

        logging.info(f'Инфо о добавленных и приглашенных в чат добавлено в БД. Чат: {chat}')
        return chat


def get_user(tg_id) -> Union[User, None]:
    """
    Получить пользователя из БД по tg_id

    :return: User-объект, если пользователь существует, None - если нет
    """

    s = make_session()
    with s() as session:

        try:
            return session.execute(select(User).filter_by(tg_id=tg_id)).scalar_one()
        except exc.NoResultFound:
            return None


def get_all_users() -> List[User]:

    """
    Получить всех пользователей из таблицы users
    Список отсортирован по месяцу и дню рождения

    :return:
    """

    s = make_session()
    with s() as session:
        users = session.query(User).order_by(User.birth_month, User.birth_day).all()
        return users


def get_active_users() -> List[User]:

    """
    Получить всех пользователей из таблицы users

    :return:
    """

    s = make_session()
    with s() as session:
        users = session.query(User).filter(User.is_active == True).all()
        return users


def get_account_link(chat_id) -> str:
    """
    Проверяет, закреплен ли за чатом банковский счет. Если нет - закрепляет один из свободных.

    :raises RuntimeError: ошибка при отсутствии свободных счетов.
    :return: ссылка на счет
    """

    s = make_session()
    with s() as session:

        try:
            existing_account = session.query(Account).filter(Account.used_in == chat_id).one()
            return existing_account.link

        except exc.NoResultFound:
            free_account = session.query(Account).filter(Account.used_in == None).first()
            if free_account is not None:
                free_account.used_in = chat_id
                session.commit()
                return free_account.link
            else:
                raise RuntimeError("Нет свободных счетов!")


def deactivate_user(tg_id: int) -> bool:
    """
    Деактивирует пользователя

    :param tg_id: tg_id пользователя
    :return: True, если деактивирован успешно
    """
    s = make_session()
    with s() as session:

        try:
            user = session.query(User).filter(User.tg_id == tg_id).one()
            user.is_active = False
            session.commit()

            logging.info(f'Деактивирован пользователь: {user}')
            return True

        except exc.NoResultFound:
            return False
