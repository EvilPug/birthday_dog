from typing import List, Union, Type

from sqlalchemy import select, exc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker

from config import engine
from logger import logging
from models import Base, User, Chat, BankAccount


def make_session() -> sessionmaker:
    """
    Генератор сессий

    :return: неинициализированная сущность sessionmaker
    """
    return sessionmaker(engine)


def create_db_and_tables() -> None:
    """
    Создает БД и таблицы
    """
    Base.metadata.create_all(engine)


def get_active_chats() -> List[Type[Chat]]:
    """
    Возвращает список активных (не удаленных) чатов
    """

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
            account = session.execute(
                select(BankAccount).filter_by(used_in=chat_id)
            ).scalar_one()
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
            user = session.execute(
                select(User).filter_by(tg_id=chat[0].bdayer_id)
            ).first()
            if user:
                return user[0]

        return None


def get_active_chats_for_user(user_id) -> List[Type[Chat]]:
    """
    Проверяет, если активные чаты для пользователя

    :param user_id: id пользователя
    :return: список сущностей чатов
    """

    s = make_session()
    with s() as session:
        chats = (
            session.query(Chat)
            .filter(Chat.bdayer_id == user_id, Chat.is_active == True)
            .all()
        )

        return chats


def chat_create(
    chat_id: int, invite_link: str, bdayer_id: int, chat_title: str
) -> Chat:
    """
    Добавляет в таблицу chats запись о созданном чате

    :param chat_id: id чата/канала
    :param invite_link: ссылка для приглашения пользователей
    :param bdayer_id: id именинника, для которого был создан чат
    :param chat_title: название созданного чата
    :return: сущность Chat
    """

    s = make_session()
    with s() as session:

        chat = Chat(
            chat_id=chat_id,
            invite_link=invite_link,
            bdayer_id=bdayer_id,
            chat_title=chat_title,
        )
        session.add(chat)
        session.commit()

        logging.info(f"Запись о создании чата добавлена в таблицу. Чат: {chat}")
        return chat


def chat_update(
    chat_id: int, added: int = None, invited: int = None, account_link: str = None
) -> Chat:
    """
    Обновляет запись о чате в БД

    :param chat_id: Id чата.
    :param added: Люди, добавленные в чат напрямую.
    :param invited: Люди, которым было выслано приглашение в чат в виде ссылки.
    :param account_link: Ссылка на сбор денег. Добавляется отдельно, чтобы хранить статистику.
    :return: Объект Chat.
    """

    s = make_session()
    with s() as session:
        chat = session.execute(select(Chat).filter_by(chat_id=chat_id)).scalar_one()
        if added is not None:
            chat.users_added = added
        if invited is not None:
            chat.users_invited = invited
        if account_link is not None:
            chat.account_link = account_link
        session.commit()
    return chat


def log_notified(
    chat_id: int, birthday_sent: bool = None, deletion_sent: bool = None
) -> Chat:
    """
    Добавляет к существующей записи количество добавленных и приглашенных людей.

    :param chat_id: Id чата, для которого нужно записать статистику.
    :param birthday_sent: Отправлено уведомление о дне рождения именинника.
    :param deletion_sent: Отправлено уведомление о скором удалении чата.
    :return: Сущность Chat.
    """

    s = make_session()
    with s() as session:
        chat = session.execute(select(Chat).filter_by(chat_id=chat_id)).scalar_one()

        if birthday_sent is not None:
            chat.notification_birthday_sent = birthday_sent
        if deletion_sent is not None:
            chat.notification_deletion_sent = deletion_sent
        session.commit()
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


def get_all_users() -> List[Type[User]]:
    """
    Получить всех пользователей из таблицы users
    Список отсортирован по месяцу и дню рождения

    :return:
    """

    s = make_session()
    with s() as session:
        users = session.query(User).order_by(User.birth_month, User.birth_day).all()
        return users


def get_active_users() -> List[Type[User]]:
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
            existing_account = (
                session.query(BankAccount).filter(BankAccount.used_in == chat_id).one()
            )
            return existing_account.link

        except exc.NoResultFound:
            free_account = (
                session.query(BankAccount).filter(BankAccount.used_in == None).first()
            )
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

            logging.info(f"Деактивирован пользователь: {user}")
            return True

        except exc.NoResultFound:
            return False


if __name__ == "__main__":
    create_db_and_tables()
