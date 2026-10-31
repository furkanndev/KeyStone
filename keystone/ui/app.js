/* KeyStone interface. Plain JS, no build step.
   Talks to the Python core through pywebview (native window) or HTTP+SSE (browser mode). */
(function () {
  "use strict";

  // ------------------------------------------------------------------ transport
  const hashToken = (location.hash.match(/token=([^&]+)/) || [])[1];
  let token = hashToken || sessionStorageGet("ks_token");
  if (hashToken) { sessionStorageSet("ks_token", hashToken); history.replaceState(null, "", location.pathname); }

  function sessionStorageGet(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
  function sessionStorageSet(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* ignore */ } }
  function localGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function localSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } }

  const native = () => window.pywebview && window.pywebview.api && window.pywebview.api.call;

  async function api(name, ...args) {
    if (native()) return window.pywebview.api.call(name, args);
    const r = await fetch("/api/" + name, {
      method: "POST", headers: { "Content-Type": "application/json", "X-KeyStone-Token": token || "" },
      body: JSON.stringify({ args }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || r.statusText);
    return j.result;
  }

  window.KS = { emit: (ev) => onEvent(ev) };

  function connectEvents() {
    if (native()) return;               // native host pushes through window.KS.emit
    const es = new EventSource("/events?token=" + encodeURIComponent(token || ""));
    es.onmessage = (m) => { try { onEvent(JSON.parse(m.data)); } catch (e) { /* ignore */ } };
    es.onerror = () => { es.close(); setTimeout(connectEvents, 2000); };
  }

  // ------------------------------------------------------------------ state
  const S = {
    boot: null, view: localGet("ks_view") || "apps", lang: "tr",
    catalog: [], scanning: false, tweaks: null, tweakBusy: {}, backupItems: null, backups: [],
    jobs: {}, jobOrder: [], logs: {}, dockJob: null, dockOpen: false,
    f: { q: "", cat: "all", show: "all", other: false },
    bmode: "backup", bform: { folder: "", encrypt: true, pw: "", pw2: "" },
    restore: { path: "", pw: "", plan: null, error: "", loading: false },
  };
  const OS_LABEL = { windows: "Windows", macos: "macOS", linux: "Linux" };
  const OS_SHORT = { windows: "W", macos: "M", linux: "L" };
  const STYLES = ["calm", "console", "bold", "apple"];
  const ACCENTS = { calm: "#2557D6", console: "#B8F25B", bold: "#5B36F5", apple: "#007AFF" };
  const SWATCHES = ["", "#2557D6", "#0F7B6C", "#B4441A", "#7C3AED", "#D6336C", "#B8F25B", "#007AFF"];

  const $ = (sel, root = document) => root.querySelector(sel);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  function t(key, vars) {
    const d = window.I18N[S.lang] || window.I18N.tr;
    let s = d[key] != null ? d[key] : (window.I18N.en[key] != null ? window.I18N.en[key] : key);
    if (vars) for (const k in vars) s = s.split("{" + k + "}").join(vars[k]);
    return s;
  }
  const L = (obj) => (obj && (obj[S.lang] || obj.en || obj.tr)) || "";
  const profile = () => S.boot.profiles.find((p) => p.id === S.boot.active) || S.boot.profiles[0];
  const fmtSize = (n) => n == null ? "—" : n < 1024 ? n + " B" : n < 1048576 ? (n / 1024).toFixed(0) + " KB" : n < 1073741824 ? (n / 1048576).toFixed(1) + " MB" : (n / 1073741824).toFixed(2) + " GB";
  const fmtDate = (s) => { try { return new Date(typeof s === "number" ? s * 1000 : s).toLocaleString(S.lang === "tr" ? "tr-TR" : "en-GB", { dateStyle: "medium", timeStyle: "short" }); } catch (e) { return s; } };
  const mono = (name) => { const w = name.replace(/[^\p{L}\p{N} ]/gu, "").split(/\s+/).filter(Boolean); return ((w[0] || "?")[0] + (w[1] ? w[1][0] : (w[0] || "?")[1] || "")).toUpperCase(); };
  const hue = (id) => { let h = 0; for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0; return "c" + (h % 4); };

  // ------------------------------------------------------------------ icons
  const IC = {
    apps: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    tweaks: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    backup: '<rect x="3" y="4" width="18" height="5" rx="1.5"/><path d="M5 9v9a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9M10 13h4"/>',
    profiles: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    check: '<path d="M5 12l5 5 9-10"/>', shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    up: '<path d="M6 15l6-6 6 6"/>', down: '<path d="M6 9l6 6 6-6"/>', x: '<path d="M6 6l12 12M18 6 6 18"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  };
  const icon = (n, cls = "i") => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${IC[n] || ""}</svg>`;

  // ------------------------------------------------------------------ appearance
  function applyAppearance() {
    const s = S.boot.settings;
    const style = STYLES.includes(s.style) ? s.style : "calm";
    let theme = s.theme || "system";
    if (theme === "system") theme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    const root = document.documentElement;
    root.dataset.style = style;
    root.dataset.theme = theme;
    root.lang = S.lang;
    const acc = s.accent || ACCENTS[style];
    root.style.setProperty("--accent", acc);
    root.style.setProperty("--accent-ink", contrastInk(acc));
  }
  function contrastInk(hex) {
    const m = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(hex || "");
    if (!m) return "#fff";
    const [r, g, b] = [m[1], m[2], m[3]].map((x) => { const v = parseInt(x, 16) / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.4 ? "#0E100F" : "#FFFFFF";
  }
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => S.boot && applyAppearance());

  // ------------------------------------------------------------------ boot
  async function boot() {
    if (S.booting) return;
    S.booting = true;
    try {
      S.boot = await api("bootstrap");
    } catch (e) {
      $("#main").innerHTML = `<div class="page"><div class="empty">KeyStone: ${esc(e.message)}</div></div>`;
      return;
    }
    S.lang = S.boot.settings.lang || "tr";
    S.bform.folder = S.boot.backup_dir;
    applyAppearance();
    connectEvents();
    renderShell();
    $("#app").setAttribute("aria-busy", "false");
    loadCatalog();
    api("job_list").then((list) => { list.forEach((j) => upsertJob(j)); renderDock(); });
  }

  async function loadCatalog() {
    const r = await api("get_catalog");
    S.catalog = r.packages;
    S.scanning = r.scanning;
    if (S.view === "apps") renderView(); else renderNav();
  }

  // ------------------------------------------------------------------ events
  function onEvent(ev) {
    if (ev.type === "job") {
      const prev = S.jobs[ev.job.id];
      upsertJob(ev.job);
      if (ev.job.state === "running" && (!S.dockJob || (S.jobs[S.dockJob] && !["running", "queued"].includes(S.jobs[S.dockJob].state)))) S.dockJob = ev.job.id;
      if (!prev) { S.dockJob = S.dockJob || ev.job.id; }
      const fin = ["done", "failed", "cancelled"].includes(ev.job.state);
      if (fin && prev && !["done", "failed", "cancelled"].includes(prev.state)) {
        toast(t(ev.job.state === "done" ? "toast_job_done" : "toast_job_failed", { t: jobTitle(ev.job) }), ev.job.state !== "done");
        if (ev.job.kind === "backup") refreshBackups();
      }
      renderDock();
      if (S.view === "apps" && ev.job.kind === "install") renderList();
      if (S.view === "backup" && ["backup", "restore"].includes(ev.job.kind)) renderView();
    } else if (ev.type === "log") {
      (S.logs[ev.job] = S.logs[ev.job] || []).push(ev.line);
      if (S.logs[ev.job].length > 3000) S.logs[ev.job].splice(0, 500);
      if (ev.job === S.dockJob) appendLog(ev.line);
    } else if (ev.type === "catalog") {
      loadCatalog();
    } else if (ev.type === "tweaks") {
      S.tweakBusy = {};
      if (S.view === "tweaks") loadTweaks();
    }
  }
  function upsertJob(j) {
    if (!S.jobs[j.id]) S.jobOrder.push(j.id);
    S.jobs[j.id] = j;
  }
  const jobTitle = (j) => t("job_" + (j.kind === "install" ? j.title : j.kind));

  // ------------------------------------------------------------------ shell
  function renderShell() { renderNav(); renderSys(); renderView(); renderDock(); }

  function renderNav() {
    const p = profile();
    const avail = S.catalog.filter((x) => x.status === "available" || x.status === "installed").length;
    const items = [["apps", avail || ""], ["tweaks", ""], ["backup", ""], ["profiles", S.boot.profiles.length], ["settings", ""]];
    $("#nav").innerHTML = items.map(([id, n]) =>
      `<button class="nav-link" data-nav="${id}" ${S.view === id ? 'aria-current="page"' : ""}>` +
      `<span class="ico">${icon(id)}</span><span>${t("nav_" + id)}</span>${n !== "" ? `<span class="count">${n}</span>` : ""}</button>`).join("");
    void p;
  }

  function renderSys() {
    const s = S.boot.system;
    const mg = S.boot.managers.filter((m) => m.available).map((m) => m.label).join(" + ") || "—";
    $("#syscard").innerHTML =
      `<span class="label">${t("this_system")}</span><span class="os">${esc(s.os_name)}</span>` +
      `<span class="mono muted sub">${esc(mg)} · ${esc(s.arch)}</span>` +
      `<span class="${s.is_admin ? "ok" : "muted"} sub" style="font-size:12px;display:flex;gap:6px;align-items:center">${s.is_admin ? icon("check", "i") : ""}${t(s.is_admin ? "admin_yes" : "admin_no")}</span>` +
      (S.boot.can_elevate ? `<button class="btn small" data-act="elevate">${icon("shield")}${t("run_admin")}</button>` : "");
  }

  function go(view) {
    S.view = view;
    localSet("ks_view", view);
    renderNav();
    renderView();
    $("#main").scrollTop = 0;
  }

  function renderView() {
    renderNav();
    const v = { apps: viewApps, tweaks: viewTweaks, backup: viewBackup, profiles: viewProfiles, settings: viewSettings }[S.view] || viewApps;
    v();
  }

  // ================================================================== APPS
  function visibleApps() {
    const f = S.f, q = f.q.trim().toLowerCase(), sel = new Set(profile().apps);
    return S.catalog.filter((p) => {
      const here = p.status === "installed" || p.status === "available";
      if (!f.other && !here && p.status !== "needs_manager") return false;
      if (f.cat !== "all" && p.category !== f.cat) return false;
      if (f.show === "installed" && p.status !== "installed") return false;
      if (f.show === "selected" && !sel.has(p.id)) return false;
      if (q && !(p.name + " " + p.name_tr + " " + L(p.desc) + " " + p.id + " " + p.sources.map((s) => s.id).join(" ")).toLowerCase().includes(q)) return false;
      return true;
    });
  }

  function viewApps() {
    const here = S.catalog.filter((p) => p.status === "installed" || p.status === "available");
    const inst = here.filter((p) => p.status === "installed").length;
    const cats = S.boot.categories.filter((c) => S.catalog.some((p) => p.category === c && (S.f.other || p.status !== "unsupported")));
    const bold = document.documentElement.dataset.style === "bold";
    const catCounts = (c) => S.catalog.filter((p) => p.category === c && p.status !== "unsupported").length;
    $("#main").innerHTML = `<div class="page">
      <div class="page-head">
        <div><h1>${t("apps_title")}</h1><p>${S.scanning ? t("scanning") : t("apps_sub", { n: here.length, i: inst })}</p></div>
        <label class="search">${icon("search")}<span class="sr">${t("search")}</span><input id="q" type="search" placeholder="${t("search")}" value="${esc(S.f.q)}" autocomplete="off"><kbd>Ctrl K</kbd></label>
      </div>
      <div class="toolbar">
        <span class="label-sm">${t("presets")}</span>
        ${S.boot.presets.map((p) => `<button class="chip" data-preset="${p}">${t("preset_" + p)}</button>`).join("")}
        <span class="grow"></span>
        <span class="seg" role="group">${["all", "installed", "selected"].map((k) => `<button data-show="${k}" aria-pressed="${S.f.show === k}">${t(k === "all" ? "all" : k + "_f")}</button>`).join("")}</span>
      </div>
      ${bold ? `<div class="catgrid">${["all", ...cats].map((c) => `<button data-cat="${c}" aria-pressed="${S.f.cat === c}"><b>${c === "all" ? here.length : catCounts(c)}</b>${c === "all" ? t("all") : t("cat_" + c)}</button>`).join("")}</div>`
        : `<div class="toolbar"><span class="seg" role="group">${["all", ...cats].map((c) => `<button data-cat="${c}" aria-pressed="${S.f.cat === c}">${c === "all" ? t("all") : t("cat_" + c)}</button>`).join("")}</span>
          <span class="grow"></span><label class="check label-sm" style="align-items:center"><input type="checkbox" class="sel" data-other ${S.f.other ? "checked" : ""}>${t("show_all_os")}</label></div>`}
      <section class="panel" aria-label="${t("apps_title")}"><div class="list apps" id="applist"></div></section>
      <div class="actionbar" id="actionbar"></div>
    </div>`;
    renderList();
    const q = $("#q");
    q.addEventListener("input", () => { S.f.q = q.value; renderList(); });
  }

  function statusPill(p, job) {
    if (job) return `<span class="pill accent">${t(job === "running" ? "st_running" : "st_queued")}</span>`;
    if (p.status === "installed") return `<span class="pill ok">${t("st_installed")}</span>`;
    if (p.status === "available") return `<span class="pill">${t("st_available")}</span>`;
    if (p.status === "needs_manager") return `<span class="pill warn">${t("st_needs_manager", { m: p.missing_managers.join("/") })}</span>`;
    return `<span class="pill">${t("st_unsupported")}</span>`;
  }

  function activeInstallStates() {
    const m = {};
    for (const id of S.jobOrder) {
      const j = S.jobs[id];
      if (j.kind !== "install" || !["running", "queued"].includes(j.state)) continue;
      for (const it of j.items) if (it.state === "running" || it.state === "queued") m[it.id] = it.state;
    }
    return m;
  }

  function renderList() {
    const box = $("#applist");
    if (!box) return;
    const list = visibleApps(), sel = new Set(profile().apps), js = activeInstallStates(), os = S.boot.system.os;
    box.innerHTML = list.length ? list.map((p) => {
      const usable = p.status === "available" || p.status === "installed";
      const desc = L(p.desc) + (!usable && p.alt ? " · " + t("alt_hint", { a: (S.catalog.find((x) => x.id === p.alt) || {}).name || p.alt }) : "");
      return `<div class="row ${usable ? "" : "dim"} ${sel.has(p.id) ? "on" : ""}" data-pkg="${p.id}">
        <input type="checkbox" class="sel" aria-label="${esc(p.name)}" ${sel.has(p.id) ? "checked" : ""} ${usable ? "" : "disabled"}>
        ${p.icon ? `<img class="mono-tile app-icon" src="assets/apps/${p.id}.png" alt="" loading="lazy">` : `<span class="mono-tile ${hue(p.id)}">${esc(mono(p.name))}</span>`}
        <span class="body"><span class="title">${esc(S.lang === "tr" ? p.name_tr : p.name)}</span><span class="desc">${esc(desc)}</span></span>
        <span class="src mono">${p.sources[0] ? esc(p.sources[0].label) : ""}</span>
        <span class="plat" aria-label="${t("platforms")}">${["windows", "macos", "linux"].map((o) => `<span class="${p.platforms.includes(o) ? "on" : ""} ${o === os ? "here" : ""}" title="${OS_LABEL[o]}">${OS_SHORT[o]}</span>`).join("")}</span>
        ${statusPill(p, js[p.id])}
        <button class="info" data-detail="${p.id}" aria-label="${t("sources")}">${icon("info")}</button>
      </div>`;
    }).join("") : `<div class="empty">${S.scanning && !S.catalog.length ? '<div class="skeleton"></div>' : t("no_results")}</div>`;
    renderActionbar();
  }

  function renderActionbar() {
    const bar = $("#actionbar");
    if (!bar) return;
    const ids = selectedUsable();
    const isWin = S.boot.system.os === "windows";
    bar.innerHTML = `<strong>${ids.length ? t("n_selected", { n: ids.length }) : t("none_selected")}</strong>
      <button class="btn ghost small" data-act="select-visible">${t("select_all")}</button>
      ${ids.length ? `<button class="btn ghost small" data-act="clear-apps">${t("clear")}</button>` : ""}
      <span class="grow"></span>
      <button class="btn" data-act="export-script" ${ids.length ? "" : "disabled"}>${t("export_script")}</button>
      ${isWin ? `<button class="btn" data-act="download" ${ids.length ? "" : "disabled"}>${t("download")}</button>` : ""}
      <button class="btn primary" data-act="install" ${ids.length ? "" : "disabled"}>${t("install")}</button>`;
  }

  function selectedUsable() {
    const ok = new Set(S.catalog.filter((p) => p.status === "available" || p.status === "installed").map((p) => p.id));
    return profile().apps.filter((id) => ok.has(id));
  }

  let saveTimer = null;
  function saveProfile(values) {
    Object.assign(profile(), values);
    clearTimeout(saveTimer);
    const pid = profile().id, snapshot = { ...values };
    saveTimer = setTimeout(() => api("profile_update", pid, snapshot).catch((e) => toast(e.message, true)), 300);
  }
  function toggleApp(id, on) {
    const set = new Set(profile().apps);
    on ? set.add(id) : set.delete(id);
    saveProfile({ apps: [...set] });
    renderList();
  }

  function showDetail(id) {
    const p = S.catalog.find((x) => x.id === id);
    if (!p) return;
    modal(`<h2>${esc(p.name)}</h2>
      <p style="margin:0">${esc(L(p.long))}</p>
      <div class="field"><span>${t("sources")}</span>${p.sources.length ? p.sources.map((s, i) => `<span class="mono">${i === 0 ? "● " : "○ "}${esc(s.label)}</span>`).join("") : `<span class="muted">${t("st_unsupported")}</span>`}</div>
      <div class="field"><span>${t("platforms")}</span><span>${p.platforms.map((o) => OS_LABEL[o]).join(" · ")}</span></div>
      <div class="actions">${p.website ? `<button class="btn" data-url="${esc(p.website)}">${t("website")}</button>` : ""}<button class="btn primary" data-close>${t("close")}</button></div>`);
  }

  async function exportScript() {
    const r = await api("export_script", selectedUsable());
    const name = "keystone-install" + r.ext;
    if (S.boot.native_dialogs) {
      const p = await api("save_text", name, r.text);
      if (p) toast(t("saved_to", { p }));
      return;
    }
    modal(`<h2>${t("export_script")}</h2><pre class="log" style="max-height:50vh;border-radius:8px">${esc(r.text)}</pre>
      <div class="actions"><button class="btn" data-act="copy-script">${t("copy")}</button><button class="btn primary" data-close>${t("close")}</button></div>`);
    $("[data-act=copy-script]").onclick = () => navigator.clipboard.writeText(r.text).then(() => toast(t("copied")));
  }

  // ================================================================== TWEAKS
  async function loadTweaks() {
    S.tweaks = await api("get_tweaks");
    if (S.view === "tweaks") viewTweaks();
  }

  function viewTweaks() {
    if (!S.tweaks) {
      $("#main").innerHTML = `<div class="page"><div class="page-head"><div><h1>${t("tweaks_title")}</h1></div></div>${'<div class="skeleton"></div>'.repeat(4)}</div>`;
      loadTweaks();
      return;
    }
    const cats = S.boot.tweak_categories.filter((c) => S.tweaks.some((x) => x.category === c));
    $("#main").innerHTML = `<div class="page">
      <div class="page-head"><div><h1>${t("tweaks_title")}</h1><p>${t("tweaks_sub", { n: S.tweaks.length, os: OS_LABEL[S.boot.system.os] })}</p></div></div>
      ${cats.map((c) => `<section aria-label="${t("tcat_" + c)}"><h2 class="group-title">${t("tcat_" + c)}</h2><div class="panel"><div class="list">
        ${S.tweaks.filter((x) => x.category === c).map(tweakRow).join("")}</div></div></section>`).join("")}
    </div>`;
  }

  function tweakRow(x) {
    const busy = S.tweakBusy[x.id];
    const tags = [x.admin ? `<span class="tag">${t("admin_needed")}</span>` : "", x.risk === "high" ? `<span class="tag warn">${t("risky")}</span>` : "",
      x.restart ? `<span class="tag">${t("restart_note", { x: x.restart })}</span>` : ""].join("");
    let ctl;
    if (x.action) ctl = `<button class="btn small" data-tweak-run="${x.id}" ${busy ? "disabled" : ""}>${t("run")}</button>`;
    else if (x.state === null) ctl = `<span class="toolbar"><button class="btn small" data-tweak-do="${x.id}" data-a="revert">${t("revert")}</button><button class="btn small primary" data-tweak-do="${x.id}" data-a="apply">${t("apply")}</button></span>`;
    else ctl = `<input type="checkbox" class="sw" role="switch" data-tweak="${x.id}" aria-label="${esc(L(x.name))}" ${x.state ? "checked" : ""} ${busy ? 'disabled data-busy="true"' : ""}>`;
    return `<div class="row" style="cursor:default"><span class="body"><span class="title">${esc(L(x.name))} ${tags}</span>
      <span class="desc" style="white-space:normal">${esc(L(x.desc))}</span></span>${ctl}</div>`;
  }

  async function runTweak(id, action) {
    const x = S.tweaks.find((y) => y.id === id);
    if (action === "apply" && x && x.risk === "high" && !(await confirmBox(t("risky_confirm")))) { viewTweaks(); return; }
    S.tweakBusy[id] = true;
    if (x && !x.action && x.state !== null) x.state = action === "apply";
    viewTweaks();
    await api("tweaks_run", [id], action);
  }

  // ================================================================== BACKUP
  async function refreshBackups() {
    try { S.backups = await api("list_backups", S.bform.folder); } catch (e) { S.backups = []; }
    if (S.view === "backup") viewBackup();
  }

  function viewBackup() {
    if (!S.backupItems) {
      $("#main").innerHTML = `<div class="page"><div class="page-head"><div><h1>${t("backup_title")}</h1><p>${t("backup_sub")}</p></div></div>${'<div class="skeleton"></div>'.repeat(4)}</div>`;
      api("backup_items").then((r) => { S.backupItems = r; refreshBackups(); });
      return;
    }
    $("#main").innerHTML = `<div class="page">
      <div class="page-head"><div><h1>${t("backup_title")}</h1><p>${t("backup_sub")}</p></div>
        <span class="seg" role="group"><button data-bmode="backup" aria-pressed="${S.bmode === "backup"}">${t("mode_backup")}</button><button data-bmode="restore" aria-pressed="${S.bmode === "restore"}">${t("mode_restore")}</button></span></div>
      ${S.bmode === "backup" ? backupPane() : restorePane()}
    </div>`;
    bindBackupInputs();
  }

  const compatLabel = (r) => t(r === "any" ? "any_os" : r === "family" ? "same_family" : "same_os");

  function backupPane() {
    const sel = new Set(profile().backup.length ? profile().backup : S.backupItems.filter((i) => i.found).map((i) => i.id));
    const usable = S.backupItems.filter((i) => i.supported && i.found);
    const chosen = usable.filter((i) => sel.has(i.id));
    const size = chosen.reduce((a, i) => a + (i.found.size || 0), 0);
    const running = Object.values(S.jobs).some((j) => j.kind === "backup" && ["running", "queued"].includes(j.state));
    const pwBad = S.bform.encrypt && (S.bform.pw.length < 1 || S.bform.pw !== S.bform.pw2);
    return `<div class="split"><section class="primary cards" aria-label="${t("mode_backup")}">
      ${S.backupItems.map((i) => {
        const ok = i.supported && i.found, on = ok && sel.has(i.id);
        const detail = !i.supported ? t("not_on_os") : !i.found ? t("none_found") : [i.found.count != null ? i.found.count : "", i.found.detail || ""].filter(Boolean).join(" · ") || L(i.desc);
        return `<label class="card ${on ? "on" : ""} ${ok ? "" : "off"}" title="${esc(L(i.desc))}">
          <span class="head"><input type="checkbox" class="sel" data-bitem="${i.id}" ${on ? "checked" : ""} ${ok ? "" : "disabled"}><span class="name">${esc(L(i.name))}</span><span class="mono muted">${ok ? fmtSize(i.found.size) : ""}</span></span>
          <span class="detail">${esc(detail)}</span>
          <span class="tags"><span class="tag">${compatLabel(i.restore_on)}</span>${i.sensitive ? `<span class="tag warn">${t("sensitive")}</span>` : ""}</span></label>`;
      }).join("")}
    </section>
    <aside class="sidepanel" aria-label="${t("mode_backup")}">
      <div class="field"><span>${t("target_folder")}</span><span class="toolbar" style="flex-wrap:nowrap">
        <input class="input mono grow" id="bfolder" value="${esc(S.bform.folder)}" aria-label="${t("target_folder")}">
        ${S.boot.native_dialogs ? `<button class="btn small" data-act="pick-folder">${t("change")}</button>` : ""}</span></div>
      <hr>
      <div class="kv"><span class="muted">${t("selected_items")}</span><strong>${chosen.length} / ${usable.length}</strong></div>
      <div class="kv"><span class="muted">${t("est_size")}</span><strong>${fmtSize(size)}</strong></div>
      <div class="kv"><span class="muted">${t("format")}</span><span class="mono">.ksbak</span></div>
      <hr>
      <label class="check"><input type="checkbox" class="sw" id="benc" ${S.bform.encrypt ? "checked" : ""}><span><strong>${t("encrypt")}</strong><small>${t("encrypt_hint")}</small></span></label>
      ${S.bform.encrypt ? `<label class="field"><span>${t("password")}</span><input class="input" type="password" id="bpw" value="${esc(S.bform.pw)}" autocomplete="new-password"></label>
        <label class="field"><span>${t("password2")}</span><input class="input" type="password" id="bpw2" value="${esc(S.bform.pw2)}" autocomplete="new-password"></label>
        <small id="pwmis" style="color:var(--err)" ${S.bform.pw2 && S.bform.pw !== S.bform.pw2 ? "" : "hidden"}>${t("pw_mismatch")}</small>` : ""}
      <button class="btn primary" data-act="start-backup" data-chosen="${chosen.length}" data-running="${running}" ${!chosen.length || pwBad || running ? "disabled" : ""}>${running ? icon("backup", "i spin") : ""}${t("start_backup")}</button>
      <hr>
      <div class="field"><span>${t("recent")}</span>${S.backups.length ? S.backups.slice(0, 5).map((b) => `<div class="kv" style="font-size:13px">
        <button class="btn ghost small" style="padding:0;height:auto" data-open="${esc(b.path)}">${esc(b.host ? b.host.hostname + " · " + fmtDate(b.mtime) : b.name)}</button>
        <span class="muted">${b.encrypted ? icon("lock") : ""}${fmtSize(b.size)}</span></div>`).join("") : `<span class="muted" style="font-size:13px">${t("no_backups")}</span>`}</div>
    </aside></div>`;
  }

  function restorePane() {
    const R = S.restore, plan = R.plan;
    let body = "";
    if (plan) {
      const m = plan.manifest, src = m.host || {};
      body = `<div class="panel" style="padding:16px"><strong>${esc(t("restore_from", { h: src.hostname || "?", os: src.os_name || src.os, d: fmtDate(m.created) }))}</strong></div>
      <section class="cards">${plan.items.map((i) => `<label class="card ${i.compatible ? "on" : "off"}">
        <span class="head"><input type="checkbox" class="sel" data-ritem="${i.id}" ${i.compatible && !(R.skip || []).includes(i.id) ? "checked" : ""} ${i.compatible ? "" : "disabled"}>
        <span class="name">${esc(L(i.name))}</span></span>
        <span class="detail">${i.compatible ? t("compatible") : t("incompatible")}${i.backup && i.backup.count != null ? " · " + i.backup.count : ""}</span></label>`).join("")}</section>
      ${plan.apps.length ? `<section><h2 class="group-title">${t("apps_map")}</h2><div class="panel" style="overflow-x:auto"><table class="map">
        <thead><tr><th>${t("from_backup")} (${esc(OS_LABEL[src.os] || "")})</th><th></th><th>${t("on_this")} (${OS_LABEL[S.boot.system.os]})</th><th>${t("action")}</th></tr></thead>
        <tbody>${plan.apps.map((a) => { const nm = (id) => (S.catalog.find((x) => x.id === id) || { name: id }).name;
          return `<tr><td>${esc(nm(a.from))}</td><td class="muted">→</td><td>${a.to ? esc(nm(a.to)) : "—"}</td>
          <td><span class="pill ${a.action === "install" ? "ok" : a.action === "alternative" ? "warn" : ""}">${t("a_" + a.action)}</span></td></tr>`; }).join("")}</tbody></table></div></section>` : ""}
      <p class="muted" style="margin:0">${t("restore_note")}</p>
      <div class="toolbar"><span class="grow"></span><button class="btn primary" data-act="start-restore">${t("start_restore")}</button></div>`;
    }
    return `<div class="sidepanel">
      <div class="field"><span>${t("choose_backup")}</span><span class="toolbar" style="flex-wrap:nowrap">
        <input class="input mono grow" id="rpath" placeholder="${t("path_ph")}" value="${esc(R.path)}">
        ${S.boot.native_dialogs ? `<button class="btn small" data-act="pick-backup">${t("browse")}</button>` : ""}</span></div>
      ${S.backups.length ? `<div class="toolbar">${S.backups.slice(0, 6).map((b) => `<button class="chip" data-rpick="${esc(b.path)}" aria-pressed="${R.path === b.path}">${b.encrypted ? "🔒 " : ""}${esc(b.host ? b.host.hostname : b.name)} · ${esc(fmtDate(b.mtime))}</button>`).join("")}</div>` : ""}
      <div class="toolbar"><label class="field grow"><span>${t("password")}</span><input class="input" type="password" id="rpw" value="${esc(R.pw)}" autocomplete="current-password"></label>
        <button class="btn" data-act="analyze" style="align-self:flex-end" ${R.path ? "" : "disabled"}>${R.loading ? icon("backup", "i spin") : ""}${t("analyze")}</button></div>
      ${R.error ? `<small style="color:var(--err)">${esc(R.error === "password" ? t("wrong_pw") : R.error)}</small>` : ""}
    </div>${body}`;
  }

  function bindBackupInputs() {
    const on = (id, fn) => { const el = $("#" + id); if (el) el.addEventListener("input", fn); };
    on("bfolder", (e) => { S.bform.folder = e.target.value; });
    $("#bfolder") && $("#bfolder").addEventListener("change", refreshBackups);
    on("bpw", (e) => { S.bform.pw = e.target.value; });
    on("bpw2", (e) => { S.bform.pw2 = e.target.value; });
    on("rpath", (e) => { S.restore.path = e.target.value; S.restore.plan = null; });
    on("rpw", (e) => { S.restore.pw = e.target.value; });
  }

  async function analyze() {
    const R = S.restore;
    R.loading = true; R.error = ""; viewBackup();
    const r = await api("restore_plan", R.path, R.pw);
    R.loading = false;
    if (r.ok) { R.plan = r; R.skip = []; } else { R.plan = null; R.error = r.error; }
    viewBackup();
  }

  // ================================================================== PROFILES
  function viewProfiles() {
    $("#main").innerHTML = `<div class="page">
      <div class="page-head"><div><h1>${t("profiles_title")}</h1><p>${t("profiles_sub")}</p></div>
        <span class="toolbar">${S.boot.native_dialogs ? `<button class="btn" data-act="import-profile">${t("import")}</button>` : ""}<button class="btn primary" data-act="new-profile">${t("new_profile")}</button></span></div>
      <section class="cards">${S.boot.profiles.map((p) => {
        const act = p.id === S.boot.active;
        return `<div class="card ${act ? "on" : ""}" style="cursor:default">
          <span class="head"><span class="tile">${esc(mono(p.name))}</span><span class="name">${esc(p.name)}</span>${act ? `<span class="pill accent">${t("active")}</span>` : ""}</span>
          <span class="muted" style="font-size:13px">${t("p_counts", { a: p.apps.length, t: p.tweaks.length, b: p.backup.length })}</span>
          <span class="toolbar">${act ? "" : `<button class="btn small primary" data-pact="activate" data-pid="${p.id}">${t("activate")}</button>`}
            <button class="btn small" data-pact="rename" data-pid="${p.id}">${t("rename")}</button>
            <button class="btn small" data-pact="duplicate" data-pid="${p.id}">${t("duplicate")}</button>
            ${S.boot.native_dialogs ? `<button class="btn small" data-pact="export" data-pid="${p.id}">${t("export")}</button>` : ""}
            ${S.boot.profiles.length > 1 ? `<button class="btn small danger" data-pact="delete" data-pid="${p.id}">${t("del")}</button>` : ""}</span>
        </div>`;
      }).join("")}</section></div>`;
  }

  async function refreshBoot() {
    const b = await api("bootstrap");
    S.boot.profiles = b.profiles; S.boot.active = b.active; S.boot.settings = b.settings; S.boot.backup_dir = b.backup_dir;
  }

  async function profileAction(act, pid) {
    const p = S.boot.profiles.find((x) => x.id === pid);
    if (act === "activate") await api("profile_activate", pid);
    else if (act === "rename") { const n = await promptBox(t("rename"), p.name); if (!n) return; await api("profile_update", pid, { name: n }); }
    else if (act === "duplicate") await api("profile_create", p.name + " 2", pid);
    else if (act === "delete") { if (!(await confirmBox(t("del_confirm", { n: p.name })))) return; await api("profile_delete", pid); }
    else if (act === "export") { const r = await api("profile_export", pid); if (r) toast(t("saved_to", { p: r })); return; }
    await refreshBoot();
    renderView();
  }

  // ================================================================== SETTINGS
  function stylePreview(s) {
    const P = {
      calm: ["#F4F5F7", "#E3E5E9", "#FFFFFF", "#2557D6", "#C9CED6"],
      console: ["#0E100F", "#262A27", "#121513", "#B8F25B", "#3A403B"],
      bold: ["#F3F1FF", "#FFFFFF", "#FFFFFF", "#5B36F5", "#FFC93C"],
      apple: ["#E9E9EE", "#F2F2F7", "#FFFFFF", "#34C759", "#D1D1D6"],
    }[s];
    const radius = s === "console" ? "0" : s === "bold" ? "6px" : "3px";
    const row = (on) => `<span class="r"><i style="background:${P[4]}"></i>${s === "apple" ? `<i style="width:14px;height:8px;border-radius:4px;background:${on ? P[3] : P[4]}"></i>` : `<i style="width:8px;height:8px;border-radius:${radius};background:${on ? P[3] : "transparent"};border:1px solid ${P[4]}"></i>`}</span>`;
    return `<span class="pv" style="background:${P[0]}"><span class="s" style="background:${s === "bold" ? P[0] : P[1]}"><i style="background:${P[3]};width:70%"></i><i style="background:${P[4]}"></i><i style="background:${P[4]}"></i></span>
      <span class="m" style="background:${P[0]}"><span style="background:${P[2]};border-radius:${radius};padding:5px;display:flex;flex-direction:column;gap:5px">${row(true)}${row(false)}${row(true)}</span></span></span>`;
  }

  function viewSettings() {
    const s = S.boot.settings, sys = S.boot.system;
    $("#main").innerHTML = `<div class="page"><div class="page-head"><div><h1>${t("settings_title")}</h1></div></div>
      <div class="settings">
        <section><h2>${t("style")}</h2><div class="stylegrid">${STYLES.map((st) => `<button class="stylecard" data-set-style="${st}" aria-pressed="${(s.style || "calm") === st}">
          ${stylePreview(st)}<b>${t("st_" + st)}</b><small>${t("st_" + st + "_d")}</small></button>`).join("")}</div></section>
        <section class="grouped">
          <div class="gr"><span class="t">${t("theme")}</span><span class="seg">${["system", "light", "dark"].map((k) => `<button data-set-theme="${k}" aria-pressed="${(s.theme || "system") === k}">${t("th_" + k)}</button>`).join("")}</span></div>
          <div class="gr"><span class="t">${t("language")}</span><span class="seg"><button data-lang="tr" aria-pressed="${S.lang === "tr"}">Türkçe</button><button data-lang="en" aria-pressed="${S.lang === "en"}">English</button></span></div>
          <div class="gr"><span class="t">${t("accent")}</span><span class="swatches">${SWATCHES.map((c) => `<button class="swatch" data-accent="${c}" aria-pressed="${(s.accent || "") === c}" aria-label="${c || "auto"}" style="background:${c || ACCENTS[s.style || "calm"]}"></button>`).join("")}</span></div>
          ${sys.os === "linux" ? `<div class="gr"><span class="t">${t("linux_pref")}<small>${t("pref_hint")}</small></span><span class="seg"><button data-prefer="native" aria-pressed="${s.prefer !== "flatpak"}">${t("pref_native")}</button><button data-prefer="flatpak" aria-pressed="${s.prefer === "flatpak"}">${t("pref_flatpak")}</button></span></div>` : ""}
          <div class="gr"><span class="t">${t("default_folder")}</span><input class="input mono" id="defdir" style="width:min(360px,100%)" value="${esc(s.backup_dir || S.boot.backup_dir)}">${S.boot.native_dialogs ? `<button class="btn small" data-act="pick-default">${t("change")}</button>` : ""}</div>
        </section>
        <section><h2>${t("managers")}</h2><div class="grouped">${S.boot.managers.map((m) => `<div class="gr"><span class="t">${esc(m.label)}</span><span class="pill ${m.available ? "ok" : ""}">${m.available ? icon("check") : t("missing")}</span></div>`).join("")}</div></section>
        <section><h2>${t("about")}</h2><div class="grouped">
          <div class="gr"><span class="t">${t("version")}</span><span class="mono">KeyStone ${esc(S.boot.version)}</span></div>
          <div class="gr"><span class="t">${t("this_system")}</span><span class="mono">${esc(sys.os_name)} · ${esc(sys.arch)} · ${esc(sys.hostname)}</span></div>
        </div></section>
      </div></div>`;
    const dd = $("#defdir");
    dd.addEventListener("change", () => setSetting({ backup_dir: dd.value.trim() }).then(refreshBoot).then(() => { S.bform.folder = S.boot.backup_dir; }));
  }

  async function setSetting(values) {
    S.boot.settings = await api("settings_set", values);
    if (values.lang) S.lang = values.lang;
    applyAppearance();
    renderShell();
  }

  // ================================================================== DOCK (jobs + log)
  function renderDock() {
    const dock = $("#dock");
    const j = S.jobs[S.dockJob];
    if (!j) { dock.hidden = true; return; }
    dock.hidden = false;
    const active = ["running", "queued"].includes(j.state);
    const queued = Object.values(S.jobs).filter((x) => x.state === "queued").length;
    const done = j.items.filter((i) => ["done", "failed", "skipped"].includes(i.state)).length;
    dock.innerHTML = `<div class="dock-bar">
      <span class="t">${jobTitle(j)} · ${t("js_" + j.state)}${queued && j.state !== "queued" ? ` <span class="muted">(+${queued})</span>` : ""}</span>
      <span class="mono muted">${done}/${j.items.length}</span>
      <span class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(j.progress * 100)}"><i style="width:${Math.round(j.progress * 100)}%"></i></span>
      ${active ? `<button class="btn small" data-act="cancel-job">${t("stop")}</button>` : `<button class="btn small ghost" data-act="dismiss-job">${t("dismiss")}</button>`}
      <button class="btn small ghost" data-act="toggle-dock" aria-expanded="${S.dockOpen}">${icon(S.dockOpen ? "down" : "up")}${t("show_log")}</button>
    </div>
    ${S.dockOpen ? `<div class="dock-body"><div class="dock-items">${j.items.map((i) => `<div><span class="st ${i.state}">${{ done: "✓", failed: "✗", running: "●", queued: "·", skipped: "↷" }[i.state] || "·"}</span>
      <span class="nm">${esc(typeof i.name === "object" ? L(i.name) : i.name)}</span><span class="note">${esc(i.note && i.note.length < 30 ? i.note : "")}</span></div>`).join("")}</div>
      <pre class="log" id="log"></pre></div>` : ""}`;
    if (S.dockOpen) {
      const log = $("#log");
      log.innerHTML = (S.logs[j.id] || []).slice(-1500).map(fmtLine).join("");
      log.scrollTop = log.scrollHeight;
      if (!S.logs[j.id]) api("job_log", j.id).then((lines) => { S.logs[j.id] = lines; if (S.dockJob === j.id && $("#log")) { $("#log").innerHTML = lines.map(fmtLine).join(""); $("#log").scrollTop = 1e9; } });
    }
  }
  function fmtLine(l) {
    const cls = l.startsWith("$ ") ? "cmd" : /^(✓|→)/.test(l) ? "good" : /^(✗|error|E:|Error)/i.test(l) ? "bad" : "";
    return `<span class="${cls}">${esc(l)}</span>\n`;
  }
  function appendLog(line) {
    const log = $("#log");
    if (!log) return;
    const stick = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
    log.insertAdjacentHTML("beforeend", fmtLine(line));
    if (stick) log.scrollTop = log.scrollHeight;
  }

  // ================================================================== overlays
  function toast(msg, err) {
    const el = document.createElement("div");
    el.className = "toast" + (err ? " err" : "");
    el.textContent = msg;
    $("#toasts").appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }
  let modalResolve = null;
  function modal(html) {
    $("#modal").innerHTML = `<div class="modal" role="dialog" aria-modal="true">${html}</div>`;
    const first = $("#modal").querySelector("input, button");
    first && first.focus();
  }
  function closeModal(value) {
    $("#modal").innerHTML = "";
    if (modalResolve) { const r = modalResolve; modalResolve = null; r(value); }
  }
  function confirmBox(msg) {
    return new Promise((res) => { modalResolve = res; modal(`<p style="margin:0">${esc(msg)}</p><div class="actions"><button class="btn" data-mres="0">${t("cancel")}</button><button class="btn primary" data-mres="1">OK</button></div>`); });
  }
  function promptBox(title, value) {
    return new Promise((res) => {
      modalResolve = res;
      modal(`<h2>${esc(title)}</h2><input class="input" id="pval" value="${esc(value || "")}"><div class="actions"><button class="btn" data-mres="">${t("cancel")}</button><button class="btn primary" data-mres="ok">${t("save")}</button></div>`);
      const i = $("#pval"); i.select();
      i.addEventListener("keydown", (e) => { if (e.key === "Enter") closeModal(i.value.trim()); });
    });
  }

  // ================================================================== delegated input
  document.addEventListener("click", async (e) => {
    const el = e.target.closest("[data-nav],[data-act],[data-preset],[data-show],[data-cat],[data-detail],[data-url],[data-close],[data-mres],[data-bmode],[data-rpick],[data-open],[data-pact],[data-set-style],[data-set-theme],[data-lang],[data-accent],[data-prefer],[data-tweak-run],[data-tweak-do],.row[data-pkg]");
    if (!el) { if (e.target.id === "modal") closeModal(); return; }
    const d = el.dataset;
    try {
      if (d.nav) return go(d.nav);
      if (d.mres !== undefined) return closeModal(d.mres === "ok" ? ($("#pval") || {}).value : d.mres === "1");
      if (d.close !== undefined) return closeModal();
      if (d.url) return api("open_url", d.url);
      if (d.detail) { e.stopPropagation(); return showDetail(d.detail); }
      if (d.preset) {
        const ids = S.catalog.filter((p) => p.presets.includes(d.preset) && (p.status === "available" || p.status === "installed")).map((p) => p.id);
        saveProfile({ apps: [...new Set([...profile().apps, ...ids])] });
        return renderList();
      }
      if (d.show) { S.f.show = d.show; return viewApps(); }
      if (d.cat) { S.f.cat = d.cat; return viewApps(); }
      if (el.matches(".row[data-pkg]")) {
        const cb = el.querySelector(".sel");
        if (cb.disabled) return;
        if (e.target !== cb) cb.checked = !cb.checked;
        return toggleApp(d.pkg, cb.checked);
      }
      if (d.bmode) { S.bmode = d.bmode; return viewBackup(); }
      if (d.rpick) { S.restore.path = d.rpick; S.restore.plan = null; S.restore.error = ""; return viewBackup(); }
      if (d.open) return api("open_path", d.open);
      if (d.pact) return profileAction(d.pact, d.pid);
      if (d.setStyle) return setSetting({ style: d.setStyle, accent: "" });
      if (d.setTheme) return setSetting({ theme: d.setTheme });
      if (d.lang) return setSetting({ lang: d.lang });
      if (d.accent !== undefined && el.classList.contains("swatch")) return setSetting({ accent: d.accent });
      if (d.prefer) return setSetting({ prefer: d.prefer });
      if (d.tweakRun) return runTweak(d.tweakRun, "apply");
      if (d.tweakDo) return runTweak(d.tweakDo, d.a);
      switch (d.act) {
        case "install": return api("install", selectedUsable(), "install");
        case "download": { let dest = ""; if (S.boot.native_dialogs) { dest = await api("pick_folder", ""); if (!dest) return; } return api("install", selectedUsable(), "download", dest); }
        case "export-script": return exportScript();
        case "select-visible": saveProfile({ apps: [...new Set([...profile().apps, ...visibleApps().filter((p) => p.status === "available" || p.status === "installed").map((p) => p.id)])] }); return renderList();
        case "clear-apps": saveProfile({ apps: [] }); return renderList();
        case "elevate": return api("relaunch_admin");
        case "pick-folder": { const f = await api("pick_folder", S.bform.folder); if (f) { S.bform.folder = f; refreshBackups(); } return; }
        case "pick-default": { const f = await api("pick_folder", ""); if (f) { await setSetting({ backup_dir: f }); await refreshBoot(); S.bform.folder = S.boot.backup_dir; viewSettings(); } return; }
        case "pick-backup": { const f = await api("pick_backup"); if (f) { S.restore.path = f; S.restore.plan = null; viewBackup(); } return; }
        case "start-backup": {
          const ids = S.backupItems.filter((i) => i.supported && i.found && (profile().backup.length ? profile().backup.includes(i.id) : true)).map((i) => i.id);
          await api("backup_start", ids, S.bform.folder, S.bform.encrypt ? S.bform.pw : "");
          S.dockOpen = true; S.bform.pw = S.bform.pw2 = ""; return viewBackup();
        }
        case "analyze": return analyze();
        case "start-restore": {
          const ids = [...document.querySelectorAll("[data-ritem]")].filter((c) => c.checked).map((c) => c.dataset.ritem);
          await api("restore_start", S.restore.path, S.restore.pw, ids);
          S.dockOpen = true; return renderDock();
        }
        case "new-profile": { const n = await promptBox(t("new_profile"), ""); if (!n) return; await api("profile_create", n, ""); await refreshBoot(); return renderView(); }
        case "import-profile": { const p = await api("profile_import"); if (p) { await refreshBoot(); renderView(); } return; }
        case "cancel-job": return api("job_cancel", S.dockJob);
        case "dismiss-job": S.dockJob = null; S.dockOpen = false; return renderDock();
        case "toggle-dock": S.dockOpen = !S.dockOpen; return renderDock();
      }
    } catch (err) { toast(err.message || String(err), true); }
  });

  document.addEventListener("change", (e) => {
    const el = e.target;
    if (el.dataset.tweak) return runTweak(el.dataset.tweak, el.checked ? "apply" : "revert");
    if (el.dataset.other !== undefined) { S.f.other = el.checked; return viewApps(); }
    if (el.dataset.bitem) {
      const base = profile().backup.length ? profile().backup : S.backupItems.filter((i) => i.found).map((i) => i.id);
      const set = new Set(base);
      el.checked ? set.add(el.dataset.bitem) : set.delete(el.dataset.bitem);
      saveProfile({ backup: [...set] });
      return viewBackup();
    }
    if (el.id === "benc") { S.bform.encrypt = el.checked; return viewBackup(); }
  });

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); if (S.view !== "apps") go("apps"); setTimeout(() => $("#q") && $("#q").focus(), 0); }
    if (e.key === "Escape" && $("#modal").innerHTML) closeModal();
  });
  document.addEventListener("input", (e) => {
    // re-validate backup button as passwords are typed without re-rendering the inputs
    if (["bpw", "bpw2"].includes(e.target.id)) {
      const btn = $("[data-act=start-backup]"), mis = $("#pwmis");
      const bad = !S.bform.pw || S.bform.pw !== S.bform.pw2;
      if (btn) btn.disabled = bad || btn.dataset.chosen === "0" || btn.dataset.running === "true";
      if (mis) mis.hidden = !(S.bform.pw2 && S.bform.pw !== S.bform.pw2);
    }
  });

  // ------------------------------------------------------------------ start
  if (native()) boot();
  else if (token || !("pywebview" in window)) {
    // In the native window pywebview injects its bridge slightly after load.
    let waited = 0;
    const tick = () => { if (native() || token || waited > 1500) boot(); else { waited += 50; setTimeout(tick, 50); } };
    tick();
  }
  window.addEventListener("pywebviewready", () => { if (!S.boot) boot(); });
})();
