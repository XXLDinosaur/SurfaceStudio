// Preserve dependency order while loading explicit ES modules.
await import("./glass.js");
await import("./app.js");
await import("./blender.js");
await import("./material-names.js");
await import("./context-menu.js");
await import("./readability.js");
await import("./workbench.js");
await import("./window-chrome.js");
await import("./material-drag.js");
await import("./categories.js");
await import("./select-menu.js");
await import("./organizer.js");
await import("./updates.js");
await import("./release-notes.js");
document.documentElement.dataset.appReady = "true";
