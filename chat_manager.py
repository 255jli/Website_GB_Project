from __future__ import annotations
from typing import Dict, List, Optional
import uuid
import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw
import random
import base64

from db_manager import get_session, Chat, serialize_history, deserialize_history
from ai_core import generate_chat_title


def _fetch_cat_image_bytes() -> Optional[bytes]:
    """Получить изображение кота с aleatori.cat"""
    try:
        # Получаем JSON с информацией о случайном коте
        url = "https://aleatori.cat/random.json"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        # Берем URL изображения из ответа
        img_url = data["url"]
        
        # Загружаем само изображение
        img_resp = requests.get(img_url, timeout=10)
        img_resp.raise_for_status()
        
        # Проверяем, что это действительно изображение
        if img_resp.headers.get('content-type', '').startswith('image/'):
            return img_resp.content
        else:
            print("❌ Полученные данные не являются изображением")
            return _load_default_avatar()
            
    except Exception as e:
        print(f"❌ Ошибка получения кота с aleatori.cat: {e}")
        return _load_default_avatar()


def _load_default_avatar() -> Optional[bytes]:
    """Загрузить default_avatar.png из папки assets"""
    try:
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "assets", "default_avatar.png"),
            os.path.join(os.path.dirname(__file__), "..", "assets", "default_avatar.png"),
            os.path.join(os.getcwd(), "assets", "default_avatar.png"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    print(f"✅ Загружен default_avatar.png: {path}")
                    return f.read()
        
        print("default_avatar.png не найден")
        
    except Exception as e:
        print(f"Ошибка загрузки default_avatar.png: {e}")

def get_chat_avatar(chat_id: str) -> Optional[bytes]:
    """Получить аватар чата по его ID"""
    with get_session() as session:
        chat = session.query(Chat).filter_by(chat_id=chat_id).first()
        if chat and chat.cat_avatar_blob:
            return chat.cat_avatar_blob
        return None


def update_chat_avatar(chat_id: str, avatar_blob: bytes) -> None:
    """Обновить аватар чата"""
    with get_session() as session:
        chat = session.query(Chat).filter_by(chat_id=chat_id).first()
        if chat:
            chat.cat_avatar_blob = avatar_blob
            session.commit()


def _load_chat(session, chat_id: str) -> Optional[Chat]:
    """Загрузить чат из базы данных"""
    return session.query(Chat).filter(Chat.chat_id == chat_id).first()


def _circle_crop(image_bytes: bytes, size: int = 500) -> Optional[bytes]:
    """Обрезает изображение по ширине до квадрата, масштабирует до нужного размера и делает круглую обрезку"""
    try:
        with Image.open(BytesIO(image_bytes)) as im:
            if im.mode != 'RGB':
                im = im.convert('RGB')
            
            w, h = im.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            im = im.crop((left, top, left + side, top + side))
            
            im = im.resize((size, size), Image.LANCZOS)
            
            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            
            im = im.convert("RGBA")
            im.putalpha(mask)
            
            out = BytesIO()
            im.save(out, format="PNG", optimize=True, compress_level=9)
            return out.getvalue()
            
    except Exception as e:
        print(f"❌ Ошибка при обработке изображения: {e}")
        return None


def create_chat(user_id: int, first_message: str = None) -> str:
    """Создать новый чат с аватаром кота и сгенерированным названием"""
    chat_id = uuid.uuid4().hex[:16]
    
    with get_session() as session:
        # Получаем аватар кота
        cat_bytes = _fetch_cat_image_bytes()
        circle_bytes = _circle_crop(cat_bytes, 500) if cat_bytes else None
        
        if not circle_bytes:
            default_avatar = _load_default_avatar()
            circle_bytes = _circle_crop(default_avatar, 500) if default_avatar else None
        
        # Создаем иконку (маленький аватар 64x64)
        icon_bytes = _circle_crop(circle_bytes, 64) if circle_bytes else None
        
        # Генерируем название чата
        if first_message:
            title = generate_chat_title(first_message)
        else:
            title = "Новый чат с Космокотом"
        
        chat = Chat(
            user_id=user_id,
            chat_id=chat_id,
            chat_history=serialize_history([]),
            cat_avatar_blob=circle_bytes,
            title=title,
            icon_blob=icon_bytes,
        )
        session.add(chat)
        session.commit()
        
        print(f"✅ Создан чат '{title}' ({chat_id}) для пользователя {user_id}")
        return chat_id


def list_chats(user_id: int) -> List[Dict[str, any]]:
    """Получить список чатов пользователя с иконками и названиями"""
    result: List[Dict[str, any]] = []
    with get_session() as session:
        rows = (
            session.query(Chat)
            .filter(Chat.user_id == user_id)
            .order_by(Chat.id.desc())
            .all()
        )
        for c in rows:
            # Конвертируем иконку в base64 для фронтенда
            icon_base64 = None
            if c.icon_blob:
                icon_base64 = base64.b64encode(c.icon_blob).decode('utf-8')
            
            result.append({
                "chat_id": c.chat_id,
                "title": c.title or "Чат с Космокотом",
                "icon": icon_base64
            })
    return result


def get_chat_info(chat_id: str) -> Optional[Dict[str, any]]:
    """Получить информацию о чате (название, иконка)"""
    with get_session() as session:
        chat = _load_chat(session, chat_id)
        if not chat:
            return None
            
        icon_base64 = None
        if chat.icon_blob:
            icon_base64 = base64.b64encode(chat.icon_blob).decode('utf-8')
            
        return {
            "chat_id": chat.chat_id,
            "title": chat.title or "Чат с Космокотом",
            "icon": icon_base64
        }


def get_chat_history(chat_id: str) -> List[Dict]:
    """Получить историю сообщений чата"""
    with get_session() as session:
        chat = _load_chat(session, chat_id)
        if not chat:
            return []
    return deserialize_history(chat.chat_history)


def append_message(chat_id: str, role: str, content: str) -> None:
    """Добавить сообщение в историю чата"""
    with get_session() as session:
        chat = _load_chat(session, chat_id)
        if not chat:
            return
            
        history = deserialize_history(chat.chat_history)
        
        # Если это первое сообщение пользователя, генерируем название чата
        if role == 'user' and len(history) == 0:
            title = generate_chat_title(content)
            chat.title = title
        
        history.append({"role": role, "content": content})

        def _prune_history(hist: List[Dict]) -> List[Dict]:
            """Ограничить историю последними 5 парами сообщений пользователь-ассистент"""
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
        chat.chat_history = serialize_history(pruned)
        session.commit()


def clear_history(chat_id: str) -> None:
    """Очистить историю сообщений чата"""
    with get_session() as session:
        chat = _load_chat(session, chat_id)
        if not chat:
            return
        chat.chat_history = serialize_history([])
        session.commit()


def process_avatar(image_bytes: bytes, size: int = 500) -> Optional[bytes]:
    """Обработать аватар - круглая обрезка"""
    return _circle_crop(image_bytes, size)