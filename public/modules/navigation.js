/** @param {import("./runtime.js").AppContext} ctx */
export function createNavigation(ctx) {
  function assetInType(a, type) {
    return type === "uncategorized"
      ? a.category === "Uncategorized"
      : a.assetGroup === type && a.category !== "Uncategorized";
  }
  function renderNav() {
    ctx.$("#all-count").textContent = ctx.fmt(ctx.assets.length);
    ctx.$("#fav-count").textContent = ctx.state.favorites.filter((x) =>
      ctx.byId.has(x),
    ).length;
    ctx
      .$$("#main-nav button")
      .forEach((b) =>
        b.classList.toggle(
          "active",
          b.dataset.view === ctx.view &&
            !ctx.category &&
            !ctx.assetType &&
            !ctx.nature,
        ),
      );
    ctx.$("#category-number").textContent = "4";
    ctx.$("#categories").innerHTML = Object.entries(ctx.assetTypeNames)
      .map(([type, label]) => {
        const items = ctx.assets.filter((a) => ctx.assetInType(a, type)),
          counts = new Map();
        items.forEach((a) =>
          counts.set(a.category, (counts.get(a.category) || 0) + 1),
        );
        if (type === "uncategorized")
          return `<button class="nav-item ${ctx.assetType === type ? "active" : ""}" data-asset-type="${type}"><span class="category-dot"></span>${label}<span class="nav-count">${items.length}</span></button>`;
        const children = ctx.library.categories.filter(
          (c) =>
            c.id !== "Uncategorized" &&
            (counts.has(c.id) || c.id.startsWith("custom-")),
        );
        children.sort(
          (a, b) =>
            (a.id !== "Uncategorized") - (b.id !== "Uncategorized") ||
            (counts.get(b.id) || 0) - (counts.get(a.id) || 0),
        );
        return `<div class="asset-type"><div class="asset-type-row"><button class="type-toggle" data-toggle-type="${type}" aria-label="展开或收起${label}" aria-expanded="${ctx.expandedTypes.has(type)}">${ctx.expandedTypes.has(type) ? "⌄" : "›"}</button><button class="nav-item ${ctx.assetType === type && !ctx.category ? "active" : ""}" data-asset-type="${type}">${label}<span class="nav-count">${items.length}</span></button></div><div class="asset-type-children" ${ctx.expandedTypes.has(type) ? "" : "hidden"}>${children.map((c) => `<button class="nav-item category-item ${ctx.assetType === type && ctx.category === c.id ? "active" : ""}" data-category="${ctx.esc(c.id)}" data-parent-type="${type}"><span class="category-dot"></span>${ctx.esc(c.name)}<span class="nav-count">${counts.get(c.id) || 0}</span></button>`).join("")}</div></div>`;
      })
      .join("");
  }
  function currentTitle() {
    if (ctx.assetType && !ctx.category)
      return ctx.assetTypeNames[ctx.assetType];
    if (ctx.category)
      return (
        ctx.library.categories.find((c) => c.id === ctx.category)?.name ||
        ctx.category
      );
    if (ctx.nature) return "自然材质";
    return { all: "全部材质", favorites: "我的收藏", recent: "最近浏览" }[
      ctx.view
    ];
  }
  function navigate(
    next = "all",
    cat = "",
    coll = "",
    natural = false,
    type = "",
  ) {
    ctx.assetType = type;
    if (type) ctx.expandedTypes = new Set([type]);
    ctx.view = next;
    ctx.category = cat;
    ctx.nature = natural;
    ctx.$("#search").value = "";
    ctx.$("#map-filter").value = "";
    ctx.$("#resolution-filter").value = "";
    ctx.$("#tileable-filter").checked = false;
    ctx.renderNav();
    ctx.renderResults();
    ctx.$("#scroll-area").scrollTo({ top: 0, behavior: "instant" });
  }
  function curated(items) {
    const groups = new Map();
    const order = [
      "Rock",
      "Concrete",
      "Wood",
      "Grass",
      "Brick",
      "Metal",
      "Fabric",
      "Moss",
      "Stone",
      "Ground",
      "Sand",
      "Plaster",
      "Asphalt",
    ];
    for (const a of items) {
      if (!groups.has(a.category)) groups.set(a.category, []);
      groups.get(a.category).push(a);
    }
    const keys = [
      ...order.filter((k) => groups.has(k)),
      ...Array.from(groups.keys()).filter((k) => !order.includes(k)),
    ];
    const output = [];
    let i = 0;
    while (output.length < items.length) {
      for (const k of keys) {
        const a = groups.get(k)[i];
        if (a) output.push(a);
      }
      i++;
    }
    return output;
  }
  return { assetInType, renderNav, currentTitle, navigate, curated };
}
