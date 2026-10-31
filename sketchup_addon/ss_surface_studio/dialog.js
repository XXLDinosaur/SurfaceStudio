(() => {
  const row = document.querySelector(".detail-actions");
  if (!row || row.querySelector(".ss-su-apply")) return;
  const id = row.querySelector("[data-favorite]")?.dataset.favorite;
  if (!id) return;
  const button = document.createElement("button");
  button.className = "primary-button ss-su-apply";
  button.textContent = "赋予到 SketchUp";
  button.onclick = () => window.sketchup.ss_apply(id);
  const panel = document.querySelector("#blender-panel");
  if (panel) panel.style.display = 'none';
  row.appendChild(button);
})();

