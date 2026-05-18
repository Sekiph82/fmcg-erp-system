# Standalone Operational Pages

**Date:** 2026-05-18

This chapter covers workspaces that serve specific operational functions and do not fit neatly into the main module clusters.

---

## NPD (New Product Development)

**URL:** `/dashboard/npd`  
**Tab:** npd  
**Permission:** `npd.view`

![NPD Workspace](../screenshots/captured/118_npd.png)

Manages new product development projects from concept to launch:
- Project pipeline with stage gates
- Formula development linked to BOM
- Regulatory approval tracking
- Launch readiness checklist

---

## Maintenance

**URL:** `/dashboard/maintenance`  
**Permission:** `maintenance.view`

![Maintenance — Assets Tab](../screenshots/captured/120_maintenance-assets.png)

| Tab | Purpose |
|---|---|
| Overview | Maintenance KPI summary |
| Assets | Equipment register |
| Breakdowns | Corrective maintenance jobs |
| Plans | Preventive maintenance schedules |
| Predictive | Predictive maintenance (sensor data) |
| Spares | Spare parts inventory |
| Reports | Maintenance reports |

Linked to Production OEE — downtime in Production links to Maintenance breakdown records.

---

## Utility Management

**URL:** `/dashboard/utility-management`  
**Permission:** `utility_management.view`

![Utility Management](../screenshots/captured/122_utility-management.png)

| Tab | Purpose |
|---|---|
| Assets | Utility assets (meters, generators) |
| Electricity | kWh readings, cost, alerts |
| Water | Water consumption per process |
| Solar | Solar generation vs consumption |
| Steam | Steam boiler readings |
| Wastewater | Effluent discharge monitoring |
| Soft Water | Softener readings |
| Compressor | Air compressor records |
| Chemical Treatment | Water treatment records |
| Machine Utility | Per-machine utility allocation |
| Readings | Manual meter entry |
| Devices | IoT device configuration |
| KPI Center | Utility KPI dashboard |
| Alarm Center | Active alarms |
| Alarm Rules | Alarm threshold setup |
| Billing | Utility billing |
| Transactions | Utility cost transactions |
| Reports | Utility reports |
| Integration | External system sync |
| IoT | IoT stream config |
| ESG | Environmental metrics for ESG report |

---

## Helpdesk

**URL:** `/dashboard/helpdesk`  
**Permission:** `quality.view`

![Helpdesk Workspace](../screenshots/captured/140_helpdesk.png)

| Tab | Purpose |
|---|---|
| All | All tickets |
| Open | Open/unresolved tickets |
| Escalated | Escalated tickets |
| SLA | SLA compliance |
| Tickets | Ticket list |

Used for internal IT support and customer service tickets. Links to Consumer Complaints (Quality workspace).

---

## Documents

**URL:** `/dashboard/documents`  
**Permission:** `documents.view`

![Documents Workspace](../screenshots/captured/115_documents.png)

| Tab | Purpose |
|---|---|
| Documents | General document library |
| Compliance | Compliance documents |
| Expiring | Documents expiring soon |
| Knowledge Base | SOPs, guides, FAQs |
| E-Sign | Electronic signature queue |

---

## Communication

**URL:** `/dashboard/communication`

![Communication Workspace](../screenshots/captured/139_communication.png)

| Tab | Purpose |
|---|---|
| Messages | Internal direct messages |
| Chatter | Record-linked comments |
| Email | Email integration |
| WhatsApp | WhatsApp business messaging |
| Calls | VoIP call log |
| Meetings | Meeting scheduler |
| Calendar | Shared calendar |
| Notifications | Notification settings |

---

## Shop Floor

**URL:** `/dashboard/shop-floor`  
**Permission:** `production.view`

![Shop Floor — Terminal](../screenshots/captured/051_shop-floor-terminal.png)

| Tab | Purpose |
|---|---|
| Overview | Line summary |
| Terminal | Operator job card confirm/reject |
| Supervisor | Supervisor floor view |
| Queue | Work queue board |
| Downtime | Live downtime logging |
| Handover | Shift handover notes |

Designed for touchscreen use on the factory floor. Large buttons, minimal text.
