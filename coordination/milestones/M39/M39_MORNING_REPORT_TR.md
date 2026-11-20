# Sabah raporu — 19/20 Kasım 2026 gece çalışması

Hazırlayan: Claude (otonom). Tüm işler `main` dalına commit + push edildi; her commit'in yerel ve uzak SHA'sı eşit.
Bu rapor dürüst durumdur: [v] = yapıldı ve test edildi, [x] = bağımsız inceleme de geçti, [!] = sizden/dışarıdan bir şey gerekiyor.

---

## 1. Kısa özet

- **Herkes yalnızca kendi ekranlarını görüyor.** Kurulu 42 rolün her biri için sahte bir kullanıcıyla tüm menü ve sekmeler tek tek açıldı.
  - İlk taramada **314 sorun** çıktı: görünen ama açılınca "Access restricted", 403 veya 500 veren ekranlar.
  - Düzeltmelerden sonra 42 rolde **4 sorun** kaldı. Dördü de aynı nedenden: üretim operatörü ve denetçi rolündeki test kullanıcılarına üretim hattı atanmamış. Bu bir kod hatası değil, kullanıcı tanımlanırken yapılacak bir ayar.
- **Dükkânlar kendi siparişini veriyor.** Uygulamadan kayıt isteği, sipariş, ödeme (kapıda nakit / M-Pesa / vadeli) ve şoförün tahmini varış saatiyle takip yapılabiliyor.
- **Sistemler arası kopuk bağlar kapatıldı.** Şu işlemler artık muhasebeye (genel deftere) yevmiye kaydı olarak düşüyor:
  - bordro onayı,
  - masraf onayı,
  - tedarikçi ödemesi,
  - sayım farkı,
  - POS satışı (iptalde ters kayıt).
- **Satış ile depo birbirine bağlandı.** Sevkiyat, depo zemininde okutmalı toplama görevi oluşturuyor. Yeni dükkân/saha siparişinde satış masasına zil bildirimi gidiyor.
- **Yeni roller eklendi:** muhasebeci, bordro sorumlusu, planlamacı, sipariş masası, saha denetçisi, saha şefi.
- **Her kullanıcı için "Bugünkü işlerim" ana ekranı var.**

---

## 2. Ne eksikti → ne yapıldı (commit'ler)

| Commit | Ne eksikti | Ne yapıldı |
|---|---|---|
| 66081d0 | Telefon testinde saha menüsü çok geniş, iPhone kamera okutma çalışmıyor, ofis ekranlarında hatalar, POVU ürünleri yok | Saha menüsü en az yetkiye indirildi, iPhone kamera okutma düzeltildi, ofis hataları giderildi, POVU ürün yelpazesi ve 54 fotoğraf yüklendi |
| 8a29f1b | M39 iş listesi yoktu | TASKS.md'ye M39 (rol taraması + dükkân siparişi) eklendi |
| 1b42325 | Dükkân sipariş veremiyor, ödeyemiyor, siparişini takip edemiyordu; zil bildirimi herkese 403 veriyordu; Saha Uygulaması/My HR herkese görünüyordu | Dükkân kaydı, ödeme yöntemi, M-Pesa ödeme, durum çizelgesi ve tahmini varış eklendi; zil herkesin kendi bildirimlerini gösteriyor; menüler kişinin kimliğine göre |
| 0b2e1ca | Rol taramasında sunucu hatası (500) veren ekranlar | Rota, parti, QC, fire, WIP listeleri, MRP paneli, satın alma listesi düzeltildi |
| 0cf0032 | Satış sevkiyatı depo zeminine düşmüyordu; yeni sipariş kimseye haber vermiyordu | "Toplamaya başla" her satır için okutma görevi açıyor; satış masasına bildirim gidiyor |
| bbd20d2 | Onaylanan bordro muhasebeye geçmiyordu | `payroll/PAYROLL_APPROVED` kuralıyla yevmiye |
| 90aa996 | Onaylanan masraf muhasebeye geçmiyordu | `expenses/EXPENSE_FINANCE_APPROVED` kuralıyla yevmiye |
| 2326b96 | Tedarikçi ödemesi muhasebeye geçmiyordu | `procurement/SUPPLIER_PAYMENT_MADE` kuralıyla yevmiye |
| 403b6cc | Takvim açılmıyordu; webhooks sekmesi herkese görünüyordu | Takvim düzeltildi; webhooks yalnız süper kullanıcıya |
| 99d0d18 | Sayım farkı muhasebeye geçmiyordu | `inventory/STOCK_ADJUSTMENT` kuralıyla yevmiye (eksik: gider/stok, fazla: tersi) |
| 6f10e64 | POS satışı muhasebeye geçmiyordu | `pos/POS_SALE` kuralıyla yevmiye; iptal ters kayıt atıyor |
| 782087f | Muhasebeci, bordro sorumlusu, planlamacı, sipariş masası rolleri yoktu; açılış ekranı herkes için aynıydı | Roller eklendi; herkese "Bugünkü işlerim" (kendi kuyruğu, onaylar, istisnalar) |
| 607aa5f | Bağımsız inceleme bulguları | İnceleme bulguları düzeltildi; sekme izinleri taramaya göre ayarlandı |
| (bu sabahki son commit) | İkinci taramada kalan izin uyuşmazlıkları | Bkz. bölüm 3 |

