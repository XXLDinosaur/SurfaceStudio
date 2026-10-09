/* Workspace layout; preferences never modify the material library. */
(() => {
  const controls = document.createElement('section');
  controls.className = 'workbench-controls';
  controls.setAttribute('aria-label', '材质搜索与筛选');
  document.querySelector('.main-shell').insertBefore(controls, $('#scroll-area'));
  for (const selector of ['.library-tabs', '.toolbar', '#advanced-filters', '#active-filters']) controls.append($(selector));
  $('.tab-caption').textContent = '浏览 · 筛选 · 赋予';
  const featuredToggle = document.createElement('button');
  featuredToggle.className = 'outline-button';
  featuredToggle.id = 'featured-toggle';
  featuredToggle.setAttribute('aria-controls', 'featured');
  $('.tabs').append(featuredToggle);
  function syncFeatured() {
    featuredToggle.textContent = prefs.showFeatured ? '收起专题' : '精选专题';
    featuredToggle.setAttribute('aria-expanded', String(!!prefs.showFeatured));
    if (library) renderResults(true);
  }
  featuredToggle.onclick = () => {
    const expand = $('#featured').hidden;
    preference('showFeatured', expand);
    if (expand && library) navigate();
    syncFeatured(); $('#scroll-area').scrollTop = 0;
  };
  syncFeatured();

  const density = document.createElement('select');
  density.id = 'density-preset'; density.setAttribute('aria-label', '卡片大小');
  density.innerHTML = '<option value="190">紧凑</option><option value="230">标准</option><option value="300">大图</option><option value="custom" hidden>自定义</option>';
  $('.toolbar').insertBefore(density, $('.view-buttons'));
  function syncDensity() {
    const size = Number(prefs.density) || 230;
    density.value = ['190','230','300'].includes(String(size)) ? String(size) : 'custom';
    $('#density').value = size;
    document.documentElement.style.setProperty('--card-size', size + 'px');
  }
  density.onchange = () => { if(density.value === 'custom') return; preference('density', density.value); syncDensity(); gridMode('grid'); };
  $('#density').addEventListener('input', syncDensity);
  syncDensity();
  const clear = document.createElement('button');
  clear.id = 'clear-workbench-filters'; clear.className = 'text-button'; clear.textContent = '清除筛选';
  clear.onclick = () => $('#reset-filters').click();
  $('.toolbar').append(clear);
  function syncFilters() {
    featuredToggle.textContent = $('#featured').hidden ? '精选专题' : '收起专题';
    featuredToggle.setAttribute('aria-expanded', String(!$('#featured').hidden));
    const active = ['search','map-filter','resolution-filter'].some(id => $('#'+id).value) || $('#tileable-filter').checked;
    clear.hidden = !active;
    $('#map-filter').classList.toggle('has-value', !!$('#map-filter').value);
    $('#filter-toggle').classList.toggle('has-value', !!$('#resolution-filter').value || $('#tileable-filter').checked);
    $('#filter-toggle').setAttribute('aria-expanded', String(!$('#advanced-filters').hidden));
    $('#grid-view').setAttribute('aria-pressed', String(!$('#asset-grid').classList.contains('list-mode')));
    $('#list-view').setAttribute('aria-pressed', String($('#asset-grid').classList.contains('list-mode')));
  }
  new MutationObserver(syncFilters).observe($('#active-filters'), {childList:true});
  new MutationObserver(syncFilters).observe($('#asset-grid'), {attributes:true,attributeFilter:['class']});
  $('#filter-toggle').addEventListener('click', syncFilters);
  syncFilters();

  const appearance = document.createElement('details');
  appearance.className = 'appearance-menu';
  appearance.innerHTML = '<summary>外观</summary><div class="appearance-popover"><span>阅读字号</span><div class="reading-slot"></div><span>浅色 / 深色</span><div class="theme-slot"></div></div>';
  $('.topbar-right').append(appearance);
  $('.reading-slot').append($('#reading-settings'));
  $('.theme-slot').append($('#appearance-toggle'));
  document.addEventListener('click', e => {if(!appearance.contains(e.target)) appearance.open=false;});
  document.addEventListener('keydown', e => {if(e.key==='Escape') appearance.open=false;});
  $('#reading-settings').addEventListener('click', () => {appearance.open=false;});

  const libraryInfo=document.createElement('details');
  libraryInfo.className='library-info';
  libraryInfo.innerHTML='<summary>本地材质库 <span>路径与容量</span></summary>';
  libraryInfo.append($('.storage'));
  $('.sidebar-bottom').prepend(libraryInfo);
  $('#settings').innerHTML=icon('settings')+'材质库设置';
})();
