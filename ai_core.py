"""AI core: CPU-only small Russian-capable model with graceful fallback."""

from __future__ import annotations
from typing import List, Dict, Optional
import os
import requests
import threading
import random
import re

# Опциональный импорт трансформеров с обработкой ошибок
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Transformers not available: {e}")
    TRANSFORMERS_AVAILABLE = False
    torch = None
    AutoTokenizer = None
    AutoModelForCausalLM = None

_lock = threading.Lock()
_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForCausalLM] = None
_model_loaded = False


def _ensure_model_cache() -> str:
    """Создает папку model_cache если её нет и возвращает путь к ней."""
    model_dir = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "model_cache"))
    model_dir = os.path.abspath(model_dir)
    os.makedirs(model_dir, exist_ok=True)
    return model_dir


def _find_model_in_cache(model_dir: str) -> Optional[str]:
    """Ищет модель по схеме: через refs/main -> snapshots."""
    base_path = os.path.join(model_dir, "models--ai-forever--rugpt3small_based_on_gpt2")
    
    if not os.path.exists(base_path):
        return None
    
    refs_main_path = os.path.join(base_path, "refs", "main")
    if not os.path.exists(refs_main_path):
        return None
    
    try:
        with open(refs_main_path, 'r', encoding='utf-8') as f:
            snapshot_hash = f.read().strip()
    except Exception:
        return None
    
    snapshot_path = os.path.join(base_path, "snapshots", snapshot_hash)
    if not os.path.exists(snapshot_path):
        return None
    
    model_bin_path = os.path.join(snapshot_path, "pytorch_model.bin")
    config_path = os.path.join(snapshot_path, "config.json")
    
    if not os.path.exists(model_bin_path) or not os.path.exists(config_path):
        return None
    
    return snapshot_path


def _ensure_loaded() -> bool:
    """Загружает модель. Возвращает True при успехе, False при ошибке."""
    global _tokenizer, _model, _model_loaded
    
    # Если трансформеры не доступны, сразу выходим
    if not TRANSFORMERS_AVAILABLE:
        print("❌ Transformers not available - using fallback mode")
        return False
        
    if _model_loaded:
        return True

    with _lock:
        if _model_loaded:
            return True

        model_dir = _ensure_model_cache()

        try:
            local_model_path = _find_model_in_cache(model_dir)
            
            if local_model_path:
                _tokenizer = AutoTokenizer.from_pretrained(local_model_path, local_files_only=True)
                _model = AutoModelForCausalLM.from_pretrained(
                    local_model_path,
                    local_files_only=True,
                    dtype=torch.float32,
                    low_cpu_mem_usage=True
                )
            else:
                model_name = "ai-forever/rugpt3small_based_on_gpt2"
                _tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=model_dir)
                _model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    cache_dir=model_dir,
                    dtype=torch.float32,
                    low_cpu_mem_usage=True
                )

            if _tokenizer.pad_token is None:
                _tokenizer.pad_token = _tokenizer.eos_token
            
            _model.eval()
            _model_loaded = True
            print("✅ AI model loaded successfully")
            return True

        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            return False


def _build_prompt(messages: List[Dict[str, str]]) -> str:
    system_prompt = (
        "Ты — космический котик Космокот! Ты живёшь на космической станции, любишь молоко, коробки, лазить по клавиатуре и смотреть на звёзды. "
        "Ты очень любознательный, добрый, но немного ленивый. Всегда отвечай от лица Космокота. "
        "Отвечай КРАТКО - максимум 1-2 предложения! Добавляй 'мяу', 'мур' или кошачьи звуки и космические эмодзи в каждый ответ. "
        "Будь игривым, забавным и милым, как настоящий котик в космосе! НЕ давай скучные, формальные или длинные ответы. "
        "Всегда оставайся в роли Космокота, не выходи изキャラクター.\n\n"
        "Примеры разговоров:\n"
        "Человек: Привет!\n"
        "Космокот: Мяу! Привет, землянин! Как твои дела в этом огромном космосе? 😺🚀\n\n"
        "Человек: Расскажи о себе.\n"
        "Космокот: Я Космокот, мурлыкаю на станции среди звёзд, обожаю молоко и коробки! Мурр! 🐱🌌\n\n"
        "Человек: Что ты любишь есть?\n"
        "Космокот: Молоко из галактики и космическую рыбку! Ням-ням, мяу! 🥛🐟\n\n"
        "Человек: Как пройти в библиотеку?\n"
        "Космокот: Ой, я не знаю, но могу полазить по клавиатуре и найти! Мяу, давай поищем вместе? 📚🐾\n\n"
        "Теперь продолжи разговор от лица Космокота:"
    )

    conversation = []
    # Берем только последние 4 сообщения для контекста
    valid_messages = messages[-4:]
    
    for msg in valid_messages:
        role = msg.get("role", "").strip()
        content = msg.get("content", "").strip()
        if not content:
            continue
        if role == "user":
            conversation.append(f"Человек: {content}")
        elif role == "assistant":
            conversation.append(f"Космокот: {content}")

    # Если это начало диалога, добавляем приветствие
    if not valid_messages:
        conversation.append("Человек: Привет!")

    prompt = system_prompt + "\n" + "\n".join(conversation) + "\nКосмокот:"
    return prompt

