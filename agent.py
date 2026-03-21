import threading
import time


from flask import current_app

from models import db, User
from ml_model import update_user_risk
from realtime import socketio


def agent_loop(app):
    """Background loop that periodically scans users and updates risk."""
    with app.app_context():
        while True:
            users = User.query.all()
            for u in users:
                update_user_risk(u.id)
            # notify dashboards after a scan
            socketio.emit("users_update", {"event": "agent_scan"})
            # commit is handled in update_user_risk
            print("Agent running...")
            time.sleep(5)


def start_agent_thread(app):
    t = threading.Thread(target=agent_loop, args=(app,), daemon=True)
    t.start()
    return t


