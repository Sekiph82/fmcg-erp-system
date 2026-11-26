"use client";
// M46 CMS block renderer, shared by the public site (/site/...) and the staff preview.
// Blocks are data, never HTML: every string is rendered as React text (escaped). Inline formatting is limited to
// **bold** and [label](url); URLs were validated by the server (site path or http/https only) and are checked again here.
import React from "react";
import { API_ORIGIN } from "@/lib/api";

export type Theme = { brand_color: string; text_color: string; background: string; accent: string; font: string; radius: string };
export type Block = Record<string, any> & { type: string; id?: string };

const safe = (u: string) => (/^\/(?!\/)/.test(u) || /^https?:\/\//i.test(u) ? u : "#");

export function siteHref(u: string, base: string) {
  return u.startsWith("/") ? `${base}${u === "/" ? "" : u}` : u;
}

export function Inline({ text, base }: { text: string; base: string }) {
  const out: React.ReactNode[] = [];
  const re = /\*\*(.+?)\*\*|\[([^\]]{1,120})\]\(([^)\s]{1,400})\)/g;
  let last = 0; let m: RegExpExecArray | null; let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1] !== undefined) out.push(<strong key={i++}>{m[1]}</strong>);
    else out.push(<a key={i++} href={siteHref(safe(m[3]), base)} className="underline" rel={m[3].startsWith("/") ? undefined : "noopener noreferrer"}>{m[2]}</a>);
    last = re.lastIndex;
  }
  if (last < text.length) out.push(text.slice(last));
  return <>{out.map((x, k) => (typeof x === "string" ? x.split("\n").flatMap((line, j) => (j ? [<br key={`${k}-${j}`} />, line] : [line])) : x))}</>;
}

function Cta({ cta, theme, base, siteKey }: { cta: { key: string; label: string; href: string; style: string }; theme: Theme; base: string; siteKey: string }) {
  const click = () => { fetch(`${API_ORIGIN}/api/v1/public/cms/site/${siteKey}/cta/${cta.key}/click`, { method: "POST", keepalive: true }).catch(() => {}); };
  const style = cta.style === "link" ? { color: theme.brand_color } : cta.style === "secondary"
    ? { border: `2px solid ${theme.brand_color}`, color: theme.brand_color, borderRadius: +theme.radius }
    : { background: theme.brand_color, color: "#fff", borderRadius: +theme.radius };
  return <a href={siteHref(safe(cta.href), base)} onClick={click} style={style}
    className={cta.style === "link" ? "underline font-medium" : "inline-block px-5 py-3 font-semibold"}>{cta.label}</a>;
}

function Media({ b }: { b: Block }) {
  const [meta, setMeta] = React.useState<{ title: string; captions: string[]; mime: string } | null | "denied">(null);
  const sent = React.useRef(false);
  React.useEffect(() => {
    fetch(`${API_ORIGIN}/api/v1/public/cms/media/${b.media_id}`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : "denied")).then(setMeta).catch(() => setMeta("denied"));
  }, [b.media_id]);
  const view = (e: React.SyntheticEvent<HTMLMediaElement>) => {
    const s = Math.round(e.currentTarget.currentTime);
    if (sent.current && s < 5) return;
    sent.current = true;
    fetch(`${API_ORIGIN}/api/v1/public/cms/media/${b.media_id}/view`, { method: "POST", credentials: "include", keepalive: true,
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ seconds: s }) }).catch(() => {});
  };
  if (meta === null) return <p className="text-sm opacity-70">Loading media…</p>;
  if (meta === "denied") return <p className="text-sm border rounded p-3">This media is for signed-in members. <a className="underline" href="/portal/login">Sign in</a></p>;
  const src = `${API_ORIGIN}/api/v1/public/cms/media/${b.media_id}/file`;
  const tracks = meta.captions.map((l) => <track key={l} kind="captions" srcLang={l} label={l.toUpperCase()} src={`${API_ORIGIN}/api/v1/public/cms/media/${b.media_id}/captions/${l}`} />);
  return b.type === "video"
    ? <video controls playsInline preload="metadata" crossOrigin="use-credentials" className="w-full rounded" aria-label={b.title || meta.title} onPause={view} onEnded={view}><source src={src} type={meta.mime} />{tracks}</video>
    : <audio controls preload="metadata" crossOrigin="use-credentials" className="w-full" aria-label={b.title || meta.title} onPause={view} onEnded={view}><source src={src} type={meta.mime} />{tracks}</audio>;
}

