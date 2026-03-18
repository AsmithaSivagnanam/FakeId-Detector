from datetime import datetime, timedelta

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_cors import CORS
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)

import json
import os

from models import db, User, Post, Follow, LoginEvent, UserRisk, ActivityLog
from ml_model import load_model, predict_risk_from_features, update_user_risk
from simulator import start_simulation_threads
from agent import start_agent_thread


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///fake_accounts.db")
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
                db.session.add(ActivityLog(user_id=user.id, event_type="login", metadata_json=json.dumps({"source": "form"})))
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
        db.session.add(
            ActivityLog(
                user_id=current_user.id,
                event_type="post",
                metadata_json=json.dumps({"length": len(content)}),
            )
        )
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
        db.session.add(
            ActivityLog(
                user_id=current_user.id,
                event_type="follow",
                metadata_json=json.dumps({"target_user_id": target.id}),
            )
        )
        db.session.commit()
        return jsonify({"status": "ok"})

    # --------- API-first endpoints ----------

    @app.route("/api/predict", methods=["POST"])
    def api_predict():
        data = request.get_json() or {}
        features = data.get("features")
        if not isinstance(features, list) or len(features) != 6:
            return jsonify({"error": "features must be an array of 6 numbers"}), 400
        try:
            risk_score, status = predict_risk_from_features(features)
        except Exception:
            return jsonify({"error": "invalid features"}), 400
        return jsonify({"risk_score": round(float(risk_score), 2), "status": status})

    @app.route("/api/users", methods=["GET"])
    def api_users():
        users = User.query.order_by(User.id.asc()).all()
        risks = UserRisk.query.all()
        risk_by_user_id = {r.user_id: r for r in risks}
        result = []
        for u in users:
            r = risk_by_user_id.get(u.id)
            result.append(
                {
                    "id": u.id,
                    "username": u.username,
                    "risk_score": round(float(r.risk_score), 2) if r else 0.0,
                    "status": r.status if r else "Safe",
                }
            )
        return jsonify(result)

    @app.route("/api/user/<int:user_id>", methods=["GET"])
    def api_user(user_id: int):
        u = User.query.get_or_404(user_id)
        r = UserRisk.query.filter_by(user_id=u.id).first()
        posts_count = db.session.query(Post.id).filter_by(user_id=u.id).count()
        followers_count = db.session.query(Follow.id).filter_by(followed_id=u.id).count()
        following_count = db.session.query(Follow.id).filter_by(follower_id=u.id).count()
        login_count = db.session.query(LoginEvent.id).filter_by(user_id=u.id).count()
        return jsonify(
            {
                "id": u.id,
                "username": u.username,
                "metrics": {
                    "posts": posts_count,
                    "followers": followers_count,
                    "following": following_count,
                    "login_events": login_count,
                },
                "risk_score": round(float(r.risk_score), 2) if r else 0.0,
                "status": r.status if r else "Safe",
                "updated_at": r.updated_at.isoformat() if r and r.updated_at else None,
            }
        )

    @app.route("/api/activity", methods=["POST"])
    def api_activity():
        """
        External platforms can report activity:
        {
          "user_id": 1,
          "event_type": "post" | "follow" | "login",
          "content": "...",            # for post
          "target_user_id": 2          # for follow
        }
        """
        data = request.get_json() or {}
        try:
            user_id = int(data.get("user_id"))
        except Exception:
            return jsonify({"error": "user_id required"}), 400

        event_type = (data.get("event_type") or "").strip().lower()
        u = User.query.get(user_id)
        if not u:
            return jsonify({"error": "user not found"}), 404

        now = datetime.utcnow()
        if event_type == "post":
            content = (data.get("content") or "").strip()
            if not content:
                return jsonify({"error": "content required for post"}), 400
            db.session.add(Post(user_id=u.id, content=content, timestamp=now))
            db.session.add(ActivityLog(user_id=u.id, event_type="post", metadata_json=json.dumps({"length": len(content), "source": "api"})))
            db.session.commit()
        elif event_type == "follow":
            try:
                target_user_id = int(data.get("target_user_id"))
            except Exception:
                return jsonify({"error": "target_user_id required for follow"}), 400
            if target_user_id == u.id:
                return jsonify({"error": "cannot follow yourself"}), 400
            target = User.query.get(target_user_id)
            if not target:
                return jsonify({"error": "target user not found"}), 404
            existing = Follow.query.filter_by(follower_id=u.id, followed_id=target.id).first()
            if not existing:
                db.session.add(Follow(follower_id=u.id, followed_id=target.id, timestamp=now))
                db.session.add(ActivityLog(user_id=u.id, event_type="follow", metadata_json=json.dumps({"target_user_id": target.id, "source": "api"})))
                db.session.commit()
        elif event_type == "login":
            db.session.add(LoginEvent(user_id=u.id, timestamp=now))
            db.session.add(ActivityLog(user_id=u.id, event_type="login", metadata_json=json.dumps({"source": "api"})))
            db.session.commit()
        else:
            return jsonify({"error": "event_type must be post, follow, or login"}), 400

        # Trigger immediate re-evaluation after activity.
        update_user_risk(u.id)
        r = UserRisk.query.filter_by(user_id=u.id).first()
        return jsonify(
            {
                "status": "ok",
                "risk_score": round(float(r.risk_score), 2) if r else 0.0,
                "risk_status": r.status if r else "Safe",
            }
        )

    # --------- Routes: Admin Dashboard ----------

    @app.route("/admin")
    @login_required
    def admin_dashboard():
        return render_template("admin.html")

    @app.route("/profile/<int:user_id>")
    @login_required
    def profile(user_id: int):
        u = User.query.get_or_404(user_id)
        risk = UserRisk.query.filter_by(user_id=u.id).first()

        posts_count = db.session.query(Post.id).filter_by(user_id=u.id).count()
        followers_count = db.session.query(Follow.id).filter_by(followed_id=u.id).count()
        following_count = db.session.query(Follow.id).filter_by(follower_id=u.id).count()
        window_start = datetime.utcnow() - timedelta(days=7)
        recent_logins = (
            db.session.query(LoginEvent.id)
            .filter(LoginEvent.user_id == u.id, LoginEvent.timestamp >= window_start)
            .count()
        )

        score = float(risk.risk_score) if risk else 0.0
        status = risk.status if risk else "Safe"
        status_class = (
            "status-blocked" if status == "Blocked" else ("status-restricted" if status == "Restricted" else "status-safe")
        )

        return render_template(
            "profile.html",
            user=u,
            posts_count=posts_count,
            followers_count=followers_count,
            following_count=following_count,
            recent_logins=recent_logins,
            risk_score=round(score, 2),
            status=status,
            status_class=status_class,
        )

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

    @app.route("/api/admin/logs")
    @login_required
    def admin_logs():
        limit = request.args.get("limit", "50")
        try:
            limit_i = max(1, min(200, int(limit)))
        except Exception:
            limit_i = 50

        logs = (
            ActivityLog.query.order_by(ActivityLog.timestamp.desc())
            .limit(limit_i)
            .all()
        )
        user_ids = {l.user_id for l in logs}
        users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
        users_by_id = {u.id: u for u in users}

        payload = []
        for l in logs:
            payload.append(
                {
                    "id": l.id,
                    "user_id": l.user_id,
                    "username": users_by_id.get(l.user_id).username if users_by_id.get(l.user_id) else None,
                    "event_type": l.event_type,
                    "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                    "metadata": l.metadata_json,
                }
            )
        return jsonify(payload)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)



