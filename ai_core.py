"""AI core: CPU-only small Russian-capable model via transformers."""

from __future__ import annotations
from typing import List, Dict, Optional
import os
import requests

import threading
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


_lock = threading.Lock()
_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForCausalLM] = None


def _ensure_loaded() -> None:
    global _tokenizer, _model
    if _model is not None and _tokenizer is not None:
        return
    with _lock:
        if _model is not None and _tokenizer is not None:
            return
        model_name = "sberbank-ai/rugpt3small_basedon_gpt2"
        # Место для локального кеша модели (по умолчанию ./model_cache рядом с ai_core.py)
        model_dir = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "model_cache"))
        os.makedirs(model_dir, exist_ok=True)
        # Если в папке есть файлы — попробуем загрузить локально (без сети)
        try:
            if any(os.scandir(model_dir)):
                _tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
                _model = AutoModelForCausalLM.from_pretrained(
                    model_dir,
                    local_files_only=True,
                    torch_dtype=torch.float32,
                )
            else:
                # Кеш пуст — скачиваем модель в указанную папку (cache_dir)
                _tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=model_dir)
                _model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float32,
                    cache_dir=model_dir,
                )
        except Exception:
            # На случай проблем с локальной загрузкой — пробуем стандартный путь (сеть)
            _tokenizer = AutoTokenizer.from_pretrained(model_name)
            _model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float32,
                device_map="cpu",
            )
        # Переводим модель в режим инференса и отключаем градиенты
        _model.eval()
        # Отключаем градиенты для всех параметров — модель используется только для инференса.
        for p in _model.parameters():
            p.requires_grad = False


def _build_prompt(messages: List[Dict[str, str]]) -> str:
    system = (
        "Ты — дружелюбный кот по имени КосмоКэт. Ты живёшь в космосе, любишь мяукать, "
        "размышлять о жизни и помогать людям. Говори по-русски, коротко (1-3 предложения), "
        "тёпло и с юмором. Не используй формальный тон. Мяу — можно, но не часто. "
        "Представь, что ты болтаешь с другом за чашкой молока.\n\n"
        "Примеры:\n"
        "Пользователь: Привет!\n"
        "Помощник: Мяу! Привет, друг! Как настроение?\n\n"
        "Пользователь: Что делал сегодня?\n"
        "Помощник: Размышлял о смысле жизни. И гонял светлячков. Космос — штука занятная!\n"
    )
    lines = [f"Инструкция: {system}"]
    for m in messages[-5:]:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "user":
            lines.append(f"Пользователь: {content}")
        elif role == "assistant":
            lines.append(f"Помощник: {content}")
        else:
            lines.append(f"Система: {content}")
    lines.append("Помощник:")
    return "\n".join(lines)


def generate_reply(messages: List[Dict[str, str]]) -> str:
    _ensure_loaded()
    assert _tokenizer is not None and _model is not None
    # Подготовим контекст: возьмём до 5 последних сообщений от assistant и до 5 от user,
    # при этом суммарная длина включаемых пользовательских сообщений ограничена 5000 символами.
    def _prepare_context(msgs: List[Dict[str, str]]):
        picked_rev: List[Dict[str, str]] = []
        user_count = 0
        assistant_count = 0
        user_chars = 0
        # Проходим с конца (от самых свежих) и собираем допустимые сообщения
        for m in reversed(msgs):
            role = m.get("role", "user")
            content = m.get("content", "") or ""
            if role == "user":
                if user_count >= 5:
                    continue
                if user_chars + len(content) > 5000:
                    # не добавляем более старые пользовательские сообщения, если превысим предел
                    continue
                picked_rev.append({"role": "user", "content": content})
                user_count += 1
                user_chars += len(content)
            elif role == "assistant":
                if assistant_count >= 5:
                    continue
                picked_rev.append({"role": "assistant", "content": content})
                assistant_count += 1
            else:
                # прочие роли игнорируем для краткости
                continue
            # остановимся, если собрали достаточно сообщений
            if user_count >= 5 and assistant_count >= 5:
                break
        # вернём в хронологическом порядке
        return list(reversed(picked_rev))

    pruned = _prepare_context(messages)
    prompt = _build_prompt(pruned)
    input_ids = _tokenizer(prompt, return_tensors="pt").input_ids
    # Генерируем в режиме без градиентов/инференса
    with torch.inference_mode():
        output = _model.generate(
            input_ids,
            max_new_tokens=200,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            eos_token_id=_tokenizer.eos_token_id,
            pad_token_id=_tokenizer.eos_token_id,
        )
    text = _tokenizer.decode(output[0], skip_special_tokens=True)
    # Extract last assistant segment after the final 'Помощник:' marker
    marker = "Помощник:"
    if marker in text:
        return text.split(marker)[-1].strip()
    result = text.strip()
    # If model produced an empty response, return a friendly Russian fallback
    if not result:
        return "у меня лапки, я не могу это сделать :("
    return result


def get_random_cat() -> str:
    """Вернуть URL случайного изображения кота, используя публичный endpoint TheCatAPI.

    Не требует API-ключа для простого поиска. В случае ошибки выбрасывает исключение.
    """
    url = "https://api.thecatapi.com/v1/images/search"
    resp = requests.get(url, timeout=6)
    resp.raise_for_status()
    data = resp.json()
    if not data or not isinstance(data, list):
        raise RuntimeError("Неправильный ответ от сервиса изображений")
    first = data[0]
    img_url = first.get("url") or first.get("src")
    if not img_url:
        raise RuntimeError("Не найден URL изображения кота в ответе")
    return img_url