export function SiteBlocks({ blocks, theme, base, siteKey }: { blocks: Block[]; theme: Theme; base: string; siteKey: string }) {
  const one = (b: Block, i: number): React.ReactNode => {
    const k = b.id ?? i;
    switch (b.type) {
      case "hero":
        return <section key={k} className="py-10 sm:py-16 text-center space-y-4" style={b.image ? { backgroundImage: `url(${JSON.stringify(safe(b.image))})`, backgroundSize: "cover" } : {}}>
          <h1 className="text-3xl sm:text-5xl font-bold break-words">{b.title}</h1>
          {b.subtitle && <p className="text-lg opacity-80 break-words"><Inline text={b.subtitle} base={base} /></p>}
          {b.cta && <Cta cta={b.cta} theme={theme} base={base} siteKey={siteKey} />}</section>;
      case "heading": {
        const H = (`h${b.level}` as "h1" | "h2" | "h3");
        return <H key={k} className={`${b.level === 1 ? "text-3xl" : b.level === 2 ? "text-2xl" : "text-xl"} font-bold mt-6 break-words`}><Inline text={b.text} base={base} /></H>;
      }
      case "text": return <p key={k} className="leading-relaxed my-3 break-words"><Inline text={b.text} base={base} /></p>;
      case "image": return <img key={k} src={safe(b.url)} alt={b.alt} className="max-w-full h-auto rounded my-4" loading="lazy" />;
      case "button": return <p key={k} className="my-4"><a href={siteHref(safe(b.href), base)} className="inline-block px-5 py-3 font-semibold"
        style={{ background: theme.brand_color, color: "#fff", borderRadius: +theme.radius }}>{b.label}</a></p>;
      case "cta": return b.cta ? <p key={k} className="my-4"><Cta cta={b.cta} theme={theme} base={base} siteKey={siteKey} /></p> : null;
      case "divider": return <hr key={k} className="my-6 opacity-30" />;
      case "spacer": return <div key={k} style={{ height: b.height }} />;
      case "form": return <iframe key={k} title={`Form ${b.form_slug}`} src={`/forms/${encodeURIComponent(b.form_slug)}`} className="w-full min-h-[420px] border rounded my-4" />;
      case "embed": return <div key={k}><SiteBlocks blocks={b.blocks ?? []} theme={theme} base={base} siteKey={siteKey} /></div>;
      case "faq": return <section key={k} className="my-6 space-y-2">{b.items.map((q: { q: string; a: string }, j: number) =>
        <details key={j} className="border rounded p-3"><summary className="font-semibold cursor-pointer">{q.q}</summary><p className="mt-2"><Inline text={q.a} base={base} /></p></details>)}</section>;
      case "table": return <div key={k} className="overflow-x-auto my-4"><table className="min-w-full text-sm border">
        <thead><tr>{b.columns.map((c: string) => <th key={c} className="text-left p-2 border-b capitalize">{c.replace(/_/g, " ")}</th>)}</tr></thead>
        <tbody>{b.rows.map((r: Record<string, string>) => <tr key={r.slug} className="border-b">{b.columns.map((c: string, j: number) =>
          <td key={c} className="p-2">{j === 0 && b.link_prefix ? <a className="underline" href={siteHref(`${b.link_prefix}/${r.slug}`, base)}>{r[c]}</a> : String(r[c] ?? "")}</td>)}</tr>)}</tbody></table></div>;
      case "video": case "audio": return <div key={k} className="my-4"><Media b={b} /></div>;
      case "product": return <div key={k} className="border rounded p-3 my-3 flex gap-3 items-center">{b.image && <img src={safe(b.image)} alt={b.name} className="w-20 h-20 object-contain" />}
        <div><p className="font-semibold">{b.name}</p><p className="text-sm opacity-80">{b.size}</p><p className="text-sm font-medium">{b.price}</p></div></div>;
      case "columns": return <div key={k} className="grid grid-cols-1 sm:grid-cols-2 gap-6 my-4">
        <div><SiteBlocks blocks={b.left} theme={theme} base={base} siteKey={siteKey} /></div><div><SiteBlocks blocks={b.right} theme={theme} base={base} siteKey={siteKey} /></div></div>;
      default: return null;
    }
  };
  return <>{blocks.map(one)}</>;
}
