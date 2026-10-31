import { app as ctx } from "./modules/runtime.js";
import { createNavigation } from "./modules/navigation.js";
import { createLibrary } from "./modules/library.js";
import { createDetails } from "./modules/details.js";
import { createSettings } from "./modules/settings.js";
import { createUi } from "./modules/ui.js";
Object.defineProperties(ctx, {
  $: { get: () => $ },
  $$: { get: () => $$ },
  esc: { get: () => esc },
  icon: { get: () => icon },
  fmt: { get: () => fmt },
  bytes: { get: () => bytes },
  assetType: {
    get: () => assetType,
    set: (value) => {
      assetType = value;
    },
  },
  expandedTypes: {
    get: () => expandedTypes,
    set: (value) => {
      expandedTypes = value;
    },
  },
  assetTypeNames: { get: () => assetTypeNames },
  assetInType: {
    get: () => assetInType,
    set: (value) => {
      assetInType = value;
    },
  },
  library: {
    get: () => library,
    set: (value) => {
      library = value;
    },
  },
  assets: {
    get: () => assets,
    set: (value) => {
      assets = value;
    },
  },
  byId: {
    get: () => byId,
    set: (value) => {
      byId = value;
    },
  },
  state: {
    get: () => state,
    set: (value) => {
      state = value;
    },
  },
  token: {
    get: () => token,
    set: (value) => {
      token = value;
    },
  },
  view: {
    get: () => view,
    set: (value) => {
      view = value;
    },
  },
  category: {
    get: () => category,
    set: (value) => {
      category = value;
    },
  },
  nature: {
    get: () => nature,
    set: (value) => {
      nature = value;
    },
  },
  selected: {
    get: () => selected,
    set: (value) => {
      selected = value;
    },
  },
  filtered: {
    get: () => filtered,
    set: (value) => {
      filtered = value;
    },
  },
  limit: {
    get: () => limit,
    set: (value) => {
      limit = value;
    },
  },
  compared: {
    get: () => compared,
    set: (value) => {
      compared = value;
    },
  },
  timer: {
    get: () => timer,
    set: (value) => {
      timer = value;
    },
  },
  toastTimer: {
    get: () => toastTimer,
    set: (value) => {
      toastTimer = value;
    },
  },
  scanPoll: {
    get: () => scanPoll,
    set: (value) => {
      scanPoll = value;
    },
  },
  prefs: {
    get: () => prefs,
    set: (value) => {
      prefs = value;
    },
  },
  preference: {
    get: () => preference,
    set: (value) => {
      preference = value;
    },
  },
  assetFolder: {
    get: () => assetFolder,
    set: (value) => {
      assetFolder = value;
    },
  },
  imageURL: {
    get: () => imageURL,
    set: (value) => {
      imageURL = value;
    },
  },
  fileURL: {
    get: () => fileURL,
    set: (value) => {
      fileURL = value;
    },
  },
  toast: {
    get: () => toast,
    set: (value) => {
      toast = value;
    },
  },
  post: {
    get: () => post,
    set: (value) => {
      post = value;
    },
  },
  stateQueue: {
    get: () => stateQueue,
    set: (value) => {
      stateQueue = value;
    },
  },
  saveState: {
    get: () => saveState,
    set: (value) => {
      saveState = value;
    },
  },
  setFavorite: {
    get: () => setFavorite,
    set: (value) => {
      setFavorite = value;
    },
  },
  skeleton: {
    get: () => skeleton,
    set: (value) => {
      skeleton = value;
    },
  },
  load: {
    get: () => load,
    set: (value) => {
      load = value;
    },
  },
  renderNav: {
    get: () => renderNav,
    set: (value) => {
      renderNav = value;
    },
  },
  currentTitle: {
    get: () => currentTitle,
    set: (value) => {
      currentTitle = value;
    },
  },
  navigate: {
    get: () => navigate,
    set: (value) => {
      navigate = value;
    },
  },
  curated: {
    get: () => curated,
    set: (value) => {
      curated = value;
    },
  },
  renderResults: {
    get: () => renderResults,
    set: (value) => {
      renderResults = value;
    },
  },
  drawCards: {
    get: () => drawCards,
    set: (value) => {
      drawCards = value;
    },
  },
  closeDetail: {
    get: () => closeDetail,
    set: (value) => {
      closeDetail = value;
    },
  },
  openDetail: {
    get: () => openDetail,
    set: (value) => {
      openDetail = value;
    },
  },
  statsHTML: {
    get: () => statsHTML,
    set: (value) => {
      statsHTML = value;
    },
  },
  copy: {
    get: () => copy,
    set: (value) => {
      copy = value;
    },
  },
  modal: {
    get: () => modal,
    set: (value) => {
      modal = value;
    },
  },
  previewModal: {
    get: () => previewModal,
    set: (value) => {
      previewModal = value;
    },
  },
  toggleCompare: {
    get: () => toggleCompare,
    set: (value) => {
      toggleCompare = value;
    },
  },
  renderCompareTray: {
    get: () => renderCompareTray,
    set: (value) => {
      renderCompareTray = value;
    },
  },
  settings: {
    get: () => settings,
    set: (value) => {
      settings = value;
    },
  },
  rescan: {
    get: () => rescan,
    set: (value) => {
      rescan = value;
    },
  },
  pollScan: {
    get: () => pollScan,
    set: (value) => {
      pollScan = value;
    },
  },
  gridMode: {
    get: () => gridMode,
    set: (value) => {
      gridMode = value;
    },
  },
  autoLoadPending: {
    get: () => autoLoadPending,
    set: (value) => {
      autoLoadPending = value;
    },
  },
  queueMoreMaterials: {
    get: () => queueMoreMaterials,
    set: (value) => {
      queueMoreMaterials = value;
    },
  },
  moreObserver: { get: () => moreObserver },
});
let { assetInType, renderNav, currentTitle, navigate, curated } =
  createNavigation(ctx);
