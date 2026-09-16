from app import app

# Google Search Console HTML-file verification.
@app.route('/google827a650554bab237.html')
def google_site_verification():
    return 'google-site-verification: google827a650554bab237.html', 200, {'Content-Type': 'text/plain; charset=utf-8'}

application = app
