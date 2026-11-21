# Canlı Anahtarlar Rehberi (M-Pesa, SMS, WhatsApp, SMTP, Shopify, Yapay Zekâ)

Bu dosya, ERP'yi gerçek sağlayıcılara bağlamak için adım adım yol haritasıdır.
Zamanı gelince bu dosyayı açın ve sırayla ilerleyin. Kontrol listesi en altta.

> **Güvenlik kuralları**
> - Anahtarları bu dosyaya, e-postaya, sohbete veya git'e **yazmayın**. Yalnızca uygulama ekranına ya da sunucudaki `.env.production` dosyasına girilir.
> - `.env.production` git'e gönderilmez; sunucuda kalır.
> - Uygulama ekranına girilen anahtarlar şifreli saklanır; ekran yalnızca "girildi / girilmedi" gösterir.
> - `SECRET_KEY` değiştirilirse ekrandan girilmiş anahtarlar çözülemez → hepsi yeniden girilmelidir. Önce `SECRET_KEY`'i kesinleştirin, sonra anahtarları girin.

---

## 0. Ön koşullar (hepsinden önce)

1. **Herkese açık alan adı + HTTPS** (ör. `erp.sirketiniz.co.ke`). M-Pesa geri bildirimi, WhatsApp webhook'u ve web push bunsuz çalışmaz.
2. Sunucuda `.env.production` hazır (`.env.production.example` kopyalanarak):
   - `ENVIRONMENT=production`
   - `SECRET_KEY` ve `WEBHOOK_SECRET_ENCRYPTION_KEY`: her biri 64 karakter rastgele hex. Üretmek için:
     ```powershell
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - `PUBLIC_APP_URL=https://<alan-adınız>`
   - `OTP_DEV_DELIVERY_MODE=false` (üretimde zorunlu)
3. Uygulamayı yeniden başlatın: `docker compose -f docker-compose.prod.yml up -d`

---

## Anahtarlar nereye girilir?

| Sağlayıcı | Nereye | Kim girebilir |
|---|---|---|
| M-Pesa, SMS, WhatsApp, SMTP | Uygulama: **Entegrasyonlar → Provider keys** (`/dashboard/integrations/provider-keys`) | Süper kullanıcı veya `integrations.provider_keys` yetkisi (varsayılan: yalnız sahip rolü) |
| WhatsApp webhook doğrulama tokenı | Uygulama: **WhatsApp → Config sekmesi** | WhatsApp yöneticisi |
| Shopify, Yapay zekâ, MQTT | Sunucu: `.env.production` + yeniden başlatma | Sunucu yöneticisi |

Ekrandan girilen değer `.env`'dekini ezer; diğer sunucu işçileri 1 dakika içinde alır. Gizli alan boş bırakılırsa kayıtlı değer korunur.

Her adımdan sonra **Entegrasyonlar → Console** ekranına bakın: bağlayıcı yalnızca gerçek başarılı bir çalışmadan sonra **HEALTHY** olur. Anahtar girmek tek başına yeşil yapmaz.

---

## 1. M-Pesa (Safaricom Daraja) — STK ödeme, mutabakat

**Sağlayıcıdan alınacaklar** (developer.safaricom.co.ke → uygulama oluştur → "Lipa Na M-Pesa Online"):
- Consumer key, Consumer secret
- Paybill veya Till numarası (shortcode)
- Lipa na M-Pesa passkey (canlı için Safaricom "Go Live" sürecinden gelir)

**Provider keys → M-Pesa (Safaricom Daraja) alanları:**

| Alan | Değer |
|---|---|
| Environment | Önce `sandbox`, testler bitince `production` |
| Paybill / till number | Shortcode |
| Transaction type | Paybill ise `CustomerPayBillOnline`, Till ise `CustomerBuyGoodsOnline` |
| Consumer key / secret | Daraja'dan |
| Lipa na M-Pesa passkey | Daraja'dan |
| Callback secret token | Uzun rastgele değer (yukarıdaki python komutuyla üretin) |
| Callback URL | `https://<alan-adınız>/api/v1/integrations/mpesa/callback?token=<callback secret>` |

**Test:** Satış siparişinde veya saha uygulamasında küçük tutarlı (ör. 1 KES) STK ödeme başlatın → telefonda PIN → işlem ERP'de "tamamlandı" görünmeli → Finans → M-Pesa mutabakat ekranında eşleşmeli. Token'sız gelen geri bildirimler reddedilir (bu doğru davranış).

---

## 2. SMS — iki aşamalı giriş kodu, müşteri bildirimleri