let { skeleton, load, renderResults, drawCards, queueMoreMaterials } =
  createLibrary(ctx);
let { closeDetail, openDetail, statsHTML, previewModal, toggleCompare } =
  createDetails(ctx);
let { settings, rescan, pollScan } = createSettings(ctx);
let {
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
} = createUi(ctx);
("use strict");
const $ = (s, r = document) => r.querySelector(s),
  $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const icon = (n) => `<svg aria-hidden="true"><use href="#i-${n}"/></svg>`;
const fmt = (n) => new Intl.NumberFormat("en-US").format(n);
const bytes = (n) =>
  n >= 1073741824
    ? (n / 1073741824).toFixed(1) + " GB"
    : n >= 1048576
      ? (n / 1048576).toFixed(1) + " MB"
      : (n / 1024).toFixed(0) + " KB";
let assetType = "",
  expandedTypes = new Set(["material"]);
const assetTypeNames = {
  uncategorized: "未分类",
  material: "材质",
  normal: "法线",
  decal: "贴花",
};

let library,
  assets = [],
  byId = new Map(),
  state = { favorites: [], collections: [], recent: [] },
  token = "",
  view = "all",
  category = "",
  nature = false,
  selected = null,
  filtered = [],
  limit = 48,
  compared = [],
  timer,
  toastTimer,
  scanPoll;
let prefs = {};
try {
  prefs = JSON.parse(localStorage.getItem("surface-preferences") || "{}");
} catch {}

let stateQueue = Promise.resolve();

