# M48.S00.T002 — Official public API capability and format matrix

**Checked:** 2026-11-26.
- Facts come from the official developer documentation fetched on that date, with each URL listed under its provider.
- Anything that could not be confirmed on an official page is marked **UNVERIFIED** and must be re-checked before an adapter depends on it.
- No account was opened. No real post, ad, payment, signature or AI call was made.

**Purpose:**
- This is the source of truth for the M48.S01 adapters and the M49 social, ads and audience work.
- It is also the evidence that an unsupported format or operation is genuinely unsupported (rubric rule: N/A only with an official source).

## UNVERIFIED facts

**137** facts are marked UNVERIFIED in total.

| Section | UNVERIFIED facts | Weak spots |
|---|---|---|
| Advertising | 34 | TikTok docs render only with JavaScript; KES account currency for Google, LinkedIn and TikTok |
| Organic social | 31 | X metrics fields, TikTok comments/Display API, Facebook multi-photo, YouTube comment scopes |
| Mail, data, signature, payments, AI | 72 | See below |

The 72 in the last row are concentrated in three providers whose official sites could not be read during this check:
- **Pesapal 3.0:** the site returned errors.
- **Safaricom Daraja:** the portal returned 404 or hung.
- **Africa's Talking:** the docs returned 403, so the official Python SDK source was used instead.

These three providers must be re-verified in a browser before their adapters are accepted.

## Key changes since earlier assumptions (affects implementation)

| # | Provider | Change | Impact on POVU |
|---|---|---|---|
| 1 | Google Ads (v26.2) | The developer token was retired on 2026-09-09. Access levels now belong to the Google Cloud project. | Do not require a developer token in new code. |
| 2 | Google Ads | Customer Match is closed to new projects since 2026-04-01. | Audience sync goes through the **Data Manager API** path. |
| 3 | Google Ads | Video campaigns on YouTube cannot be created via the API (reporting only). | The supported paths are Demand Gen video and Performance Max. |
| 4 | TikTok Ads (v1.3) | Manual non-Search Sales, App and Lead campaigns lose create support on 2027-01-01 (Upgraded Smart+ replaces them). Accounts created on or after 2026-01-15 cannot use non-Spark Custom Identity ads. | The adapter must support Spark Ads and Smart+. |
| 5 | Meta (Graph / Marketing v27.0) | Access tiers were renamed Limited (development) and Full (live). Full needs ≥ 500 API calls in 15 days. | — |
| 6 | Meta | `post_impressions*` is deprecated above v25. Some Page Insights metrics were removed on 2026-06-15. | — |
| 7 | YouTube Data v3 | The `videos.insert` quota changed: 1 unit, with its own limit of 100 calls/day since 2026-06-01. Unverified projects are no longer forced to private (since 2026-11-02). | Community `posts` is a pilot only (GA planned 2027). Shorts have no dedicated API. |
| 8 | Instagram | The documents disagree on the publishing limit (50 vs 100 per 24 h). | Read `content_publishing_limit.config.quota_total` at runtime. |
| 9 | LinkedIn (`Linkedin-Version: 202611`) | No native scheduled publish. Organic carousel is unsupported; multi-image (2–20) is supported. | The documents disagree on the video size limit; use 500 MB. Comment scopes are `*_social_feed`. |
| 10 | TikTok Content Posting (v2) | Unaudited apps can post private only. The final post id appears only once the post is public. There is no delete, edit or comment endpoint in this API. | Never mark a post PUBLISHED before `PUBLISH_COMPLETE` (audit finding M48.S01.T005). |
| 11 | X API v2 | Pay-per-use pricing: $0.015 per post, $0.20 for a post with a URL. Quote-posts need Enterprise. Since 2026-02-23, self-serve programmatic replies are allowed only when the replier was summoned. | Whether the Free, Basic and Pro tiers still exist is UNVERIFIED. |
| 12 | AI | OpenAI `gpt-4o` is marked Deprecated (the repo default is `OPENAI_MODEL`). `gemini-flash-latest` is a moving alias; Google recommends a pinned model. | Change both defaults in config. |

## Provider version index

| Group | Provider | Version / header |
|---|---|---|
| Ads | Meta Marketing API | Graph v27.0 (2026-11-04) |
| Ads | Google Ads API | v26.2 (2026-11-11) |
| Ads | LinkedIn Marketing API | `Linkedin-Version: 202611` |
| Ads | TikTok API for Business | v1.3 |
| Social | Facebook Pages / Instagram | Graph v27.0 |
| Social | LinkedIn Posts, Images and Videos APIs | 202611 |
| Social | TikTok Content Posting API | v2 |
| Social | YouTube Data API | v3 |
| Social | X API | v2 |
| Mail and data | Gmail v1, Microsoft Graph v1.0, Google Calendar v3, Snowflake SQL API v2, BigQuery v2, Search Console (webmasters v3 / searchconsole v1) | See the provider sections |
| Signature | DocuSign eSignature | v2.1 |
| Signature | Adobe Acrobat Sign | REST v6 |
| Payments | Pesapal | 3.0 |
| Payments | Flutterwave | v3 |
| Payments | M-Pesa Daraja | OAuth + STK v1 (details UNVERIFIED) |
| AI | Anthropic Messages, OpenAI Chat/Responses, Gemini `generateContent` | See the AI section |

The per-provider sections below each contain:
- the docs fetched;
- the version;
- the documented read and write operations relevant to POVU;
- auth and scopes;
- upload, async, status and reconciliation;
- limits and quotas;
- a **per-format table** (text, link, image, multi-image/carousel, video, reels/shorts, stories) with the exact reason for any unsupported cell;
- access tier or app review;
- Kenya relevance.

For mail, voice, data, signature and payment providers, "content format" does not apply. Their sections list the supported payload and channel types instead.

## Advertising APIs

Capability matrix for POVU (Kenyan FMCG ERP) ad integrations. Real provider actions stay **off by default**; this section only documents what each official API allows.
Legend: **UNVERIFIED** = not confirmed on an official page fetched on 2026-11-26 (best-known value given where useful).

---

### Meta Marketing API (Facebook / Instagram / Messenger / WhatsApp placements)

**Checked: 2026-11-26**

**Doc URLs fetched**
- https://developers.facebook.com/docs/marketing-api/overview
- https://developers.facebook.com/docs/graph-api/changelog
- https://developers.facebook.com/docs/marketing-api/overview/authorization
- https://developers.facebook.com/docs/marketing-api/overview/rate-limiting
- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group
- https://developers.facebook.com/docs/marketing-api/reference/ad-creative
- https://developers.facebook.com/docs/marketing-api/reference/ad-account/advideos
- https://developers.facebook.com/docs/marketing-api/insights
- https://developers.facebook.com/docs/marketing-api/insights/best-practices
- https://developers.facebook.com/docs/marketing-api/audiences/guides/custom-audiences
- https://developers.facebook.com/docs/marketing-api/currencies

**Current version:** Graph API / Marketing API **v27.0** (introduced 2026-11-04, expiry TBD). v26.0 (2026-07-29), v25.0 (2026-02-18, available until 2028-07-29). Changelog notes a Marketing API version auto-upgrade mechanism released 2026-07-29.

#### Documented operations relevant to POVU
| Area | Operation | Endpoint / field |
|---|---|---|
| Campaign | Create | `POST /act_{ad_account_id}/campaigns` (`objective`, `name`, `status`, `special_ad_categories` required – empty array/NONE if none) |
| Campaign | Read / update | `GET /{campaign_id}?fields=…`, `POST /{campaign_id}` |
| Campaign | Delete | `DELETE /{campaign_id}`; or `status=DELETED`/`ARCHIVED` via update |
| Status | Pause / resume | `status` = `ACTIVE` / `PAUSED` (create accepts only ACTIVE/PAUSED). Pausing a campaign makes child ad sets/ads `effective_status=CAMPAIGN_PAUSED` |
| Budget | Campaign (CBO) or ad-set level, not both | `daily_budget`, `lifetime_budget` (integer, currency minor units); `budget_schedule_specs`; `is_adset_budget_sharing_enabled` |
| Ad set | CRUD, budget, schedule, bidding, targeting, placements | Ad set object (overview: holds budget, billing, schedule, bidding, audience). Reels placements via `targeting.facebook_positions` (`facebook_reels`) / `instagram_positions` (`reels`) |
| Ad | CRUD + status | Ad object references a creative |
| Creative | Create (content effectively immutable) | `object_story_spec` with `link_data` / `video_data`; carousel via `link_data.child_attachments`; `asset_feed_spec` (dynamic creative); only `name`, `status`, `adlabels` updatable after create |
| Image upload | Ad image library → `image_hash` | `/act_{id}/adimages` – **UNVERIFIED** (not on fetched pages; referenced via `image_hash` only) |
| Video upload | `POST /act_{id}/advideos` (`source` or `file_url`, chunked `upload_phase=start/transfer/finish/cancel`) | Status via `GET /{video_id}?fields=status` → `video_status` (`processing`, `ready`, `error`, …) |
| Insights | Account/campaign/adset/ad level | `GET /{object}/insights` (fields, breakdowns, `date_preset`, time_range); async `POST …/insights` → `report_run_id` |
| Custom audience | Create customer-list audience | `POST /act_{id}/customaudiences` (`subtype=CUSTOM`, `customer_file_source`) |
| Custom audience | Add / remove / replace members | `POST /{audience_id}/users`, `DELETE /{audience_id}/users`, `POST /{audience_id}/usersreplace` |
| Conversions API | Server-side events | Referenced from Insights docs as the tracking mechanism; endpoint details **UNVERIFIED** (not fetched) |

#### Auth & scopes
- OAuth permissions: `ads_read` (read ads + reports), `ads_management` (read + manage ads). Limited/Standard access is enough when the app manages only its **own** ad account; managing other businesses' accounts needs Advanced/Full access via App Review.
- `business_management`: not described on fetched pages – **UNVERIFIED** (commonly required for Business Manager/system-user flows).
- System users: Limited tier = 1 system user + 1 admin system user; Full tier = 10 system users + 1 admin system user.
- Custom audiences additionally require: ad account linked to the business portfolio (else error 1870050) and **Custom Audience Terms accepted** for the business (else error 1870090).

#### Upload / async / status / reconciliation
- **Video:** chunked resumable upload (`upload_session_id`, `start_offset`/`end_offset`); processing is async – poll `status.video_status` until `ready` before using in a creative (the "must be ready" link to ad creation is an inference – **UNVERIFIED**).
- **Creative dedupe:** duplicate creative payloads return the existing creative ID (natural idempotency for creatives).
- **True state:** read `effective_status` (ACTIVE, PAUSED, DELETED, ARCHIVED, IN_PROCESS, WITH_ISSUES; plus parent-derived states like CAMPAIGN_PAUSED) and `issues_info` – not just the configured `status`.
- **Ad review state:** ad-level review statuses (e.g. `PENDING_REVIEW`, `DISAPPROVED`) – **UNVERIFIED** (ad object page not fetched).
- **Async insights:** `async_status` (Job Not Started/Started/Running/Completed/Failed/Skipped), `async_percent_completion`; `report_run_id` expires after 30 days; async jobs may take up to 1 hour.
- **Batch:** Graph batch requests recommended for throttling mitigation; details **UNVERIFIED** (batch page not fetched).
- **Audience upload batching:** ≤10,000 users per request; multi-request uploads use `session` (`session_id`, `batch_seq`, `last_batch_flag`, `estimated_num_total`).
- **Hashing:** SHA-256 lowercase hex; EMAIL trimmed+lowercased; PHONE digits only with country code (e.g. Kenya `254…`), no leading zeros; `EXTERN_ID`/`MADID` not hashed.
- Insights data refreshes every ~15 min and is stable after 28 days; reach/frequency with breakdowns >13 months old no longer returned by sync queries.

#### Limits / quotas
| Limit | Limited (dev) tier | Full tier |
|---|---|---|
| BUC `ads_management` /ad account/hour | 300 + 40×active ads | 100,000 + 40×active ads |
| BUC `custom_audience` | 5,000 + 40×active audiences | 190,000 + 40×active audiences (cap 700,000) |
| BUC `ads_insights` | 600 + 400×active ads − 0.001×user errors | 190,000 + 400×active ads − 0.001×user errors |
| Score limit (read=1, write=3) | max 60, 300 s decay, 300 s block | max 9,000, 300 s decay, 60 s block |
- Mutation QPS: 100 req/s per app per ad account; same-object edits: 1 per 30 s.
- Spend-cap changes: 10/day per ad account; **ad set budget changes: 4/hour per ad set**; ad creation limited by account daily spend limit.
- Headers to monitor: `X-Business-Use-Case`, `X-Ad-Account-Usage`, `X-FB-Ads-Insights-Throttle`.
- Upload size limits for images/videos: not on fetched pages – **UNVERIFIED** (best known: large video uploads via chunked flow, multi-GB).

#### Creative formats
| Format | Supported via API? | Notes |
|---|---|---|
| Text-only | No | No text-only ad unit; every creative needs image/video/post (link ads carry text in `message`). |
| Link | Yes | `object_story_spec.link_data` (`link`, `message`, `image_hash`, `call_to_action`). |
| Single image | Yes | `link_data.image_hash` / `image_url`. |
| Multi-image / carousel | Yes | `link_data.child_attachments` (each card: name, description, link, image_hash, optional video_id). |
| Video | Yes | `video_data` (`video_id`, thumbnail). |
| Reels / vertical | Yes (Partial) | Placement-driven: `facebook_reels`, `instagram reels` positions; vertical assets via `portrait_customizations` / placement asset customization. Objective compatibility restricted. |
| Stories | Yes (Partial) | `portrait_customizations` covers IG/FB Stories; placement via targeting positions. |

#### Access tier / app review
- Tiers renamed: **Limited Access** (formerly Standard) and **Full Access** (formerly Advanced). Limited = default, heavily rate-limited, development only, "not for production apps serving live advertisers".
- Full Access via App Review ("Marketing API Access Tier" feature). Retention rule: ≥500 Marketing API calls in 15 days with <15% error rate over the last 500 calls.
- Business verification required if the app accesses sensitive data. Calls at every tier hit **production** data (no sandbox spend isolation in these pages).

#### Kenya relevance
- **KES is a supported ad account currency** (offset 100 → budgets/bids in cents, e.g. `daily_budget=50000` = KES 500).
- Minimum budgets per currency: not stated on fetched pages – **UNVERIFIED**.
- Special categories / flagged audiences: health or financial-status audiences may be blocked (op status 471) – relevant if POVU segments by purchase behaviour.

---

### Google Ads API

**Checked: 2026-11-26**

**Doc URLs fetched**
- https://developers.google.com/google-ads/api/docs/release-notes
- https://developers.google.com/google-ads/api/docs/api-policy/access-levels
- https://developers.google.com/google-ads/api/docs/api-policy/developer-token
- https://developers.google.com/google-ads/api/docs/oauth/overview
- https://developers.google.com/google-ads/api/docs/oauth/internals
- https://developers.google.com/google-ads/api/docs/best-practices/quotas
- https://developers.google.com/google-ads/api/docs/best-practices/partial-failures
- https://developers.google.com/google-ads/api/docs/remarketing/audience-segments/customer-match/get-started
- https://developers.google.com/google-ads/api/docs/ads/ad-types
- https://developers.google.com/google-ads/api/docs/assets/overview
- https://developers.google.com/google-ads/api/docs/assets/working-with-assets
- https://developers.google.com/google-ads/api/docs/assets/upload-videos
- https://developers.google.com/google-ads/api/docs/campaigns/overview
- (search result, official) https://developers.google.com/google-ads/api/data/codes-formats

**Current version:** **v26.2** (released 2026-11-11). v26.1 (2026-10-28), v26 (2026-10-14). Sunset dates live in the "Deprecation and sunset timetable" – not read (**UNVERIFIED**).

