import { app as ctx } from "./modules/runtime.js";
/* Installed-version notes are bundled and available without network access. */
(() => {
  let attempted = false;
  window.openReleaseNotes = (back = null) => {
    const notes = ctx.library?.releaseNotes;
    if (!notes) return;
    ctx.modal(
      `SS ${notes.version} 更新说明`,
      `<p class="modal-description">${ctx.esc(notes.title)}<br>${ctx.esc(notes.channel)}</p>${notes.sections.map((section) => `<section class="release-section"><h3>${ctx.esc(section.title)}</h3><ul>${section.items.map((item) => `<li>${ctx.esc(item)}</li>`).join("")}</ul></section>`).join("")}<div class="modal-actions"><button class="primary-button" id="notes-done">${back ? "返回材质库设置" : "开始使用"}</button></div>`,
      "本版本更新",
      "680px",
    );
    const dialog = ctx.$("#modal");
    const acknowledge = () => {
      ctx
        .post("/api/release-notes/seen", { version: notes.version })
        .then(() => {
          ctx.library.releaseNotesSeen = true;
        })
        .catch(() => ctx.toast("阅读记录未能保存，下次启动会再次显示"));
      if (back) back();
    };
    dialog.addEventListener("close", acknowledge, { once: true });
    ctx.$("#notes-done").onclick = () => dialog.close();
  };
  const show = () => {
    if (attempted || !ctx.library?.releaseNotes || ctx.library.releaseNotesSeen)
      return;
    if (ctx.$("#modal").open) return;
    attempted = true;
    window.openReleaseNotes();
  };
  document.addEventListener("library-loaded", show);
  ctx.$("#modal").addEventListener("close", () => setTimeout(show, 0));
  show();
})();
