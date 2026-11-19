# Phone acceptance test (real device) — M37/M38

What is already verified automatically: every flow below runs in an emulated phone (390 px, simulated GPS) and
against a real ClamAV scanner. What only a real phone can prove: the GPS fix, the camera, the signature on a touch
screen, barcode reading with the camera, and installing the app. Real M-Pesa payments are out of scope (no live account).

## 1. Start the dev stack for the phone (laptop)

Find the laptop's address on the network the phone uses (`ipconfig`). With the iPhone's Personal Hotspot over the
cable the laptop is usually `172.20.10.x`; on office Wi-Fi something like `192.168.1.x`. Then:

```powershell
$env:LAN_IP = "172.20.10.4"
python scripts/dev_lan_tls.py $env:LAN_IP     # test certificate for this address only (once per address)
docker compose -f docker-compose.yml -f docker-compose.lan.yml up -d --force-recreate backend frontend lan-https
```

If the phone cannot open the pages, allow inbound TCP 3443, 8443 and 8088 for Docker Desktop in Windows Defender
Firewall — a change only the laptop owner makes.

## 2. iPhone (Safari) — HTTPS with the test certificate

Safari gives location and camera only to HTTPS pages, so the phone trusts a test certificate that is valid for this
one laptop address only (it cannot be used for any other website):

1. In Safari open `http://<LAN_IP>:8088/rootCA.crt` → *Allow* → "Profile Downloaded".
2. Settings → *Profile Downloaded* → *Install* (passcode) → *Install*.
3. Settings → General → About → *Certificate Trust Settings* → switch on "FMCG ERP local test CA".
4. Open `https://<LAN_IP>:3443` — the app, with the POVU logo.
5. To install the app: Share button → *Add to Home Screen* → *Add*. It opens full screen from the POVU icon.

After testing remove it: Settings → General → VPN & Device Management → the profile → *Remove Profile*.

**Android Chrome** works the same way via `https://<LAN_IP>:3443` after installing `rootCA.crt` (Settings → Security →
Encryption & credentials → Install a certificate → CA certificate), or without a certificate by opening
`http://<LAN_IP>:3000` and enabling `chrome://flags/#unsafely-treat-insecure-origin-as-secure` for that address.

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

### Results — iPhone (Safari, home-screen app), 2026-11-19

| # | Result |
|---|---|
| 1 | pass |
| 2 | pass — server stored the phone's real GPS fix and the photo |
| 3 | pass — FS-261119-5F1E6707 |
| 4 | form works; refused correctly because the invoice already had a pending collection |
| 5 | not shown yet — the stop was already delivered by the emulated run; retest on `SYNTH-TRIP-CC47` |
| 6 | pass — AUD-261119-837BC741, photo stored |
| 7 | camera button was missing on iPhone (no native BarcodeDetector) — fixed with a WebAssembly decoder; retest on `SYNTH-PICK-CC47` (bin `SY-A-01`) |
| 8 | pass |
| 9 | pass — opens full screen from the POVU icon |
| 10–12 | not run yet |

## 5. Back to laptop-only

```powershell
docker compose rm -sf lan-https
docker compose up -d --force-recreate backend frontend
```
