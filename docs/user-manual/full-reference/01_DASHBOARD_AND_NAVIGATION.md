# Dashboard and Navigation

**URL:** `/dashboard`  
**Module:** Core  
**Permission:** Any authenticated user

---

## Screenshot

![Main Dashboard](../screenshots/captured/002_dashboard.png)

---

## Purpose

The dashboard is the home page after login. It shows business KPIs, pending tasks, and quick navigation to all modules.

---

## Sidebar Navigation

The left sidebar shows all accessible modules, grouped by cluster:

| Cluster | Workspaces |
|---|---|
| Supply Chain | Products, Materials, Suppliers, Inventory, Warehouses, Procurement |
| Manufacturing | Production, Planning, NPD, BOM, Recipes, Quality, Compliance, Shop Floor |
| Commercial | Sales, CRM, Marketing, POS |
| Finance | Finance |
| Factory Operations | Maintenance, Utilities |
| Logistics | Logistics |
| HR & Payroll | HR, Kenya Payroll |
| Documents & Communication | Documents, Communication, Helpdesk |
| Intelligence | AI, Analytics |
| Administration | Admin, Integrations |

Workspaces you do not have permission for are hidden or greyed out.

---

## Global Search

Press `Ctrl+K` (or click the search icon) to open global search. Search for:
- Module names (e.g., "production")
- Page tab names (e.g., "cycle count")
- Records (if backend search is enabled)

Search hints from workspace `searchHints` are shown in the dropdown.

---

## Theme

Toggle dark/light mode via the user menu (top right).

---

## User Menu

Top-right corner:
- Profile: view/edit your profile
- Security: change password, set up 2FA
- Notifications: unread notification count
- Logout

---

## Navigation Pattern

All modules use the workspace pattern:
1. Click a workspace in the sidebar (e.g., Production)
2. Workspace opens with a default tab active
3. Click tab buttons at the top to switch between functions
4. Tab state persists in the URL: `/dashboard/production?tab=orders`

Bookmarking a tab URL opens the correct tab directly.