Ayrıca: Docker Desktop'ta kullanılmayan imajlar ve volume'lar temizlendi (bu projeye ait olmayanlara dokunulmadı, bkz. bölüm 6).

---

## 3. Bu gece son turda düzeltilenler (rol taraması 2. ve 3. tur)

1. **İzin kontrolü arka uçla aynı hale getirildi.**
   - `modül.işlem_all` yetkisi artık hem ön yüzde hem arka uçta düz `modül.işlem` kontrolünü karşılıyor.
   - Kapsam farkında olmayan modüllerde (İK, bordro, bakım, yardımcı tesisler) "kendi kapsamı" yetkisi ekranı açmıyor. Böylece ekran açılıp sonra hata vermek yerine hiç gösterilmiyor.
2. **Sekmeler, API'lerinin istediği yetkiye göre gösteriliyor.** Kapsanan alanlar:
   - Pazarlama (kampanya, promosyon, trade spend, reklam, sosyal medya, segment, influencer, e-ticaret, marka harcaması, ziyaret, analitik),
   - Finans,
   - Analitik,
   - Satış,
   - Satın alma,
   - Üretim maliyeti (WIP / maliyet / sapma),
   - Kalite (tüketici şikâyetleri),
   - Yönetim (şirketler, onaylar).
3. **Kenya Bordro ekranına hiç girilemiyordu.** Eski bir yönlendirme `/dashboard/payroll` adresini İK sayfasına atıyordu, bu yüzden finans müdürü "Access restricted" görüyordu. Yönlendirme kaldırıldı.
4. **Giriş sonrası açılan ilk ekran düzeltildi.** Yalnızca toplama/yerleştirme yetkisi olan depo toplayıcı artık Depo Zemini'ne düşüyor (önce Stok sayfasında "Access restricted" görüyordu). Genel kural: bir modülün sayfası ancak `modül.view` yetkisi varsa ilk ekran olarak açılıyor.
5. **E-posta kampanyası yazarları şirket listesini görebiliyor.** Bunun için yönetici yetkisi gerekmiyor; yeni uç `/crm/email-campaigns/companies`.
6. **Diğer düzeltmeler:**
   - Üretim şefine reçete görüntüleme yetkisi verildi.
   - Bazı paneller artık sadece yetkisi olanda veri çekiyor: nakit pozisyonu, M-Pesa özeti, raporlar, roller, tedarikçiler, reçeteler, kampanyalar, kapasite raporu.

---

## 4. Rol taraması — kanıt

- **1. tur (düzeltmelerden önce):** 38 rolde 314 sorun.
- **Son durum:** 42 rolde 4 sorun. Kalanlar:
  - `shop_floor_operator`: 3,
  - `read_only_auditor`: 1.
  - İkisinin de nedeni üretim hattı kapsamının atanmamış olması.
