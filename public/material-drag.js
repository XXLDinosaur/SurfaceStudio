/* Windows native drag-out; Blender's file handler resolves the hovered mesh. */
(() => {
  let candidate=null, dragging=false, suppressClickUntil=0, cached=null;
  function options(){try{return JSON.parse(localStorage.getItem('surface-blender-options')||'{}')}catch{return {}}}
  function prepare(id){
    const opts=options(),key=JSON.stringify(opts);
    if(!cached||cached.id!==id||cached.key!==key||Date.now()-cached.created>240000){
      const prepared=post('/api/blender/drop',{asset:id,options:opts});prepared.catch(()=>{});
      cached={id,key,created:Date.now(),prepared};
    }
    return cached.prepared;
  }
  function assetAt(target){
    if(target.closest('button,input,select,a'))return null;
    const image=target.closest('.card-image');
    if(image)return image.closest('[data-asset]')?.dataset.asset;
    if(target.closest('#detail-preview'))return selected;
    return null;
  }
  document.addEventListener('dragstart',e=>{if(assetAt(e.target))e.preventDefault()},true);
  document.addEventListener('pointerover',e=>{
    if(!window.pywebview?.api?.start_material_drag||dragging)return;
    const id=assetAt(e.target);if(id){prepare(id);const area=e.target.closest('.card-image,#detail-preview');if(area)area.title='按住拖到 Blender 模型上（对象模式）'}
  });
  document.addEventListener('pointerdown',e=>{
    if(e.button!==0||!window.pywebview?.api?.start_material_drag)return;
    const id=assetAt(e.target);if(id){
      const prepared=prepare(id);
      candidate={id,x:e.clientX,y:e.clientY,prepared};
    }
  });
  document.addEventListener('pointerup',()=>candidate=null);
  document.addEventListener('pointercancel',()=>candidate=null);
  document.addEventListener('click',e=>{
    if(dragging||Date.now()<suppressClickUntil){e.preventDefault();e.stopImmediatePropagation()}
  },true);
  document.addEventListener('pointermove',async e=>{
    if(!candidate||dragging||!(e.buttons&1)||Math.hypot(e.clientX-candidate.x,e.clientY-candidate.y)<10)return;
    const pending=candidate;candidate=null;cached=null;dragging=true;
    document.body.classList.add('material-dragging');
    try{
      const prepared=await pending.prepared;
      const result=await window.pywebview.api.start_material_drag(prepared.path);
      if(result.dropped){
        toast('已拖出材质，正在等待 Blender 应用…');
        const deadline=Date.now()+90000;
        async function poll(){
          try{
            const response=await fetch('/api/blender/result?id='+prepared.id);const status=await response.json();
            if(['success','error','unknown'].includes(status.status)){toast(status.message);return}
            if(Date.now()<deadline)setTimeout(poll,500);
            else toast('未收到 Blender 确认，请检查是否拖到网格上，以及插件是否为 1.1.0 或更新版本');
          }catch{toast('暂未收到结果，请在 Blender 中检查材质')}
        }
        poll();
      }
    }catch(error){toast('拖拽未完成：'+error.message)}
    finally{dragging=false;suppressClickUntil=Date.now()+300;document.body.classList.remove('material-dragging')}
  });
})();
