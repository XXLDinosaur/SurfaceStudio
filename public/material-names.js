import { app as ctx } from "./modules/runtime.js";
function materialRenamer(id) {
  const a = ctx.byId.get(id);
  if (!a) return;
  ctx.modal(
    "重命名材质",
    `<p class="modal-description">${a.kind === "normal" ? "同步修改这张法线图片的文件名，保留扩展名。" : "同时修改材质文件夹名称，内部贴图文件名保持不变。"} SS 中的收藏和分类会保留；其他工程若引用旧路径，需要重新定位。</p><label class="form-label" for="material-name">材质名称</label><input class="form-input" id="material-name" maxlength="100" value="${ctx.esc(a.name)}"><p id="rename-error" class="modal-error" role="alert"></p><div class="modal-actions"><button class="outline-button" id="rename-cancel">取消</button><button class="primary-button" id="rename-save">保存名称</button></div>`,
  );
  ctx.$("#rename-cancel").onclick = () => ctx.$("#modal").close();
  ctx.$("#rename-save").onclick = async () => {
    const b = ctx.$("#rename-save");
    b.disabled = true;
    try {
      await ctx.stateQueue;
      await ctx.post("/api/material/rename", {
        id,
        name: ctx.$("#material-name").value,
      });
      ctx.$("#modal").close();
      await ctx.load();
      if (ctx.selected === id) ctx.openDetail(id);
      ctx.toast("材质名称及本地名称已更新");
    } catch (e) {
      ctx.$("#rename-error").textContent = e.message;
    } finally {
      b.disabled = false;
    }
  };
  ctx.$("#material-name").onkeydown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      ctx.$("#rename-save").click();
    }
  };
  ctx.$("#material-name").focus();
  ctx.$("#material-name").select();
}
let inlineMaterialEdit = null;
function editMaterialNameInPlace(name, id) {
  const a = ctx.byId.get(id);
  if (!a) return;
  if (inlineMaterialEdit) {
    inlineMaterialEdit.focus();
    return;
  }
  const input = document.createElement("input");
  input.className = "inline-material-name";
  input.value = a.name;
  input.maxLength = 100;
  input.setAttribute("aria-label", "材质名称");
  input.title = "回车保存 · Esc 取消";
  let finished = false,
    saving = false;
  inlineMaterialEdit = input;
  function finish(value) {
    finished = true;
    if (name.contains(input)) name.textContent = value;
    if (inlineMaterialEdit === input) inlineMaterialEdit = null;
  }
  async function save() {
    if (finished || saving) return;
    const value = input.value.trim();
    if (value === a.name) {
      finish(a.name);
      return;
    }
    if (!value) {
      input.setAttribute("aria-invalid", "true");
      ctx.toast("请输入材质名称");
      input.focus();
      return;
    }
    saving = true;
    input.readOnly = true;
    input.setAttribute("aria-busy", "true");
    try {
      await ctx.stateQueue;
      await ctx.post("/api/material/rename", { id, name: value });
      finish(value);
      const top = ctx.$("#scroll-area").scrollTop;
      await ctx.load();
      ctx.$("#scroll-area").scrollTop = top;
      if (ctx.selected === id && !ctx.$("#detail").hidden) ctx.openDetail(id);
      ctx.toast("名称已更新，文件夹名称已同步");
    } catch (e) {
      ctx.toast(e.message);
      input.setAttribute("aria-invalid", "true");
      input.title = e.message;
      if (input.isConnected) {
        input.readOnly = false;
        input.focus();
        input.select();
      } else finish(a.name);
    } finally {
      saving = false;
      input.readOnly = false;
      input.removeAttribute("aria-busy");
    }
  }
  input.addEventListener("click", (e) => e.stopPropagation());
  input.addEventListener("dblclick", (e) => e.stopPropagation());
  input.addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.isComposing) return;
    if (e.key === "Enter") {
      e.preventDefault();
      save();
    }
    if (e.key === "Escape" && !saving) {
      e.preventDefault();
      finish(a.name);
    }
  });
  input.addEventListener("blur", save);
  input.addEventListener("input", () => {
    input.removeAttribute("aria-invalid");
    input.title = "回车保存 · Esc 取消";
  });
  name.replaceChildren(input);
  input.focus();
  input.select();
}
(() => {
  let nameClick;
  document.addEventListener(
    "click",
    (e) => {
      const name = e.target.closest("#asset-grid .card-info h3");
      if (e.target.closest("input")) return;
      if (
        !name ||
        document.body.classList.contains("bulk-mode") ||
        e.ctrlKey ||
        e.metaKey ||
        e.shiftKey
      )
        return;
      e.preventDefault();
      e.stopImmediatePropagation();
      clearTimeout(nameClick);
      const id = name.closest("[data-asset]").dataset.asset;
      if (e.detail < 2) nameClick = setTimeout(() => ctx.openDetail(id), 500);
    },
    true,
  );
  document.addEventListener("dblclick", (e) => {
    const name = e.target.closest(
      "#asset-grid .card-info h3,#detail .detail-body h2",
    );
    if (!name || document.body.classList.contains("bulk-mode")) return;
    e.preventDefault();
    e.stopPropagation();
    clearTimeout(nameClick);
    window.getSelection()?.removeAllRanges();
    editMaterialNameInPlace(
      name,
      name.closest("[data-asset]")?.dataset.asset || ctx.selected,
    );
  });
})();