#### Documented operations relevant to POVU
| Area | Operation | Service |
|---|---|---|
| Budget | Create/update shared or per-campaign budget (micros) | `CampaignBudgetService` |
| Campaign | Create/update/remove; status ENABLED / PAUSED | `CampaignService.MutateCampaigns` (needs `advertising_channel_type`, budget, bidding strategy) |
| Status | Pause/resume = set `status` ENABLED/PAUSED; remove = `REMOVED` (REMOVED value **UNVERIFIED** on fetched page) | Campaign / AdGroup / AdGroupAd |
| Schedule | `start_date`/`end_date` on campaign – **UNVERIFIED** (not on fetched overview page) |  |
| Ad group | CRUD (Search/Display); Performance Max uses `AssetGroup` | `AdGroupService`, `AssetGroupService` |
| Ads | Responsive Search, Responsive Display, Demand Gen (multi-asset, carousel, product, video responsive), App ads – mutable | `AdGroupAdService` |
| Assets | Image (raw bytes in `image_asset.data`, immutable once uploaded), text, YouTube video | `AssetService.MutateAssets` |
| Video upload | Upload file → YouTube (brand channel or Google-managed unlisted) | `YouTubeVideoUploadService.CreateYouTubeVideoUpload` |
| Reporting | GAQL `Search` / `SearchStream` | `GoogleAdsService` |
| Customer Match | Create CRM user list; add/remove hashed members via jobs | `UserListService` (`crm_based_user_list`), `OfflineUserDataJobService`, `UserDataService` (small sync) |
| Conversions | Click/call conversion upload (2,000 per request), adjustments | `ConversionUploadService` (name **UNVERIFIED**; limits verified on quotas page) |

#### Auth & scopes
- OAuth 2.0 scope: **`https://www.googleapis.com/auth/adwords`**; `Authorization: Bearer <token>`.
- Service accounts supported and recommended for accounts you already have access to.
- **Developer token retired 2026-09-09**: optional and ignored; access level now belongs to the **Google Cloud project** that owns the OAuth client/service account. A future major version will reject developer tokens.
- Manager account only needed to manage multiple linked accounts. `login-customer-id` header semantics not on fetched pages – **UNVERIFIED** (best known: required when acting through a manager account).

#### Upload / async / status / reconciliation
- **Partial failure:** `partial_failure=true` executes valid ops; errors in `partial_failure_error` (`GoogleAdsFailure`), mapped by `location.field_path_elements[0].index`. Avoid with interdependent temp-ID ops.
- **validate_only:** exists on mutate requests (seen in sample) – semantics not documented on fetched page (**UNVERIFIED**: dry-run validation).
- **Idempotency:** no documented idempotency key; `request_id` only for support/debug.
- **Video upload states:** PENDING → UPLOADED → PROCESSED (or FAILED / REJECTED / UNAVAILABLE); poll via GAQL, then create `YoutubeVideoAsset` from `video_id`. No dry-run mode. Brand-channel upload requires user OAuth (not service account).
- **Customer Match jobs:** create job (with consent for create ops) → `AddOfflineUserDataJobOperations` (≤100,000 ids/request, ~10,000 recommended) → `RunOfflineUserDataJob` within 5 days → poll; 10 min–24 h processing; check `match_rate_range`. Don't mix create/remove in one job; one RUNNING job per list. Job can be `SUCCESS` with rejected ops → check `partial_failure_error`.
- **True state:** serving/primary status fields (`primary_status`, `serving_status`) and `policy_summary.approval_status` on ads – **UNVERIFIED** (field reference not fetched).
- BatchJobService exists (`ListBatchJobResults` counts as 1 op); batch limits **UNVERIFIED**.

#### Limits / quotas
| Access level | Daily operations |
|---|---|
| Test | 15,000/day, test accounts only |
| Explorer | 2,880/day production, 15,000/day test |
| Basic | 15,000/day (test + production) |
| Standard | Unlimited (per-service rate limits still apply) |
- Max **10,000 mutate operations per request**; billing/account-budget: 1 op/request, ≥12 h between account budget changes.
- `RESOURCE_EXHAUSTED` for daily/QPS breaches; 64 MB response cap; GAQL `IN` ≤ 20,000 items.
- UserDataService: 10 ops / 100 identifiers per request; UserData ≤ 20 identifiers.
- Image/video upload size limits: not on fetched pages – **UNVERIFIED**.

#### Creative formats
| Format | Supported via API? | Notes |
|---|---|---|
| Text | Yes (as Responsive Search Ad) | Legacy `TextAd`/`ExpandedTextAd` deprecated (existing ETAs only pause/remove). |
| Link | Yes | Final URLs on RSA / RDA / Demand Gen ads. |
| Single image | Partial | `ImageAd` is **not mutable** (remove & recreate); images normally via Responsive Display / Demand Gen image assets. |
| Multi-image / carousel | Yes | `DemandGenCarouselAd`, `DemandGenMultiAssetAd`. |
| Video | Partial | Classic `VideoAd` (YouTube video campaigns) is **reporting-only – must be created in UI or Google Ads scripts**; supported path = `DemandGenVideoResponsiveAd` or PMax video assets. |
| Shorts-style vertical | Partial | Via Demand Gen / PMax video assets; explicit Shorts control not documented on fetched pages – **UNVERIFIED**. |
| Stories | No | Google Ads has no "stories" placement; nearest equivalent is YouTube Shorts (Demand Gen) – **UNVERIFIED** as an official statement. |

#### Access tier / review
- Apply from the **Google Ads API Overview page in Cloud Console** (no longer the API Center). Test = automatic; Explorer = usually automated review; Basic = requires completed **brand verification**; Standard = manual audit (~10 business days) + Required Minimum Functionality.
- Explorer excludes: account creation/linking, user management, planning services, billing, multi-party approvals.
- Customer Match: requires good policy + payment history; **since 2026-04-01 projects with no Customer Match activity between 2025-10-01 and 2026-03-31 get `CUSTOMER_NOT_ALLOWLISTED_FOR_THIS_FEATURE` and must use the Data Manager API** – a new POVU integration should plan on the Data Manager API for audience sync.

#### Kenya relevance
- **KES listed** in Google Ads API currency codes (min billable unit 10000 micros). Whether KES is an active **signup** currency for `CreateCustomerClient` – **UNVERIFIED**.
- Customer Match availability for Kenyan advertisers – **UNVERIFIED**.

---

### LinkedIn Marketing API (Advertising API)

**Checked: 2026-11-26**

**Doc URLs fetched**
- https://learn.microsoft.com/en-us/linkedin/marketing/versioning
- https://learn.microsoft.com/en-us/linkedin/marketing/increasing-access
- https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/getting-started
- https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaigns
- https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-creatives
- https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/videos-api
- https://learn.microsoft.com/en-us/linkedin/marketing/matched-audiences/create-and-manage-segments
- https://learn.microsoft.com/en-us/linkedin/marketing/matched-audiences/create-and-manage-segment-users
- https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting
- https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits
- https://learn.microsoft.com/en-us/linkedin/shared/references/v2/ads/supported-currencies

**Current version:** header **`Linkedin-Version: 202611`** (November 2026). Monthly releases, each supported ≥1 year; 202601 sunsets 2027-01-15. Unversioned calls and sunset versions return errors. Also required: `X-Restli-Protocol-Version: 2.0.0`. Base path `https://api.linkedin.com/rest/`.

#### Documented operations relevant to POVU
| Area | Operation | Endpoint |
|---|---|---|
| Ad account | Create (Standard tier; Dev tier = 1 test account) | `POST /rest/adAccounts` |
| Campaign group | Create/update (status, `runSchedule`, `totalBudget`) | `POST /rest/adAccounts/{id}/adCampaignGroups` |
| Campaign | Create / partial update / delete | `POST /rest/adAccounts/{id}/adCampaigns`; update with `X-RestLi-Method: PARTIAL_UPDATE` + `{"patch":{"$set":{…}}}`; `DELETE` only for DRAFT, else `status=PENDING_DELETION` |
| Status | Pause/resume | campaign `status` ACTIVE / PAUSED (also ARCHIVED, COMPLETED, CANCELED, DRAFT, PENDING_DELETION, REMOVED); creative `intendedStatus` |
| Budget | `dailyBudget`, `totalBudget` (string amounts, currency must match account), `pacingStrategy=LIFETIME` | campaign fields |
| Schedule | `runSchedule.start` (inclusive, immutable), `runSchedule.end` (exclusive, optional) | campaign / group |
| Creative | Create (incl. inline post via `action=createInline` + `inlineContent`), batch create/get/partial update/delete | `POST /rest/adAccounts/{id}/creatives` |
| Media | Video upload (`/rest/videos?action=initializeUpload` → PUT parts → `finalizeUpload`); Images API (**UNVERIFIED**, not fetched) | Videos API |
| Targeting helpers | `adTargetingFacets`, `adTargetingEntities`, `audienceCounts`, `adBudgetPricing` | |
| Reporting | `adAnalytics` finders `analytics` (1 pivot), `statistics` (≤3 pivots), `attributedRevenueMetrics` | `GET /rest/adAnalytics` |
| Matched audiences | Create/get/update/delete DMP segment; add/remove users (stream) or CSV list upload | `POST /rest/dmpSegments`, `POST /rest/dmpSegments/{id}/users` |
| Conversions API | Upload conversions | separate product, scope `rw_conversions` (endpoint details **UNVERIFIED**) |

#### Auth & scopes (all 3-legged member permissions)
- Advertising API: `r_ads`, `rw_ads` (member must hold ACCOUNT_BILLING_ADMIN / ACCOUNT_MANAGER / CAMPAIGN_MANAGER / CREATIVE_MANAGER), `r_ads_reporting`, `r_organization_social`, `w_organization_social`, `rw_organization_admin`, etc.
- Matched Audiences API (separate application, requires Advertising API first): **`rw_dmp_segments`**; member role ≠ VIEWER.
- Conversions API: `rw_conversions`, `r_ads`.
- Video upload with organization owner needs company ADMIN/DSC rights.

#### Upload / async / status / reconciliation
- **Video:** `initializeUpload(fileSizeBytes, owner, uploadCaptions, uploadThumbnail)` → 4 MB parts PUT to `uploadInstructions[].uploadUrl` (save ETags) → `finalizeUpload(uploadedPartIds)` → poll `GET /rest/videos/{urn}` until `status=AVAILABLE` (others: WAITING_UPLOAD, PROCESSING, PROCESSING_FAILED + `processingFailureReason`). Upload URLs expire ~30 days.
- **Creative review:** `reviewStatus` PENDING / APPROVED / REJECTED / NEEDS_REVIEW; read-only `isServing` + `servingHoldReasons` (e.g. REJECTED). **Cannot pause a creative that is in review** (400).
- **Campaign true state:** read-only `servingStatuses` (RUNNABLE, STOPPED, *_HOLD reasons such as CAMPAIGN_TOTAL_BUDGET_HOLD, CAMPAIGN_AUDIENCE_COUNT_HOLD).
- **Batch:** BATCH_CREATE / BATCH_GET / BATCH_PARTIAL_UPDATE / BATCH_DELETE; all entities in one ad account; per-element statuses (partial success).
- **DMP users:** add/remove is idempotent (re-adding returns 201); batch ≤5,000 users, per-element 201/400 with `batchIndex`. Wait 5 s after segment creation before adding users. Segment `destinations[].status` = BUILDING → READY (READY value **UNVERIFIED**; BUILDING seen). Hashing: SHA256_EMAIL / SHA512_EMAIL (lowercase, no whitespace), GOOGLE_AID.
- **Reporting:** no pagination; ≤15,000 elements; ≤20 metrics; performance metrics near-real-time, demographics 24–48 h delay; retention 10 y performance / 2 y demographics; daily granularity only for 6 months.

#### Limits / quotas
- Daily application + member limits, reset midnight UTC; **values not published** – visible in Developer Portal → app → Analytics after ≥1 call; 429 on breach; email alert at 75% app quota.
- DMP `/users`: 600 requests/min per member; ≤1,000 DMP segments per ad account (429 SEGMENT_LIMIT_EXCEEDED).
- adAnalytics: 45 million metric values per 5-min window (429).
- Campaigns: 5,000 per ad account, 1,000 concurrently ACTIVE; 15 active + 85 inactive creatives per campaign. Min target audience 300 members.
- Video: 3 s–30 min, 75 KB–500 MB (ads spec), MP4; API max file 5 GB.

#### Creative formats
| Format | Supported via API? | Notes |
|---|---|---|
| Text | Yes | `TEXT_AD` campaign type, `TextAdCreativeVariables` (title + text + clickUri). |
| Link (article/single image post) | Yes | Sponsored Content (`SPONSORED_UPDATES`, format `STANDARD_UPDATE`). |
| Single image | Yes | Image ads via Sponsored Content. |
| Multi-image / carousel | Yes | Format `CAROUSEL` (must be set at campaign creation). |
| Video | Yes | Format `SINGLE_VIDEO`, Videos API upload. |
| Vertical video | Partial | Videos API returns aspect ratio (e.g. 9:16 seen in samples); explicit vertical-video ad placement support **UNVERIFIED**. |
| Stories | No | No stories placement exists in the Advertising API docs fetched (LinkedIn Stories product discontinued – **UNVERIFIED**). |

#### Access tier / review
- All apps start in **Development tier**: unlimited read for administered accounts, 1 test ad account creatable, edits on **≤5 ad accounts** (ad accounts must be mapped to the app in Developer Portal).
- **Standard tier**: unlimited accounts/edits; requested via Developer Support Portal ticket; LinkedIn may decline at its discretion.
- Matched Audiences, Conversions, Lead Sync = separate product applications.

#### Kenya relevance
- **KES is NOT in the documented ad-account billing currency list** (AED, ARS, AUD, BRL, CAD, CHF, CLP, CNY, COP, DKK, EGP, EUR, GBP, HKD, IDR, INR, JPY, KRW, MXN, MYR, NOK, NZD, PEN, PLN, SAR, SEK, SGD, THB, TRY, USD, ZAR). A Kenyan advertiser would bill in USD (or another listed currency); POVU must convert KES budgets. Note: that page was last updated 2023 – current Campaign Manager list **UNVERIFIED**.
- Kenya geo targeting is available via `adTargetingEntities` locations facet – Kenya URN **UNVERIFIED**.

---

### TikTok API for Business (Marketing API)

**Checked: 2026-11-26** (docs are JS-rendered; read via rendered browser page text)

**Doc URLs fetched**
- https://business-api.tiktok.com/portal/docs/create-a-campaign/v1.3
- https://business-api.tiktok.com/portal/docs/create-ads/v1.3
- https://business-api.tiktok.com/portal/docs/rate-limits/v1.3
- https://business-api.tiktok.com/portal/docs/api-reference/v1.3
- https://business-api.tiktok.com/portal/docs/upload-a-video/v1.3
- https://business-api.tiktok.com/portal/docs/upload-an-audience-file/v1.3
- https://business-api.tiktok.com/portal/docs/update-an-audience/v1.3
- https://business-api.tiktok.com/portal/docs/update-the-statuses-of-ads/v1.3
- https://business-api.tiktok.com/portal/docs/run-a-synchronous-report/v1.3
- (search summaries of official pages) register-as-a-developer/v1.3, create-a-developer-app/v1.3, create-an-audience-by-file/v1.3, whats-new/v1.3

**Current version:** **v1.3** (`https://business-api.tiktok.com/open_api/v1.3/…`). Header `Access-Token`. IDs are strings in v1.3.
**Deprecation:** from **2027-01-01**, `/campaign/create/`, `/campaign/copy/task/create/`, `/adgroup/create/`, `/ad/create/`, `/ad/aco/create/` stop supporting non-Search **Legacy Manual** campaigns for **Sales, App Promotion and Lead Generation** objectives → migrate to **Upgraded Smart+** APIs (`/smart_plus/campaign/create/` etc.). Traffic/Reach/Video Views/Engagement manual flow not named in the notice.

