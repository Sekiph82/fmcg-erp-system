"use client";
/* eslint-disable @next/next/no-img-element -- blob/data URLs and the shared brand host; next/image adds nothing here */
// Public employee business card (M42, no login). Layout follows the owner's POVU card (github.com/Sekiph82/SekipHayit):
// cover video, large portrait, Save contact + Share, Call / WhatsApp / E-mail tiles, tabs. The person's own data
// (name, title, work phone/e-mail, photo) comes from the ERP; cover, logo, videos, gallery and catalogue are the shared
// POVU brand content (assets_base). A closed card shows only "no longer valid".
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { publicCardApi, type PublicCard } from "@/lib/businessCards";

type Lang = "en" | "sw" | "tr";
const LANGS: Lang[] = ["en", "sw", "tr"];
const LANG_NAME: Record<Lang, string> = { en: "English", sw: "Kiswahili", tr: "Türkçe" };
const T: Record<string, Record<Lang, string>> = {
  save: { en: "Save Contact", sw: "Hifadhi Mawasiliano", tr: "Rehbere Kaydet" },
  call: { en: "Call", sw: "Piga simu", tr: "Ara" },
  email: { en: "Email", sw: "Barua pepe", tr: "E-posta" },
  contact: { en: "Contact", sw: "Mawasiliano", tr: "İletişim" },
  company: { en: "Company", sw: "Kampuni", tr: "Şirket" },
  videos: { en: "Videos", sw: "Video", tr: "Videolar" },
  gallery: { en: "Gallery", sw: "Picha", tr: "Galeri" },
  catalogs: { en: "Catalogs", sw: "Katalogi", tr: "Kataloglar" },
  mobile: { en: "Mobile", sw: "Simu", tr: "Cep Telefonu" },
  position: { en: "Position", sw: "Nafasi", tr: "Görev" },
  website: { en: "Website", sw: "Tovuti", tr: "Web Sitesi" },
  view: { en: "View", sw: "Tazama", tr: "Görüntüle" },
  download: { en: "Download", sw: "Pakua", tr: "İndir" },
  catalogue: { en: "Povu Product Catalogue", sw: "Katalogi ya Bidhaa za Povu", tr: "Povu Ürün Kataloğu" },
  pdf: { en: "PDF · 52 pages · 12 MB", sw: "PDF · kurasa 52 · MB 12", tr: "PDF · 52 sayfa · 12 MB" },
  copied: { en: "Copied", sw: "Imenakiliwa", tr: "Kopyalandı" },
  linkCopied: { en: "Link copied", sw: "Kiungo kimenakiliwa", tr: "Link kopyalandı" },
  gone: { en: "This card is no longer valid.", sw: "Kadi hii haitumiki tena.", tr: "Bu kartvizit artık geçerli değil." },
  loading: { en: "Loading…", sw: "Inapakia…", tr: "Yükleniyor…" },
  retry: { en: "Please try again later.", sw: "Tafadhali jaribu tena baadaye.", tr: "Lütfen daha sonra tekrar deneyin." },
  close: { en: "Close", sw: "Funga", tr: "Kapat" },
};
const VIDEOS: { file: string; poster: string; cap: Record<Lang, string> }[] = [
  { file: "video3.mp4", poster: "video3.jpg", cap: { en: "Povu · Mascots at work", sw: "Povu · Wahusika kazini", tr: "Povu · Maskotlar iş başında" } },
  { file: "video1.mp4?v=2", poster: "video1.jpg", cap: { en: "Povu · Power Meets Care", sw: "Povu · Power Meets Care", tr: "Povu · Power Meets Care" } },
  { file: "video2.mp4?v=2", poster: "video2.jpg", cap: { en: "Povu Kenya · Digital Twin", sw: "Povu Kenya · Pacha wa Kidijitali", tr: "Povu Kenya · Dijital İkiz" } },
];
const GALLERY: { i: number; cap: Record<Lang, string> }[] = [
  { i: 7, cap: { en: "Povu mascots", sw: "Wahusika wa Povu", tr: "Povu maskotları" } },
  { i: 8, cap: { en: "Povu dolphin", sw: "Pomboo wa Povu", tr: "Povu yunusu" } },
  { i: 9, cap: { en: "Povu logo", sw: "Nembo ya Povu", tr: "Povu logosu" } },
  { i: 10, cap: { en: "Povu dolphin & logo", sw: "Pomboo na nembo ya Povu", tr: "Povu yunusu ve logo" } },
  { i: 11, cap: { en: "Mascots in Kenyan attire", sw: "Wahusika kwa mavazi ya Kenya", tr: "Kenya kıyafetli maskotlar" } },
  { i: 12, cap: { en: "Against dirt and germs", sw: "Dhidi ya uchafu na vijidudu", tr: "Kirlere ve mikroplara karşı" } },
  { i: 13, cap: { en: "Povu dolphin in the savanna", sw: "Pomboo wa Povu mbugani", tr: "Savanada Povu yunusu" } },
  { i: 14, cap: { en: "Povu yeti", sw: "Yeti wa Povu", tr: "Povu yetisi" } },
  { i: 1, cap: { en: "Povu product family", sw: "Familia ya bidhaa za Povu", tr: "Povu ürün ailesi" } },
  { i: 2, cap: { en: "Power Meets Care · Made in Kenya", sw: "Power Meets Care · Imetengenezwa Kenya", tr: "Power Meets Care · Made in Kenya" } },
  { i: 3, cap: { en: "Povu Kenya campus", sw: "Kampasi ya Povu Kenya", tr: "Povu Kenya kampüsü" } },
  { i: 4, cap: { en: "Povu Glass Deck", sw: "Povu Glass Deck", tr: "Povu Glass Deck" } },
  { i: 5, cap: { en: "Smart production", sw: "Uzalishaji wa kisasa", tr: "Akıllı üretim" } },
  { i: 6, cap: { en: "Wet processing", sw: "Usindikaji wa majimaji", tr: "Islak proses" } },
];
const TABS = ["contact", "company", "videos", "gallery", "catalogs"] as const;

