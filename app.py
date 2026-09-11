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

@app.after_request
def final_frontend_fixes(response):
    if response.content_type and 'text/html' in response.content_type:
        html = response.get_data(as_text=True)
        html = html.replace(' · La croisière est offerte séparément par Olivier et n’entre pas dans l’effort d’épargne.', '')
        html = html.replace(" · La croisière est offerte séparément par Olivier et n'entre pas dans l'effort d'épargne.", '')
        patch = r'''<script>
(function(){
  var activityPrices={
    'Avion':256,
    'Tromsø':380,
    'Croisière Aurore Boréale et Safari Baleine':1215,
    'Les îles Lofoten':192.50,
    "S'endormir sous les aurores boréales dans des cabanes au bout du monde":173.50,
    'Traversée Bodø → Moskenes':39,
    'Oslo':160,
    'Repas & gourmandises':330
  };
  var activityPromises={
    'Avion':'Camille devra aller au travail en vélo cet hiver pour rattraper son empreinte carbone.',
    'Tromsø':'Camille vous enverra une carte postale de l’endroit le plus au nord de la Planète.',
    'Croisière Aurore Boréale et Safari Baleine':'Une photo en exclusivité des aurores boréales.',
    'Les îles Lofoten':'Camille devra prononcer 3 fois correctement Kjærlighet devant vous.',
    "S'endormir sous les aurores boréales dans des cabanes au bout du monde":'Vous envoyez une photo de la vue, sans se la raconter.',
    'Traversée Bodø → Moskenes':'Camille vous chantera une petite chanson de marin norvégienne !',
    'Oslo':'Camille vous fera écouter sa chanson norvégienne préférée du voyage.',
    'Repas & gourmandises':'Camille mangera à votre santé sa gourmandise norvégienne préférée du voyage'
  };
  function getSelectedTitle(){
    var select=document.querySelector('select[name="activity_id"],#activity');
    if(!select || !select.options.length) return '';
    var option=select.options[select.selectedIndex];
    return (option.textContent||'').replace(/\s+—\s+offerte par Olivier\s*$/,'').trim().replace(/^[^A-Za-zÀ-ÿ0-9]+\s*/,'');
  }
  function getCardData(title){
    var cards=document.querySelectorAll('#activites .activity-card');
    for(var i=0;i<cards.length;i++){
      var h=cards[i].querySelector('h3');
      if(!h) continue;
      var cardTitle=(h.textContent||'').trim().replace(/^[^A-Za-zÀ-ÿ0-9]+\s*/,'');
      if(cardTitle===title || cardTitle.indexOf(title)>=0){
        var img=cards[i].querySelector('.media img, .gallery img');
        var p=cards[i].querySelector('.cardbody > p');
        var price=cards[i].querySelector('.price');
        return {title:cardTitle, img:img?img.src:'', desc:p?p.textContent.trim():'', price:price?price.textContent.trim():''};
      }
    }
    return null;
  }
  function ensurePriceElement(){
    var preview=document.querySelector('.selected-preview');
    if(!preview) return null;
    var content=preview.querySelector(':scope > div');
    if(!content) return null;
    var price=document.getElementById('selected-price');
    if(!price){
      price=document.createElement('div');
      price.id='selected-price';
      price.style.cssText='font-size:20px;font-weight:800;margin:0 0 10px;color:#f5d58a;';
      var title=content.querySelector('#selected-title');
      if(title) content.insertBefore(price,title);
      else content.prepend(price);
    }
    return price;
  }
  function updateActivity(id){
    var select=document.querySelector('select[name="activity_id"],#activity');
    if(select && id!=null) select.value=String(id);
    var title=getSelectedTitle();
    var card=getCardData(title);
    if(!card) return;
    var img=document.getElementById('selected-img');
    var h=document.getElementById('selected-title');
    var p=document.getElementById('selected-desc');
    var promise=document.getElementById('selected-promise');
    if(img && card.img){img.src=card.img;img.alt=title;}
    if(h) h.textContent=(card.title||title);
    if(p) p.textContent=card.desc||'';
    if(promise) promise.textContent=activityPromises[title]||'';
    var price=ensurePriceElement();
    if(price){
      var amount=activityPrices[title];
      price.textContent='💶 Montant du poste : '+(amount===undefined?'':(Number.isInteger(amount)?amount:amount.toFixed(2))+' €');
    }
  }
  window.showActivity=updateActivity;
  window.chooseActivity=function(id){
    var select=document.querySelector('select[name="activity_id"],#activity');
    if(select) select.value=String(id);
    updateActivity(id);
    var target=document.getElementById('promesse');
    if(target) target.scrollIntoView({behavior:'smooth'});
  };
  window.setGallery=function(id,index){
    var g=document.querySelector('[data-gallery="'+id+'"]');
    if(!g) return;
    var imgs=Array.prototype.slice.call(g.querySelectorAll('img'));
    var dots=Array.prototype.slice.call(g.querySelectorAll('.dotg'));
    if(!imgs.length) return;
    index=((Number(index)||0)%imgs.length+imgs.length)%imgs.length;
    imgs.forEach(function(img,n){img.classList.toggle('active',n===index);});
    dots.forEach(function(dot,n){dot.classList.toggle('active',n===index);});
    g.dataset.index=String(index);
  };
  window.moveGallery=function(id,delta){
    var g=document.querySelector('[data-gallery="'+id+'"]');
    if(!g) return;
    var current=parseInt(g.dataset.index||'0',10)||0;
    window.setGallery(id,current+(Number(delta)||0));
  };
  document.addEventListener('DOMContentLoaded',function(){
    ensurePriceElement();
    var select=document.querySelector('select[name="activity_id"],#activity');
    if(select){
      select.addEventListener('change',function(){updateActivity(this.value);});
      updateActivity(select.value);
    }
    document.querySelectorAll('[data-gallery]').forEach(function(g){if(!g.dataset.index)g.dataset.index='0';});
  });
})();
</script>'''
        html = html.replace('</body>', patch + '</body>')
        response.set_data(html)
    return response

