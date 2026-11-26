/**
 * M45.S01.T012 / M50.S01.T011 Gmail add-on (Apps Script, CardService). Same API as the Outlook sidebar:
 * /api/v1/public/crm-addin. Sign-in is the ERP's OAuth authorization-code + PKCE flow:
 *   1. the add-on makes a code verifier and opens the ERP consent page (APP_ORIGIN/addin/authorize) in a browser tab;
 *   2. the signed-in ERP user approves; the page shows a one-time code (60 s) that is useless without the verifier;
 *   3. the user types the code into the card; the add-on exchanges code + verifier for a 15-minute access token and a
 *      rotating refresh token, kept in this user's script properties (private to the user).
 * No token, code or verifier ever appears in a URL. Every API call carries X-Addin-Host: gmail. Sign-out revokes the grant.
 * APP_ORIGIN / API_ORIGIN are set by addins/build.py (the placeholder below is never deployed).
 */
var APP_ORIGIN = "https://erp.povu.example";
var API_ORIGIN = "https://erp.povu.example";
var API = API_ORIGIN + "/api/v1/public/crm-addin";
var SESSION_KEY = "POVU_SESSION", PKCE_KEY = "POVU_PKCE";

function props_() { return PropertiesService.getUserProperties(); }
function session_() { try { return JSON.parse(props_().getProperty(SESSION_KEY) || "null"); } catch (e) { return null; } }
function setSession_(s) { if (s) props_().setProperty(SESSION_KEY, JSON.stringify(s)); else props_().deleteProperty(SESSION_KEY); }
function b64url_(bytes) { return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/, ""); }

function raw_(method, path, payload, token) {
  var headers = { "X-Addin-Host": "gmail" };
  if (token) headers["Authorization"] = "Bearer " + token;
  var res = UrlFetchApp.fetch(API + path, {
    method: method, contentType: "application/json", muteHttpExceptions: true, headers: headers,
    payload: payload ? JSON.stringify(payload) : undefined
  });
  var body = {};
  try { body = JSON.parse(res.getContentText() || "{}"); } catch (e) { body = {}; }
  return { code: res.getResponseCode(), body: body };
}
function detail_(r) {
  var d = r.body && r.body.detail;
  return typeof d === "string" ? d : (d && d.detail) || "Request failed (" + r.code + ")";
}
function store_(t) {
  setSession_({ access: t.access_token, refresh: t.refresh_token, exp: Date.now() + (t.expires_in - 30) * 1000 });
}
function refresh_() {
  var s = session_();
  if (!s) throw new Error("Signed out.");
  var r = raw_("post", "/auth/refresh", { refresh_token: s.refresh });
  if (r.code !== 200) { setSession_(null); throw new Error("Signed out. Sign in again."); }
  store_(r.body);
  return session_();
}
function call_(method, path, payload) {
  var s = session_();
  if (!s) throw new Error("Signed out.");
  if (Date.now() > s.exp) s = refresh_();
  var r = raw_(method, path, payload, s.access);
  if (r.code === 401) { s = refresh_(); r = raw_(method, path, payload, s.access); }
  if (r.code >= 400) throw new Error(detail_(r));
  return r.body;
}

// ── sign-in ────────────────────────────────────────────────────────────────────────
function authCard_(note) {
  var verifier = b64url_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, Utilities.getUuid() + Utilities.getUuid() + Date.now()))
    + b64url_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, Utilities.getUuid()));
  var state = b64url_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, Utilities.getUuid())).slice(0, 16);
  var challenge = b64url_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, verifier));
  props_().setProperty(PKCE_KEY, JSON.stringify({ verifier: verifier, state: state, exp: Date.now() + 10 * 60 * 1000 }));
  var url = APP_ORIGIN + "/addin/authorize?host=gmail&challenge=" + challenge + "&state=" + state;
  var sec = CardService.newCardSection()
    .addWidget(CardService.newTextParagraph().setText(note || "Sign in with your ERP account to use the CRM from Gmail."))
    .addWidget(CardService.newTextButton().setText("1. Open the ERP sign-in page").setOpenLink(CardService.newOpenLink().setUrl(url)))
    .addWidget(CardService.newTextInput().setFieldName("code").setTitle("2. Code shown on that page"))
    .addWidget(CardService.newTextButton().setText("3. Finish sign-in").setOnClickAction(CardService.newAction().setFunctionName("finishAuth_")));
  return CardService.newCardBuilder().setHeader(CardService.newCardHeader().setTitle("POVU CRM")).addSection(sec).build();
}

