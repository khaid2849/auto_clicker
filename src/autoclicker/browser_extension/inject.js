// Các hàm ở đây được chrome.scripting.executeScript CHÉP NGUYÊN VĂN vào trang web,
// nên mỗi hàm phải tự đủ: không dùng biến, hàm hay import nào bên ngoài thân hàm.

/**
 * Click vào mục tiêu bằng chuỗi sự kiện chuột giống người dùng thật
 * (pointerdown → mousedown → pointerup → mouseup → click).
 * target: { mode: "element", selector } | { mode: "point", x, y }  (x, y theo khung nhìn)
 */
export function performClick(target, button = "left", clicks = 1) {
  let el = null;
  let x = 0;
  let y = 0;
  if (target.mode === "point") {
    x = target.x;
    y = target.y;
    el = document.elementFromPoint(x, y);
  } else {
    try {
      el = document.querySelector(target.selector);
    } catch {
      el = null;
    }
    if (el) {
      let r = el.getBoundingClientRect();
      const visible = r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth;
      if (!visible) {
        el.scrollIntoView({ block: "center", inline: "center" });
        r = el.getBoundingClientRect();
      }
      x = r.left + r.width / 2;
      y = r.top + r.height / 2;
    }
  }
  if (!el) return { ok: false, error: "not_found" };

  const code = { left: 0, middle: 1, right: 2 }[button] ?? 0;
  const pressed = [1, 4, 2][code];
  const common = {
    bubbles: true, cancelable: true, composed: true, view: window, button: code,
    clientX: x, clientY: y, screenX: x + (window.screenX || 0), screenY: y + (window.screenY || 0),
  };
  const pointer = { pointerId: 1, pointerType: "mouse", isPrimary: true };
  const send = (Type, type, extra) => el.dispatchEvent(new Type(type, { ...common, ...extra }));

  send(PointerEvent, "pointerover", { ...pointer, buttons: 0 });
  send(MouseEvent, "mouseover", { buttons: 0 });
  for (let i = 1; i <= clicks; i++) {
    send(PointerEvent, "pointerdown", { ...pointer, buttons: pressed, detail: i });
    send(MouseEvent, "mousedown", { buttons: pressed, detail: i });
    if (code === 0 && i === 1 && typeof el.focus === "function") el.focus({ preventScroll: true });
    send(PointerEvent, "pointerup", { ...pointer, buttons: 0, detail: i });
    send(MouseEvent, "mouseup", { buttons: 0, detail: i });
    send(MouseEvent, code === 0 ? "click" : code === 1 ? "auxclick" : "contextmenu", { buttons: 0, detail: i });
  }
  if (code === 0 && clicks === 2) send(MouseEvent, "dblclick", { buttons: 0, detail: 2 });
  return { ok: true };
}

/**
 * Chế độ chọn mục tiêu: tô sáng phần tử dưới chuột, hiện CSS selector + tọa độ; click để chọn, Esc để hủy.
 * Kết quả gửi về service worker: { type: "picked", target: { selector, x, y, label } }.
 */