#### Documented operations relevant to POVU
| Area | Operation | Endpoint |
|---|---|---|
| Campaign | Create / update / status | `/campaign/create/`, `/campaign/update/`, `/campaign/status/update/` (`operation_status` ENABLE / DISABLE / DELETE) |
| Ad group | Create / update / status (budget, schedule, targeting, placement, bidding) | `/adgroup/create/`, `/adgroup/update/`, `/adgroup/status/update/` |
| Ad | Create (≤20 creatives/request; 20–50 ads per ad group), update, get, status (1–20 ids/request) | `/ad/create/`, `/ad/update/`, `/ad/get/`, `/ad/status/update/` |
| Budget | Campaign: `budget_mode` BUDGET_MODE_DAY / TOTAL / INFINITE / DYNAMIC_DAILY_BUDGET (CBO via `budget_optimize_on`), `budget` float | campaign/adgroup |
| Schedule | Ad-group schedule fields – **UNVERIFIED** (ad group page not fetched) | |
| Creative assets | Image upload, video upload, video/image search | `/file/image/ad/upload/`, `/file/video/ad/upload/`, `/file/video/ad/search/` |
| Review | Ad review info; creative pre-review | `/ad/review_info/`, `pre_review_enabled` on upload |
| Reporting | Sync report (≤20,000 ads; filter ≤100 ids) and async report tasks | `/report/integrated/get/`, `/report/task/create/` |
| Custom audience | Upload hashed file → create / append / remove / replace | `/dmp/custom_audience/file/upload/`, `/dmp/custom_audience/create/`, `/dmp/custom_audience/update/` |
| Events API (CAPI) | Server-side web/app/offline events | `/event/track/` (1,000 QPS) |

#### Auth & scopes
- Advertiser authorization: advertiser approves the developer app → redirect with auth code → exchange at `/oauth2/access_token/` for long-term access token; list authorized advertisers via `/oauth2/advertiser/get/`; revoke via `/oauth2/revoke_token/`.
- Permission scopes chosen per app (e.g. "Video Management → Create and Update Videos" maps to `/file/video/ad/upload/`). Full scope list page not fetched – **UNVERIFIED** detail.
- Using `/campaign/create/` = agreeing to TikTok Online Data Terms.

#### Upload / async / status / reconciliation
- **Video upload:** `UPLOAD_BY_FILE` (multipart + MD5 `video_signature`), `UPLOAD_BY_URL`, `UPLOAD_BY_FILE_ID`, `UPLOAD_BY_VIDEO_ID`; 10 s request timeout; recommended ≤500 MB, ratios 9:16 / 16:9 / 1:1, mp4/mov/mpeg/avi. Re-uploading the same file returns the existing video (but each upload method call may yield a new `video_id`). File names must be unique per advertiser. Optional Smart Fix (LOW_RESOLUTION, ILLEGAL_VIDEO_SIZE) returns `fix_task_id`.
- **Idempotency:** campaign `request_id` (64-bit int string) dedupes retries within **10 seconds**.
- **True state:** `operation_status` on get endpoints; deleted entities cannot be modified; review via `/ad/review_info/`; secondary/delivery status fields **UNVERIFIED** (ad get page not fetched).
- **Reporting:** sync vs async differ (sync truncates at 20,000 ads; TTAM downloads match async). Response header `X-Tt-Ads-Throttle`.
- **Custom audience:** CSV/TXT ≤250 MB, MD5 or SHA256 (SHA256 recommended; phones E.164 before hashing), multi-ID files with headers (`email_SHA256`, `phone_SHA256`, `MAID…`); ≤50 file paths per request; processing 30–60 min; **24 update ops per audience per rolling 24 h**; APPEND/REMOVE/REPLACE fail if resulting size <1,000; only the uploading advertiser can use a `file_path`.

#### Limits / quotas
| App level | QPS | QPM | QPD |
|---|---|---|---|
| Basic (default) | 10 | 600 | 864,000 |
| Advanced | 20 | 1,200 | 1,728,000 |
| Premium | 30 | 1,800 | 2,592,000 |
| Ultimate | 50 | 3,000 | 4,320,000 |
- Throttle → `code: 40100`; QPM breach = wait 5 min; QPD resets 00:00 UTC. Upgrades one level at a time via My Apps → App Detail → Authorization.
- Endpoint-specific: `/ad/create/` 5 QPS / 150 QPM (Basic); async report task create 2 QPS / 4,500 QPD; `/event/track/` 1,000 QPS.
- 999 campaigns per ad account.

#### Creative formats
| Format | Supported via API? | Notes |
|---|---|---|
| Text-only | No | `ad_format` enum has no text format (SINGLE_IMAGE, SINGLE_VIDEO, LIVE_CONTENT, CAROUSEL_ADS, CATALOG_CAROUSEL); text is `ad_text` on image/video ads. |
| Link | Yes | Landing page URL + CTA on image/video ads (field name `landing_page_url` per pre-review doc). |
| Single image | Partial | `SINGLE_IMAGE` exists; placement eligibility (e.g. TikTok feed vs Pangle) **UNVERIFIED**. |
| Carousel | Yes | `CAROUSEL_ADS` with 1–35 `image_ids` (order preserved); cannot change format after set. |
| Video | Yes | `SINGLE_VIDEO` with `video_id` (or Spark Ads `tiktok_item_id`) + cover `image_ids`. |
| Vertical (TikTok feed) | Yes | 9:16 is a native supported ratio; this is TikTok's primary format. |
| Stories | No | No stories placement in TikTok API docs fetched – **UNVERIFIED** as an explicit statement. |
- Caveat: non-Spark ads with **Custom Identity** on TikTok placements are no longer supported for new ad accounts created on/after 2026-01-15 → POVU must use Spark Ads (authorized TikTok account/posts) for TikTok placement.

#### Access tier / app review
- TikTok for Business account → register as developer (company email/name/website; individuals not accepted; review ≤3 business days) → create developer app (use-case description, redirect URL, scopes; review 2–3 business days; ≤5 apps per developer) → advertiser authorization.
- Rate-limit tier upgrades require application with justification. Many features allowlist-only (Search Ads, Product Sales, RTA, etc.).
- Sandbox: being deprecated ("To-be-deprecated Sandbox accounts"), 1 QPS / 30 QPM / 1,000 QPD per endpoint.

