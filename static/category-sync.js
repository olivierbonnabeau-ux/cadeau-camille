(function(){
  function norm(s){return String(s||'').replace(/^[^A-Za-zÀ-ÿ0-9\s]*\s*/,'').trim();}
  function sync(){
    var select=document.querySelector('select[name="activity_id"]');
    var section=document.getElementById('restored-categories');
    if(!select||!section)return;
    var value=select.value;
    var option=select.options[select.selectedIndex];
    var title=norm(option?option.textContent:'');
    var cards=section.querySelectorAll('.restored-card');
    var found=false;
    cards.forEach(function(card){
      var h=card.querySelector('h3');
      var match=h && norm(h.textContent)===title;
      card.style.display=match?'block':'none';
      if(match){found=true;card.classList.add('selected-category');}
      else card.classList.remove('selected-category');
    });
    if(!found && value){
      cards.forEach(function(card){card.style.display='block';});
    }
  }
  function install(){
    var select=document.querySelector('select[name="activity_id"]');
    if(!select)return;
    select.addEventListener('change',sync);
    sync();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
  var observer=new MutationObserver(function(){install();sync();});
  observer.observe(document.documentElement,{childList:true,subtree:true});
})();
