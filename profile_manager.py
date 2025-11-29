from __future__ import annotations
from typing import Optional
from io import BytesIO
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash
import db_manager

AVATAR_SIZE = 1024
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 2000

def update_name(user_id: int, new_name: str) -> bool:
    if not new_name or not new_name.strip():
        return False
    new_name = new_name.strip()
    with db_manager.get_session() as session:
        user = session.get(db_manager.User, user_id)
        if user is None:
            return False
        user.name = new_name
        return True

def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    if not old_password or not new_password:
        return False
    with db_manager.get_session() as session:
        user = session.get(db_manager.User, user_id)
        if user is None:
            return False
        if not check_password_hash(user.password_hash, old_password):
            return False
        user.password_hash = generate_password_hash(new_password)
        return True

def _prepare_avatar_1024(image_bytes: bytes) -> Optional[bytes]:
    if len(image_bytes) > MAX_FILE_SIZE:
        return None
    try:
        with Image.open(BytesIO(image_bytes)) as im:
            if im.width > MAX_IMAGE_PIXELS or im.height > MAX_IMAGE_PIXELS:
                return None
            im = im.convert("RGB")
            w, h = im.size
            if w != h:
                side = min(w, h)
                left = (w - side) // 2
                top = (h - side) // 2
                im = im.crop((left, top, left + side, top + side))
            im = im.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
            out = BytesIO()
            im.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return None

def upload_avatar(user_id: int, image_bytes: bytes) -> bool:
    if not image_bytes:
        return False
    prepared = _prepare_avatar_1024(image_bytes)
    if not prepared:
        return False
    with db_manager.get_session() as session:
        user = session.get(db_manager.User, user_id)
        if user is None:
            return False
        user.avatar_blob = prepared
        return True

def get_user_avatar(user_id: int) -> Optional[bytes]:
    with db_manager.get_session() as session:
        user = session.get(db_manager.User, user_id)
        if user is None or not user.avatar_blob:
            return None
        return user.avatar_blob