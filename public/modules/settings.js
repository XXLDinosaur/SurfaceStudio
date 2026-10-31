/** @param {import("./runtime.js").AppContext} ctx */
export function createSettings(ctx) {
  function settings() {
    ctx.modal(
      "你的材质，妥善安放",
      `<p class="modal-description">Surface 直接读取本地材质库。收藏、分类记录和缩略图保存在软件目录，不会修改或搬动任何原始素材。</p><div class="settings-tools"><button class="outline-button" id="organization-backup">${ctx.icon("folder")}整理备份与恢复 ${ctx.icon("arrow")}</button><button class="outline-button" id="software-updates">${ctx.icon("refresh")}软件更新</button></div><label class="form-label" for="root-path">材质库文件夹</label><input class="form-input" id="root-path" value="${ctx.esc(ctx.library.root)}"><p class="form-note">选择包含材质子文件夹的目录。新增或移除素材后，重新扫描即可更新。<br>中文路径与 Megascans / Bridge 材质结构均受支持。</p><p class="form-note">普通库结构：素材库 / 材质文件夹 / 贴图。仅扫描一层；支持 JPG、JPEG、PNG、TIF、TIFF、EXR，不直接解析普通 blend、sbsar 或压缩包；SS 插件导出的 Blender 材质包请在下方添加。</p><label class="form-label" for="material-save-root">Blender 添加材质的保存位置</label><input class="form-input" id="material-save-root" placeholder="留空：与上方材质库文件夹一致" value="${ctx.esc(ctx.library.materialSaveRoot || "")}"><p class="form-note">默认保存到当前导入的材质库。也可填写其他文件夹；Blender 点击“添加到 SS”后直接存入这里并显示在“未分类”，无需单独导出或再次添加目录。</p><label class="form-label" for="decal-root">贴花图库</label><input class="form-input" id="decal-root" placeholder="选择包含贴花子文件夹的目录" value="${ctx.esc(ctx.library.decalRoot || "")}"><p class="form-note">颜色贴图 + Opacity 遮罩，一目录一贴花；拖到 Blender 模型表面叠加，保留原材质。需插件 1.3.0；图集暂整张显示。</p><label class="form-label" for="normal-root">法线贴图库（每张图单独入库）</label><input class="form-input" id="normal-root" placeholder="可选：例如 D:\\水面法线" value="${ctx.esc(ctx.library.normalRoot || "")}"><p class="form-note">递归扫描子文件夹，每张图单独作为 Normal 素材，不要求特定文件名。仅放法线图；留空可取消此来源。EXR 可入库及送入 Blender，界面不解码其预览。</p><label class="form-label" for="blender-roots">其他已有 Blender 材质目录（可选，每行一个）</label><textarea class="form-input" id="blender-roots" rows="3" placeholder="仅在需要读取其他材质包目录时填写">${ctx.esc((ctx.library.blenderRoots || []).join("\n"))}</textarea><p class="form-note">当前材质库和上方保存位置会自动识别，无需重复填写。此处仅用于添加其他已有材质包目录；留空不删除文件。</p><div class="modal-stats"><div><b>${ctx.fmt(ctx.assets.length)}</b><small>已索引材质</small></div><div><b>${ctx.bytes(ctx.library.totalBytes)}</b><small>素材总大小</small></div><div><b>${ctx.library.categories.length}</b><small>材质分类</small></div></div><p class="form-note">上次扫描：${ctx.library.scannedAt ? new Date(ctx.library.scannedAt * 1000).toLocaleString("zh-CN") : "尚未扫描"}${ctx.library.warnings.length ? `<br>有 ${ctx.library.warnings.length} 个目录未能读取，请检查索引日志。` : ""}</p><div id="settings-error" class="modal-error" role="alert"></div><div class="modal-actions"><button class="outline-button" id="settings-cancel">取消</button><button class="primary-button" id="settings-save">${ctx.icon("refresh")}保存并重新扫描</button></div><div class="settings-version"><span>Surface Studio · v${ctx.esc(ctx.library.releaseNotes?.version || "—")}</span><button class="text-button" id="view-release-notes">本版本更新说明</button></div>`,
      "LIBRARY SETTINGS",
    );
    ctx.$("#view-release-notes").onclick = () => {
      const draft = [
        "root-path",
        "normal-root",
        "decal-root",
        "blender-roots",
        "material-save-root",
      ].map((id) => [id, ctx.$("#" + id).value]);
      window.openReleaseNotes(() => {
        ctx.settings();
        draft.forEach(([id, value]) => (ctx.$("#" + id).value = value));
      });
    };
    ctx.$("#software-updates").onclick = () => window.openUpdates();
    ctx.$("#organization-backup").onclick = () => {
      const draft = [
        "root-path",
        "normal-root",
        "decal-root",
        "blender-roots",
        "material-save-root",
      ].map((id) => [id, ctx.$("#" + id).value]);
      window.openOrganizationBackup(() => {
        ctx.settings();
        draft.forEach(([id, value]) => (ctx.$("#" + id).value = value));
      });
    };
    ctx.$("#settings-cancel").onclick = () => ctx.$("#modal").close();
    ctx.$("#settings-save").onclick = async () => {
      const b = ctx.$("#settings-save");
      b.disabled = true;
      try {
        await ctx.post("/api/rescan", {
          root: ctx.$("#root-path").value.trim(),
          materialSaveRoot: ctx.$("#material-save-root").value.trim(),
          decalRoot: ctx.$("#decal-root").value.trim(),
          normalRoot: ctx.$("#normal-root").value.trim(),
          blenderRoots: ctx
            .$("#blender-roots")
            .value.split(/\r?\n/)
            .map((s) => s.trim())
            .filter(Boolean),
        });
        ctx.$("#modal").close();
        ctx.pollScan();
      } catch (e) {
        ctx.$("#settings-error").textContent = e.message;
      } finally {
        b.disabled = false;
      }
    };
  }
  async function rescan() {
    if (!ctx.library) return;
    try {
      await ctx.post("/api/rescan");
      ctx.pollScan();
    } catch (e) {
      ctx.toast(e.message);
    }
  }
  function pollScan() {
    clearTimeout(ctx.scanPoll);
    ctx.$("#refresh").disabled = true;
    ctx.$("#refresh svg").classList.add("spin");
    ctx.$("#index-status").textContent = "正在扫描材质库…";
    ctx.toast("正在更新本地索引");
    async function poll() {
      try {
        const r = await fetch("/api/status");
        const status = await r.json();
        if (status.scanning) {
          ctx.scanPoll = setTimeout(poll, 700);
          return;
        }
        ctx.$("#refresh").disabled = false;
        ctx.$("#refresh svg").classList.remove("spin");
        if (status.error) {
          ctx.toast("扫描失败：" + status.error);
          ctx.$("#index-status").textContent = "扫描失败 · 请检查路径";
          return;
        }
        ctx.closeDetail();
        ctx.compared = [];
        ctx.$("#compare-tray").hidden = true;
        await ctx.load();
        ctx.toast(
          ctx.library.warnings.length
            ? `扫描完成：${ctx.fmt(status.count)} 个素材；${ctx.library.warnings[0]}`
            : `扫描完成，${ctx.fmt(status.count)} 个材质已就绪`,
        );
      } catch (e) {
        ctx.$("#refresh").disabled = false;
        ctx.$("#refresh svg").classList.remove("spin");
        ctx.toast("连接中断，请重新启动软件");
      }
    }
    ctx.scanPoll = setTimeout(poll, 500);
  }
  return { settings, rescan, pollScan };
}
