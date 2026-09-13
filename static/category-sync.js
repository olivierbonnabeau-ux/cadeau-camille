(function(){
  'use strict';

  var PROMISES = {
    'Avion': 'Camille devra aller au travail en vélo cet hiver pour rattraper son empreinte carbone.',
    'Tromsø': 'Camille vous enverra une carte postale de l’endroit le plus au nord de la Planète.',
    'Croisière Aurore Boréale et Safari Baleine': 'Une photo en exclusivité des aurores boréales.',
    'Les îles Lofoten': 'Camille devra prononcer 3 fois correctement Kjærlighet devant vous.',
    "S'endormir sous les aurores boréales dans des cabanes au bout du monde": 'Vous envoyez une photo de la vue, sans se la raconter.',
    'Traversée Bodø → Moskenes': 'Camille vous chantera une petite chanson de marin norvégienne !',
    'Oslo': 'Camille vous fera écouter sa chanson norvégienne préférée du voyage.',
    'Repas & gourmandises': 'Camille mangera à votre santé sa gourmandise norvégienne préférée du voyage'
  };

  function cleanTitle(text){
    return String(text || '')
      .replace(/^\s*[^A-Za-zÀ-ÿ0-9]+\s*/, '')
      .replace(/\s+—\s+offerte par Olivier\s*$/,'')
      .trim();
  }

  function getCards(){
    return Array.prototype.slice.call(document.querySelectorAll('#activites .activity-card'));
  }

  function getCardFor(option, index){
    var cards = getCards();
    var wanted = cleanTitle(option ? option.textContent : '');
    for(var i=0;i<cards.length;i++){
      var heading = cards[i].querySelector('h3');
      if(heading && cleanTitle(heading.textContent) === wanted) return cards[i];
    }
    return cards[index] || null;
  }

  function updatePreview(select){
    if(!select) return;
    var option = select.options[select.selectedIndex];
    if(!option) return;

    var index = select.selectedIndex;
    var card = getCardFor(option, index);
    if(!card) return;

    var img = card.querySelector('img');
    var heading = card.querySelector('h3');
    var paragraphs = card.querySelectorAll('.cardbody p');
    var desc = '';
    for(var i=0;i<paragraphs.length;i++){
      if(!paragraphs[i].classList.contains('gift-note')){
        desc = paragraphs[i].textContent.trim();
        break;
      }
    }

    var title = cleanTitle(heading ? heading.textContent : option.textContent);
    var titleWithEmoji = heading ? heading.textContent.trim() : option.textContent.trim();
    var promise = PROMISES[title] || 'Une attention personnalisée depuis le voyage.';

    var selectedImg = document.getElementById('selected-img');
    var selectedTitle = document.getElementById('selected-title');
    var selectedDesc = document.getElementById('selected-desc');
    var selectedPromise = document.getElementById('selected-promise');

    if(selectedImg && img){
      selectedImg.src = img.currentSrc || img.src;
      selectedImg.alt = title;
    }
    if(selectedTitle) selectedTitle.textContent = titleWithEmoji;
    if(selectedDesc) selectedDesc.textContent = desc;
    if(selectedPromise) selectedPromise.textContent = promise;
  }

  function install(){
    var select = document.getElementById('activity');
    if(!select || select.dataset.categorySyncInstalled === '1') return;
    select.dataset.categorySyncInstalled = '1';
    select.addEventListener('change', function(){ updatePreview(select); });
    updatePreview(select);
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', install);
  }else{
    install();
  }
})();