**Sağlayıcı:** Africa's Talking (Kenya için önerilen) veya Twilio.

| Alan | Africa's Talking | Twilio |
|---|---|---|
| Provider | `africastalking` | `twilio` |
| Username / Account SID | AT kullanıcı adı | Account SID |
| API key / auth token | AT API key | Auth token |
| Sender ID | Onaylı Sender ID (ör. `POVU`) | Gönderen numara |

SMS ile giriş kodu için `.env.production` içinde `TWO_FACTOR_SMS_ENABLED=true`.

**Test:** SMS 2FA açık bir test kullanıcısıyla giriş yapın → kod telefona gelmeli.

---

## 3. WhatsApp Business (Meta Cloud API) — müşteri mesajları

**Meta'dan alınacaklar** (business.facebook.com → WhatsApp → API Setup):
- Phone number ID
- Kalıcı erişim tokenı (System User token; geçici 24 saatlik token değil)
- App secret (App Settings → Basic)

**Adımlar:**
1. Provider keys → WhatsApp Business: Phone number ID, Permanent access token, App secret.
2. Uygulama → **WhatsApp → Config sekmesi**: bir webhook doğrulama tokenı belirleyin (kendiniz uydurursunuz, uzun rastgele).
3. Meta → WhatsApp → Configuration → Webhook:
   - Callback URL: `https://<alan-adınız>/api/v1/whatsapp/webhook`
   - Verify token: 2. adımdaki token
   - Abone olun: `messages`
4. Mesaj şablonlarını Meta'da onaylatın (ERP'de WhatsApp → Templates ile adları aynı olmalı).

**Test:** Kendi numaranızdan işletme numarasına mesaj atın → WhatsApp → Conversations'ta görünmeli; ERP'den cevap verin → telefona gelmeli. İmzası tutmayan webhook'lar reddedilir.

---

## 4. Giden e-posta (SMTP) — faturalar, kampanyalar, giriş kodları

**Sağlayıcı:** Şirket e-posta sunucusu, Microsoft 365, Google Workspace, SendGrid, Mailgun vb.

