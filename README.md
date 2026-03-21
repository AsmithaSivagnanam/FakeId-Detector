## Autonomous Agent AI for Detecting Fake Social Media Accounts (Prototype)

This is a small end‑to‑end demo of an autonomous agent that protects a social media platform by detecting and acting on fake accounts in near real time.

### Features

- **Mini social app**: User registration/login, posting messages, following other users.
- **Activity logging**: Posts, follows, login events, and risk automation events stored in SQLite (`ActivityLog`).
- **Simulation**: Background threads simulate both fake (bot) users and real users.
- **ML model (scikit‑learn)**: Uses activity‑based features (message frequency, follow rate, duplicate content, login frequency) to predict whether a user is fake.
- **Autonomous agent**: Periodically recomputes a risk score for each user and sets their status to Safe / Restricted / Blocked.
- **Admin dashboard**: Web UI showing all users, risk scores, and statuses updating every few seconds.
- **API-first platform**: Predict endpoint + user and activity APIs for external integration.

### Tech Stack

- **Backend**: Python, Flask, Flask‑Login, SQLAlchemy
- **ML / AI**: scikit‑learn, RandomForestClassifier
- **Frontend**: HTML, CSS, vanilla JavaScript
- **Database**: SQLite

### Project Structure

- **`app.py`**: Flask app factory, routes (auth, social API, admin API), app startup.
- **`models.py`**: SQLAlchemy models (`User`, `Post`, `Follow`, `LoginEvent`, `UserRisk`).
- **`ml_model.py`**: Feature computation, model training from historical data, and risk scoring.
- **`agent.py`**: Background agent loop that calls the ML model and updates `UserRisk`.
- **`simulator.py`**: Creates synthetic real and bot users and simulates their behavior in background threads.
- **`templates/`**: HTML templates (`base.html`, `login.html`, `register.html`, `feed.html`, `admin.html`).
- **`static/`**: Frontend assets (`styles.css`, `feed.js`, `admin.js`, `profile.js`).
- **`requirements.txt`**: Python dependencies.
- **`wsgi.py`**: WSGI entrypoint for production servers.
- **`gunicorn.conf.py`**: Gunicorn configuration.

### Running Locally

1. **Create and activate a virtual environment (optional but recommended)**  
   ```bash
   cd "FakeAccount Detector"
   python -m venv .venv
   .venv\Scripts\activate  # on Windows
   # source .venv/bin/activate  # on macOS / Linux
   ```

2. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Flask app**  
   ```bash
   python app.py
   ```

   The app will:
   - Initialize the SQLite database (`fake_accounts.db`).
   - Create simulated real and bot users.
   - (If possible) train a simple model from those users.
   - Start background threads for:
     - The bot/real user behavior simulators.
     - The autonomous risk‑scoring agent.

4. **Use the app**

   - Open `http://127.0.0.1:5000/` in your browser.
   - Register a new account and log in.
   - Post messages and follow other users (including simulated ones `alice`, `bob`, `charlie`, `bot_alpha`, `bot_beta`, `bot_gamma`).
   - Open `http://127.0.0.1:5000/admin` to view the **Admin Dashboard**.  
     You will see:
     - All users (human + simulated).
     - Their current risk score (0–100%).
     - Status: **Safe**, **Restricted**, or **Blocked**.

   As the simulator runs, bot users will naturally accumulate very high activity rates and duplicate content, pushing their risk scores up. The autonomous agent periodically re‑evaluates all users and updates their status, which is reflected in the dashboard.

### API Endpoints (Integration)

- **`POST /api/predict`**
  - Request:
    - `{"features": [msg_freq, follow_rate, duplicate_ratio, login_freq, engagement_rate, suspicious_ratio]}`
  - Response:
    - `{"risk_score": 82.5, "status": "Restricted"}`
- **`GET /api/users`**: List users with risk and status.
- **`GET /api/user/<id>`**: Single user + metrics + risk.
- **`GET /api/user/<id>/explain`**: Explainability (top feature contributors) + raw feature values.
- **`POST /api/activity`**: External activity ingestion.
  - Example:
    - `{"user_id": 1, "event_type": "post", "content": "hello"}`
    - `{"user_id": 1, "event_type": "follow", "target_user_id": 2}`
    - `{"user_id": 1, "event_type": "login"}`
  - Auth:
    - If `API_KEYS` is set, send header `X-API-Key: <your_key>`

### Production / Deployment

- **Environment variables**
  - `SECRET_KEY`: required in production
  - `DATABASE_URL`: e.g. `sqlite:///fake_accounts.db` or a managed DB URL
  - `API_KEYS`: comma-separated keys for `/api/activity` (e.g. `key1,key2`)
  - `ADMIN_USERS`: comma-separated usernames allowed to access `/admin` (e.g. `alice,bob`)
- **Gunicorn**
  - Run:
    - For HTTP only: `gunicorn -c gunicorn.conf.py wsgi:app`
    - For WebSockets (admin real-time): run a Socket.IO-compatible server. For example, install an async worker and use:
      - `gunicorn -k eventlet -w 1 wsgi:app`