- **Diğer kontroller:**
  - Arka uç testleri: 1736 geçti, 352 atlandı (ayrı veritabanı gerektirenler), 0 başarısız.
  - TypeScript ve eslint temiz.
  - Son düzeltmeler bağımsız incelemeden geçti; hata bulunmadı.
- **Rol bazında tablo:** `coordination/milestones/M39/M39_PERSONA_GAP_AUDIT.md` bölüm 4.

---

## 5. Devam eden / açık işler

| Konu | Durum | Gereken |
|---|---|---|
| Üretimde hammadde tüketimi ve mamul maliyeti muhasebeye geçmiyor | açık | Standart maliyetle WIP ve mamul girişini kaydetme (sonraki iş) |
| Kapsamlı şablon roller (şube finans/İK, denetçi) finans/İK verisini göremiyor | ekranlar gizlendi, hata vermiyor | Şube bazlı finans/İK kullanıcısı istenirse bu API'lere kapsam filtresi yazılmalı |
| Üretim operatörünün canlı kuyruk / makine ekranı | operatöre hat kapsamı atanmamış | Operatör tanımlanırken üretim hattı kapsamı atanmalı |
| Kenya bordrosunda "Aç" bağlantısı İK bordro çekmecesine gidiyor | eski davranış, bu gece değişmedi | Kenya bordro koşusu için ayrı detay sayfası |
| Dükkâna "yolda" SMS/WhatsApp | yok | SMS/WhatsApp sağlayıcı bilgileri [!] |

### Sizin kararınızı bekleyenler

1. **Muhasebe kuralları zorunlu mu?** Beş yeni kural (bordro, masraf, tedarikçi ödemesi, sayım, POS) finans tarafından tanımlanana kadar onaylar yine çalışıyor, olay "kaydedilmedi" olarak loglanıyor. Seçenekler: böyle kalsın / satış faturası gibi zorunlu olsun.
2. **Teslimatta otomatik fatura mı?** Kapıda nakit dükkânlar ofis işlem yapana kadar fatura almıyor.
3. **Promosyonlar dükkân fiyatına yansısın mı?** Şu an satış ekibi görüyor, portal fiyatı uygulamıyor.
4. **Para alanlarının metin olarak gönderilmesi.** Yaklaşık 80 yer etkileniyor. Ekranlarda `Number()` ile düzeltildi; API tarafında tümden sayıya çevrilsin mi?
5. **İşveren bordro payları** çalıştırma toplamlarına ve muhasebeye eklensin mi?
6. **Üretim maliyeti muhasebeye** (yukarıdaki açık iş) bir sonraki öncelik mi?
7. **Şube bazlı finans/İK** kapsam filtresi gerekli mi?

### Dışarıdan gerekenler [!]

- **POVU fiyat listesi:** ürünler fiyatsız yüklendi, dükkânlar bu ürünleri sipariş edemez.
- **App Store / Google Play:** şirketin Apple Developer ve Google Play hesapları gerekiyor.
- **Canlı M-Pesa ve SMS/WhatsApp sağlayıcı bilgileri.**

---

## 6. Docker temizliği

- Bu projenin kullanmadığı imaj ve volume'lar silindi.
- Kalanlar (yaklaşık):
  - **~30 GB imaj** ve **~7.6 GB volume**: başka projelere ait olduğu için dokunulmadı. İsterseniz Docker Desktop'tan ya da `docker image prune -a` / `docker volume prune` ile siz silebilirsiniz (geri alınamaz).
  - **~22.6 GB build cache:** `docker builder prune` ile temizlenebilir.

---

## 7. Telefon testi (yeni Wi-Fi IP: 192.168.1.192)

Telefon artık kablo yerine Wi-Fi ile bağlanıyor:

1. Bilgisayarda `python scripts/dev_lan_tls.py` çalıştırın. Yeni IP için sertifika üretilir.
2. iPhone'a yeni CA profilini kurup güvenin.
3. `docs/PHONE_ACCEPTANCE_TEST.md` adımlarını izleyin.

Yeniden denenecekler:

- SYNTH-TRIP-CC47 seferinde teslimat imzası,
- SYNTH-PICK-CC47 toplamasında kamera ile okutma.
