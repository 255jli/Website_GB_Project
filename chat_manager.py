from __future__ import annotations
from typing import Dict, List, Optional
import uuid
import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw

import db_manager


def _load_chat(session, chat_id: str) -> Optional[db_manager.Chat]:
    return (
        session.query(db_manager.Chat)
        .filter(db_manager.Chat.chat_id == chat_id)
        .first()
    )


def _fetch_cat_image_bytes() -> Optional[bytes]:
    try:
        api_key = os.environ.get("CAT_API_KEY", "")
        headers = {"x-api-key": api_key} if api_key else {}
        resp = requests.get("https://api.thecatapi.com/v1/images/search", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        img_url = data[0].get("url")
        if not img_url:
            return None
        img_resp = requests.get(img_url, timeout=20)
        img_resp.raise_for_status()
        return img_resp.content
    except Exception:
        return None


def _circle_crop(image_bytes: bytes, size: int = 512) -> Optional[bytes]:
    try:
        with Image.open(BytesIO(image_bytes)) as im:
            im = im.convert("RGB")
            w, h = im.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            im = im.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            im = im.convert("RGBA")
            im.putalpha(mask)
            out = BytesIO()
            im.save(out, format="PNG")
            return out.getvalue()
    except Exception:
        return None


def create_chat(user_id: int) -> str:
    chat_id = uuid.uuid4().hex[:16]
    with db_manager.get_session() as session:
        cat_bytes = _fetch_cat_image_bytes()
        circle_bytes = _circle_crop(cat_bytes) if cat_bytes else None
        if not circle_bytes:
            with open("assets/default_avatar.png", "rb") as f:
                circle_bytes = f.read()
        chat = db_manager.Chat(
            user_id=user_id,
            chat_id=chat_id,
            chat_history=db_manager.serialize_history([]),
            cat_avatar_blob=circle_bytes,
        )
        session.add(chat)
        return chat_id


def list_chats(user_id: int) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    with db_manager.get_session() as session:
        rows = (
            session.query(db_manager.Chat)
            .filter(db_manager.Chat.user_id == user_id)
            .order_by(db_manager.Chat.id.desc())
            .all()
        )
        for c in rows:
            result.append({"chat_id": c.chat_id})
    return result



def get_chat_history(chat_id: str) -> List[Dict]:
    with db_manager.get_session() as session:
        chat = _load_chat(session, chat_id)
        if not chat:
            return []
        return db_manager.deserialize_history(chat.chat_history)



def append_message(chat_id: str, role: str, content: str) -> None:
    with db_manager.get_session() as session:
        chat = _load_chat(session, chat_id)
        if not chat:
            return
        history = db_manager.deserialize_history(chat.chat_history)
        history.append({"role": role, "content": content})

        def _prune_history(hist: List[Dict]) -> List[Dict]:
            picked_rev = []
            user_count = 0
            assistant_count = 0
            for m in reversed(hist):
                r = m.get("role", "user")
                if r == "user" and user_count < 5:
                    picked_rev.append(m)
                    user_count += 1
                elif r == "assistant" and assistant_count < 5:
                    picked_rev.append(m)
                    assistant_count += 1
                if user_count >= 5 and assistant_count >= 5:
                    break
            return list(reversed(picked_rev))

        pruned = _prune_history(history)
        chat.chat_history = db_manager.serialize_history(pruned)


def clear_history(chat_id: str) -> None:
    with db_manager.get_session() as session:
        chat = _load_chat(session, chat_id)
        if not chat:
            return
        chat.chat_history = db_manager.serialize_history([])