def admin_ok():
    return session.get('admin') is True

def total_pledges():
    return db.session.query(func.coalesce(func.sum(Pledge.amount), 0)).join(Activity, Pledge.activity_id == Activity.id).filter(Activity.active.is_(True), Activity.title != 'Croisière Aurore Boréale et Safari Baleine').scalar() or 0

def images_for(activity):
    return IMAGE_MAP.get(activity.title, [FALLBACK_IMAGE])

@app.route('/')
def home():
    activities = Activity.query.filter_by(active=True).order_by(Activity.sort_order).all()
    total = total_pledges()
    goal = 1531.5
    return render_template('index.html', activities=activities, total=total, goal=goal, images_for=images_for, promises=PROMISES)

@app.route('/pledge', methods=['POST'])
def pledge():
    name = request.form.get('name','').strip()
    contact = request.form.get('contact','').strip()
    message = request.form.get('message','').strip()
    amount_raw = request.form.get('amount','').strip().replace(',','.')
    activity_id = request.form.get('activity_id')
    if not name or not contact or not amount_raw or not activity_id:
        flash('Merci de remplir tous les champs obligatoires.', 'error')
        return redirect(url_for('home') + '#promesse')
    try:
        amount = float(amount_raw)
    except ValueError:
        flash('Le montant indiqué n’est pas valide.', 'error')
        return redirect(url_for('home') + '#promesse')
    activity = db.session.get(Activity, int(activity_id))
    if not activity or not activity.active:
        flash('Cette activité n’est plus disponible.', 'error')
        return redirect(url_for('home') + '#promesse')
    if activity.title == 'Croisière Aurore Boréale et Safari Baleine':
        flash('La croisière est offerte séparément par Olivier et ne peut pas faire l’objet d’une promesse de don.', 'error')
        return redirect(url_for('home') + '#promesse')
    db.session.add(Pledge(activity_id=activity.id, name=name, contact=contact, amount=amount, message=message, public_message=True))
    db.session.commit()
    flash('Merci pour elle ! Votre don a bien été enregistré, on se recontacte quand nous procéderons aux réservations pour que Camille puisse récupérer sa part.', 'success')
    return redirect(url_for('home') + '#promesse')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
