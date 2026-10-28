/* Installed-version notes are bundled and available without network access. */
(() => {
  let attempted=false;
  window.openReleaseNotes=(back=null)=>{
    const notes=library?.releaseNotes;if(!notes)return;
    modal(`SS ${notes.version} 更新说明`, `<p class="modal-description">${esc(notes.title)}<br>${esc(notes.channel)}</p>${notes.sections.map(section=>`<section class="release-section"><h3>${esc(section.title)}</h3><ul>${section.items.map(item=>`<li>${esc(item)}</li>`).join('')}</ul></section>`).join('')}<div class="modal-actions"><button class="primary-button" id="notes-done">${back?'返回材质库设置':'开始使用'}</button></div>`,'本版本更新','680px');
    const dialog=$('#modal');
    const acknowledge=()=>{
      post('/api/release-notes/seen',{version:notes.version}).then(()=>{library.releaseNotesSeen=true}).catch(()=>toast('阅读记录未能保存，下次启动会再次显示'));
      if(back)back();
    };
    dialog.addEventListener('close',acknowledge,{once:true});
    $('#notes-done').onclick=()=>dialog.close();
  };
  const show=()=>{
    if(attempted||!library?.releaseNotes||library.releaseNotesSeen)return;
    if($('#modal').open)return;
    attempted=true;window.openReleaseNotes();
  };
  document.addEventListener('library-loaded',show);
  $('#modal').addEventListener('close',()=>setTimeout(show,0));
  show();
})();
