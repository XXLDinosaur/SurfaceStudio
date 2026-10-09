/* Native-feeling material actions; editable fields retain their normal copy/paste menu. */
(() => {
  const menu = document.createElement('div');
  menu.id = 'material-context-menu'; menu.className = 'material-context-menu';
  menu.setAttribute('role', 'menu'); menu.setAttribute('aria-label', '材质操作');
  menu.hidden = true; document.body.append(menu);
  let origin = null, actions = [];
  const editable = target => target.closest('input,textarea,[contenteditable="true"],[contenteditable=""]');
  function close(restore = false) {
    const wasOpen = !menu.hidden;
    menu.hidden = true;
    document.querySelectorAll('.context-target').forEach(card => card.classList.remove('context-target'));
    if (restore && wasOpen && origin?.isConnected) origin.focus({preventScroll:true});
  }
  function entry(label, glyph, run, shortcut = '') { return {label, glyph, run, shortcut}; }
  function show(target, x, y) {
    close();
    const card = target.closest('[data-asset]');
    const detail = target.closest('#detail');
    const id = card?.dataset.asset || (detail && selected);
    const asset = id && byId.get(id);
    origin = card || (detail ? document.querySelector('#close-detail') : document.activeElement);
    card?.classList.add('context-target');
    if (asset) {
      const map = target.closest('[data-map]')?.dataset.map;
      actions = [
        entry('查看材质详情', 'cube', () => openDetail(id), 'Enter'),
        entry('赋予到 Blender', 'arrow', () => window.surfaceBlender.applyFromMenu(id)),
        null,
        entry(state.favorites.includes(id) ? '取消收藏' : '收藏材质', 'heart', () => setFavorite(id)),
        entry('添加到集合…', 'folder', () => collectionPicker(id)),
        entry(compared.includes(id) ? '移出对比' : '加入材质对比', 'compare', () => toggleCompare(id)),
        null,
        entry('在资源管理器中打开', 'folder', () => post('/api/open',{id}).then(() => toast('已打开材质文件夹'))),
        entry('复制文件夹路径', 'copy', () => copy(library.root+'\\'+asset.folder)),
      ];
      if (map) actions.push(entry('复制这张贴图的路径', 'copy', () => copy(library.root+'\\'+asset.folder+'\\'+map)));
    } else {
      actions = [entry('查看全部材质', 'grid', () => navigate()),
        entry('重新扫描素材库', 'refresh', () => rescan()), null,
        entry('素材库设置', 'settings', () => settings())];
    }
    menu.innerHTML = `${asset ? `<div class="context-menu-heading">${esc(asset.name)}<small>${esc(asset.categoryZh)} · ${esc(asset.resolution)}</small></div>` : ''}` +
      actions.map((action, index) => action ? `<button role="menuitem" tabindex="-1" data-menu-action="${index}">${icon(action.glyph)}<span>${esc(action.label)}</span>${action.shortcut ? `<kbd>${esc(action.shortcut)}</kbd>` : ''}</button>` : '<div class="context-menu-separator" role="separator"></div>').join('');
    menu.hidden = false;
    menu.style.left = '0px'; menu.style.top = '0px';
    const rect = menu.getBoundingClientRect();
    menu.style.left = Math.max(8, Math.min(x, innerWidth - rect.width - 8))+'px';
    menu.style.top = Math.max(8, Math.min(y, innerHeight - rect.height - 8))+'px';
    menu.querySelector('[role="menuitem"]')?.focus({preventScroll:true});
  }
  document.addEventListener('contextmenu', event => {
    if (editable(event.target)) { close(); return; }
    event.preventDefault();
    if (document.querySelector('#modal').open) { close(); return; }
    const rect = event.target.getBoundingClientRect();
    show(event.target, event.clientX || rect.left + 18, event.clientY || rect.top + 18);
  });
  menu.addEventListener('click', event => {
    const button = event.target.closest('[data-menu-action]');
    if (!button) return;
    const action = actions[Number(button.dataset.menuAction)];
    close(true);
    try { Promise.resolve(action.run()).catch(error => toast(error.message || '操作失败')); }
    catch (error) { toast(error.message || '操作失败'); }
  });
  document.addEventListener('pointerdown', event => { if (!menu.contains(event.target)) close(); });
  document.addEventListener('scroll', event => { if (!menu.contains(event.target)) close(); }, true);
  window.addEventListener('resize', () => close());
  window.addEventListener('blur', () => close());
  document.addEventListener('keydown', event => {
    if (!menu.hidden) {
      if (event.key === 'Escape' || event.key === 'Tab') {
        close(true); if (event.key === 'Escape') {event.preventDefault(); event.stopImmediatePropagation();}
        return;
      }
      if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
        event.preventDefault(); event.stopImmediatePropagation();
        const items = [...menu.querySelectorAll('[role="menuitem"]')];
        const current = items.indexOf(document.activeElement);
        const index = event.key === 'Home' ? 0 : event.key === 'End' ? items.length-1 : (current+(event.key==='ArrowDown'?1:-1)+items.length)%items.length;
        items[index].focus();
      }
      // Avoid the material viewer's global shortcuts while navigating this menu.
      if (event.key.toLowerCase() === 'f') event.stopImmediatePropagation();
    } else if ((event.shiftKey && event.key === 'F10') || event.key === 'ContextMenu') {
      if (editable(event.target)) return;
      if (!event.target.closest('[data-asset],#detail')) return;
      event.preventDefault(); const rect=event.target.getBoundingClientRect();
      show(event.target, rect.left+18, rect.top+18);
    }
  }, true);
})();