function finishAuth_(e) {
  var p = null;
  try { p = JSON.parse(props_().getProperty(PKCE_KEY) || "null"); } catch (x) { p = null; }
  var code = ((e.formInput && e.formInput.code) || "").trim();
  if (!p || Date.now() > p.exp || !code) return notify_("Open the sign-in page first, then type its code.");
  var r = raw_("post", "/auth/token", { code: code, code_verifier: p.verifier, host: "gmail" });
  props_().deleteProperty(PKCE_KEY);
  if (r.code !== 200) return notify_("Sign-in failed: " + detail_(r));
  store_(r.body);
  return CardService.newActionResponseBuilder().setNavigation(CardService.newNavigation().popToRoot())
    .setNotification(CardService.newNotification().setText("Signed in. Reopen the e-mail.")).build();
}

function signOut_() {
  var s = session_();
  if (s) { try { raw_("post", "/auth/revoke", null, s.access); } catch (e) { /* the grant also expires on its own */ } }
  setSession_(null);
  return CardService.newActionResponseBuilder().setNavigation(CardService.newNavigation().popToRoot())
    .setNotification(CardService.newNotification().setText("Signed out.")).build();
}
function notify_(text) { return CardService.newActionResponseBuilder().setNotification(CardService.newNotification().setText(text)).build(); }

// ── cards ──────────────────────────────────────────────────────────────────────────
function onHomepage() {
  if (!session_()) return authCard_();
  var who = call_("get", "/whoami");
  var sec = CardService.newCardSection()
    .addWidget(CardService.newTextParagraph().setText("Signed in as " + who.name + ". Open an e-mail to see its CRM contact."))
    .addWidget(CardService.newTextButton().setText("Sign out").setOnClickAction(CardService.newAction().setFunctionName("signOut_")));
  return CardService.newCardBuilder().setHeader(CardService.newCardHeader().setTitle("POVU CRM")).addSection(sec).build();
}

