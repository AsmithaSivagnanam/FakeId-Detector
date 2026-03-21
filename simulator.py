import random
import threading
import time
from datetime import datetime

from models import db, User, Post, Follow, LoginEvent


# Simulator users that should always exist.
# Keep in sync with the UI suggestions on /feed.
BOT_USERNAMES = [
    "bot_alpha",
    "bot_beta",
    "bot_gamma",
    "agan_11",
    "merlin_cutiee",
    "jeeva_007",
]
REAL_USERNAMES = [
    "alice",
    "bob",
    "charlie",
    "priya_sweety",
    "im_prabu",
    "its_me!!",
]


def ensure_sim_users():
    """Create a few bot and real users used only by the simulator."""
    users = []
    for username in BOT_USERNAMES:
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, user_type="bot")
            user.set_password("password")
            db.session.add(user)
            db.session.commit()
        users.append(user)

    for username in REAL_USERNAMES:
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, user_type="real")
            user.set_password("password")
            db.session.add(user)
            db.session.commit()
        users.append(user)
    return users


def bot_behavior_loop(user: User, app):
    """Bots send many messages quickly, follow many users, and repeat content."""
    repeated_messages = [
        "Buy now!!!",
        "Click this link for free stuff",
        "Limited offer!!!",
    ]
    while True:
        with app.app_context():
            # many messages per minute
            for _ in range(random.randint(3, 8)):
                msg = random.choice(repeated_messages)
                post = Post(user_id=user.id, content=msg, timestamp=datetime.utcnow())
                db.session.add(post)
            # aggressive follow behavior
            all_users = User.query.all()
            targets = random.sample(all_users, min(len(all_users), random.randint(3, 10)))
            for target in targets:
                if target.id == user.id:
                    continue
                existing = (
                    Follow.query.filter_by(follower_id=user.id, followed_id=target.id)
                    .first()
                )
                if not existing:
                    follow = Follow(
                        follower_id=user.id,
                        followed_id=target.id,
                        timestamp=datetime.utcnow(),
                    )
                    db.session.add(follow)
            # frequent logins
            login_event = LoginEvent(user_id=user.id, timestamp=datetime.utcnow())
            db.session.add(login_event)
            db.session.commit()
        time.sleep(random.uniform(3, 6))


def real_user_behavior_loop(user: User, app):
    """Real users post and follow at a slower, more natural rate."""
    natural_messages = [
        "Nice day today!",
        "Enjoying this platform.",
        "Just checking in.",
        "Having coffee and coding.",
    ]
    while True:
        with app.app_context():
            # fewer messages
            if random.random() < 0.5:
                msg = random.choice(natural_messages)
                post = Post(user_id=user.id, content=msg, timestamp=datetime.utcnow())
                db.session.add(post)

            # occasional follows
            if random.random() < 0.3:
                all_users = User.query.all()
                target = random.choice(all_users)
                if target.id != user.id:
                    existing = (
                        Follow.query.filter_by(follower_id=user.id, followed_id=target.id)
                        .first()
                    )
                    if not existing:
                        follow = Follow(
                            follower_id=user.id,
                            followed_id=target.id,
                            timestamp=datetime.utcnow(),
                        )
                        db.session.add(follow)

            # occasional login event
            if random.random() < 0.4:
                login_event = LoginEvent(user_id=user.id, timestamp=datetime.utcnow())
                db.session.add(login_event)

            db.session.commit()
        time.sleep(random.uniform(15, 30))


def start_simulation_threads(app):
    """Start background threads for bot and real user simulation."""
    from flask import current_app

    def _runner():
        with app.app_context():
            users = ensure_sim_users()
            for u in users:
                if u.user_type == "bot":
                    t = threading.Thread(target=bot_behavior_loop, args=(u, app), daemon=True)
                else:
                    t = threading.Thread(
                        target=real_user_behavior_loop, args=(u, app), daemon=True
                    )
                t.start()

    t_main = threading.Thread(target=_runner, daemon=True)
    t_main.start()


