# Digital Ads & Social Media

---

## Digital Advertising

**Route:** `/dashboard/marketing?tab=ads`  
**Permission required:** `marketing.view`

### What It Does

The Ads tab manages digital advertising placements across paid media platforms. It tracks ad spend, impressions, clicks, and conversions per platform and links ad performance to campaigns.

![Ads tab](../../../screenshots/captured/module-ui/marketing/marketing/ads-tab.png)
*Digital Ads tab showing ad records by platform with spend, impressions, clicks, and conversion data.*

### Ad Platforms

| Value | Label |
|---|---|
| `META` | Meta (Facebook / Instagram) |
| `GOOGLE` | Google Ads |
| `TIKTOK` | TikTok Ads |
| `TWITTER` | Twitter / X Ads |
| `LINKEDIN` | LinkedIn Ads |
| `YOUTUBE` | YouTube Ads |
| `OTHER` | Other |

### Ad Record Fields

| Field | Description |
|---|---|
| `platform` | Advertising platform |
| `campaign_id` | Linked marketing campaign |
| `ad_name` | Ad creative name |
| `budget` | Planned ad budget |
| `spend` | Actual spend |
| `impressions` | Number of views |
| `clicks` | Number of clicks |
| `conversions` | Attributed conversions |
| `start_date` / `end_date` | Ad run dates |
| `approval_status` | PENDING · APPROVED · REJECTED |
| `optimizer_status` | PENDING · COMPLETE · APPROVED · ARCHIVED |

---

## Social Media

**Route:** `/dashboard/marketing?tab=social-media`  
**Permission required:** `marketing.view`

### What It Does

The Social Media tab manages organic content — posts, stories, reels, videos, and live sessions. It tracks engagement metrics (likes, comments, shares) and sentiment analysis per post.

![Social Media tab](../../../screenshots/captured/module-ui/marketing/marketing/social-tab.png)
*Social Media tab showing content calendar, post records, and engagement metrics.*

### Content Types

| Value | Label |
|---|---|
| `POST` | Standard post |
| `STORY` | Ephemeral story |
| `REEL` | Short video reel |
| `VIDEO` | Long-form video |
| `LIVE` | Live stream |
| `BLOG` | Blog article |
| `OTHER` | Other |

### Sentiment Scores

| Value | Meaning |
|---|---|
| `POSITIVE` | Positive audience response |
| `NEUTRAL` | Neutral response |
| `NEGATIVE` | Negative feedback |
