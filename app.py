from __future__ import annotations
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, send_file
from flask_login import LoginManager, login_required, current_user
import os

import auth_manager
import db_manager
import ai_core
import profile_manager
import chat_manager


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # Init DB
    db_manager.init_db()

    # Flask-Login setup
    login_manager = LoginManager(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id: str):
        return auth_manager.get_user_by_id(int(user_id))

    @app.route("/")
    def index():
        return render_template("index.html")


    @app.route("/random-cat")
    def random_cat():
        """Возвращает JSON с URL случайного кота"""
        try:
            cat_url = ai_core.get_random_cat()
            if not cat_url:
                return jsonify({"error": "Не удалось получить изображение кота"}), 500
            
            # Проверяем, что URL валидный и не является data URL
            if cat_url.startswith('data:'):
                # Если это data URL, возвращаем ошибку или преобразуем
                return jsonify({"error": "Некорректный формат изображения"}), 500
                
            return jsonify({"url": cat_url})
        except Exception as e:
            print(f"Ошибка в random-cat: {e}")
            return jsonify({"error": "Не удалось получить изображение кота"}), 500

    @app.route("/favicon.ico")
    def favicon():
        path = os.path.join(app.root_path, "static", "favicon.ico")
        if os.path.exists(path):
            return send_file(path, mimetype="image/x-icon")
        return "", 404

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            login_value = request.form.get("login", "").strip()
            password = request.form.get("password", "")
            if auth_manager.verify_login(login_value, password):
                user = auth_manager.get_user_by_login(login_value)
                if user:
                    auth_manager.login_user_session(user)
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for("platform"))
            flash("Неверный логин или пароль", "error")
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            login_value = request.form.get("login", "").strip()
            name = request.form.get("name", "").strip() or None
            password = request.form.get("password", "")
            if not login_value or not password:
                flash("Укажите логин и пароль", "error")
                return render_template("register.html")
            ok = auth_manager.register_user(login_value, password, name)
            if not ok:
                flash("Такой логин уже существует", "error")
                return render_template("register.html")
            # Auto-login after successful registration
            user = auth_manager.get_user_by_login(login_value)
            if user:
                auth_manager.login_user_session(user)
                return redirect(url_for("platform"))
        return render_template("register.html")

    @app.route("/logout")
    @login_required
    def logout():
        auth_manager.logout_user_session()
        return redirect(url_for("index"))

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        if request.method == "POST":
            updated = False
            # Update name
            new_name = request.form.get("name", "").strip()
            if new_name:
                if profile_manager.update_name(int(current_user.id), new_name):
                    updated = True
            # Change password
            old_pw = request.form.get("old_password", "")
            new_pw = request.form.get("new_password", "")
            if old_pw and new_pw:
                if profile_manager.change_password(int(current_user.id), old_pw, new_pw):
                    updated = True
                else:
                    flash("Неверный старый пароль", "error")
            # Upload avatar
            if "avatar" in request.files:
                file = request.files["avatar"]
                if file and file.filename and file.filename != '':
                    data = file.read()
                    if data:
                        if not profile_manager.upload_avatar(int(current_user.id), data):
                            flash("Ошибка загрузки аватара (ожидается PNG/JPG)", "error")
                        else:
                            updated = True
            if updated:
                flash("Изменения сохранены", "success")
            return redirect(url_for("profile"))
        return render_template("profile.html")

    @app.route("/platform")
    @login_required
    def platform():
        chats = chat_manager.list_chats(int(current_user.id))
        return render_template("platform.html", chats=chats)

    @app.route("/chat/new", methods=["POST"])
    @login_required
    def new_chat():
        chat_id = chat_manager.create_chat(int(current_user.id))
        return redirect(url_for("chat", chat_id=chat_id))

    @app.route("/chat/<string:chat_id>", methods=["GET"])
    @login_required
    def chat(chat_id: str):
        """Страница чата - только GET запросы"""
        # Проверяем принадлежит ли чат текущему пользователю
        if not _check_chat_access(chat_id, int(current_user.id)):
            flash("Чат не найден", "error")
            return redirect(url_for("platform"))
        
        history = chat_manager.get_chat_history(chat_id)
        chat_info = chat_manager.get_chat_info(chat_id)
        return render_template("chat.html", chat_id=chat_id, history=history, chat_info=chat_info)

    @app.route("/api/send_message", methods=["POST"])
    @login_required
    def api_send_message():
        """API endpoint для асинхронной отправки сообщений"""
        data = request.get_json()
        chat_id = data.get('chat_id')
        message = data.get('message', '').strip()
        
        if not chat_id or not message:
            return jsonify({'error': 'Неверные данные'}), 400
        
        # Проверяем доступ к чату
        if not _check_chat_access(chat_id, int(current_user.id)):
            return jsonify({'error': 'Чат не найден'}), 404
        
        # Добавляем сообщение пользователя
        chat_manager.append_message(chat_id, 'user', message)
        
        # Генерируем ответ ИИ
        history = chat_manager.get_chat_history(chat_id)
        try:
            reply = ai_core.generate_reply(history)
        except Exception as e:
            print(f"❌ Ошибка генерации ответа: {e}")
            reply = "Мяу... Похоже, мои двигатели перегрелись. Попробуйте ещё раз."
        
        # Добавляем ответ ассистента
        chat_manager.append_message(chat_id, 'assistant', reply)
        
        return jsonify({'reply': reply})

    @app.route("/user/<int:user_id>/avatar")
    def user_avatar(user_id: int):
        """Получить аватар пользователя"""
        avatar_blob = profile_manager.get_user_avatar(user_id)
        if not avatar_blob:
            # Вернуть дефолтный аватар из assets через отдельный маршрут
            return redirect(url_for('default_avatar'))
        return Response(avatar_blob, mimetype="image/png")

    @app.route("/assets/<path:filename>")
    def assets(filename):
        assets_path = os.path.join(app.root_path, "assets", filename)
        if os.path.exists(assets_path):
            return send_file(assets_path)
        return "", 404

    @app.route("/user/default_avatar.png")
    def default_avatar():
        assets_path = os.path.join(app.root_path, "assets", "default_avatar.png")
        if os.path.exists(assets_path):
            return send_file(assets_path, mimetype="image/png")
        return "", 404

    @app.route("/chat/<string:chat_id>/avatar")
    def chat_avatar(chat_id: str):
        """Получить аватар чата"""
        cat_avatar_blob = chat_manager.get_chat_avatar(chat_id)
        if not cat_avatar_blob:
            # Генерируем новый аватар
            cat_avatar_blob = _generate_chat_avatar(chat_id)
            
        if not cat_avatar_blob:
            return "", 204
            
        return Response(cat_avatar_blob, mimetype="image/png")

    def _check_chat_access(chat_id: str, user_id: int) -> bool:
        """Проверяет принадлежит ли чат пользователю"""
        user_chats = chat_manager.list_chats(user_id)
        return any(chat['chat_id'] == chat_id for chat in user_chats)

    def _generate_chat_avatar(chat_id: str) -> bytes:
        """Генерирует аватар для чата используя aleatori.cat"""
        try:
            import requests
            url = ai_core.get_random_cat()
            if url:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return chat_manager.process_avatar(response.content, 500)
        except Exception as e:
            print(f"❌ Ошибка генерации аватара чата: {e}")
        return None


    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)