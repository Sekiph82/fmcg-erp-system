// M45.S01.T012 / M50.S01.T011 shared CRM sidebar for the Outlook add-in (and the local host harness, harness.html).
// Sign-in: OAuth authorization code + PKCE through the ERP consent page (addin/authorize) opened with the Office dialog API;
// the code comes back by dialog message (never in a URL), is exchanged for a 15-minute access token and a rotating refresh
// token that live in sessionStorage of this task pane only. The API origin is whatever the ERP's own consent page reports,
// never a URL parameter. Every request carries X-Addin-Host: outlook. Mail content is only ever rendered as text.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var SKEY = "povu-crm-addin-session";
  var HARNESS = /[?&]host=harness/.test(location.search) && /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  var mail = { from: "", subject: "", body: "", id: "", thread: "" };
  var sess = null;
  try { sess = JSON.parse(sessionStorage.getItem(SKEY) || "null"); } catch (e) { sess = null; }

  function say(t, bad) { $("msg").textContent = t; $("msg").className = bad ? "err" : ""; }
  function save() { try { if (sess) sessionStorage.setItem(SKEY, JSON.stringify(sess)); else sessionStorage.removeItem(SKEY); } catch (e) { /* in-memory only */ } }
  function el(tag, value, cls) { var n = document.createElement(tag); n.textContent = value; if (cls) n.className = cls; return n; }
  function b64url(buf) { var s = ""; new Uint8Array(buf).forEach(function (b) { s += String.fromCharCode(b); }); return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); }
  function raw(method, path, body, token) {
    var h = { "Content-Type": "application/json", "X-Addin-Host": "outlook" };
    if (token) h["Authorization"] = "Bearer " + token;
    return fetch(sess.api + "/api/v1/public/crm-addin" + path, { method: method, headers: h, body: body ? JSON.stringify(body) : undefined });
  }
  function parse(r) {
    return r.json().catch(function () { return {}; }).then(function (d) {
      if (!r.ok) { var e = new Error(typeof d.detail === "string" ? d.detail : (d.detail && d.detail.detail) || "Request failed (" + r.status + ")"); e.status = r.status; throw e; }
      return d;
    });
  }
  var inflight = null;      // single-flight: concurrent 401s share ONE refresh, so the rotating token is never presented twice
  function refresh() {
    if (inflight) return inflight;
    var attempt = function (n) {
      try { sess = JSON.parse(sessionStorage.getItem(SKEY) || "null") || sess; } catch (e) { /* keep in-memory */ }
      return raw("POST", "/auth/refresh", { refresh_token: sess.refresh }).then(parse).then(function (t) { sess.access = t.access_token; sess.refresh = t.refresh_token; save(); },
        function (e) {      // 409: another request just rotated the token; pick up its result and retry once
          if (e.status === 409 && n < 2) return new Promise(function (ok) { setTimeout(ok, 1000); }).then(function () { return attempt(n + 1); });
          throw e;
        });
    };
    inflight = attempt(0).then(function () { inflight = null; }, function (e) { inflight = null; throw e; });
    return inflight;
  }
  function call(method, path, body, retried) {
    return raw(method, path, body, sess.access).then(function (r) {
      if (r.status === 401 && !retried) return refresh().then(function () { return call(method, path, body, true); });
      return parse(r);
    }).catch(function (e) { if (e.status === 401) { sess = null; save(); show(); } throw e; });
  }

  function signIn() {
    var verifier = b64url(crypto.getRandomValues(new Uint8Array(32))), state = b64url(crypto.getRandomValues(new Uint8Array(12)));
    crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)).then(function (d) {
      var url = location.origin + "/addin/authorize?host=outlook&challenge=" + b64url(d) + "&state=" + state + "&origin=" + encodeURIComponent(location.origin);
      var finish = function (msg) {
        var m; try { m = JSON.parse(msg); } catch (e) { return say("Sign-in answer not understood.", true); }
        if (m.type === "povu-addin-denied") return say("Sign-in cancelled.", true);
        if (m.type !== "povu-addin-code" || m.state !== state || !/^https?:\/\//.test(m.api || "")) return say("Sign-in answer rejected.", true);
        var api = m.api.replace(/\/$/, "");
        fetch(api + "/api/v1/public/crm-addin/auth/token", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code: m.code, code_verifier: verifier, host: "outlook" }) }).then(parse).then(function (t) {
          sess = { api: api, access: t.access_token, refresh: t.refresh_token }; save(); show();
        }).catch(function (e) { say(e.message, true); });
      };
      if (window.Office && Office.context && Office.context.ui && Office.context.ui.displayDialogAsync) {
        Office.context.ui.displayDialogAsync(url, { height: 55, width: 30 }, function (res) {
          if (res.status !== "succeeded") return say("Could not open the sign-in window.", true);
          var dlg = res.value;
          dlg.addEventHandler(Office.EventType.DialogMessageReceived, function (arg) {
            if (arg.origin && arg.origin !== location.origin) return say("Sign-in answer came from an unexpected origin.", true);   // the dialog is an ERP page
            dlg.close(); finish(arg.message);
          });
        });
      } else say("Sign-in needs Outlook (or the local harness).", true);
    });
  }

  function render(d) {
    var box = $("contact"); box.textContent = "";
    if (!d.found) { box.appendChild(el("p", "No CRM contact for " + mail.from + ".", "muted")); $("actions").hidden = true; return; }
    box.appendChild(el("p", d.contact.name + (d.contact.job_title ? " · " + d.contact.job_title : "") + (d.contact.lifecycle_stage ? " · " + d.contact.lifecycle_stage.toLowerCase() : "")));
    var ul = document.createElement("ul");
    d.recent.forEach(function (a) { ul.appendChild(el("li", a.type.toLowerCase() + ": " + a.subject)); });
    if (d.recent.length) { box.appendChild(el("h2", "Recent")); box.appendChild(ul); }
    var sel = $("deal"); sel.textContent = "";
    d.deals.forEach(function (r) { var o = el("option", r.company + " (" + String(r.status).toLowerCase() + ")"); o.value = r.id; sel.appendChild(o); });
    $("actions").hidden = d.deals.length === 0;
  }
  function load() {
    $("who").textContent = mail.from ? "Sender: " + mail.from : "No e-mail open.";
    call("GET", "/whoami").then(function (w) { $("who").textContent += " · signed in as " + w.name + (w.scopes.indexOf("addin.write") < 0 ? " (look-up only)" : ""); $("actions").dataset.write = String(w.scopes.indexOf("addin.write") >= 0); }).catch(function () {});
    if (mail.from) call("GET", "/lookup?email=" + encodeURIComponent(mail.from)).then(render).catch(function (e) { say(e.message, true); });
    if (mail.thread) call("GET", "/thread?thread_id=" + encodeURIComponent(mail.thread)).then(function (list) {
      var t = $("thread"); t.textContent = "";
      if (list.length) { t.appendChild(el("h2", "Already logged from this conversation")); var ul = document.createElement("ul"); list.forEach(function (a) { ul.appendChild(el("li", a.type.toLowerCase() + " on " + a.deal + ": " + a.subject)); }); t.appendChild(ul); }
    }).catch(function () {});
    call("GET", "/templates").then(function (list) {
      var sel = $("tpl"); list.forEach(function (t) { var o = el("option", t.name); o.value = t.id; o.dataset.body = t.body; sel.appendChild(o); });
    }).catch(function () { /* templates optional */ });
  }
  function show() { $("setup").hidden = !!sess; $("main").hidden = !sess; if (sess) load(); }

  $("signin").onclick = signIn;
  $("signout").onclick = function () {
    var done = function () { sess = null; save(); show(); say("Signed out."); };
    if (!sess) return done();
    raw("POST", "/auth/revoke", null, sess.access).then(done, done);
  };
  $("log").onclick = function () {
    call("POST", "/log-email", { crm_record_id: $("deal").value, subject: mail.subject || "(no subject)", body: mail.body, direction: "IN",
      message_id: mail.id.replace(/[<>]/g, "") || null, thread_id: mail.thread || null })
      .then(function (d) { say(d.duplicate ? "Already logged." : "E-mail logged."); load(); }).catch(function (e) { say(e.message, true); });
  };
  ["note", "task"].forEach(function (k) {
    $(k).onclick = function () {
      if (!$("text").value.trim()) return say("Write the note first.", true);
      call("POST", "/" + k, { crm_record_id: $("deal").value, text: $("text").value }).then(function () { $("text").value = ""; say(k === "note" ? "Note added." : "Task added."); })
        .catch(function (e) { say(e.message, true); });
    };
  });
  $("tpl").onchange = function (e) {
    var o = e.target.selectedOptions[0]; if (!o || !o.value) return;
    var item = window.Office && Office.context && Office.context.mailbox && Office.context.mailbox.item;
    if (item && item.displayReplyForm) { item.displayReplyForm(o.dataset.body); say("Reply opened with the template."); }   // plain text, never HTML
    else if (navigator.clipboard) navigator.clipboard.writeText(o.dataset.body).then(function () { say("Template copied."); });
  };

  function start(item, getBody) {
    if (item) {
      mail.from = (item.from && item.from.emailAddress) || ""; mail.subject = item.subject || ""; mail.id = item.internetMessageId || ""; mail.thread = item.conversationId || "";
    }
    if (getBody) getBody(function (t) { mail.body = (t || "").slice(0, 2000); show(); }); else show();
  }
  if (HARNESS && window.POVU_HARNESS) { window.POVU_HARNESS.ready(function (item, getBody) { start(item, getBody); }); }
  else if (window.Office) {
    Office.onReady(function () {
      var item = Office.context.mailbox && Office.context.mailbox.item;
      start(item, item && item.body && item.body.getAsync ? function (cb) { item.body.getAsync("text", function (r) { cb(r.value); }); } : null);
    });
  } else { $("setup").hidden = false; say("Open this add-in from Outlook (or the local harness).", true); }
})();
