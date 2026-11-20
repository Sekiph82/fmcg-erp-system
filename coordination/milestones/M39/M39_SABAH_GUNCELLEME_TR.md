# 20 Kasım 2026: sabah notlarınızın uygulanması

Durum işaretleri:
- **[v]** yapıldı ve test edildi.
- **[!]** sizden bir şey bekleniyor.

Test sonuçları:
- Arka uç testleri: 1737 geçti, 0 başarısız. 360 test gerçek veritabanı ya da posta sunucusu gerektirdiği için tam koşuda atlandı.
- Değişen akışlar, geçici veritabanlarında 17 dosyada ayrıca test edildi: 15 dosya toplu koşuda, kalan ikisi yerel posta sunucusuyla ayrı koşuldu.
- TypeScript ve eslint temiz.
- Yeni ekranlar tarayıcıda açıldı; API hatası yok.

Değişiklikleri ayrı bir yapay zekâ ajanı bağımsız olarak inceledi. Bulduğu 3 önemli ve 4 küçük konunun hepsi düzeltildi (bölüm 9).

---

## 1. Fiyat listesi [v]
- Verdiğiniz 91 ürünün fiyatı yüklendi. Liste adı: **POVU-INTERIM-USD**; aktif ve varsayılan liste.
- Liste dolar (USD) cinsinden. Dükkânlar ise Kenya şilini (KES) ile çalışıyor.
  - Dükkânın göreceği fiyat, finansın girdiği güncel USD→KES kuruyla otomatik çevrilir.
  - Kur girilmemişse ürün "fiyatsız" görünür ve sipariş edilemez.
  - Kur kendiliğinden tahmin edilmiyor.
- **[!] Yapmanız gereken:** Finans → Döviz kurları ekranına bugünün USD kurunu girin.
- Son fiyat listesi geldiğinde aynı yöntemle güncellenecek.

## 2. Üretim ↔ depolar ↔ muhasebe [v]
**Depo bağlantıları.** Yeni ekran: Üretim → *Warehouse Links*. Burada dört depo seçilir:
- hammadde deposu,
- ambalaj deposu,
- yarı mamul (WIP) deposu,
- sevke hazır bitmiş ürün deposu.

Üretim emri kapanınca:
- ambalaj malzemesi ambalaj deposundan düşer,
- yarı mamul WIP deposundan düşer,
- hammadde hammadde deposundan düşer,
- bitmiş ürün sevk deposuna girer.

**Muhasebe.** Üretim emri tamamlanınca tek bir yevmiye kaydı atılır:
- hammadde, ambalaj ve yarı mamul, standart maliyetle yarı mamul (WIP) hesabına geçer;
- işçilik, makine ve enerji maliyeti de WIP'e eklenir;
- WIP gerçek maliyetle bitmiş ürün stok hesabına aktarılır.

**Bulunan ve düzeltilen hata.** Hesap planı her açılışta kuruluyordu ama veritabanına hiç kaydedilmiyordu. Bu yüzden sistemde hesap yoktu. Artık kalıcı: 18 hesap. Hesaplara "1230 Ambalaj Malzemesi Stoku" eklendi.

## 3. Kenya Bordro detay sayfası [v]
"Aç" bağlantısı artık bordro koşusunun kendi sayfasını açıyor. Sayfada:
- toplamlar,
- çalışan bazında brüt, kesintiler ve net,
- yetkisi olana Hesapla / Onayla düğmeleri.

## 4. Şube bazlı finans/İK
Talimatınızla kapatıldı: bu işler merkez ofisten yapılacak.

## 5. Teslimatta fatura [v]
**Kanıt.** Teslimatta yeni bir cihaz gerekmiyor. Şoför uygulamada imzayı alıp "teslim edildi" dediği anda:
- fatura oluşur ve muhasebeye işlenir;
- faturanın vadesi, dükkânın tanımlı ödeme vadesine göre belirlenir;
- fatura dükkânın e-posta adresine gönderilir.

Fatura kesilemezse (örneğin satış muhasebe kuralı yoksa) teslimat yine tamamlanır. Fatura sonra ofisten kesilir.

**Pazar yeri siparişleri** (Shopify bugün; n11, Hepsiburada, Trendyol bağlantıları anahtarlar gelince):
- Fatura teslimatta değil, **ödeme alınınca** kesilir.
- Ödeme de kayda geçer, böylece müşteri borçlu görünmez.
- Fatura alıcının pazar yerindeki e-posta adresine gider.
- Depo toplama ekranında "faturanın kağıt kopyasını koliye koy" uyarısı ve **Yazdır** düğmesi çıkar.

Gittigidiyor 2022'de kapandığı için listeden çıkarıldı.

