# M37 — Çalışan Mobil Uygulaması: Dağıtım Kararı (2026-11-19)

**Karar:** Herkese açık Google Play / App Store yayını **yapılmayacak**. Faz 1 olarak mevcut Next.js
ERP'si **kurulabilir PWA** (Progressive Web App) olarak çalışanlara açılır. Native kabuk (Capacitor)
ancak aşağıdaki "Faz 2 tetikleyicileri"nden biri gerçekleşirse yapılır ve o zaman da **yalnızca özel
kanallardan** dağıtılır: Android → managed Google Play private app, iOS → Apple Business Manager Custom App.

Durum: Faz 1 uygulandı ve yerelde doğrulandı. Gerçek cihaz / mağaza hesabı gerektiren adımlar `[!]`.

## 1. Mevcut durum (kaynak incelemesi, `main` @ 950a4d4)

| Alan | Bulgu |
|---|---|
| Oturum | HttpOnly `erp_access_token` + refresh cookie, `withCredentials`; `/api/v1/auth/refresh` ile otomatik yenileme (`frontend/src/lib/api.ts`). Admin/finans rolleri için zorunlu TOTP 2FA. |
| Kimler girebilir | Açık kayıt (self-signup) endpoint'i yok; kullanıcılar yalnızca admin tarafından oluşturulur. API'de varsayılan-yetkili, `PUBLIC_ROUTES` beyaz listesi (`backend/app/core/module_registry.py`). Mobil uygulama ek bir giriş yolu açmaz. |
| Mobil modül | `mobile_push_tokens`, `mobile_app_sessions` tabloları; `POST/GET/DELETE /api/v1/mobile/devices`, `/mobile/approvals`, `/mobile/kpis`, `/devices/stats`; `/push/send` **stub** (FCM/APNs bağlı değil). UI: Admin → Mobile Apps sekmesi, `/dashboard/mobile/{approvals,devices}`. |
| Saha ekranları | Shop-floor terminal zaten dokunmatik için ayarlı (`min-h-11`, `text-base`, `inputMode=decimal`) ve **bilinçli olarak çevrimdışı kayıt yapmaz** (`ShopFloorConnectionNotice`). Van-sales POS'ta "UUID or scan barcode" serbest metin alanı (klavye-wedge tarayıcı uyumlu). |
| PWA | Yoktu: manifest, service worker, ikon, viewport/theme meta yoktu. |

## 2. Mobilde gerçekten gerekenler

| İhtiyaç | Faz 1 (PWA) karşılığı | Not |
|---|---|---|
| Barkod/QR tarama | Donanım tarayıcı (Zebra/Honeywell klavye-wedge) her alanda çalışır. Kamera ile tarama: yerel `BarcodeDetector` API (Android Chrome/Edge) — `BarcodeScanButton`, shop-floor lot seçiminde. | iOS Safari `BarcodeDetector` desteklemez → buton gizlenir. iOS kamera taraması gerekiyorsa JS çözücü (zxing) eklenir (Faz 1.1). |
| Kamera | `getUserMedia` (HTTPS zorunlu). | Prod'da HTTPS şart. |
| Offline | Yalnızca uygulama kabuğu + statik "bağlantı yok" sayfası. **ERP yazma işlemleri çevrimdışı kuyruğa alınmaz.** | Stok/üretim bütünlüğü: offline kuyruk idempotency anahtarı + çakışma çözümü olmadan güvenli değil. Mevcut shop-floor politikasıyla tutarlı. |
| Push bildirim | Henüz yok (backend stub). Android PWA ve iOS 16.4+ ana ekrana eklenmiş PWA Web Push destekler. | M37.S03: VAPID Web Push ya da Faz 2'de FCM/APNs. |
| Cihaz güvenliği | Kurulu uygulama (standalone) açıldığında cihaz `/mobile/devices`'a kaydolur (platform tespiti, kalıcı cihaz kimliği) → Admin cihaz envanterini görür, cihazı devre dışı bırakabilir. Service worker hiçbir API yanıtını, kimlik doğrulamalı HTML'i veya GET dışı isteği önbelleğe almaz → paylaşılan cihazda çıkıştan sonra veri kalmaz. | Cihaz-onaylı giriş (yalnız kayıtlı cihaz) ve uzaktan silme MDM işidir (Faz 2). |

## 3. Seçenek karşılaştırması

Ücretler yaklaşık ve satın alma anında resmi sayfadan teyit edilmelidir.

