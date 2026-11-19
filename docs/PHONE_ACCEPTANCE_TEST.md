# Phone acceptance test (real device) — M37/M38

What is already verified automatically: every flow below runs in an emulated phone (390 px, simulated GPS) and
against a real ClamAV scanner. What only a real phone can prove: the GPS fix, the camera, the signature on a touch
screen, barcode reading with the camera, and installing the app. Real M-Pesa payments are out of scope (no live account).

## 1. Start the dev stack for the local network (laptop)

```powershell
$env:LAN_IP = "192.168.1.189"   # the laptop's Wi-Fi address (ipconfig)
docker compose -f docker-compose.yml -f docker-compose.lan.yml up -d backend frontend
```

The phone must be on the same Wi-Fi. If the phone cannot open `http://192.168.1.189:3000/login`, allow inbound TCP
3000 and 8000 for Docker Desktop in Windows Defender Firewall (private network) — a change only the laptop owner makes.

## 2. Let the phone use location and camera on this test address

Browsers only allow GPS and camera on secure (HTTPS) pages. For a local test on **Android Chrome**:
open `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, enter `http://192.168.1.189:3000`, set *Enabled*,
tap *Relaunch*. (iPhone Safari has no such switch; it needs an HTTPS address — ask for an HTTPS tunnel if needed.)

## 3. Test accounts (synthetic, local only)

Set a password you know for each account you want to use (asked interactively, never printed):

```powershell
docker cp scripts/dev_set_password.py fmcg-erp-system-backend-1:/tmp/p.py
docker compose exec -e PYTHONPATH=/app backend python /tmp/p.py synth-field
```

| Login | What it is |
|---|---|
| `synth-field` | moto rider with a 3-outlet route, driver of today's trip, outlet auditor, field supervisor, warehouse picker, employee (My HR) |
| `synth-distributor@example.com` | distributor partner portal (`/portal/login`) |
| `synth-supplier@example.com` | supplier portal (`/supplier/login`) |

## 4. Checklist — tick each on the phone

| # | Where | Do | Expected |
|---|---|---|---|
| 1 | `/login` → menu *Field App* | sign in as `synth-field` | route with 3 outlets, owed amount on the first |
| 2 | first outlet → *Check in* | allow location, add an outlet photo with the camera, *Save visit* | message "saved **with location**"; supervisor page shows *With GPS* 100% |
| 3 | *Order* | 24 × a product, *Send order* | order number shown |
| 4 | *Collect* | M-Pesa code (any 10 letters/digits) | collection number shown (finance confirms later) |
| 5 | *My deliveries* | *Start trip*, open the stop, sign with a finger, take a photo, *Confirm delivery* | "Delivered to …" |
| 6 | *Outlet audits* | find "Umoja", mark one item *Not OK* + photo, *Save audit* | score shown |
| 7 | menu *Warehouse Floor* | *Camera* button on the bin field, scan a printed barcode | code appears in the field |
| 8 | menu *My HR* → *Attendance* | *Check in now* | "Checked in." |
| 9 | browser menu → *Install app* / *Add to Home screen* | open from the home screen | app opens full screen on the dashboard |
| 10 | `/portal/login` | distributor: order, *Support* → open a ticket | order number, ticket number |
| 11 | `/supplier/login` | supplier: accept the PO, upload a PDF | "uploaded for review" |
| 12 | `/verify/SYNTH-QR-0001` | open (no login) | "Genuine product", batch and dates |

Report any step that fails with the step number and a screenshot.

## 5. Back to laptop-only

```powershell
docker compose up -d backend frontend
```
