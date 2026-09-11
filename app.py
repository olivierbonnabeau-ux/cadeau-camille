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
('✈️','Les vols de l’aventure','Paris → Tromsø → Bodø → Oslo → Paris. Le grand départ et le retour.',512),
('🏨','Deux nuits à Tromsø','Le point de départ pour découvrir Tromsø et son ambiance arctique.',509),
('🐋','L’expédition MV Quest','24 h en mer : baleines, recherche d’aurores, cabine double, dîner et repas inclus.',1215.06),
('🏨','La nuit à Tromsø','Une nuit avec kitchenette avant de mettre le cap sur les Lofoten.',251),
('🏔️','Les Lofoten — Sakrisøy','Deux nuits au cœur des paysages de Reine, Hamnøy et Sakrisøy.',385),
('🌊','La cabine à Å','Une cabine avec cuisine privée, patio et vue mer + montagne.',347),
('🚌','Les déplacements aux Lofoten','Les bus entre Moskenes, Reine, Hamnøy et Å — sans voiture.',39),
('⛴️','Les ferries des Lofoten','La traversée piéton Bodø ↔ Moskenes.',0),
('🏙️','Trois nuits à Oslo','Un appartement près d’Oslo S et Karl Johan pour terminer l’aventure.',320),
('🍽️','Les repas & courses','Courses, repas simples, quelques restaurants et petits plaisirs pendant le voyage.',660),
('🎟️','Les extras de l’aventure','Transports locaux, visites, musées, souvenirs, taxi de secours et imprévus.',545),
]

# Images d'illustration trouvées sur le web pour la V4.
# Elles pourront ensuite être remplacées par des images sous licence choisie pour la mise en ligne définitive.
IMAGE_URLS = {
    'Les vols de l’aventure': 'https://cdn-imgix.headout.com/media/images/e3731c94cbab2f0b6c120433f3f0cf57-AdobeStock-241204676.jpeg?ar=16%3A9&auto=format&crop=faces&fit=crop&h=687.6&q=90&w=1222.4',
    'Deux nuits à Tromsø': 'https://cdn-imgix.headout.com/media/images/e3731c94cbab2f0b6c120433f3f0cf57-AdobeStock-241204676.jpeg?ar=16%3A9&auto=format&crop=faces&fit=crop&h=687.6&q=90&w=1222.4',
    'L’expédition MV Quest': 'https://static.wixstatic.com/media/e1bd66_8a9759fdbd894782899fa85fb2fe99c1~mv2.jpg/v1/fill/w_1000%2Ch_563%2Cal_c%2Cq_85%2Cusm_0.66_1.00_0.01%2Cenc_auto/e1bd66_8a9759fdbd894782899fa85fb2fe99c1~mv2.jpg',
    'La nuit à Tromsø': 'https://www.ncl.com/adobe/dynamicmedia/deliver/dm-aid--3c6054a0-ee85-4748-9048-a6fb5a4d545e/ncl-norway-tromso-cruise-northern-lights-sky-hero.jpg?preferwebp=true&quality=85',
    'Les Lofoten — Sakrisøy': 'https://www.intrepidtravel.com/v3/assets/blt0de87ff52d9c34a8/bltf71636c45aa5d69e/6528b77388bee50f8b87174e/Intrepid-travel-Panoramic-evening-view-of-popular-tourist-destination-Lofoten-Islands-archipelago-Colorful-houses-on-the-shore-of-Norwegian-sea-Wonderful-winter-scene-of-Sakrisoy-fishing-village.shutterstock-1682341456-2560.jpg?auto=webp&branch=prd&crop=2560%2C667%2Coffset-x50%2Coffset-y50&format=pjpg&quality=75&width=2560',
    'La cabine à Å': 'https://www.photopills.com/sites/default/files/articles/2025/18-day-4.1-reine-twilight.jpg',
    'Les déplacements aux Lofoten': 'https://www.intrepidtravel.com/v3/assets/blt0de87ff52d9c34a8/bltf71636c45aa5d69e/6528b77388bee50f8b87174e/Intrepid-travel-Panoramic-evening-view-of-popular-tourist-destination-Lofoten-Islands-archipelago-Colorful-houses-on-the-shore-of-Norwegian-sea-Wonderful-winter-scene-of-Sakrisoy-fishing-village.shutterstock-1682341456-2560.jpg?auto=webp&branch=prd&crop=2560%2C667%2Coffset-x50%2Coffset-y50&format=pjpg&quality=75&width=2560',
    'Les ferries des Lofoten': 'https://www.photopills.com/sites/default/files/articles/2025/18-day-4.1-reine-twilight.jpg',
    'Trois nuits à Oslo': 'https://www.nordicvisitor.com/images/oslo-opera-house-covered-in-snow.jpg',
    'Les repas & courses': 'https://cdn-imgix.headout.com/media/images/e3731c94cbab2f0b6c120433f3f0cf57-AdobeStock-241204676.jpeg?ar=16%3A9&auto=format&crop=faces&fit=crop&h=687.6&q=90&w=1222.4',
    'Les extras de l’aventure': 'https://www.ncl.com/adobe/dynamicmedia/deliver/dm-aid--3c6054a0-ee85-4748-9048-a6fb5a4d545e/ncl-norway-tromso-cruise-northern-lights-sky-hero.jpg?preferwebp=true&quality=85',
}

