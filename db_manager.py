from __future__ import annotations
from typing import Optional, Iterator, List, Dict, Any
from contextlib import contextmanager
import os
import json
from sqlalchemy import create_engine, String, Integer, LargeBinary, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session

class Base(DeclarativeBase):
    pass

_engine = None
SessionLocal: sessionmaker[Session] | None = None

def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///cosmocats.db")

def init_db(database_url: Optional[str] = None) -> None:
    global _engine, SessionLocal
    url = database_url or get_database_url()
    _engine = create_engine(url, future=True)
    SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False, future=True)
    Base.metadata.create_all(_engine)

@contextmanager
def get_session() -> Iterator[Session]:
    if SessionLocal is None:
        init_db()
    assert SessionLocal is not None
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_blob: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    chats: Mapped[List["Chat"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    chat_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    chat_history: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    cat_avatar_blob: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    icon_blob: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    user: Mapped[User] = relationship(back_populates="chats")

def serialize_history(messages: List[Dict[str, Any]]) -> bytes:
    return json.dumps(messages, ensure_ascii=False).encode("utf-8")

def deserialize_history(blob: Optional[bytes]) -> List[Dict[str, Any]]:
    if not blob:
        return []
    try:
        return json.loads(blob.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []