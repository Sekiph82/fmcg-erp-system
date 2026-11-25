/**
 * M45.S01.T012 Gmail add-on (Apps Script, CardService). Same API as the Outlook sidebar:
 * /api/v1/public/crm-addin with a personal access token (scope crm.addin) kept in the user's script properties.
 * Replace ERP_ORIGIN (and urlFetchWhitelist in appsscript.json) with the ERP's public HTTPS origin.
 */
var ERP_ORIGIN = "https://erp.povu.example";
var API = ERP_ORIGIN + "/api/v1/public/crm-addin";

function token_() { return PropertiesService.getUserProperties().getProperty("POVU_TOKEN"); }

function call_(method, path, payload) {
  var res = UrlFetchApp.fetch(API + path, {
    method: method, contentType: "application/json", muteHttpExceptions: true,
    headers: { Authorization: "Bearer " + token_() },
    payload: payload ? JSON.stringify(payload) : undefined
  });
  var code = res.getResponseCode(), body = {};
  try { body = JSON.parse(res.getContentText() || "{}"); } catch (e) { body = {}; }
  if (code === 401) { PropertiesService.getUserProperties().deleteProperty("POVU_TOKEN"); throw new Error("Token invalid or revoked."); }
  if (code >= 400) throw new Error(typeof body.detail === "string" ? body.detail : "Request failed (" + code + ")");
  return body;
}

function onGmailMessage(e) {
  if (!token_()) return tokenCard_();
  GmailApp.setCurrentMessageAccessToken(e.gmail.accessToken);
  var msg = GmailApp.getMessageById(e.gmail.messageId);
  var from = (msg.getFrom().match(/<([^>]+)>/) || [null, msg.getFrom()])[1];
  var d = call_("get", "/lookup?email=" + encodeURIComponent(from));
  var sec = CardService.newCardSection();
  if (!d.found) {
    sec.addWidget(CardService.newTextParagraph().setText("No CRM contact for " + from + "."));
    return CardService.newCardBuilder().addSection(sec).build();
  }
  sec.addWidget(CardService.newDecoratedText().setTopLabel("Contact").setText(d.contact.name).setBottomLabel(d.contact.job_title || ""));
  d.deals.forEach(function (r) {
    sec.addWidget(CardService.newTextButton().setText("Log e-mail to " + r.company).setOnClickAction(
      CardService.newAction().setFunctionName("logEmail_").setParameters({ deal: r.id, id: e.gmail.messageId })));
  });
  d.recent.forEach(function (a) { sec.addWidget(CardService.newTextParagraph().setText(a.type.toLowerCase() + ": " + a.subject)); });
  return CardService.newCardBuilder().setHeader(CardService.newCardHeader().setTitle("POVU CRM")).addSection(sec).build();
}

function logEmail_(e) {
  var msg = GmailApp.getMessageById(e.parameters.id);
  var d = call_("post", "/log-email", { crm_record_id: e.parameters.deal, subject: msg.getSubject(),
    body: msg.getPlainBody().slice(0, 2000), direction: "IN", message_id: (msg.getHeader("Message-ID") || e.parameters.id).replace(/[<>]/g, "") });
  return CardService.newActionResponseBuilder().setNotification(
    CardService.newNotification().setText(d.duplicate ? "Already logged." : "E-mail logged.")).build();
}

function tokenCard_() {
  var sec = CardService.newCardSection()
    .addWidget(CardService.newTextParagraph().setText("Paste a personal access token with the crm.addin scope (ERP → My profile → Access tokens)."))
    .addWidget(CardService.newTextInput().setFieldName("token").setTitle("Access token"))
    .addWidget(CardService.newTextButton().setText("Save").setOnClickAction(CardService.newAction().setFunctionName("saveToken_")));
  return CardService.newCardBuilder().addSection(sec).build();
}

function saveToken_(e) {
  PropertiesService.getUserProperties().setProperty("POVU_TOKEN", e.formInput.token);
  return CardService.newActionResponseBuilder().setNotification(CardService.newNotification().setText("Saved. Reopen the e-mail.")).build();
}