| Alan | Örnek |
|---|---|
| SMTP server | `smtp.office365.com` / `smtp.gmail.com` / `smtp.sendgrid.net` |
| Port | `587` |
| Username / Password | SMTP kullanıcısı / uygulama şifresi (Gmail/M365'te normal şifre değil, "app password") |
| From address | `noreply@<alan-adınız>` |
| Send e-mail | `true` (kampanya e-postalarını açar) |

Alan adı DNS'inde SPF, DKIM ve DMARC kayıtlarını sağlayıcının verdiği şekilde ekleyin; yoksa e-postalar spam'e düşer.

**Test:** CRM → Outbox'tan kendinize test e-postası → gelmeli. Console'da e-posta satırı HEALTHY olmalı.

**Gelen kutular (isteğe bağlı):** CRM → Inbox'a bağlanacak IMAP kutuları CRM ekranından ayrı ayrı eklenir.

---

## 5. Shopify — web siparişleri ve stok

**Shopify'da** (Settings → Apps and sales channels → Develop apps → Create app):
- Admin API izinleri: `read_orders`, `read_products`, `read_inventory`, `write_inventory`, `read_locations`
- Uygulamayı kurun → **Admin API access token**'ı kopyalayın (yalnızca bir kez gösterilir).

**ERP'de önce hazırlayın:**
- **Misafir siparişleri** için bir müşteri kaydı (ör. "Online Mağaza") → id'sini not edin. Hesabı olan Shopify alıcıları otomatik olarak ERP müşterisi (kanal ONLINE) olur.
- Web siparişleri ve stok için **depo** → id'sini not edin.
- Shopify ürün SKU'ları ERP ürün SKU'larıyla **birebir aynı** olmalı (ör. POVU SKU'ları). Bir satırı bile eşleşmeyen sipariş FAILED olarak nedeniyle kaydedilir, satış siparişi oluşmaz; SKU düzeltilip yeniden senkron edilir.

**Sunucu `.env.production`:**
```
SHOPIFY_SHOP_DOMAIN=<magaza>.myshopify.com
SHOPIFY_ACCESS_TOKEN=<Admin API token>
SHOPIFY_API_VERSION=2024-10
SHOPIFY_LOCATION_ID=<Shopify lokasyon id>
SHOPIFY_CUSTOMER_ID=<ERP müşteri id>
SHOPIFY_WAREHOUSE_ID=<ERP depo id>
```
Sonra yeniden başlatın.

**Test:** Shopify'da test siparişi verin → Entegrasyonlar → Console → Shopify → "Sync" → sipariş ERP'de taslak satış siparişi olarak görünmeli; stok Shopify'a gitmeli. Eşleme hataları Console'daki eşleme sağlığında listelenir.

---

## 5b. KRA eTIMS (e-fatura) — önce karar gerekir

Kod şu an `ETIMS_PROVIDER=simulation` ile çalışır; KRA'ya hiçbir şey gitmez.
Canlıya geçmeden önce **bağlantı yolu seçilmeli**: doğrudan KRA OSCU/VSCU, KRA onaylı ara yazılım (middleware) veya üçüncü taraf servis sağlayıcı. Seçilen sağlayıcının API dokümanı geldiğinde kodda sağlayıcıya özel 3 parça tamamlanacak: kimlik doğrulama başlığı, iptal ve durum sorgulama (etims_connector.py'de işaretli).

**KRA'dan / sağlayıcıdan alınacaklar:** KRA PIN, şube kodu (bhfId), OSCU/VSCU cihaz seri numarası, sağlayıcının API adresi.

**Sunucu `.env.production`:**
```
ETIMS_PROVIDER=http
ETIMS_ENV=sandbox
ETIMS_API_URL=<sağlayıcı adresi>
ETIMS_PIN=<KRA PIN>
ETIMS_BRANCH_ID=<bhfId>
ETIMS_DEVICE_SERIAL_NO=<cihaz seri no>
```
**Test:** sandbox'ta bir fatura gönderin → KRA kontrol numarası ve QR faturaya gelmeli → sonra `ETIMS_ENV=production`.

## 5c. Banka bağlantısı

Bankaya göre değişir (Equity, KCB, Co-op, NCBA… her birinin kendi API'si ve sözleşmesi var). Banka seçilip API erişimi alınınca bağlayıcı o bankaya göre tamamlanır; şimdilik banka ekstresi dosya ile içe aktarılır.

---

## 6. Yapay zekâ (isteğe bağlı)

`.env.production` içine **birini** girin (sıra: Anthropic → OpenAI → Gemini):
```
AI_PROVIDER=auto
ANTHROPIC_API_KEY=<anahtar>
```
Müşteri/tedarikçi adları varsayılan olarak dış modele gönderilmez (`AI_SEND_CUSTOMER_NAMES_TO_LLM=false`); öyle kalmasını öneririm.

---

## 7. Diğerleri (isteğe bağlı)

- **Web push (PWA bildirimleri):** anahtar gerekmez; ilk kullanımda otomatik üretilir. Yalnızca `PUBLIC_APP_URL` doğru olmalı.
- **IoT / MQTT:** `MQTT_BROKER_URL=mqtts://<broker>:8883`, `MQTT_USERNAME`, `MQTT_PASSWORD` (üretimde TLS zorunlu).
- **Virüs taraması (belge yüklemeleri):** `DOCUMENT_CLAMAV_HOST=<clamav sunucusu>`.

---

## Son adım: kullanıcı kapsamları

Canlıya geçmeden önce **Yönetim → Kullanıcılar → Kapsamlar**: operatörlere üretim hattı, bölgesel/departman yöneticilerine kendi kapsamları atanmalı. Kapsamsız kullanıcının temel yetkisi tüm şirkette geçerlidir.

---

## Kontrol listesi

- [ ] Alan adı + HTTPS hazır, `PUBLIC_APP_URL` girildi
- [ ] `SECRET_KEY`, `WEBHOOK_SECRET_ENCRYPTION_KEY` üretildi, `OTP_DEV_DELIVERY_MODE=false`
- [ ] M-Pesa sandbox testi geçti → `production`'a alındı → 1 KES canlı test geçti
- [ ] SMS: giriş kodu telefona geldi
- [ ] WhatsApp: webhook doğrulandı, gelen ve giden mesaj test edildi
- [ ] SMTP: SPF/DKIM/DMARC eklendi, test e-postası geldi
- [ ] Shopify: müşteri/depo id'leri girildi, SKU'lar eşleşti, test siparişi aktarıldı
- [ ] eTIMS: sağlayıcı seçildi, sandbox faturası KRA'dan onay aldı
- [ ] Banka: banka seçildi, API erişimi alındı
- [ ] Console'da bağlanan her satır HEALTHY
- [ ] Kullanıcı kapsamları atandı
- [ ] TASKS.md'deki ilgili [!] satırları kanıtla güncellendi
