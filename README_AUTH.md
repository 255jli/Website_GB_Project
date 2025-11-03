# Website_GB_Project — регистрация и подтверждение по email (Gmail / Yandex)

Этот проект — прототип регистрации с подтверждением по одноразовому коду, отправляемому по email.
Поддерживаются адресаты только Gmail и Yandex. Отправка писем производится через SMTP-профили для Gmail и Yandex (можно настроить отдельные учётные данные для каждого).

Файлы и структуры
- `app.py` — основной Flask-приложение (маршруты `/auth`, `/register`, `/verify`, `/login`, `/logout`, `/account`).
- `db.py` — sqlite-модуль: `users` и `verification_codes`.
- `email_sender.py` — отправка писем; выбирает SMTP-конфигурацию по домену получателя (Gmail/Yandex) и отправляет письмо с кодом.
- `templates/auth.html`, `static/auth.js` — минимальная страница для теста регистрации/входа.
- `show_db.py` — утилита для просмотра содержимого БД.

Зависимости
```
pip install -r requirements.txt
```

Переменные окружения (обязательно)
- Общие (альтернативно можно задать провайдера-специфичные переменные ниже):
  - `EMAIL_HOST` — хост SMTP по умолчанию
  - `EMAIL_PORT` — порт (обычно `465` для SSL или `587` для STARTTLS)
  - `EMAIL_USER` — логин отправителя
  - `EMAIL_PASS` — пароль или app-password
  - `EMAIL_FROM` — от кого отправлять (опционально)

Провайдер-специфичные (рекомендуется, если вы хотите использовать разные аккаунты для Gmail и Yandex):
- Gmail:
  - `GMAIL_SMTP_HOST` (напр., `smtp.gmail.com`)
  - `GMAIL_SMTP_PORT` (обычно `465`)
  - `GMAIL_SMTP_USER`
  - `GMAIL_SMTP_PASS`
  - `GMAIL_SMTP_FROM`
- Yandex:
  - `YANDEX_SMTP_HOST` (напр., `smtp.yandex.com`)
  - `YANDEX_SMTP_PORT` (обычно `465`)
  - `YANDEX_SMTP_USER`
  - `YANDEX_SMTP_PASS`
  - `YANDEX_SMTP_FROM`

Примеры (PowerShell):
```
$env:GMAIL_SMTP_HOST='smtp.gmail.com'
$env:GMAIL_SMTP_PORT='465'
$env:GMAIL_SMTP_USER='your@gmail.com'
$env:GMAIL_SMTP_PASS='app_password_here'
$env:GMAIL_SMTP_FROM='your@gmail.com'

$env:YANDEX_SMTP_HOST='smtp.yandex.com'
$env:YANDEX_SMTP_PORT='465'
$env:YANDEX_SMTP_USER='your@yandex.ru'
$env:YANDEX_SMTP_PASS='app_password_here'
$env:YANDEX_SMTP_FROM='your@yandex.ru'
```

Gmail: создайте App Password
- Включите двухфакторную аутентификацию в вашем аккаунте Google.
- В настройках безопасности создайте "App password" и используйте его в `GMAIL_SMTP_PASS`.

Yandex: создайте пароль приложения
- Войдите в аккаунт Yandex, в настройках безопасности создайте пароль для приложения и используйте его в `YANDEX_SMTP_PASS`.

Запуск
```
# в папке проекта
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# установить переменные окружения (см. выше)
python .\app.py
```

Тестирование
- Откройте http://127.0.0.1:5000/auth — зарегистрируйте почту gmail/yandex и пароль.
- После регистрации придёт письмо с кодом (если SMTP настроен) или в режиме разработки сервер вернёт `dev_code` в JSON и вы увидите его в UI.
- Введите код на странице — вы попадёте в аккаунт.

Безопасность и продакшен
- Никогда не храните пароли в репозитории — используйте переменные окружения или секреты контейнера.
- Для продакшена используйте HTTPS, Redis для хранения кодов с TTL, фоновые задачи для отправки почты (Celery/RQ) и rate-limiting.
