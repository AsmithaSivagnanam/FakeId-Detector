
import os
import threading
from datetime import datetime, timedelta
from typing import Tuple

import joblib
import numpy as np
from flask import current_app
from sqlalchemy import func

import json

from models import db, User, Post, Follow, LoginEvent, UserRisk, ActivityLog

MODEL_PATH = "model.joblib"
_model_lock = threading.Lock()
_model = None

STATUS_SAFE = "Safe"
STATUS_RESTRICTED = "Restricted"
STATUS_BLOCKED = "Blocked"


def train_model_from_history():
    """Train a simple binary classifier from existing labeled users (user_type field)."""
    from sklearn.ensemble import RandomForestClassifier

    users = User.query.all()
    X = []
    y = []
    for u in users:
        features = compute_user_features(u.id)
        if features is None:
            continue
        X.append(features)
        y.append(1 if u.user_type == "bot" else 0)

    if not X:
        return None

    X = np.array(X)
    y = np.array(y)
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)
    joblib.dump(clf, MODEL_PATH)
    return clf


def load_model(app):
    """Load model at app startup; train if missing."""
    global _model
    with app.app_context():
        if os.path.exists(MODEL_PATH):
            _model = joblib.load(MODEL_PATH)
        else:
            _model = train_model_from_history()


def compute_user_features(user_id: int):
    window = datetime.utcnow() - timedelta(minutes=10)

    posts = (
        db.session.query(Post)
        .filter(Post.user_id == user_id, Post.timestamp >= window)
        .all()
    )

    msg_count = len(posts)
    minutes = max((datetime.utcnow() - window).total_seconds() / 60.0, 1e-3)
    msg_freq = msg_count / minutes

    follows = (
        db.session.query(Follow)
        .filter(Follow.follower_id == user_id, Follow.timestamp >= window)
        .all()
    )
    follow_rate = len(follows) / minutes

    # Duplicate ratio
    if posts:
        contents = [p.content for p in posts]
        unique_contents = len(set(contents))
        duplicate_ratio = 1.0 - (unique_contents / len(contents))
    else:
        duplicate_ratio = 0.0

    logins = (
        db.session.query(LoginEvent)
        .filter(LoginEvent.user_id == user_id, LoginEvent.timestamp >= window)
        .all()
    )
    login_freq = len(logins) / minutes

    #NEW FEATURES
    engagement_rate = msg_count / (len(follows) + 1)
    suspicious_ratio = len(follows) / (msg_count + 1)

    return (
        float(msg_freq),
        float(follow_rate),
        float(duplicate_ratio),
        float(login_freq),
        float(engagement_rate),      # NEW
        float(suspicious_ratio)      # NEW
    )

def _ensure_model():
    global _model
    if _model is None:
        # Lazy-train if still None
        _model = train_model_from_history()
    return _model


def predict_risk_for_user(user_id: int) -> float:
    """Return probability that user is fake (0-100)."""
    model = _ensure_model()
    if model is None:
        # If model is not trained yet, default to low risk
        return 10.0

    features = compute_user_features(user_id)
    if features is None:
        return 5.0

    X = np.array(features).reshape(1, -1)
    proba = model.predict_proba(X)[0][1]  # probability of class 'bot'
    return float(proba * 100.0)


def update_user_risk(user_id: int):
    """Compute risk and update UserRisk row and status based on thresholds."""
    risk = predict_risk_for_user(user_id)
    if risk >= 90.0:
        status = STATUS_BLOCKED
    elif risk >= 60.0:
        status = STATUS_RESTRICTED
    else:
        status = STATUS_SAFE

    record = UserRisk.query.filter_by(user_id=user_id).first()
    prev_status = record.status if record else None
    if not record:
        record = UserRisk(user_id=user_id, risk_score=risk, status=status)
        db.session.add(record)
    else:
        record.risk_score = risk
        record.status = status
    db.session.commit()

    # Automation + audit trail (log only meaningful events).
    if prev_status != status:
        event_type = "blocked" if status == STATUS_BLOCKED else ("restricted" if status == STATUS_RESTRICTED else "safe")
        db.session.add(
            ActivityLog(
                user_id=user_id,
                event_type=event_type,
                metadata_json=json.dumps({"risk_score": float(risk), "from": prev_status, "to": status}),
            )
        )
        db.session.commit()


def predict_risk_from_features(features) -> tuple[float, str]:
    """
    Predict risk score (0-100) and status from a raw features array.

    Expected order:
    [msg_freq, follow_rate, duplicate_ratio, login_freq, engagement_rate, suspicious_ratio]
    """
    model = _ensure_model()
    if model is None:
        risk = 10.0
    else:
        X = np.array(features, dtype=float).reshape(1, -1)
        proba = model.predict_proba(X)[0][1]
        risk = float(proba * 100.0)

    if risk >= 90.0:
        status = STATUS_BLOCKED
    elif risk >= 60.0:
        status = STATUS_RESTRICTED
    else:
        status = STATUS_SAFE
    return risk, status