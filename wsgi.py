from app import app, db, Member, current_admin
from flask import session, redirect, url_for, request, send_file
from functools import wraps
import html
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

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

def _superadmin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        admin = current_admin()
        if not admin or not admin.active or admin.role != 'superadmin':
            return redirect(url_for('admin_dashboard'))
        return fn(*args, **kwargs)
    return wrapper

# Member-management screen: review/approval, fee tracking, member-card access and safe deletion.
@app.route('/admin/manage')
@_admin_required
def admin_manage():
    members = Member.query.order_by(Member.created_at.desc()).all()
    rows = []
    for m in members:
        actions = []
        actions.append(f'<a href="/admin/application/{m.id}">{"Review Application" if m.status != "Approved" else "View Application"}</a>')
        if m.status != 'Approved':
            actions.append(f'<a href="/admin/approve/{m.id}">Approve</a>')
        if m.fee_status != 'Paid':
            actions.append(f'<a href="/admin/member/{m.id}/fee-paid">Mark fee paid</a>')
        if m.membership_number:
            actions.append(f'<a href="/member-card/{html.escape(m.membership_number)}.pdf">Member card PDF</a>')
        if m.status == 'Approved' and current_admin() and current_admin().role == 'superadmin':
            actions.append(f'<a href="/admin/member/{m.id}/delete" style="color:#a32222;font-weight:700">Delete Approved Member</a>')
        rows.append(
            f'<tr><td>{html.escape(m.name)}</td><td>{html.escape(m.application_code)}</td>'
            f'<td>{html.escape(m.status)}</td><td>{html.escape(m.fee_status)}</td>'
            f'<td>{" | ".join(actions)}</td></tr>'
        )
    table = ''.join(rows) or '<tr><td colspan="5">No applications yet.</td></tr>'
    return f'''<div style="font-family:Arial,sans-serif;max-width:1200px;margin:30px auto;padding:20px">
    <h1>GDA Member Management</h1>
    <p><a href="/admin">← Admin Dashboard</a> &nbsp; <a href="/admin/approved-members-pdf">📄 Print Approved Members PDF</a> &nbsp; <a href="/admin/logout">Logout</a></p>
    <p style="color:#607086">Approved members can be deleted by a Super Admin if an application was approved by mistake.</p>
    <table style="width:100%;border-collapse:collapse">
    <tr><th style="text-align:left;padding:10px;border-bottom:1px solid #ddd">Name</th><th style="text-align:left;padding:10px;border-bottom:1px solid #ddd">Application</th><th style="text-align:left;padding:10px;border-bottom:1px solid #ddd">Status</th><th style="text-align:left;padding:10px;border-bottom:1px solid #ddd">Fee</th><th style="text-align:left;padding:10px;border-bottom:1px solid #ddd">Actions</th></tr>
    {table}</table>
    </div>'''

@app.route('/admin/approved-members-pdf')
@_admin_required
def approved_members_pdf():
    members = Member.query.filter_by(status='Approved').order_by(Member.name.asc()).all()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    title_style.alignment = TA_CENTER
    story = [
        Paragraph('Greater Dhaka Association, Denmark', title_style),
        Paragraph('Approved Members List — Established 2026', styles['Heading2']),
        Spacer(1, 12)
    ]
    data = [['No.', 'Member Name', 'Membership Number', 'Member Since', 'Fee']]
    for i, m in enumerate(members, 1):
        data.append([
            str(i),
            m.name or '',
            m.membership_number or '',
            m.created_at.strftime('%d %B %Y') if m.created_at else '',
            m.fee_status or 'Unpaid'
        ])
    if len(data) == 1:
        data.append(['—', 'No approved members yet', '—', '—', '—'])
    table = Table(data, colWidths=[35, 170, 115, 95, 55], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0b3768')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd7e4')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f4f8fc')]),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph(f'Total approved members: {len(members)}', styles['Normal']))
    story.append(Spacer(1, 8))
    story.append(Paragraph('Greater Dhaka Association, Denmark · সম্প্রীতি · সংস্কৃতি · কল্যাণ', styles['Normal']))
    doc.build(story)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='GDA_Denmark_Approved_Members_List.pdf', mimetype='application/pdf')


@app.route('/admin/member/<int:member_id>/delete', methods=['GET','POST'])
@_superadmin_required
def delete_approved_member(member_id):
    member = Member.query.get_or_404(member_id)
    if member.status != 'Approved':
        return redirect(url_for('admin_manage'))
    if request.method == 'POST':
        db.session.delete(member)
        db.session.commit()
        return redirect(url_for('admin_manage'))
    name = html.escape(member.name)
    membership = html.escape(member.membership_number or 'No membership number')
    return f'''<div style="font-family:Arial,sans-serif;max-width:720px;margin:60px auto;padding:30px;background:#fff;border:1px solid #ddd;border-radius:14px">
    <h1 style="color:#a32222">Delete Approved Member?</h1>
    <p>You are about to permanently delete:</p>
    <p><strong>Name:</strong> {name}<br><strong>Membership Number:</strong> {membership}</p>
    <p style="color:#a32222"><strong>This cannot be undone.</strong> The member record will be removed, and the membership number will no longer verify or generate a member card.</p>
    <form method="post" style="display:flex;gap:10px;flex-wrap:wrap">
      <button type="submit" style="background:#a32222;color:#fff;border:0;border-radius:8px;padding:12px 18px;font-weight:700">Yes, Delete Member</button>
      <a href="/admin/manage" style="padding:12px 18px;background:#eef3f8;border-radius:8px;color:#0b3768;text-decoration:none">Cancel</a>
    </form>
    </div>'''

@app.route('/admin/member/<int:member_id>/fee-paid')
@_admin_required
def mark_fee_paid(member_id):
    member = Member.query.get_or_404(member_id)
    member.fee_status = 'Paid'
    db.session.commit()
    return redirect(url_for('admin_manage'))

application = app
