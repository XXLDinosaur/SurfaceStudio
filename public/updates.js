/* Updates are desktop-host operations; web pages cannot select arbitrary executables. */
(() => {
  let api=null,status=null,started=false,polling=false;
  const badge=document.createElement('button');badge.id='update-badge';badge.className='sidebar-update';badge.textContent='更新';badge.title='发现新版本，查看更新';badge.setAttribute('aria-label','发现新版本，查看更新');badge.hidden=true;badge.onclick=()=>window.openUpdates();$('.sidebar-bottom').append(badge);
  function render(){
    badge.hidden=!['available','ready'].includes(status?.phase);
    if(!$('#update-state'))return;
    $('#update-state').textContent=status?.message||'请在桌面版 SS 中检查更新';
    $('#update-current').textContent=status?.current||library?.releaseNotes?.version||'—';
    $('#update-notes').textContent=status?.notes||'';
    $('#update-auto').checked=status?.autoCheck!==false;
    $('#update-auto').disabled=!api;
    const busy=['checking','downloading','handoff'].includes(status?.phase);
    $('#update-check').disabled=!api||busy;
    const button=$('#update-install');button.hidden=!['available','ready','downloading','handoff'].includes(status?.phase);button.disabled=busy;
    button.textContent=status?.phase==='ready'?'安装并重启':status?.phase==='downloading'?`下载中 ${status.progress||0}%`:'下载更新';
  }
  async function refresh(){if(!api||polling)return;polling=true;try{status=await api.update_status();render()}catch{}finally{polling=false}}
  window.openUpdates=()=>{
    modal('软件更新',`<p class="modal-description">当前版本 <b id="update-current">—</b> · GitHub 正式版本</p><label class="check-label"><input type="checkbox" id="update-auto">自动检查更新（安装前由你确认）</label><p id="update-state" class="form-note" role="status"></p><pre id="update-notes" style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:240px;overflow:auto;font:inherit;font-size:var(--read-secondary)"></pre><p class="form-note">更新会保留材质库路径及整理记录。安装前请保存并关闭 Blender，以便同时更新插件；SS 会在安装器就绪后退出。</p><div class="modal-actions"><button id="update-check" class="outline-button">检查更新</button><button id="update-install" class="primary-button" hidden>下载更新</button></div>`,'SURFACE STUDIO UPDATE');
    $('#update-check').onclick=async()=>{try{status=await api.check_updates();render()}catch(e){toast(e.message)}};
    $('#update-auto').onchange=async e=>{status=await api.set_auto_updates(e.target.checked);render()};
    $('#update-install').onclick=async()=>{
      try{
        const r=status.phase==='ready'?await api.install_update():await api.download_update();
        if(r.error)toast(r.error);
        await refresh();
      }catch(e){toast(e.message)}
    };
    render();refresh();
  };
  async function start(){
    if(started||!window.pywebview?.api?.update_status)return;
    started=true;api=window.pywebview.api;await refresh();
    setTimeout(async()=>{try{if(status?.autoCheck){await api.check_updates();await refresh()}}catch{}},5000);
    setInterval(refresh,1500);
    setInterval(async()=>{try{if(status?.autoCheck&&!['downloading','ready','handoff'].includes(status.phase))await api.check_updates()}catch{}},6*60*60*1000);
  }
  window.addEventListener('pywebviewready',start);start();
})();
