from typing import List, Optional

from sqlalchemy import ForeignKey, String, BigInteger, Integer, DateTime, Boolean, func
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), nullable=True, unique=True)
    short_name: Mapped[str] = mapped_column(String(32), nullable=True)
    last_name: Mapped[str] = mapped_column(String(32), nullable=True)
    birth_day: Mapped[int] = mapped_column(Integer, nullable=True)
    birth_month: Mapped[int] = mapped_column(Integer, nullable=True)
    gender: Mapped[str] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    chats: Mapped[List["Chat"]] = relationship()
    bank_account: Mapped[List["BankAccount"]] = relationship()

    def __repr__(self):
        return (
            "User(tg_id=%s, username='%s', short_name='%s', last_name='%s', bday='%s.%s')"
            % (
                self.tg_id,
                self.username,
                self.short_name,
                self.last_name,
                self.birth_day,
                self.birth_month,
            )
        )


class Chat(Base):
    __tablename__ = "chats"
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    invite_link: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    bdayer_id: Mapped[int] = mapped_column(ForeignKey("users.tg_id"))
    bdayer_last_name: Mapped[str] = mapped_column(
        String(64), nullable=True, default=None
    )
    created_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    users_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    users_invited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    participated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    account_link: Mapped[str] = mapped_column(String(64), nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["User"] = relationship(back_populates="chats")
    bank_account: Mapped["BankAccount"] = relationship(back_populates="chat")

    def __repr__(self):
        return "Chat(id=%s, invite_link='%s', bdayer_id='%s', created_at='%s')" % (
            self.chat_id,
            self.invite_link,
            self.bdayer_id,
            self.created_at,
        )


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    link: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.tg_id"))
    used_in: Mapped[int] = mapped_column(
        ForeignKey("chats.chat_id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="bank_account")
    chat: Mapped[Optional["Chat"]] = relationship(back_populates="bank_account")

    def __repr__(self):
        return "BankAccount(link=%s, owner_id='%s', used_in='%s')" % (
            self.link,
            self.owner_id,
            self.used_in,
        )
