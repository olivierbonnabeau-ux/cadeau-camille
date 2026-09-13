import os
from jinja2 import FileSystemLoader
from app import app

app.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app.jinja_loader = FileSystemLoader(app.template_folder)

@app.after_request
def frontend_fixes(response):
    if response.content_type and 'text/html' in response.content_type:
        html = response.get_data(as_text=True)
        patch = r'''<script>
(function(){
  var IMAGES={
    'Tromsø':['/static/images/tromso.png','/static/images/tromso_01.jpeg','/static/images/tromso_02.jpeg'],
    'Les îles Lofoten':['/static/images/lofoten.png','/static/images/lofoten_01.jpeg','/static/images/lofoten_02.jpeg'],
    "S'endormir sous les aurores boréales dans des cabanes au bout du monde":['/static/images/cabin.png','/static/images/cabane_aa_01.jpeg','/static/images/cabane_aa_02.jpeg','/static/images/cabane_aa_03.jpeg']
  };
  window.setGallery=function(id,n){var g=document.querySelector('[data-gallery="'+id+'"]');if(!g)return;var a=[].slice.call(g.querySelectorAll('img')),d=[].slice.call(g.querySelectorAll('.dotg'));if(!a.length)return;n=((n%a.length)+a.length)%a.length;a.forEach(function(x,i){x.classList.toggle('active',i===n)});d.forEach(function(x,i){x.classList.toggle('active',i===n)});g.dataset.index=n};
  window.moveGallery=function(id,n){var g=document.querySelector('[data-gallery="'+id+'"]');setGallery(id,(parseInt(g&&g.dataset.index||0,10)||0)+n)};
  function buildChoices(){
    var s=document.querySelector('select[name="activity_id"]');
    if(!s||document.getElementById('activites'))return;
    var sec=document.createElement('section');sec.id='activites';
    sec.innerHTML='<h2 class="sectiontitle">🎁 Choisissez votre souvenir</h2><p class="intro">Chaque catégorie correspond à une partie de l’aventure que vous pouvez soutenir.</p><div class="cards"></div>';
    var grid=sec.querySelector('.cards');
    [].slice.call(s.options).forEach(function(o){
      if(!o.value)return;
      var title=(o.textContent||'').replace(/^[^A-Za-zÀ-ÿ0-9]+\s*/,'').replace(/\s+—.*$/,'').trim();
      var card=document.createElement('article');card.className='card activity-card';card.dataset.title=title;
      card.innerHTML='<div class="gallery"></div><div class="cardbody"><h3></h3><p>Choisissez cette catégorie pour participer à cette partie du voyage.</p><button class="btn" type="button">Choisir cette catégorie</button></div>';
      card.querySelector('h3').textContent=title;
      var gallery=card.querySelector('.gallery'),pics=IMAGES[title]||[];
      pics.forEach(function(src,i){var img=document.createElement('img');img.src=src;if(i===0)img.className='active';gallery.appendChild(img)});
      if(pics.length>1){
        var id='choice'+grid.children.length;gallery.dataset.gallery=id;
        ['‹','›'].forEach(function(txt,i){var b=document.createElement('button');b.className='arrow '+(i?'next':'prev');b.textContent=txt;b.onclick=function(){moveGallery(id,i?1:-1)};gallery.appendChild(b)});
        var dots=document.createElement('div');dots.className='dots';pics.forEach(function(_,i){var d=document.createElement('span');d.className='dotg'+(i?'':' active');d.onclick=function(){setGallery(id,i)};dots.appendChild(d)});gallery.appendChild(dots);
      }
      card.querySelector('.btn').onclick=function(){s.value=o.value;s.dispatchEvent(new Event('change'));var p=document.getElementById('promesse');if(p)p.scrollIntoView({behavior:'smooth'})};
      grid.appendChild(card);
    });
    var anchor=document.getElementById('promesse');if(anchor)anchor.parentNode.insertBefore(sec,anchor.nextSibling);
  }
  document.addEventListener('DOMContentLoaded',buildChoices);
})();
</script>'''
        response.set_data(html.replace('</body>',patch+'</body>'))
    return response
