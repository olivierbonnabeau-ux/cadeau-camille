import csv, io, os, secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

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

def seed():
    if Activity.query.count() == 0:
        for i, (emoji,title,desc,target) in enumerate(ACTIVITIES):
            db.session.add(Activity(emoji=emoji,title=title,description=desc,target=target,sort_order=i))
        db.session.commit()

with app.app_context():
    db.create_all()
    seed()

def admin_ok(): return session.get('admin') is True

def total_pledges(): return db.session.query(func.coalesce(func.sum(Pledge.amount),0)).scalar() or 0

@app.route('/')
def home():
    acts = Activity.query.filter_by(active=True).order_by(Activity.sort_order, Activity.id).all()
    total = total_pledges()
    return render_template('index.html', activities=acts, total=total, goal=4800)

@app.post('/promesse')
def pledge():
    try:
        name=request.form['name'].strip(); contact=request.form['contact'].strip(); amount=float(request.form['amount']); activity_id=int(request.form['activity_id']); message=request.form.get('message','').strip()
        if not name or not contact or amount <= 0: raise ValueError()
        activity=Activity.query.get_or_404(activity_id)
        db.session.add(Pledge(activity=activity,name=name,contact=contact,amount=amount,message=message))
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
        elif action=='activity':
            a=Activity.query.get_or_404(int(request.form['id'])); a.title=request.form['title'].strip(); a.description=request.form['description'].strip(); a.target=float(request.form['target']); a.active='active' in request.form; db.session.commit()
        return redirect(url_for('admin'))
    pledges=Pledge.query.order_by(Pledge.created_at.desc()).all()
    acts=Activity.query.order_by(Activity.sort_order, Activity.id).all()
    return render_template('admin.html', pledges=pledges, activities=acts, total=total_pledges(), goal=4800)

@app.get('/admin/export.csv')
def export_csv():
    if not admin_ok(): return redirect(url_for('login'))
    out=io.StringIO(); w=csv.writer(out); w.writerow(['Date','Nom','Contact','Activité','Montant','Statut','Message'])
    for p in Pledge.query.order_by(Pledge.created_at).all(): w.writerow([p.created_at.isoformat(),p.name,p.contact,p.activity.title if p.activity else '',p.amount,p.status,p.message])
    return Response('\ufeff'+out.getvalue(), mimetype='text/csv', headers={'Content-Disposition':'attachment; filename=promesses-camille.csv'})

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=True)
