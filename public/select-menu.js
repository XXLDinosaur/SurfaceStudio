import { app as ctx } from "./modules/runtime.js";
/* Keep native select values/events; replace only the platform popup. */
(() => {
  let owner = null,
    panel = null,
    options = [],
    active = 0,
    prefix = "",
    timer;
  function close(restore = false) {
    const previous = owner;
    if (panel) {
      panel.hidePopover();
      panel.remove();
    }
    panel = null;
    owner = null;
    prefix = "";
    clearTimeout(timer);
    previous?.setAttribute("aria-expanded", "false");
    if (restore && previous?.isConnected)
      previous.focus({ preventScroll: true });
  }
  function focusOption(index) {
    active = (index + options.length) % options.length;
    const buttons = [...panel.querySelectorAll('[role="option"]')];
    buttons.forEach((b, i) => (b.tabIndex = i === active ? 0 : -1));
    buttons[active]?.focus({ preventScroll: true });
    buttons[active]?.scrollIntoView({ block: "nearest" });
  }
  function choose(index) {
    const target = owner,
      value = options[index].value;
    close(true);
    if (target.value !== value) {
      target.value = value;
      target.dispatchEvent(new Event("input", { bubbles: true }));
      target.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }
  function open(select) {
    if (select.disabled) return;
    if (owner === select) {
      close(true);
      return;
    }
    close();
    owner = select;
    options = [...select.options].filter(
      (o) => !o.hidden && !o.disabled && !o.parentElement.disabled,
    );
    if (!options.length) {
      close();
      return;
    }
    panel = document.createElement("div");
    panel.className = "glass-select-menu";
    panel.setAttribute("popover", "manual");
    panel.setAttribute("role", "listbox");
    panel.setAttribute(
      "aria-label",
      select.getAttribute("aria-label") ||
        select.labels?.[0]?.textContent ||
        "选择选项",
    );
    options.forEach((o, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "option");
      b.setAttribute("aria-selected", String(o.value === select.value));
      b.textContent = o.textContent;
      b.onclick = () => choose(i);
      panel.append(b);
    });
    (select.closest("dialog") || document.body).append(panel);
    panel.showPopover();
    select.setAttribute("aria-expanded", "true");
    const rect = select.getBoundingClientRect();
    panel.style.width =
      Math.min(Math.max(rect.width, 190), innerWidth - 16) + "px";
    panel.style.maxHeight =
      Math.max(
        80,
        Math.min(320, Math.max(innerHeight - rect.bottom - 16, rect.top - 16)),
      ) + "px";
    const height = panel.getBoundingClientRect().height;
    panel.style.left =
      Math.max(8, Math.min(rect.left, innerWidth - panel.offsetWidth - 8)) +
      "px";
    panel.style.top =
      (rect.bottom + 8 + height <= innerHeight
        ? rect.bottom + 8
        : Math.max(8, rect.top - height - 8)) + "px";
    focusOption(
      Math.max(
        0,
        options.findIndex((o) => o.value === select.value),
      ),
    );
  }
  document.addEventListener(
    "mousedown",
    (e) => {
      const s = e.target.closest("select");
      if (s && !s.multiple) {
        e.preventDefault();
        open(s);
      } else if (panel && !panel.contains(e.target)) close();
    },
    true,
  );
  document.addEventListener(
    "keydown",
    (e) => {
      if (!panel) {
        if (
          e.target.matches("select") &&
          !e.target.multiple &&
          ["ArrowDown", "ArrowUp", "Enter", " ", "Home", "End"].includes(e.key)
        ) {
          e.preventDefault();
          e.stopImmediatePropagation();
          open(e.target);
        }
        return;
      }
      if (e.key === "Tab") {
        close(true);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopImmediatePropagation();
        close(true);
        return;
      }
      if (
        ["ArrowDown", "ArrowUp", "Home", "End", "Enter", " "].includes(e.key)
      ) {
        e.preventDefault();
        e.stopImmediatePropagation();
        if (e.key === "Enter" || e.key === " ") choose(active);
        else
          focusOption(
            e.key === "Home"
              ? 0
              : e.key === "End"
                ? options.length - 1
                : active + (e.key === "ArrowDown" ? 1 : -1),
          );
      } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
        e.stopImmediatePropagation();
        prefix += e.key.toLowerCase();
        clearTimeout(timer);
        timer = setTimeout(() => (prefix = ""), 700);
        const i = options.findIndex((o) =>
          o.textContent.trim().toLowerCase().startsWith(prefix),
        );
        if (i >= 0) focusOption(i);
      }
    },
    true,
  );
  document.addEventListener(
    "scroll",
    (e) => {
      if (panel && !panel.contains(e.target)) close();
    },
    true,
  );
  window.addEventListener("resize", () => close());
  window.addEventListener("blur", () => close());
  document.addEventListener("close", () => close(), true);
})();