const Ico = {
  call: <svg viewBox="0 0 24 24" fill="currentColor"><path d="M6.6 10.8a15 15 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2Z" /></svg>,
  wa: <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm4.5 12.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3c-.2.3-.9.9-.9 2.2s1 2.6 1.1 2.8c.1.2 1.9 2.9 4.6 4 1.7.7 2.4.8 3.2.7.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2l-.5-.2Z" /></svg>,
  mail: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></svg>,
  web: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" /></svg>,
  save: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="9" cy="8" r="4" /><path d="M2 21c0-4 3-7 7-7s7 3 7 7M19 8v6M16 11h6" /></svg>,
  share: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="m8.6 10.5 6.8-4M8.6 13.5l6.8 4" /></svg>,
  copy: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="12" height="12" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" /></svg>,
  user: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-7 8-7s8 3 8 7" /></svg>,
};

export default function BusinessCardPage() {
  const slug = String(useParams().slug ?? "");
  const [card, setCard] = useState<PublicCard | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "gone" | "error">("loading");
  const [lang, setLang] = useState<Lang>("en");
  const [tab, setTab] = useState<(typeof TABS)[number]>("contact");
  const [toast, setToast] = useState<string | null>(null);
  const [lb, setLb] = useState<number | null>(null);
  const t = (k: string) => T[k]?.[lang] ?? k;

  useEffect(() => {
    try { const saved = localStorage.getItem("kv-lang") as Lang | null; if (saved && LANGS.includes(saved)) setLang(saved); } catch { /* private mode */ }
    fetch(`${publicCardApi}/${encodeURIComponent(slug)}`)
      .then(async (r) => {
        if (r.status === 404) return setState("gone");
        if (!r.ok) return setState("error");
        const c = (await r.json()) as PublicCard;
        setCard(c); setState("ok");
        document.title = `${c.name} · POVU`;
      })
      .catch(() => setState("error"));
  }, [slug]);

  useEffect(() => { if (lb === null) return; const k = (e: KeyboardEvent) => { if (e.key === "Escape") setLb(null); if (e.key === "ArrowRight") setLb((i) => ((i ?? 0) + 1) % GALLERY.length); if (e.key === "ArrowLeft") setLb((i) => ((i ?? 0) - 1 + GALLERY.length) % GALLERY.length); }; window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k); }, [lb]);

  const nextLang = () => { const l = LANGS[(LANGS.indexOf(lang) + 1) % LANGS.length]; setLang(l); try { localStorage.setItem("kv-lang", l); } catch { /* ignore */ } };
  const say = (m: string) => { setToast(m); window.setTimeout(() => setToast(null), 1800); };
  const copy = (txt: string, msg: string) => navigator.clipboard?.writeText(txt).then(() => say(msg), () => say(txt)) ?? say(txt);
  const share = () => { const url = location.href.split("#")[0]; if (navigator.share) navigator.share({ title: `${card?.name} · POVU`, url }).catch(() => undefined); else copy(url, t("linkCopied")); };
  const A = (f: string) => `${card?.assets_base}/${f}`;

  return (
    <main className="kv">
      <style>{CSS}</style>
      {state !== "ok" || !card ? (
        <div className="kv-msg" role={state === "gone" || state === "error" ? "alert" : "status"}>
          <span className="kv-msg-logo">POVU</span>
          <p>{state === "loading" ? t("loading") : state === "gone" ? t("gone") : t("retry")}</p>
          {state === "gone" && <p className="kv-small">{T.gone.sw} · {T.gone.tr}</p>}
        </div>
      ) : (
        <div className="kv-card">
          <header className="kv-cover" style={{ backgroundImage: `url(${A("kapak.jpg?v=2")})` }}>
            <video className="kv-cover-vid" src={A("kapak.mp4?v=2")} poster={A("kapak.jpg?v=2")} autoPlay muted loop playsInline preload="auto" aria-hidden="true" />
            <div className="kv-topbar">
              <button className="kv-pill" type="button" onClick={nextLang} aria-label="Language / Lugha / Dil">{Ico.web}<span>{LANG_NAME[LANGS[(LANGS.indexOf(lang) + 1) % LANGS.length]]}</span></button>
              <span className="kv-pill kv-brand"><img src={A("logo.webp")} alt="Povu" /></span>
            </div>
          </header>

          <section className="kv-who">
            <div className="kv-avatar">
              {card.has_photo ? <img src={`${publicCardApi}/${card.slug}/photo`} alt={card.name} width={720} height={720} /> : <span className="kv-initials">{card.name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase()}</span>}
            </div>
            <h1>{card.name}</h1>
            <p className="kv-org">Povu</p>
            <p className="kv-role">{card.title}</p>
          </section>

          <div className="kv-body">
            <div className="kv-save-row">
              <a className="kv-save" href={`${publicCardApi}/${card.slug}.vcf`}>{Ico.save}<span>{t("save")}</span></a>
              <button className="kv-share" type="button" onClick={share} aria-label="Share">{Ico.share}</button>
            </div>

            <nav className="kv-tiles">
              {card.phone && <a className="kv-tile" href={`tel:${card.phone.replace(/\s/g, "")}`}><i className="c-call">{Ico.call}</i>{t("call")}</a>}
              {card.whatsapp && <a className="kv-tile" href={`https://wa.me/${card.whatsapp}`} target="_blank" rel="noopener noreferrer"><i className="c-wa">{Ico.wa}</i>WhatsApp</a>}
              {card.email && <a className="kv-tile" href={`mailto:${card.email}`}><i className="c-mail">{Ico.mail}</i>{t("email")}</a>}
            </nav>

            <div className="kv-tabs" role="tablist">
              {TABS.map((k) => (
                <button key={k} type="button" role="tab" id={`kv-t-${k}`} aria-controls={`kv-p-${k}`} aria-selected={tab === k} className="kv-tab" onClick={() => setTab(k)}>{t(k)}</button>
              ))}
            </div>

            {tab === "contact" && (
              <section className="kv-panel" id="kv-p-contact" role="tabpanel" aria-labelledby="kv-t-contact">
                {card.phone && (
                  <div className="kv-item"><i className="c-call">{Ico.call}</i>
                    <a className="kv-txt" href={`tel:${card.phone.replace(/\s/g, "")}`}><small>{t("mobile")}</small><b>{card.phone}</b></a>
                    {card.whatsapp && <a className="kv-mini wa" href={`https://wa.me/${card.whatsapp}`} target="_blank" rel="noopener noreferrer" aria-label="WhatsApp">{Ico.wa}</a>}
                  </div>
                )}
                {card.email && (
                  <div className="kv-item"><i className="c-mail">{Ico.mail}</i>
                    <a className="kv-txt" href={`mailto:${card.email}`}><small>{t("email")}</small><b>{card.email}</b></a>
                    <button className="kv-mini" type="button" onClick={() => copy(card.email!, t("copied"))} aria-label="Copy">{Ico.copy}</button>
                  </div>
                )}
                {!card.phone && !card.email && <div className="kv-item"><i className="c-web">{Ico.web}</i><a className="kv-txt" href={card.website} target="_blank" rel="noopener noreferrer"><small>{t("website")}</small><b>www.povu.com</b></a></div>}
              </section>
            )}

            {tab === "company" && (
              <section className="kv-panel" id="kv-p-company" role="tabpanel" aria-labelledby="kv-t-company">
                <div className="kv-logo-box"><img src={A("logo.webp")} alt="Povu" /></div>
                <div className="kv-item"><i className="c-call">{Ico.user}</i><div className="kv-txt"><small>{t("position")}</small><b>{card.title}</b></div></div>
                <a className="kv-item" href={card.website} target="_blank" rel="noopener noreferrer"><i className="c-web">{Ico.web}</i><div className="kv-txt"><small>{t("website")}</small><b>www.povu.com</b></div></a>
              </section>
            )}

            {tab === "videos" && (
              <section className="kv-panel" id="kv-p-videos" role="tabpanel" aria-labelledby="kv-t-videos">
                {VIDEOS.map((v) => (
                  <figure className="kv-vplay" key={v.file}><video src={A(v.file)} poster={A(v.poster)} controls playsInline preload="none" /><figcaption>{v.cap[lang]}</figcaption></figure>
                ))}
              </section>
            )}

            {tab === "gallery" && (
              <section className="kv-panel" id="kv-p-gallery" role="tabpanel" aria-labelledby="kv-t-gallery">
                <div className="kv-grid">
                  {GALLERY.map((g, n) => (
                    <button key={g.i} type="button" className="kv-gi" onClick={() => setLb(n)} aria-label={g.cap[lang]}><img src={A(`galeri/${g.i}-k.jpg`)} alt={g.cap[lang]} loading="lazy" /></button>
                  ))}
                </div>
              </section>
            )}

            {tab === "catalogs" && (
              <section className="kv-panel" id="kv-p-catalogs" role="tabpanel" aria-labelledby="kv-t-catalogs">
                <div className="kv-cat">
                  <a className="kv-cat-cover" href={A("katalog/POVU_Catalogue.pdf")} target="_blank" rel="noopener noreferrer"><img src={A("katalog/kapak.jpg")} alt="" loading="lazy" /></a>
                  <div className="kv-cat-body">
                    <b>{t("catalogue")}</b><small>{t("pdf")}</small>
                    <div className="kv-cat-btns">
                      <a className="kv-cat-btn" href={A("katalog/POVU_Catalogue.pdf")} target="_blank" rel="noopener noreferrer">{t("view")}</a>
                      <a className="kv-cat-btn primary" href={A("katalog/POVU_Catalogue.pdf")} download="POVU_Catalogue.pdf">{t("download")}</a>
                    </div>
                  </div>
                </div>
              </section>
            )}

            <footer>Povu · www.povu.com</footer>
          </div>
        </div>
      )}
      {toast && <div className="kv-toast" role="status">{toast}</div>}
      {lb !== null && card && (
        <div className="kv-lb" role="dialog" aria-modal="true" aria-label={t("gallery")} onClick={(e) => e.target === e.currentTarget && setLb(null)}>
          <button className="kv-lb-x" type="button" onClick={() => setLb(null)} aria-label={t("close")}>×</button>
          <img src={A(`galeri/${GALLERY[lb].i}.jpg`)} alt={GALLERY[lb].cap[lang]} />
          <p>{GALLERY[lb].cap[lang]}</p>
          <div className="kv-lb-nav">
            <button type="button" onClick={() => setLb((lb - 1 + GALLERY.length) % GALLERY.length)} aria-label="Previous">‹</button>
            <span>{lb + 1} / {GALLERY.length}</span>
            <button type="button" onClick={() => setLb((lb + 1) % GALLERY.length)} aria-label="Next">›</button>
          </div>
        </div>
      )}
    </main>
  );
}