#### Kenya relevance
- Kenya added as a targetable ad-group location in **August 2024** (What's New, via search summary of official page).
- Kenyan **ad account currency KES** – **UNVERIFIED** (only seen in an Ads Manager events-parameter currency list, not account currency). `/bc/advertiser/attribute/` returns allowed currencies/regions per BC – use it at onboarding.

---

#### Cross-provider notes for POVU design
- Build state reconciliation on provider read-back (`effective_status`, `servingStatuses`/`isServing`, `operation_status`/review info, GAQL status) – never trust POVU's last write.
- Budget mutation throttles differ sharply (Meta 4/hour per ad set; Google account-budget 12 h; LinkedIn/TikTok undocumented) → queue + debounce budget edits.
- Audience sync: Meta (≤10k/request, session batching), Google (Data Manager API for new projects), LinkedIn (≤5k/batch, 600/min), TikTok (file-based, 24 updates/day, min 1,000). All require SHA-256 normalized identifiers; phones in E.164 (+254…).
- Currency: Meta and Google support KES; LinkedIn does not list KES; TikTok unconfirmed.

## Organic social APIs

Capability matrix for organic posting, publish-status polling, metrics, and comments. Every fact below comes from an official provider page fetched on 2026-11-26. Anything not confirmed on an official page is marked **UNVERIFIED**. Real posting stays off by default in POVU. This matrix only says what the providers document.

Legend: Yes = documented API path. Partial = possible with documented caveats. No = no documented API path.

---

### 1. Facebook Pages API (Meta Graph API)

- **Docs fetched:**
  - https://developers.facebook.com/docs/pages-api/posts
  - https://developers.facebook.com/docs/video-api/guides/publishing
  - https://developers.facebook.com/docs/video-api/guides/reels-publishing
  - https://developers.facebook.com/docs/page-stories-api
  - https://developers.facebook.com/docs/graph-api/reference/v27.0/object/comments
  - https://developers.facebook.com/docs/graph-api/reference/insights
- **API version:** Graph API **v27.0**, used in all current examples. Some older Reels examples still show v18.0.
- **Checked:** 2026-11-26

#### Operations relevant to POVU
| Operation | Endpoint | Notes |
|---|---|---|
| Create text/link post | `POST /{page_id}/feed` (`message`, `link`) | |
| Schedule post | same, with `published=false` and `scheduled_publish_time` | Must be **10 minutes to 30 days** from the request. Accepts UNIX timestamp, ISO 8601, or a strtotime string. |
| Single photo | `POST /{page_id}/photos` (`url`) | Returns a photo id and a post id. |
| Video | `POST graph-video.facebook.com/v27.0/{page_id}/videos` with a file handle from the Resumable Upload API (`POST /{app_id}/uploads` → `POST /upload:{session}` with `file_offset`) | Resume with `GET /upload:{session}`, which returns `file_offset`. |
| Reels | `POST /{page_id}/video_reels` `upload_phase=start` → upload to `rupload.facebook.com/video-upload/{video_id}` (or `file_url`) → `upload_phase=finish` with `video_state` DRAFT, SCHEDULED, or PUBLISHED | |
| Stories | Video: `POST /{page_id}/video_stories` (start → upload → finish). Photo: `POST /{page_id}/photos` `published=false`, then `POST /{page_id}/photo_stories` with `photo_id` | `GET /{page_id}/stories` lists stories. |
| Read posts | `GET /{page_id}/feed` | |
| Edit post | `POST /{page_post_id}` | "An app can only update a Page post if that app created the post." |
| Delete post | `DELETE /{page_post_id}` | |
| Read comments | `GET /{object-id}/comments` | Comment `id` is returned only when the token holder can perform MODERATE on the Page. |
| Reply to comment | `POST /{object-id}/comments` | Needs `pages_manage_engagement` or a MODERATE-task Page token. Delete a comment via `/{comment-id}`. |
| Post metrics | `GET /{page_post_id}/insights?metric=...` | Metrics include `post_clicks*`, `post_reactions_by_type_total`, `post_activity_by_action_type*`. `post_impressions*` are marked "Deprecated above Graph API v25". "By June 15, 2026, a number of the Page Insights metrics will be deprecated for all API versions." |

#### Auth and scopes
- **Publishing:** `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`, and `publish_video` for video to a Page. The Posts guide also lists `pages_manage_engagement` and `pages_read_user_engagement`.
- **Stories with a business system user:** add `business_management`.
- **Insights:** `read_insights` and `pages_read_engagement`, with a Page token from someone who can perform the ANALYZE task.
- **Page tasks:** CREATE_CONTENT, MANAGE, and MODERATE.

#### Upload, async status, and reconciliation
- **Video, Reel, and Story status:** `GET /{video_id}?fields=status`.
  - `video_status`: error, expired, processing, ready, uploading, upload_failed, upload_complete.
  - `uploading_phase`, `processing_phase`, and `publishing_phase` each report a status. `publishing_phase` also gives `publish_status` (draft, error, published, scheduled) and `publish_time`.
- **Photo and feed posts:** synchronous. The response returns the post id.
- **Webhooks:** Page webhooks for publish completion were not checked. **UNVERIFIED**

#### Limits
- **Reels:** "limited to 30 API-published posts within a 24-hour moving period."
- **Reels and Story video specs:** 9:16 aspect ratio. 1080×1920 recommended, 540×960 minimum. 24–60 fps. Duration 3–90 s, with Stories capped at 60 s.
- **Story photo:** at most 10 MB. A Story asset cannot reuse media from a previously published post.
- **Regular `/videos`:** no maximum size or duration is stated on the publishing guide. **UNVERIFIED**
- **Feed post rate limit:** no numeric per-Page daily limit was found. **UNVERIFIED**

#### Content formats
| Format | API? | Notes |
|---|---|---|
| Text-only | Yes | `/feed` with `message` |
| Link | Yes | `/feed` with `link` |
| Single image | Yes | `/photos` |
| Multi-image | Partial | Unpublished photos attached to a feed post (`attached_media`) are not described on the fetched pages. **UNVERIFIED** |
| Video | Yes | `/videos` with resumable upload |
| Reels | Yes | `/video_reels`, 30 per 24 h |
| Stories | Yes | `/video_stories`, `/photo_stories` |

#### Access tier and app review
- Standard Access covers Pages the developer's own app-role users manage. Serving Pages of other businesses needs **Advanced Access**, which requires **App Review** and **Business Verification**.
- The Facebook Pages-specific App Review wording was not fetched. This follows the same Meta access-level model documented in the Instagram overview. **UNVERIFIED**

---

### 2. Instagram Platform (Graph API content publishing)

- **Docs fetched:**
  - https://developers.facebook.com/docs/instagram-platform/content-publishing/
  - https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media
  - https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/content_publishing_limit
  - https://developers.facebook.com/docs/instagram-platform/overview
  - https://developers.facebook.com/docs/instagram-platform/insights
- **API version:** examples use **v27.0** (`graph.instagram.com/v27.0` or `graph.facebook.com/v27.0`).
- **Checked:** 2026-11-26

#### Operations relevant to POVU
| Operation | Endpoint |
|---|---|
| Create container | `POST /{IG_ID}/media`. Image: `image_url` (JPEG only). Video: `video_url` + `media_type=VIDEO`. Reel: `media_type=REELS`. Story: `media_type=STORIES`. Carousel: `media_type=CAROUSEL` + `children` |
| Publish | `POST /{IG_ID}/media_publish` with `creation_id` |
| Container status | `GET /{container_id}?fields=status_code` |
| Quota | `GET /{IG_ID}/content_publishing_limit` (`quota_usage`, `config{quota_total,quota_duration}`) |
| Comments | Get, reply, delete, hide/unhide, enable/disable comments on media |
| Media insights | `GET /{IG_MEDIA_ID}/insights` (e.g. `reach`, `views`, `likes`, `comments`) |
| Edit caption | Not found on the fetched pages. **UNVERIFIED** |
| Delete media | Not found on the fetched pages. **UNVERIFIED** |

#### Auth and scopes

There are three login paths:

| Path | Host | Publish scopes | Comment scope | Insights scope |
|---|---|---|---|---|
| Instagram Login (Business Login for Instagram), Instagram User token | `graph.instagram.com` | `instagram_business_basic`, `instagram_business_content_publish` | `instagram_business_manage_comments` | `instagram_business_manage_insights` |
| Facebook Login for Business, Page token | `graph.facebook.com` | `instagram_basic`, `instagram_content_publish`, `pages_read_engagement` (plus `ads_management` or `ads_read` if the user's Page role comes from Business Manager) | `instagram_manage_comments` | `instagram_manage_insights` |
| Unified Login, business-integration system user token | `graph.facebook.com` | `instagram_basic`, `instagram_content_publish` | — | — |

- The account must be an Instagram **professional** account (business or creator). Consumer accounts are not supported.
- Page Publishing Authorization (PPA) must be completed for Pages that require it.

#### Async flow and reconciliation
1. Create the container. Media must be on a publicly reachable URL at publish time. Resumable upload to `rupload.facebook.com/ig-api-upload/{container_id}` is available only on the Facebook Login for Business path.
2. Poll `status_code` until it is `FINISHED`. Possible values: `EXPIRED`, `ERROR`, `FINISHED`, `IN_PROGRESS`, `PUBLISHED`. Meta recommends polling once per minute for no more than 5 minutes.
3. Call `media_publish`. It returns the final IG media id, which is different from the container id.

"Containers expire after 24 hours." Publish webhooks were not checked. **UNVERIFIED**

#### Limits
- **Publishing quota (conflict in Meta's own docs):**
  - The `content_publishing_limit` reference says `quota_total` is "currently `50`" per `quota_duration` 86400 s. This counts published containers.
  - The content-publishing guide's Rate Limit section says **100** API-published posts per 24 h, with a carousel counting as one.
  - POVU should read `config.quota_total` at runtime and not hard-code either number.
- **Containers:** at most 400 created per rolling 24 h.
- **Images:** JPEG only, 8 MB max, aspect ratio 4:5 to 1.91:1, width 320–1440 px.
- **Reels:** MOV/MP4, 3 s to 15 min, 300 MB max, 23–60 fps, 9:16 recommended. Reels cannot appear in carousels.
- **Stories:** image JPEG 8 MB. Video 3–60 s, 100 MB. Stories expire after 24 h.
- **Carousel:** up to **20** images or videos.
- **Caption:** 2200 characters, 30 hashtags, 20 @tags.
- **Alt text:** images only, up to 1000 characters.

#### Content formats
| Format | API? | Notes |
|---|---|---|
| Text-only | No | No text-only container type is documented. Every container needs `image_url` or `video_url`. The guide does not state this explicitly. **UNVERIFIED** |
| Link | No | Instagram has no link-post type. URLs in captions are not clickable. **UNVERIFIED** |
| Single image | Yes | JPEG only |
| Carousel | Yes | Up to 20 items; Reels are not allowed as children |
| Video | Yes | `media_type=VIDEO` |
| Reels | Yes | `media_type=REELS` (trial reels via `trial_params`) |
| Stories | Yes | `media_type=STORIES` |

#### Access tier and app review
- **Standard Access:** enough when the app serves only Instagram accounts the developer owns or manages.
- **Advanced Access:** needed to serve other businesses. It requires **App Review** and **Business Verification**.

---

### 3. LinkedIn Community Management API (Posts, Images, Videos, Documents)

- **Docs fetched:**
  - https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
  - …/shares/images-api
  - …/shares/videos-api
  - …/shares/documents-api
  - …/shares/multiimage-post-api
  - …/shares/comments-api
  - …/organizations/share-statistics
  - …/community-management-overview
- **API version:** header `Linkedin-Version: YYYYMM`. The docs' default moniker is **li-lms-2026-11**, so the latest documented version is **202611**. Also required: `X-Restli-Protocol-Version: 2.0.0`. Version 202601 sunsets on 2027-01-15.
- **Checked:** 2026-11-26

#### Operations relevant to POVU
| Operation | Endpoint | Notes |
|---|---|---|
| Create post | `POST /rest/posts` | Returns 201; the `x-restli-id` header holds `urn:li:share:…` or `urn:li:ugcPost:…` |
| Get, batch get, or find by author | `GET /rest/posts/{urn}`, `?ids=List(...)`, `?q=author&author=…` | `viewContext=AUTHOR` shows DRAFT or PROCESSING states |
| Edit post | `POST /rest/posts/{urn}` with `X-RestLi-Method: PARTIAL_UPDATE` | Only these fields can change: `commentary`, `contentCallToActionLabel`, `contentLandingPage`, `lifecycleState`, `adContext` |
| Delete post | `DELETE /rest/posts/{urn}` | Idempotent (204); no batch delete |
| Comments | `GET`/`POST /rest/socialActions/{urn}/comments`; reply via `parentComment`; edit; delete | Comment creation has a short-term per-member 1-minute throttle (429) |
| Post metrics | `GET /rest/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity=…&shares=List(...)` or `ugcPosts[...]` | Returns `impressionCount`, `uniqueImpressionsCount`, `clickCount`, `likeCount`, `commentCount`, `shareCount`, `engagement`. Organic only, rolling 12 months. Per-post queries are lifetime only. |
| Video analytics | Video Analytics API (watch time, views, viewers) | Not fetched in detail. **UNVERIFIED** |

#### Auth and scopes
- **Posting:** `w_organization_social` (member must be ADMINISTRATOR, DIRECT_SPONSORED_CONTENT_POSTER, or CONTENT_ADMIN) or `w_member_social`.
- **Reading posts:** `r_organization_social`. `r_member_social` is "closed", with no new requests accepted.
- **Comments API page:** lists `w_organization_social_feed`, `r_organization_social_feed`, `w_member_social_feed`, and `r_member_social_feed` (restricted).
- **Share statistics:** `rw_organization_admin` (ADMINISTRATOR role).
- **Images API:** works with `w_member_social`, `w_organization_social`, `rw_ads`, or `w_power_creators`. A `w_member_social`-only token cannot GET `/rest/images`.

#### Upload, async status, and reconciliation
- **Images and documents:**
  1. `POST /rest/{images|documents}?action=initializeUpload` returns `uploadUrl` and a `urn:li:image|document`.
  2. PUT the file to `uploadUrl`.
  3. `GET /rest/{images|documents}/{urn}` and check `status`: WAITING_UPLOAD, PROCESSING, AVAILABLE, or PROCESSING_FAILED.
- **Videos:**
  1. `POST /rest/videos?action=initializeUpload` (owner, fileSizeBytes, optional captions or thumbnail) returns `uploadInstructions[]` with 4 MB byte ranges (0–4194303, …), an `uploadToken`, and a `urn:li:video`.
  2. PUT each part and save the **ETag** header.
  3. `POST /rest/videos?action=finalizeUpload` with `uploadedPartIds` (the ETags in order).
  4. Poll `GET /rest/videos/{urn}` for `status` until AVAILABLE. `processingFailureReason` is set on failure.
  5. Upload URLs typically expire 30 days after initialization.
- **Post lifecycle:** `lifecycleState` accepts only PUBLISHED on create. Read-back values are DRAFT, PUBLISHED, PUBLISH_REQUESTED (asynchronous), and PUBLISH_FAILED. POVU should reconcile by GET with `viewContext=AUTHOR`.
- **Scheduling:** no native scheduled-publish field on create. POVU must schedule on its side.
- **Webhooks for publish:** not documented on the fetched pages. **UNVERIFIED**

#### Limits
- **Video:** 3 s to 30 min, MP4.
  - The spec section says 75 KB to 500 MB.
  - The schema says `fileSizeBytes` "Maximum allowed Videos size is 5GB". The two conflict, so use 500 MB as the safe limit.
- **Images:** under 36,152,320 pixels; JPG, GIF (up to 250 frames), or PNG.
- **Documents:** PPT, PPTX, DOC, DOCX, or PDF; at most 100 MB and 300 pages.
- **MultiImage:** 2 to 20 images.
- **Rate limits, Development Tier:** 500 requests per app and 100 per member. The time window is not stated on the overview page. **UNVERIFIED**
- **Rate limits, Standard Tier:** numbers not fetched. **UNVERIFIED**
- **Commentary maximum length:** only the error `FIELD_LENGTH_TOO_LONG` is documented; no number is given. **UNVERIFIED**

#### Content formats
| Format | API? | Notes |
|---|---|---|
| Text-only | Yes | |
| Link (article) | Yes | No URL scraping. The partner must supply the title, description, and thumbnail (an image URN). |
| Single image | Yes | Images API |
| Multi-image | Yes | MultiImage API, 2–20 images, organic only |
| Carousel | No (organic) | "Organic carousel is currently not supported", sponsored only |
| Document | Yes | Documents API |
| Video | Yes | Videos API |
| Reels/shorts | Partial | No separate short-video type; a vertical video is posted as a normal video |
| Stories | No | Not a documented Posts API content type |
| Poll | Yes | Organic only |

#### Access tier and app review
- The Community Management API is a **vetted product** with two tiers.
  - **Development Tier:** initial approval with limited call volume.
  - **Standard Tier:** requires a screencast for each requested use case.
- Request Development Tier only from a **new** developer app that has no other API products.
- Integration requirements and Technical Sign Off apply to partners.

---

### 4. TikTok Content Posting API

- **Docs fetched:**
  - https://developers.tiktok.com/doc/content-posting-api-get-started
  - …/content-posting-api-reference-direct-post
  - …/content-posting-api-reference-upload-video
  - …/content-posting-api-reference-photo-post
  - …/content-posting-api-reference-query-creator-info
  - …/content-posting-api-reference-get-video-status
  - …/content-posting-api-media-transfer-guide
- **API version:** **v2** (`/v2/post/publish/...`).
- **Checked:** 2026-11-26

#### Operations relevant to POVU
| Operation | Endpoint | Scope | Rate limit |
|---|---|---|---|
| Query creator info (required before Direct Post) | `POST /v2/post/publish/creator_info/query/` | `video.publish` | 20 per minute per user token |
| Direct Post video | `POST /v2/post/publish/video/init/` (`source`: FILE_UPLOAD or PULL_FROM_URL) | `video.publish` | 6 per minute per user token |
| Upload video to inbox/draft | `POST /v2/post/publish/inbox/video/init/` | `video.upload` | 6 per minute per user token |
| Photo post | `POST /v2/post/publish/content/init/`, `media_type=PHOTO`, `post_mode` DIRECT_POST or MEDIA_UPLOAD; PULL_FROM_URL only | `video.publish` (direct) or `video.upload` (inbox) | 6 per minute per user token |
| Publish status | `POST /v2/post/publish/status/fetch/` | `video.upload` / `video.publish` | 30 per minute per user token |

- **Metrics:** Display API `POST /v2/video/query/` with scope `video.list`, up to 20 ids per call, fields such as `like_count`, `comment_count`, `share_count`, `view_count`. Seen only in official search-result snippets; the page was not fetched. **UNVERIFIED**
- **Delete or edit a post:** no endpoint in the Content Posting API docs. **UNVERIFIED** whether one exists elsewhere.
- **Read or reply to comments:** not in the Content Posting API. Possibly available through the TikTok API for Business. **UNVERIFIED**

#### Direct Post requirements
- `post_info.privacy_level` is **required**. It must be one of the `privacy_level_options` returned by `creator_info`: PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, or SELF_ONLY.
- Respect `comment_disabled`, `duet_disabled`, `stitch_disabled`, and `max_video_post_duration_sec` from `creator_info`.
- Other fields: `title` (up to 2200 UTF-16 runes for video), `disable_comment`, `disable_duet`, `disable_stitch`, `video_cover_timestamp_ms`, `brand_content_toggle`, `brand_organic_toggle`, `is_aigc`.

#### Async flow and reconciliation
1. The init call returns a `publish_id` and, for FILE_UPLOAD, an `upload_url` that expires 1 hour after issue.
2. Upload the file in chunks: each chunk 5–64 MB (the final chunk up to 128 MB), 1–1000 chunks, in sequence. Files under 5 MB go up whole.
3. PULL_FROM_URL requires a **verified domain or URL prefix** owned by the app. The URL must be https with no redirects.
4. Poll `status/fetch` with the `publish_id`. Statuses:
   - `PROCESSING_UPLOAD`
   - `PROCESSING_DOWNLOAD`
   - `SEND_TO_USER_INBOX` (upload flow)
   - `PUBLISH_COMPLETE`
   - `FAILED`, with a `fail_reason` such as `spam_risk_too_many_posts`, `duration_check_failed`, `video_pull_failed`, `auth_removed`, or `internal` (retryable)
5. The final post id is `publicaly_available_post_id` (TikTok's spelling). It is "returned only if the post is published for public viewership", after moderation. `publish_id` is **not** the post id.
6. **Webhooks:** TikTok sends events for publish failed, publish complete, inbox delivered, and post becoming publicly available or unavailable, if the app has a webhook URL configured.

#### Limits
- **Video:** MP4 (recommended), WebM, or MOV. H.264 (recommended), H.265, VP8, or VP9. 23–60 fps. 360–4096 px per side. At most 4 GB. Up to 10 minutes can be sent, but the per-creator maximum comes from `max_video_post_duration_sec`. All creators can post 3 minutes; some can post 5 or 10.
- **Photo:** WebP or JPEG, at most 1080p, 20 MB per image, **up to 35** images. Title up to 90 runes, description up to 4000.
- **Inbox uploads:** "at most 5 pending shares within any 24-hour period."
- **Daily post cap:** exists but has no published number; it surfaces as `spam_risk_too_many_posts`. `reached_active_user_cap` means the client's daily quota of active publishing users is used up.

#### Content formats
| Format | API? | Notes |
|---|---|---|
| Text-only | No | No text-only endpoint. `content/init` allows only `media_type=PHOTO`. |
| Link | No | No link-post type is documented |
| Single image | Yes | Photo post with 1 image |
| Multi-image | Yes | Photo post, up to 35 images |
| Video | Yes | Direct Post or inbox upload |
| Reels/shorts | Yes | Every TikTok video is short vertical-first video. This is the same video endpoint. |
| Stories | No | No Stories endpoint in the Content Posting API |

#### Access tier and app review
- The app must be approved for `video.publish` and `video.upload`.
- **Audit is required for public visibility.** The docs say "All content posted by unaudited clients will be restricted to private viewing mode." The init call can also fail with `unaudited_client_can_only_post_to_private_accounts`.
- A cap on the number of users for unaudited clients is not stated on the fetched pages. **UNVERIFIED**

---

### 5. YouTube Data API v3

- **Docs fetched:**
  - https://developers.google.com/youtube/v3/docs/videos/insert
  - https://developers.google.com/youtube/v3/docs/videos
  - https://developers.google.com/youtube/v3/determine_quota_cost
  - https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol
  - https://developers.google.com/youtube/v3/revision_history
  - https://support.google.com/youtube/answer/15424877 (Shorts classification)
- **API version:** **v3**.
- **Checked:** 2026-11-26

#### Operations relevant to POVU
| Operation | Method | Quota cost |
|---|---|---|
| Upload video | `videos.insert` (`POST https://www.googleapis.com/upload/youtube/v3/videos`) | **1 unit in its own Video Uploads bucket, default 100 calls/day** (see history below) |
| Update metadata, privacy, or schedule | `videos.update` | 50 |
| Delete | `videos.delete` | 50 |
| Read status and statistics | `videos.list` | 1 |
| List comments | `commentThreads.list` | 1 |
| Reply to a comment | `comments.insert` | 50 |
| Add to playlist | `playlistItems.insert` | 50 |
| Custom thumbnail | `thumbnails.set` | 50 (supports Shorts since 2026-11-03) |
| Default shared quota | — | 10,000 units/day across all methods except `videos.insert` and `search.list` |

**Quota history for `videos.insert`:**
- About 1600 units until 2025-12-04, when it dropped to about 100 units.
- Moved to its own bucket on 2026-06-01.
- The current reference reads "1 unit in the Video Uploads quota bucket", with "a limit of 100 calls per day".

#### Auth and scopes
- `videos.insert` needs one of:
  - `https://www.googleapis.com/auth/youtube.upload`
  - `…/auth/youtube`
  - `…/auth/youtubepartner`
  - `…/auth/youtube.force-ssl`
- The exact scope list for comments was not fetched. It is likely `youtube.force-ssl`. **UNVERIFIED**

#### Upload, async status, and reconciliation
1. **Resumable upload:** `POST …/videos?uploadType=resumable&part=…` with headers `X-Upload-Content-Length` and `X-Upload-Content-Type`. The session URI comes back in the `Location` header.
2. PUT the bytes. The response is 201 with the video resource; its `id` is the final video id.
3. **Resume:** send an empty PUT with `Content-Range: bytes */N`. The reply is `308 Resume Incomplete` plus a `Range` header. Chunks must be multiples of 256 KB (the last chunk is exempt). An expired session URI returns 404.
4. **Processing status:** call `videos.list` with `part=status,processingDetails`.
   - `status.uploadStatus`: deleted, failed, processed, rejected, uploaded.
   - `status.failureReason`: codec, conversion, emptyFile, invalidFile, tooSmall, uploadAborted.
   - `status.rejectionReason`: claim, copyright, duplicate, inappropriate, legal, length, termsOfUse, trademark, uploaderAccountClosed, uploaderAccountSuspended.
   - `processingDetails.processingStatus`: failed, processing, succeeded, terminated.
5. **Scheduling:** `status.publishAt` can be set only when `privacyStatus` is `private` and the video has never been published.
6. **Metrics:** `statistics.viewCount`, `likeCount`, `commentCount`. Views are counted "the moment a video begins to play". Co-views are included from 2026-11-16.
7. **Publish webhooks:** not documented for uploads. A PubSubHubbub channel feed exists but was not checked. **UNVERIFIED**

#### Limits
- **Max file size:** 256 GB. MIME types `video/*` or `application/octet-stream`.
- **Max duration for API uploads:** not stated on the fetched pages; it depends on the channel's verification state. **UNVERIFIED**

#### Content formats
| Format | API? | Notes |
|---|---|---|
| Text-only | Partial | The new `posts` resource (community posts, 2026-11-16) is a **pilot limited to select launch partners**, with GA planned for 2027. Not generally usable. |
| Link | No | No link-post type outside the `posts` pilot |
| Single image | No | Only via the `posts` pilot |
| Multi-image | No | Only via the `posts` pilot |
| Video | Yes | `videos.insert` |
| Shorts | Partial | No Shorts-specific API or flag. A video is classified as a Short when it is "square or vertical aspect ratio up to three minutes in length" (uploads on or after 2024-10-15 for standard channels). Upload through `videos.insert` like any other video. |
| Stories | No | No Stories API |
| Playlists | Yes | `playlistItems.insert` (50 units) |

#### Access tier and app review
- **Unverified projects:** since **2026-11-02**, videos uploaded from unverified API projects "are no longer restricted to private viewing mode". This reverses the 2020-07-28 policy. Uploads default to `public` when no privacy status is given; some may default to private depending on the creator's account settings.
- **Quota increases:** still require Google's audit and quota-extension form. That process was not fetched. **UNVERIFIED**
- **OAuth app verification:** Google's verification for sensitive YouTube scopes likely applies, but was not checked. **UNVERIFIED**

---

### 6. X API v2

- **Docs fetched:**
  - https://docs.x.com/x-api/posts/create-post
  - https://docs.x.com/x-api/media/quickstart/media-upload-chunked
  - https://docs.x.com/x-api/fundamentals/rate-limits
  - https://docs.x.com/x-api/getting-started/pricing
  - https://docs.x.com/changelog
  - https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code
- **API version:** **v2**.
- **Checked:** 2026-11-26

#### Operations relevant to POVU
| Operation | Endpoint | Notes |
|---|---|---|
| Create post | `POST /2/tweets` (`text`, `media.media_ids`, `poll`, `reply.in_reply_to_tweet_id`) | Synchronous; returns the post id |
| Edit post | Same endpoint, labeled "Create or Edit Post" | Edit fields and eligibility were not checked. **UNVERIFIED** |
| Delete post | `DELETE /2/tweets/:id` | |
| Read posts | `GET /2/tweets` | |
| Quote-post | `quote_tweet_id` | Requires an **Enterprise plan**; removed from self-serve tiers on 2026-04-20 |
| Replies | `reply.in_reply_to_tweet_id` | Since 2026-02-23, programmatic replies on self-serve tiers are allowed only when the original author has summoned the replier |
| Metrics | `public_metrics` / `non_public_metrics` fields on `GET /2/tweets` | Not fetched. **UNVERIFIED** |
| Read replies | Search by `conversation_id` | Not fetched. **UNVERIFIED** |

#### Auth and scopes
- OAuth 2.0 scopes: `tweet.read`, `tweet.write`, `users.read`, `media.write` (media upload), and `offline.access` (refresh token; otherwise the token lasts 2 hours).
- The create-post page lists `tweet.read`, `tweet.write`, and `users.read` for `POST /2/tweets`.

#### Upload, async status, and reconciliation
1. `POST /2/media/upload/initialize`.
2. `POST /2/media/upload/{id}/append`, with segments of at most 5 MB indexed from 0.
3. `POST /2/media/upload/{id}/finalize`.
4. If `processing_info` is returned, poll `GET /2/media/upload?command=STATUS&media_id=…` every `check_after_secs` until the state is `succeeded` or `failed`. States: `pending` → `in_progress` → `succeeded` or `failed`.
5. Attach the `media_id` to `POST /2/tweets`.

The old command-style `POST /2/media/upload` flow was replaced on 2026-09-01. Webhooks are not needed for posting.

#### Limits
- **Rate limits:**

  | Endpoint | Per user | Per app |
  |---|---|---|
  | `POST /2/tweets` | 100 / 15 min | 10,000 / 24 h |
  | `DELETE /2/tweets/:id` | 50 / 15 min | — |
  | Media initialize, append, finalize | 1,875 / 15 min | 180,000 / 24 h |

- **Media sizes:**
  - `tweet_image`: 5 MB.
  - `tweet_gif`: 15 MB.
  - `tweet_video`: 20 min and 8 GB by default; 125 min and 16 GB for Premium or verified accounts (as of 2026-09-01).
- **Per-post media:** up to 4 photos, or 1 GIF, or 1 video. The schema allows 20 ids, which conflicts with the guide's wording.
- **Poll:** 2–4 options, duration 5–10080 minutes.
- **Post text length:** not checked. **UNVERIFIED**

#### Content formats
| Format | API? | Notes |
|---|---|---|
| Text-only | Yes | |
| Link | Yes | Costs **$0.20** per post containing a URL, against $0.015 for a normal post |
| Single image | Yes | |
| Multi-image | Yes | Up to 4 photos |
| Video | Yes | Chunked v2 upload |
| Reels/shorts | Partial | No distinct short-video type; a vertical video is just a video |
| Stories | No | X has no Stories product or endpoint. **UNVERIFIED** as an explicit doc statement. |

#### Access tier and pricing
- **Pay-per-use** credits launched 2026-02-06, with "No subscriptions" and no minimum spend.
  - Create post: $0.015.
  - Post with a URL: $0.20.
  - Post read: $0.005.
  - User read: $0.010.
  - Owned reads: $0.001.
  - Pay-per-use is capped at 3M post reads per billing cycle. Above that requires Enterprise.
- **Basic and Pro:** the changelog entry of 2026-02-06 says "Basic and Pro plans remain available". An official forum post titled "Legacy X API Basic Plans Are Moving to Pay-Per-Use" (May 2026) suggests they are being phased out, but it returned 403 and could not be read. **UNVERIFIED**
- **Legacy Free tier:** recently active users got a one-time $10 voucher. Whether a Free tier still exists is **UNVERIFIED**.
- **Enterprise:** custom rate limits; required for quote-posts and high read volume.

---

### Cross-provider summary for POVU

| Format | Facebook Page | Instagram | LinkedIn | TikTok | YouTube | X |
|---|---|---|---|---|---|---|
| Text-only | Yes | No | Yes | No | Partial (posts pilot) | Yes |
| Link | Yes | No | Yes (manual card) | No | No | Yes ($0.20) |
| Single image | Yes | Yes | Yes | Yes | No | Yes |
| Multi-image/carousel | Partial (UNVERIFIED) | Yes (20) | Yes (2–20, organic) | Yes (35) | No | Yes (4) |
| Video | Yes | Yes | Yes | Yes | Yes | Yes |
| Reels/shorts | Yes (30/24h) | Yes | Partial | Yes | Partial (auto-classified) | Partial |
| Stories | Yes | Yes | No | No | No | No |
| Async status poll | `GET /{video_id}?fields=status` | `status_code` on container | asset `status` + post `lifecycleState` | `status/fetch` by `publish_id` | `videos.list` status/processingDetails | media STATUS (media only) |
| Final id differs from job id | Yes (video_id → post) | Yes (container → media id) | No (`x-restli-id`) | Yes (`publish_id` → `publicaly_available_post_id`) | No | No |
| Gate for public posting to others' accounts | App Review + Advanced Access + Business Verification | App Review + Advanced Access + Business Verification | Community Mgmt API vetting (Dev → Standard tier) | TikTok audit (unaudited = private only) | None for privacy since 2026-11-02; quota audit for more than 100 uploads/day | Paid pay-per-use credits |


Method: official developer documentation fetched on 2026-11-26. Every fact below comes from a page listed under "Docs fetched" unless it is marked **UNVERIFIED**. Facts marked **UNVERIFIED** come from memory, SDK source, third-party pages, or search snippets only; they must be checked before implementation. Version numbers are given only where an official page states them.

## Mail, calendar and voice APIs

### Gmail API v1

- Docs fetched: https://developers.google.com/workspace/gmail/api/guides/push ; https://developers.google.com/workspace/gmail/api/reference/quota ; https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send
- API version: v1 (path `/gmail/v1/`).
- Checked: 2026-11-26
- Read/write operations relevant to POVU:
  - Send: `POST https://gmail.googleapis.com/gmail/v1/users/{userId}/messages/send` (metadata) or `POST https://gmail.googleapis.com/upload/gmail/v1/users/{userId}/messages/send` (media upload). `userId` = email or `me`.
  - Change feed: `history.list` with `startHistoryId` = last stored historyId.
  - Push: `users.watch` with `topicName` (`projects/{p}/topics/{t}`), optional `labelIds` + `labelFilterBehavior: INCLUDE`.
- Auth & scopes: OAuth 2.0. `messages.send` accepts any of `https://mail.google.com/`, `gmail.modify`, `gmail.compose`, `gmail.send`. Use `gmail.send` (least privilege) for outbound only.
- Async/status/reconciliation:
  - Pub/Sub push: create a topic and a push (HTTPS) or pull subscription; grant publish to `gmail-api-push@system.gserviceaccount.com`. Domain-restricted-sharing org policies can block this grant.
  - The push body is a Pub/Sub message; `message.data` is base64url JSON `{"emailAddress": ..., "historyId": ...}`.
  - `watch` returns `historyId` + `expiration`. It must be re-called at least every 7 days; Google recommends once per day.
  - Max 1 notification/second per watched user; excess notifications are dropped. Notifications can be delayed or dropped, so fall back to periodic `history.list`.
  - Pub/Sub push endpoint authentication (OIDC token on push subscription): **UNVERIFIED** (not on the fetched pages).
- Limits/quotas: 1,200,000 quota units/min per project; 6,000 units/min per user per project. Costs: `messages.send` 100, `drafts.send` 100, `watch` 100, `history.list` 2, `messages.list` 5, `messages.get` 20 (60 for `format=full|raw|html`). Max send size: not stated on the send reference page (**UNVERIFIED**).
- Access tier/go-live: OAuth consent screen verification for sensitive scopes (`gmail.send`) and restricted scopes (`gmail.modify`, `mail.google.com`) with security assessment: **UNVERIFIED** (not fetched).
- Supported payload/channel types: RFC 2822 email (raw base64url) via REST; push notifications via Cloud Pub/Sub.
- Kenya relevance: global Google Workspace/Gmail service; no country restriction on the fetched pages.

### Microsoft Graph v1.0 (mail, calendar, change notifications)

- Docs fetched: https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks ; https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0 ; https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0
- API version: v1.0 (`https://graph.microsoft.com/v1.0`).
- Checked: 2026-11-26
- Read/write operations relevant to POVU:
  - Send mail: `POST /me/sendMail` or `POST /users/{id|upn}/sendMail`. JSON (`message`, `saveToSentItems`) or MIME (base64, `Content-Type: text/plain`). Returns `202 Accepted` with no body. 202 means accepted, not delivered; Exchange Online limits apply.
  - Subscriptions: `POST /subscriptions`, `PATCH /subscriptions/{id}` (renew), `DELETE /subscriptions/{id}`, plus reauthorize. Outlook resources include message, event, contact.
  - Calendar event CRUD endpoints and their permissions (`Calendars.ReadWrite`): **UNVERIFIED** (not fetched).
- Auth & scopes: Bearer token (Microsoft identity platform). `sendMail` needs `Mail.Send` (delegated work/school, delegated personal, or application). Admin consent requirements for application permissions: **UNVERIFIED**.
- Async/status/reconciliation:
  - Validation: on create, Graph POSTs `?validationToken=...` to `notificationUrl` (and to `lifecycleNotificationUrl` if set). Within 10 seconds, return `200 OK`, `Content-Type: text/plain`, body = URL-decoded token. If validation fails, no subscription is created.
  - `clientState`: max 128 chars. The webhooks guide says it is required (the resource reference marks it Optional); validate it on every notification and reject mismatches.
  - Delivery: a 2xx within 3 seconds counts as delivered. Return `202` after queueing if processing takes longer. Non-2xx or timeout triggers retries for up to 4 hours with exponential backoff (10 s timeout on retries).
  - Throttling: "slow" if >10% of responses exceed 3 s in 10 min (10-min delay); "drop" if >15% exceed 10 s (notifications dropped for 10 min, unrecoverable).
  - Lifecycle notifications (`lifecycleNotificationUrl`): `reauthorizationRequired`, `subscriptionRemoved`, `missed`. The endpoint access token generally expires within 1 hour; renewing the subscription refreshes it.
  - Duplicate subscription (same changeType+resource) returns `409 Conflict`.
- Limits/quotas: Outlook message/event/contact max subscription lifetime is 10,080 minutes (under 7 days), or 1,440 minutes (under 1 day) with resource data. Any expiration under 45 minutes is raised to 45 minutes. Message notification latency: average under 1 minute, maximum 3 minutes; event latency is listed as unknown.
- Access tier/go-live: app registration in Entra ID; publisher verification/admin consent for multi-tenant apps: **UNVERIFIED**.
- Supported payload/channel types: JSON or MIME email; webhook (HTTPS), Event Hubs, or Event Grid notification delivery.
- Kenya relevance: global Microsoft 365 service; no country restriction on the fetched pages.

### Google Calendar API v3 (push notification channels)

- Docs fetched: https://developers.google.com/workspace/calendar/api/guides/push ; https://developers.google.com/workspace/calendar/api/v3/reference/events/watch
- API version: v3.
- Checked: 2026-11-26
- Read/write operations relevant to POVU: `POST https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events/watch` (`primary` allowed); `POST https://www.googleapis.com/calendar/v3/channels/stop` with `id` + `resourceId`. Event insert/update/list endpoints and the `syncToken` incremental sync flow: **UNVERIFIED** (not on the fetched push guide).
- Auth & scopes: OAuth 2.0. `events.watch` accepts any of `calendar`, `calendar.readonly`, `calendar.events`, `calendar.events.readonly`, `calendar.app.created`, `calendar.events.freebusy`, `calendar.events.owned`, `calendar.events.owned.readonly`, `calendar.events.public.readonly`.
- Async/status/reconciliation:
  - Watch body: `id` (unique, ≤64 chars, UUID recommended), `type: "web_hook"`, `address` (HTTPS with a valid, trusted certificate), optional `token` (≤256 chars, echoed back; no secrets), optional `expiration` (Unix ms).
  - A `sync` message is sent first and may arrive before the watch response.
  - Headers: `X-Goog-Channel-ID`, `X-Goog-Message-Number` (sync = 1; increasing but not sequential), `X-Goog-Resource-ID`, `X-Goog-Resource-State` (`sync`/`exists`/`not_exists`), `X-Goog-Resource-URI`, plus `X-Goog-Channel-Expiration` and `X-Goog-Channel-Token` when set.
  - Notifications have no body; call the API to fetch changes. Delivery is not 100% reliable, so also sync periodically.
  - No automatic renewal: create a new channel (new `id`) before expiry and stop the old one; brief overlap is allowed.
  - Acknowledge with 200/201/202/204/102. 500/502/503/504 trigger retries with exponential backoff.
- Limits/quotas: default/max channel lifetime is not stated on the guide (the effective expiration is whichever is more restrictive, the request or the API's internal limit). Specific max TTL: **UNVERIFIED**.
- Access tier/go-live: domain verification of the webhook address is not mentioned on the current guide; only a valid HTTPS certificate is required. OAuth verification for sensitive calendar scopes: **UNVERIFIED**.
- Supported payload/channel types: `web_hook` channel only (HTTPS POST, headers only).
- Kenya relevance: global service.

### Africa's Talking Voice API

- Docs fetched: https://developers.africastalking.com/docs/voice/handle_calls and /docs/voice/overview returned HTTP 403 to automated fetch. https://help.africastalking.com/... also returned 403. Fallback: the official SDK source https://raw.githubusercontent.com/AfricasTalkingLtd/africastalking-python/master/africastalking/Voice.py and .../Service.py (owner AfricasTalkingLtd).
- API version: no version string in the SDK paths (**UNVERIFIED**).
- Checked: 2026-11-26
- Read/write operations relevant to POVU (from the official SDK source):
  - Make call: `POST https://voice.<domain>/call`, form-encoded `username`, `from`, `to` (comma-joined numbers).
  - Queue status: `POST /queueStatus` (`username`, `phoneNumbers`).
  - Media upload: `POST /mediaUpload` (`username`, `phoneNumber`, `url`).
  - Exact live/sandbox voice hostnames (presumed `voice.africastalking.com` / `voice.sandbox.africastalking.com`; the SDK builds `https://voice.` + domain): **UNVERIFIED**.
  - `clientRequestId` parameter: **UNVERIFIED**.
- Auth & scopes: header `apiKey: <key>`; username `sandbox` selects the sandbox (`https://api.sandbox.africastalking.com` vs `https://api.africastalking.com` for the general API). No OAuth scopes.
- Async/status/reconciliation: the voice callback URL (configured per phone number) receives call events and must return XML actions. Callback parameters (`isActive`, `sessionId`, `direction`, `callerNumber`, `durationInSeconds`, `amount`, `currencyCode`, `hangupCause`) and XML actions (`Say`, `Play`, `GetDigits`, `Dial`, `Record`, `Enqueue`, `Dequeue`, `Conference`, `Redirect`, `Reject`): **UNVERIFIED** (official docs blocked). Malformed XML aborts calls: **UNVERIFIED** (help-centre snippet only). Signature verification on callbacks: **UNVERIFIED** (none known).
- Limits/quotas: **UNVERIFIED**.
- Access tier/go-live: whether the Voice API works in the sandbox (sources conflict; one tutorial says live calls only): **UNVERIFIED**. Production needs a provisioned voice number: **UNVERIFIED**.
- Supported payload/channel types: outbound calls, inbound calls, IVR via XML actions, call queues, media upload (SDK-confirmed methods only).
- Kenya relevance: Nairobi-headquartered, Kenya-native provider; local numbers and KES billing: **UNVERIFIED** (not fetched).

### Twilio Programmable Voice

- Docs fetched: https://www.twilio.com/docs/voice/api/call-resource (first 100k chars) ; https://www.twilio.com/docs/usage/webhooks/webhooks-security
- API version: `2010-04-01` (in the REST path).
- Checked: 2026-11-26
- Read/write operations relevant to POVU:
  - Create call: `POST https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Calls.json`. `To` and `From` are required; instructions come via `Url`, `Twiml` (ignored if `Url` is also given), or `ApplicationSid`.
  - Fetch call: `GET .../Calls/{Sid}.json`. This is eventually consistent; prefer status callbacks.
  - Update call (redirect/hangup): **UNVERIFIED** (section not read).
- Auth & scopes: HTTP Basic with an API Key SID/secret (examples), or Account SID/Auth Token (local testing).
- Async/status/reconciliation:
  - `StatusCallback` URL + `StatusCallbackMethod` (GET/POST, default POST). `StatusCallbackEvent`: `initiated`, `ringing`, `answered`, `completed` (default `completed` only).
  - Call statuses: `queued`, `ringing`, `in-progress`, `completed`, `busy`, `failed`, `no-answer`, `canceled`.
  - `X-Twilio-Signature`: HMAC-SHA1 keyed by the Auth Token, over the full URL plus POST params sorted alphabetically and concatenated. Optional shared-key signing (HMAC-SHA256 or SHA1) is named in the `X-Twilio-Webhooks-Signature-Settings` header (recommended for production). JSON bodies: Twilio adds a `bodySHA256` query param (SHA-256 of the raw body) to validate. Use the URL exactly as received and an SDK validator. Base64 output encoding is not stated explicitly on the page (**UNVERIFIED**, widely assumed).
  - Webhook retry / connection-override behaviour: **UNVERIFIED** (not on the fetched page).
- Limits/quotas: outbound `/Calls` POSTs are limited by CPS, default 1 CPS (excess is queued); up to 5 CPS with an approved Business Profile. Inbound and `<Dial>` calls are not CPS-limited.
- Access tier/go-live: trial-account restrictions (verified numbers only) and Kenya regulatory bundle/number availability: **UNVERIFIED**.
- Supported payload/channel types: PSTN calls, TwiML voice instructions (verb list `Say`, `Play`, `Gather`, `Dial`, `Record`, etc.: **UNVERIFIED**, not fetched), status callbacks.
- Kenya relevance: outbound calls to Kenyan numbers and Kenyan number availability: **UNVERIFIED**.

## Data APIs

### Snowflake SQL API v2

- Docs fetched: https://docs.snowflake.com/en/developer-guide/sql-api/submitting-requests ; https://docs.snowflake.com/en/developer-guide/sql-api/authenticating ; https://docs.snowflake.com/en/developer-guide/sql-api/handling-responses
- API version: v2 (`/api/v2/statements`).
- Checked: 2026-11-26
- Read/write operations relevant to POVU:
  - `POST /api/v2/statements` with body `statement`, `bindings` (`?` placeholders; not allowed in multi-statement), `warehouse`, `database`, `schema`, `role` (case-sensitive), `timeout` (falls back to `STATEMENT_TIMEOUT_IN_SECONDS`).
  - Multi-statement requests are separated by `;`.
  - `GET /api/v2/statements/{statementHandle}` to poll, `POST /api/v2/statements/{statementHandle}/cancel` to cancel.
- Auth & scopes:
  - Key-pair JWT: RS256. `iss` = `<ACCOUNT>.<USER>.SHA256:<fingerprint>` (uppercase; periods in the account become hyphens), `sub` = `<ACCOUNT>.<USER>`, `iat`, `exp`. Valid at most 1 hour.
  - OAuth: `/oauth/authorize` then `/oauth/token-request`, with refresh tokens.
  - Programmatic access token.
  - Workload identity federation: header `Authorization: Bearer WIF.{AWS|AZURE|GCP|OIDC}.{token}` with token type `WORKLOAD_IDENTITY_FEDERATION`.
  - Header `Authorization: Bearer <token>`; optional `X-Snowflake-Authorization-Token-Type: KEYPAIR_JWT | OAUTH | PROGRAMMATIC_ACCESS_TOKEN` (inferred if omitted).
- Async/status/reconciliation:
  - `?async=true` requests async execution; synchronous completion is never guaranteed.
  - `200` returns a ResultSet; `202` returns QueryStatus with `statementHandle` + `statementStatusUrl` (running >45 s or async); `422` is QueryFailureStatus; `429` means overloaded, so retry.
  - Idempotency: resubmit with the same `requestId` plus `retry=true`; already-succeeded statements are skipped.
  - Partitions: `resultSetMetaData.partitionInfo` lists them; partition 0 is in the first response. Fetch others with `?partition=N`; those responses are gzip and carry no metadata.
  - Multi-statement 200 returns `statementHandles`; poll each.
- Limits/quotas: concurrency is subject to Snowflake limits (429). Numeric limits are not stated (**UNVERIFIED**).
- Access tier/go-live: needs a Snowflake account plus a user with an assigned RSA public key (`RSA_PUBLIC_KEY_FP` visible via `DESCRIBE USER`). No app review.
- Supported payload/channel types: SQL statements (single/multi), JSON result sets.
- Kenya relevance: cloud regions near Kenya (e.g. AWS af-south-1) and availability: **UNVERIFIED**.

### Google BigQuery REST API v2

- Docs fetched: https://docs.cloud.google.com/bigquery/quotas (full) ; https://docs.cloud.google.com/bigquery/docs/write-api ; https://docs.cloud.google.com/bigquery/docs/reference/rest/v2/jobs/insert (cloud.google.com URLs 301-redirect to docs.cloud.google.com)
- API version: v2.
- Checked: 2026-11-26
- Read/write operations relevant to POVU:
  - `jobs.insert`: `POST https://bigquery.googleapis.com/bigquery/v2/projects/{projectId}/jobs` for load or query jobs. Media variant: `POST https://bigquery.googleapis.com/upload/bigquery/v2/projects/{projectId}/jobs`, multipart (config + data).
  - Streaming: legacy `tabledata.insertAll`, documented in quotas as "Storage Write API (REST)/streaming inserts", versus the Storage Write API (gRPC).
- Auth & scopes: `jobs.insert` accepts `bigquery`, `cloud-platform`, `devstorage.full_control`, `devstorage.read_only`, `devstorage.read_write`. Service accounts are the norm for server-side ERP.
- Async/status/reconciliation:
  - Jobs are async; poll `jobs.get` (1,000 req/s per project).
  - Idempotent retry via a client-set `jobReference.jobId`: **UNVERIFIED** (not stated on the jobs.insert page).
  - Storage Write API: exactly-once requires an application-created **committed** stream with client offsets. The **default** stream is at-least-once and immediately queryable. **Pending** streams use an atomic commit (batch alternative to load jobs). **Buffered** is advanced (Beam).
  - `insertAll` dedup via `insertId` (≤128 chars).
  - Google recommends the gRPC Storage Write API over REST for new projects; gRPC ingestion is cheaper.
- Limits/quotas:
  - Load jobs: 1,500 per table per day and 100,000 per project per day (failures count); max load job size 15 TB.
  - Queued interactive queries: 1,000 per project. Query request size 10 MB.
  - Streaming inserts (REST): 1 GB/s per project in US/EU multi-regions, 300 MB/s elsewhere; 10 MB per row; 10 MB per request; 50,000 rows per request max (≈500 recommended).
  - Storage Write API (gRPC): 3 GB/s in US/EU multi-regions, 300 MB/s elsewhere; 5,000 concurrent connections per region (20,000 in US/EU); `CreateWriteStream` 10,000/h per project per region; `AppendRows` 20 MB.
  - API: 100 req/s per user per method; 300 concurrent requests per user; `tables.insert` 10/s per user.
  - `tabledata.list`: 7.5 GB/min (US/EU) or 3.7 GB/min elsewhere; 100,000 rows per response.
- Access tier/go-live: GCP project with billing (sandbox limits: **UNVERIFIED**).
- Supported payload/channel types: load jobs (CSV, JSON, Avro, Parquet, ORC), query jobs, REST streaming inserts, gRPC Storage Write streams.
- Kenya relevance: GCP regions in Africa (e.g. Johannesburg) and data-residency fit for Kenyan DPA: **UNVERIFIED**.

### Google Search Console API

- Docs fetched: https://developers.google.com/webmaster-tools/v1/searchanalytics/query ; https://developers.google.com/webmaster-tools/limits
- API version: the path is `webmasters/v3` (the docs live under `/webmaster-tools/v1/`; a "Search Console API v1" naming for other resources such as URL Inspection is **UNVERIFIED**).
- Checked: 2026-11-26
- Read/write operations relevant to POVU: read-only `POST https://www.googleapis.com/webmasters/v3/sites/{siteUrl}/searchAnalytics/query`. `siteUrl` is a URL-prefix (`https://www.example.com/`) or `sc-domain:example.com`.
  - Request body: `startDate`/`endDate` (YYYY-MM-DD, Pacific Time, inclusive); `dimensions` (incl. `date`, `hour`); `type` (`web` default, `discover`, `googleNews`, `news`, `image`, `video`, `webMultimodal`; replaces deprecated `searchType`); `dimensionFilterGroups` (`and` only); `aggregationType` (`auto`, `byPage`, `byProperty`, `byNewsShowcasePanel`); `rowLimit` (default 1,000, range 1–25,000); `startRow` (paging); `dataState` (`final` default, `all`, `hourly_all`).
- Auth & scopes: `https://www.googleapis.com/auth/webmasters.readonly` (sufficient) or `.../webmasters`.
- Async/status/reconciliation: synchronous. Page through `startRow` in 25,000 steps. The API returns top rows within internal limits, not guaranteed all rows. Use `dataState=final` for reconciled numbers. No webhooks.
- Limits/quotas:
  - Search Analytics: per-site 1,200 QPM; per-user 1,200 QPM; per-project 40,000 QPM and 30,000,000 QPD.
  - Load quota: short-term window is 10 minutes (wait 15 min if exceeded); long-term window is 1 day. Page+query grouping is the most expensive.
  - URL Inspection: per-site 600 QPM and 2,000 QPD; per-project 15,000 QPM and 10,000,000 QPD.
- Access tier/go-live: the user must be verified owner/user of the property. OAuth verification for the `webmasters.readonly` sensitive scope: **UNVERIFIED**.
- Supported payload/channel types: JSON search analytics rows (clicks, impressions, ctr, position).
- Kenya relevance: `country` dimension/filter supports Kenya (ISO `ken`): **UNVERIFIED** (filter values not on the fetched page).

## Signature APIs

### DocuSign eSignature REST API v2.1

- Docs fetched: https://developers.docusign.com/platform/webhooks/connect/hmac/ ; https://developers.docusign.com/platform/auth/jwt/jwt-get-token/ ; https://developers.docusign.com/platform/go-live/ ; https://developers.docusign.com/docs/esign-rest-api/esign101/rules-and-limits/ ; https://developers.docusign.com/docs/esign-rest-api/reference/envelopes/envelopes/create/ (first 100k chars)
- API version: v2.1 (`/restapi/v2.1/`).
- Checked: 2026-11-26
- Read/write operations relevant to POVU:
  - Create envelope: `POST {base_uri}/restapi/v2.1/accounts/{accountId}/envelopes`. `status: "sent"` sends immediately; `"created"` (or omitted) saves a draft.
  - Status values: `created`, `sent`, `delivered`, `signed`, `completed`, `declined`, `voided` (also `Processing` when `asynchronous=true`).
  - Per-envelope Connect webhook via `eventNotification` in the envelope body.
  - Status reads: `GET` envelope / `listStatusChanges`.
  - Hosts: demo `https://demo.docusign.net/restapi`; production `https://www.docusign.net/restapi`. Production clients must use the account `base_uri` from `/oauth/userinfo`.
- Auth & scopes: JWT Grant, RS256-signed. Claims: `iss` = integration key, `sub` = user GUID, `aud` = `account-d.docusign.com` (demo) or `account.docusign.com` (prod) without `https://`, `iat`/`exp`, `scope: "signature impersonation"`. One-time consent per scope set. Access token lasts 1 hour with no refresh token; renew ~15 min early.
- Async/status/reconciliation:
  - Connect HMAC: up to 100 keys; one header per key `X-Docusign-Signature-1..N` holding HMAC-SHA256 of the raw body (including line endings). Accept if any header matches. Base64 encoding of the value is not stated on the page (**UNVERIFIED**).
  - Connect retry schedule: **UNVERIFIED** (not on the HMAC page).
  - Polling: max one GET status per envelope per 15 min (20 min recommended). DocuSign recommends Connect over polling. Use `listStatusChanges` with overlapping windows for reconciliation.
- Limits/quotas: 3,000 API calls/hour per account (shared; resets on the hour; `X-RateLimit-Limit` header). Burst per 30 s: 200 (demo) / 500 (prod). Uploads 32 MB via API (chunked up to 52 MB). Envelope 200 MB total. Incoming request ~35–36 MB.
- Access tier/go-live:
  - Promote the integration key from the developer account to a paid production account. The key is copied; secrets and redirect URIs must be re-created.
  - Identity verification in the Developer Console for most accounts.
  - Statuses: Ready to submit → Pending approval → (In Review, 24–48 h manual) → App is live.
  - Public integrations need Partner Program membership; embedded integrations need ISV Embed licensing.
  - A "20 successful demo API calls" requirement is not stated on the current page (**UNVERIFIED** / possibly retired).
- Supported payload/channel types: PDF/DOCX documents in envelopes, remote email signing, embedded signing; Connect webhooks (JSON/XML).
- Kenya relevance: global service; enforceability under the Kenya Information and Communications Act / Business Laws (Amendment) Act e-signature provisions: **UNVERIFIED**.

### Adobe Acrobat Sign REST API v6

- Docs fetched: https://developer.adobe.com/acrobat-sign/docs/overview/developer_guide/gstarted ; https://developer.adobe.com/acrobat-sign/docs/overview/acrobat_sign_events/ ; https://developer.adobe.com/acrobat-sign/docs/overview/developer_guide/apiusage (the original webhooks URL returned 404)
- API version: v6 (`/api/rest/v6/`).
- Checked: 2026-11-26
- Read/write operations relevant to POVU:
  - `POST /api/rest/v6/transientDocuments`: multipart, one file per request, returns `transientDocumentId`, retained 7 days.
  - `POST /api/rest/v6/agreements`: `fileInfos[].transientDocumentId`, `participantSetsInfo` (email, `order`, `role`), `signatureType` `ESIGN|WRITTEN`, `state: IN_PROCESS` to send.
  - `GET /api/rest/v6/agreements/{id}` for `status`; `GET /agreements/{id}/combinedDocument` (optional `versionId`).
  - Base URI: the API access point is returned in the OAuth token response, per shard. A `GET /api/rest/v6/baseUris` endpoint is not documented on the fetched page (**UNVERIFIED**).
- Auth & scopes:
  - OAuth 2.0 authorization code: auth code valid 5 minutes; `POST /oauth/v2/token` returns access + refresh token and the api_access_point.
  - App domain is CUSTOMER (own account) or PARTNER (other accounts; certification required for full access).
  - Scopes: `user_read`, `user_write`, `user_login`, `agreement_read`, `agreement_write`, `agreement_send`, `widget_read`/`_write`, `library_read`/`_write`, `workflow_read`/`_write`, with modifiers `:self` (default), `:group`, `:account` (admin; Business/Enterprise).
  - Webhook OAuth scope names (`webhook_read`/`webhook_write`/`webhook_retention`): **UNVERIFIED**.
  - Integration keys: **UNVERIFIED** (not on the fetched pages).
- Async/status/reconciliation:
  - Verification of intent: an HTTPS GET with header `X-ADOBESIGN-CLIENTID` (the app client ID). Return 2XX and echo the ID in response header `X-AdobeSign-ClientId` or JSON `{"xAdobeSignClientId": ...}`. Every POST notification carries the header and needs the same echo. Re-run when a webhook is re-activated.
  - Must respond within 5 s (`WEBHOOK_REQUEST_TIMEOUT_VALIDATION`). Retries start at 30 s, doubling to a 12 h max, until 72 h (~15 retries); then the webhook is disabled and events are lost. Check with `GET /webhooks/{id}`.
  - Scopes: ACCOUNT, GROUP, USER, RESOURCE (USER/RESOURCE are API-only).
  - Events include `AGREEMENT_CREATED`, `AGREEMENT_ACTION_REQUESTED`, `AGREEMENT_WORKFLOW_COMPLETED`.
  - Conditional payload flags: `includeDetailedInfo`, `includeDocumentsInfo`, `includeParticipantsInfo`, `includeSignedDocuments` (base64 signed PDF, only on WORKFLOW_COMPLETED).
  - Optional mutual TLS; TLS 1.2 only.
- Limits/quotas: throttled requests return 429 `THROTTLING_TOO_MANY_REQUESTS` with `Retry-After`/`retryAfter`; limits per minute/hour/day per user. GET polling threshold: 3 identical calls per 1 min (GLOBAL/ENTERPRISE/DEVELOPER) or per 3 min (other tiers). Numeric per-tier limits: **UNVERIFIED**.
- Access tier/go-live: developer accounts are free, but documents are watermarked/not legally binding (**UNVERIFIED**, not on the fetched pages). PARTNER apps require certification.
- Supported payload/channel types: PDF/Office documents (transient upload), e-sign or written signatures, webhooks (JSON).
- Kenya relevance: global service; local legal enforceability: **UNVERIFIED**.

## Payment APIs

### Pesapal API 3.0

- Docs fetched: https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/api-reference , /registeripnurl , /submitorderrequest , /gettransactionstatus , /authentication. All returned a server error page ("Infinite loop detected in JError") on 2026-11-26; developers.pesapal.com did not resolve. Only official-page **search snippets** were readable.
- API version: 3.0 (JSON), per the official doc URL path `api-30-json`.
- Checked: 2026-11-26
- Read/write operations relevant to POVU:
  - From official snippets: RegisterIPN must be called before order requests and returns an IPN ID. That ID is passed as `notification_id` in SubmitOrderRequest. SubmitOrderRequest uses Bearer token auth from the auth step. After payment the customer is redirected to the `callback_url` supplied in SubmitOrderRequest. GetTransactionStatus is listed in the API 3.0 index.
  - Endpoint paths `/api/Auth/RequestToken`, `/api/URLSetup/RegisterIPN`, `/api/URLSetup/GetIpnList`, `/api/Transactions/SubmitOrderRequest`, `/api/Transactions/GetTransactionStatus?orderTrackingId=`: **UNVERIFIED** (third-party tutorials/SDKs).
  - Base URLs sandbox `https://cybqa.pesapal.com/pesapalv3` and live `https://pay.pesapal.com/v3`: **UNVERIFIED** (community SDK README).
  - Refund / cancel order / recurring endpoints: **UNVERIFIED** (the "Additional API3 endpoints" page requires login).
- Auth & scopes: `consumer_key` + `consumer_secret` exchanged for a Bearer token. Token lifetime (commonly cited as 5 minutes): **UNVERIFIED**.
- Async/status/reconciliation: the IPN notifies `OrderTrackingId`/`OrderMerchantReference`/`OrderNotificationType`; the merchant then calls GetTransactionStatus and responds with an acknowledgement JSON. Status codes (0 INVALID, 1 COMPLETED, 2 FAILED, 3 REVERSED): **UNVERIFIED**. No signature scheme is known on IPN, so always re-query status (**UNVERIFIED**).
- Limits/quotas: **UNVERIFIED**.
- Access tier/go-live: sandbox demo merchant credentials and production merchant onboarding/KYC: **UNVERIFIED**.
- Supported payload/channel types: hosted checkout (iframe/redirect) covering M-Pesa, Airtel Money, cards (Visa/Mastercard), bank: **UNVERIFIED** (not readable on official pages today).
- Kenya relevance: Kenya-based PSP with KES support: **UNVERIFIED** (official site unreachable during check).

### Flutterwave v3

- Docs fetched: https://developer.flutterwave.com/docs/webhooks ; https://developer.flutterwave.com/docs/transaction-verification (v3.0/docs/webhooks and v3.0/docs/flutterwave-standard-1 returned 404). Official-domain search snippets: /v3.0/docs/flutterwave-standard-1, /reference/charge-via-mpesa, /docs/refunds, /reference/transaction-refund, /v3.0/docs/webhooks.
- API version: v3 (`/v3/` paths). The developer site now also hosts v4 docs; v4 uses a different signature mechanism (search snippet).
- Checked: 2026-11-26
- Read/write operations relevant to POVU:
  - Standard (hosted): server `POST /v3/payments` with a unique `tx_ref`, amount, currency, `redirect_url`, customer, optional `payment_options`, and `configurations.session_duration` (max 1,440 min). Returns a hosted payment link. Flutterwave redirects to `redirect_url` with `status`, `tx_ref`, `transaction_id` (from official-domain search snippets; full page 404 on fetch).
  - Verify: `GET /v3/transactions/{id}/verify` (Bearer secret key). Fetched page; `verify_by_reference?tx_ref=` is **UNVERIFIED**.
  - M-Pesa direct charge: `POST /v3/charges?type=mpesa` with KES, phone, email, `tx_ref`. The initial response is pending; completion arrives by webhook (search snippet of the official reference).
  - Refund: `POST https://api.flutterwave.com/v3/transactions/{id}/refund` with optional `amount` (partial) and `comments`. Mobile-money refunds take 3–5 days (the reference also says 3–15 working days); pending momo refund status is `pending-momo` (search snippet).
- Auth & scopes: Bearer secret key. No OAuth scopes.
- Async/status/reconciliation:
  - Webhook header `verif-hash` must equal the dashboard secret hash; discard if missing or mismatched (use a timing-safe compare).
  - Respond 200 within 60 s. If retries are enabled in the dashboard, Flutterwave retries 3 times at 30-minute intervals.
  - Events include `charge.completed`, `transfer.completed`, `subscription.cancelled`, plus refund payloads.
  - Always verify before fulfilment: `tx_ref` matches, `status == "successful"`, currency matches, amount ≥ expected.
- Limits/quotas: **UNVERIFIED**.
- Access tier/go-live: test vs live keys and business KYC/compliance approval before live: **UNVERIFIED** (not on the fetched pages).
- Supported payload/channel types: hosted Standard checkout, card, M-Pesa (KES), mobile money, bank transfer, refunds, transfers/payouts. Bank transfer availability for KES specifically: **UNVERIFIED**.
- Kenya relevance: the M-Pesa charge uses KES (official reference snippet: currency defaults to/expects KES). Kenyan merchant onboarding and settlement in KES: **UNVERIFIED**.

### Safaricom M-Pesa Daraja

- Docs fetched: https://developer.safaricom.co.ke/ (landing page only; no endpoint content). https://developer.safaricom.co.ke/APIs/MpesaExpressSimulate and /Documentation returned 404; /apis hung up. The portal is a JS app that is not fetchable, so **all endpoint details below are UNVERIFIED** (from third-party SDKs/tutorials and prior knowledge).
- API version: path-embedded `v1` per endpoint (**UNVERIFIED**).
- Checked: 2026-11-26
- Read/write operations relevant to POVU (all **UNVERIFIED**):
  - OAuth `GET /oauth/v1/generate?grant_type=client_credentials` (Basic consumer key:secret; token ~3600 s).
  - STK Push `POST /mpesa/stkpush/v1/processrequest`: `BusinessShortCode`, `Password` = base64(shortcode+passkey+timestamp), `Timestamp` (YYYYMMDDHHmmss), `TransactionType` `CustomerPayBillOnline`/`CustomerBuyGoodsOnline`, `Amount`, `PartyA`, `PartyB`, `PhoneNumber` (2547XXXXXXXX), `CallBackURL`, `AccountReference`, `TransactionDesc`.
  - STK Query `POST /mpesa/stkpushquery/v1/query`.
  - C2B Register URL `POST /mpesa/c2b/v1/registerurl` (or v2) with `ConfirmationURL`/`ValidationURL`/`ResponseType`.
  - B2C `POST /mpesa/b2c/v1/paymentrequest` (or v3) with `SecurityCredential` (RSA-encrypted initiator password).
  - Transaction Status `POST /mpesa/transactionstatus/v1/query`.
  - Reversal `POST /mpesa/reversal/v1/request`.
  - Hosts: sandbox `https://sandbox.safaricom.co.ke`, production `https://api.safaricom.co.ke`.
- Auth & scopes: OAuth client-credentials bearer token; B2C/reversal/status also need an initiator plus a SecurityCredential encrypted with Safaricom's public certificate (**UNVERIFIED**).
- Async/status/reconciliation (all **UNVERIFIED**):
  - STK returns `MerchantRequestID`/`CheckoutRequestID`; the result is POSTed to `CallBackURL` with `ResultCode` (0 = success) and `CallbackMetadata` (`MpesaReceiptNumber`, `Amount`, `PhoneNumber`, `TransactionDate`).
  - B2C/status/reversal results come via `ResultURL`/`QueueTimeOutURL`.
  - No callback signature: secure callbacks via IP allow-listing and re-querying (STK query / transaction status).
  - Idempotency: dedupe on `CheckoutRequestID` and `MpesaReceiptNumber`.
- Limits/quotas: **UNVERIFIED**.
- Access tier/go-live: create the app on the Daraja portal (sandbox test shortcodes/passkey); "Go Live" needs a real PayBill/Till with a business administrator (M-Pesa Org portal), OTP verification, and production credentials and passkey issued by email (**UNVERIFIED**).
- Supported payload/channel types: STK Push (M-Pesa Express), C2B (PayBill/Till confirmation/validation), B2C payouts, B2B, transaction status, account balance, reversal (**UNVERIFIED**).
- Kenya relevance: Safaricom M-Pesa is Kenya's dominant mobile-money rail; KES only (**UNVERIFIED** in this check because the official portal is not fetchable).

## AI APIs

### Anthropic Claude API (Messages)

- Docs fetched: https://platform.claude.com/docs/en/api/overview ; https://platform.claude.com/docs/en/api/rate-limits ; https://platform.claude.com/docs/en/build-with-claude/structured-outputs ; https://platform.claude.com/docs/en/manage-claude/api-and-data-retention ; https://platform.claude.com/docs/en/api/supported-regions (docs.claude.com 301-redirects to platform.claude.com)
- API version: header `anthropic-version` (example value on the overview page: `2026-10-21`; also used in the structured-outputs examples).
- Checked: 2026-11-26
- Read/write operations relevant to POVU: `POST https://api.anthropic.com/v1/messages`; `POST /v1/messages/batches` (async, 50% cost reduction); `POST /v1/messages/count_tokens`; `GET /v1/models`; Files API `/v1/files`.
- Auth & headers:
  - `Authorization: Bearer <api key or WIF token>`, or legacy `x-api-key`.
  - `anthropic-version` (required) and `content-type: application/json` (required).
  - `anthropic-workspace-id` is required for keys not scoped to a workspace.
  - Response headers: `request-id`, `anthropic-organization-id`, `anthropic-workspace-id`.
- Rate-limit model:
  - Org-level token bucket with RPM, ITPM, OTPM per model class, plus monthly spend caps by tier: Start $500, Build $1,000, Scale $200,000, Custom uncapped. An Evaluation tier applies to new orgs.
  - Claude Sonnet 5.5 (repo default `claude-sonnet-5-5`): Start 4,000 RPM / 2M ITPM / 400k OTPM; Build 10,000 / 5M / 1M; Scale 13,000 / 10M / 2M.
  - Cached reads don't count toward ITPM. Ramp limits on sharp increases return 429 with `error_code: ramp_limit_exceeded`. The spend-cap 429 (`enforced_spend_limit_reached`) has no `retry-after`.
  - Headers: `retry-after` and `anthropic-ratelimit-{requests,tokens,input-tokens,output-tokens}-{limit,remaining,reset}`.
  - Batches: 100,000 requests per batch; queue 200k/300k/500k by tier.
- Request size: Messages 128 MB; Batches 256 MB; Files 500 MB.
- Data retention: API data is not used for training without permission. Prompts/outputs are not retained by default except for Covered Models (Fable/Mythos 5.x, which need 30-day retention). Legacy ZDR is per-org via sales. ZDR orgs cannot call from the browser (CORS rejected). Batches have 29-day retention and are not ZDR-eligible. Flagged content may be retained up to 2 years.
- Structured output: GA (`status: stable`, no beta header) via `output_config.format = {type: "json_schema", schema}` plus `strict: true` on tools. Supported models include `sonnet-5-5`, `opus-5-5`, `haiku-5-5`. ZDR "Yes (qualified)": only the schema is cached up to 24 h.
- Access tier/go-live: Console account plus API key; tiers advance automatically with usage history.
- Kenya relevance: Kenya is listed on the official supported-regions page.

### OpenAI API (Chat Completions / Responses)

- Docs fetched: https://developers.openai.com/api/docs/guides/your-data ; https://developers.openai.com/api/docs/guides/rate-limits ; https://developers.openai.com/api/docs/guides/structured-outputs (first 100k chars) ; https://developers.openai.com/api/docs/models/gpt-4o ; https://developers.openai.com/api/docs/supported-countries (platform.openai.com 301-redirects to developers.openai.com)
- API version: path `/v1/` (`/v1/chat/completions`, `/v1/responses`). No date-version header is documented on the fetched pages.
- Checked: 2026-11-26
- Read/write operations relevant to POVU: `POST /v1/responses` (the structured-outputs guide's examples all use it) and `POST /v1/chat/completions`. `gpt-4o` supports both.
- Auth & headers: `Authorization: Bearer $OPENAI_API_KEY`, `Content-Type: application/json`. `OpenAI-Organization`/`OpenAI-Project` headers: **UNVERIFIED** (not on the fetched pages).
- Rate-limit model:
  - Limits are per organization/project and per model: RPM, RPD, TPM, TPD, IPM (plus audio minutes). Some model families share limits.
  - Tiers by cumulative credit purchase: Free (allowed geography, $100/mo), Build ($5 → $500/mo), Launch ($100 → $5,000/mo), Grow ($500 → $200,000/mo).
  - Headers: `x-ratelimit-{limit,remaining,reset}-{requests,tokens}` and project-token variants; `Retry-After` on temporary 429/503.
  - Hard spend limits return 429.
- Data retention: API data is not used for training unless opted in (since 2023-03-01). Abuse-monitoring logs are kept up to 30 days. ZDR/Modified Abuse Monitoring need prior approval. ZDR forces `store=false` on `/v1/responses` and `/v1/chat/completions`. The Responses default `store=true` keeps response data at least 30 days.
- Structured output: Responses `text.format = {type: "json_schema", name, schema, strict: true}`; Chat Completions `response_format: {type: "json_schema", ...}` (`gpt-4o-2024-08-06`+, `gpt-4o-mini`). JSON mode guarantees valid JSON only.
- **Caveat for repo default `gpt-4o`:** the official model page marks GPT-4o as **Deprecated** (snapshot `gpt-4o-2024-05-13` is shut down; `-2024-08-06` and `-2024-11-20` are deprecated). No shutdown date is given. The guide recommends a newer model for new projects. Whether the bare `gpt-4o` alias still serves: **UNVERIFIED**.
- Access tier/go-live: tiers advance automatically with credit purchases.
- Kenya relevance: Kenya is listed on the official supported-countries page.

### Google Gemini API (generateContent)

- Docs fetched: https://aistudio.google.com/api-reference/generate-content (first 100k chars) ; https://aistudio.google.com/docs/rate-limits ; https://aistudio.google.com/docs/terms ; https://aistudio.google.com/docs/models ; https://aistudio.google.com/docs/available-regions ; https://aistudio.google.com/docs/api-key (ai.google.dev 301-redirects to aistudio.google.com)
- API version: `v1beta` (`/v1beta/models/{model}:generateContent`). A `v1` stable path is not mentioned on the fetched excerpt (**UNVERIFIED**).
- Checked: 2026-11-26
- Read/write operations relevant to POVU: `POST /v1beta/models/{model}:generateContent`, `POST /v1beta/models/{model}:streamGenerateContent`. Host `generativelanguage.googleapis.com`: **UNVERIFIED** (not shown in the fetched excerpt).
- Auth & headers: API key in header `x-goog-api-key`.
- Rate-limit model:
  - RPM, input TPM, and RPD, applied per project (not per API key). RPD resets at midnight Pacific.
  - Tiers: Free; Tier 1 (linked billing); Tier 2 ($100 spend + 3 days); Tier 3 ($1,000 + 30 days).
  - Spend-based caps on a rolling 10 min: Tier 1 $10, Tiers 2/3 $200. Exceeding returns 429 `RESOURCE_EXHAUSTED`.
  - Per-model numbers are shown in AI Studio.
- Data retention: Unpaid (free) services use prompts/responses to improve Google products, may involve human review, and must not receive sensitive or personal data. Paid services don't use data for improvement; prompts are logged for a limited, unspecified period for abuse detection. EEA/CH/UK end users must be served via Paid Services only. **POVU should use a paid (billing-linked) project for any customer/ERP data.**
- Structured output: `generationConfig.responseMimeType` (`application/json`, `text/x.enum`) with `responseJsonSchema` (preferred field) / `Schema`. The exact relationship between `responseSchema` and `responseJsonSchema` is **UNVERIFIED** (circular description in the excerpt).
- **Caveat for repo default `gemini-flash-latest`:** the official models page confirms the alias exists and is hot-swapped on each release (stable, preview or experimental) with 2-week email notice. Google recommends pinning a specific stable model (e.g. `gemini-3.6-flash`) for production.
- Access tier/go-live: AI Studio API key; billing link for Tier 1+.
- Kenya relevance: Kenya is listed on the official available-regions page.

---
Notes:
- Fetch failures on official sites: Africa's Talking (403), Pesapal (site error / DNS), Safaricom Daraja (JS portal 404), and Flutterwave v3 doc pages (404, partially covered by the current docs plus official-domain search snippets). The Pesapal, Daraja and Africa's Talking sections must be re-verified manually in a browser before implementation.
- The repo's default AI models `gpt-4o` (deprecated) and `gemini-flash-latest` (moving alias) carry upgrade/pinning risk. `claude-sonnet-5-5` is current, with structured outputs GA.

---

## Kenya-relevant options

This section is a summary. The sources and UNVERIFIED markers are in the provider sections above. No account was opened for any of these.

| Need | Kenya-first option | Alternative | Notes |
|---|---|---|---|
| Mobile money collection | **Safaricom M-Pesa Daraja**: STK Push (Lipa na M-Pesa Online), STK query, C2B register URL, B2C, transaction status, reversal | Pesapal or Flutterwave M-Pesa charge | Already wired in the repo (`MPESA_*` settings, `/integrations/mpesa/callback` with a shared-token check). Production go-live needs a Safaricom shortcode and approval, which is an [D] activation. The official portal was unreachable on 2026-11-26, so the endpoint details are UNVERIFIED. |
| Card plus mobile-money hosted checkout | **Pesapal API 3.0**, a Kenya-based PSP: card, M-Pesa and Airtel Money through one hosted page, IPN plus GetTransactionStatus | **Flutterwave v3**: card, M-Pesa (KES) and bank; webhook `verif-hash`; verify-transaction endpoint | M48.S01.T010 uses these (`card_payments_public.py` has the Pesapal route). Pesapal facts are mostly UNVERIFIED because the site was down. |
| Voice and SMS | **Africa's Talking**: Nairobi-based voice and SMS; callback XML actions | Twilio Programmable Voice | `VOICE_PROVIDER` / `VOICE_AT_*` exist. Twilio availability for Kenyan numbers is UNVERIFIED. |
| E-signature | Native typed-name signature with tamper evidence (M36.S04.T003 / M41) | DocuSign eSignature v2.1; Adobe Acrobat Sign v6 | Enforceability under Kenyan e-signature law (KICA) is UNVERIFIED and needs a legal review, which is outside software scope. |
| Ads | Meta: KES is a supported ad account currency (offset 100) | Google Ads: KES is listed, but selecting it on a new account is UNVERIFIED. TikTok: Kenya can be targeted as a location since 2024-08 (UNVERIFIED source). | LinkedIn does not list KES as an ad account currency, so use USD. |
| Social | Facebook, Instagram, TikTok, YouTube and X all operate in Kenya | — | Public visibility of TikTok posts requires TikTok's app audit (a [D] step). |
| AI | Anthropic, OpenAI and Gemini all list Kenya as a supported country | Local `mock` provider | PII masking (`AI_MASK_EXTERNAL_CONTEXT`) stays on by default. |
| Data residency | BigQuery `africa-south1` (Johannesburg); Snowflake on AWS `af-south-1` | Local Postgres, S3 or Parquet export | Region availability is UNVERIFIED. The fit with Kenya's Data Protection Act needs an owner decision. |
| Tax | KRA eTIMS: item codes already modelled (M41.S01.T003) | — | Provider auth is still [!]/[D]. eTIMS was not in scope for this matrix. |
| FX | CBK published rates (`cbk_rates.py`) | Manual rate entry | Already implemented (M39.S03.T013). |

## Local simulator coverage per provider

Simulators live in `backend/tests/provider_sim/`. "Committed" means the file is tracked at `6ac96f1`. "New (untracked)" means a concurrent M48.S01 implementation agent created the file in the working tree on 2026-11-26; it is not yet gated or committed.

Every simulator must:
- shape requests and responses exactly as the official docs above describe;
- record each request (`/_control/calls` or an equivalent) so tests can assert the exact wire contract;
- support one-shot fault injection (`/_control`): auth failure, 429 with retry-after, 5xx, permission error, and validation error;
- stay loopback-only, use synthetic data, and never proxy to a real host. `PROVIDER_EGRESS=local` must be honoured.

| Provider | Simulator file (state) | Already covers | Must still cover (M48/M49 acceptance) |
|---|---|---|---|
| Meta Marketing API | `ads_app.py` (committed; modified in working tree) | Ad accounts, insights, create/read/update of edges and objects, version in path | Ad image and video upload with async video `status`. `effective_status` and review (`ad_review_feedback`) transitions. Batch requests. Pause and resume read-back. Budget-edit throttle. |
| Meta Custom Audiences and CAPI | `ads_lists_app.py` (committed) | `customaudiences`, `users` (refuses non-SHA-256 identifiers), CAPI events | Member removal (`DELETE …/users`), session-based multi-batch upload, minimum-size message, consent-withdrawal removal. |
| Google Ads API | `ads_app.py` (committed) | `searchStream`, `search`, `{svc}:mutate` | `partialFailure` responses, `validateOnly`, asset upload, Demand Gen / Performance Max creation, campaign budget mutate, status read-back. No developer-token header; Cloud-project access level instead. |
| Google audience sync | `ads_lists_app.py` (committed) | `userLists:mutate`, `offlineUserDataJobs` create, add and run, click conversions | **Data Manager API** audience ingestion, because Customer Match is closed to new projects. Job status polling to DONE or FAILED. |
| LinkedIn Marketing API | `ads_app.py` (committed) | `adAccounts`, campaigns, campaign groups, creatives (`/rest` with version header), `adAnalytics` | `X-RestLi-Method` partial update, image and video upload (`initializeUpload`), `rw_dmp_segments` DMP segment users, version-header rejection. |
| TikTok API for Business | `ads_app.py` (committed) | `report/integrated/get`, `{kind}/create`, `status/update`, `update`, `get` (v1.3) | Video and image upload (`file/video/ad/upload`) and its async info. Spark Ads authorization. Smart+ campaign create. Custom audience upload (`dmp/custom_audience/file/upload`). Review status. |
| Facebook Pages / Instagram | `ads_app.py` social routes (committed); `social_app.py` (new, untracked) | `/feed`, `/photos`, IG `/media` + `/media_publish`, messages | IG container `status_code` (IN_PROGRESS, FINISHED, ERROR, EXPIRED), carousel children, reels, stories, `content_publishing_limit`. FB Reels and Stories upload phases. Webhook `X-Hub-Signature-256` (`signing.py:11`). |
| LinkedIn organic | `ads_app.py` `/rest/posts` (committed); `social_app.py` (new) | Create a post | Images and Videos API `initializeUpload` with upload parts and finalize, multi-image (2–20), document posts, video processing status, delete. |
| TikTok Content Posting | `ads_app.py` `video/init` (committed); `social_app.py` (new) | `init` returns `publish_id` | `creator_info/query`, FILE_UPLOAD chunk PUT, PULL_FROM_URL, `status/fetch` progression (PROCESSING_UPLOAD … PUBLISH_COMPLETE / FAILED), private-only behaviour when unaudited, photo posts, inbox upload, webhook signature. |
| YouTube Data v3 | none | — | **New:** resumable `videos.insert` (session URI, chunk PUT, 308 resume), `processingDetails` / `uploadStatus` polling, `videos.list` statistics, the `commentThreads` read, and quota errors (`quotaExceeded`). |
| X API v2 | none | — | **New:** `POST /2/tweets`, media upload v2 (INIT, APPEND, FINALIZE, STATUS for video), `DELETE /2/tweets/:id`, rate-limit headers, and the reply restriction error. |
| Google / Microsoft OAuth, Gmail, Graph mail and calendar, Google Calendar | `app.py` (committed) | OAuth with PKCE, refresh, revoke, userinfo; Gmail messages, history and send; Graph delta and `sendMail`; Calendar and Graph events, delta, create, delete | Gmail `users.watch` + Pub/Sub push. Graph `/subscriptions` create, renew, validation token, `clientState`, lifecycle notifications. Calendar `events.watch` channels with expiry, `channels.stop` and `X-Goog-*` headers. |
| Africa's Talking Voice | `app.py` `/at-voice/call` (committed) | Outbound call | Callback XML actions (Say, Play, GetDigits, Record, Dial), call status callback, sandbox host. |
| Twilio Voice | none | — | **New** (only if Twilio is chosen): Calls API, TwiML fetch, status callback with `X-Twilio-Signature`. |
| Transcription | `app.py` `/transcribe`, `/recordings` (committed) | HTTP transcription stub | Local faster-whisper fixture (no HTTP) for M50. |
| OIDC SSO | `oidc_app.py` (committed) | Discovery, authorize, token, JWKS, token tampering | **SAML IdP simulator** (new): signed AuthnResponse, assertion encryption, wrong audience, expired assertion, replayed InResponseTo, SLO. |
| Snowflake SQL API v2 | `warehouse_app.py` (new, untracked) | Statements submit and poll by handle (per the file header) | Key-pair JWT validation, `202` async + `GET /statements/{handle}`, partitions, `requestId` + `retry=true` idempotency, cancel, `MERGE` result counts. |
| BigQuery REST v2 | `warehouse_app.py` (new) | Google token, jobs (per the file header) | `jobs.insert` load (multipart or resumable), `jobs.get` to DONE with `errorResult`, `insertAll` `insertId` dedupe, `tabledata.list`. |
| Search Console | none | — | **New:** `searchanalytics.query` paging beyond `rowLimit` 25 000 with `startRow`, `sites.list`, the quota error. |
| S3-compatible export | `s3_app.py` (committed) | PUT, GET, HEAD, LIST | — |
| DocuSign / Acrobat Sign | `esign_app.py` (new, untracked) | DocuSign JWT grant, userinfo; Acrobat Sign (per the file header) | Envelope create, `status` polling, Connect HMAC (`X-DocuSign-Signature-1`), void. Acrobat transient documents, agreements, webhook verification (`X-AdobeSign-ClientId` echo), cancel. |
| Pesapal / Flutterwave / M-Pesa | `card_app.py` (new, untracked); M-Pesa is monkeypatched in tests | Pesapal RequestToken, RegisterIPN, GetIpnList, SubmitOrderRequest (per the file header) | Pesapal GetTransactionStatus, IPN, refund. Flutterwave hosted link, `verif-hash` webhook, verify transaction, refund. M-Pesa simulator **app** (STK push, callback, STK query, C2B validation and confirmation, reversal) instead of a monkeypatch. Late and duplicate callbacks for all three. |
| Slack | `slack_app.py` (committed) | Incoming webhook, v0 signing | — |
| AI (Anthropic, OpenAI, Gemini) | none (`AI_PROVIDER=mock` only) | — | **New** HTTP simulator for the three APIs: correct headers (`x-api-key` + `anthropic-version`; Bearer; `x-goog-api-key`), structured output, 429 and 529 overload, token usage, so that the real adapter path is exercised without a paid call. |

Rubric impact: a provider with no simulator (YouTube, X, Search Console, Twilio, the AI HTTP APIs, SAML IdP) cannot score PASS on W-criteria. This follows `QUALITY_RUBRIC.md` §3, where a simulated criterion is eligible only through the real adapter boundary.

## Recommended maintained libraries (M50.S01.T010 and related)

PyPI metadata and GitHub repository metadata were read on 2026-11-26. None of these libraries is installed in `backend/requirements*.txt` today. Each needs the normal licence and security review before it is added.

| Need | Recommendation | Version (2026-11-26) | Licence | Maintenance signal | Notes |
|---|---|---|---|---|---|
| SAML 2.0 SP | **pysaml2** (primary) | 7.5.5 (released 2026-09-17) | Apache-2.0 (GitHub `IdentityPython/pysaml2`) | Last push 2026-11-03; not archived | Needs the `xmlsec1` **binary** in the image (apt `xmlsec1`). It is more flexible (SP and IdP), so the test IdP simulator can reuse it. |
| SAML 2.0 SP | python3-saml (alternative) | 1.16.0 (last PyPI release 2023-10-09) | MIT | Repo push 2026-01-14; no release for over 3 years | Its SP API is simpler. It depends on `xmlsec` 1.3.18 (MIT, libxmlsec1 binding) and `lxml` (BSD). Its release staleness is the reason it is not the primary choice. |
| Parquet | **pyarrow** | 26.0.1 | Apache-2.0 | Apache Arrow project, active | Requires Python ≥ 3.11 (the repo uses 3.12). Large wheel, about 40 MB; accept it, or use the `pyarrow` core without extras. |
| OCR | **pytesseract** + **Tesseract OCR** engine | pytesseract 0.3.13; Tesseract 5.x | Apache-2.0 (both) | Tesseract repo push 2026-11-25 | pytesseract is a thin wrapper and needs the `tesseract-ocr` binary plus the `eng` and `swa` traineddata in the image. `receipt_ocr.py` exists today. |
| Transcription | **faster-whisper** (primary) | 1.2.1 | MIT; its dependency `ctranslate2` 4.9.1 is MIT | Active | Runs on CPU with int8. The Whisper model weights are MIT (`openai-whisper` 20250625, MIT). Models must be downloaded once into a local cache; no runtime call to an external API. |
| Transcription | whisper.cpp (alternative, CLI or server) | — | MIT (`ggml-org/whisper.cpp`) | Push 2026-11-26 | Use it if the Python dependency weight matters. Call it as a subprocess; there is no Python binding requirement. |

General rules for all of these:
- Pin exact versions.
- Run `pip-audit` at the gate.
- Keep the native binaries (xmlsec1, tesseract, ffmpeg) in the Dockerfile with versions recorded.
- Do not use any paid or proprietary SDK.