document.addEventListener("click", (e) => {
  const fav = e.target.closest("[data-favorite]");
  if (fav) {
    e.preventDefault();
    e.stopPropagation();
    setFavorite(fav.dataset.favorite);
    return;
  }
  const comp = e.target.closest("[data-compare]");
  if (comp) {
    e.preventDefault();
    e.stopPropagation();
    toggleCompare(comp.dataset.compare);
    return;
  }
  const card = e.target.closest("[data-asset]");
  if (card) openDetail(card.dataset.asset);
  const cat = e.target.closest("[data-category]");
  if (cat)
    navigate(
      "all",
      cat.dataset.category,
      "",
      false,
      cat.dataset.parentType || "",
    );
  const type = e.target.closest("[data-asset-type]");
  if (type) navigate("all", "", "", false, type.dataset.assetType);
  const toggle = e.target.closest("[data-toggle-type]");
  if (toggle) {
    const key = toggle.dataset.toggleType;
    expandedTypes.has(key)
      ? expandedTypes.delete(key)
      : (expandedTypes = new Set([key]));
    renderNav();
  }
  const filter = e.target.closest("[data-clear]");
  if (filter) {
    const key = filter.dataset.clear;
    if (key === "view") navigate();
    else {
      const input = $("#" + key);
      if (input.type === "checkbox") input.checked = false;
      else input.value = "";
      renderResults();
    }
  }
});
$("#asset-grid").addEventListener("keydown", (e) => {
  if (
    (e.key === "Enter" || e.key === " ") &&
    e.target.matches("[data-asset]")
  ) {
    e.preventDefault();
    openDetail(e.target.dataset.asset);
  }
});
$$("#main-nav button").forEach(
  (b) => (b.onclick = () => navigate(b.dataset.view)),
);
$("#search").oninput = () => {
  clearTimeout(timer);
  timer = setTimeout(() => renderResults(), 120);
};
$("#map-filter").onchange = () => renderResults();
$("#sort").onchange = () => {
  preference("sort", $("#sort").value);
  renderResults();
};
$("#resolution-filter").onchange = () => renderResults();
$("#tileable-filter").onchange = () => renderResults();
$("#empty-reset").onclick = () => navigate();
$("#tab-all").onclick = () => navigate();
$("#refresh").onclick = rescan;
$("#settings").onclick = settings;
$("#library-button").onclick = settings;
$("#filter-toggle").onclick = () => {
  $("#advanced-filters").hidden = !$("#advanced-filters").hidden;
  $("#filter-toggle").classList.toggle(
    "active",
    !$("#advanced-filters").hidden,
  );
};
$("#reset-filters").onclick = () => {
  for (const id of ["search", "map-filter", "resolution-filter"])
    $("#" + id).value = "";
  $("#tileable-filter").checked = false;
  renderResults();
};
$("#density").oninput = (e) => {
  document.documentElement.style.setProperty(
    "--card-size",
    e.target.value + "px",
  );
  preference("density", e.target.value);
};
$("#grid-view").onclick = () => gridMode("grid");
$("#list-view").onclick = () => gridMode("list");
$("#modal").onclick = (e) => {
  if (e.target === $("#modal")) {
    const rect = $("#modal").getBoundingClientRect();
    if (
      e.clientX < rect.left ||
      e.clientX > rect.right ||
      e.clientY < rect.top ||
      e.clientY > rect.bottom
    )
      $("#modal").close();
  }
};
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    $("#search").focus();
    $("#search").select();
  }
  if (e.key === "Escape" && !$("#modal").open) closeDetail();
  if (
    e.key.toLowerCase() === "f" &&
    !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName) &&
    !$("#modal").open &&
    selected
  ) {
    e.preventDefault();
    setFavorite(selected);
  }
});
if (prefs.density) {
  $("#density").value = prefs.density;
  document.documentElement.style.setProperty(
    "--card-size",
    prefs.density + "px",
  );
}
if (prefs.sort) $("#sort").value = prefs.sort;
gridMode(prefs.mode || "grid");
skeleton();
load();

// Observe the list footer inside its actual scroll container; append preserves focus and previews.
let autoLoadPending = false;

const moreObserver = new IntersectionObserver(
  (entries) => {
    if (entries.some((entry) => entry.isIntersecting)) queueMoreMaterials();
  },
  { root: $("#scroll-area"), rootMargin: "0px 0px 160px 0px" },
);
moreObserver.observe($(".load-more"));
$("#scroll-area").addEventListener("scroll", queueMoreMaterials, {
  passive: true,
});
new ResizeObserver(queueMoreMaterials).observe($("#scroll-area"));
