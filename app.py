import os, secrets, io
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template_string, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6
import qrcode

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
db_url = os.getenv('DATABASE_URL', 'sqlite:///gda.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_code = db.Column(db.String(32), unique=True, nullable=False)
    membership_number = db.Column(db.String(32), unique=True, nullable=True)
    name = db.Column(db.String(160), nullable=False)
    father_name = db.Column(db.String(160), nullable=False)
    grandfather_name = db.Column(db.String(160), nullable=False)
    address_bd = db.Column(db.Text, nullable=False)
    address_dk = db.Column(db.Text, nullable=False)
    nationality_birth = db.Column(db.String(100), nullable=False)
    nationality_current = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(60), nullable=False)
    status = db.Column(db.String(30), default='Pending', nullable=False)
    fee_status = db.Column(db.String(30), default='Unpaid', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, default='')

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Committee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    position = db.Column(db.String(160), nullable=False)
    bio = db.Column(db.Text, default='')
    sort_order = db.Column(db.Integer, default=0)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default='New')

def setting(key, default=''):
    x = Setting.query.filter_by(key=key).first()
    return x.value if x else default

def set_setting(key, value):
    x = Setting.query.filter_by(key=key).first()
    if not x:
        x = Setting(key=key)
        db.session.add(x)
    x.value = value

def admin_ok():
    return bool(session.get('admin'))

def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not admin_ok(): return redirect(url_for('admin_login'))
        return fn(*a, **kw)
    return wrapper

