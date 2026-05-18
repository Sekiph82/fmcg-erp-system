# Admin User Manual

**Audience:** IT Administrator, System Administrator  
**URL:** `/dashboard/admin`  
**Permission required:** `users.view` (admin role)

---

## Your Role

As admin, you set up and maintain the ERP. You create user accounts, assign roles, configure the system, and troubleshoot issues. You are the first line of support for all other staff.

---

## Pages You Use

| Page | URL | What you do there |
|---|---|---|
| Dashboard | /dashboard | Overview |
| Admin workspace | /dashboard/admin | Manage all system settings |
| Approvals | /dashboard/approvals | Review pending approval requests |
| Documents | /dashboard/documents | Manage shared documents |
| Logs | /dashboard/logs | Audit trail |
| AI | /dashboard/ai | AI configuration |
| Integrations | /dashboard/integrations | M-Pesa, API keys |

---

## Screenshot

![Admin Workspace — Users Tab](../screenshots/captured/004_admin-users.png)

---

## Step 1: Initial System Setup

### 1.1 Configure Company Details

1. Go to `/dashboard/admin`
2. Click the **System Config** tab
3. Set:
   - Company Name: your company name
   - Timezone: `Africa/Nairobi`
   - Default Currency: `KES`
   - Country: `Kenya`
4. Upload logo (PNG, max 2MB)
5. Click **Save**

![Admin — System Config Tab](../screenshots/captured/008_admin-system-config.png)

### 1.2 Configure Email (SMTP)

For order confirmations, OTP delivery, and notifications:
1. Admin → System Config → Email Settings
2. Enter SMTP host, port, username, password
3. Click **Send Test Email** to verify
4. Save

### 1.3 Configure M-Pesa Integration

1. Go to `/dashboard/integrations?tab=mpesa`
2. Enter M-Pesa Consumer Key, Consumer Secret, Shortcode, Passkey
3. Set environment to `production` (not sandbox)
4. Click **Test Connection**
5. Save

![Integrations — M-Pesa Tab](../screenshots/captured/134_integrations-mpesa.png)

---

## Step 2: Create User Accounts

### 2.1 Create a New User

1. Go to `/dashboard/admin?tab=users`
2. Click **+ Invite User** (or **+ Create User**)
3. Fill in:
   - Full Name
   - Email address (used for login and notifications)
   - Username (short, no spaces)
   - Temporary password (user must change on first login)
4. Assign Role (see section below)
5. Click **Create**

![Admin — Users Tab](../screenshots/captured/004_admin-users.png)

### 2.2 Assign Roles

Roles control what each user can see and do.

| Role | For |
|---|---|
| Admin | IT staff only — full access |
| Production | Factory floor supervisors and operators |
| Warehouse | Storekeepers, receiving staff |
| Procurement | Purchasing officers |
| Quality | QC technicians, lab staff |
| Sales | Sales reps, invoicing clerks |
| HR | HR officers, payroll clerks |
| Finance | Finance team, accountants |
| Manager | Read-only dashboard access + approvals |

To assign: Admin → Roles tab → select role → add user to role members.

![Admin — Roles Tab](../screenshots/captured/005_admin-roles.png)

### 2.3 Deactivate a User

1. Admin → Users tab → find user
2. Click the user → click **Deactivate**
3. User can no longer log in; their data is preserved

---

## Step 3: Security Configuration

### 3.1 Password Policy

1. Admin → Security tab
2. Recommended settings:
   - Minimum length: 12
   - Require uppercase: Yes
   - Require digit: Yes
   - Require special character: Yes
3. Save

![Admin — Security Tab](../screenshots/captured/007_admin-security.png)

### 3.2 Two-Factor Authentication (2FA)

2FA adds a second login step using an OTP code.

To enable for all admin accounts:
1. Admin → Security → 2FA Settings
2. Set **Require 2FA for Admin role**: Yes
3. Users will be prompted to set up 2FA on next login

Supported methods: Email OTP, SMS OTP, or Authenticator app (TOTP).

### 3.3 Session Management

Admin → Security → Session Settings:
- Session timeout: 8 hours (recommended)
- Max concurrent sessions: 1 per user (recommended for security)

---

## Step 4: Manage Roles and Permissions

1. Go to `/dashboard/admin?tab=roles`
2. Each role has a set of permissions
3. Click a role → **Edit Permissions**
4. Check/uncheck permission boxes
5. Save

**Do not remove permissions from a role while users are logged in — they will see permission errors until they re-login.**

![Admin — Permissions Tab](../screenshots/captured/006_admin-permissions.png)

---

## Step 5: Approval Workflows

1. Go to `/dashboard/admin?tab=approvals`
2. Create approval rules for:
   - Purchase orders above KES [threshold]
   - Sales discounts above [%]
   - Expense claims above KES [threshold]
3. Assign approvers by role
4. Save

Users will receive notifications when their records require approval.

---

## Step 6: Monitor System Health

### Audit Logs

Every user action (login, create, edit, delete, approve) is recorded.

1. Go to `/dashboard/admin?tab=logs` or `/dashboard/logs`
2. Filter by user, action type, date
3. Export to CSV for compliance audits

![Admin — Audit Logs Tab](../screenshots/captured/011_admin-logs.png)

### System Config Tab

Shows:
- Database connection status
- Current Alembic migration revision
- Active user count
- Background job status

---

## Common Admin Tasks

| Task | How |
|---|---|
| Reset a user's password | Admin → Users → user → Reset Password |
| Unlock a locked account | Admin → Users → user → Unlock Account |
| Add a new module permission | Admin → Roles → role → Edit Permissions |
| View who approved a PO | Procurement → PO → History tab |
| Check email delivery failure | Admin → System Config → Email Logs |

---

## Troubleshooting

**Problem:** User cannot log in — "Account inactive"  
**Solution:** Admin → Users → find user → Activate Account

**Problem:** User sees "Permission denied"  
**Solution:** Check the user's role → ensure correct permissions are assigned

**Problem:** Emails not being sent  
**Solution:** Admin → System Config → Email Settings → Send Test Email → check SMTP logs

**Problem:** M-Pesa payments not reconciling  
**Solution:** Integrations → M-Pesa → check API logs; verify credentials are for production not sandbox

---

## Training Checklist

- [ ] Can log in to admin account
- [ ] Has configured company name, timezone, currency
- [ ] Has created at least 3 staff accounts
- [ ] Has assigned correct roles to all staff
- [ ] Has enabled 2FA for admin accounts
- [ ] Has configured SMTP and sent a test email
- [ ] Has configured M-Pesa integration
- [ ] Can view audit logs and filter by user
- [ ] Has set up approval workflows for POs and expenses
- [ ] Knows how to reset a user's password
