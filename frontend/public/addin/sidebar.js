// M45.S01.T012 shared CRM sidebar for the Outlook add-in (and the local harness). The Gmail add-on uses the same API
// from Apps Script (addins/gmail). Token: personal access token with the crm.addin scope, kept in this browser only.
(function () {
  var q = new URLSearchParams(location.search);
  var API = (q.get("api") || location.origin).replace(/\/$/, "") + "/api/v1/public/crm-addin";
  var KEY = "povu-crm-addin-token";
  var $ = function (id) { return document.getElementById(id); };
  var mail = { from: q.get("email") || "", subject: q.get("subject") || "", body: q.get("body") || "", id: q.get("message_id") || "" };
  var token = null;
  try { token = localStorage.getItem(KEY); } catch (e) { /* storage blocked */ }

  function say(t, bad) { $("msg").textContent = t; $("msg").className = bad ? "err" : ""; }
  function call(method, path, body) {
    return fetch(API + path, { method: method, headers: { "Authorization": "Bearer " + token, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (r.status === 401) { forget(); throw new Error("Token invalid, expired or revoked."); }
        if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : "Request failed (" + r.status + ")");
        return d;
      });
    });
  }
  function forget() { try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ } token = null; show(); }
  function text(tag, value, cls) { var el = document.createElement(tag); el.textContent = value; if (cls) el.className = cls; return el; }

  function render(d) {
    var box = $("contact"); box.innerHTML = "";
    if (!d.found) { box.appendChild(text("p", "No CRM contact for " + mail.from + ".", "muted")); $("actions").hidden = true; return; }
    box.appendChild(text("p", d.contact.name + (d.contact.job_title ? " · " + d.contact.job_title : "") + (d.contact.lifecycle_stage ? " · " + d.contact.lifecycle_stage.toLowerCase() : "")));
    var ul = document.createElement("ul");
    d.recent.forEach(function (a) { ul.appendChild(text("li", a.type.toLowerCase() + ": " + a.subject)); });
    if (d.recent.length) { box.appendChild(text("h2", "Recent")); box.appendChild(ul); }
    var sel = $("deal"); sel.innerHTML = "";
    d.deals.forEach(function (r) { var o = text("option", r.company + " (" + String(r.status).toLowerCase() + ")"); o.value = r.id; sel.appendChild(o); });
    $("actions").hidden = d.deals.length === 0;
  }
  function load() {
    $("who").textContent = mail.from ? "Sender: " + mail.from : "No e-mail open.";
    if (mail.from) call("GET", "/lookup?email=" + encodeURIComponent(mail.from)).then(render).catch(function (e) { say(e.message, true); });
    call("GET", "/templates").then(function (list) {
      var sel = $("tpl"); list.forEach(function (t) { var o = text("option", t.name); o.value = t.id; o.dataset.body = t.body; sel.appendChild(o); });
    }).catch(function () { /* templates optional */ });
  }
  function show() { $("setup").hidden = !!token; $("main").hidden = !token; if (token) load(); }

  $("save").onclick = function () { token = $("token").value.trim(); try { localStorage.setItem(KEY, token); } catch (e) { /* session only */ } show(); };
  $("forget").onclick = forget;
  $("log").onclick = function () {
    call("POST", "/log-email", { crm_record_id: $("deal").value, subject: mail.subject || "(no subject)", body: mail.body, direction: "IN", message_id: mail.id.replace(/[<>]/g, "") || null })
      .then(function (d) { say(d.duplicate ? "Already logged." : "E-mail logged."); }).catch(function (e) { say(e.message, true); });
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
    if (window.Office && Office.context && Office.context.mailbox && Office.context.mailbox.item && Office.context.mailbox.item.body && Office.context.mailbox.item.body.setSelectedDataAsync) {
      Office.context.mailbox.item.body.setSelectedDataAsync(o.dataset.body, { coercionType: "text" }); say("Template inserted.");
    } else if (navigator.clipboard) { navigator.clipboard.writeText(o.dataset.body).then(function () { say("Template copied."); }); }
  };

  if (window.Office) {
    Office.onReady(function () {
      var item = Office.context.mailbox && Office.context.mailbox.item;
      if (item && item.from) { mail.from = item.from.emailAddress; mail.subject = item.subject; mail.id = item.internetMessageId || ""; }
      if (item && item.body && item.body.getAsync) item.body.getAsync("text", function (r) { mail.body = (r.value || "").slice(0, 2000); show(); });
      else show();
    });
  } else { show(); }
})();
