(() => {
  const button=document.createElement('button');button.className='nav-item';button.id='normal-library';button.innerHTML=icon('grid')+'纯法线贴图';
  $('#main-nav').append(button);
  button.onclick=()=>{navigate();$('#map-filter').value='NormalOnly';renderResults();toast('纯法线素材可在素材库设置中添加独立文件夹')};
})();
