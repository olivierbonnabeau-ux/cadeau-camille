import csv, io, os, secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, inspect, text

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
db_url = os.environ.get('DATABASE_URL', 'sqlite:///cadeau.sqlite3')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    emoji = db.Column(db.String(20), default='🎁')
    description = db.Column(db.Text, nullable=False)
    target = db.Column(db.Float, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)

class Pledge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=True)
    name = db.Column(db.String(160), nullable=False)
    contact = db.Column(db.String(240), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    message = db.Column(db.Text, default='')
    public_message = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(30), default='promesse')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activity = db.relationship('Activity', backref='pledges')

# The public collection represents Camille's share of the trip (≈ 2,400 €).
# Targets below are therefore based on half of the estimated 2-person budget.
ACTIVITIES = [
    ('✈️', 'Avion', 'Les vols de l’aventure : Paris → Tromsø → Bodø → Oslo → Paris.', 256),
    ('🌌', 'Tromsø', 'Trois nuits à Tromsø pour découvrir la ville, le port, les cafés et profiter des possibilités d’aurores.', 380),
    ('🐋', 'Croisière Aurore Boréale et Safari Baleine', '24 h en mer : safari baleine, recherche d’aurores, cabine double, dîner, petit-déjeuner et déjeuner inclus.', 607.53),
    ('🏔️', 'Les îles Lofoten', 'Découvrez Sakrisøy, Reine, Hamnøy, les fjords et les montagnes qui plongent dans la mer.', 192.50),
    ('🛖', "S'endormir sous les aurores boréales dans des cabanes au bout du monde", 'Cabin 1 à Å : studio 23 m², cuisine privée, salle de bain, entrée privée, patio et vue mer + montagne.', 173.50),
    ('⛴️', 'Traversée Bodø → Moskenes', 'Traversée piétonne Bodø → Moskenes. Budget prévu : 0 € ; réservation de siège facultative à 65 NOK par personne.', 0),
    ('🏙️', 'Oslo', 'Après notre périple dans le Grand Nord, nous poserons nos valises à Oslo pour profiter de la capitale et terminer ce voyage en douceur.', 160),
    ('🍽️', 'Repas & gourmandises', 'Des spécialités norvégiennes végétariennes, des repas chauds, des gaufres au brunost, des brioches à la cannelle et quelques gourmandises locales.', 330),
]

# Images uploaded/selected for this draft. They are stored locally so the draft is self-contained.
IMAGE_MAP = {
    'Avion': ['/static/images/avion.png'],
    'Tromsø': ['/static/images/tromso.png'],
    'Croisière Aurore Boréale et Safari Baleine': [
        '/static/images/quest.png', '/static/images/orca.png', '/static/images/aurora.png'
    ],
    'Les îles Lofoten': ['/static/images/lofoten.png'],
    "S'endormir sous les aurores boréales dans des cabanes au bout du monde": ['/static/images/cabin.png'],
    'Traversée Bodø → Moskenes': ['/static/images/ferry.png'],
    'Oslo': [
        '/static/images/oslo_palace.png',
        '/static/images/oslo_port.png',
        'https://imageio.forbes.com/specials-images/imageserve/67780d31ab136252656d799b/0x0.jpg?fit=bounds&format=jpg&height=900&width=1600'
    ],
    'Repas & gourmandises': [
        '/static/images/waffles.png', '/static/images/kanelboller.png', '/static/images/lefse.png',
        '/static/images/rommegrot.png', '/static/images/lefse_savory.png', '/static/images/sandwich.png',
        '/static/images/potatoes_mushrooms.png'
    ],
}

OLD_ALIASES = {
    'Avion': ['Les vols de l’aventure'],
    'Tromsø': ['Deux nuits à Tromsø', 'La nuit à Tromsø'],
    'Croisière Aurore Boréale et Safari Baleine': ['L’expédition MV Quest', 'Croisière Aurore Boréale et Safari Baleine'],
    'Les îles Lofoten': ['Les Lofoten — Sakrisøy', 'Les îles Lofoten'],
    "S'endormir sous les aurores boréales dans des cabanes au bout du monde": ['La cabine à Å', "S'endormir sous les aurores boréales dans des cabanes au bout du monde"],
    'Traversée Bodø → Moskenes': ['Les ferries des Lofoten', 'Traversée Bodø → Moskenes'],
    'Oslo': ['Trois nuits à Oslo', 'Oslo'],
    'Repas & gourmandises': ['Les repas & courses', 'Repas & gourmandises'],
}

FALLBACK_IMAGE = '/static/images/lofoten.png'

def ensure_schema():
    inspector = inspect(db.engine)
    cols = {c['name'] for c in inspector.get_columns('pledge')}
    if 'public_message' not in cols:
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE pledge ADD COLUMN public_message BOOLEAN DEFAULT FALSE'))
            conn.execute(text('UPDATE pledge SET public_message = FALSE WHERE public_message IS NULL'))