def page(title, body, **ctx):
    base = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} | GDA Denmark</title><style>body{font-family:Arial,sans-serif;margin:0;background:#f6f7f9;color:#20242a}header{background:#fff;border-bottom:1px solid #ddd;padding:14px 5%;display:flex;gap:18px;align-items:center;flex-wrap:wrap}header a{text-decoration:none;color:#183b63;font-weight:600}.logo{font-size:21px;font-weight:800;margin-right:auto}.hero{background:#183b63;color:#fff;padding:55px 5%}.wrap{max-width:1050px;margin:28px auto;padding:0 18px}.card{background:#fff;padding:24px;border-radius:12px;box-shadow:0 2px 10px #00000010;margin:18px 0}input,textarea,select{width:100%;padding:11px;margin:6px 0 14px;border:1px solid #ccd2da;border-radius:7px;box-sizing:border-box}button,.btn{background:#183b63;color:#fff;border:0;border-radius:7px;padding:11px 16px;text-decoration:none;display:inline-block;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}.muted{color:#68727d}.ok{color:#176b36}.warn{color:#9b5b00}.danger{color:#a32222}table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:10px;border-bottom:1px solid #e4e7eb;text-align:left}footer{text-align:center;padding:35px;color:#69727d}</style></head><body><header><div class="logo">GDA Denmark</div><a href="/">Home</a><a href="/about">About</a><a href="/committee">Committee</a><a href="/constitution">Constitution</a><a href="/news">News & Events</a><a href="/membership-fee">Membership Fee</a><a href="/register">Join</a><a href="/contact">Contact</a></header>'''+body+'''<footer>Greater Dhaka Association, Denmark · Established 2026<br>Harmony, Culture and Welfare</footer></body></html>'''
    return render_template_string(base, title=title, **ctx)

with app.app_context():
    db.create_all()
    if not Setting.query.filter_by(key='fee_amount').first():
        set_setting('fee_amount','')
        set_setting('bank_name','')
        set_setting('iban','')
        set_setting('mobilepay','')
        set_setting('contact_email','')
        set_setting('contact_phone','')
        db.session.commit()

@app.route('/')
def home():
    return page('Home','''<section class="hero"><div class="wrap"><h1>Greater Dhaka Association, Denmark</h1><p>Harmony, Culture and Welfare</p><a class="btn" href="/register">Apply for Membership</a></div></section><div class="wrap"><div class="grid"><div class="card"><h2>Our Association</h2><p>A non-profit, non-political social and cultural association connecting people from Greater Dhaka and supporting community welfare.</p></div><div class="card"><h2>Membership</h2><p>Submit your membership application online and keep your application reference for status checking.</p><a class="btn" href="/status">Check Application</a></div><div class="card"><h2>Verification</h2><p>Approved members can be verified online using their membership number.</p></div></div></div>''')

@app.route('/about')
def about(): return page('About','''<div class="wrap"><div class="card"><h1>About GDA Denmark</h1><p>Greater Dhaka Association, Denmark was established in 2026. The association aims to promote harmony, Bangladeshi culture and community welfare.</p><p><b>Motto:</b> Harmony, Culture and Welfare</p><p><b>বাংলা:</b> সম্প্রীতি, সংস্কৃতি ও কল্যাণ</p></div></div>''')

@app.route('/constitution')
def constitution(): return page('Constitution','''<div class="wrap"><div class="card"><h1>Constitution</h1><p>The association operates as a non-profit, non-political social, cultural and welfare organisation in accordance with applicable Danish law.</p><p>Its aims include community unity, cultural activities, language and heritage, welfare support, education, sports and mutual assistance.</p></div></div>''')

@app.route('/committee')
def committee():
    rows=Committee.query.order_by(Committee.sort_order, Committee.id).all()
    body='<div class="wrap"><div class="card"><h1>Committee</h1><div class="grid">'
    body += ''.join(f'<div><h3>{x.name}</h3><b>{x.position}</b><p class="muted">{x.bio}</p></div>' for x in rows) or '<p class="muted">Committee information will be published here.</p>'
    return page('Committee',body+'</div></div></div>')

@app.route('/news')
def news():
    rows=News.query.order_by(News.created_at.desc()).all()
    body='<div class="wrap"><div class="card"><h1>News & Events</h1>'
    body += ''.join(f'<article><h2>{x.title}</h2><p>{x.body}</p><small class="muted">{x.created_at:%d %B %Y}</small><hr></article>' for x in rows) or '<p class="muted">No announcements yet.</p>'
    return page('News & Events',body+'</div></div>')

@app.route('/membership-fee')
def membership_fee():
    return page('Membership Fee',f'''<div class="wrap"><div class="card"><h1>Membership Fee</h1><p><b>Fee:</b> {setting('fee_amount') or 'To be announced'}</p><p><b>Bank:</b> {setting('bank_name') or 'To be announced'}</p><p><b>IBAN:</b> {setting('iban') or 'To be announced'}</p><p><b>MobilePay:</b> {setting('mobilepay') or 'To be announced'}</p><p class="muted">After payment, keep your payment reference for the association administrator.</p></div></div>''')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        email=request.form.get('email','').strip().lower()
        if Member.query.filter_by(email=email).first(): return page('Already Applied','<div class="wrap"><div class="card"><h1>Already Applied</h1><p>An application with this email already exists.</p></div></div>')
        code='GDA-'+secrets.token_hex(6).upper()
        m=Member(application_code=code,name=request.form['name'],father_name=request.form['father_name'],grandfather_name=request.form['grandfather_name'],address_bd=request.form['address_bd'],address_dk=request.form['address_dk'],nationality_birth=request.form['nationality_birth'],nationality_current=request.form['nationality_current'],date_of_birth=request.form['date_of_birth'],email=email,phone=request.form['phone'])
        db.session.add(m); db.session.commit()
        return page('Application Submitted',f'''<div class="wrap"><div class="card"><h1>Application Submitted</h1><p>Your application reference is:</p><h2>{code}</h2><p>Please save this reference to check your application status.</p><a class="btn" href="/status?code={code}">Check Status</a></div></div>''')
    return page('Membership Application','''<div class="wrap"><div class="card"><h1>Membership Application</h1><form method="post"><label>Name</label><input name="name" required><label>Father's Name</label><input name="father_name" required><label>Grandfather's Name</label><input name="grandfather_name" required><label>Address in Bangladesh</label><textarea name="address_bd" required></textarea><label>Present Address in Denmark</label><textarea name="address_dk" required></textarea><label>Nationality by Birth</label><input name="nationality_birth" required><label>Present Nationality</label><input name="nationality_current" required><label>Date of Birth</label><input name="date_of_birth" required><label>Email</label><input type="email" name="email" required><label>Phone</label><input name="phone" required><button>Submit Application</button></form></div></div>''')

@app.route('/status')
def status():
    code=request.args.get('code','').strip()
    result=Member.query.filter_by(application_code=code).first() if code else None
    found=f'<div class="card"><h2>{result.name}</h2><p>Status: <b>{result.status}</b></p><p>Fee: <b>{result.fee_status}</b></p><p>Application reference: {result.application_code}</p></div>' if result else ''
    return page('Application Status',f'''<div class="wrap"><div class="card"><h1>Application Status</h1><form><input name="code" placeholder="GDA-XXXXXXXXXXXX" value="{code}" required><button>Check Status</button></form></div>{found}</div>''')

@app.route('/verify/<membership_number>')
def verify(membership_number):
    m=Member.query.filter_by(membership_number=membership_number,status='Approved').first()
    if not m: return page('Verification','<div class="wrap"><div class="card"><h1>Not Verified</h1><p class="danger">No approved member was found for this number.</p></div></div>')
    return page('Member Verification',f'<div class="wrap"><div class="card"><h1>Verified Member</h1><h2>{m.name}</h2><p>Membership Number: <b>{m.membership_number}</b></p><p class="ok">Status: Approved</p></div></div>')

@app.route('/member-card/<membership_number>.pdf')
def member_card(membership_number):
    if not admin_ok(): abort(403)
    m=Member.query.filter_by(membership_number=membership_number).first_or_404()
    buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=A6); w,h=A6
    c.setFont('Helvetica-Bold',14); c.drawString(25,h-35,'GREATER DHAKA ASSOCIATION')
    c.setFont('Helvetica',9); c.drawString(25,h-49,'DENMARK · EST. 2026')
    c.setFont('Helvetica-Bold',12); c.drawString(25,h-85,m.name[:40])
    c.setFont('Helvetica',9); c.drawString(25,h-101,'Membership No: '+m.membership_number)
    c.drawString(25,h-116,'Status: Approved')
    qr=qrcode.make(request.url_root.rstrip('/')+'/verify/'+m.membership_number); qbuf=io.BytesIO(); qr.save(qbuf,format='PNG'); qbuf.seek(0)
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(qbuf),w-95,25,width=65,height=65)
    c.save(); buf.seek(0)
    return send_file(buf,as_attachment=True,download_name=m.membership_number+'.pdf',mimetype='application/pdf')

