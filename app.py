from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import os
import io
import db
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from dotenv import load_dotenv
from PIL import Image, ImageOps

# Загружаем переменные окружения из .env если есть
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

# Инициализация БД
db.init_db()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/auth')
def auth_page():
    return render_template('auth.html')


@app.route('/register', methods=['POST'])
def register():
    # БЛОКИРОВКА РЕГИСТРАЦИИ (ВРЕМЕННО)
    if os.environ.get('DISABLE_REGISTRATION', '').lower() in ('1', 'true', 'yes'):
        return jsonify({'error': 'registrations are temporarily disabled'}), 403

    # Простая регистрация по login + password
    data = request.get_json(silent=True) or request.form or {}
    login = (data.get('login') or '').strip()
    password = data.get('password')
    if not login or not password:
        return jsonify({'error': 'login and password required'}), 400
    if len(login) < 3 or len(login) > 64:
        return jsonify({'error': 'login length must be between 3 and 64 chars'}), 400
    if len(password) < 6:
        return jsonify({'error': 'password too short (min 6 chars)'}), 400

    existing = db.get_user(login)
    if existing:
        return jsonify({'error': 'user exists'}), 400

    pw_hash = generate_password_hash(password)
    try:
        db.create_user(login, pw_hash)
    except sqlite3.IntegrityError:
        return jsonify({'error': 'user exists'}), 400
    except Exception as e:
        return jsonify({'error': 'failed to create user', 'detail': str(e)}), 500

    return jsonify({'status': 'ok'})


# Email verification removed in simplified flow


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or request.form or {}
    login = (data.get('login') or '').strip()
    password = data.get('password')
    if not login or not password:
        return jsonify({'error': 'login and password required'}), 400

    user = db.get_user(login)
    if not user:
        return jsonify({'error': 'no such user'}), 400
    if not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'invalid credentials'}), 400

    session['user'] = login
    return jsonify({'status': 'ok'})


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'status': 'ok'})


@app.route('/account')
def account():
    user_login = session.get('user')
    if not user_login:
        return redirect(url_for('auth_page'))
    user = db.get_user(user_login)
    avatar_url = None
    if user and user.get('avatar_path'):
        avatar_url = url_for('static', filename=user['avatar_path'].replace('static/', '')) if user['avatar_path'].startswith('static/') else url_for('static', filename=user['avatar_path'])
    return render_template('account.html', login=user_login, display_name=user.get('display_name') if user else None, avatar_url=avatar_url)


def _require_auth():
    login = session.get('user')
    if not login:
        return None, (jsonify({'error': 'unauthorized'}), 401)
    return login, None


@app.route('/account/change_password', methods=['POST'])
def change_password():
    login, err = _require_auth()
    if err:
        return err
    data = request.get_json(silent=True) or request.form or {}
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    if not old_password or not new_password:
        return jsonify({'error': 'old_password and new_password are required'}), 400
    if len(new_password) < 6:
        return jsonify({'error': 'new_password too short (min 6 chars)'}), 400
    user = db.get_user(login)
    if not user or not check_password_hash(user['password_hash'], old_password):
        return jsonify({'error': 'invalid old password'}), 400
    db.update_password(login, generate_password_hash(new_password))
    return jsonify({'status': 'ok'})


@app.route('/account/display_name', methods=['POST'])
def set_display_name():
    login, err = _require_auth()
    if err:
        return err
    data = request.get_json(silent=True) or request.form or {}
    display_name = (data.get('display_name') or '').strip()
    if len(display_name) > 80:
        return jsonify({'error': 'display_name too long'}), 400
    db.update_display_name(login, display_name or None)
    return jsonify({'status': 'ok', 'display_name': display_name or None})


def _ensure_avatar_dir() -> str:
    root = os.path.dirname(__file__)
    rel_dir = os.path.join('static', 'avatars')
    abs_dir = os.path.join(root, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    return abs_dir


@app.route('/account/avatar', methods=['POST'])
def upload_avatar():
    login, err = _require_auth()
    if err:
        return err
    if 'avatar' not in request.files:
        return jsonify({'error': 'file field "avatar" is required'}), 400
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'empty filename'}), 400
    try:
        img = Image.open(file.stream).convert('RGBA')
    except Exception:
        return jsonify({'error': 'invalid image'}), 400

    # Приводим к 1024x1024, центр-кроп
    target_size = (1024, 1024)
    img = ImageOps.fit(img, target_size, Image.LANCZOS)

    # Маска круга
    mask = Image.new('L', target_size, 0)
    mask_draw = Image.new('L', target_size, 0)
    mask_draw_pil = Image.new('L', target_size, 0)
    # Используем ImageDraw без отдельного импорта через ImageOps.expand трюк
    from PIL import ImageDraw
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, target_size[0], target_size[1]), fill=255)
    img.putalpha(mask)

    # Сохраняем
    abs_dir = _ensure_avatar_dir()
    filename = f"{login}.png"
    abs_path = os.path.join(abs_dir, filename)
    img.save(abs_path, format='PNG')

    # Сохраним относительный путь для static
    rel_path = os.path.join('avatars', filename).replace('\\', '/')
    db.update_avatar_path(login, rel_path)
    return jsonify({'status': 'ok', 'avatar_url': url_for('static', filename=rel_path)})


@app.route('/account/delete', methods=['POST'])
def delete_account():
    login, err = _require_auth()
    if err:
        return err
    # удалить аватар, если есть
    user = db.get_user(login)
    if user and user.get('avatar_path'):
        path = user['avatar_path']
        # поддержка как 'avatars/...' так и 'static/avatars/...'
        if not path.startswith('static/'):
            path = os.path.join('static', path)
        abs_path = os.path.join(os.path.dirname(__file__), path)
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception:
            pass
    db.delete_user(login)
    session.pop('user', None)
    return jsonify({'status': 'ok'})


# send-test-email removed — email sender is not used in simplified flow


if __name__ == '__main__':
    app.run(debug=True)