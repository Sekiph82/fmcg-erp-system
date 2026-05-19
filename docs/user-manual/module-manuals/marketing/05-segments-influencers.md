# Customer Segments & Influencers

---

## Customer Segments

**Route:** `/dashboard/marketing?tab=segments`  
**Permission required:** `marketing.view`

### What It Does

The Segments tab classifies customers into trade channel segments for targeted marketing. Each segment has a relationship status, loyalty tier, and acquisition source. Segments allow campaign targeting and promotion eligibility rules to be applied at the channel level.

![Segments tab](../../../screenshots/captured/module-ui/marketing/marketing/segments-tab.png)
*Customer Segments tab showing segment classifications, relationship status, and loyalty tier.*

### Segment Types (Trade Channel)

| Value | Label |
|---|---|
| `RETAIL` | General Retail |
| `WHOLESALE` | Wholesale |
| `KIOSK` | Kiosk / Duka |
| `SUPERMARKET` | Supermarket |
| `DISTRIBUTOR` | Distributor |
| `HORECA` | Hotels / Restaurants / Catering |
| `PHARMACY` | Pharmacy |
| `MODERN_TRADE` | Modern Trade Chain |
| `GENERAL_TRADE` | General Trade |
| `ONLINE` | Online / E-Commerce |

### Relationship Status

| Value | Meaning |
|---|---|
| `PROSPECT` | New, not yet active |
| `ACTIVE` | Regular buyer |
| `AT_RISK` | Declining frequency |
| `DORMANT` | Not purchased recently |
| `CHURNED` | Lost customer |
| `VIP` | Key account |

### Loyalty Tiers (Marketing View)

| Value |
|---|
| `BRONZE` |
| `SILVER` |
| `GOLD` |
| `PLATINUM` |
| `NONE` |

### Acquisition Sources

| Value | Label |
|---|---|
| `ADS` | Paid Advertising |
| `INFLUENCER` | Influencer Campaign |
| `ORGANIC` | Organic / Word of Mouth |
| `REFERRAL` | Customer Referral |
| `MARKETPLACE` | Online Marketplace |
| `DIRECT` | Direct Sales |
| `SOCIAL` | Social Media |
| `FIELD_SALES` | Field Sales Team |
| `EVENT` | Event / Exhibition |
| `OTHER` | Other |

---

## Influencers

**Route:** `/dashboard/marketing?tab=influencers`  
**Permission required:** `marketing.view`

### What It Does

The Influencers tab manages the influencer registry — profiles, platform, follower counts, engagement rates, and content assignment history.

![Influencers tab](../../../screenshots/captured/module-ui/marketing/marketing/influencers-tab.png)
*Influencers tab showing influencer profiles, platforms, follower counts, and content assignments.*

### Influencer Platforms

| Value | Label |
|---|---|
| `INSTAGRAM` | Instagram |
| `TIKTOK` | TikTok |
| `YOUTUBE` | YouTube |
| `FACEBOOK` | Facebook |
| `X` | X (Twitter) |
| `OTHER` | Other |

### Influencer Status

| Value | Meaning |
|---|---|
| `PROSPECT` | Under evaluation |
| `ACTIVE` | Active partnership |
| `INACTIVE` | Paused |
| `BLOCKED` | Blocked from partnership |