# For URLs that are pages rather than direct images, use a reliable fallback image.
FALLBACK_IMAGE = 'https://www.photopills.com/sites/default/files/articles/2025/18-day-4.1-reine-twilight.jpg'

def seed():
    if Activity.query.count() == 0:
        for i, (emoji,title,desc,target) in enumerate(ACTIVITIES):
            db.session.add(Activity(emoji=emoji,title=title,description=desc,target=target,sort_order=i))
        db.session.commit()

def ensure_schema():
    """Small non-destructive migration for existing Render databases."""
    inspector = inspect(db.engine)
    cols = {c['name'] for c in inspector.get_columns('pledge')}
    if 'public_message' not in cols:
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE pledge ADD COLUMN public_message BOOLEAN DEFAULT FALSE'))
            conn.execute(text('UPDATE pledge SET public_message = FALSE WHERE public_message IS NULL'))

with app.app_context():
    db.create_all()
    ensure_schema()
    seed()

def admin_ok(): return session.get('admin') is True

def total_pledges(): return db.session.query(func.coalesce(func.sum(Pledge.amount),0)).scalar() or 0

def image_for(activity):
    return IMAGE_URLS.get(activity.title, FALLBACK_IMAGE)

@app.route('/')
def home():
    acts = Activity.query.filter_by(active=True).order_by(Activity.sort_order, Activity.id).all()
    total = total_pledges()
    messages = Pledge.query.filter(Pledge.public_message.is_(True), Pledge.message.isnot(None), Pledge.message != '').order_by(Pledge.created_at.desc()).limit(30).all()
    return render_template('index.html', activities=acts, total=total, goal=4800, messages=messages, image_for=image_for)

@app.post('/promesse')
def pledge():
    try:
        name=request.form['name'].strip(); contact=request.form['contact'].strip(); amount=float(request.form['amount']); activity_id=int(request.form['activity_id']); message=request.form.get('message','').strip()
        public_message = request.form.get('public_message') == 'on'
        if not name or not contact or amount <= 0: raise ValueError()
        activity=Activity.query.get_or_404(activity_id)
        db.session.add(Pledge(activity=activity,name=name,contact=contact,amount=amount,message=message,public_message=public_message))
        db.session.commit(); flash('Merci ! Ta promesse a bien été enregistrée. ❤️','success')
    except Exception:
        db.session.rollback(); flash('Impossible d’enregistrer la promesse. Vérifie les informations.','error')
    return redirect(url_for('home')+'#merci')

@app.route('/admin/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        if secrets.compare_digest(request.form.get('password',''), os.environ.get('ADMIN_PASSWORD','camille30')):
            session['admin']=True; return redirect(url_for('admin'))
        flash('Mot de passe incorrect.','error')
    return render_template('login.html')

@app.get('/admin/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/admin', methods=['GET','POST'])
def admin():
    if not admin_ok(): return redirect(url_for('login'))
    if request.method=='POST':
        action=request.form.get('action')
        if action=='delete':
            p=Pledge.query.get_or_404(int(request.form['id'])); db.session.delete(p); db.session.commit(); flash('Promesse supprimée.','success')
        elif action=='status':
            p=Pledge.query.get_or_404(int(request.form['id'])); p.status=request.form.get('status','promesse'); db.session.commit()
        elif action=='public_message':
            p=Pledge.query.get_or_404(int(request.form['id'])); p.public_message=request.form.get('public') == '1'; db.session.commit(); flash('Visibilité du message mise à jour.','success')
        elif action=='activity':
            a=Activity.query.get_or_404(int(request.form['id'])); a.title=request.form['title'].strip(); a.description=request.form['description'].strip(); a.target=float(request.form['target']); a.active='active' in request.form; db.session.commit()
        return redirect(url_for('admin'))
    pledges=Pledge.query.order_by(Pledge.created_at.desc()).all()
    acts=Activity.query.order_by(Activity.sort_order, Activity.id).all()
    public_messages=Pledge.query.filter(Pledge.public_message.is_(True), Pledge.message.isnot(None), Pledge.message != '').order_by(Pledge.created_at.desc()).all()
    return render_template('admin.html', pledges=pledges, activities=acts, public_messages=public_messages, total=total_pledges(), goal=4800, image_for=image_for)

@app.get('/admin/export.csv')
def export_csv():
    if not admin_ok(): return redirect(url_for('login'))
    out=io.StringIO(); w=csv.writer(out); w.writerow(['Date','Nom','Contact','Activité','Montant','Statut','Message','Message public'])
    for p in Pledge.query.order_by(Pledge.created_at).all():
        w.writerow([p.created_at.isoformat(),p.name,p.contact,p.activity.title if p.activity else '',p.amount,p.status,p.message,'Oui' if p.public_message else 'Non'])
    return Response('\ufeff'+out.getvalue(), mimetype='text/csv', headers={'Content-Disposition':'attachment; filename=promesses-camille.csv'})

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=True)
