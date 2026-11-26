"""Per-network content formats, validation and the capability matrix shown in the UI (M49.S01.T007-T010).

Pure data and rules, no I/O. Every limit comes from coordination/milestones/M48/CAPABILITY_MATRIX.md (organic social
section, checked 2026-11-26); a fact the matrix marks UNVERIFIED carries verified=False. A format that a network's API
does not offer is listed with available=False and the exact reason, so the UI can show it disabled and never offers a
path that does not exist (manual export is the only fallback, and only for what the API cannot do).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings

MB = 1024 * 1024
NETWORKS = ("facebook", "instagram", "linkedin", "tiktok", "x", "youtube")


def cfg(name: str, default):
    v = getattr(settings, name, None)
    return default if v is None or v == "" else v      # declared-but-blank settings fall back to the default


def _f(label, *, media=(0, 0), kinds=("image",), link="no", text=63206, schedule="own", ok=True, reason=None,
       verified=True, note=None, alt=False, **rules):
    """link: no | optional | required. schedule: native | own | none."""
    return {"label": label, "min": media[0], "max": media[1], "kinds": kinds, "link": link, "max_text": text,
            "schedule": schedule, "available": ok, "reason": reason, "verified": verified, "note": note, "alt": alt, **rules}


def _no(label, why):
    return _f(label, ok=False, reason=why, schedule="none")


NO_TEXT_IG = ("Instagram has no text-only post: every container needs an image_url or video_url "
              "(matrix: no text-only container type is documented).")
FORMATS: dict[str, dict[str, dict]] = {
    "facebook": {
        "text": _f("Text post", schedule="native", note="POST /{page}/feed"),
        "link": _f("Link post", link="required", schedule="native"),
        "photo": _f("Photo", media=(1, 1), alt=True, schedule="native"),
        "photos": _f("Multi-photo post", media=(2, 10), alt=True, schedule="native", verified=False,
                     note="Unpublished photos attached with attached_media. The matrix marks this UNVERIFIED and gives no photo limit; 10 is our cap."),
        "video": _f("Video", media=(1, 1), kinds=("video",), schedule="native", resumable=True,
                    note="Resumable Upload API, then POST graph-video.facebook.com/{page}/videos."),
        "reel": _f("Reel", media=(1, 1), kinds=("video",), schedule="native", reel=True, min_sec=3, max_sec=90, min_w=540, min_h=960,
                   ratio=(9, 16), note="At most 30 API-published Reels per 24 h per Page."),
        "story_photo": _f("Story (photo)", media=(1, 1), schedule="none", max_bytes=10 * MB, note="A Story cannot reuse media from a published post."),
        "story_video": _f("Story (video)", media=(1, 1), kinds=("video",), schedule="none", min_sec=3, max_sec=60, min_w=540, min_h=960, ratio=(9, 16)),
    },
    "instagram": {
        "text": _no("Text post", NO_TEXT_IG),
        "link": _no("Link post", "Instagram has no link-post type; links in captions are not clickable."),
        "image": _f("Photo", media=(1, 1), alt=True, text=2200, max_bytes=8 * MB, jpeg=True, ratio_range=(0.8, 1.91), min_w=320, max_w=1440,
                    note="JPEG only, 8 MB, width 320-1440, aspect 4:5 to 1.91:1."),
        "carousel": _f("Carousel (up to 20)", media=(2, 20), kinds=("image", "video"), alt=True, text=2200, max_bytes=8 * MB,
                       note="Reels cannot be carousel items. Counts as one post against the daily quota."),
        "video": _f("Video", media=(1, 1), kinds=("video",), text=2200, max_bytes=300 * MB, resumable=True),
        "reel": _f("Reel", media=(1, 1), kinds=("video",), text=2200, min_sec=3, max_sec=900, max_bytes=300 * MB, reel=True, resumable=True,
                   note="MOV/MP4, 3 s to 15 min, 300 MB, 23-60 fps; optional cover image or frame offset."),
        "story_image": _f("Story (photo)", media=(1, 1), schedule="own", max_bytes=8 * MB, jpeg=True, text=2200),
        "story_video": _f("Story (video)", media=(1, 1), kinds=("video",), min_sec=3, max_sec=60, max_bytes=100 * MB, text=2200),
    },
    "linkedin": {
        "text": _f("Text post", text=3000, note="No native scheduling: our scheduler publishes at the time."),
        "link": _f("Link (article card)", link="required", text=3000,
                   note="LinkedIn does not scrape the URL: title, description and an optional thumbnail image are sent by us."),
        "image": _f("Image", media=(1, 1), alt=True, text=3000),
        "images": _f("Multi-image (2-20)", media=(2, 20), alt=True, text=3000, note="MultiImage API, organic only."),
        "video": _f("Video", media=(1, 1), kinds=("video",), text=3000, min_sec=3, max_sec=1800, max_bytes=500 * MB,
                    note="Videos API; 500 MB is the safe limit (LinkedIn's pages disagree)."),
        "carousel": _no("Carousel", "LinkedIn: organic carousel is not supported (sponsored only). Use Multi-image."),
        "document": _f("Document (PDF/PPT)", ok=False, schedule="none", reason="The Documents API exists, but this release does not build it (not requested for POVU). Post manually."),
    },
    "tiktok": {
        "text": _no("Text post", "TikTok has no text-only endpoint."),
        "link": _no("Link post", "TikTok has no link-post type."),
        "video": _f("Video (Direct Post)", media=(1, 1), kinds=("video",), text=2200, tiktok=True, max_bytes=4096 * MB,
                    note="Needs creator_info, privacy choice and consent. Unaudited apps: private (SELF_ONLY) only."),
        "video_inbox": _f("Video to TikTok drafts (inbox)", media=(1, 1), kinds=("video",), text=2200, tiktok=True, inbox=True, max_bytes=4096 * MB,
                          note="Delivered to the creator's inbox; the creator finishes publishing in the TikTok app. Max 5 pending per 24 h."),
        "photo": _f("Photo post (up to 35)", media=(1, 35), text=90, tiktok=True, photo=True, max_bytes=20 * MB,
                    note="WebP/JPEG, 20 MB each, PULL_FROM_URL from a verified domain only. Title 90, description 4000."),
        "photo_inbox": _f("Photo post to drafts (inbox)", media=(1, 35), text=90, tiktok=True, photo=True, inbox=True, max_bytes=20 * MB),
        "story": _no("Story", "The Content Posting API has no Stories endpoint."),
    },
    "youtube": {
        "video": _f("Video", media=(1, 1), kinds=("video",), text=5000, yt=True, max_bytes=256 * 1024 * MB,
                    note="Resumable upload. Scheduling uses publishAt (video must be private until then)."),
        "short": _f("Short", media=(1, 1), kinds=("video",), text=5000, yt=True, short=True, max_sec=180, max_bytes=256 * 1024 * MB,
                    note="There is no Shorts flag: YouTube classifies a square or vertical video up to 3 minutes as a Short."),
        "text": _no("Community post", "YouTube's posts resource is a pilot for select launch partners (GA planned 2027); not generally usable."),
        "image": _no("Image post", "Only available through the posts-resource pilot; not generally usable."),
        "story": _no("Story", "YouTube has no Stories API."),
    },
    "x": {
        "text": _f("Post", text=280, note="Post length above 280 for premium accounts is UNVERIFIED in the matrix."),
        "link": _f("Post with link", link="required", text=280, note="Pay-per-use: $0.20 for a post containing a URL (vs $0.015)."),
        "image": _f("Images (up to 4)", media=(1, 4), text=280, max_bytes=5 * MB),
        "gif": _f("GIF", media=(1, 1), kinds=("gif",), text=280, max_bytes=15 * MB),
        "video": _f("Video", media=(1, 1), kinds=("video",), text=280, max_bytes=8 * 1024 * MB, max_sec=1200, note="20 min / 8 GB by default; 125 min / 16 GB for Premium (2026-09-01)."),
        "story": _no("Story", "X has no Stories product or endpoint."),
    },
}

def infer_format(network: str, media: list[dict], link: Optional[str]) -> Optional[str]:
    kinds = [m.get("kind") for m in media]
    if network == "x":
        if not media:
            return "link" if link else "text"
        return "video" if "video" in kinds else "gif" if "gif" in kinds else "image"
    if network == "youtube":
        return "video" if "video" in kinds else None
    return None


# ── capabilities (what the UI may offer) ───────────────────────────────

SCHEDULING = {"facebook": "Facebook native scheduling (scheduled_publish_time, 10 min to 30 days) or our scheduler",
              "instagram": "Instagram has no native scheduling: our scheduler publishes at the time",
              "linkedin": "LinkedIn has no native scheduling: our scheduler publishes at the time",
              "tiktok": "TikTok has no scheduling in the Content Posting API: our scheduler submits at the time",
              "youtube": "YouTube publishAt (private until then) or our scheduler",
              "x": "X has no scheduling in the posting API: our scheduler posts at the time"}
INSIGHTS = {"facebook": (True, "GET /{post}/insights (read_insights + pages_read_engagement; Page ANALYZE task)"),
            "instagram": (True, "GET /{media}/insights (instagram_manage_insights)"),
            "linkedin": (True, "organizationalEntityShareStatistics (rw_organization_admin, organic, lifetime per post)"),
            "tiktok": (True, "Display API POST /v2/video/query/ (video.list scope; UNVERIFIED in the matrix)"),
            "youtube": (True, "videos.list statistics (1 quota unit)"),
            "x": (True, "public_metrics on GET /2/tweets (UNVERIFIED in the matrix)")}
# moderation per network: op -> (available, reason or note, verified)
MODERATION = {
    "facebook": {"read": (True, "Webhook feed comments (signed), opted-in Pages only", True),
                 "reply": (True, "POST /{comment}/comments (pages_manage_engagement)", True),
                 "hide": (True, "POST /{comment} is_hidden=true; not on the fetched matrix pages", False),
                 "delete": (True, "DELETE /{comment}", True)},
    "instagram": {"read": (True, "Webhook comments and mentions (signed), opted-in accounts only", True),
                  "reply": (True, "POST /{comment}/replies (instagram_manage_comments)", True),
                  "hide": (True, "POST /{comment} hide=true", True), "delete": (True, "DELETE /{comment}", True)},
    "linkedin": {"read": (True, "Polling GET /rest/socialActions/{post}/comments (r_organization_social_feed, restricted product); no webhook documented", True),
                 "reply": (True, "POST socialActions comments with parentComment (w_organization_social_feed; 1-minute per-member throttle)", True),
                 "hide": (False, "LinkedIn documents no hide/moderation call for comments.", True),
                 "delete": (True, "DELETE comment (organization admin)", True)},
    "tiktok": {"read": (False, "TikTok's Content Posting and Display APIs expose no comments; the TikTok API for Business route is UNVERIFIED. Metrics only.", True),
               "reply": (False, "No comment API available to this integration.", True),
               "hide": (False, "No comment API available to this integration.", True),
               "delete": (False, "No comment API available to this integration.", True)},
    "youtube": {"read": (True, "Polling commentThreads.list (youtube.force-ssl, 1 quota unit); no webhook documented", False),
                "reply": (True, "comments.insert (50 quota units)", True),
                "hide": (True, "comments.setModerationStatus=rejected (50 units); not on the fetched matrix pages", False),
                "delete": (True, "comments.delete (50 units); not on the fetched matrix pages", False)},
    "x": {"read": (True, "Polling GET /2/users/{id}/mentions; UNVERIFIED in the matrix", False),
          "reply": (True, "POST /2/tweets with reply.in_reply_to_tweet_id. Self-serve tiers: only when the original author summoned (mentioned) the account (2026-02-23).", True),
          "hide": (True, "PUT /2/tweets/{id}/hidden on replies to our own posts; UNVERIFIED in the matrix", False),
          "delete": (False, "X only lets you delete your own posts, not other people's comments.", True)},
}


def format_reason(network: str, fmt: str, channel_opts: Optional[dict] = None) -> Optional[str]:
    """Why a format cannot be used right now (None = usable). Includes access-tier restrictions."""
    spec = FORMATS.get(network, {}).get(fmt)
    if spec is None:
        return f"{network} has no {fmt!r} format."
    if not spec["available"]:
        return spec["reason"]
    return None


def capabilities(network: str, channel_opts: Optional[dict] = None) -> dict:
    o = channel_opts or {}
    notes: list[str] = []
    if network == "tiktok" and not cfg("TIKTOK_APP_AUDITED", False):
        notes.append("This TikTok app is not audited: every post is restricted to private (SELF_ONLY) viewing.")
    if network == "youtube" and youtube_private_only(o):
        notes.append("YouTube API project is treated as unverified: uploads are forced to private until the project is verified "
                     "(Google lifted this on 2026-11-02 per the matrix; the safe default stays until the owner confirms).")
    if network == "x":
        notes.append("Activation note: X API is pay-per-use ($0.015 per post, $0.20 per post with a URL, $0.005 per post read). "
                     "Enable only after the owner funds credits and approves the cap.")
    if network == "linkedin":
        notes.append("Community Management API is a vetted product (Development tier, then Standard tier after a screencast review).")
    if network == "instagram" and o.get("ig_login", "instagram") != "facebook":
        notes.append("Resumable video upload (rupload) exists only on the Facebook Login path; this channel uses a public video_url.")
    fm = [{"key": k, "label": s["label"], "available": s["available"], "reason": s["reason"], "verified": s["verified"],
           "note": s["note"], "schedule": s["schedule"], "media_min": s["min"], "media_max": s["max"], "kinds": list(s["kinds"]),
           "alt_text": s["alt"], "link": s["link"], "max_text": s["max_text"]}
          for k, s in FORMATS[network].items()]
    ins = INSIGHTS[network]
    return {"network": network, "formats": fm, "scheduling": SCHEDULING[network], "notes": notes,
            "insights": {"available": ins[0], "note": ins[1]},
            "moderation": {op: {"available": a, "note": n, "verified": v} for op, (a, n, v) in MODERATION[network].items()}}


# ── YouTube restriction ────────────────────────────────────────────────

def youtube_private_only(channel_opts: Optional[dict] = None) -> bool:
    if (channel_opts or {}).get("youtube_project_verified"):
        return False
    return bool(cfg("YOUTUBE_UNVERIFIED_PRIVATE_ONLY", True))


# ── validation ─────────────────────────────────────────────────────────

def _aspect_ok(m: dict, ratio: tuple[int, int]) -> bool:
    w, h = m.get("width"), m.get("height")
    return not (w and h) or abs(w / h - ratio[0] / ratio[1]) < 0.02


def validate(network: str, fmt: str, text: str, media: list[dict], link: Optional[str], fopts: Optional[dict] = None,
             *, scheduled_at: Optional[datetime] = None, channel_opts: Optional[dict] = None, now: Optional[datetime] = None) -> list[str]:
    """Problems that stop a post of this format. Empty = acceptable. Only declared media metadata can be checked here;
    the real file is measured again when it is fetched for upload."""
    fopts = fopts or {}
    spec = FORMATS.get(network, {}).get(fmt)
    if spec is None:
        return [f"{network} has no {fmt!r} format."]
    if not spec["available"]:
        return [spec["reason"]]
    out: list[str] = []
    if len(text) > spec["max_text"]:
        out.append(f"Text is {len(text)} characters; the {spec['label']} format on {network} allows {spec['max_text']}.")
    n = len(media)
    if n < spec["min"] or n > spec["max"]:
        want = f"exactly {spec['max']}" if spec["min"] == spec["max"] else f"{spec['min']} to {spec['max']}"
        out.append(f"{spec['label']} needs {want} media item(s); this post has {n}." if spec["max"] else f"{spec['label']} takes no media.")
    if link and spec["link"] == "no":
        out.append(f"{spec['label']} cannot carry a link on {network}.")
    if spec["link"] == "required" and not link:
        out.append(f"{spec['label']} needs a link.")
    for i, m in enumerate(media, 1):
        k = m.get("kind")
        if k not in spec["kinds"]:
            out.append(f"Media {i} is a {k}; {spec['label']} takes {' or '.join(spec['kinds'])}.")
        if not str(m.get("url", "")).startswith("https://"):
            out.append(f"Media {i} must be a public https URL.")
        if spec.get("max_bytes") and m.get("size_bytes") and m["size_bytes"] > spec["max_bytes"]:
            out.append(f"Media {i} is {m['size_bytes'] // MB} MB; the limit is {spec['max_bytes'] // MB} MB.")
        d = m.get("duration_sec")
        if d is not None and (d < spec.get("min_sec", 0) or d > spec.get("max_sec", 10 ** 9)):
            out.append(f"Media {i} lasts {d}s; {spec['label']} allows {spec.get('min_sec', 0)}-{spec.get('max_sec', '∞')}s.")
        if spec.get("ratio") and not _aspect_ok(m, spec["ratio"]):
            out.append(f"Media {i} is not 9:16.")
        if spec.get("min_w") and m.get("width") and (m["width"] < spec["min_w"] or m.get("height", 10 ** 6) < spec.get("min_h", 0)):
            out.append(f"Media {i} is {m['width']}x{m.get('height')}; minimum {spec['min_w']}x{spec.get('min_h')}.")
        if spec.get("jpeg") and m.get("content_type") and m["content_type"] != "image/jpeg":
            out.append(f"Media {i} must be JPEG on {network}.")
        if spec.get("photo") and m.get("content_type") and m["content_type"] not in ("image/jpeg", "image/webp"):
            out.append(f"Media {i} must be JPEG or WebP for TikTok photo posts.")
        if spec.get("short") and m.get("width") and m.get("height") and m["width"] > m["height"]:
            out.append("A YouTube Short must be square or vertical.")
        if m.get("alt_text") and (not spec["alt"] or len(m["alt_text"]) > 1000):
            out.append(f"Alt text is not supported on media {i} for this format, or longer than 1000 characters." if not spec["alt"]
                       else f"Alt text on media {i} exceeds 1000 characters.")
        if spec.get("ratio_range") and m.get("width") and m.get("height"):
            r = m["width"] / m["height"]
            if not spec["ratio_range"][0] <= r <= spec["ratio_range"][1]:
                out.append(f"Media {i} aspect ratio must be between 4:5 and 1.91:1.")
        if spec.get("max_w") and m.get("width") and not 320 <= m["width"] <= spec["max_w"]:
            out.append(f"Media {i} width must be 320-{spec['max_w']} px.")
    if network == "instagram" and len(re.findall(r"#\w+", text)) > 30:
        out.append("Instagram allows at most 30 hashtags.")
    if network == "instagram" and len(re.findall(r"@\w+", text)) > 20:
        out.append("Instagram allows at most 20 @tags.")
    if network == "instagram" and fmt == "carousel" and any(m.get("kind") == "video" and m.get("is_reel") for m in media):
        out.append("Reels cannot be carousel items.")
    if network == "x":
        kinds = {m.get("kind") for m in media}
        if len(kinds) > 1:
            out.append("X takes up to 4 photos, or 1 GIF, or 1 video; they cannot be mixed.")
        if link and len(text) + 24 > 280:
            out.append("Text plus link (23 characters) is over 280.")
    if network == "facebook" and fopts.get("native_schedule"):
        if not spec["schedule"] == "native":
            out.append(f"{spec['label']} cannot use Facebook native scheduling.")
        if scheduled_at is None:
            out.append("Native scheduling needs a publish time.")
        else:
            now = now or datetime.now(timezone.utc)
            if not now + timedelta(minutes=10) <= scheduled_at <= now + timedelta(days=30):
                out.append("Facebook native scheduling needs a time 10 minutes to 30 days from now.")
    if network == "youtube":
        out += _yt_problems(fopts, scheduled_at, channel_opts, now)
    if network == "linkedin" and fmt == "link" and not (fopts.get("article_title") or "").strip():
        out.append("A LinkedIn link post needs an article title (LinkedIn does not read the page).")
    if network == "tiktok" and fmt.startswith("photo") and not (fopts.get("title") or text.strip()):
        out.append("TikTok photo posts need a title.")
    return out


def _yt_problems(fopts: dict, scheduled_at, channel_opts, now) -> list[str]:
    out = []
    title = (fopts.get("title") or "").strip()
    if not title or len(title) > 100 or re.search(r"[<>]", title):
        out.append("YouTube needs a title of 1-100 characters without < or >.")
    if fopts.get("made_for_kids") is None:
        out.append("State whether the video is made for kids (YouTube requires selfDeclaredMadeForKids).")
    if len(",".join(fopts.get("tags") or [])) > 500:
        out.append("YouTube tags are limited to 500 characters in total.")
    priv = fopts.get("privacy_status", "private")
    if priv not in ("private", "unlisted", "public"):
        out.append("privacy_status must be private, unlisted or public.")
    elif priv != "private" and youtube_private_only(channel_opts):
        out.append("This YouTube API project is unverified: the video can only be uploaded as private.")
    if fopts.get("publish_at"):
        if priv != "private":
            out.append("YouTube publishAt needs privacy_status private (the video turns public at that time).")
        try:
            at = datetime.fromisoformat(str(fopts["publish_at"]).replace("Z", "+00:00"))
            if at.tzinfo is None or at <= (now or datetime.now(timezone.utc)):
                out.append("publish_at must be a future time with a time zone.")
            elif youtube_private_only(channel_opts):
                out.append("An unverified YouTube project cannot schedule a public release (the video would stay private).")
        except ValueError:
            out.append("publish_at must be an ISO 8601 time.")
    return out
