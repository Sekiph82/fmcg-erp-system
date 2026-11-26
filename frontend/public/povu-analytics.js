/* POVU first-party website analytics (M44.S01.T009).
 * <script src="https://<erp>/povu-analytics.js" data-api="https://<erp-api>" defer></script>
 * Nothing is sent before the visitor chooses in the banner. Categories: necessary (always), analytics, marketing.
 * Page views are automatic; <a|button data-povu-cta="demo"> sends CTA:demo; <form data-povu-form="contact"> sends
 * FORM:contact on submit. API: povuAnalytics.track(kind, name), .identify(email) (marketing consent only),
 * .openConsent(), .forget().
 */
(function () {
  var me = document.currentScript, api = (me && me.getAttribute("data-api")) || "";
  var K = "povu_consent_v1", V = "povu_vid", S = "povu_sid";
  function rid() { var a = new Uint8Array(16); crypto.getRandomValues(a); return Array.prototype.map.call(a, function (b) { return ("0" + b.toString(16)).slice(-2); }).join(""); }
  function get(store, k) { try { return store.getItem(k); } catch (e) { return null; } }
  function put(store, k, v) { try { store.setItem(k, v); } catch (e) { /* storage blocked */ } }
  function send(path, body) {
    var data = JSON.stringify(body);
    if (navigator.sendBeacon && navigator.sendBeacon(api + "/api/v1/public/web/" + path, new Blob([data], { type: "text/plain" }))) return;
    fetch(api + "/api/v1/public/web/" + path, { method: "POST", body: data, keepalive: true, mode: "no-cors", headers: { "Content-Type": "text/plain" } });
  }
  var consent = null; try { consent = JSON.parse(get(localStorage, K) || "null"); } catch (e) { consent = null; }
  var vid = get(localStorage, V) || rid(); var sid = get(sessionStorage, S) || rid();
  var qs = new URLSearchParams(location.search);
  var utm = { utm_source: qs.get("utm_source") || undefined, utm_medium: qs.get("utm_medium") || undefined, utm_campaign: qs.get("utm_campaign") || undefined };
  function track(kind, name, props) {
    if (!consent || !consent.analytics) return;
    send("collect", { visitor: vid, session: sid, events: [Object.assign({ event_id: rid(), kind: kind, name: name || null, path: location.pathname, referrer: document.referrer || null, properties: props || undefined }, utm)] });
  }
  // M47.S01.T011 point-and-click tagging: staff open a page with ?povu_tagger=1, click an element and copy its selector
  // into POVU (Web analytics → Event tags). Tag rules are fetched from the API; nothing is sent in tagger mode.
  var tags = [];
  function loadTags() {
    fetch(api + "/api/v1/public/web/tags").then(function (r) { return r.ok ? r.json() : []; }).then(function (t) { tags = Array.isArray(t) ? t : []; }).catch(function () { tags = []; });
  }
  function selectorOf(el) {
    var parts = [];
    while (el && el.nodeType === 1 && parts.length < 4) {
      if (el.id) { parts.unshift("#" + CSS.escape(el.id)); break; }
      var s = el.tagName.toLowerCase(), cls = Array.prototype.slice.call(el.classList, 0, 2);
      if (cls.length) s += "." + cls.map(function (c) { return CSS.escape(c); }).join(".");
      var sib = el.parentElement ? Array.prototype.filter.call(el.parentElement.children, function (x) { return x.tagName === el.tagName; }) : [];
      if (sib.length > 1) s += ":nth-of-type(" + (sib.indexOf(el) + 1) + ")";
      parts.unshift(s); el = el.parentElement;
    }
    return parts.join(" > ");
  }
  if (qs.get("povu_tagger") === "1") {
    var last = null;
    document.addEventListener("mouseover", function (e) { if (last) last.style.outline = ""; last = e.target; last.style.outline = "2px solid #f59e0b"; }, true);
    document.addEventListener("click", function (e) { e.preventDefault(); e.stopPropagation(); window.prompt("POVU event tag — copy this selector:", selectorOf(e.target)); }, true);
  }
  function decide(analytics, marketing) {
    consent = { analytics: analytics, marketing: marketing };
    put(localStorage, K, JSON.stringify(consent));
    if (analytics || marketing) { put(localStorage, V, vid); put(sessionStorage, S, sid); }
    send("consent", { visitor: vid, analytics: analytics, marketing: marketing });
    var b = document.getElementById("povu-consent"); if (b) b.remove();
    if (analytics) track("PAGE");
  }
  function banner() {
    if (document.getElementById("povu-consent")) return;
    var d = document.createElement("div"); d.id = "povu-consent"; d.setAttribute("role", "dialog"); d.setAttribute("aria-label", "Cookie choices");
    d.style.cssText = "position:fixed;left:12px;right:12px;bottom:12px;max-width:560px;margin:auto;background:#fff;color:#111;border:1px solid #ccc;border-radius:8px;padding:14px;font:14px/1.4 Arial,sans-serif;z-index:2147483647;box-shadow:0 4px 16px rgba(0,0,0,.15)";
    d.innerHTML = '<p style="margin:0 0 8px">We use necessary storage to run this site. With your permission we also measure visits (analytics) and remember you for marketing.</p>' +
      '<label style="display:block"><input type="checkbox" id="povu-c-a"> Analytics</label><label style="display:block;margin-bottom:8px"><input type="checkbox" id="povu-c-m"> Marketing</label>' +
      '<button id="povu-c-no" style="margin-right:8px">Necessary only</button><button id="povu-c-save" style="margin-right:8px">Save choices</button><button id="povu-c-all">Accept all</button>';
    document.body.appendChild(d);
    d.querySelector("#povu-c-no").onclick = function () { decide(false, false); };
    d.querySelector("#povu-c-all").onclick = function () { decide(true, true); };
    d.querySelector("#povu-c-save").onclick = function () { decide(d.querySelector("#povu-c-a").checked, d.querySelector("#povu-c-m").checked); };
  }
  document.addEventListener("click", function (e) {
    var t = e.target.closest && e.target.closest("[data-povu-cta]"); if (t) track("CTA", t.getAttribute("data-povu-cta"));
    for (var i = 0; i < tags.length; i++) { try { if (e.target.closest(tags[i].selector)) track("CUSTOM", tags[i].event); } catch (x) { /* bad selector */ } }
  });
  document.addEventListener("submit", function (e) { var f = e.target; if (f && f.getAttribute && f.getAttribute("data-povu-form")) track("FORM", f.getAttribute("data-povu-form")); });
  window.povuAnalytics = {
    track: function (kind, name, props) { track(kind === "PAGE" ? "PAGE" : kind === "FORM" || kind === "CTA" ? kind : "CUSTOM", name, props); },
    identify: function (email) { if (consent && consent.marketing) send("identify", { visitor: vid, email: email }); },
    openConsent: banner,
    forget: function () { send("forget", { visitor: vid }); try { localStorage.removeItem(K); localStorage.removeItem(V); sessionStorage.removeItem(S); } catch (e) { /* ignore */ } consent = null; }
  };
  function start() { if (qs.get("povu_tagger") === "1") return; if (consent) { if (consent.analytics) { track("PAGE"); loadTags(); } } else banner(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
