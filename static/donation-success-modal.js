(function(){
  function init(){
    var flash=document.querySelector('.flash.success');
    if(!flash)return;
    var message=flash.textContent.trim();
    flash.remove();

    var style=document.createElement('style');
    style.textContent=''+
      '.donation-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:20px;z-index:100000}'+
      '.donation-modal{position:relative;width:min(620px,100%);background:#102c3a;border:1px solid #49d3a0;border-radius:24px;padding:34px 28px 28px;box-shadow:0 24px 80px rgba(0,0,0,.55);text-align:center;color:#f4f8fa}'+
      '.donation-modal h2{margin:0 35px 16px;font-size:28px}'+
      '.donation-modal p{margin:0;color:#dcecf2;line-height:1.6;font-size:17px}'+
      '.donation-modal-close{position:absolute;right:14px;top:10px;width:38px;height:38px;border:0;border-radius:50%;background:transparent;color:#fff;font-size:30px;line-height:1;cursor:pointer}'+
      '.donation-modal-close:hover{background:#ffffff18}';
    document.head.appendChild(style);

    var overlay=document.createElement('div');
    overlay.className='donation-modal-overlay';
    overlay.setAttribute('role','dialog');
    overlay.setAttribute('aria-modal','true');
    overlay.innerHTML='<div class="donation-modal"><button class="donation-modal-close" type="button" aria-label="Fermer">×</button><h2>❤️ Merci pour elle !</h2><p></p></div>';
    overlay.querySelector('p').textContent=message;
    document.body.appendChild(overlay);

    function close(){overlay.remove();document.removeEventListener('keydown',onKey);}
    function onKey(e){if(e.key==='Escape')close();}
    overlay.querySelector('.donation-modal-close').addEventListener('click',close);
    overlay.addEventListener('click',function(e){if(e.target===overlay)close();});
    document.addEventListener('keydown',onKey);
    overlay.querySelector('.donation-modal-close').focus();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