def sync_activities():
    """Non-destructive update of the existing activity catalog for the new draft."""
    by_title = {a.title: a for a in Activity.query.all()}
    used_ids = set()
    for i, (emoji, title, desc, target) in enumerate(ACTIVITIES):
        aliases = OLD_ALIASES.get(title, [title])
        activity = None
        for alias in aliases:
            if alias in by_title and by_title[alias].id not in used_ids:
                activity = by_title[alias]
                break
        if activity is None:
            activity = Activity(emoji=emoji, title=title, description=desc, target=target, sort_order=i, active=True)
            db.session.add(activity)
            db.session.flush()
        activity.emoji = emoji
        activity.title = title
        activity.description = desc
        activity.target = target
        activity.sort_order = i
        activity.active = True
        used_ids.add(activity.id)
        # Merge duplicate/old aliases into the surviving activity without deleting pledges.
        for alias in aliases:
            old = by_title.get(alias)
            if old and old.id != activity.id:
                Pledge.query.filter_by(activity_id=old.id).update({'activity_id': activity.id})
                old.active = False
                used_ids.add(old.id)

    # Hide activities removed from the public draft (notably the old "extras" category).
    for activity in Activity.query.all():
        if activity.id not in used_ids:
            activity.active = False
    db.session.commit()

with app.app_context():
    db.create_all()
    ensure_schema()
    sync_activities()

def admin_ok():
    return session.get('admin') is True

def total_pledges():
    return db.session.query(func.coalesce(func.sum(Pledge.amount), 0)).scalar() or 0

def images_for(activity):
    return IMAGE_MAP.get(activity.title, [FALLBACK_IMAGE])

def image_for(activity):
    return images_for(activity)[0]

@app.route('/')
def home():
    acts = Activity.query.filter_by(active=True).order_by(Activity.sort_order, Activity.id).all()
    total = total_pledges()
    messages = Pledge.query.filter(Pledge.public_message.is_(True), Pledge.message.isnot(None), Pledge.message != '').order_by(Pledge.created_at.desc()).limit(30).all()
    return render_template('index.html', activities=acts, total=total, goal=2400, messages=messages, image_for=image_for, images_for=images_for)

@app.post('/promesse')
def pledge():
    try:
        name = request.form['name'].strip()
        contact = request.form['contact'].strip()
        amount = float(request.form['amount'])
        activity_id = int(request.form['activity_id'])
        message = request.form.get('message', '').strip()
        public_message = request.form.get('public_message') == 'on'
        if not name or not contact or amount <= 0:
            raise ValueError()
        activity = Activity.query.get_or_404(activity_id)
        db.session.add(Pledge(activity=activity, name=name, contact=contact, amount=amount, message=message, public_message=public_message))
        db.session.commit()
        flash('Merci ! Ta promesse a bien été enregistrée. ❤️', 'success')
    except Exception:
        db.session.rollback()
        flash('Impossible d’enregistrer la promesse. Vérifie les informations.', 'error')
    return redirect(url_for('home') + '#promesse')

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if secrets.compare_digest(request.form.get('password', ''), os.environ.get('ADMIN_PASSWORD', 'camille30')):
            session['admin'] = True
            return redirect(url_for('admin'))
        flash('Mot de passe incorrect.', 'error')
    return render_template('login.html')

@app.get('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not admin_ok():
        return redirect(url_for('login'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'delete':
            p = Pledge.query.get_or_404(int(request.form['id']))
            db.session.delete(p)
            db.session.commit()
            flash('Promesse supprimée.', 'success')
        elif action == 'status':
            p = Pledge.query.get_or_404(int(request.form['id']))
            p.status = request.form.get('status', 'promesse')
            db.session.commit()
        elif action == 'public_message':
            p = Pledge.query.get_or_404(int(request.form['id']))
            p.public_message = request.form.get('public') == '1'
            db.session.commit()
            flash('Visibilité du message mise à jour.', 'success')
        elif action == 'activity':
            a = Activity.query.get_or_404(int(request.form['id']))
            a.title = request.form['title'].strip()
            a.description = request.form['description'].strip()
            a.target = float(request.form['target'])
            a.active = 'active' in request.form
            db.session.commit()
        return redirect(url_for('admin'))
    pledges = Pledge.query.order_by(Pledge.created_at.desc()).all()
    acts = Activity.query.order_by(Activity.sort_order, Activity.id).all()
    public_messages = Pledge.query.filter(Pledge.public_message.is_(True), Pledge.message.isnot(None), Pledge.message != '').order_by(Pledge.created_at.desc()).all()
    return render_template('admin.html', pledges=pledges, activities=acts, public_messages=public_messages, total=total_pledges(), goal=2400, image_for=image_for)

@app.get('/admin/export.csv')
def export_csv():
    if not admin_ok():
        return redirect(url_for('login'))
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['Date', 'Nom', 'Contact', 'Activité', 'Montant', 'Statut', 'Message', 'Message public'])
    for p in Pledge.query.order_by(Pledge.created_at).all():
        w.writerow([p.created_at.isoformat(), p.name, p.contact, p.activity.title if p.activity else '', p.amount, p.status, p.message, 'Oui' if p.public_message else 'Non'])
    return Response('\ufeff' + out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=promesses-camille.csv'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
