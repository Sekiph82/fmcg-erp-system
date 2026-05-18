# Production

**URL:** `/dashboard/production`  
**Module:** Production  
**Permission:** `production.view`

---

## Screenshot

> Screenshot pending: Production workspace overview

---

## Purpose

The Production workspace manages the entire manufacturing lifecycle: planning, order execution, material consumption, quality control, batch tracking, OEE, and costing.

---

## Tabs

| Tab | URL | Purpose |
|---|---|---|
| Plans | ?tab=plans | Daily/weekly production plans |
| Orders | ?tab=orders | Production order management |
| Scheduling | ?tab=scheduling | Finite scheduling board |
| Work Centers | ?tab=work-centers | Machine/line configuration |
| Routing | ?tab=routing | Operation sequences |
| Batch & Lots | ?tab=batch-lots | Batch number assignment |
| Quality Control | ?tab=quality-control | In-process QC |
| Labor | ?tab=labor | Labor allocation |
| Time Tracking | ?tab=time-tracking | Job timing |
| OEE | ?tab=oee | Overall Equipment Effectiveness |
| Downtime | ?tab=downtime | Downtime log |
| Waste & Yield | ?tab=waste-yield | Waste and yield recording |
| WIP | ?tab=wip | Work in progress |
| Costing | ?tab=costing | Standard vs actual cost |
| Variance | ?tab=variance | Cost variance analysis |
| Reports | ?tab=reports | Production reports |
| Execution | ?tab=execution | Production output confirmation |
| Machine Ops | ?tab=machine-ops | Machine operator view |
| Material Flow | ?tab=material-flow | Material issue and backflush |
| Projects | ?tab=projects | Production projects |

---

## Key Workflows

See `../kenya-go-live/02_PRODUCTION_USER_MANUAL.md` for step-by-step workflows.

---

## Related Workspaces

- Shop Floor (`/dashboard/shop-floor`) — operator terminal
- BOM & Formula (`/dashboard/bom`) — recipes
- Recipes (`/dashboard/recipes`) — formula definitions
- Planning (`/dashboard/planning`) — MRP and capacity
- Maintenance (`/dashboard/maintenance`) — machine maintenance
- Quality (`/dashboard/quality`) — QC inspections

---

## Production Order Status Flow

```
Draft → Released → In Progress → Completed → Closed
         ↓
       Cancelled
```

---

## OEE Formula

OEE = Availability × Performance × Quality

- Availability: planned time vs actual run time
- Performance: actual output rate vs ideal rate
- Quality: good units vs total units produced

Target: OEE > 85% for most FMCG lines.
