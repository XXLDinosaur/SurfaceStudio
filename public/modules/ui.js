/** @param {import("./runtime.js").AppContext} ctx */
export function createUi(ctx) {
  function preference(key, value) {
    ctx.prefs[key] = value;
    try {
      localStorage.setItem("surface-preferences", JSON.stringify(ctx.prefs));
    } catch {}
  }
  function assetFolder(a) {
    return (
      (a.sourceRoot || ctx.library.root) +
      (a.folder && a.folder !== "."
        ? "\\" + a.folder.replaceAll("/", "\\")
        : "")
    );
  }
  function imageURL(a, file = a.preview, size = 480) {
    if (/\.exr$/i.test(file)) return "/normal-exr.svg";
    return `/api/image?id=${encodeURIComponent(a.id)}&file=${encodeURIComponent(file)}&size=${size}&v=3-${ctx.library?.scannedAt || 0}`;
  }
  function fileURL(a, file) {
    return `/api/file?id=${encodeURIComponent(a.id)}&file=${encodeURIComponent(file)}`;
  }
  function toast(message) {
    ctx.$("#toast").textContent = message;
    ctx.$("#toast").classList.add("show");
    clearTimeout(ctx.toastTimer);
    ctx.toastTimer = setTimeout(
      () => ctx.$("#toast").classList.remove("show"),
      2800,
    );
  }
  async function post(path, body = {}) {
    const r = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Studio-Token": ctx.token,
      },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) throw Error(data.error || "操作失败");
    return data;
  }
  function saveState() {
    const snapshot = JSON.parse(JSON.stringify(ctx.state));
    ctx.stateQueue = ctx.stateQueue
      .then(() => ctx.post("/api/state", snapshot))
      .catch((e) => ctx.toast("保存失败：" + e.message));
    return ctx.stateQueue;
  }
  function setFavorite(id) {
    const adding = !ctx.state.favorites.includes(id);
    ctx.state.favorites = adding
      ? [...ctx.state.favorites, id]
      : ctx.state.favorites.filter((x) => x !== id);
    ctx.saveState();
    ctx.renderNav();
    if (ctx.view === "favorites") ctx.renderResults();
    else
      ctx.$$(`[data-favorite="${id}"]`).forEach((el) => {
        el.classList.toggle("is-favorite", adding);
        el.setAttribute("aria-pressed", String(adding));
        el.title = adding ? "取消收藏" : "收藏材质";
      });
    ctx.toast(adding ? "已添加到我的收藏" : "已取消收藏");
  }
  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      ctx.toast("路径已复制到剪贴板");
    } catch {
      ctx.toast("无法访问剪贴板，请在详情中选中路径复制");
    }
  }
  function modal(title, body, kicker = "SURFACE STUDIO", width = "520px") {
    const el = ctx.$("#modal");
    el.style.width = width;
    el.className = "";
    ctx.$("#modal-content").innerHTML =
      `<div class="modal-kicker">${ctx.esc(kicker)}</div><div class="modal-head"><h2>${ctx.esc(title)}</h2><button class="icon-button" id="close-modal" title="关闭">${ctx.icon("close")}</button></div>${body}`;
    ctx.$("#close-modal").onclick = () => el.close();
    if (!el.open) el.showModal();
  }
  function renderCompareTray() {
    const tray = ctx.$("#compare-tray");
    tray.hidden = !ctx.compared.length;
    tray.innerHTML = `<span>材质对比 ${ctx.compared.length} / 2</span>${ctx.compared.map((id) => `<img src="${ctx.imageURL(ctx.byId.get(id), ctx.byId.get(id).preview, 96)}" alt="${ctx.esc(ctx.byId.get(id).name)}">`).join("")}<button class="primary-button" id="start-compare">开始对比 ${ctx.icon("arrow")}</button><button class="icon-button" id="clear-compare" title="清除对比">${ctx.icon("close")}</button>`;
    ctx.$("#clear-compare").onclick = () => {
      ctx.compared = [];
      ctx.renderCompareTray();
      ctx
        .$$("[data-compare]")
        .forEach((b) => b.classList.remove("is-compared"));
    };
    ctx.$("#start-compare").onclick = () => {
      if (ctx.compared.length < 2)
        return ctx.toast("再选择一个材质，即可并排对比");
      ctx.modal(
        "每一处差异，都值得看清",
        `<div class="compare-grid">${ctx.compared
          .map((id) => {
            const a = ctx.byId.get(id);
            return `<div><img src="${ctx.imageURL(a, a.preview, 1024)}" alt="${ctx.esc(a.name)}"><h3>${ctx.esc(a.name)}</h3><p>${ctx.esc(a.categoryZh)} · ${a.maps.length} 个文件 · ${ctx.esc(a.assetId)}</p><div class="detail-stats">${ctx.statsHTML(a)}</div><p>${ctx.esc(a.tags.join(" · "))}</p><button class="outline-button" data-inspect="${id}">查看详情 ${ctx.icon("arrow")}</button></div>`;
          })
          .join("")}</div>`,
        "MATERIAL COMPARISON",
        "1060px",
      );
      ctx.$$("[data-inspect]").forEach(
        (b) =>
          (b.onclick = () => {
            ctx.$("#modal").close();
            ctx.openDetail(b.dataset.inspect);
          }),
      );
    };
  }
  function gridMode(mode) {
    ctx.$("#asset-grid").classList.toggle("list-mode", mode === "list");
    ctx.$("#grid-view").classList.toggle("active", mode !== "list");
    ctx.$("#list-view").classList.toggle("active", mode === "list");
    ctx.preference("mode", mode);
  }
  return {
    preference,
    assetFolder,
    imageURL,
    fileURL,
    toast,
    post,
    saveState,
    setFavorite,
    copy,
    modal,
    renderCompareTray,
    gridMode,
  };
}
