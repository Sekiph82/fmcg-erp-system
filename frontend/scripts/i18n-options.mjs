// M51 re-review: finds places where TRANSLATED text can become DATA. An <option> without a `value` attribute submits its
// text, so wrapping that text in tx() makes SW/TR users submit translated values. Also flagged: tx() inside a value /
// defaultValue / checked / name attribute, and reading displayed text back as data (textContent / innerText).
//   node scripts/i18n-options.mjs        -> JSON list of issues, exit 1 when there is any
import ts from "typescript";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const hasTx = (text) => /\b(tx|xlate|txApi|lx)\(/.test(text);
const DATA_ATTRS = new Set(["value", "defaultValue", "name", "id", "htmlFor"]);

function attrNames(openOrSelf) {
  const names = new Set();
  let spread = false;
  for (const a of openOrSelf.attributes.properties) {
    if (ts.isJsxSpreadAttribute(a)) spread = true;
    else names.add(a.name.getText());
  }
  return { names, spread };
}

/** Does the array expression feeding a `.map` (resolved through same-file consts) carry tx()/lx() text? */
function arrayIsTranslated(arr, sf) {
  if (hasTx(arr.getText(sf))) return true;
  let id = arr;
  while (ts.isParenthesizedExpression(id) || ts.isAsExpression(id) || ts.isNonNullExpression(id)) id = id.expression;
  if (!ts.isIdentifier(id)) return false;
  let found = false;
  const visit = (n) => {
    if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.name.text === id.text && n.initializer && hasTx(n.initializer.getText(sf))) found = true;
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return found;
}

export function scanSource(file, source) {
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const issues = [];
  const line = (n) => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const add = (n, reason) => issues.push({ file, line: line(n), reason });
  const visit = (n) => {
    if (ts.isJsxElement(n) && n.openingElement.tagName.getText(sf) === "option") {
      const { names, spread } = attrNames(n.openingElement);
      if (!names.has("value") && !spread) {
        const inner = n.children.map((c) => c.getText(sf)).join("");
        if (hasTx(inner)) add(n, "option_without_value_wraps_tx");
        else {
          // {x} where x is the parameter of a .map callback over a translated array
          for (const c of n.children) {
            if (!ts.isJsxExpression(c) || !c.expression || !ts.isIdentifier(c.expression)) continue;
            for (let p = n.parent; p; p = p.parent) {
              if ((ts.isArrowFunction(p) || ts.isFunctionExpression(p)) && p.parameters[0] && ts.isIdentifier(p.parameters[0].name) && p.parameters[0].name.text === c.expression.text) {
                const call = p.parent;
                if (ts.isCallExpression(call) && ts.isPropertyAccessExpression(call.expression) && call.expression.name.text === "map" && arrayIsTranslated(call.expression.expression, sf))
                  add(n, "option_without_value_mapped_from_translated_array");
                break;
              }
            }
          }
        }
      }
    }
    if (ts.isJsxAttribute(n) && DATA_ATTRS.has(n.name.getText(sf)) && n.initializer && hasTx(n.initializer.getText(sf))) {
      const tag = n.parent.parent;
      const name = ts.isJsxOpeningElement(tag) || ts.isJsxSelfClosingElement(tag) ? tag.tagName.getText(sf) : "";
      if (/^(option|input|select|textarea|datalist|label|button|Select|Input)$/.test(name)) add(n, "translated_text_in_data_attribute");
    }
    if (ts.isPropertyAccessExpression(n) && /^(textContent|innerText|innerHTML)$/.test(n.name.text) && /\btarget\b|\bcurrentTarget\b/.test(n.expression.getText(sf)))
      add(n, "displayed_text_read_back_as_data");
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return issues;
}

export function scanAll() {
  const out = [];
  const walk = (abs) => {
    for (const nme of readdirSync(abs)) {
      const p = join(abs, nme);
      if (statSync(p).isDirectory()) { if (nme !== "node_modules") walk(p); continue; }
      if (!p.endsWith(".tsx")) continue;
      out.push(...scanSource(relative(root, p).split(sep).join("/"), readFileSync(p, "utf8")));
    }
  };
  walk(join(root, "src"));
  return out;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const issues = scanAll();
  console.log(JSON.stringify(issues, null, 1));
  process.exit(issues.length ? 1 : 0);
}
