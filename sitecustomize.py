"""Runtime hook: load GDA's extra routes with Render's gunicorn app:app command."""
try:
    import wsgi  # noqa: F401
except Exception:
    # Do not prevent the main Flask application from starting if the hook fails.
    pass
