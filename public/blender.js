import { app as ctx } from "./modules/runtime.js";

// Refresh the library when a host adds a material to SS.
let timer;
let stopped = false;
async function pollLibrary() {
  try {
    const response = await fetch("/api/blender/status");
    if (response.ok) {
      const { scannedAt } = await response.json();
      if (ctx.library && scannedAt && scannedAt !== ctx.library.scannedAt)
        await ctx.load();
    }
  } catch {
    // Retry when the local service is available.
  } finally {
    if (!stopped) timer = setTimeout(pollLibrary, document.hidden ? 2500 : 1000);
  }
}
window.addEventListener("beforeunload", () => {
  stopped = true;
  clearTimeout(timer);
});
pollLibrary();
