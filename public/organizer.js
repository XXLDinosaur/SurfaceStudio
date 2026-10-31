import { app as ctx } from "./modules/runtime.js";
/* Selection and portable organization records; source textures stay untouched. */
(() => {
  let enabled = false,
    busy = false,
    anchor = null;
  const picked = new Set();
  const toggle = document.createElement("button");
  toggle.id = "bulk-toggle";
  toggle.className = "outline-button";
  toggle.textContent = "批量整理";
  ctx.$(".toolbar").append(toggle);
  const bar = document.createElement("div");
  bar.id = "bulk-bar";
  bar.hidden = true;
  bar.innerHTML =
    '<span id="bulk-count"></span><button data-bulk="all">全选筛选结果</button><button data-bulk="clear">清空选择</button><button data-bulk="category">修改分类</button><button data-bulk="favorite">收藏</button><button data-bulk="unfavorite">取消收藏</button><button data-bulk="exit">完成</button>';
  ctx.$(".workbench-controls").append(bar);
  function sync() {
    const allowed = new Set(ctx.filtered.map((a) => a.id));
    for (const id of picked) if (!allowed.has(id)) picked.delete(id);
    document.body.classList.toggle("bulk-mode", enabled);
    bar.hidden = !enabled;
    toggle.setAttribute("aria-pressed", String(enabled));
    ctx.$("#bulk-count").textContent =
      `已选 ${picked.size} / ${ctx.filtered.length}`;
    ctx
      .$$("#bulk-bar button")
      .forEach(
        (b) =>
          (b.disabled =
            busy ||
            (["category", "favorite", "unfavorite", "collection"].includes(
              b.dataset.bulk,
            ) &&
              !picked.size)),
      );
    ctx.$$("#asset-grid [data-asset]").forEach((c) => {
      c.classList.toggle("bulk-picked", picked.has(c.dataset.asset));
      if (enabled) {
        c.setAttribute("aria-pressed", String(picked.has(c.dataset.asset)));
        c.setAttribute(
          "aria-label",
          `选择 ${ctx.byId.get(c.dataset.asset)?.name || "材质"}`,
        );
      } else {
        c.removeAttribute("aria-pressed");
        c.setAttribute(
          "aria-label",
          `查看 ${ctx.byId.get(c.dataset.asset)?.name || "材质"}`,
        );
      }
    });
  }
  toggle.onclick = () => {
    enabled = !enabled;
    picked.clear();
    anchor = null;
    sync();
  };
  function pick(card, event) {
    enabled = true;
    const id = card.dataset.asset;
    const index = ctx.filtered.findIndex((a) => a.id === id),
      start = ctx.filtered.findIndex((a) => a.id === anchor);
    if (event.shiftKey && start >= 0)
      ctx.filtered
        .slice(Math.min(start, index), Math.max(start, index) + 1)
        .forEach((a) => picked.add(a.id));
    else {
      if (picked.has(id)) picked.delete(id);
      else picked.add(id);
    }
    anchor = id;
    sync();
  }
  document.addEventListener(
    "click",
    (e) => {
      const c = e.target.closest("#asset-grid [data-asset]");
      if (c && (enabled || e.ctrlKey || e.metaKey || e.shiftKey)) {
        e.preventDefault();
        e.stopImmediatePropagation();
        if (!busy) pick(c, e);
      }
    },
    true,
  );
  document.addEventListener(
    "keydown",
    (e) => {
      if (
        (e.ctrlKey || e.metaKey) &&
        !e.altKey &&
        e.key.toLowerCase() === "a"
      ) {
        const target = e.target;
        if (
          target instanceof Element &&
          (target.closest("input,textarea") || target.isContentEditable)
        )
          return;
        e.preventDefault();
        window.getSelection()?.removeAllRanges();
        if (enabled && !busy && !document.querySelector("dialog[open]")) {
          ctx.filtered.forEach((a) => picked.add(a.id));
          sync();
        }
        return;
      }
      const c = e.target.closest("#asset-grid [data-asset]");
      if (c && enabled && [" ", "Enter"].includes(e.key)) {
        e.preventDefault();
        e.stopImmediatePropagation();
        if (!busy) pick(c, e);
      }
    },
    true,
  );
  new MutationObserver(sync).observe(ctx.$("#asset-grid"), { childList: true });
  async function apply(action, extra = {}) {
    if (busy) return;
    busy = true;
    sync();
    const ids = [...picked];
    try {
      await ctx.stateQueue;
      await ctx.post("/api/organize", { action, ids, ...extra });
      ctx.$("#modal").close();
      picked.clear();
      await ctx.load();
      if (ctx.selected && ctx.byId.has(ctx.selected))
        ctx.openDetail(ctx.selected);
      ctx.toast(`已整理 ${ids.length} 个材质，操作前记录已备份`);
    } catch (e) {
      ctx.toast(e.message);
    } finally {
      busy = false;
      sync();
    }
  }
  bar.onclick = (e) => {
    const action = e.target.closest("[data-bulk]")?.dataset.bulk;
    if (!action) return;
    if (action === "all") {
      ctx.filtered.forEach((a) => picked.add(a.id));
      sync();
      return;
    }
    if (action === "clear" || action === "exit") {
      picked.clear();
      if (action === "exit") enabled = false;
      sync();
      return;
    }
    const choices = action === "category" ? ctx.library.categoryOptions : null;
    ctx.modal(
      `批量${{ category: "修改分类", favorite: "收藏", unfavorite: "取消收藏" }[action]}`,
      `<p class="modal-description">将处理选中的 ${picked.size} 个材质。仅修改整理记录；操作前会自动备份。</p>${choices ? `<label class="form-label" for="bulk-choice">目标分类</label><select id="bulk-choice" class="form-input">${choices.map((c) => `<option value="${ctx.esc(c.id)}">${ctx.esc(c.name)}</option>`).join("")}${action === "category" ? '<option value="__auto__">恢复自动分类</option>' : ""}</select>` : ""}<div class="modal-actions"><button id="bulk-cancel" class="outline-button">取消</button><button id="bulk-apply" class="primary-button" ${choices && !choices.length ? "disabled" : ""}>确认处理</button></div>`,
    );
    ctx.$("#bulk-cancel").onclick = () => ctx.$("#modal").close();
    ctx.$("#bulk-apply").onclick = () => {
      const value = ctx.$("#bulk-choice")?.value;
      ctx.$("#bulk-apply").disabled = true;
      apply(
        action,
        action === "category"
          ? { category: value === "__auto__" ? null : value }
          : {},
      );
    };
  };
  window.openOrganizationBackup = (backToSettings) => {
    ctx.modal(
      "整理备份与恢复",
      `<p class="modal-description">备份当前素材库的分类、分类改名、收藏和最近浏览（兼容保留旧集合记录）。备份不含贴图、缩略图或软件外观设置。</p><p class="form-note">换电脑后先导入素材库，再选择备份文件。按材质子文件夹名称匹配，素材库可以换盘；未匹配项会跳过。</p><div class="backup-actions"><button id="backup-export" class="primary-button">创建备份</button><button id="backup-folder" class="outline-button">打开备份文件夹</button></div><label class="form-label" for="backup-file">从 JSON 备份恢复</label><input id="backup-file" type="file" accept=".json,application/json"><p class="form-note">建议将生成的备份文件另外复制到其他磁盘或云盘，避免随软件一起丢失。</p><p id="backup-result" class="form-note" role="status"></p><div class="modal-actions"><button id="backup-back" class="outline-button">返回材质库设置</button></div>`,
    );
    ctx.$("#backup-back").onclick = backToSettings;
    ctx.$("#backup-folder").onclick = () =>
      ctx
        .post("/api/organize", { action: "open-backups" })
        .catch((e) => ctx.toast(e.message));
    ctx.$("#backup-export").onclick = async () => {
      const b = ctx.$("#backup-export");
      b.disabled = true;
      try {
        await ctx.stateQueue;
        const r = await ctx.post("/api/organize", { action: "export" });
        ctx.$("#backup-result").textContent = "已保存：" + r.path;
      } catch (e) {
        ctx.$("#backup-result").textContent = e.message;
      } finally {
        b.disabled = false;
      }
    };
    ctx.$("#backup-file").onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      try {
        if (file.size > 15 * 1024 * 1024)
          throw Error("备份文件过大（最多 15 MB）");
        const data = JSON.parse(await file.text());
        await ctx.stateQueue;
        const r = await ctx.post("/api/organize", {
          action: "preview",
          backup: data,
        });
        ctx.modal(
          "确认合并恢复",
          `<p class="modal-description">匹配 ${r.matched} 个材质，未匹配 ${r.missing} 个（跳过）。备份含 ${r.favorites} 条收藏、${r.collections} 个集合。</p><p class="form-note">合并收藏和集合；已有手动归类与分类改名优先保留，${r.conflicts} 条归类冲突保留当前记录。恢复不会删除现有整理结果，也不会更改贴图文件。恢复前自动创建备份。</p><div class="modal-actions"><button id="restore-cancel" class="outline-button">取消</button><button id="restore-apply" class="primary-button">合并恢复</button></div><p id="restore-error" class="modal-error" role="alert"></p>`,
        );
        ctx.$("#restore-cancel").onclick = () => ctx.$("#modal").close();
        ctx.$("#restore-apply").onclick = async () => {
          const b = ctx.$("#restore-apply");
          b.disabled = true;
          try {
            await ctx.stateQueue;
            await ctx.post("/api/organize", {
              action: "restore",
              backup: data,
            });
            picked.clear();
            await ctx.load();
            ctx.$("#modal").close();
            ctx.toast("整理记录已合并恢复");
          } catch (e) {
            ctx.$("#restore-error").textContent = e.message;
            b.disabled = false;
          }
        };
      } catch (error) {
        ctx.$("#backup-result").textContent = "无法读取备份：" + error.message;
      }
    };
  };
})();