export function startPicker(strings) {
  if (window.__autoClickerPicking) return;
  window.__autoClickerPicking = true;

  const esc = (s) => CSS.escape(s);
  const isUnique = (el, sel) => {
    try {
      const found = document.querySelectorAll(sel);
      return found.length === 1 && found[0] === el;
    } catch {
      return false;
    }
  };

  // CSS selector ngắn nhất mà vẫn trỏ đúng một phần tử; ưu tiên id / thuộc tính ổn định
  function cssPath(el) {
    if (el.id && isUnique(el, `#${esc(el.id)}`)) return `#${esc(el.id)}`;
    for (const attr of ["data-testid", "data-test", "data-qa", "name", "aria-label", "title"]) {
      const v = el.getAttribute(attr);
      const sel = v && `${el.localName}[${attr}="${esc(v)}"]`;
      if (sel && isUnique(el, sel)) return sel;
    }
    const parts = [];
    for (let node = el; node && node.nodeType === 1 && node !== document.documentElement; node = node.parentElement) {
      let part = node.localName;
      const classes = [...node.classList].filter((c) => /^[a-zA-Z][\w-]{1,30}$/.test(c) && !/\d{3,}/.test(c));
      if (classes.length) part += "." + classes.slice(0, 2).map(esc).join(".");
      const parent = node.parentElement;
      if (parent) {
        const same = [...parent.children].filter((c) => c.localName === node.localName);
        if (same.length > 1) part += `:nth-of-type(${same.indexOf(node) + 1})`;
      }
      parts.unshift(part);
      const sel = parts.join(" > ");
      if (isUnique(el, sel)) return sel;
      if (parent && parent.id) {
        const anchored = `#${esc(parent.id)} > ${sel}`;
        if (isUnique(el, anchored)) return anchored;
      }
    }
    return parts.join(" > ");
  }

  function describe(el) {
    const text = (el.getAttribute("aria-label") || el.innerText || el.value || el.title || el.alt || "")
      .toString().trim().replace(/\s+/g, " ");
    return `<${el.localName}>${text ? ` “${text.slice(0, 40)}${text.length > 40 ? "…" : ""}”` : ""}`;
  }

  // Giao diện chọn nằm trong shadow DOM để CSS của trang không ảnh hưởng
  const host = document.createElement("div");
  host.style.cssText = "all: initial; position: fixed; inset: 0; z-index: 2147483647; pointer-events: none;";
  const root = host.attachShadow({ mode: "closed" });
  root.innerHTML = `<style>
    .box { position: fixed; border: 2px solid #ff453a; background: rgba(255,69,58,.12); border-radius: 4px; }
    .tip { position: fixed; max-width: 60vw; padding: 4px 8px; border-radius: 6px; background: rgba(20,20,20,.92);
           color: #fff; font: 12px/1.4 ui-monospace, Menlo, Consolas, monospace; white-space: nowrap;
           overflow: hidden; text-overflow: ellipsis; }
    .bar { position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%); padding: 10px 18px;
           border-radius: 10px; background: rgba(0,0,0,.82); color: #fff; font: 600 14px/1.4 system-ui, sans-serif; }
  </style><div class="box" hidden></div><div class="tip" hidden></div><div class="bar"></div>`;
  const box = root.querySelector(".box");
  const tip = root.querySelector(".tip");
  root.querySelector(".bar").textContent = strings.hint;
  document.documentElement.appendChild(host);

  let current = null;
  const block = (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
  };

  function onMove(e) {
    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el || el === host) return;
    current = el;
    const r = el.getBoundingClientRect();
    Object.assign(box.style, { left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${r.height}px` });
    box.hidden = false;
    tip.textContent = `${cssPath(el)}   ·   X ${e.clientX}  Y ${e.clientY}`;
    tip.hidden = false;
    const left = e.clientX + 14 + tip.offsetWidth > innerWidth ? e.clientX - 14 - tip.offsetWidth : e.clientX + 14;
    const top = e.clientY + 18 + tip.offsetHeight > innerHeight ? e.clientY - 18 - tip.offsetHeight : e.clientY + 18;
    Object.assign(tip.style, { left: `${Math.max(4, left)}px`, top: `${Math.max(4, top)}px` });
  }

  function onClick(e) {
    block(e);
    const el = current || document.elementFromPoint(e.clientX, e.clientY);
    cleanup();
    if (!el) return;
    const target = { selector: cssPath(el), x: Math.round(e.clientX), y: Math.round(e.clientY), label: describe(el) };
    chrome.runtime.sendMessage({ type: "picked", target });
    toast(strings.done);
  }

  function onKey(e) {
    if (e.key === "Escape") {
      block(e);
      cleanup();
    }
  }

  const blocked = ["pointerdown", "pointerup", "mousedown", "mouseup", "dblclick", "auxclick"];
  function cleanup() {
    window.removeEventListener("mousemove", onMove, true);
    window.removeEventListener("click", onClick, true);
    window.removeEventListener("keydown", onKey, true);
    window.removeEventListener("contextmenu", onCancel, true);
    blocked.forEach((t) => window.removeEventListener(t, block, true));
    host.remove();
    window.__autoClickerPicking = false;
  }
  function onCancel(e) {
    block(e);
    cleanup();
  }

  function toast(text) {
    const t = document.createElement("div");
    t.textContent = text;
    t.style.cssText = "all: initial; position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%);" +
      "z-index: 2147483647; padding: 10px 18px; border-radius: 10px; background: #16a34a; color: #fff;" +
      "font: 600 14px/1.4 system-ui, sans-serif; box-shadow: 0 4px 16px rgba(0,0,0,.25);";
    document.documentElement.appendChild(t);
    setTimeout(() => t.remove(), 3500);
  }

  window.addEventListener("mousemove", onMove, true);
  window.addEventListener("click", onClick, true);
  window.addEventListener("keydown", onKey, true);
  window.addEventListener("contextmenu", onCancel, true);
  blocked.forEach((t) => window.addEventListener(t, block, true));
}
