(() => {
  const sizes = ['standard','comfortable','large'];
  let size = 'comfortable';
  try { const saved=localStorage.getItem('surface-reading-size'); if(sizes.includes(saved))size=saved; } catch {}
  document.documentElement.dataset.reading=size;
  const button=document.createElement('button');
  button.id='reading-settings';button.className='icon-button reading-button';button.textContent='Aa';
  button.title='字号与阅读';button.setAttribute('aria-label','字号与阅读');
  document.querySelector('.topbar-right').prepend(button);
  button.onclick=()=>{
    modal('让阅读更舒服', `<p class="modal-description">选择适合你的字号，界面会立即调整，并自动记住你的选择。</p><div class="reading-options" role="group" aria-label="界面字号"><button class="reading-choice" data-size="standard"><b>Aa</b><span>标准</span></button><button class="reading-choice" data-size="comfortable"><b>Aa</b><span>舒适 · 默认</span></button><button class="reading-choice" data-size="large"><b>Aa</b><span>大字</span></button></div><div class="reading-example"><strong>岩石与自然表面</strong><p>搜索材质、浏览分类，让每一处细节都清晰可见。</p><small>4K 贴图 · 本地素材 · 已连接 Blender</small></div><div class="modal-actions"><button class="primary-button" id="reading-done">完成</button></div>`, '阅读设置', '560px');
    function update(){document.querySelectorAll('[data-size]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.size===size)));}
    document.querySelectorAll('[data-size]').forEach(el=>el.onclick=()=>{
      size=el.dataset.size;document.documentElement.dataset.reading=size;
      try{localStorage.setItem('surface-reading-size',size);}catch{}
      update();
    });
    document.querySelector('#reading-done').onclick=()=>document.querySelector('#modal').close();update();
  };
})();
