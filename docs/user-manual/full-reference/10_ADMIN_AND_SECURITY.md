# Admin and Security

**URL:** `/dashboard/admin`
**Module:** Admin
**Permission:** `users.view` (admin role)

---

## Screenshot

![Admin Workspace](../screenshots/captured/004_admin-users.png)

---

## Admin Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Users | ?tab=users | User account management |
| Roles | ?tab=roles | Role definitions |
| Permissions | ?tab=permissions | Permission matrix |
| Companies | ?tab=companies | Multi-company setup |
| Security | ?tab=security | 2FA, password policy, sessions |
| Approvals | ?tab=approvals | Approval workflow rules |
| Custom Fields | ?tab=custom-fields | Add fields to any record type |
| System Config | ?tab=system-config | Company settings, integrations |
| Mobile | ?tab=mobile | Mobile app configuration |
| Logs | ?tab=logs | Audit trail |
| Import History | ?tab=import-history | Bulk data import records |

---

## Integrations Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Overview | — | Integration status |
| M-Pesa | ?tab=mpesa | M-Pesa API credentials |
| Sync | ?tab=sync | Data sync jobs |
| Marketplace | ?tab=marketplace | Third-party app marketplace |
| Barcode | ?tab=barcode | Barcode scanner config |
| Marketing Sync | ?tab=marketing-sync | Marketing tool sync |
| Logs | ?tab=logs | Integration event logs |
| Webhooks | ?tab=webhooks | Outbound webhook endpoints |
| Developer | ?tab=developer | API keys, developer portal |

---

## Logs Workspace

**URL:** `/dashboard/logs`

| Tab | Purpose |
|---|---|
| Operational | General system event log |
| M-Pesa | M-Pesa API call log |
| Security | Login attempts, permission changes |

---

## Approvals Workspace

**URL:** `/dashboard/approvals`

| Tab | Purpose |
|---|---|
| All | All pending and completed approvals |
| Rules | Approval rule configuration |

---

## 2FA Configuration

Admin → Security tab:
- Enable 2FA requirement per role
- Supported methods: TOTP (authenticator app), Email OTP, SMS OTP
- OTP expiry: 5 minutes (configurable)
- OTP resend: 60 second cooldown

Production guard: `OTP_DEV_DELIVERY_MODE=true` is blocked in production — ensures real OTP delivery via SMTP/Twilio.

---

## Custom Fields

Add organisation-specific fields to any record type without code changes:
- Field types: text, number, date, dropdown, checkbox
- Assign to: products, customers, suppliers, employees, etc.
- Visible in: record forms and list columns

---

## Role-Based Access Control

Permission strings follow the pattern: `{module}.{action}`
Examples: `production.view`, `production.create`, `finance.approve`

Each role has a set of permissions. Users can have multiple roles.

---

## Management User Seeding (No Hardcoded Admin Secrets)

Management users (superusers, initial admin accounts) are seeded via environment variables — not hardcoded credentials.

### How It Works

The seed script reads management user configuration from env vars at startup:

| Variable | Description |
|---|---|
| `MANAGEMENT_USER_EMAIL` | Email address for the management superuser |
| `MANAGEMENT_USER_USERNAME` | Username |
| `MANAGEMENT_USER_PASSWORD` | Initial password (hashed at seed time) |
| `MANAGEMENT_USER_FULL_NAME` | Display name |
| `SEED_DEMO_DATA` | `true` to run the full demo seed (products, inventory, production, etc.) |

**Security rules:**
- Never commit actual management credentials to git
- `.env.production` and `.env.development` are gitignored by design
- Only example files (`.env.*.example`) are tracked — these contain no real credentials
- If `MANAGEMENT_USER_PASSWORD` is not set, the seed exits without creating a management user

### Force Password Change

Management users created via seed are flagged for forced password change on first login. The user is redirected to the password change page before accessing any other module.

This ensures the seeded initial password is replaced with a user-chosen password before normal operations begin.

---

## PyJWT Authentication

The ERP uses PyJWT for JSON Web Token generation and validation. Key security behaviors:

| Behavior | Detail |
|---|---|
| Token signing | HS256 algorithm with `SECRET_KEY` from env |
| Token expiry | Configured via `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Expiry check | Token is rejected if `exp` claim is in the past |
| Refresh token | Separate `REFRESH_TOKEN_EXPIRE_DAYS` config |
| Invalid token | Returns HTTP 401 with `WWW-Authenticate: Bearer` header |
| `python-jose` | Not used — replaced by PyJWT. Do not add `python-jose` back. |

**Security note:** The `SECRET_KEY` must be a long random string (minimum 32 characters). Set it in `.env.production` — never hardcode it or commit it to git. Generate with: `openssl rand -hex 32`

---

## GS1 Label Generator — Auth-Gated

The GS1 label generator at `/dashboard/compliance/gs1` requires authentication. All 38 GS1 API endpoints are protected by `require_auth` middleware.

**Before go-live:**
- Unauthenticated access to GS1 endpoints returns HTTP 401
- The frontend GS1 page requires a valid session (login-gated)
- GS1 label printing, template management, and barcode generation all require `users.view` minimum permission

**Why this matters:** GS1 barcodes are used on product packaging. Unauthorized label generation would create fraudulent barcodes. The auth gate prevents unauthenticated access to the label workflow.

---

## Alembic Migration Safety — PostgreSQL Advisory Lock

Database migrations use a PostgreSQL advisory lock (`pg_advisory_lock(20260517)`) to prevent race conditions in multi-replica deployments.

### How It Works

When the backend starts, Alembic runs `upgrade head`. Before running any migration:
1. Attempts to acquire `pg_advisory_lock(20260517)` — a session-level exclusive lock
2. If the lock is held by another replica, waits until released
3. Runs migration once the lock is acquired
4. Releases the lock when migration completes (or on connection close)

**Result:** Only one replica runs migrations at a time. Other replicas wait. After the first replica completes, subsequent replicas see the DB is already at `head` and skip.

**Deployment implication:** Rolling deploys are safe — no split-brain migration state. Do not interrupt the startup container before migrations complete; the lock is held until the migration transaction commits.

---

## Blocked Live Integrations

The following integrations are implemented with a simulation/sandbox mode. **Do not enable live mode without the specified prerequisites:**

| Integration | Current state | Prerequisites to enable live |
|---|---|---|
| eTIMS (KRA fiscalization) | SimulationETIMSConnector — no KRA calls | Provider selection + KRA sandbox credentials + accountant GL gate approval |
| M-Pesa (Daraja) | Simulation — no real STK Push | Safaricom Daraja credentials (Consumer Key, Secret, Shortcode, Passkey, Callback URL) |
| WhatsApp | Demo mode — no Meta Cloud API calls | Meta Cloud API token + Phone Number ID configured in DB |
| AI (LLM features) | Mock mode — canned responses | Anthropic/OpenAI/Gemini API key in env |
| SMTP (email/OTP) | Dev delivery mode may be active | Confirm `OTP_DEV_DELIVERY_MODE=false` in production |

**Do not enable any live integration without real credentials from the respective provider.** Do not commit credentials to git.

---

## Security Best Practices

- Use strong passwords (12+ chars, mixed case, digits, special chars)
- Enable 2FA for all admin accounts
- Review audit logs weekly
- Deactivate accounts immediately when staff leave
- Never share login credentials
- Rotate `SECRET_KEY` if compromised — all existing tokens become invalid immediately
- Set `OTP_DEV_DELIVERY_MODE=false` in production
- Verify `production_execution_allowed` for all integrations before go-live
