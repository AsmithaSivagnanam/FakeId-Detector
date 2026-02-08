import threading
import time


from flask import current_app

from models import db, User
from ml_model import update_user_risk


def agent_loop(app, interval_seconds: int = 5):
    """Background loop that periodically scans users and updates risk."""
    with app.app_context():
        while True:
            users = User.query.all()
            for u in users:
                update_user_risk(u.id)
            # commit is handled in update_user_risk
            time.sleep(interval_seconds)


def start_agent_thread(app):
    t = threading.Thread(target=agent_loop, args=(app,), daemon=True)
    t.start()


