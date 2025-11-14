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
        model_name = "ai-forever/rugpt3small_based_on_gpt2"
        model_dir = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "model_cache"))
        os.makedirs(model_dir, exist_ok=True)
        
        # Оптимизация потоков для CPU
        torch.set_num_threads(max(1, os.cpu_count() // 2))
        
        # Путь к локальной модели
        local_model_path = os.path.join(model_dir, "models--ai-forever--rugpt3small_based_on_gpt2")
        
        try:
            # Проверяем, есть ли уже скачанная модель
            if os.path.isdir(local_model_path):
                # Используем локальную версию
                snapshot_dir = os.path.join(local_model_path, "snapshots")
                if os.path.exists(snapshot_dir):
                    # Берём первую папку в snapshots (любая версия)
                    snapshot_folders = [f for f in os.listdir(snapshot_dir) if os.path.isdir(os.path.join(snapshot_dir, f))]
                    if snapshot_folders:
                        first_snapshot = snapshot_folders[0]
                        model_path = os.path.join(snapshot_dir, first_snapshot)
                        _tokenizer = AutoTokenizer.from_pretrained(model_path)
                        _model = AutoModelForCausalLM.from_pretrained(
                            model_path,
                            torch_dtype=torch.float32,
                            low_cpu_mem_usage=True,
                        )
                        print(f"Модель загружена из: {model_path}")
                    else:
                        # Если snapshots пуст — пытаемся загрузить без него
                        _tokenizer = AutoTokenizer.from_pretrained(local_model_path, local_files_only=True)
                        _model = AutoModelForCausalLM.from_pretrained(
                            local_model_path,
                            local_files_only=True,
                            torch_dtype=torch.float32,
                            low_cpu_mem_usage=True,
                        )
                else:
                    # Если нет snapshots — загружаем вручную
                    _tokenizer = AutoTokenizer.from_pretrained(local_model_path, local_files_only=True)
                    _model = AutoModelForCausalLM.from_pretrained(
                        local_model_path,
                        local_files_only=True,
                        torch_dtype=torch.float32,
                        low_cpu_mem_usage=True,
                    )
            else:
                # Первый запуск — скачиваем через cache_dir
                print("Скачивание модели... Это может занять 5–10 минут.")
                _tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=model_dir)
                _model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float32,
                    cache_dir=model_dir,
                    low_cpu_mem_usage=True,
                )
                print("Модель успешно скачана.")
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}, пробуем стандартный способ...")
            _tokenizer = AutoTokenizer.from_pretrained(model_name)
            _model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
        
        # Важное исправление - добавляем pad token
        if _tokenizer.pad_token is None:
            _tokenizer.pad_token = _tokenizer.eos_token
        
        _model.eval()
        for p in _model.parameters():
            p.requires_grad = False


def _build_prompt(messages: List[Dict[str, str]]) -> str:
    """Простой промптинг для русскоязычной модели"""
    conversation = []
    for m in messages[-6:]:  # берем последние 6 сообщений для контекста
        role = m.get("role", "")
        content = m.get("content", "")
        if role == "user":
            conversation.append(f"Пользователь: {content}")
        elif role == "assistant":
            conversation.append(f"Ассистент: {content}")
    
    if conversation:
        prompt = "\n".join(conversation) + "\nАссистент:"
    else:
        prompt = "Ассистент: Привет! Я дружелюбный AI-помощник."
    
    return prompt

def generate_reply(messages: List[Dict[str, str]]) -> str:
    _ensure_loaded()
    assert _tokenizer is not None and _model is not None
    
    prompt = _build_prompt(messages)
    input_ids = _tokenizer.encode(prompt, return_tensors="pt")
    
    with torch.no_grad():
        output = _model.generate(
            input_ids,
            max_new_tokens=100,  # Правильный параметр для генерации
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True,
            pad_token_id=_tokenizer.eos_token_id,
            eos_token_id=_tokenizer.eos_token_id,
            repetition_penalty=1.1,
            early_stopping=True,  # Остановка при достижении EOS
        )
    
    response = _tokenizer.decode(output[0], skip_special_tokens=True)
    
    # Извлекаем только ответ ассистента
    if "Ассистент:" in response:
        response = response.split("Ассистент:")[-1].strip()
    
    return response

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