E-postaların gerçekten gitmesi için e-posta (SMTP) anahtarlarının girilmesi gerekiyor (bölüm 8).

## 6. Promosyonlar [v]
- Liste fiyatı her dükkân için aynı kalır.
- Promosyonlar ayrı tanımlanır. Bir promosyon şunlardan birine verilebilir:
  - tek bir dükkâna,
  - bir müşteri grubuna,
  - bir bölgeye,
  - bir kanala,
  - herkese.
- Dükkânın uygulamasında yeni sekme: **"My promotions"**. Dükkân kendine tanımlı promosyonları tablo halinde görür.
- Sipariş promosyona uyuyorsa yüzde indirim satıra yazılır. Faturada şunlar görünür:
  - liste fiyatı,
  - indirim yüzdesi,
  - son fiyat,
  - promosyonun adı.
- Hediye ürün ve sabit tutar indirimleri siparişe ve faturaya isimle kaydedilir. Ancak satır fiyatını değiştirmezler.

## 7. Para alanları sayı olarak [v]
- API'deki tüm para ve miktar alanları artık metin değil sayı olarak gidiyor. Bu, tek bir merkezi noktada yapıldı; 80 yeri tek tek değiştirmek gerekmedi.
- Ekranlardaki tip tanımları da buna göre düzeltildi.
- Veritabanında değerler hassas ondalık olarak kalıyor.

## 8. Sağlayıcı anahtarları için giriş ekranı [v]; anahtarlar [!]
Yeni ekran: **Entegrasyonlar → Provider Keys**. Yalnızca sistem yöneticisi ve sahip (owner) rolü görür. Her sağlayıcı için açılan pencereye anahtarları girersiniz:

