import { app as ctx } from "./modules/runtime.js";
/* Windows native drag-out; Blender's file handler resolves the hovered mesh. */
(() => {
  // The library is a drag source, never a file/URL drop destination.
  // Prevent WebView2's default navigation or external browser launch.
  for (const name of ["dragenter", "dragover", "drop"])
    document.addEventListener(
      name,
      (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer) e.dataTransfer.dropEffect = "none";
      },
      true,
    );
  let candidate = null,
    dragging = false,
    suppressClickUntil = 0,
    cached = null;
  function options() {
    try {
      return JSON.parse(
        localStorage.getItem("surface-blender-options") || "{}",
      );
    } catch {
      return {};
    }
  }
  function prepare(id) {
    const opts = options(),
      key = JSON.stringify(opts);
    if (
      !cached ||
      cached.id !== id ||
      cached.key !== key ||
      Date.now() - cached.created > 240000
    ) {
      const prepared = ctx.post("/api/blender/drop", {
        asset: id,
        options: opts,
      });
      prepared.catch(() => {});
      cached = { id, key, created: Date.now(), prepared };
    }
    return cached.prepared;
  }
  function assetAt(target) {
    if (document.body.classList.contains("bulk-mode")) return null;
    if (target.closest("button,input,select,a")) return null;
    const image = target.closest(".card-image");
    if (image) return image.closest("[data-asset]")?.dataset.asset;
    if (target.closest("#detail-preview")) return ctx.selected;
    return null;
  }
  document.addEventListener(
    "dragstart",
    (e) => {
      if (assetAt(e.target)) e.preventDefault();
    },
    true,
  );
  document.addEventListener("pointerover", (e) => {
    if (!window.pywebview?.api?.start_material_drag || dragging) return;
    const id = assetAt(e.target);
    if (id) {
      const area = e.target.closest(".card-image,#detail-preview");
      if (area) area.title = "拖到 SketchUp 或 Blender 模型上";
    }
  });
  document.addEventListener("pointerdown", (e) => {
    if (
      e.ctrlKey ||
      e.shiftKey ||
      e.metaKey ||
      e.button !== 0 ||
      !window.pywebview?.api?.start_material_drag
    )
      return;
    const id = assetAt(e.target);
    if (id) {
      const prepared = prepare(id);
      candidate = { id, x: e.clientX, y: e.clientY, prepared };
    }
  });
  document.addEventListener("pointerup", () => (candidate = null));
  document.addEventListener("pointercancel", () => (candidate = null));
  document.addEventListener(
    "click",
    (e) => {
      if (dragging || Date.now() < suppressClickUntil) {
        e.preventDefault();
        e.stopImmediatePropagation();
      }
    },
    true,
  );
  document.addEventListener("pointermove", async (e) => {
    if (
      !candidate ||
      dragging ||
      !(e.buttons & 1) ||
      Math.hypot(e.clientX - candidate.x, e.clientY - candidate.y) < 10
    )
      return;
    const pending = candidate;
    candidate = null;
    cached = null;
    dragging = true;
    document.body.classList.add("material-dragging");
    try {
      const prepared = await pending.prepared;
      const result = await window.pywebview.api.start_material_drag(
        prepared.path,
      );
      if (result.dropped) {
        ctx.toast("正在赋予到 " + (result.target || "Blender") + "…");
        const deadline = Date.now() + 90000;
        async function poll() {
          try {
            const response = await fetch(
              "/api/blender/result?id=" + prepared.id,
            );
            const status = await response.json();
            if (["success", "error", "unknown"].includes(status.status)) {
              ctx.toast(status.message);
              return;
            }
            if (Date.now() < deadline) setTimeout(poll, 500);
            else
              ctx.toast(
                "未收到目标软件确认，请检查插件和模型视口",
              );
          } catch {
            ctx.toast("暂未收到结果，请在目标软件中检查材质");
          }
        }
        poll();
      }
    } catch (error) {
      ctx.toast("拖拽未完成：" + error.message);
    } finally {
      dragging = false;
      suppressClickUntil = Date.now() + 300;
      document.body.classList.remove("material-dragging");
    }
  });
})();

