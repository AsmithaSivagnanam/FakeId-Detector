import threading
import time
from datetime import datetime, timedelta

from flask import app, render_template, redirect, url_for
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_cors import CORS
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)

from models import db, User, Post, Follow, LoginEvent, UserRisk
from ml_model import load_model, compute_user_features, predict_risk_for_user
from simulator import start_simulation_threads
from agent import start_agent_thread


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key-change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fake_accounts.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    CORS(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def setup_background_components():
        """Initialize database, model, and background threads."""
        with app.app_context():
            # Ensure DB tables exist
            db.create_all()
            # Load / train model if needed
            load_model(app)
            # Start simulation and agent threads
            start_simulation_threads(app)
            start_agent_thread(app)
    
    # Setup components on app creation
    setup_background_components()

    # --------- Routes: Auth & Basic Pages ----------
    
    @app.route("/")
    def home():
      return render_template("login.html")

    @app.route("/signin")
    def signin():
        if current_user.is_authenticated:
            return redirect(url_for("feed"))
        return render_template("signin.html")


    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")

        if not username or not password:
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            return render_template("register.html")

        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

        return render_template("register.html")


    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                # log login event
                login_event = LoginEvent(user_id=user.id, timestamp=datetime.utcnow())
                db.session.add(login_event)
                db.session.commit()
                return redirect(url_for("feed"))
            return render_template("login.html", error="Invalid credentials")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    # --------- Routes: Social Features ----------

    @app.route("/feed")
    @login_required
    def feed():
        posts = (
            Post.query.order_by(Post.timestamp.desc())
            .limit(50)
            .all()
        )
        return render_template("feed.html", posts=posts)

    @app.route("/api/post", methods=["POST"])
    @login_required
    def api_post():
        data = request.get_json() or {}
        content = data.get("content", "").strip()
        if not content:
            return jsonify({"error": "Content required"}), 400
        post = Post(user_id=current_user.id, content=content, timestamp=datetime.utcnow())
        db.session.add(post)
        db.session.commit()
        return jsonify({"status": "ok"})

    @app.route("/api/follow", methods=["POST"])
    @login_required
    def api_follow():
        data = request.get_json() or {}
        target_username = data.get("username")
        if not target_username:
            return jsonify({"error": "username required"}), 400
        target = User.query.filter_by(username=target_username).first()
        if not target:
            return jsonify({"error": "User not found"}), 404
        if target.id == current_user.id:
            return jsonify({"error": "Cannot follow yourself"}), 400
        existing = Follow.query.filter_by(follower_id=current_user.id, followed_id=target.id).first()
        if existing:
            return jsonify({"status": "already_following"})
        follow = Follow(follower_id=current_user.id, followed_id=target.id, timestamp=datetime.utcnow())
        db.session.add(follow)
        db.session.commit()
        return jsonify({"status": "ok"})

    # --------- Routes: Admin Dashboard ----------

    @app.route("/admin")
    def admin_dashboard():
        # No auth for prototype; in real system, protect this endpoint
        return render_template("admin.html")

    @app.route("/api/admin/users")
    def admin_users():
        users = User.query.all()
        result = []
        for u in users:
            risk = UserRisk.query.filter_by(user_id=u.id).first()
            score = risk.risk_score if risk else 0.0
            status = risk.status if risk else "Safe"
            result.append(
                {
                    "id": u.id,
                    "username": u.username,
                    "risk_score": round(score, 2),
                    "status": status,
                }
            )
        return jsonify(result)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)



