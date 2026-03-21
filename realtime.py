"""
Realtime layer.

If `flask-socketio` isn't installed, we provide a no-op fallback so the app can
still run (dashboard will use polling fallback in the browser).
"""

try:
    from flask_socketio import SocketIO  # type: ignore
except Exception:  # pragma: no cover
    SocketIO = None


class _NoopSocketIO:
    def init_app(self, *args, **kwargs):
        return None

    def emit(self, *args, **kwargs):
        return None

    def run(self, app, **kwargs):
        # Fall back to standard Flask dev server
        return app.run(**kwargs)


# Shared SocketIO instance to avoid circular imports.
socketio = SocketIO(cors_allowed_origins="*") if SocketIO else _NoopSocketIO()