| Sağlayıcı | Neye yarıyor |
|---|---|
| M-Pesa | Dükkânların ödemesi |
| SMS (Africa's Talking veya Twilio) | "Siparişiniz yolda" mesajı |
| WhatsApp (Meta) | "Siparişiniz yolda" mesajı |
| E-posta (SMTP) | Fatura ve kampanya postaları |

- Anahtarlar şifreli saklanır ve kaydedildikten sonra en geç 1 dakikada her yerde geçerli olur. Kodda değişiklik ya da yeniden başlatma gerekmez.
- Gizli değerler bir daha ekrana gelmez; ekranda yalnızca "girildi" görünür.
- Anahtarlar eksikken ana sayfada "anahtar bekleniyor" uyarısı çıkar.
- Şoför sefere başladığında her dükkâna "siparişiniz yolda" mesajı gider: WhatsApp varsa WhatsApp'tan, yoksa SMS ile. Anahtar girilene kadar sessizce atlanır.
- **[!] Yapmanız gereken:** sağlayıcılardan aldığınız bilgileri bu ekrana girmek.

---

## 9. Bağımsız incelemede bulunan ve düzeltilen konular
1. Ödenmiş pazar yeri faturası muhasebede açık alacak olarak kalıyordu. Artık ödeme de kaydediliyor.
2. Geçersiz sayılar (NaN veya sonsuz) yanıtın tamamını bozabiliyordu. Artık boş değer olarak gidiyor.
3. Şifreli anahtar kayıtları genel ayarlar listesinde görünüyordu. Artık gizli.
4. Küçük konular:
   - e-posta sorunu teslimatı geri alabiliyordu;
   - iptal edilmiş sipariş faturalanabiliyordu;
   - zaten faturalanmış siparişte "e-posta gönderildi" yanlış bildiriliyordu;
   - e-posta metninde promosyonlarla ilgili yanlış bir açıklama vardı.

---

## Sorularınızın cevapları

### Muhasebe kuralları nedir, ne işe yarar?
Sistemdeki her olayın muhasebede hangi hesaba borç, hangi hesaba alacak yazılacağını söyleyen tanımlardır. Örnekler:

| Olay | Borç | Alacak |
|---|---|---|
| Satış faturası kesildi | 120 Alıcılar (müşteri alacağı) | 600 Satışlar, 391 KDV |
| Bordro onaylandı | Personel gideri | Ödenecek ücretler, ödenecek vergi ve kesintiler |
| Üretim tamamlandı | Bitmiş ürün stoku | Yarı mamul (WIP) |

- Bu kurallar Finans → Posting Rules ekranında **bir kez** tanımlanır. Sonra sistem her olayda yevmiyeyi kendisi atar; muhasebeci tek tek fiş kesmez.
- Hangi hesabın kullanılacağı şirketin hesap planına bağlı olduğu için kuralları finans ekibi seçer.
- **Bugünkü davranış:**
  - Satış faturası için kural **zorunlu**. Kural yoksa ofisten fatura kesilemez; teslimattaki otomatik fatura da kesilmez ve ofise bırakılır.
  - Bordro, masraf, tedarikçi ödemesi, sayım farkı, POS ve üretim için kural yoksa işlem yine yapılır, yalnızca muhasebeye yazılmaz ve bu durum kayda geçer. Böylece kurallar tanımlanana kadar iş durmaz.
- **Önerim:** kurallar bir kez tanımlandıktan sonra hepsini zorunlu yapalım; böylece muhasebeye düşmeyen işlem kalmaz.
- Hesap planı artık hazır: 18 hesap, hammadde, WIP, bitmiş ürün ve ambalaj stokları dahil. İsterseniz önerilen kural setini hazırlayayım, finans onaylasın.

### İşveren bordro payı nedir?
Çalışanın maaşından kesilen tutarlara ek olarak, **işverenin kendi cebinden** devlete ödediği tutarlardır. Kenya'da başlıcaları:

| Pay | Ne kadar |
|---|---|
| NSSF (emeklilik) işveren payı | Çalışan payı kadar |
| Konut vergisi (Affordable Housing Levy) işveren payı | Brüt maaşın %1,5'i |
| NITA eğitim vergisi | Çalışan başına aylık 50 KES |

Türkiye'deki karşılığı SGK işveren payıdır.

- Bu tutarlar çalışanın netini değiştirmez ama şirkete ek maliyettir.
- **Bugün:** sistem çalışan kesintilerini hesaplıyor, bu işveren paylarını hesaplamıyor ve muhasebeye yazmıyor. Bu yüzden personel maliyeti olduğundan düşük görünüyor.
- **Önerim:**
  1. Bordro hesaplamasına bu payları ekleyelim.
  2. Muhasebeye ayrı bir satır olarak yazalım: personel gideri borç, ödenecek SGK/NSSF ve vergi alacak.
  3. Bordro ekranında "işverene toplam maliyet" sütunu gösterelim.
- **[!] Onay verirseniz yaparım.**

### Apple ve Google Play: SDK'lar var mı?
- **Bu bilgisayarda kurulu olanlar:**
  - Android SDK (platform 37, build-tools 36),
  - Android Studio,
  - Expo/EAS CLI 25.2.0.
- Android uygulaması bu bilgisayarda derlenebilir.
- **iOS:** Xcode yalnızca Mac'te çalışır. Bu bilgisayarda Apple SDK'sı kurulamaz. iOS derlemesi EAS ile Apple'ın bulut derleme servisi üzerinden yapılabilir; bunun için Mac gerekmez, Apple Developer hesabı yeterlidir.
- **Hesaplar:** hesap sayfalarına bakamadım, çünkü Chrome eklentisi (Claude in Chrome) bu oturumda bağlı değildi.
- **[!] Bakabilmem için:**
  1. Chrome'u açın.
  2. Araç çubuğundaki Claude simgesine tıklayıp aynı hesapla giriş yapın.
- **Gereken hesaplar:**
  - **Apple Developer Program:** yıllık 99 USD. Şirket adına açılacaksa D-U-N-S numarası gerekir.
  - **Google Play Console:** tek seferlik 25 USD. Kurumsal hesapta kimlik ve kuruluş doğrulaması var.

### Telefon testi (iPhone kabloyla bağlı)
- Bilgisayar şu anda iPhone'un USB internet paylaşımı üzerinden **172.20.10.4** adresinde. Bu adres için yeni sertifika üretildi ve uygulama bu adreste çalışıyor.
- **Adımlar:**
  1. iPhone'da Safari ile **http://172.20.10.4:8088/rootCA.crt** adresini açıp profili indirin.
  2. Ayarlar → Genel → VPN ve Aygıt Yönetimi bölümünden profili yükleyin.
  3. Ayarlar → Genel → Hakkında → Sertifika Güven Ayarları bölümünden güveni açın.
  4. **https://172.20.10.4:3443** adresini açın.
- **Yeniden denenecekler:**
  - SYNTH-TRIP-CC47 seferinde teslimat imzası. Bu sefer fatura da otomatik kesilecek; satış muhasebe kuralı tanımlıysa.
  - SYNTH-PICK-CC47 toplamasında kamerayla okutma.

---

# Ek: 20 Kasım öğleden önce — kararlarınızın uygulanması

## Muhasebe kural seti [v] — finans onayı bekliyor [!]
- Kural setini ben hazırladım: **16 kural**. Kapsadığı işlemler:
  - satış faturası;
  - müşteri tahsilatı (nakit, banka, M-Pesa);
  - POS satışı;
  - tedarikçi faturası ve tedarikçi ödemesi;
  - bordro ve işveren payları;
  - masraf;
  - sayım farkı;
  - üretimin 5 adımı.
- Hesap planı bunun için tamamlandı (34 hesap): banka, kasa, M-Pesa, alıcılar, KDV, satıcılar, bordro borçları, ücret ve işveren payı giderleri, fire, yarı mamul.
- Ekran: **Finans → Posting Rules**.
  - Her kuralın borç, alacak, vergi ve kasa/banka hesabı açılır listeden değiştirilebilir.
  - Finans **"Approve the rule set"** düğmesiyle onaylar. Hesabı eksik kural varsa onay verilmez ve eksikler listelenir.
- **Onaydan sonra hepsi zorunlu.** Kuralı olmayan bir işlem kaydedilmez, hata verir. Böylece muhasebeye düşmeyen işlem kalmaz.
- Onaya kadar eski davranış sürer: işlem kaydedilir, yalnızca deftere yazılmaz. Finans incelerken iş durmaz.

## İşveren bordro payları [v]
- Her çalışan için hesaplanıyor:
  - NSSF işveren payı (çalışanınkiyle aynı),
  - konut vergisi işveren payı (%1,5),
  - NITA (aylık 50 KES).
- Muhasebeye ayrı yevmiye olarak yazılıyor: işveren payı gideri borç, ödenecek işveren payları alacak.
- Bordro detay sayfasında çalışan bazında **işveren payı** ve **şirkete toplam maliyet** sütunları var.
- **Düzeltme:** NSSF tavanı eski 2023 değerinde kalmıştı (1.080 KES). Şubat 2025'ten beri geçerli limite göre güncellendi: üst sınır 72.000 KES × %6 = en fazla **4.320 KES**. İşveren de aynı tutarı öder. Maliyetler artık tam çıkıyor.

## Döviz kuru [v]
- Kenya Merkez Bankası'nın en son yayımladığı kur girildi: **1 USD = 129,99 KES** (19.11.2026). Bugünün kuru henüz yayımlanmamıştı.
- Dükkân fiyatları artık KES olarak çıkıyor. Örnek: 20 g toz deterjan 0,17 USD → **22,10 KES**.
- Yeni kurlar Finans → Exchange Rates ekranından girilir. Sistem her zaman en son tarihli kuru kullanır.

## iPhone sertifikası [v]
- **Sebep:** Safari, yazılan `http://` adresini otomatik olarak `https://`'e çeviriyor. 8088 portu düz HTTP olduğu için "güvenli bağlantı kurulamıyor" hatası çıkıyordu.
- **Çözüm:** Sertifika artık uygulamanın HTTPS adresinden de iniyor: `https://<IP>:3443/rootCA.crt`. Uyarıda "Ayrıntıları göster → web sitesini ziyaret et" deyip profili indirmek yeterli. `docs/PHONE_ACCEPTANCE_TEST.md` buna göre güncellendi.
- Telefonu çıkardığınız için geliştirme ortamı normal moda (localhost) alındı. Telefon testine döndüğünüzde LAN ortamını yeniden kurarım.

## Test ve inceleme
- Arka uç testleri: 1737 geçti, 0 başarısız.
- Etkilenen akışlar ayrı test veritabanlarında 26 dosyada ayrıca test edildi; hepsi geçti.
- Bağımsız inceleme ciddi bir hata bulmadı. Önerdiği iki iyileştirme uygulandı: onaydan önce eksik hesap kontrolü ve pasif kuralın doğru gösterilmesi.
- Yazdığım testler bir hatayı yakaladı: iki bordro yevmiyesi aynı numarayı alıyordu. Düzeltildi.

## Ek 2 — Otomatik kur, finansa kural seti, telefon

### Kur artık otomatik [v]
- Sistem Kenya Merkez Bankası ana sayfasındaki günlük kur kutusunu her 6 saatte bir kendisi okuyor: USD, GBP ve EUR.
- Okunan kur `exchange_rates` tablosuna CBK kaynağıyla yazılıyor.
- Finans aynı gün için elle kur girdiyse o kur korunur, üzerine yazılmaz.
- CBK'ya ulaşılamazsa son kayıtlı kur kullanılmaya devam eder.
- Finans → Exchange Rates ekranında "Fetch CBK rates now" düğmesi var.
- İlk otomatik çekim (20.11.2026): USD 130,00 · GBP 170,35 · EUR 142,71.

### Kural seti finansın karşısına çıkıyor [v]
- Kural seti onaylanana kadar CFO veya finans müdürü her oturumunun başında doğrudan Finans → Posting Rules ekranına düşer.
- CEO ve sahip yönlendirilmez.
- Kenya şirketi kurulup ilk finans kullanıcısı tanımlandığında bu ekran onun ilk göreceği şey olur. Onaydan sonra yönlendirme kendiliğinden durur.
