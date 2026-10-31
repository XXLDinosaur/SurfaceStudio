/** @param {import("./runtime.js").AppContext} ctx */
export function createLibrary(ctx) {
  function skeleton() {
    ctx.$("#asset-grid").innerHTML = Array.from(
      { length: 12 },
      () =>
        '<div class="asset-card skeleton"><div class="card-image"></div><div class="card-info"></div></div>',
    ).join("");
  }
  async function load() {
    try {
      const response = await fetch("/api/library");
      if (!response.ok) throw Error("无法连接素材库");
      ctx.library = await response.json();
      ctx.assets = ctx.library.assets;
      ctx.byId = new Map(ctx.assets.map((a) => [a.id, a]));
      ctx.state = ctx.library.state;
      ctx.token = ctx.library.token;
      ctx.assets.forEach((a) => {
        a.searchText = [
          a.name,
          a.folder,
          a.assetId,
          a.category,
          a.categoryZh,
          a.search,
          ...a.tags,
        ]
          .join(" ")
          .toLowerCase();
      });
      ctx.$("#category-number").textContent = ctx.library.categories.length;
      ctx.$("#index-status").textContent =
        `${ctx.fmt(ctx.assets.length)} 个材质已索引`;
      ctx.renderNav();
      ctx.renderResults();
      if (ctx.library.error) ctx.toast("扫描提示：" + ctx.library.error);
      if (ctx.library.scanning) ctx.pollScan();
      document.dispatchEvent(new Event("library-loaded"));
    } catch (e) {
      ctx.$("#asset-grid").innerHTML =
        `<div class="error-banner">连接素材库失败：${ctx.esc(e.message)}<button id="retry" class="outline-button">重新连接</button></div>`;
      ctx.$("#retry").onclick = ctx.load;
    }
  }
  function renderResults(keepLimit = false) {
    if (!ctx.library) return;
    if (!keepLimit) {
      ctx.limit = 48;
      ctx.$("#scroll-area").scrollTo({ top: 0, behavior: "instant" });
    }
    const query = ctx.$("#search").value.trim().toLowerCase();
    const words = query.split(/\s+/).filter(Boolean);
    const map = ctx.$("#map-filter").value;
    const res = ctx.$("#resolution-filter").value;
    const tile = ctx.$("#tileable-filter").checked;
    const recentIds = ctx.state.recent.map((x) =>
      typeof x === "string" ? x : x.id,
    );
    ctx.filtered = ctx.assets.filter(
      (a) =>
        (!ctx.assetType || ctx.assetInType(a, ctx.assetType)) &&
        (!ctx.category || a.category === ctx.category) &&
        (!ctx.nature ||
          ["Rock", "Moss", "Grass", "Soil", "Ground", "Sand", "Tree"].includes(
            a.category,
          )) &&
        (ctx.view !== "favorites" || ctx.state.favorites.includes(a.id)) &&
        (ctx.view !== "recent" || recentIds.includes(a.id)) &&
        words.every((w) => a.searchText.includes(w)) &&
        (!map ||
          (map === "NormalOnly"
            ? a.normalOnly
            : a.maps.some((m) => m.channel === map))) &&
        (!res || a.resolution === res) &&
        (!tile || a.meta.tileable === true),
    );
    const sort = ctx.$("#sort").value;
    if (sort === "name")
      ctx.filtered.sort((a, b) => a.name.localeCompare(b.name));
    else if (sort === "recent")
      ctx.filtered.sort((a, b) => b.modified - a.modified);
    else if (sort === "size") ctx.filtered.sort((a, b) => b.bytes - a.bytes);
    else if (ctx.view === "recent")
      ctx.filtered.sort(
        (a, b) => recentIds.indexOf(a.id) - recentIds.indexOf(b.id),
      );
    else ctx.filtered = ctx.curated(ctx.filtered);
    const title = ctx.currentTitle();
    const home =
      ctx.view === "all" && !ctx.category && !ctx.assetType && !ctx.nature;
    ctx.$("#page-title").innerHTML = home
      ? "好材质，让灵感落地<span>.</span>"
      : ctx.esc(title) + "<span>.</span>";
    ctx.$("#page-description").textContent = home
      ? "你的私人材质档案。发现、整理，构建下一个真实世界。"
      : ctx.view === "favorites"
        ? "把心动的质感留下，让创作随时发生。"
        : ctx.view === "recent"
          ? "沿着灵感的足迹，回到刚刚看过的材质。"
          : `${ctx.category || "NATURE"} COLLECTION / 在 ${ctx.fmt(ctx.filtered.length)} 份真实质感中，找到你的灵感。`;
    ctx.$("#breadcrumb-title").textContent = title;
    ctx.$("#result-count").textContent = ctx.fmt(ctx.filtered.length);
    ctx.$("#active-filters").innerHTML = [
      ctx.assetType || ctx.category || ctx.nature || ctx.view !== "all"
        ? `<button class="filter-chip" data-clear="view">${ctx.esc(title)} ${ctx.icon("close")}</button>`
        : "",
      query
        ? `<button class="filter-chip" data-clear="search">${ctx.esc(query)} ${ctx.icon("close")}</button>`
        : "",
      map
        ? `<button class="filter-chip" data-clear="map-filter">${ctx.esc(ctx.$("#map-filter").selectedOptions[0].textContent)} ${ctx.icon("close")}</button>`
        : "",
      res
        ? `<button class="filter-chip" data-clear="resolution-filter">${ctx.esc(res)} ${ctx.icon("close")}</button>`
        : "",
      tile
        ? `<button class="filter-chip" data-clear="tileable-filter">可平铺 ${ctx.icon("close")}</button>`
        : "",
    ].join("");
    ctx.drawCards();
  }
  function drawCards(append = false) {
    const grid = ctx.$("#asset-grid");
    const start = append ? grid.children.length : 0;
    const visible = ctx.filtered.slice(0, ctx.limit);
    const html = visible
      .slice(start)
      .map(
        (a, i) =>
          `<article tabindex="0" role="button" aria-label="查看 ${ctx.esc(a.name)}" class="asset-card ${a.normalOnly ? "normal-only" : ""} ${ctx.selected === a.id ? "selected" : ""}" data-asset="${a.id}" style="animation-delay:${Math.min(i, 12) * 15}ms"><div class="card-image"><img src="${ctx.imageURL(a)}" loading="lazy" decoding="async" alt="${ctx.esc(a.name)} 材质预览"><span class="resolution-badge">${a.kind === "decal" ? "贴花" : a.normalOnly ? "法线" : ctx.esc(a.resolution)}</span><button class="card-favorite ${ctx.state.favorites.includes(a.id) ? "is-favorite" : ""}" data-favorite="${a.id}" aria-pressed="${ctx.state.favorites.includes(a.id)}" aria-label="收藏 ${ctx.esc(a.name)}" title="收藏材质">${ctx.icon("heart")}</button><button class="card-compare ${ctx.compared.includes(a.id) ? "is-compared" : ""}" data-compare="${a.id}" title="加入对比">${ctx.icon("compare")}对比</button></div><div class="card-info"><h3 title="${ctx.esc(a.name)}">${ctx.esc(a.name)}</h3><div class="card-meta"><span class="card-category">${ctx.esc(a.categoryZh)}<i class="tiny-dot"></i>${a.kind === "blend" ? "原生节点材质" : new Set(a.maps.map((m) => m.channel)).size + " 贴图"}</span><span class="card-downloaded">${ctx.icon("check")}本地</span></div></div></article>`,
      )
      .join("");
    if (append) grid.insertAdjacentHTML("beforeend", html);
    else grid.innerHTML = html;
    ctx.$("#empty").hidden = ctx.filtered.length > 0;
    ctx.$("#shown-count").textContent =
      `已显示 ${ctx.fmt(visible.length)} / ${ctx.fmt(ctx.filtered.length)} 个材质`;
    ctx.$("#load-more").textContent =
      visible.length >= ctx.filtered.length
        ? "已全部显示"
        : "继续向下滚动，自动加载";
    ctx.$$(".card-image>img").forEach(
      (img) =>
        (img.onerror = () => {
          img.removeAttribute("src");
          img.alt = "预览暂不可用";
        }),
    );
  }
  function queueMoreMaterials() {
    if (ctx.autoLoadPending || !ctx.library || ctx.limit >= ctx.filtered.length)
      return;
    ctx.autoLoadPending = true;
    requestAnimationFrame(() => {
      ctx.autoLoadPending = false;
      if (!ctx.library || ctx.limit >= ctx.filtered.length) return;
      const area = ctx.$("#scroll-area"),
        footer = ctx.$(".load-more");
      const bounds = area.getBoundingClientRect(),
        end = footer.getBoundingClientRect();
      if (end.top > bounds.bottom + 160 || end.bottom < bounds.top) return;
      ctx.limit = Math.min(ctx.limit + 48, ctx.filtered.length);
      ctx.drawCards(true);
      ctx.queueMoreMaterials();
    });
  }
  return { skeleton, load, renderResults, drawCards, queueMoreMaterials };
}