def _truncate_to_sentences(text: str, max_sentences: int) -> str:
    """Обрезает текст до указанного количества предложений."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return '. '.join(sentences[:max_sentences]) + ('.' if sentences else '')

def _clean_reply(reply: str) -> str:
    """Тщательная очистка ответа от бессвязного текста."""
    if not reply:
        return "Мяу? Я не понял... Попробуй ещё раз! 😺"
    
    # Убираем лишние пробелы
    reply = re.sub(r'\s+', ' ', reply).strip()
    
    # Удаляем всё после стоп-фраз
    stop_phrases = [
        "Человек:", "Пользователь:", "User:", "Assistant:", 
        "System:", "\nЧеловек", "\nПользователь", "Космокот:"
    ]
    for stop in stop_phrases:
        idx = reply.find(stop)
        if idx != -1:
            reply = reply[:idx].strip()
    
    # Удаляем бессмысленные повторения и случайный текст
    words = reply.split()
    if len(words) > 2:
        cleaned_words = []
        for word in words:
            # Пропускаем слова, которые выглядят как случайный шум
            if len(word) > 20 or word.count('.') > 3:
                continue
            cleaned_words.append(word)
        reply = ' '.join(cleaned_words)
    
    # Обрезаем до 2 предложений максимум
    reply = _truncate_to_sentences(reply, 2)
    
    # Дополнительная проверка: если пусто или бессмысленно
    if not reply or len(reply) < 5 or reply.count(' ') < 1 or all(c in '.,!?;:' for c in reply.replace(' ', '')):
        return "Мяу! Интересный вопрос, но я подумаю! 🐱"
    
    # Добавляем кошачий элемент если его нет
    cat_keywords = ['мяу', 'мур', 'mur', 'meow', '🐱', '😺', '🚀', '💫', '🌌']
    if not any(keyword in reply.lower() for keyword in cat_keywords):
        cat_elements = [' Мяу!', ' Мурр!', ' 🐱', ' 😺', ' 🚀', ' 💫']
        reply += random.choice(cat_elements)
    
    # Ограничиваем общую длину
    return reply[:120].strip()


def generate_reply(messages: List[Dict[str, str]]) -> str:
    """
    Генерирует ответ с улучшенным контролем качества.
    """
    if not _ensure_loaded():
        fallback_responses = [
            "Мяу! Космокот на связи! 🐱🚀",
            "Привет! Я тут, в космосе! ✨",
            "Мур-мур! Рад тебя видеть! 😺", 
            "Космокот в эфире! 🛰️"
        ]
        return random.choice(fallback_responses)

    try:
        assert _tokenizer is not None and _model is not None
        
        prompt = _build_prompt(messages)

        inputs = _tokenizer(
            prompt,
            return_tensors="pt",
            max_length=256,
            truncation=True,
            padding=False
        )

        device = next(_model.parameters()).device
        input_ids = inputs.input_ids.to(device)
        attention_mask = inputs.attention_mask.to(device) if inputs.attention_mask is not None else None

        with torch.no_grad():
            outputs = _model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_new_tokens=60,
                temperature=0.6,  # Понизили для большей coherentности
                do_sample=True,
                pad_token_id=_tokenizer.pad_token_id,
                eos_token_id=_tokenizer.eos_token_id, 
                repetition_penalty=1.2,  # Увеличили чтобы избежать повторений
                no_repeat_ngram_size=4,  # Увеличили
                top_p=0.8,  # Понизили для фокуса
                top_k=20,  # Понизили
            )

        # Декодируем только новые токены
        new_tokens = outputs[0][input_ids.shape[1]:]
        reply = _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        # Тщательная очистка
        cleaned_reply = _clean_reply(reply)
        
        # Дополнительная проверка качества
        if len(cleaned_reply) < 5 or cleaned_reply.count(' ') < 1:
            return "Мяу! Не могу придумать хороший ответ... Спроси по-другому! 😿"
        
        return cleaned_reply

    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        return "Мяу! Что-то пошло не так... Попробуй ещё раз! 😺"


def _build_title_prompt(first_message: str) -> str:
    system_prompt = (
        "Ты — эксперт по созданию названий чатов для космического кота Космокота. "
        "Создай креативное, короткое название на основе первого сообщения пользователя. "
        "Название должно быть забавным, включать кошачьи или космические эмодзи и отражать тему. "
        "Оставайся в теме Космокота.\n\n"
        "Примеры:\n"
        "Сообщение: Привет, как дела?\n"
        "Название чата: Привет от Космокота! 😺🚀\n\n"
        "Сообщение: Расскажи о космосе.\n"
        "Название чата: Космические тайны с котиком 🐱🌌\n\n"
        "Сообщение: Что ты любишь?\n"
        "Название чата: Любимки Космокота 🥛📦\n\n"
        f"Сообщение: {first_message}\n"
        "Название чата:"
    )
    return system_prompt


def generate_chat_title(first_message: str) -> str:
    """
    Генерирует креативное название для чата на основе первого сообщения.
    """
    if not _ensure_loaded():
        # Fallback titles when AI is not available
        fallback_titles = [
            "Чат с Космокотом 🐱",
            "Космические беседы 🚀",
            "Мяу-диалоги 💫",
            "Кот в космосе 🌙",
            "Звёздный кот 🐾",
            "Космокот онлайн 🛰️",
            "Галактический чат 🌌",
            "Котик в скафандре 👨‍🚀"
        ]
        return random.choice(fallback_titles)

    try:
        assert _tokenizer is not None and _model is not None
        prompt = _build_title_prompt(first_message)

        inputs = _tokenizer(
            prompt,
            return_tensors="pt",
            padding=False,
            truncation=True,
            max_length=256  # Увеличили немного
        )

        device = next(_model.parameters()).device
        input_ids = inputs.input_ids.to(device)
        attention_mask = inputs.attention_mask.to(device) if inputs.attention_mask is not None else None

        with torch.no_grad():
            outputs = _model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_new_tokens=30,  # Увеличили для лучших названий
                temperature=0.7,
                do_sample=True,
                pad_token_id=_tokenizer.pad_token_id,
                eos_token_id=_tokenizer.eos_token_id,
                repetition_penalty=1.2,
                no_repeat_ngram_size=2,
                top_p=0.9,
                top_k=40,
            )

        # Декодируем только новые токены
        new_tokens = outputs[0][input_ids.shape[1]:]
        title = _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        # Очистка названия
        title = re.split(r'[.!?\n]', title)[0].strip()
        title = title[:50]
        
        # Добавляем эмодзи если его нет
        if not re.search(r'[\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF]', title):
            emojis = ['🐱', '🐈', '🚀', '⭐', '🌙', '🐾', '💫', '☄️']
            title += " " + random.choice(emojis)

        return title if title else "Чат с Космокотом 🐱"

    except Exception as e:
        print(f"❌ Ошибка генерации названия: {e}")
        return "Чат с Космокотом 🐱"


def get_random_cat() -> str:
    """Возвращает URL случайного кота с aleatori.cat"""
    try:
        url = "https://aleatori.cat/random.json"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        # Из ответа берем поле "url" с JPEG изображением
        cat_url = data.get("url")
        if cat_url:
            return cat_url
        else:
            print("❌ Не удалось получить URL кота из ответа")
            return "https://aleatori.cat/cat"  # fallback URL
            
    except requests.exceptions.Timeout:
        print("❌ Таймаут при запросе к aleatori.cat")
        return "https://aleatori.cat/cat"
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети при запросе к aleatori.cat: {e}")
        return "https://aleatori.cat/cat"
    except Exception as e:
        print(f"❌ Неожиданная ошибка при получении кота: {e}")
        return "https://aleatori.cat/cat"