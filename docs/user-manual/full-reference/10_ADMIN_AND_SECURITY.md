# Admin and Security

**URL:** `/dashboard/admin`  
**Module:** Admin  
**Permission:** `users.view` (admin role)

---

## Screenshot

> Screenshot pending: Admin workspace — Users tab

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

## Security Best Practices

- Use strong passwords (12+ chars, mixed case, digits, special chars)
- Enable 2FA for all admin accounts
- Review audit logs weekly
- Deactivate accounts immediately when staff leave
- Never share login credentials
