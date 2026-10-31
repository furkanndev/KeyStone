/* Welcome window. Python drives it through window.Splash (see app.py). */
(function () {
  "use strict";

  const STEPS = ["os", "managers", "rights", "catalog"];
  const BADGE = { done: ["st", "sp_ok"], lim: ["st lim", "sp_lim"], run: ["st pen pulse", "sp_wait"], wait: ["st pen", "sp_wait"] };
  const ACCENTS = { calm: "#2557D6", console: "#B8F25B", bold: "#5B36F5", apple: "#007AFF" };
  let lang = "tr";
  let finished = 0;

  const $ = (id) => document.getElementById(id);
  const t = (key, vars) => {
    const d = window.I18N[lang] || window.I18N.tr;
    let s = d[key] != null ? d[key] : key;
    for (const k in vars || {}) s = s.split("{" + k + "}").join(vars[k]);
    return s;
  };

  // Same rules as applyAppearance() in app.js, so the window opens in the app's look.
  function appearance(cfg) {
    const style = ACCENTS[cfg.style] ? cfg.style : "calm";
    let theme = cfg.theme || "system";
    if (theme === "system") theme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    const root = document.documentElement, acc = cfg.accent || ACCENTS[style];
    root.dataset.style = style;
    root.dataset.theme = theme;
    root.lang = lang;
    root.style.setProperty("--accent", acc);
    const m = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(acc) || [0, "ff", "ff", "ff"];
    const [r, g, b] = [m[1], m[2], m[3]].map((x) => { const v = parseInt(x, 16) / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    root.style.setProperty("--accent-ink", 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.4 ? "#0E100F" : "#FFFFFF");
  }

  function progress(n) {
    $("fill").style.width = n + "%";
    $("bar").setAttribute("aria-valuenow", n);
    $("tag_l").textContent = t("sp_scan_tag", { n });
  }

  function proceed() {
    $("go").disabled = true;
    $("skip").disabled = true;
    if (window.pywebview && window.pywebview.api) window.pywebview.api.proceed();
  }

  function render(first) {
    $("kick").textContent = t(first ? "sp_kick_first" : "sp_kick");
    $("title").textContent = t("sp_scanning");
    $("lead").textContent = t("sp_lead");
    $("go").textContent = t("sp_go");
    $("skip").textContent = t("sp_skip");
    [["a_os", "sp_a_os"], ["a_pkg", "sp_a_pkg"], ["a_rights", "sp_a_rights"], ["a_cat", "sp_a_cat"]].forEach(([id, key]) => { $(id).textContent = t(key); });
    $("tag_r").textContent = t("sp_hide_wait");
    $("steps").innerHTML = STEPS.map((id) =>
      `<div class="it" id="s_${id}"><span class="k">${t("sp_" + id)}</span><span class="v">—</span><span class="st pen">${t("sp_wait")}</span></div>`).join("");
    progress(0);
  }

  window.Splash = {
    init(cfg) { lang = cfg.lang || "tr"; appearance(cfg); render(cfg.first); },
    step(id, state, detail, vars) {
      const row = $("s_" + id);
      if (!row) return;
      const [cls, label] = BADGE[state];
      const badge = row.querySelector(".st");
      badge.className = cls;
      badge.textContent = t(label);
      row.querySelector(".v").textContent = state === "run" ? t("sp_checking") : t(detail, vars);
      if (state !== "run") progress(Math.round(++finished / STEPS.length * 100));
    },
    finish(r) {
      $("title").textContent = t("sp_done");
      $("stone").classList.remove("pulse");
      $("tag_l").textContent = r.managers;
      $("tag_r").textContent = t("sp_hidden", { n: r.hidden });
      $("go").disabled = false;
      $("skip").hidden = true;
      $("go").focus();
    },
  };

  $("go").addEventListener("click", proceed);
  $("skip").addEventListener("click", proceed);
  render(false);
})();
