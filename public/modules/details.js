/** @param {import("./runtime.js").AppContext} ctx */
export function createDetails(ctx) {
  function closeDetail() {
    ctx.selected = null;
    ctx.$("#detail").hidden = true;
    document.body.classList.remove("detail-open");
    ctx
      .$$(".asset-card.selected")
      .forEach((el) => el.classList.remove("selected"));
  }
  function openDetail(id) {
    const a = ctx.byId.get(id);
    if (!a) return;
    ctx.selected = id;
    ctx.state.recent = [
      { id, time: Date.now() },
      ...ctx.state.recent.filter(
        (x) => (typeof x === "string" ? x : x.id) !== id,
      ),
    ].slice(0, 100);
    ctx.saveState();
    document.body.classList.add("detail-open");
    ctx.$("#detail").hidden = false;
    const channels = [
      "Albedo",
      "Normal",
      "Roughness",
      "Displacement",
      "AO",
      "Metalness",
      "Opacity",
      "Specular",
      "Gloss",
      "Other",
    ];
    const maps = [...a.maps].sort(
      (x, y) => channels.indexOf(x.channel) - channels.indexOf(y.channel),
    );
    ctx.$("#detail").innerHTML =
      `<div class="detail-top"><span>ASSET INSPECTOR</span><button class="icon-button" id="close-detail" title="关闭详情 · Esc">${ctx.icon("close")}</button></div><div class="detail-preview ${a.normalOnly ? "flat" : ""}" id="detail-preview"><img id="detail-image" src="${ctx.imageURL(a, a.preview, 1024)}" alt="${ctx.esc(a.name)}"><button class="icon-button expand-button" id="expand-preview" title="放大预览">${ctx.icon("expand")}</button><div class="preview-control"><button class="active" data-preview="sphere">${a.kind === "decal" ? "贴花预览" : a.normalOnly ? "法线原图" : "材质球"}</button>${a.kind === "blend" ? "" : `${a.normalOnly ? "" : '<button data-preview="albedo">表面</button>'}<button data-preview="tile">平铺检视</button>`}</div></div><div class="detail-body"><div class="detail-eyebrow">SURFACE <span> / </span> ${ctx.esc(a.category.toUpperCase())}</div><h2>${ctx.esc(a.name)}</h2>${a.kind === "blend" ? '<p class="form-note">Blender 原生材质 · 完整节点与内嵌贴图。赋予时保留原节点；预览来自标准材质球，实际效果随模型、UV 和灯光变化。</p>' : ""}${a.normalOnly ? '<p class="form-note normal-note">纯法线素材 · 原图与平铺预览。赋予 Blender 会创建带法线的基础材质；水的透明、折射请在 Blender 调整。</p>' : ""}<span class="asset-identifier">${ctx.esc(a.assetId)} · ${ctx.esc(a.resolution)} · ${ctx.esc(a.categoryZh)}</span><div class="detail-actions"><button class="primary-button" id="open-folder">${ctx.icon("folder")}打开材质文件夹</button><button class="icon-button ${ctx.state.favorites.includes(id) ? "is-favorite" : ""}" data-favorite="${id}" title="收藏材质" aria-pressed="${ctx.state.favorites.includes(id)}">${ctx.icon("heart")}</button><button class="icon-button" id="detail-compare" title="加入对比">${ctx.icon("compare")}</button></div><button id="copy-path" class="outline-button copy-path">${ctx.icon("copy")}复制文件夹路径</button><button id="edit-material-category" class="outline-button copy-path">修改分类 · ${ctx.esc(a.categoryZh)}</button><div class="detail-stats">${ctx.statsHTML(a)}</div><div class="section-title">材质标签<span>点击标签搜索</span></div><div class="tags">${[
        a.category,
        ...a.tags,
      ]
        .slice(0, 18)
        .map((t) => `<button data-tag="${ctx.esc(t)}">${ctx.esc(t)}</button>`)
        .join(
          "",
        )}</div><div class="section-title">${a.kind === "blend" ? "材质文件" : "贴图通道"}<span>${a.kind === "blend" ? "BLEND" : a.maps.length + " FILES"}</span></div>${a.kind === "blend" ? '<p class="form-note">material.blend · 节点及贴图已包含在材质文件内</p>' : ""}<div class="map-list">${maps.map((m) => `<button class="map-row" data-map="${ctx.esc(m.name)}" title="${ctx.esc(m.name)}">${m.ext === "EXR" ? '<span class="map-thumb">EXR</span>' : `<img class="map-thumb" loading="lazy" src="${ctx.imageURL(a, m.name, 96)}" alt="${ctx.esc(m.channel)}">`}<div><b>${ctx.esc(m.channel)} <span style="color:#617062">· ${ctx.esc(m.ext)}</span></b><small>${ctx.esc(m.name)}</small></div><span>${ctx.bytes(m.bytes)}</span></button>`).join("")}</div><div class="section-title">本地位置<span>LOCAL PATH</span></div><div class="path-box">${ctx.esc(ctx.assetFolder(a))}</div><div class="detail-foot">${ctx.icon("check")} AVAILABLE OFFLINE · ${ctx.bytes(a.bytes)}</div></div>`;
    ctx.$("#detail").scrollTop = 0;
    ctx.$("#close-detail").onclick = ctx.closeDetail;
    ctx.$("#open-folder").onclick = () =>
      ctx
        .post("/api/open", { id })
        .then(() => ctx.toast("已在文件资源管理器中打开"))
        .catch((e) => ctx.toast(e.message));
    ctx.$("#copy-path").onclick = () => ctx.copy(ctx.assetFolder(a));
    ctx.$("#detail-compare").onclick = () => ctx.toggleCompare(id);
    ctx.$("#expand-preview").onclick = () => ctx.previewModal(a, a.preview);
    ctx.$$("[data-preview]", ctx.$("#detail")).forEach(
      (b) =>
        (b.onclick = () => {
          const color = a.maps.find(
            (m) =>
              m.channel === (a.normalOnly ? "Normal" : "Albedo") &&
              m.ext !== "EXR",
          );
          if (b.dataset.preview === "tile") {
            if (!color)
              return ctx.toast(
                a.normalOnly
                  ? "EXR 法线暂不能在这里预览，可在 Blender 中使用原图"
                  : "这个材质没有可预览的颜色贴图",
              );
            ctx.previewModal(a, color.name, true);
            return;
          }
          if (b.dataset.preview === "albedo" && !color)
            return ctx.toast("这个材质没有可预览的颜色贴图");
          ctx
            .$$("[data-preview]", ctx.$("#detail"))
            .forEach((el) => el.classList.toggle("active", el === b));
          const file = b.dataset.preview === "sphere" ? a.preview : color.name;
          ctx
            .$("#detail-preview")
            .classList.toggle(
              "flat",
              a.normalOnly || b.dataset.preview !== "sphere",
            );
          ctx.$("#detail-image").src = ctx.imageURL(a, file, 1024);
          ctx.$("#expand-preview").onclick = () => ctx.previewModal(a, file);
        }),
    );
    ctx.$$("[data-tag]", ctx.$("#detail")).forEach(
      (b) =>
        (b.onclick = () => {
          ctx.navigate();
          ctx.$("#search").value = b.dataset.tag;
          ctx.renderResults();
        }),
    );
    ctx.$$("[data-map]", ctx.$("#detail")).forEach(
      (b) =>
        (b.onclick = () => {
          const m = a.maps.find((m) => m.name === b.dataset.map);
          if (m.ext === "EXR") {
            const fallback = a.maps.find(
              (x) => x.channel === m.channel && x.ext !== "EXR",
            );
            if (fallback) {
              ctx.previewModal(a, fallback.name);
              ctx.toast("EXR 使用同通道 JPG 代理预览");
            } else ctx.toast("EXR 可在专业软件中查看；请打开文件夹");
          } else ctx.previewModal(a, m.name);
        }),
    );
    ctx
      .$$(".asset-card")
      .forEach((el) =>
        el.classList.toggle("selected", el.dataset.asset === id),
      );
  }
  function statsHTML(a) {
    if (a.kind === "blend")
      return `<div><small>材质类型</small><b>Blender 原生节点</b></div><div><small>文件大小</small><b>${ctx.bytes(a.bytes)}</b></div><div><small>保存版本</small><b>Blender ${ctx.esc(a.blenderVersion.join("."))}</b></div><div><small>资源保存</small><b>贴图已内嵌</b></div>`;
    return `<div><small>分辨率</small><b>${ctx.esc(a.resolution)} TEXTURES</b></div><div><small>文件大小</small><b>${ctx.bytes(a.bytes)}</b></div><div><small>扫描范围</small><b>${ctx.esc(a.meta.scanArea || "未提供")}</b></div><div><small>无缝平铺</small><b>${a.meta.tileable === true ? "支持 · Tileable" : a.meta.tileable === false ? "不支持" : "未标注"}</b></div>`;
  }
  function previewModal(a, file, tile = false) {
    ctx.modal(
      tile ? "平铺检视" : a.name,
      `<div class="large-preview">${tile ? `<div class="tiling-preview" id="tile-canvas" style="background-image:url('${ctx.imageURL(a, file, 1024)}')"></div>` : `<img src="${ctx.imageURL(a, file, 2048)}" alt="${ctx.esc(file)}">`}</div>${tile ? '<div class="tile-tools"><span>平铺次数</span><input type="range" min="1" max="8" value="3" id="tile-repeat"><span id="tile-repeat-label">3 × 3</span></div>' : ""}<p class="form-note">${ctx.esc(file)}${tile ? (a.normalOnly ? " · 法线图平铺检查（不是水材质渲染）" : " · 颜色贴图平铺检查") : " · 预览已缩放，原始文件保持不变"}</p><div class="modal-actions"><button class="outline-button" id="copy-file">${ctx.icon("copy")}复制文件路径</button></div>`,
      `${a.category.toUpperCase()} / ${a.resolution}`,
      "900px",
    );
    ctx.$("#copy-file").onclick = () =>
      ctx.copy(ctx.assetFolder(a) + "\\" + file);
    if (tile)
      ctx.$("#tile-repeat").oninput = (e) => {
        ctx.$("#tile-canvas").style.backgroundSize = 100 / e.target.value + "%";
        ctx.$("#tile-repeat-label").textContent =
          `${e.target.value} × ${e.target.value}`;
      };
  }
  function toggleCompare(id) {
    if (ctx.compared.includes(id))
      ctx.compared = ctx.compared.filter((x) => x !== id);
    else {
      if (ctx.compared.length === 2)
        return ctx.toast("一次可对比两个材质，请先移除一个");
      ctx.compared.push(id);
    }
    ctx.renderCompareTray();
    ctx
      .$$("[data-compare]")
      .forEach((b) =>
        b.classList.toggle(
          "is-compared",
          ctx.compared.includes(b.dataset.compare),
        ),
      );
  }
  return { closeDetail, openDetail, statsHTML, previewModal, toggleCompare };
}
