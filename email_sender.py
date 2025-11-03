import os
import random
import time
from typing import Tuple
from email.message import EmailMessage
import ssl
import smtplib
import db

# время жизни кода по умолчанию 5 минут
CODE_TTL = int(os.environ.get('CODE_TTL', '300'))


def _send_smtp_with_config(host: str, port: int, user: str, password: str, from_addr: str, to_email: str, subject: str, body: str):
    if not host or not user or not password:
        raise RuntimeError('SMTP credentials not set for provider')

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_email
    msg.set_content(body)

    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(user, password)
            server.send_message(msg)
            print(f"[email_sender] sent email to {to_email} via {host}")
    else:
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(user, password)
            server.send_message(msg)
            print(f"[email_sender] sent email to {to_email} via {host}")


def _choose_provider_config_for_recipient(recipient_email: str):
    """Выбирает конфигурацию SMTP по домену получателя: gmail -> GMAIL_*, yandex -> YANDEX_*, иначе -> default EMAIL_*"""
    domain = recipient_email.lower().split('@')[-1]
    if domain.endswith('gmail.com'):
        return {
            'host': os.environ.get('GMAIL_SMTP_HOST', os.environ.get('EMAIL_HOST')),
            'port': int(os.environ.get('GMAIL_SMTP_PORT', os.environ.get('EMAIL_PORT', '465'))),
            'user': os.environ.get('GMAIL_SMTP_USER', os.environ.get('EMAIL_USER')),
            'pass': os.environ.get('GMAIL_SMTP_PASS', os.environ.get('EMAIL_PASS')),
            'from': os.environ.get('GMAIL_SMTP_FROM', os.environ.get('EMAIL_FROM'))
        }
    if 'yandex' in domain:
        return {
            'host': os.environ.get('YANDEX_SMTP_HOST', os.environ.get('EMAIL_HOST')),
            'port': int(os.environ.get('YANDEX_SMTP_PORT', os.environ.get('EMAIL_PORT', '465'))),
            'user': os.environ.get('YANDEX_SMTP_USER', os.environ.get('EMAIL_USER')),
            'pass': os.environ.get('YANDEX_SMTP_PASS', os.environ.get('EMAIL_PASS')),
            'from': os.environ.get('YANDEX_SMTP_FROM', os.environ.get('EMAIL_FROM'))
        }
    # default
    return {
        'host': os.environ.get('EMAIL_HOST'),
        'port': int(os.environ.get('EMAIL_PORT', '465')),
        'user': os.environ.get('EMAIL_USER'),
        'pass': os.environ.get('EMAIL_PASS'),
        'from': os.environ.get('EMAIL_FROM', os.environ.get('EMAIL_USER'))
    }


def send_verification_code(email: str) -> Tuple[str, float]:
    """Сгенерировать код, сохранить в БД и отправить по SMTP.
    Поддерживает выбор провайдера по домену получателя: Gmail/Yandex (требует соответствующих env vars).
    Возвращает (code, expires) — в dev режиме код также возвращается в ответе.
    """
    code = '{:06d}'.format(random.randint(0, 999999))
    expires = time.time() + CODE_TTL
    # сохраняем код в БД
    db.set_verification_code(email, code, expires)

    subject = 'Код подтверждения вашего аккаунта'
    body = f'Ваш код подтверждения: {code}\nОн действителен {CODE_TTL//60} минут.'

    cfg = _choose_provider_config_for_recipient(email)
    try:
        _send_smtp_with_config(cfg['host'], cfg['port'], cfg['user'], cfg['pass'], cfg['from'], email, subject, body)
    except Exception as e:
        # Логируем ошибку — в dev режиме вернём код для тестирования
        print(f"[email_sender] failed to send email to {email}: {e}")
    return code, expires


def send_plain_email(email: str, subject: str, body: str) -> None:
    """Отправить простое письмо без сохранения кода (используется для тестирования)."""
    cfg = _choose_provider_config_for_recipient(email)
    _send_smtp_with_config(cfg['host'], cfg['port'], cfg['user'], cfg['pass'], cfg['from'], email, subject, body)


def is_smtp_configured_for(email: str) -> bool:
    """Проверяет, есть ли конфигурация SMTP (host,user,pass) для данного email-получателя."""
    cfg = _choose_provider_config_for_recipient(email)
    return bool(cfg.get('host') and cfg.get('user') and cfg.get('pass'))