const CSS = `
.kv{--bg:#0e1620;--surface:#17222e;--surface-2:#1f2c3a;--line:#2a394a;--fg:#f2f6fa;--muted:#8ea2b5;--blue:#1670b8;--sky:#3fb4ec;--wa:#25d366;
  min-height:100vh;background:var(--bg);color:var(--fg);font:15px/1.5 "Plus Jakarta Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased;color-scheme:dark}
.kv *{box-sizing:border-box}
.kv img{max-width:100%}
.kv-card{max-width:480px;margin:0 auto;padding-bottom:calc(32px + env(safe-area-inset-bottom,0px))}
.kv-cover{position:relative;height:230px;background:#cfd6dc center 30%/cover no-repeat}
.kv-cover-vid{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 30%}
@media (prefers-reduced-motion:reduce){.kv-cover-vid{display:none}}
.kv-cover::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,22,32,.35) 0%,rgba(14,22,32,0) 35%,rgba(14,22,32,.25) 70%,var(--bg) 100%)}
.kv-topbar{position:absolute;z-index:2;left:16px;right:16px;top:calc(14px + env(safe-area-inset-top,0px));display:flex;justify-content:space-between;align-items:center}
.kv-pill{display:inline-flex;align-items:center;gap:8px;height:38px;padding:0 14px;border-radius:999px;background:rgba(14,22,32,.72);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.12);color:var(--fg);font:600 13px/1 inherit;font-family:inherit;cursor:pointer}
.kv-pill svg{width:16px;height:16px}
.kv-brand{background:rgba(255,255,255,.92);padding:0 10px;border:0;cursor:default}
.kv-brand img{height:30px;width:auto;display:block}
.kv-who{position:relative;z-index:3;margin-top:-104px;padding-inline:20px;text-align:center}
.kv-avatar{width:min(211px,calc(100vw - 48px));aspect-ratio:1;margin:0 auto;border-radius:50%;padding:6px;background:linear-gradient(140deg,var(--sky),var(--blue) 55%,var(--bg))}
.kv-avatar img,.kv-initials{display:grid;place-items:center;width:100%;height:100%;border-radius:50%;object-fit:cover;border:5px solid var(--bg)}
.kv-initials{background:var(--surface-2);font-size:64px;font-weight:800;color:var(--sky)}
.kv h1{margin:16px 0 0;font-size:30px;line-height:1.15;font-weight:800;letter-spacing:-.02em;text-wrap:balance}
.kv-org{margin:6px 0 0;font-size:16px;font-weight:700;color:var(--sky)}
.kv-role{margin:2px 0 0;color:var(--muted);font-weight:500}
.kv-body{padding-inline:16px;margin-top:22px;display:flex;flex-direction:column;gap:14px}
.kv-save-row{display:flex;gap:10px}
.kv-save{flex:1;display:flex;align-items:center;justify-content:center;gap:10px;height:56px;border-radius:16px;background:linear-gradient(135deg,var(--blue),#2391d8);color:#fff;font-weight:700;font-size:16px;text-decoration:none;box-shadow:0 12px 28px -12px rgba(35,145,216,.75)}
.kv-share{width:56px;height:56px;display:grid;place-items:center;border-radius:16px;background:var(--surface-2);border:1px solid var(--line);color:var(--fg);cursor:pointer}
.kv-save svg,.kv-share svg{width:22px;height:22px}
.kv-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));gap:10px}
.kv-tile{display:flex;align-items:center;justify-content:center;gap:7px;height:52px;padding:0 4px;white-space:nowrap;border-radius:16px;background:var(--surface);border:1px solid var(--line);color:var(--fg);text-decoration:none;font-size:13px;font-weight:600}
.kv-tile i,.kv-item>i{flex:none;border-radius:50%;display:grid;place-items:center;color:#fff}
.kv-tile i{width:30px;height:30px}.kv-tile i svg{width:16px;height:16px}
.c-call{background:var(--blue)}.c-wa{background:var(--wa)}.c-mail{background:#e2574c}.c-web{background:#5865c9}
.kv-tabs{display:flex;gap:8px;margin-top:6px;overflow-x:auto;scrollbar-width:none}
.kv-tab{flex:none;height:40px;padding:0 12px;border-radius:12px;border:1px solid var(--line);background:var(--surface);color:var(--muted);font:600 13px/1 inherit;font-family:inherit;cursor:pointer;white-space:nowrap}
.kv-tab[aria-selected="true"]{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.kv-panel{display:flex;flex-direction:column;gap:10px}
.kv-item{display:flex;align-items:center;gap:14px;padding:14px;border-radius:16px;background:var(--surface);border:1px solid var(--line);color:var(--fg);text-decoration:none;min-width:0}
.kv-item>i{width:42px;height:42px}.kv-item>i svg{width:20px;height:20px}
.kv-txt{flex:1;min-width:0;color:inherit;text-decoration:none}
.kv-txt small{display:block;font-size:12px;font-weight:600;color:var(--muted)}
.kv-txt b{display:block;font-weight:600;font-size:15px;overflow-wrap:anywhere}
.kv-mini{flex:none;width:40px;height:40px;border-radius:12px;display:grid;place-items:center;background:var(--surface-2);border:1px solid var(--line);color:var(--fg);cursor:pointer}
.kv-mini svg{width:19px;height:19px}.kv-mini.wa{background:var(--wa);border-color:var(--wa);color:#fff}
.kv-logo-box{display:grid;place-items:center;padding:18px;border-radius:16px;background:#fff}.kv-logo-box img{height:84px;width:auto}
.kv-vplay{margin:0;display:flex;flex-direction:column;gap:8px}
.kv-vplay video{display:block;width:100%;aspect-ratio:16/9;border-radius:16px;background:var(--surface)}
.kv-vplay figcaption{font-size:14px;font-weight:600;color:var(--muted)}
.kv-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.kv-gi{all:unset;cursor:pointer;display:block;border-radius:14px;overflow:hidden;background:var(--surface);aspect-ratio:1}
.kv-gi img{display:block;width:100%;height:100%;object-fit:cover}
.kv-cat{display:flex;gap:14px;padding:12px;border-radius:16px;background:var(--surface);border:1px solid var(--line);align-items:center}
.kv-cat-cover{flex:none;width:96px;border-radius:8px;overflow:hidden}.kv-cat-cover img{display:block;width:100%}
.kv-cat-body{flex:1;min-width:0;display:flex;flex-direction:column;gap:4px}.kv-cat-body small{color:var(--muted);font-size:13px}
.kv-cat-btns{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.kv-cat-btn{display:inline-flex;align-items:center;height:38px;padding:0 12px;border-radius:10px;border:1px solid var(--line);background:var(--surface-2);color:var(--fg);text-decoration:none;font-weight:600;font-size:13px}
.kv-cat-btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}
.kv footer{margin-top:10px;text-align:center;font-size:12px;color:var(--muted)}
.kv-toast{position:fixed;left:50%;bottom:calc(24px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);background:var(--fg);color:var(--bg);padding:10px 16px;border-radius:12px;font-weight:600;font-size:14px;z-index:9}
.kv-lb{position:fixed;inset:0;z-index:20;background:rgba(5,9,14,.97);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:56px 12px 24px}
.kv-lb img{max-width:100%;max-height:68vh;border-radius:12px;object-fit:contain}.kv-lb p{margin:0;font-weight:600;text-align:center}
.kv-lb-x{position:absolute;top:12px;right:12px}
.kv-lb-x,.kv-lb-nav button{width:44px;height:44px;border-radius:50%;border:1px solid var(--line);background:var(--surface-2);color:var(--fg);font-size:22px;cursor:pointer}
.kv-lb-nav{display:flex;align-items:center;gap:18px;color:var(--muted)}
.kv-msg{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:24px;text-align:center}
.kv-msg-logo{font-size:28px;font-weight:800;letter-spacing:.08em;color:var(--sky)}.kv-msg p{margin:0;font-size:18px;font-weight:600}.kv-small{font-size:13px!important;color:var(--muted)}
.kv :focus-visible{outline:2px solid var(--sky);outline-offset:2px}
`;
