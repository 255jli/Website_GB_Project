from __future__ import annotations
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import (
    LoginManager,
    login_required,
    current_user,
)
import os
from flask import send_file
 
import auth_manager
import db_manager
import ai_core
import profile_manager
import chat_manager


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # Init DB lazily (engine/session inside db_manager)
    db_manager.init_db()

    # Flask-Login setup
    login_manager = LoginManager(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id: str):
        return auth_manager.get_user_by_id(user_id)

    @app.route("/")
    def index():
        return render_template("index.html")


    @app.route("/random-cat")
    def random_cat():
        """Возвращает JSON с URL случайного кота (через ai_core.get_random_cat)."""
        try:
            cat_url = ai_core.get_random_cat()
        except Exception:
            return jsonify({"error": "Не удалось получить изображение кота"}), 500
        return jsonify({"url": cat_url})

    @app.route("/favicon.ico")
    def favicon():
        path = os.path.join(os.path.dirname(__file__), "favicon.ico")
        if os.path.exists(path):
            return send_file(path, mimetype="image/x-icon")
        return redirect(url_for("index"))

    # Placeholders for future routes per plan
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            login_value = request.form.get("login", "").strip()
            password = request.form.get("password", "")
            if auth_manager.verify_login(login_value, password):
                user = auth_manager.get_user_by_login(login_value)
                if user:
                    auth_manager.login_user_session(user)
                    return redirect(url_for("platform"))
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
            new_name = request.form.get("name")
            if new_name is not None and new_name.strip():
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
                if file and file.filename:
                    data = file.read()
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

    @app.route("/chat/new", methods=["POST", "GET"])
    @login_required
    def new_chat():
        chat_id = chat_manager.create_chat(int(current_user.id))
        return redirect(url_for("chat", chat_id=chat_id))

    @app.route("/chat/<string:chat_id>", methods=["GET", "POST"])
    @login_required
    def chat(chat_id: str):
        if request.method == "POST":
            msg = request.form.get("message", "").strip()
            if msg:
                chat_manager.append_message(chat_id, role="user", content=msg)
                # Generate AI reply and append
                history_for_ai = chat_manager.get_chat_history(chat_id)
                try:
                    reply = ai_core.generate_reply(history_for_ai)
                except Exception:
                    reply = "Мяу... Похоже, мои двигатели перегрелись. Попробуйте ещё раз."
                chat_manager.append_message(chat_id, role="assistant", content=reply)
            return redirect(url_for("chat", chat_id=chat_id))
        history = chat_manager.get_chat_history(chat_id)
        return render_template("chat.html", chat_id=chat_id, history=history)

    @app.route("/chat/<string:chat_id>/avatar")
    @login_required
    def chat_avatar(chat_id: str):
        from flask import Response
        with db_manager.get_session() as session:
            row = session.query(db_manager.Chat).filter(db_manager.Chat.chat_id == chat_id).first()
            if not row or not row.cat_avatar_blob:
                return Response(status=404)
            return Response(row.cat_avatar_blob, mimetype="image/png")


    return app
    

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)

