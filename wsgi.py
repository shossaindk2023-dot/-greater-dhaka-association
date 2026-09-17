from app import app, db, Member
from flask import session, redirect, url_for
from functools import wraps

# Google Search Console HTML-file verification.
@app.route('/google827a650554bab237.html')
def google_site_verification():
    return 'google-site-verification: google827a650554bab237.html', 200, {'Content-Type': 'text/plain; charset=utf-8'}

def _admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return fn(*args, **kwargs)
    return wrapper

# Extra member-management screen: approval, fee tracking and member-card access.
@app.route('/admin/manage')
@_admin_required
def admin_manage():
    members = Member.query.order_by(Member.created_at.desc()).all()
    rows = []
    for m in members:
        actions = []
        if m.status != 'Approved':
            actions.append(f'<a href="/admin/approve/{m.id}">Approve</a>')
        if m.fee_status != 'Paid':
            actions.append(f'<a href="/admin/member/{m.id}/fee-paid">Mark fee paid</a>')
        if m.membership_number:
            actions.append(f'<a href="/member-card/{m.membership_number}.pdf">Member card PDF</a>')
        rows.append(f'<tr><td>{m.name}</td><td>{m.application_code}</td><td>{m.status}</td><td>{m.fee_status}</td><td>{" | ".join(actions) or "—"}</td></tr>')
    table = ''.join(rows) or '<tr><td colspan="5">No applications yet.</td></tr>'
    return f'''<div style="font-family:Arial,sans-serif;max-width:1100px;margin:30px auto;padding:20px">
    <h1>GDA Member Management</h1>
    <p><a href="/admin">← Admin Dashboard</a> &nbsp; <a href="/admin/logout">Logout</a></p>
    <table style="width:100%;border-collapse:collapse"><tr><th>Name</th><th>Application</th><th>Status</th><th>Fee</th><th>Actions</th></tr>{table}</table>
    </div>'''

@app.route('/admin/member/<int:member_id>/fee-paid')
@_admin_required
def mark_fee_paid(member_id):
    member = Member.query.get_or_404(member_id)
    member.fee_status = 'Paid'
    db.session.commit()
    return redirect(url_for('admin_manage'))

application = app
