from datetime import datetime

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_cors import CORS
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)

from models import db, User, Post, Follow, LoginEvent, UserRisk
from ml_model import load_model
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

    def _handle_register(template_name: str):
        if current_user.is_authenticated:
            return redirect(url_for("feed"))

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""

            if not username or not password:
                return render_template(template_name, error="Fill all fields")

            if User.query.filter_by(username=username).first():
                return render_template(template_name, error="User already exists")

            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            login_user(user)
            db.session.add(LoginEvent(user_id=user.id, timestamp=datetime.utcnow()))
            db.session.commit()

            return redirect(url_for("feed"))

        return render_template(template_name)
    
    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("feed"))
        return redirect(url_for("login"))

    @app.route("/signin", methods=["GET", "POST"])
    def signin():
        return _handle_register("signIn.html")


    @app.route("/register", methods=["GET", "POST"])
    def register():
        return _handle_register("signIn.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("feed"))

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                db.session.add(LoginEvent(user_id=user.id, timestamp=datetime.utcnow()))
                db.session.commit()
                return redirect(url_for("feed"))

            return render_template("login.html", error="Invalid username or password")

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
        user_ids = {p.user_id for p in posts}
        users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
        users_by_id = {u.id: u for u in users}

        risks = UserRisk.query.filter(UserRisk.user_id.in_(user_ids)).all() if user_ids else []
        risk_by_user_id = {r.user_id: r for r in risks}

        all_users = User.query.order_by(User.username.asc()).all()
        all_risks = UserRisk.query.all()
        all_risk_by_user_id = {r.user_id: r for r in all_risks}

        return render_template(
            "feed.html",
            posts=posts,
            users_by_id=users_by_id,
            risk_by_user_id=risk_by_user_id,
            all_users=all_users,
            all_risk_by_user_id=all_risk_by_user_id,
        )


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
    @login_required
    def admin_dashboard():
        return render_template("admin.html")

    @app.route("/api/admin/users")
    @login_required
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



