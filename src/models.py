from typing import List, Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column
from sqlalchemy import ForeignKey, String, BigInteger, Integer, DateTime, Boolean, func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), nullable=True, unique=True)
    first_name: Mapped[str] = mapped_column(String(32), nullable=False)
    short_name: Mapped[str] = mapped_column(String(32), nullable=False)
    middle_name: Mapped[str] = mapped_column(String(32), nullable=False)
    last_name: Mapped[str] = mapped_column(String(32), nullable=False)
    block: Mapped[str] = mapped_column(String(32), nullable=False, default='dppu')
    birth_day: Mapped[int] = mapped_column(Integer, nullable=False)
    birth_month: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    chats: Mapped[List["Chat"]] = relationship()
    account: Mapped[List["Account"]] = relationship()

    def __repr__(self):
        return "User(tg_id=%s, username='%s', first_name='%s', last_name='%s', bday='%s.%s')" % (
            self.tg_id,
            self.username,
            self.first_name,
            self.last_name,
            self.birth_day,
            self.birth_month
        )


class Chat(Base):
    __tablename__ = 'chats'
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    invite_link: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    bdayer_id: Mapped[int] = mapped_column(ForeignKey('users.tg_id'))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    users_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    users_invited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    participated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["User"] = relationship(back_populates="chats")
    account: Mapped["Account"] = relationship(back_populates="chat")

    def __repr__(self):
        return "Chat(id=%s, invite_link='%s', bdayer_id='%s', created_at='%s')" % (
            self.chat_id,
            self.invite_link,
            self.bdayer_id,
            self.created_at,
        )


class Account(Base):
    __tablename__ = 'accounts'
    link: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.tg_id'))
    used_in: Mapped[int] = mapped_column(ForeignKey('chats.chat_id', ondelete='SET NULL'), nullable=True)

    user: Mapped["User"] = relationship(back_populates="account")
    chat: Mapped[Optional["Chat"]] = relationship(back_populates="account")

    def __repr__(self):
        return "Account(link=%s, owner_id='%s', used_in='%s')" % (
            self.link,
            self.owner_id,
            self.used_in,
        )
