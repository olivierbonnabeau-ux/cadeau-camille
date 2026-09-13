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

ACTIVITIES = [
    ('✈️', 'Avion', 'Les vols de l’aventure : Paris → Tromsø → Bodø → Oslo → Paris.', 256),
    ('🌌', 'Tromsø', 'Trois nuits à Tromsø pour découvrir la ville, le port, les cafés et profiter des possibilités d’aurores boréales.', 380),
    ('🐋', 'Croisière Aurore Boréale et Safari Baleine', '24 h en mer : safari baleine, recherche d’aurores, cabine double, dîner, petit-déjeuner et déjeuner inclus. Reste offert par Olivier.', 1215),
    ('🏔️', 'Les îles Lofoten', 'Découverte de Sakrisøy, Reine, Hamnøy, des fjords et des montagnes qui plongent dans la mer.', 192.50),
    ('🛖', "S'endormir sous les aurores boréales dans des cabanes au bout du monde", 'Cabine vitrée à Å : patio et vue mer + montagne + Façade vitrée pour les aurores boréales.', 173.50),
    ('⛴️', 'Traversée Bodø → Moskenes', 'Traversée piétonne Bodø → Moskenes.', 39),
    ('🏙️', 'Oslo', 'Après notre périple dans le Grand Nord, nous poserons nos valises à Oslo pour profiter de la capitale et terminer ce voyage en douceur.', 160),
    ('🍽️', 'Repas & gourmandises', 'Des spécialités norvégiennes végétariennes, des repas chauds, des gaufres au brunost, des brioches à la cannelle et quelques gourmandises locales.', 330),
]