@app.route('/contact',methods=['GET','POST'])
def contact():
    if request.method=='POST':
        db.session.add(Message(name=request.form['name'],email=request.form['email'],message=request.form['message'])); db.session.commit()
        return page('Message Sent','<div class="wrap"><div class="card"><h1>Thank you</h1><p>Your message has been sent to the association.</p></div></div>')
    return page('Contact','''<div class="wrap"><div class="card"><h1>Contact</h1><form method="post"><label>Name</label><input name="name" required><label>Email</label><input type="email" name="email" required><label>Message</label><textarea name="message" rows="6" required></textarea><button>Send Message</button></form></div></div>''')

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        user=os.getenv('ADMIN_USERNAME','admin'); pw=os.getenv('ADMIN_PASSWORD','change-this')
        if request.form.get('username')==user and request.form.get('password')==pw:
            session['admin']=True; return redirect(url_for('admin_dashboard'))
        return page('Admin Login','<div class="wrap"><div class="card"><p class="danger">Invalid login.</p></div></div>')
    return page('Admin Login','''<div class="wrap"><div class="card"><h1>Admin Login</h1><form method="post"><input name="username" placeholder="Username" required><input type="password" name="password" placeholder="Password" required><button>Login</button></form></div></div>''')

@app.route('/admin/logout')
def admin_logout(): session.clear(); return redirect(url_for('home'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    members=Member.query.order_by(Member.created_at.desc()).all()
    rows=''.join(f'<tr><td>{m.name}</td><td>{m.application_code}</td><td>{m.status}</td><td>{m.fee_status}</td><td>{("<a href=/admin/approve/"+str(m.id)+">Approve</a>") if m.status=="Pending" else ""}</td></tr>' for m in members)
    return page('Admin Dashboard',f'''<div class="wrap"><div class="card"><h1>Admin Dashboard</h1><p><a href="/admin/settings">Website Settings</a> · <a href="/admin/news">News</a> · <a href="/admin/committee">Committee</a> · <a href="/admin/messages">Messages</a> · <a href="/admin/logout">Logout</a></p></div><div class="card"><h2>Members</h2><table><tr><th>Name</th><th>Application</th><th>Status</th><th>Fee</th><th>Action</th></tr>{rows}</table></div></div>''')

@app.route('/admin/approve/<int:member_id>')
@admin_required
def approve(member_id):
    m=Member.query.get_or_404(member_id); m.status='Approved'; m.membership_number='GDA-2026-'+str(m.id).zfill(5); db.session.commit(); return redirect(url_for('admin_dashboard'))

@app.route('/admin/settings',methods=['GET','POST'])
@admin_required
def admin_settings():
    keys=['fee_amount','bank_name','iban','mobilepay','contact_email','contact_phone']
    if request.method=='POST':
        for k in keys: set_setting(k,request.form.get(k,''))
        db.session.commit(); return redirect(url_for('admin_settings'))
    fields=''.join(f'<label>{k.replace("_"," ").title()}</label><input name="{k}" value="{setting(k)}">' for k in keys)
    return page('Website Settings',f'<div class="wrap"><div class="card"><h1>Website Settings</h1><form method="post">{fields}<button>Save Settings</button></form></div></div>')

@app.route('/admin/news',methods=['GET','POST'])
@admin_required
def admin_news():
    if request.method=='POST': db.session.add(News(title=request.form['title'],body=request.form['body'])); db.session.commit()
    rows=News.query.order_by(News.created_at.desc()).all()
    listing=''.join(f'<div><h3>{x.title}</h3><p>{x.body}</p></div>' for x in rows)
    return page('Admin News',f'<div class="wrap"><div class="card"><h1>News & Events</h1><form method="post"><input name="title" placeholder="Title" required><textarea name="body" placeholder="Announcement" required></textarea><button>Publish</button></form></div><div class="card">{listing}</div></div>')

@app.route('/admin/committee',methods=['GET','POST'])
@admin_required
def admin_committee():
    if request.method=='POST': db.session.add(Committee(name=request.form['name'],position=request.form['position'],bio=request.form.get('bio',''),sort_order=int(request.form.get('sort_order') or 0))); db.session.commit()
    rows=Committee.query.order_by(Committee.sort_order).all(); listing=''.join(f'<p><b>{x.name}</b> — {x.position}</p>' for x in rows)
    return page('Admin Committee',f'<div class="wrap"><div class="card"><h1>Committee</h1><form method="post"><input name="name" placeholder="Name" required><input name="position" placeholder="Position" required><textarea name="bio" placeholder="Bio"></textarea><input name="sort_order" placeholder="Order"><button>Add Member</button></form></div><div class="card">{listing}</div></div>')

@app.route('/admin/messages')
@admin_required
def admin_messages():
    rows=Message.query.order_by(Message.created_at.desc()).all(); listing=''.join(f'<div class="card"><b>{x.name}</b> ({x.email})<p>{x.message}</p><small>{x.created_at:%d %B %Y %H:%M}</small></div>' for x in rows) or '<p>No messages.</p>'
    return page('Messages','<div class="wrap"><h1>Contact Messages</h1>'+listing+'</div>')

@app.route('/health')
def health(): return {'status':'ok'}

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)))
