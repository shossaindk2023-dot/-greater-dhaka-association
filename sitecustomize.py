"""Runtime hook: load GDA's extra routes with Render's gunicorn app:app command."""
import os

# Safe diagnostic: never print the DATABASE_URL itself.
if os.getenv("DATABASE_URL"):
    print("GDA_DATABASE_BACKEND=POSTGRES")
else:
    print("GDA_DATABASE_BACKEND=SQLITE_FALLBACK")

try:
    import wsgi  # noqa: F401
except Exception:
    # Do not prevent the main Flask application from starting if the hook fails.
    pass
