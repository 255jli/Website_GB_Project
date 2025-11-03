from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import db
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from dotenv import load_dotenv

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
    user = session.get('user')
    if not user:
        return redirect(url_for('auth_page'))
    return render_template('account.html', login=user)


# send-test-email removed — email sender is not used in simplified flow


if __name__ == '__main__':
    app.run(debug=True)