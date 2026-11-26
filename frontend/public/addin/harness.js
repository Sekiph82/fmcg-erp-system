// Local Outlook host shim (see harness.html). Localhost only.
(function () {
  if (!/^(localhost|127\.0\.0\.1)$/.test(location.hostname)) { document.body.textContent = "The harness only runs on localhost."; return; }
  var $ = function (id) { return document.getElementById(id); };
  var onItem = null;
  var item = {
    get from() { return { emailAddress: $("h-from").value }; },
    get subject() { return $("h-subject").value; },
    get internetMessageId() { return "<" + $("h-id").value + ">"; },
    get conversationId() { return $("h-conv").value; },
    body: { getAsync: function (type, cb) { cb({ value: $("h-body").value }); } },
    displayReplyForm: function (text) { $("reply").textContent = "Reply form opened with:\n" + text; }
  };
  window.Office = {
    EventType: { DialogMessageReceived: "dialogMessageReceived" },
    onReady: function (cb) { cb(); },
    context: {
      mailbox: { item: item },
      ui: {
        displayDialogAsync: function (url, opts, cb) {
          var w = window.open(url, "povu-addin-dialog", "width=520,height=520");
          if (!w) return cb({ status: "failed" });
          var handler = null;
          var listener = function (e) {
            if (e.source !== w || e.origin !== location.origin) return;     // only the ERP's own consent page, same origin
            if (handler) handler({ message: e.data, origin: e.origin });
          };
          window.addEventListener("message", listener);
          cb({ status: "succeeded", value: {
            addEventHandler: function (type, h) { handler = h; },
            close: function () { window.removeEventListener("message", listener); try { w.close(); } catch (x) { /* already closed */ } }
          } });
        }
      }
    }
  };
  window.POVU_HARNESS = { ready: function (cb) {
    onItem = function () { cb(item, function (done) { item.body.getAsync("text", function (r) { done(r.value); }); }); };
    $("h-open").onclick = function () { location.reload(); };
    onItem();
  } };
})();
