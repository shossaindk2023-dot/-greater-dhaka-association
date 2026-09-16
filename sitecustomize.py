"""Runtime hook for Google Search Console verification."""
try:
    from app import app
    app.add_url_rule(
        '/google827a650554bab237.html',
        endpoint='google_search_console_verification',
        view_func=lambda: ('google-site-verification: google827a650554bab237.html', 200, {'Content-Type': 'text/plain; charset=utf-8'})
    )
except Exception:
    # Do not prevent the main application from starting if the hook is unavailable.
    pass
