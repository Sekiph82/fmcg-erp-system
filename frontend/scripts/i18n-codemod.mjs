#!/usr/bin/env node
// M51.S01.T008 deterministic i18n codemod for the staff UI (TypeScript compiler API, no other dependency).
//
//   node scripts/i18n-codemod.mjs --write            wrap literals with tx("…") (idempotent)
//   node scripts/i18n-codemod.mjs --report           JSON: remaining literals per area (also imported by i18n-report.mjs)
//   node scripts/i18n-codemod.mjs --catalog          rebuild src/lib/i18n/messages/staff_ui.json from every tx("…") literal
//   node scripts/i18n-codemod.mjs --chunks 1500      split the distinct English strings into staff_ui_chunks/chunk_NNN.json
//   scripts/i18n-codemod.skip.json {"src/…/file.tsx": ["English text"]} keeps a literal unwrapped (e.g. a literal-typed prop)
//
// Wrapped (only inside functions, i.e. evaluated at render/call time, never module-level constants):
//   JSX text; JSX attributes placeholder/title/aria-label/alt/label; object properties label/title/description/placeholder/
//   header/message/text; literal args of toast/alert/confirm/set*Msg/set*Error-style calls; `throw new Error("…")`.
// Never wrapped: values, keys, className, href, ids, enum-like tokens, API payload objects, console.*, comparisons,
// anything that is not a source literal (user and API data never reach tx()).
import ts from "typescript";
import { readFileSync, writeFileSync, readdirSync, statSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const SKIP_FILE = join(root, "scripts/i18n-codemod.skip.json");
const CATALOG = join(root, "src/lib/i18n/messages/staff_ui.json");
const CHUNK_DIR = join(root, "src/lib/i18n/messages/staff_ui_chunks");
const ROOTS = ["src/app/dashboard", "src/components"];
const EXCLUDE = [/[\\/]components[\\/]site[\\/]/, /PartnerLogin\.tsx$/, /PartnerActivate\.tsx$/, /LanguageSwitcher\.tsx$/, /\.(test|spec|stories)\.tsx$/, /\.d\.ts$/];
const ATTRS = new Set(["placeholder", "title", "aria-label", "alt", "label"]);
const PROPS = new Set(["label", "title", "description", "placeholder", "header", "message", "text", "desc", "badge", "group", "hint", "subtitle", "tooltip", "summary", "caption", "heading", "helper", "empty", "cta"]);
const NEXT_EXPORTS = /^(metadata|viewport|dynamic|revalidate|runtime|fetchCache|preferredRegion|maxDuration|config)$/;
const SKIP_ELEMENTS = new Set(["code", "pre", "kbd", "script", "style", "samp"]);
const MESSAGE_CALLEES = new Set(["toast", "alert", "confirm", "prompt", "notify", "showToast", "showMessage", "showError", "showSuccess"]);
const MESSAGE_RECEIVERS = new Set(["toast", "window", "notify"]);
const SETTER_MSG = /^set\w*(Msg|Message|Error|Err|Notice|Toast|Flash|Feedback|Success|Warning|Banner)$/i;
const MUTATION_CALLEE = /^(post|put|patch|delete|request|fetch|stringify|append|set|assign|upload|send|create|update|save|mutate|submit|emit)$/i;
const STATE_CALLEE = /^(useState|useReducer|useRef|useMemo|createContext)$/;
const PAYLOAD_VAR = /(payload|body|params|query|req|request|data|form|draft|initial|default|values|input|dto)/i;

const FUNCTION_KINDS = new Set([ts.SyntaxKind.FunctionDeclaration, ts.SyntaxKind.FunctionExpression, ts.SyntaxKind.ArrowFunction,
  ts.SyntaxKind.MethodDeclaration, ts.SyntaxKind.Constructor, ts.SyntaxKind.GetAccessor, ts.SyntaxKind.SetAccessor]);

const loadSkip = () => (existsSync(SKIP_FILE) ? JSON.parse(readFileSync(SKIP_FILE, "utf8")) : {});

export function listFiles() {
  const out = [];
  const walk = (abs) => {
    for (const n of readdirSync(abs)) {
      const p = join(abs, n);
      const st = statSync(p);
      if (st.isDirectory()) { if (n !== "node_modules") walk(p); }
      else if (p.endsWith(".tsx") && !EXCLUDE.some((r) => r.test(p))) out.push(p);
    }
  };
  ROOTS.forEach((r) => walk(join(root, r)));
  return out.sort();
}

const hasLetters = (s) => /\p{L}/u.test(s);
function enumLike(s) {
  const t = s.trim();
  if (/\s/.test(t)) return false;
  return /^[A-Z0-9_\-.:/]+$/.test(t) || /^[a-z0-9]+(_[a-z0-9]+)+$/.test(t) || /^[a-z0-9]+(-[a-z0-9]+)+$/.test(t)
    || /^[a-z]+(\.[a-z_*]+)+$/.test(t) || /^[a-z]+[A-Z]\w*$/.test(t) || /^[a-z_]+:[\w*.-]+$/.test(t)
    || /^(https?:|\/|#|\.|@|mailto:)/.test(t) || /[\w]@[\w]/.test(t) || /^[\w-]+\.(png|jpg|svg|json|csv|pdf|xlsx?)$/i.test(t);
}
const translatable = (s) => typeof s === "string" && hasLetters(s) && !enumLike(s);
const callName = (call) => {
  const e = call.expression;
  if (ts.isIdentifier(e)) return { name: e.text, recv: null };
  if (ts.isPropertyAccessExpression(e)) return { name: e.name.text, recv: ts.isIdentifier(e.expression) ? e.expression.text : (ts.isPropertyAccessExpression(e.expression) ? e.expression.name.text : null) };
  return { name: null, recv: null };
};
const isTx = (n) => n && ts.isCallExpression(n) && ts.isIdentifier(n.expression) && n.expression.text === "tx";
const decode = (s) => s.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;|&#39;/g, "'");

/** Analyse one file. Returns {edits, skipped, sentences, source, needsImport}. */
export function analyze(file, skipTexts = new Set()) {
  const source = readFileSync(file, "utf8");
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const edits = [];
  const skipped = [];
  let needsLx = false;
  if (/\btx\b/.test(source) && !/import\s*\{[^}]*\btx\b[^}]*\}\s*from\s*["']@\/lib\/i18n/.test(source)) {
    return { edits, skipped: [{ reason: "tx_name_conflict", text: "tx", line: 1 }], sentences: [], source, sf };
  }
  const handled = new Set();
  const compared = new Set();
  const lineOf = (n) => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const skip = (n, reason, text) => { handled.add(n); skipped.push({ reason, text: String(text).slice(0, 80), line: lineOf(n) }); };

  // texts compared against in code ("=== 'Saved'", case "Saved":) must keep their English value
  const collect = (n) => {
    if (ts.isBinaryExpression(n) && [ts.SyntaxKind.EqualsEqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsEqualsToken, ts.SyntaxKind.EqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsToken].includes(n.operatorToken.kind)) {
      for (const o of [n.left, n.right]) if (ts.isStringLiteralLike(o)) compared.add(o.text);
    }
    if (ts.isCaseClause(n) && ts.isStringLiteralLike(n.expression)) compared.add(n.expression.text);
    if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && /^(includes|startsWith|endsWith|indexOf)$/.test(n.expression.name.text))
      for (const a of n.arguments) if (ts.isStringLiteralLike(a)) compared.add(a.text);
    ts.forEachChild(n, collect);
  };
  collect(sf);

  // module-level `const X = [...]/{...}` constants are made lazy: `lx(() => [...])` is a Proxy that rebuilds per locale
  const lazy = new Map();
  for (const st of sf.statements) {
    if (!ts.isVariableStatement(st) || !(st.declarationList.flags & ts.NodeFlags.Const)) continue;
    for (const d of st.declarationList.declarations) {
      if (!ts.isIdentifier(d.name) || !d.initializer || NEXT_EXPORTS.test(d.name.text) || PAYLOAD_VAR.test(d.name.text)) continue;
      let init = d.initializer;
      while (ts.isParenthesizedExpression(init) || ts.isSatisfiesExpression(init) || (ts.isAsExpression(init) && !(ts.isTypeReferenceNode(init.type) && init.type.typeName.getText(sf) === "const"))) init = init.expression;
      if (ts.isArrayLiteralExpression(init) || ts.isObjectLiteralExpression(init)) lazy.set(d.initializer, d.initializer);
    }
  }

  // context of a node: inside a function? in an API payload / state initialiser? under `as const`?
  function context(node) {
    let inFn = false, payload = false, asConst = false;
    for (let p = node.parent, child = node; p; child = p, p = p.parent) {
      if (FUNCTION_KINDS.has(p.kind) || lazy.has(p)) { inFn = true; break; }
      if (ts.isAsExpression(p) && ts.isTypeReferenceNode(p.type) && p.type.typeName.getText(sf) === "const") asConst = true;
      if (ts.isCallExpression(p) && p.arguments.includes(child)) {
        const { name, recv } = callName(p);
        if (name && (MUTATION_CALLEE.test(name) || STATE_CALLEE.test(name) || /^set[A-Z]/.test(name)) && !SETTER_MSG.test(name)) payload = true;
        if (recv === "JSON" || recv === "FormData") payload = true;
      }
      if (ts.isVariableDeclaration(p) && ts.isIdentifier(p.name) && PAYLOAD_VAR.test(p.name.text)) payload = true;
    }
    return { inFn, payload, asConst };
  }

  function propose(node, text, kind, extra = {}) {
    if (handled.has(node)) return;
    if (!translatable(text) || (kind === "msg" && /^(success|error|info|warning|warn|danger|loading|default)$/i.test(text))) { handled.add(node); return; }
    if (compared.has(text)) return skip(node, "compared_in_code", text);
    if (skipTexts.has(text)) return skip(node, "type_constrained", text);
    const ctx = context(node);
    if (!ctx.inFn) return skip(node, "module_level", text);
    if (kind === "prop" && (ctx.payload || ctx.asConst)) return skip(node, ctx.payload ? "api_payload" : "as_const", text);
    handled.add(node);
    edits.push({ start: node.getStart(sf), end: node.end, text: extra.replacement ?? `tx(${JSON.stringify(text)})`, node });
  }

  // wrap the string leaves of a message expression (literals, "a" + b, cond ? "a" : "b", x ?? "fallback", simple templates)
  function wrapLeaves(expr, strictCase) {
    if (!expr) return;
    if (ts.isParenthesizedExpression(expr)) return wrapLeaves(expr.expression, strictCase);
    if (ts.isStringLiteral(expr) || ts.isNoSubstitutionTemplateLiteral(expr)) {
      if (strictCase && !(/\s/.test(expr.text.trim()) || /^[A-Z]/.test(expr.text))) return handled.add(expr);
      return propose(expr, expr.text, "msg");
    }
    if (ts.isTemplateExpression(expr)) {
      const names = new Map();
      let eng = expr.head.text;
      let ok = true;
      for (const sp of expr.templateSpans) {
        let e = sp.expression;
        while (ts.isParenthesizedExpression(e) || ts.isNonNullExpression(e)) e = e.expression;
        const chain = (x) => ts.isIdentifier(x) || (ts.isPropertyAccessExpression(x) && chain(x.expression));
        if (!chain(e)) { ok = false; break; }
        const code = e.getText(sf);
        const base = (ts.isIdentifier(e) ? e.text : e.name.text).replace(/\W/g, "") || "v";
        let name = [...names.entries()].find(([, c]) => c === code)?.[0];
        if (!name) { name = base; let i = 2; while (names.has(name)) name = base + i++; names.set(name, code); }
        eng += `{${name}}` + sp.literal.text;
      }
      if (!ok) return skip(expr, "complex_template", expr.getText(sf));
      const letters = eng.replace(/\{\w+\}/g, "");
      if (!translatable(letters) && !/\s/.test(letters.trim())) return handled.add(expr);
      if (compared.has(eng)) return;
      const vars = [...names.entries()].map(([n, c]) => (n === c ? n : `${n}: ${c}`)).join(", ");
      return propose(expr, eng, "msg", { replacement: `tx(${JSON.stringify(eng)}, { ${vars} })` });
    }
    if (ts.isConditionalExpression(expr)) { wrapLeaves(expr.whenTrue, strictCase); wrapLeaves(expr.whenFalse, strictCase); return; }
    if (ts.isBinaryExpression(expr) && [ts.SyntaxKind.PlusToken, ts.SyntaxKind.QuestionQuestionToken, ts.SyntaxKind.BarBarToken, ts.SyntaxKind.AmpersandAmpersandToken].includes(expr.operatorToken.kind)) {
      wrapLeaves(expr.left, strictCase); wrapLeaves(expr.right, strictCase);
    }
  }

  function jsxInSkippedElement(node) {
    for (let p = node.parent; p; p = p.parent) {
      if (ts.isJsxElement(p) && SKIP_ELEMENTS.has(p.openingElement.tagName.getText(sf))) return true;
      if (FUNCTION_KINDS.has(p.kind)) return false;
    }
    return false;
  }

  function visit(n) {
    if (isTx(n)) { n.arguments.forEach((a) => handled.add(a)); return; } // already wrapped: idempotent
    if (ts.isJsxText(n)) {
      const raw = source.slice(n.pos, n.end);
      if (!hasLetters(raw) || /&#?\w+;/.test(raw.replace(/&(amp|lt|gt|quot|apos|#39);/g, "")) || jsxInSkippedElement(n)) return;
      const core = raw.trim();
      const key = decode(core.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).join(" "));
      if (!translatable(key)) return;
      if (compared.has(key)) return skip(n, "compared_in_code", key);
      if (skipTexts.has(key)) return skip(n, "type_constrained", key);
      if (!context(n).inFn) return skip(n, "module_level", key);
      const lead = raw.match(/^\s*/)[0], trail = raw.slice(lead.length + core.length);
      edits.push({ start: n.pos, end: n.end, text: `${lead}{tx(${JSON.stringify(key)})}${trail}`, node: n });
      handled.add(n);
      return;
    }
    if (ts.isJsxExpression(n) && n.expression && (ts.isJsxElement(n.parent) || ts.isJsxFragment(n.parent) || (ts.isJsxAttribute(n.parent) && ATTRS.has(n.parent.name.getText(sf))))) {
      wrapLeaves(n.expression, false); // {cond ? "A" : "B"}, {x ?? "Fallback"} rendered as text
    } else if (ts.isArrayLiteralExpression(n) && n.elements.length && n.elements.every((e) => ts.isStringLiteral(e)) && ts.isPropertyAccessExpression(n.parent)
      && n.parent.name.text === "map" && ts.isCallExpression(n.parent.parent) && n.parent.parent.expression === n.parent
      && /<[A-Za-z]/.test(n.parent.parent.arguments[0]?.getText(sf) ?? "")) {
      n.elements.forEach((e) => propose(e, e.text, "msg")); // ["Item", "Qty"].map((h) => <th>{h}</th>)
    }
    if (ts.isJsxAttribute(n) && n.initializer && ts.isStringLiteral(n.initializer) && ATTRS.has(n.name.getText(sf))) {
      const v = n.initializer.text;
      if (translatable(v) && !/&#?\w+;/.test(n.initializer.getText(sf)) && !compared.has(v)) {
        if (skipTexts.has(v)) skip(n.initializer, "type_constrained", v);
        else if (!context(n).inFn) skip(n.initializer, "module_level", v);
        else { handled.add(n.initializer); edits.push({ start: n.initializer.getStart(sf), end: n.initializer.end, text: `{tx(${JSON.stringify(v)})}`, node: n }); }
      }
    } else if (ts.isPropertyAssignment(n) && PROPS.has(n.name.getText(sf).replace(/["']/g, "")) && (ts.isStringLiteral(n.initializer) || ts.isNoSubstitutionTemplateLiteral(n.initializer))) {
      propose(n.initializer, n.initializer.text, "prop");
    } else if (ts.isCallExpression(n)) {
      const { name, recv } = callName(n);
      const isMsg = name && ((ts.isIdentifier(n.expression) && (MESSAGE_CALLEES.has(name) || SETTER_MSG.test(name)))
        || (ts.isPropertyAccessExpression(n.expression) && recv && MESSAGE_RECEIVERS.has(recv)
          && (recv === "toast" ? true : /^(alert|confirm|prompt)$/.test(name))));
      if (isMsg) {
        const upto = ts.isIdentifier(n.expression) && /^(toast|showToast|notify)$/.test(name) ? 3 : 1; // toast("success", title, message)
        for (let i = 0; i < Math.min(upto, n.arguments.length); i++) wrapLeaves(n.arguments[i], SETTER_MSG.test(name) && !MESSAGE_CALLEES.has(name));
      }
    } else if (ts.isThrowStatement(n) && n.expression && ts.isNewExpression(n.expression) && ts.isIdentifier(n.expression.expression)
      && n.expression.expression.text === "Error" && n.expression.arguments?.length) {
      wrapLeaves(n.expression.arguments[0], false);
    }
    ts.forEachChild(n, visit);
  }
  visit(sf);
  for (const init of lazy.values()) {
    if (edits.some((e) => e.start >= init.getStart(sf) && e.end <= init.end)) {
      const obj = init.getText(sf).startsWith("{"); // arrow body: an object literal needs parentheses
      edits.push({ start: init.getStart(sf), end: init.getStart(sf), text: obj ? "lx(() => (" : "lx(() => ", node: init }, { start: init.end, end: init.end, text: obj ? "))" : ")", node: init });
      needsLx = true;
    }
  }

  // sentence-like literals no rule covers (arrays of strings, ternaries in JSX, etc.): reported, never rewritten
  const sentences = [];
  const scan = (n) => {
    if (ts.isStringLiteral(n) && !handled.has(n) && /^[A-Z][^\n]*\s[^\n]*[a-z]/.test(n.text) && n.text.trim().split(/\s+/).length >= 2 && !enumLike(n.text)) {
      const p = n.parent;
      const bad = ts.isImportDeclaration(p) || ts.isExportDeclaration(p) || ts.isLiteralTypeNode(p) || (ts.isPropertyAssignment(p) && p.name === n)
        || ts.isJsxAttribute(p) || isTx(p) || (ts.isCallExpression(p) && /^(console|require)$/.test(callName(p).recv ?? callName(p).name ?? ""))
        || (ts.isBinaryExpression(p) && compared.has(n.text)) || ts.isCaseClause(p) || ts.isElementAccessExpression(p);
      if (!bad) sentences.push({ text: n.text.slice(0, 80), line: lineOf(n) });
    }
    ts.forEachChild(n, scan);
  };
  scan(sf);
  return { edits, skipped, sentences, source, sf, needsLx };
}

function apply(file, res) {
  if (!res.edits.length) return false;
  let out = res.source;
  [...res.edits].sort((a, b) => b.start - a.start).forEach((e) => { out = out.slice(0, e.start) + e.text + out.slice(e.end); });
  const want = res.needsLx ? ["tx", "lx"] : ["tx"];
  const m = out.match(/import \{([^}]*)\} from "@\/lib\/i18n\/core";/);
  if (m) {
    const have = m[1].split(",").map((x) => x.trim()).filter(Boolean);
    const all = [...new Set([...have, ...want])];
    out = out.replace(m[0], `import { ${all.join(", ")} } from "@/lib/i18n/core";`);
  } else {
    // insert after the last import (or after the "use client" directive prologue)
    const sf2 = ts.createSourceFile(file, out, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    let pos = 0;
    for (const st of sf2.statements) {
      if (ts.isImportDeclaration(st)) pos = st.end;
      else if (pos === 0 && ts.isExpressionStatement(st) && ts.isStringLiteral(st.expression)) pos = st.end;
    }
    const line = `import { ${want.join(", ")} } from "@/lib/i18n/core";`;
    out = out.slice(0, pos) + (pos ? "\n" : "") + line + (pos ? "" : "\n") + out.slice(pos);
  }
  writeFileSync(file, out);
  return true;
}

const area = (file) => {
  const rel = relative(root, file).split(sep).join("/");
  const m = rel.match(/^src\/app\/dashboard\/([^/]+)/);
  if (m) return `dashboard/${m[1].replace(/\.tsx$/, "")}`;
  const c = rel.match(/^src\/components\/([^/]+)\//);
  return c ? `components/${c[1]}` : "components";
};

/** Remaining-literal report (used by i18n-report.mjs). */
export function report() {
  const skip = loadSkip();
  const files = listFiles();
  const byArea = {};
  const totals = { files: files.length, files_without_use_client: 0, would_wrap: 0, module_level: 0, other_skipped: 0, sentence_literals: 0 };
  for (const f of files) {
    const rel = relative(root, f).split(sep).join("/");
    const r = analyze(f, new Set(skip[rel] ?? []));
    const a = (byArea[area(f)] ??= { files: 0, would_wrap: 0, module_level: 0, other_skipped: 0, sentence_literals: 0 });
    const ml = r.skipped.filter((s) => s.reason === "module_level").length;
    const other = r.skipped.length - ml;
    a.files++; a.would_wrap += r.edits.length; a.module_level += ml; a.other_skipped += other; a.sentence_literals += r.sentences.length;
    totals.would_wrap += r.edits.length; totals.module_level += ml; totals.other_skipped += other; totals.sentence_literals += r.sentences.length;
    if (!/^\s*(\/\/[^\n]*\n|\/\*[\s\S]*?\*\/\s*)*["']use client["']/.test(r.source)) totals.files_without_use_client++;
  }
  return { totals, by_area: Object.fromEntries(Object.entries(byArea).sort()) };
}

/** Every distinct English literal passed to tx() anywhere under src. */
export function collectTxLiterals() {
  const keys = new Set();
  const walk = (abs) => {
    for (const n of readdirSync(abs)) {
      const p = join(abs, n);
      if (statSync(p).isDirectory()) { walk(p); continue; }
      if (!/\.tsx?$/.test(p) || /\.d\.ts$/.test(p)) continue;
      const src = readFileSync(p, "utf8");
      if (!/\btx\(/.test(src)) continue;
      const sf = ts.createSourceFile(p, src, ts.ScriptTarget.Latest, true, p.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
      const v = (node) => {
        if (isTx(node) && node.arguments[0] && ts.isStringLiteralLike(node.arguments[0])) keys.add(node.arguments[0].text);
        ts.forEachChild(node, v);
      };
      v(sf);
    }
  };
  walk(join(root, "src"));
  return [...keys].sort();
}

function buildCatalog(chunkSize) {
  const keys = collectTxLiterals();
  const old = existsSync(CATALOG) ? JSON.parse(readFileSync(CATALOG, "utf8")) : { sw: {}, tr: {} };
  const cat = { en: {}, sw: {}, tr: {} };
  for (const k of keys) {
    cat.en[k] = k;
    for (const l of ["sw", "tr"]) if (old[l]?.[k]) cat[l][k] = old[l][k];
  }
  writeFileSync(CATALOG, JSON.stringify(cat, null, 1) + "\n");
  if (chunkSize) {
    rmSync(CHUNK_DIR, { recursive: true, force: true });
    mkdirSync(CHUNK_DIR, { recursive: true });
    let n = 0;
    for (let i = 0; i < keys.length; i += chunkSize) {
      const part = Object.fromEntries(keys.slice(i, i + chunkSize).map((k) => [k, k]));
      writeFileSync(join(CHUNK_DIR, `chunk_${String(++n).padStart(3, "0")}.json`), JSON.stringify(part, null, 1) + "\n");
    }
    return { distinct: keys.length, chunks: n, dir: relative(root, CHUNK_DIR) };
  }
  return { distinct: keys.length };
}

const invoked = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invoked) {
  const args = process.argv.slice(2);
  if (args.includes("--report")) console.log(JSON.stringify(report(), null, 1));
  else if (args.includes("--catalog") || args.includes("--chunks")) {
    const i = args.indexOf("--chunks");
    console.log(JSON.stringify(buildCatalog(i >= 0 ? Number(args[i + 1]) : 0)));
  }
  else {
    const write = args.includes("--write");
    const skip = loadSkip();
    let changed = 0, edits = 0;
    const reasons = {};
    for (const f of listFiles()) {
      const rel = relative(root, f).split(sep).join("/");
      const r = analyze(f, new Set(skip[rel] ?? []));
      r.skipped.forEach((s) => { reasons[s.reason] = (reasons[s.reason] ?? 0) + 1; });
      if (!r.edits.length) continue;
      edits += r.edits.length;
      if (write && apply(f, r)) changed++;
    }
    console.log(JSON.stringify({ write, files_changed: changed, edits, skipped_by_reason: reasons }));
  }
}