IMAGE_MAP = {
    'Avion': ['/static/images/avion.png'],
    'Tromsø': ['/static/images/tromso.png', '/static/images/tromso_01.jpeg', '/static/images/tromso_02.jpeg'],
    'Croisière Aurore Boréale et Safari Baleine': ['/static/images/quest.png', '/static/images/orca.png', '/static/images/aurora.png'],
    'Les îles Lofoten': ['/static/images/lofoten.png', '/static/images/lofoten_01.jpeg', '/static/images/lofoten_02.jpeg'],
    "S'endormir sous les aurores boréales dans des cabanes au bout du monde": ['/static/images/cabin.png', '/static/images/cabane_aa_01.jpeg', '/static/images/cabane_aa_02.jpeg', '/static/images/cabane_aa_03.jpeg'],
    'Traversée Bodø → Moskenes': ['/static/images/ferry.png'],
    'Oslo': ['/static/images/oslo_palace.png', '/static/images/oslo_port.png', 'https://imageio.forbes.com/specials-images/imageserve/67780d31ab136252656d799b/0x0.jpg?fit=bounds&format=jpg&height=900&width=1600'],
    'Repas & gourmandises': ['/static/images/waffles.png', '/static/images/kanelboller.png', '/static/images/lefse.png', '/static/images/rommegrot.png', '/static/images/lefse_savory.png', '/static/images/sandwich.png', '/static/images/potatoes_mushrooms.png'],
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

PROMISES = {
    'Croisière Aurore Boréale et Safari Baleine': 'Une photo en exclusivité des aurores boréales.',
    'Avion': 'Camille devra aller au travail en vélo cet hiver pour rattraper son empreinte carbone.',
    'Tromsø': 'Camille vous enverra une carte postale de l’endroit le plus au nord de la Planète.',
    'Les îles Lofoten': 'Camille devra prononcer 3 fois correctement Kjærlighet devant vous.',
    "S'endormir sous les aurores boréales dans des cabanes au bout du monde": 'Vous envoyez une photo de la vue, sans se la raconter.',
    'Traversée Bodø → Moskenes': 'Camille vous chantera une petite chanson de marin norvégienne !',
    'Oslo': 'Camille vous fera écouter sa chanson norvégienne préférée du voyage.',
    'Repas & gourmandises': 'Camille mangera à votre santé sa gourmandise norvégienne préférée du voyage',
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
        for alias in aliases:
            old = by_title.get(alias)
            if old and old.id != activity.id:
                Pledge.query.filter_by(activity_id=old.id).update({'activity_id': activity.id})
                old.active = False
                used_ids.add(old.id)
    for activity in Activity.query.all():
        if activity.id not in used_ids:
            activity.active = False
    db.session.commit()

with app.app_context():
    db.create_all()
    ensure_schema()
    sync_activities()

def images_for(activity):
    imgs = IMAGE_MAP.get(activity.title, [])
    return imgs or [FALLBACK_IMAGE]

def total_pledges():
    # Afficher le total de toutes les promesses de don enregistrées.
    return db.session.query(func.coalesce(func.sum(Pledge.amount), 0)).scalar() or 0

def admin_ok():
    return session.get('admin') is True

@app.route('/')
def home():
    activities = Activity.query.filter_by(active=True).order_by(Activity.sort_order).all()
    total = total_pledges()
    goal = 1531.5
    messages = Pledge.query.order_by(Pledge.created_at.desc()).all()
    return render_template('index.html', activities=activities, total=total, goal=goal, image_for=lambda a: images_for(a)[0], images_for=images_for, promises=PROMISES, messages=messages)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        expected = os.environ.get('ADMIN_PASSWORD', '')
        if expected and secrets.compare_digest(password, expected):
            session['admin'] = True
            return redirect(url_for('admin'))
        flash('Mot de passe incorrect.', 'error')
    return render_template('login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not admin_ok():
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        action = request.form.get('action')
        pledge_id = request.form.get('pledge_id', type=int)
        if action == 'delete_pledge' and pledge_id:
            pledge = db.session.get(Pledge, pledge_id)
            if pledge:
                db.session.delete(pledge)
                db.session.commit()
                flash('Promesse supprimée.', 'success')
        elif action == 'toggle_status' and pledge_id:
            pledge = db.session.get(Pledge, pledge_id)
            if pledge:
                pledge.status = 'confirmé' if pledge.status != 'confirmé' else 'promesse'
                db.session.commit()
                flash('Statut mis à jour.', 'success')
        elif action == 'toggle_public' and pledge_id:
            pledge = db.session.get(Pledge, pledge_id)
            if pledge:
                pledge.public_message = not pledge.public_message
                db.session.commit()
                flash('Visibilité du message mise à jour.', 'success')
        elif action == 'edit_activity':
            activity_id = request.form.get('activity_id', type=int)
            activity = db.session.get(Activity, activity_id)
            if activity:
                activity.title = request.form.get('title', activity.title)
                activity.description = request.form.get('description', activity.description)
                activity.target = request.form.get('target', type=float) or activity.target
                db.session.commit()
                flash('Activité mise à jour.', 'success')
        return redirect(url_for('admin'))
    pledges = Pledge.query.order_by(Pledge.created_at.desc()).all()
    public_messages = Pledge.query.filter(Pledge.public_message.is_(True), Pledge.message.isnot(None), Pledge.message != '').order_by(Pledge.created_at.desc()).all()
    activities = Activity.query.order_by(Activity.sort_order).all()
    total = total_pledges()
    return render_template('admin.html', pledges=pledges, public_messages=public_messages, activities=activities, total=total)

@app.route('/admin/export.csv')
def admin_export():
    if not admin_ok():
        return redirect(url_for('admin_login'))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nom', 'Contact', 'Montant', 'Activité', 'Statut', 'Message', 'Public', 'Date'])
    for p in Pledge.query.order_by(Pledge.created_at.desc()).all():
        writer.writerow([p.name, p.contact, p.amount, p.activity.title if p.activity else '', p.status, p.message or '', 'oui' if p.public_message else 'non', p.created_at.isoformat() if p.created_at else ''])
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=promesses-cadeau-camille.csv'})

@app.route('/pledge', methods=['POST'])
def pledge():
    activity_id = request.form.get('activity_id', type=int)
    activity = db.session.get(Activity, activity_id) if activity_id else None
    if not activity or not activity.active:
        flash('Choisissez une activité valide.', 'error')
        return redirect(url_for('home'))
    if activity.title == 'Croisière Aurore Boréale et Safari Baleine':
        flash('Cette activité est déjà offerte par Olivier.', 'error')
        return redirect(url_for('home'))
    name = request.form.get('name', '').strip()
    contact = request.form.get('contact', '').strip()
    amount = request.form.get('amount', type=float)
    message = request.form.get('message', '').strip()
    if not name or not contact or not amount or amount <= 0:
        flash('Merci de renseigner votre nom, votre contact et un montant valide.', 'error')
        return redirect(url_for('home'))
    p = Pledge(activity_id=activity.id, name=name, contact=contact, amount=amount, message=message, public_message=True, status='promesse')
    db.session.add(p)
    db.session.commit()
    flash('Merci pour elle ! Votre don a bien été enregistré, on se recontacte quand nous procéderons aux réservations pour que Camille puisse récupérer sa part.', 'success')
    return redirect(url_for('home'))

@app.errorhandler(Exception)
def handle_exception(e):
    db.session.rollback()
    return 'Internal Server Error', 500
