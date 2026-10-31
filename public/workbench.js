import { app as ctx } from "./modules/runtime.js";
/* Workspace layout; preferences never modify the material library. */
(() => {
  const controls = document.createElement("section");
  controls.className = "workbench-controls";
  controls.setAttribute("aria-label", "材质搜索与筛选");
  document
    .querySelector(".main-shell")
    .insertBefore(controls, ctx.$("#scroll-area"));
  for (const selector of [
    ".library-tabs",
    ".toolbar",
    "#advanced-filters",
    "#active-filters",
  ])
    controls.append(ctx.$(selector));
  ctx.$(".tab-caption").textContent = "浏览 · 筛选 · 赋予";
  const density = document.createElement("select");
  density.id = "density-preset";
  density.setAttribute("aria-label", "卡片大小");
  density.innerHTML =
    '<option value="190">紧凑</option><option value="230">标准</option><option value="300">大图</option><option value="custom" hidden>自定义</option>';
  ctx.$(".toolbar").insertBefore(density, ctx.$(".view-buttons"));
  function syncDensity() {
    const size = Number(ctx.prefs.density) || 230;
    density.value = ["190", "230", "300"].includes(String(size))
      ? String(size)
      : "custom";
    ctx.$("#density").value = size;
    document.documentElement.style.setProperty("--card-size", size + "px");
  }
  density.onchange = () => {
    if (density.value === "custom") return;
    ctx.preference("density", density.value);
    syncDensity();
    ctx.gridMode("grid");
  };
  ctx.$("#density").addEventListener("input", syncDensity);
  syncDensity();
  const clear = document.createElement("button");
  clear.id = "clear-workbench-filters";
  clear.className = "text-button";
  clear.textContent = "清除筛选";
  clear.onclick = () => ctx.$("#reset-filters").click();
  ctx.$(".toolbar").append(clear);
  function syncFilters() {
    const active =
      ["search", "map-filter", "resolution-filter"].some(
        (id) => ctx.$("#" + id).value,
      ) || ctx.$("#tileable-filter").checked;
    clear.hidden = !active;
    ctx
      .$("#map-filter")
      .classList.toggle("has-value", !!ctx.$("#map-filter").value);
    ctx
      .$("#filter-toggle")
      .classList.toggle(
        "has-value",
        !!ctx.$("#resolution-filter").value ||
          ctx.$("#tileable-filter").checked,
      );
    ctx
      .$("#filter-toggle")
      .setAttribute(
        "aria-expanded",
        String(!ctx.$("#advanced-filters").hidden),
      );
    ctx
      .$("#grid-view")
      .setAttribute(
        "aria-pressed",
        String(!ctx.$("#asset-grid").classList.contains("list-mode")),
      );
    ctx
      .$("#list-view")
      .setAttribute(
        "aria-pressed",
        String(ctx.$("#asset-grid").classList.contains("list-mode")),
      );
  }
  new MutationObserver(syncFilters).observe(ctx.$("#active-filters"), {
    childList: true,
  });
  new MutationObserver(syncFilters).observe(ctx.$("#asset-grid"), {
    attributes: true,
    attributeFilter: ["class"],
  });
  ctx.$("#filter-toggle").addEventListener("click", syncFilters);
  syncFilters();

  const appearance = document.createElement("details");
  appearance.className = "appearance-menu";
  appearance.innerHTML =
    '<summary>外观</summary><div class="appearance-popover"><span>阅读字号</span><div class="reading-slot"></div><span>浅色 / 深色</span><div class="theme-slot"></div></div>';
  ctx.$(".topbar-right").append(appearance);
  ctx.$(".reading-slot").append(ctx.$("#reading-settings"));
  ctx.$(".theme-slot").append(ctx.$("#appearance-toggle"));
  document.addEventListener("click", (e) => {
    if (!appearance.contains(e.target)) appearance.open = false;
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") appearance.open = false;
  });
  ctx.$("#reading-settings").addEventListener("click", () => {
    appearance.open = false;
  });

  ctx.$("#settings").innerHTML = ctx.icon("settings") + "材质库设置";
})();
