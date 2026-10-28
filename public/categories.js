/* Category metadata lives beside the index; original material files stay untouched. */
async function submitCategory(body, button){
  button.disabled=true;
  try{
    await stateQueue;
    await post('/api/categories',body);
    await load();
    if(selected&&byId.has(selected))openDetail(selected);
    $('#modal').close();toast(body.action==='rename'?'分类已重命名':body.action==='create'?'分类已创建':body.category===null?'已恢复自动分类':'素材分类已更新');
  }catch(error){$('#category-error').textContent=error.message}
  finally{button.disabled=false}
}
function categoryCreator(asset=null){
  modal(asset?'新建分类并归入':'新建素材分类',`<p class="modal-description">分类保存在当前材质库的管理信息中，不会移动文件。重新扫描后仍会保留。</p><label class="form-label" for="category-name">分类名称</label><input id="category-name" class="form-input" maxlength="40" placeholder="例如：大理石 / 室内墙面"><p id="category-error" class="modal-error" role="alert"></p><div class="modal-actions"><button id="category-cancel" class="outline-button">取消</button><button id="category-save" class="primary-button">${asset?'创建并归入':'创建分类'}</button></div>`);
  $('#category-cancel').onclick=()=>asset?categoryPicker(asset):$('#modal').close();
  $('#category-save').onclick=()=>submitCategory({action:'create',name:$('#category-name').value,...(asset?{asset}:{})},$('#category-save'));
  $('#category-name').onkeydown=e=>{if(e.key==='Enter'&&!$('#category-save').disabled)$('#category-save').click()};
  $('#category-name').focus();
}
function categoryPicker(id){
  const a=byId.get(id);if(!a)return;
  modal('修改素材分类',`<p class="modal-description">${esc(a.name)} · 当前分类：${esc(a.categoryZh)}${a.manualCategory?'（手动）':''}</p><label class="form-label" for="category-select">归入分类</label><select id="category-select" class="form-input">${library.categoryOptions.map(c=>`<option value="${esc(c.id)}" ${c.id===a.category?'selected':''}>${esc(c.name)}</option>`).join('')}</select><p class="form-note">只修改分类记录，不移动原始材质文件。</p><p id="category-error" class="modal-error" role="alert"></p><div class="modal-actions" style="flex-wrap:wrap"><button class="outline-button" id="category-new">新建分类…</button>${a.manualCategory?'<button class="outline-button" id="category-reset">恢复自动分类</button>':''}<button class="primary-button" id="category-save">保存分类</button></div>`);
  $('#category-new').onclick=()=>categoryCreator(id);
  $('#category-save').onclick=()=>submitCategory({action:'assign',asset:id,category:$('#category-select').value},$('#category-save'));
  if($('#category-reset'))$('#category-reset').onclick=()=>submitCategory({action:'assign',asset:id,category:null},$('#category-reset'));
}
const addCategory=document.createElement('button');
addCategory.className='icon-button';addCategory.id='new-category';addCategory.title='新建素材分类';addCategory.setAttribute('aria-label','新建素材分类');addCategory.innerHTML=icon('plus');
addCategory.onclick=()=>categoryCreator();
document.querySelector('.category-label').append(addCategory);
document.addEventListener('click',e=>{if(e.target.closest('#edit-material-category')&&selected)categoryPicker(selected)});

function categoryRenamer(id){
  const c=library.categoryOptions.find(c=>c.id===id);if(!c)return;
  modal('重命名分类',`<p class="modal-description">修改分类显示名称，分类中的材质会保持原有归属。</p><label class="form-label" for="category-name">分类名称</label><input id="category-name" class="form-input" maxlength="40" value="${esc(c.name)}"><p id="category-error" class="modal-error" role="alert"></p><div class="modal-actions"><button id="category-cancel" class="outline-button">取消</button><button id="category-save" class="primary-button">保存名称</button></div>`);
  $('#category-cancel').onclick=()=>$('#modal').close();
  $('#category-save').onclick=()=>submitCategory({action:'rename',category:id,name:$('#category-name').value},$('#category-save'));
  $('#category-name').onkeydown=e=>{if(e.key==='Enter'&&!$('#category-save').disabled)$('#category-save').click()};
  $('#category-name').focus();$('#category-name').select();
}
