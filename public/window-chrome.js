/* Native controls are available only inside the desktop host. */
(() => {
  let mounted = false;
  function mount() {
    if (mounted || !window.pywebview?.api?.window_state) return;
    mounted = true;
    document.documentElement.classList.add('native-desktop');
    const top = document.querySelector('.topbar');
    top.classList.add('pywebview-drag-region');
    document.querySelector('.breadcrumb').classList.add('pywebview-drag-region');
    const drag = document.createElement('div');
    drag.className = 'window-drag-space pywebview-drag-region';
    drag.title = '拖动窗口 · 双击最大化或还原';
    top.insertBefore(drag, document.querySelector('.topbar-right'));
    const controls = document.createElement('div');
    controls.className = 'window-controls';
    controls.setAttribute('aria-label', '窗口控制');
    controls.innerHTML = '<button id="window-minimize" title="最小化" aria-label="最小化"><svg viewBox="0 0 16 16"><path d="M3 8h10"/></svg></button><button id="window-maximize" title="最大化" aria-label="最大化"><svg viewBox="0 0 16 16"><rect x="3.5" y="3.5" width="9" height="9" rx="1"/></svg></button><button id="window-close" title="关闭窗口" aria-label="关闭窗口"><svg viewBox="0 0 16 16"><path d="m4 4 8 8m0-8-8 8"/></svg></button>';
    top.append(controls);
    const run = method => window.pywebview.api[method]().catch(() => toast('窗口操作未完成，请重试'));
    document.querySelector('#window-minimize').onclick = () => run('minimize');
    document.querySelector('#window-maximize').onclick = () => run('toggle_maximize');
    document.querySelector('#window-close').onclick = () => run('close');
    top.addEventListener('dblclick', e => {
      if (e.target.classList.contains('pywebview-drag-region')) run('toggle_maximize');
    });
    window.surfaceWindowState = maximized => {
      const button = document.querySelector('#window-maximize');
      button.title = maximized ? '还原窗口' : '最大化';
      button.setAttribute('aria-label', button.title);
      button.innerHTML = maximized ? '<svg viewBox="0 0 16 16"><path d="M6 3h7v7M3 6h7v7H3z"/></svg>' : '<svg viewBox="0 0 16 16"><rect x="3.5" y="3.5" width="9" height="9" rx="1"/></svg>';
      document.documentElement.classList.toggle('window-maximized', maximized);
    };
    window.pywebview.api.window_state().then(state => window.surfaceWindowState(state.maximized));
    for (const edge of ['n','s','e','w','ne','nw','se','sw']) {
      const handle = document.createElement('div');
      handle.className = 'window-resize-edge edge-' + edge;
      handle.setAttribute('aria-hidden', 'true');
      document.body.append(handle);
      handle.onpointerdown = async e => {
        if(e.button !== 0) return;
        e.preventDefault(); handle.setPointerCapture(e.pointerId);
        const startX=e.screenX, startY=e.screenY;
        let active=true, origin, latest, sending=false;
        async function flush() {
          if(sending || !origin || !latest) return;
          sending=true;
          while(latest) {
            const {dx,dy}=latest; latest=null;
            const width=Math.max(980,origin.width+(edge.includes('e')?dx:edge.includes('w')?-dx:0));
            const height=Math.max(680,origin.height+(edge.includes('s')?dy:edge.includes('n')?-dy:0));
            try { await window.pywebview.api.resize_bounds(origin.x+(edge.includes('w')?origin.width-width:0),origin.y+(edge.includes('n')?origin.height-height:0),width,height); }
            catch { latest=null; }
          }
          sending=false;
        }
        handle.onpointermove = ev => {if(active){latest={dx:ev.screenX-startX,dy:ev.screenY-startY};flush();}};
        handle.onpointerup = handle.onpointercancel = () => {active=false;handle.onpointermove=null;};
        origin=await window.pywebview.api.bounds();flush();
      };
    }
  }
  window.addEventListener('pywebviewready', mount);
  mount();
})();