function onGmailMessage(e) {
  if (!session_()) return authCard_();
  GmailApp.setCurrentMessageAccessToken(e.gmail.accessToken);
  var msg = GmailApp.getMessageById(e.gmail.messageId);
  var from = (msg.getFrom().match(/<([^>]+)>/) || [null, msg.getFrom()])[1];
  var threadId = e.gmail.threadId || msg.getThread().getId();
  var card = CardService.newCardBuilder().setHeader(CardService.newCardHeader().setTitle("POVU CRM"));
  var sec = CardService.newCardSection();
  var d;
  try { d = call_("get", "/lookup?email=" + encodeURIComponent(from)); }
  catch (err) {
    if (/Signed out/.test(String(err.message))) return authCard_("Your sign-in ended. Sign in again.");
    sec.addWidget(CardService.newTextParagraph().setText("CRM unavailable: " + err.message));
    return card.addSection(sec).build();
  }
  var scopes = [];
  try { scopes = call_("get", "/whoami").scopes; } catch (err2) { scopes = []; }
  if (!d.found) {
    sec.addWidget(CardService.newTextParagraph().setText("No CRM contact for " + from + "."));
  } else {
    sec.addWidget(CardService.newDecoratedText().setTopLabel("Contact").setText(d.contact.name).setBottomLabel(d.contact.job_title || ""));
    d.recent.forEach(function (a) { sec.addWidget(CardService.newTextParagraph().setText(a.type.toLowerCase() + ": " + a.subject)); });
    if (d.deals.length && scopes.indexOf("addin.write") >= 0) {
      var sel = CardService.newSelectionInput().setType(CardService.SelectionInputType.DROPDOWN).setFieldName("deal").setTitle("Deal");
      d.deals.forEach(function (r, i) { sel.addItem(r.company + " (" + String(r.status).toLowerCase() + ")", r.id, i === 0); });
      sec.addWidget(sel);
      var ctx = { id: e.gmail.messageId, thread: threadId };
      sec.addWidget(CardService.newTextButton().setText("Log this e-mail").setOnClickAction(CardService.newAction().setFunctionName("logEmail_").setParameters(ctx)));
      sec.addWidget(CardService.newTextInput().setFieldName("text").setTitle("Note or follow-up task").setMultiline(true));
      sec.addWidget(CardService.newTextButton().setText("Add note").setOnClickAction(CardService.newAction().setFunctionName("addNote_")));
      sec.addWidget(CardService.newTextButton().setText("Add task").setOnClickAction(CardService.newAction().setFunctionName("addTask_")));
    }
    try {
      var logged = call_("get", "/thread?thread_id=" + encodeURIComponent(threadId));
      logged.forEach(function (a) { sec.addWidget(CardService.newTextParagraph().setText("Logged: " + a.type.toLowerCase() + " on " + a.deal + ": " + a.subject)); });
    } catch (err3) { /* thread history is optional */ }
  }
  card.addSection(sec);
  try {
    var tpls = call_("get", "/templates");
    if (tpls.length) {
      var ts = CardService.newCardSection();
      var tsel = CardService.newSelectionInput().setType(CardService.SelectionInputType.DROPDOWN).setFieldName("tpl").setTitle("Reply with a template");
      tpls.forEach(function (t, i) { tsel.addItem(t.name, t.id, i === 0); });
      ts.addWidget(tsel).addWidget(CardService.newTextButton().setText("Create reply draft").setOnClickAction(
        CardService.newAction().setFunctionName("replyTemplate_").setParameters({ id: e.gmail.messageId })));
      card.addSection(ts);
    }
  } catch (err4) { /* templates optional */ }
  card.addSection(CardService.newCardSection().addWidget(CardService.newTextButton().setText("Sign out").setOnClickAction(CardService.newAction().setFunctionName("signOut_"))));
  return card.build();
}

function logEmail_(e) {
  var msg = GmailApp.getMessageById(e.parameters.id);
  var d = call_("post", "/log-email", { crm_record_id: e.formInput.deal, subject: msg.getSubject(), body: msg.getPlainBody().slice(0, 2000),
    direction: "IN", message_id: (msg.getHeader("Message-ID") || e.parameters.id).replace(/[<>]/g, ""), thread_id: e.parameters.thread });
  return notify_(d.duplicate ? "Already logged." : "E-mail logged.");
}
function addNote_(e) { return addActivity_("note", e); }
function addTask_(e) { return addActivity_("task", e); }
function addActivity_(kind, e) {
  var text = ((e.formInput && e.formInput.text) || "").trim();
  if (!text) return notify_("Write the note first.");
  call_("post", "/" + kind, { crm_record_id: e.formInput.deal, text: text });
  return notify_(kind === "note" ? "Note added." : "Task added.");
}
function replyTemplate_(e) {
  var tpls = call_("get", "/templates");
  var t = tpls.filter(function (x) { return x.id === e.formInput.tpl; })[0];
  if (!t) return notify_("Template not found.");
  var draft = GmailApp.getMessageById(e.parameters.id).createDraftReply(t.body);   // plain text, never HTML
  return CardService.newComposeActionResponseBuilder().setGmailDraft(draft).build();
}
