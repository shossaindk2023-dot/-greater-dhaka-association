import os, secrets, io
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template_string, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6
import qrcode

app = Flask(__name__)  # GDA Denmark production app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
db_url = os.getenv('DATABASE_URL', 'sqlite:///gda.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default='admin', nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

def current_admin():
    admin_id = session.get('admin_id')
    if admin_id:
        return db.session.get(AdminUser, admin_id)
    return None

def admin_ok():
    admin = current_admin()
    if admin and admin.active:
        return True
    return bool(session.get('admin'))

def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not admin_ok(): return redirect(url_for('admin_login'))
        return fn(*a, **kw)
    return wrapper

def superadmin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        admin = current_admin()
        if not admin or not admin.active or admin.role != 'superadmin':
            return redirect(url_for('admin_dashboard'))
        return fn(*a, **kw)
    return wrapper

def page(title, body, **ctx):
    description = ctx.pop('description', 'Greater Dhaka Association, Denmark (GDA Denmark) — a non-profit, non-political social, cultural and welfare association established in 2026.')
    site_url = request.url_root.rstrip('/')
    canonical = request.base_url
    base = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{{description}}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{{canonical}}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Greater Dhaka Association, Denmark">
<meta property="og:title" content="{{title}} | GDA Denmark">
<meta property="og:description" content="{{description}}">
<meta property="og:url" content="{{canonical}}">
<meta name="theme-color" content="#0b3768">
<title>{{title}} | GDA Denmark</title>
<style>
:root{--navy:#0b3768;--navy2:#06264b;--red:#d71920;--green:#08783f;--gold:#b98a2d;--ink:#172b45;--muted:#607086;--paper:#fff;--soft:#f4f8fc}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--soft);color:var(--ink);line-height:1.6}
a{color:var(--navy);text-decoration:none}
.topbar{height:4px;background:linear-gradient(90deg,var(--green) 0 33%,#fff 33% 66%,var(--red) 66%)}
header{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.97);backdrop-filter:blur(10px);border-bottom:1px solid #dbe4ee;box-shadow:0 3px 18px rgba(6,38,75,.07)}
.nav{max-width:1220px;margin:auto;min-height:82px;padding:10px 22px;display:flex;align-items:center;gap:22px}
.brand{display:flex;align-items:center;gap:13px;margin-right:auto;min-width:245px}
.brand img{width:62px;height:62px;object-fit:contain}
.brand-text{line-height:1.08}
.brand-title{font-family:Georgia,serif;font-size:22px;font-weight:800;color:var(--navy)}
.brand-sub{font-family:Georgia,serif;font-size:15px;color:var(--navy);font-weight:700;text-align:center;margin-top:3px}
.brand-motto{font-size:12px;color:var(--green);font-weight:700;text-align:center;margin-top:5px;letter-spacing:.5px}
nav{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
nav a{font-weight:650;font-size:14px;color:#183c65;padding:8px 2px;border-bottom:2px solid transparent}
nav a:hover{color:var(--red);border-color:var(--red)}
.nav-admin{background:var(--navy);color:#fff!important;padding:10px 15px!important;border-radius:24px;box-shadow:0 5px 14px rgba(11,55,104,.18)}
.hero{position:relative;overflow:hidden;min-height:520px;display:flex;align-items:center;background:linear-gradient(110deg,rgba(255,255,255,.94) 0%,rgba(255,255,255,.78) 48%,rgba(255,255,255,.12) 100%),linear-gradient(135deg,#cfe8fb,#f7fbff);border-bottom:1px solid #d7e4ef}
.hero:before{content:'';position:absolute;inset:0;background:radial-gradient(circle at 82% 30%,rgba(185,138,45,.16),transparent 28%),radial-gradient(circle at 15% 80%,rgba(8,120,63,.10),transparent 25%)}
.hero:after{content:'';position:absolute;right:4%;top:50%;transform:translateY(-50%);width:min(470px,43vw);height:min(470px,43vw);background:url('/static/img/gda-logo.png') center/contain no-repeat;opacity:.16;filter:drop-shadow(0 15px 30px rgba(6,38,75,.12));pointer-events:none}
.hero-inner{max-width:1220px;width:100%;margin:auto;padding:70px 22px;position:relative;z-index:2}
.eyebrow{font-size:13px;letter-spacing:3px;font-weight:800;color:var(--navy);text-transform:uppercase}
.hero h1{font-family:Georgia,serif;font-size:clamp(38px,5vw,68px);line-height:1.05;max-width:720px;margin:12px 0 14px;color:var(--navy2)}
.motto{display:flex;align-items:center;gap:13px;font-size:24px;font-weight:800;color:var(--green);margin:10px 0 18px}
.motto:before,.motto:after{content:'';height:2px;width:52px;background:var(--red)}
.hero p{max-width:650px;font-size:18px;color:#38516d;margin:0 0 25px}
.actions{display:flex;gap:12px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;justify-content:center;background:var(--navy);color:#fff;border:1px solid var(--navy);border-radius:28px;padding:12px 21px;font-weight:750;box-shadow:0 8px 20px rgba(11,55,104,.18)}
.btn:hover{transform:translateY(-1px)}
.btn.alt{background:#fff;color:var(--navy);box-shadow:none}
.quick{background:#fff;border-bottom:1px solid #e2eaf2}
.quick-grid{max-width:1220px;margin:auto;display:grid;grid-template-columns:repeat(4,1fr)}
.quick-item{padding:27px 20px;text-align:center;border-right:1px solid #e3eaf2}
.quick-item:last-child{border-right:0}
.quick-icon{width:48px;height:48px;border-radius:50%;display:grid;place-items:center;margin:0 auto 9px;background:#edf5fb;font-size:22px}
.quick h3{margin:0 0 4px;color:var(--navy);font-size:17px}
.quick p{margin:0;color:var(--muted);font-size:14px}
.wrap{max-width:1220px;margin:0 auto;padding:54px 22px}
.section-head{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:22px}
.section-head h2{font-family:Georgia,serif;color:var(--navy);font-size:31px;margin:0}
.section-head p{margin:5px 0 0;color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.card{background:var(--paper);padding:27px;border:1px solid #e1e9f2;border-radius:18px;box-shadow:0 8px 28px rgba(6,38,75,.06);margin:0}
.card h2,.card h3{color:var(--navy);margin-top:0}
.card p{color:#53657a}
.feature{position:relative;overflow:hidden}
.feature:before{content:'';position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--green)}
.feature:nth-child(2):before{background:var(--red)}
.feature:nth-child(3):before{background:var(--gold)}
.news-grid{display:grid;grid-template-columns:1.15fr .85fr;gap:20px}
.list-item{display:flex;gap:15px;padding:15px 0;border-bottom:1px solid #e7edf3}
.list-item:last-child{border-bottom:0}
.datebox{min-width:58px;height:58px;border-radius:10px;background:#edf4fb;text-align:center;padding:7px 4px;color:var(--navy);font-weight:800;font-size:12px}
.datebox strong{display:block;font-size:19px;line-height:1}
.list-item h3{font-size:16px;margin:0;color:var(--navy)}
.list-item p{font-size:14px;margin:3px 0;color:var(--muted)}
.cta{margin:0 22px 54px;border-radius:22px;overflow:hidden;background:linear-gradient(110deg,var(--navy2),var(--navy));color:#fff}
.cta-inner{max-width:1220px;margin:auto;padding:42px 36px;display:flex;align-items:center;justify-content:space-between;gap:25px}
.cta h2{font-family:Georgia,serif;margin:0 0 7px;font-size:31px}
.cta p{margin:0;color:#dbe8f5}
.cta .btn{background:#fff;color:var(--navy);border-color:#fff}
.page-hero{background:linear-gradient(120deg,var(--navy2),var(--navy));color:#fff;padding:54px 22px}
.page-hero h1{max-width:1220px;margin:0 auto;font-family:Georgia,serif;font-size:42px}
input,textarea,select{width:100%;padding:12px 13px;margin:6px 0 14px;border:1px solid #cbd7e4;border-radius:9px;box-sizing:border-box;background:#fff}
button{background:var(--navy);color:#fff;border:0;border-radius:9px;padding:12px 18px;font-weight:700;cursor:pointer}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden}
th,td{padding:11px;border-bottom:1px solid #e4eaf1;text-align:left}
footer{background:var(--navy2);color:#d8e4f0;margin-top:0}
.footer-inner{max-width:1220px;margin:auto;padding:38px 22px;display:flex;justify-content:space-between;gap:20px;align-items:center}
.footer-title{font-family:Georgia,serif;font-size:18px;color:#fff}
.footer-motto{color:#fff;font-weight:700}
.footer-tag{font-style:italic;color:#cbd9e8}
.pw-wrap{position:relative}.pw-wrap input{padding-right:115px}.pw-toggle{position:absolute;right:6px;top:6px;padding:8px 10px;background:#eef3f8;color:var(--navy);border:0;border-radius:6px;font-size:12px}
.muted{color:var(--muted)}.ok{color:#176b36}.warn{color:#9b5b00}.danger{color:#a32222}
@media(max-width:950px){nav{gap:10px}.nav{flex-wrap:wrap}.brand{min-width:210px}.hero:after{opacity:.10}.cards{grid-template-columns:1fr}.news-grid{grid-template-columns:1fr}.quick-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:650px){.nav{padding:10px 14px}.brand img{width:52px;height:52px}.brand-title{font-size:18px}.brand-sub{font-size:13px}.hero{min-height:600px}.hero-inner{padding:55px 18px}.hero:after{width:330px;height:330px;right:-75px;top:70%;opacity:.11}.hero h1{font-size:39px}.motto{font-size:20px}.quick-grid{grid-template-columns:1fr 1fr}.quick-item{padding:20px 8px}.wrap{padding:42px 16px}.cta{margin:0 16px 42px}.cta-inner{padding:32px 22px;display:block}.cta .btn{margin-top:20px}.footer-inner{display:block;text-align:center}.footer-tag{margin-top:8px}}
</style>
<script>function togglePassword(id,btn){var x=document.getElementById(id);if(!x)return;if(x.type==='password'){x.type='text';btn.textContent='Hide password'}else{x.type='password';btn.textContent='Show password'}}</script>
</head>
<body>
<div class="topbar"></div>
<header><div class="nav">
<a class="brand" href="/">
<img src="/static/img/gda-logo.png" alt="Greater Dhaka Association, Denmark logo">
<div class="brand-text"><div class="brand-title">Greater Dhaka Association</div><div class="brand-sub">Denmark</div><div class="brand-motto">সম্প্রীতি · সংস্কৃতি · কল্যাণ</div></div>
</a>
<nav>
<a href="/">Home</a><a href="/about">About</a><a href="/committee">Committee</a><a href="/constitution">Constitution</a><a href="/news">News &amp; Events</a><a href="/membership-fee">Membership Fee</a><a href="/register">Join Us</a><a href="/contact">Contact</a><a class="nav-admin" href="/admin/login">Admin Login</a>
</nav>
</div></header>
''' + body + '''
<footer><div class="footer-inner"><div><div class="footer-title">Greater Dhaka Association, Denmark</div><div>Established 2026 · Harmony, Culture and Welfare</div></div><div class="footer-motto">সম্প্রীতি · সংস্কৃতি · কল্যাণ</div><div class="footer-tag">Connecting Cultures, Supporting Lives ♡</div></div></footer>
</body></html>'''
    return render_template_string(base, title=title, description=description, canonical=canonical, site_url=site_url, **ctx)

with app.app_context():
    db.create_all()
    if AdminUser.query.count() == 0:
        seed_user = os.getenv('ADMIN_USERNAME', 'admin').strip() or 'admin'
        seed_password = os.getenv('ADMIN_PASSWORD', 'change-this')
        db.session.add(AdminUser(username=seed_user, password_hash=generate_password_hash(seed_password), role='superadmin', active=True))
        db.session.commit()
    if not Setting.query.filter_by(key='fee_amount').first():
        for k in ['fee_amount','bank_name','iban','mobilepay','contact_email','contact_phone']:
            set_setting(k, '')
        db.session.commit()

@app.route('/robots.txt')
def robots():
    site = request.url_root.rstrip('/')
    return app.response_class(f'User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /member-card/\nSitemap: {site}/sitemap.xml\n', mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap():
    site = request.url_root.rstrip('/')
    paths = ['/', '/about', '/constitution', '/committee', '/news', '/membership-fee', '/register', '/status', '/contact']
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{site}{p}</loc></url>' for p in paths) + '</urlset>'
    return app.response_class(xml, mimetype='application/xml')

@app.route('/')
def home():
    news_rows=News.query.order_by(News.created_at.desc()).limit(3).all()
    news_html=''.join(f'<div class="list-item"><div class="datebox"><strong>{x.created_at:%d}</strong>{x.created_at:%b}</div><div><h3>{x.title}</h3><p>{x.body[:150]}{"..." if len(x.body)>150 else ""}</p></div></div>' for x in news_rows)
    if not news_html:
        news_html='<div class="list-item"><div class="datebox"><strong>—</strong></div><div><h3>Welcome to GDA Denmark</h3><p>Community news and announcements will appear here.</p></div></div>'
    return page('Home',f'''<section class="hero"><div class="hero-inner"><div class="eyebrow">WELCOME TO OUR COMMUNITY</div><h1>Greater Dhaka Association, Denmark</h1><div class="motto">সম্প্রীতি · সংস্কৃতি · কল্যাণ</div><p>Bringing together the people of Greater Dhaka, preserving our culture, supporting our community and building a stronger future in Denmark.</p><div class="actions"><a class="btn" href="/register">Join Our Association&nbsp; →</a><a class="btn alt" href="/about">Learn More</a></div></div></section>
<section class="quick"><div class="quick-grid"><div class="quick-item"><div class="quick-icon">👥</div><h3>Our Community</h3><p>United by our roots, stronger together.</p></div><div class="quick-item"><div class="quick-icon">🌿</div><h3>Culture &amp; Heritage</h3><p>Preserving our culture and identity.</p></div><div class="quick-item"><div class="quick-icon">🤝</div><h3>Support &amp; Welfare</h3><p>Helping each other and our community.</p></div><div class="quick-item"><div class="quick-icon">📅</div><h3>Events &amp; Activities</h3><p>Stay connected with our activities.</p></div></div></section>
<div class="wrap"><div class="section-head"><div><h2>What We Stand For</h2><p>Our work is guided by community, culture and welfare.</p></div></div><div class="cards"><div class="card feature"><h3>Community</h3><p>Connecting people from Greater Dhaka and creating a welcoming community in Denmark.</p></div><div class="card feature"><h3>Culture &amp; Heritage</h3><p>Celebrating Bangladeshi language, traditions, history and the heritage of Greater Dhaka.</p></div><div class="card feature"><h3>Welfare</h3><p>Supporting members and families through mutual assistance, information and community initiatives.</p></div></div></div>
<div class="wrap" style="padding-top:0"><div class="news-grid"><div class="card"><div class="section-head"><div><h2 style="font-size:26px">Latest News</h2><p>Updates from the association.</p></div><a href="/news">View all →</a></div>{news_html}</div><div class="card"><div class="section-head"><div><h2 style="font-size:26px">Get Involved</h2><p>Be part of our growing community.</p></div></div><p>Become a member, take part in cultural activities and help build a supportive community for everyone.</p><p><a class="btn" href="/register">Become a Member</a></p><p><a href="/membership-fee">View membership fee information →</a></p></div></div></div>
<section class="cta"><div class="cta-inner"><div><h2>Together, we can build a stronger community.</h2><p>Connecting cultures, supporting lives and keeping our roots alive in Denmark.</p></div><a class="btn" href="/contact">Contact Us →</a></div></section>''', description='Greater Dhaka Association, Denmark (GDA Denmark) — connecting the Greater Dhaka community through harmony, culture and welfare.')

@app.route('/about')
def about(): return page('About','''<div class="wrap"><div class="card"><h1>About GDA Denmark</h1><p>Greater Dhaka Association, Denmark was established in 2026. The association aims to promote harmony, Bangladeshi culture and community welfare.</p><p><b>Motto:</b> Harmony, Culture and Welfare</p><p><b>বাংলা:</b> সম্প্রীতি, সংস্কৃতি ও কল্যাণ</p></div></div>''', description='Learn about Greater Dhaka Association, Denmark, established in 2026 to promote harmony, Bangladeshi culture and community welfare.')

@app.route('/constitution')
def constitution(): return page('Constitution','''<div class="wrap"><div class="card"><h1>Constitution</h1><p>The association operates as a non-profit, non-political social, cultural and welfare organisation in accordance with applicable Danish law.</p><p>Its aims include community unity, cultural activities, language and heritage, welfare support, education, sports and mutual assistance.</p></div></div>''', description='The constitution and aims of Greater Dhaka Association, Denmark, a non-profit and non-political community association.')

@app.route('/committee')
def committee():
    rows=Committee.query.order_by(Committee.sort_order, Committee.id).all()
    body='<div class="wrap"><div class="card"><h1>Committee</h1><div class="grid">'
    body += ''.join(f'<div><h3>{x.name}</h3><b>{x.position}</b><p class="muted">{x.bio}</p></div>' for x in rows) or '<p class="muted">Committee information will be published here.</p>'
    return page('Committee',body+'</div></div></div>', description='Committee and leadership information for Greater Dhaka Association, Denmark.')

@app.route('/news')
def news():
    rows=News.query.order_by(News.created_at.desc()).all()
    body='<div class="wrap"><div class="card"><h1>News & Events</h1>'
    body += ''.join(f'<article><h2>{x.title}</h2><p>{x.body}</p><small class="muted">{x.created_at:%d %B %Y}</small><hr></article>' for x in rows) or '<p class="muted">No announcements yet.</p>'
    return page('News & Events',body+'</div></div>', description='News, announcements and community events from Greater Dhaka Association, Denmark.')

@app.route('/membership-fee')
def membership_fee():
    return page('Membership Fee',f'''<div class="wrap"><div class="card"><h1>Membership Fee</h1><p><b>Fee:</b> {setting('fee_amount') or 'To be announced'}</p><p><b>Bank:</b> {setting('bank_name') or 'To be announced'}</p><p><b>IBAN:</b> {setting('iban') or 'To be announced'}</p><p><b>MobilePay:</b> {setting('mobilepay') or 'To be announced'}</p><p class="muted">After payment, keep your payment reference for the association administrator.</p></div></div>''', description='Membership fee and payment information for Greater Dhaka Association, Denmark.')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        email=request.form.get('email','').strip().lower()
        if Member.query.filter_by(email=email).first(): return page('Already Applied','<div class="wrap"><div class="card"><h1>Already Applied</h1><p>An application with this email already exists.</p></div></div>')
        code='GDA-'+secrets.token_hex(6).upper()
        m=Member(application_code=code,name=request.form['name'],father_name=request.form['father_name'],grandfather_name=request.form['grandfather_name'],address_bd=request.form['address_bd'],address_dk=request.form['address_dk'],nationality_birth='',nationality_current='',date_of_birth='',email=email,phone=request.form['phone'])
        db.session.add(m); db.session.commit()
        return page('Application Submitted',f'''<div class="wrap"><div class="card"><h1>Application Submitted</h1><p>Your application reference is:</p><h2>{code}</h2><p>Please save this reference to check your application status.</p><a class="btn" href="/status?code={code}">Check Status</a></div></div>''')
    return page('Membership Application','''<div class="wrap"><div class="card"><h1>Membership Application</h1><form method="post"><label>Name</label><input name="name" required><label>Father's Name</label><input name="father_name" required><label>Grandfather's Name</label><input name="grandfather_name" required><label>Address in Bangladesh</label><textarea name="address_bd" required></textarea><label>Present Address in Denmark</label><textarea name="address_dk" required></textarea><label>Email</label><input type="email" name="email" required><label>Phone</label><input name="phone" required><button>Submit Application</button></form></div></div>''', description='Apply online for membership in Greater Dhaka Association, Denmark.')

@app.route('/status')
def status():
    code=request.args.get('code','').strip()
    result=Member.query.filter_by(application_code=code).first() if code else None
    found=f'<div class="card"><h2>{result.name}</h2><p>Status: <b>{result.status}</b></p><p>Fee: <b>{result.fee_status}</b></p><p>Application reference: {result.application_code}</p></div>' if result else ''
    return page('Application Status',f'''<div class="wrap"><div class="card"><h1>Application Status</h1><form><input name="code" placeholder="GDA-XXXXXXXXXXXX" value="{code}" required><button>Check Status</button></form></div>{found}</div>''', description='Check the status of a Greater Dhaka Association, Denmark membership application.')

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
    return page('Contact','''<div class="wrap"><div class="card"><h1>Contact</h1><form method="post"><label>Name</label><input name="name" required><label>Email</label><input type="email" name="email" required><label>Message</label><textarea name="message" rows="6" required></textarea><button>Send Message</button></form></div></div>''', description='Contact Greater Dhaka Association, Denmark.')

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        username=request.form.get('username','').strip()
        password=request.form.get('password','')
        admin=AdminUser.query.filter_by(username=username).first()
        if admin and admin.active and check_password_hash(admin.password_hash,password):
            session.clear()
            session['admin']=True
            session['admin_id']=admin.id
            session['admin_username']=admin.username
            session['admin_role']=admin.role
            return redirect(url_for('admin_dashboard'))
        return page('Admin Login','<div class="wrap"><div class="card"><p class="danger">Invalid username or password.</p></div></div>')
    body = '<div class="wrap"><div class="card"><h1>Admin Login</h1><p class="muted">Each administrator can use their own account.</p><form method="post"><input name="username" placeholder="Username" required><div class="pw-wrap"><input id="login-password" type="password" name="password" placeholder="Password" required><button type="button" class="pw-toggle" onclick="togglePassword(&quot;login-password&quot;,this)">Show password</button></div><button>Login</button></form></div></div>'
    return page('Admin Login', body)

@app.route('/admin/logout')
def admin_logout(): session.clear(); return redirect(url_for('home'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    members=Member.query.order_by(Member.created_at.desc()).all()
    rows=''.join(f'<tr><td>{m.name}</td><td>{m.application_code}</td><td>{m.status}</td><td>{m.fee_status}</td><td>{("<a href=/admin/approve/"+str(m.id)+">Approve</a>") if m.status=="Pending" else ""}</td></tr>' for m in members)
    admin=current_admin()
    user_link = '<a href="/admin/users">Admin Users</a> · ' if admin and admin.role == 'superadmin' else ''
    links = user_link + '<a href="/admin/manage">Member Management</a> · <a href="/admin/change-password">Change Password</a> · <a href="/admin/settings">Website Settings</a> · <a href="/admin/news">News</a> · <a href="/admin/committee">Committee</a> · <a href="/admin/messages">Messages</a> · <a href="/admin/logout">Logout</a>'
    body = '<div class="wrap"><div class="card"><h1>Admin Dashboard</h1><p>' + links + '</p></div><div class="card"><h2>Members</h2><table><tr><th>Name</th><th>Application</th><th>Status</th><th>Fee</th><th>Action</th></tr>' + rows + '</table></div></div>'
    return page('Admin Dashboard', body)

@app.route('/admin/change-password',methods=['GET','POST'])
@admin_required
def admin_change_password():
    admin=current_admin()
    if not admin:
        return redirect(url_for('admin_login'))
    if request.method=='POST':
        current=request.form.get('current_password','')
        new_password=request.form.get('new_password','')
        confirm=request.form.get('confirm_password','')
        if not check_password_hash(admin.password_hash,current):
            return page('Change Password','<div class="wrap"><div class="card"><p class="danger">Current password is incorrect.</p></div></div>')
        if len(new_password) < 8:
            return page('Change Password','<div class="wrap"><div class="card"><p class="danger">New password must be at least 8 characters.</p></div></div>')
        if new_password != confirm:
            return page('Change Password','<div class="wrap"><div class="card"><p class="danger">New passwords do not match.</p></div></div>')
        admin.password_hash=generate_password_hash(new_password)
        db.session.commit()
        return page('Password Changed','<div class="wrap"><div class="card"><h1>Password Changed</h1><p>Your password has been updated successfully.</p><p><a href="/admin">Back to Admin Dashboard</a></p></div></div>')
    body = '<div class="wrap"><div class="card"><h1>Change Password</h1><form method="post"><label>Current Password</label><div class="pw-wrap"><input id="current-password" type="password" name="current_password" required><button type="button" class="pw-toggle" onclick="togglePassword(&quot;current-password&quot;,this)">Show password</button></div><label>New Password</label><div class="pw-wrap"><input id="new-password" type="password" name="new_password" minlength="8" required><button type="button" class="pw-toggle" onclick="togglePassword(&quot;new-password&quot;,this)">Show password</button></div><label>Confirm New Password</label><div class="pw-wrap"><input id="confirm-password" type="password" name="confirm_password" minlength="8" required><button type="button" class="pw-toggle" onclick="togglePassword(&quot;confirm-password&quot;,this)">Show password</button></div><button>Change Password</button></form></div></div>'
    return page('Change Password', body)

@app.route('/admin/users',methods=['GET','POST'])
@superadmin_required
def admin_users():
    if request.method=='POST':
        username=request.form.get('username','').strip()
        password=request.form.get('password','')
        role=request.form.get('role','admin')
        if not username or not password:
            return page('Admin Users','<div class="wrap"><div class="card"><p class="danger">Username and password are required.</p></div></div>')
        if role not in ('admin','superadmin'): role='admin'
        if AdminUser.query.filter_by(username=username).first():
            return page('Admin Users','<div class="wrap"><div class="card"><p class="danger">That username already exists.</p><p><a href="/admin/users">Back</a></p></div></div>')
        db.session.add(AdminUser(username=username,password_hash=generate_password_hash(password),role=role,active=True))
        db.session.commit()
        return redirect(url_for('admin_users'))
    admins=AdminUser.query.order_by(AdminUser.username).all()
    current=current_admin()
    rows=''
    for a in admins:
        action='Current account' if a.id == current.id else f'<a href="/admin/users/{a.id}/toggle">{"Deactivate" if a.active else "Activate"}</a>'
        rows += f'<tr><td>{a.username}</td><td>{a.role}</td><td>{"Active" if a.active else "Inactive"}</td><td>{action}</td></tr>'
    body = '<div class="wrap"><div class="card"><h1>Admin Users</h1><p><a href="/admin">Admin Dashboard</a></p><form method="post"><label>Username</label><input name="username" required><label>Password</label><div class="pw-wrap"><input id="new-admin-password" type="password" name="password" required><button type="button" class="pw-toggle" onclick="togglePassword(&quot;new-admin-password&quot;,this)">Show password</button></div><label>Role</label><select name="role"><option value="admin">Admin</option><option value="superadmin">Super Admin</option></select><button>Add Admin</button></form></div><div class="card"><h2>Existing Accounts</h2><table><tr><th>Username</th><th>Role</th><th>Status</th><th>Action</th></tr>' + rows + '</table><p class="muted">Only Super Admin can add or deactivate administrator accounts.</p></div></div>'
    return page('Admin Users', body)

@app.route('/admin/users/<int:user_id>/toggle')
@superadmin_required
def toggle_admin_user(user_id):
    admin=AdminUser.query.get_or_404(user_id)
    if admin.id == current_admin().id:
        return redirect(url_for('admin_users'))
    admin.active=not admin.active
    db.session.commit()
    return redirect(url_for('admin_users'))

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

@app.route('/google827a650554bab237.html')
def google_site_verification():
    return 'google-site-verification: google827a650554bab237.html', 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/admin/manage')
@admin_required
def admin_manage():
    members=Member.query.order_by(Member.created_at.desc()).all()
    rows=[]
    for m in members:
        actions=[]
        if m.status != 'Approved':
            actions.append('<a href="/admin/approve/' + str(m.id) + '">Approve</a>')
        if m.fee_status != 'Paid':
            actions.append('<a href="/admin/member/' + str(m.id) + '/fee-paid">Mark fee paid</a>')
        if m.membership_number:
            actions.append('<a href="/member-card/' + m.membership_number + '.pdf">Member card PDF</a>')
        action_text=' | '.join(actions) if actions else '-'
        rows.append('<tr><td>' + m.name + '</td><td>' + m.application_code + '</td><td>' + m.status + '</td><td>' + m.fee_status + '</td><td>' + action_text + '</td></tr>')
    table=''.join(rows) if rows else '<tr><td colspan="5">No applications yet.</td></tr>'
    body='<div class="wrap"><div class="card"><h1>GDA Member Management</h1><p><a href="/admin">Admin Dashboard</a> | <a href="/admin/logout">Logout</a></p><table><tr><th>Name</th><th>Application</th><th>Status</th><th>Fee</th><th>Actions</th></tr>' + table + '</table></div></div>'
    return page('Member Management', body)

@app.route('/admin/member/<int:member_id>/fee-paid')
@admin_required
def mark_fee_paid(member_id):
    m=Member.query.get_or_404(member_id)
    m.fee_status='Paid'
    db.session.commit()
    return redirect(url_for('admin_manage'))

@app.route('/health')
def health(): return {'status':'ok'}

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)))