| Seçenek | Maliyet | Hesap gereksinimi | Güvenlik / erişim kontrolü | Güncelleme yolu | Değerlendirme |
|---|---|---|---|---|---|
| **A. Herkese açık App Store / Google Play** | Apple Developer Program ~99 USD/yıl; Google Play Console 25 USD tek sefer | D-U-N-S, tüzel kişilik, App Review, gizlilik beyanları, mağaza listeleme | Uygulama herkes tarafından indirilebilir (giriş yine ERP hesabına bağlı); Apple 4.2 "web sarmalayıcı" reddi riski | Mağaza incelemesi her sürümde | **Reddedildi**: yalnız iç kullanıcılar için gereksiz ifşa, inceleme yükü ve red riski. |
| **B. PWA (Faz 1 — seçildi)** | 0 (mevcut HTTPS sunucu) | Yok | ERP oturumu + 2FA; API varsayılan-yetkili; SW veri önbelleklemez; erişim fabrika ağı/VPN ile sınırlandırılabilir | Sunucuya deploy = anında tüm cihazlarda | **Seçildi**: hemen, ücretsiz, tek kod tabanı. |
| **C. Android: managed Google Play private app (Capacitor)** | Play Console 25 USD + EMM/MDM cihaz lisansı | Google Play Console kuruluş hesabı (D-U-N-S), Android Enterprise kaydı, EMM | Uygulama yalnız kuruluşun yönetilen cihazlarında görünür; MDM ile uzaktan silme, cihaz politikası | Play üzerinden otomatik | Faz 2 Android yolu. Not: managed Google Play, PWA'yı da "web app" olarak yönetilen cihazlara itebilir → native kabuk olmadan da MDM dağıtımı mümkün. |
| **D. Android: APK sideload** | 0 | Yok | Zayıf: "bilinmeyen kaynak" açılır, imza/güncelleme denetimi elle | Elle, her cihazda | Yalnız acil pilot için; kalıcı yol değil. |
| **E. iOS: Apple Business Manager Custom App (Capacitor)** | Apple Developer Program ~99 USD/yıl (+ MDM lisansı önerilir) | Apple Developer Program kuruluş üyeliği (D-U-N-S), ABM kaydı (D-U-N-S, doğrulama), App Review (custom app için de) | Yalnız ABM'de tanımlı kuruluşa görünür; MDM ile yönetilen kurulum veya kullanım kodu | App Store altyapısı ile | Faz 2 iOS yolu. |
| **F. iOS: Apple Developer Enterprise Program** | ~299 USD/yıl | Sıkı uygunluk (büyük kuruluş, Apple onayı) | Kendi imzalı dağıtım; Apple yeni başvuruları büyük ölçüde Custom App'e yönlendiriyor | Kendi altyapınız | **Reddedildi**: uygunluk ve iptal riski. |
| **G. iOS: MDM Web Clip** | MDM lisansı | MDM | PWA'yı yönetilen iPhone/iPad ana ekranına yerleştirir | PWA ile aynı | Faz 1'in iOS dağıtım tamamlayıcısı (MDM varsa). |

## 4. Gerekçe

1. Kullanıcılar yalnızca fabrika çalışanları; uygulama zaten ERP hesabı + 2FA arkasında. Herkese açık mağaza
   listesi hiçbir yetki kazandırmaz, yalnızca inceleme yükü ve ifşa ekler.
2. Tüm iş mantığı ve ekranlar web'de mevcut; PWA aynı kodu kullanır, ek bakım yükü yok, güncelleme anında.
3. İhtiyaç listesindeki kritik kalemler (donanım tarayıcı, kamera, tam ekran kurulum, cihaz envanteri) PWA ile
   karşılanıyor. Offline yazma bilinçli olarak kapsam dışı (veri bütünlüğü).
4. Native kabuk; D-U-N-S, iki geliştirici hesabı, ABM/Android Enterprise ve tercihen MDM gerektirir — bunlar
   şirket kararı ve masraf; ihtiyaç kanıtlanmadan açılmamalı.

## 5. Faz 2 tetikleyicileri (Capacitor + özel dağıtım)

- iOS'ta güvenilir push veya arka plan görevleri gerekiyorsa,
- Native tarayıcı SDK'sı (Zebra DataWedge intent vb.) ya da Bluetooth yazıcı/terazi erişimi gerekiyorsa,
- Cihaz-onaylı giriş / uzaktan silme zorunlu güvenlik politikası olursa (MDM ile birlikte),
- iOS'ta kamera ile barkod taraması yaygın ihtiyaçsa ve JS çözücü yetersiz kalırsa.

Faz 2 için şirketin hazırlaması gerekenler: D-U-N-S numarası; Apple Developer Program (kuruluş) + Apple
Business Manager; Google Play Console (kuruluş) + Android Enterprise; MDM/EMM seçimi (ör. Intune, Jamf,
Workspace ONE, Google endpoint management).

## 6. Faz 1 kurulum talimatı (çalışanlar için)

Ön koşul: ERP prod'da **HTTPS** ile yayınlanmalı (service worker ve kamera HTTPS ister; `localhost` istisna).

- **Android (Chrome):** ERP adresini açın → menü → "Uygulamayı yükle" / "Ana ekrana ekle".
- **iPhone/iPad (Safari):** ERP adresini açın → Paylaş → "Ana Ekrana Ekle". (Uygulama içinde bir kez giriş yapılır; Safari oturumundan ayrıdır.)
- **Yönetilen cihazlar:** Android → managed Google Play "web app"; iOS → MDM Web Clip.
- İlk açılışta cihaz Admin → Mobile Apps → Device Manager'da görünür.

## 7. Doğrulama kanıtı

Bkz. `TASKS.md` M37 bölümü ve `coordination/milestones/M37/screenshots/`.
