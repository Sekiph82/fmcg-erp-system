# M44 gate — step 5: real local app walkthrough (2026-11-26)

## Setup

- **Backend:** uvicorn on :8040, using the disposable DB `m44_walk` (head 0074 plus the synthetic seed). The owner's dev DB was not used.
- **Frontend:** `next dev` on :3240.
- **Environment:** `PROVIDER_EGRESS=local`, and no provider keys are set.
- **Seeded rows:**
  - one Facebook page channel;
  - one Messenger DM;
  - one custom channel with one inbound message.

## Personas (non-superusers)

- `synth-marketer`: crm.*_all and marketing.view / edit / create.
- `synth-rep`: crm.view / edit / create only.

## Results

### Marketer on desktop

- **Inbox:** shows the Custom channel thread and the Messenger thread with reply due times (`01`).
- **Messenger thread:** the reply is refused with a visible "NOT_CONFIGURED: Meta page token is not set (activation step in M47)". This is the honest no-account state (`02`).
- **Custom channel thread:** the reply is stored as "waiting for the channel to fetch it" (QUEUED) (`03`).
- **Messaging channels tab:**
  - Meta and Slack both show "Not configured".
  - Creating the channel `duka-app` works, and its token is shown once.
- **Other tabs:** Social (calendar, listening, channels), Ads (four platforms "Not configured", live publishing disabled), Audiences, Website analytics, E-mail designer and Campaigns (A/B fieldset) all load.
  - Every API call was 2xx, except the expected 503 (Messenger not configured) and the designer preview below.

### Phone width (375×812)

- No horizontal overflow (scrollWidth 375) on the Inbox, the thread page, Messaging channels, Social, Ads, Audiences and the E-mail designer (`04`, `05`).

### Rep on desktop

- Ads, Social, Audiences, Website analytics and the E-mail designer tabs are hidden.
- The Messaging channels tab shows the service status, but custom channels say "Only CRM administrators manage custom channels." The API returns 403.

## Defects found and fixed in the gate

1. **Messaging UI called `/crm-channels/...` without `/api/v1`, so every call returned 404.**
   - Reported by the reviewer and confirmed in the browser.
   - Fixed. The thread, the reply and channel creation were verified above after the fix.
2. **The E-mail designer live preview showed only "Check the design."**
   - The preview request uses `responseType: "text"`, so the error body arrived as a string and the real validation message was lost.
   - Fixed. The default button link `https://` is now reported as "Link must be a full http(s) address" (`06`).
