// Loads Office.js only inside Outlook (host=outlook in the manifest URL), then the sidebar. The local harness loads sidebar.js itself.
(function () {
  function add(src, onload) { var s = document.createElement("script"); s.src = src; if (onload) s.onload = onload; document.body.appendChild(s); }
  if (/[?&]host=outlook/.test(location.search)) add("https://appsforoffice.microsoft.com/lib/1/hosted/office.js", function () { add("sidebar.js"); });
  else add("sidebar.js");
})();
