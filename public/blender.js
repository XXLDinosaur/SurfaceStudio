import { app as ctx } from "./modules/runtime.js";
/* Local Blender bridge. Material operations execute in Blender, never in the browser. */
(() => {
  let sessions = [],
    selectedSession = "",
    busy = false,
    lastAsset = "",
    pollTimer,
    refreshingLibrary = false;
  let importOptions = {
    repeat: 1,
    autoUV: true,
    ao: true,
    bump: false,
    flipNormalY: false,
  };
  try {
    importOptions = {
      ...importOptions,
      ...JSON.parse(localStorage.getItem("surface-blender-options") || "{}"),
    };
  } catch {}
  function help() {
    ctx.modal(
      "在 Blender 中使用你的材质库",
      `<p class="modal-description">在 Windows 桌面客户端按住材质球，拖到 Blender 视口的模型表面松开，即可给落点模型赋材质，无需预先选中。需要插件 1.1.0+ 和对象模式。也可选中模型后点击「赋予到 Blender」。</p><ol class="bridge-steps"><li>Blender 的 3D 视图中按 <b>N</b> 打开侧栏。</li><li>选择 <b>Surface Studio</b> 标签，点击「打开材质库」。</li><li>回到这里选材质，检查目标模型，然后点击「赋予到 Blender」。</li></ol><div class="bridge-help-note">对象模式会覆盖选中模型各面的材质分配；编辑模式只作用于选中的面。原材质仍保留在材质槽，Blender 中可按 Ctrl + Z 撤销。</div><p class="form-note">没有 Surface Studio 标签？安装软件目录中的 surface_studio_bridge.zip：编辑 → 偏好设置 → 插件 → 从磁盘安装，然后启用 Surface Studio。兼容 Blender 4.2 及以上版本。</p><div class="modal-actions"><button class="primary-button" id="bridge-help-done">知道了</button></div>`,
      "BLENDER LIVE LINK",
    );
    document.querySelector("#bridge-help-done").onclick = () =>
      document.querySelector("#modal").close();
  }
  function activeSession() {
    return sessions.find((s) => s.id === selectedSession) || sessions[0];
  }
  function statusText(session) {
    if (!session) return "在 Blender 侧栏中点击「打开材质库」以连接";
    if (!session.objects?.length)
      return "已连接，请先在 Blender 中选中网格模型";
    const names = session.objects
      .slice(0, 3)
      .map((o) => o.name)
      .join("、");
    return `${names}${session.objects.length > 3 ? ` 等 ${session.objects.length} 个模型` : ""}${session.mode === "EDIT_MESH" ? ` · ${session.selectedFaces} 个选中面` : " · 整个模型"}`;
  }
  function updateStatus() {
    const area = document.querySelector("#blender-panel");
    if (!area) return;
    const session = activeSession();
    const label = area.querySelector("#blender-target");
    label.textContent = statusText(session);
    label.title = label.textContent;
    const select = area.querySelector("#blender-session");
    if (document.activeElement !== select) {
      const next = sessions
        .map(
          (s) =>
            `<option value="${ctx.esc(s.id)}">Blender ${ctx.esc(s.version)} · ${ctx.esc(s.file)} · PID ${s.pid}</option>`,
        )
        .join("");
      if (select.innerHTML !== next) select.innerHTML = next;
      if (session) select.value = session.id;
    }
    select.hidden = sessions.length < 2;
    const button = area.querySelector("#send-blender");
    const decal = ctx.byId.get(ctx.selected)?.kind === "decal";
    const valid =
      !decal &&
      session?.objects?.length &&
      ["OBJECT", "EDIT_MESH"].includes(session.mode) &&
      (session.mode !== "EDIT_MESH" || session.selectedFaces > 0);
    button.disabled = busy || !valid || session?.busy;
    if (!busy)
      button.innerHTML = `${ctx.icon("cube")} ${session?.busy ? "Blender 正在处理中…" : decal ? "拖到模型表面添加贴花" : "赋予到 Blender"}`;
    area.querySelector("#blender-mode-note").textContent = decal
      ? "贴花仅支持桌面拖放 · 保留原材质 · 需插件 1.3.0"
      : session?.mode === "EDIT_MESH"
        ? "仅改变选中面的材质 · Ctrl + Z 可撤销"
        : "赋予全部选中网格 · 原材质槽保留 · 可撤销";
  }
  function mount() {
    const body = document.querySelector("#detail .detail-body");
    if (!body || !ctx.selected) return;
    if (document.querySelector("#blender-panel")) return;
    lastAsset = ctx.selected;
    const panel = document.createElement("section");
    panel.className = "blender-panel";
    panel.id = "blender-panel";
    panel.innerHTML = `<div class="blender-panel-title"><span><span class="blender-symbol">◉</span> BLENDER LIVE LINK</span><button class="text-button" id="blender-help">连接帮助</button></div><select id="blender-session" aria-label="目标 Blender 窗口" hidden></select><div id="blender-target" class="blender-target" role="status"></div><button class="primary-button" id="send-blender" disabled>${ctx.icon("cube")}赋予到 Blender</button><div id="blender-mode-note" class="blender-mode-note"></div><details class="blender-options"><summary>贴图与导入选项</summary><div class="blender-options-body"><label>平铺次数<input id="blender-repeat" type="number" min="0.01" max="100" step="0.25" value="${Number(importOptions.repeat) || 1}"></label><label><input id="blender-autoUV" type="checkbox" ${importOptions.autoUV ? "checked" : ""}>无 UV 时自动展开（对象模式）</label><label><input id="blender-ao" type="checkbox" ${importOptions.ao ? "checked" : ""}>连接 AO 环境遮蔽</label><label><input id="blender-bump" type="checkbox" ${importOptions.bump ? "checked" : ""}>使用高度贴图添加凹凸细节</label><label><input id="blender-flipNormalY" type="checkbox" ${importOptions.flipNormalY ? "checked" : ""}>翻转法线绿色通道（DirectX）</label><p>默认使用 OpenGL 法线。凹凸不会改变模型几何。</p></div></details><div id="blender-result" class="blender-result" role="status"></div>`;
    body.querySelector("#copy-path").insertAdjacentElement("afterend", panel);
    panel.querySelector("#blender-help").onclick = help;
    panel.querySelector("#blender-session").onchange = (e) => {
      selectedSession = e.target.value;
      updateStatus();
    };
    panel.querySelector("#send-blender").onclick = send;
    if (ctx.byId.get(ctx.selected)?.kind === "blend") {
      panel.querySelector(".blender-options summary").textContent =
        "导入选项（原生节点保持不变）";
      for (const id of [
        "blender-repeat",
        "blender-ao",
        "blender-bump",
        "blender-flipNormalY",
      ])
        panel.querySelector("#" + id).closest("label").hidden = true;
      panel.querySelector(".blender-options-body p").textContent =
        "平铺与法线方向沿用材质原始节点设置。需要连接插件 1.2.0 或更新版本。";
    }
    if (ctx.byId.get(ctx.selected)?.kind === "decal")
      panel.querySelector(".blender-options").hidden = true;
    updateStatus();
  }
  async function send() {
    const session = activeSession();
    if (!session || busy) return;
    const assetId = ctx.selected;
    importOptions.repeat = Number(
      document.querySelector("#blender-repeat").value,
    );
    for (const key of ["autoUV", "ao", "bump", "flipNormalY"])
      importOptions[key] = document.querySelector("#blender-" + key).checked;
    if (
      !Number.isFinite(importOptions.repeat) ||
      importOptions.repeat < 0.01 ||
      importOptions.repeat > 100
    )
      return ctx.toast("平铺次数应在 0.01 到 100 之间");
    try {
      localStorage.setItem(
        "surface-blender-options",
        JSON.stringify(importOptions),
      );
    } catch {}
    busy = true;
    updateStatus();
    document.querySelector("#send-blender").innerHTML =
      `${ctx.icon("refresh")} 正在发送到 Blender…`;
    setResult("正在等待 Blender 接收…");
    try {
      const job = await ctx.post("/api/blender/apply", {
        session: session.id,
        revision: session.revision,
        asset: assetId,
        options: importOptions,
      });
      const deadline = Date.now() + 190000;
      while (Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, 700));
        const response = await fetch(
          "/api/blender/result?id=" + encodeURIComponent(job.id),
        );
        const result = await response.json();
        if (!response.ok)
          throw Error(result.error || "无法读取 Blender 导入结果");
        if (ctx.selected === assetId) setResult(result.message, result.status);
        if (["success", "error", "unknown"].includes(result.status)) {
          if (result.status === "success") {
            const suffix = result.autoUV
              ? ` · 已自动展开 ${result.autoUV} 个模型的 UV`
              : "";
            ctx.toast(result.message + suffix);
            if (ctx.selected === assetId)
              setResult(
                result.message +
                  suffix +
                  (result.warnings?.length
                    ? "\n" + result.warnings.join("；")
                    : ""),
                "success",
              );
          } else ctx.toast(result.message);
          return;
        }
      }
      throw Error("等待时间较长，请在 Blender 中检查导入结果");
    } catch (error) {
      setResult(error.message, "error");
      ctx.toast(error.message);
    } finally {
      busy = false;
      updateStatus();
    }
  }
  function setResult(text, state = "pending") {
    const el = document.querySelector("#blender-result");
    if (el) {
      el.textContent = text;
      el.dataset.state = state;
    }
  }
  const observer = new MutationObserver(() => mount());
  observer.observe(document.querySelector("#detail"), { childList: true });
  async function poll() {
    try {
      const response = await fetch("/api/blender/status");
      if (!response.ok) throw Error("offline");
      const data = await response.json();
      sessions = data.sessions || [];
      if (
        ctx.library &&
        data.scannedAt &&
        data.scannedAt !== ctx.library.scannedAt &&
        !refreshingLibrary
      ) {
        refreshingLibrary = true;
        try {
          await ctx.load();
        } finally {
          refreshingLibrary = false;
        }
      }
      if (!sessions.some((s) => s.id === selectedSession))
        selectedSession = sessions[0]?.id || "";
    } catch {
      sessions = [];
    }
    updateStatus();
    pollTimer = setTimeout(poll, document.hidden ? 2500 : 1000);
  }
  window.addEventListener("beforeunload", () => {
    clearTimeout(pollTimer);
    observer.disconnect();
  });
  window.surfaceBlender = {
    applyFromMenu(id) {
      if (busy) return ctx.toast("上一个材质仍在处理中，请稍候");
      if (ctx.selected !== id || document.querySelector("#detail").hidden)
        ctx.openDetail(id);
      mount();
      updateStatus();
      const button = document.querySelector("#send-blender");
      if (!button) return;
      button.scrollIntoView({ block: "nearest", behavior: "smooth" });
      if (button.disabled) {
        const session = activeSession();
        ctx.toast(
          session?.busy ? "Blender 正在处理中，请稍候" : statusText(session),
        );
        return;
      }
      send();
    },
  };
  mount();
  poll();
})();
