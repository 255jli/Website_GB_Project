"""Authentication utilities: registration, login verification, logout, and user loading."""

from __future__ import annotations
from typing import Optional

from flask_login import UserMixin, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

import db_manager


class AuthUser(UserMixin):
    """Lightweight user object for Flask-Login based on DB row."""

    def __init__(self, user_id: int, login: str, name: Optional[str] = None) -> None:
        self.id = str(user_id)
        self.login = login
        self.name = name or ""


def _to_auth_user(u: db_manager.User) -> AuthUser:
    return AuthUser(user_id=u.id, login=u.login, name=u.name)


def register_user(login: str, password: str, name: Optional[str] = None) -> bool:
    with db_manager.get_session() as session:
        existing = session.query(db_manager.User).filter(db_manager.User.login == login).first()
        if existing is not None:
            return False
        password_hash = generate_password_hash(password)
        user = db_manager.User(login=login, password_hash=password_hash, name=name)
        session.add(user)
        return True


def verify_login(login: str, password: str) -> bool:
    with db_manager.get_session() as session:
        user = session.query(db_manager.User).filter(db_manager.User.login == login).first()
        if user is None:
            return False
        return check_password_hash(user.password_hash, password)


def get_user_by_id(user_id: str | int) -> Optional[AuthUser]:
    """Load user by numeric id as AuthUser for Flask-Login."""
    try:
        uid = int(user_id)
    except Exception:
        return None
    with db_manager.get_session() as session:
        user = session.get(db_manager.User, uid)
        if user is None:
            return None
        return _to_auth_user(user)


def get_user_by_login(login: str) -> Optional[AuthUser]:
    with db_manager.get_session() as session:
        user = session.query(db_manager.User).filter(db_manager.User.login == login).first()
        return _to_auth_user(user) if user else None


def login_user_session(user: AuthUser, remember: bool = False) -> None:
    login_user(user, remember=remember)


def logout_user_session() -> None:
    logout_user()

