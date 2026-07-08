# Avcı Drone — Bozuk GNSS Kullanımı (CLAUDE.md)

Bu dosya, projeyi **yalnızca şartname Kural 2 — "Bozuk GNSS verisinin kullanımı"**
ekseninde tanımlar. Sistem **GPS-only**'dir: hedef uçağın bozuk GNSS verisiyle otonom
yaklaşma yapılır; **görsel takibe geçilmez** (kilitleme/handoff yoktur).

Kural 2'nin dört maddesi, ilgili kod dosyalarıyla birlikte aşağıda açıklanır.

## İLGİLİ DOSYALAR (bozuk GNSS zinciri)
- `sdk/drone_sdk.py`      → simülasyon I/O. Bozuk GNSS buradan **okunur**
  (`get_target_location`). Sim-gerçek/kıyas alanları: `get_debug_truth`, `get_active_corruption`.
- `fusion/gnss_filtre.py` → `GNSSFiltre` (bozuk GNSS'i **temizler/değerlendirir**):
  v1 z-spike + v2 x/y-spike + gecikme telafisi. Nedensel (yalnız geçmişe bakar).
- `guidance/gps_takip.py` → `GPSTakip`. Bozuk GNSS'i **hangi aşamada kullandığımız**:
  kalkış → GNSSFiltre ile temizleme → sürekli yaklaşma (güdüm girdisi budur).
- `web/gps_server.py`     → kontrol döngüsü + telemetri + **sapma/kesinti değerlendirmesi**
  (ham vs temiz hata penceresi, GNSS kesinti izleyici, olay günlüğü).
- `web/gps_index.html`    → arayüz: BOZUK GNSS GİRDİSİ paneli, sapma, kesinti rozeti,
  kuşbakışı harita (ham-bozuk hedef ↔ temiz hedef izleri).

---

## 1) Hedef uçağa ait bozuk GNSS verisinin nasıl OKUNDUĞU
- Kaynak: `sdk/drone_sdk.get_target_location()` → hedefin **(x, y, z)** konumu, santimetre.
  Bu akış **bozuktur** (spoof/sıçrama/gecikme/kayıp içerebilir); ana hedef sinyalimizdir.
- Okuma noktası: kontrol döngüsü (`web/gps_server.kontrol_dongusu`, ~50 Hz) her tikte
  `guidance/gps_takip.GPSTakip._hedef_temizle()` çağırır; o da `get_target_location()`'ı okur.
- **Yeni-paket tespiti:** `ham != self.son_ham` karşılaştırmasıyla yeni telemetri paketi
  ayırt edilir (rate-limit ile donmuş kareler yeni bilgi saymaz → `_fresh=False`).
- Bozulma bilgisi: `get_active_corruption()` aktif bozulma adlarını (ör. `FLAG_DELAY`,
  `FLAG_SPIKE`) verir; arayüzde "Aktif bozulma" olarak gösterilir.
- **Yalnızca sim/debug** için gerçek (bozulmamış) konum `get_debug_truth()` ile alınır;
  bu **güdüme girmez**, sadece hatayı ölçmek/kıyaslamak içindir (madde 3).

## 2) Bu verinin hangi AŞAMADA kullanıldığı
- **Kalkış (ilk aşama):** bozuk GNSS güdüme **girmez**. Drone bulunduğu yerden
  `TAKEOFF_ALT_AGL` (~10 m, kalkış noktası referanslı) kadar **dikey tırmanır**.
  Kalkışta **yumuşatma (rate-limit) ve frenleme (settle/momentum sönümü) YOKTUR**:
  tam `TAKEOFF_THR` komutu doğrudan uygulanır (`_send_ham`), hedef irtifaya varınca
  anında yaklaşmaya geçilir. Yalnız dikey; yatay/yaw yok.
- **GPS takip (yaklaşma):** kalkıştan sonra **tek güdüm girdisi temizlenmiş GNSS'tir.**
  Bu temiz kestirim **gecikme-telafilidir** (lead'li): ham GNSS ~`GECIKME_SN` eski
  konum verir; filtre `pos + hız·gecikme` ile ileri-tahmin yapar, böylece nişan geçmiş
  değil **güncel (gerçek) konuma** yapılır. Bu yüzden ham (bozuk/geciken) hedef ile
  temiz hedef arasında ~`gecikme·hız` kadar bir mesafe farkı görülür — bu farkın olması
  beklenir ve doğrudur. `GPSTakip.adim()` her tik bu temiz kestirimden şunları sürer:
  - **Yatay:** gecikme-telafili konum (`son_xy_anlik`) ile nişan; hedefi geçmemek için
    `APPROACH_STANDOFF` kadar geride pace (anti-overshoot). Kesintide `son_hiz·dr_dt`
    ile ölü-hesap devam eder.
  - **Dikey:** gecikme-telafili irtifa (`son_z_anlik`) üzerinden irtifa PID (anti-windup).
  - **Yaw:** burnu hedefe çevir (hedefi kadrajda tut).
- Bu sistemde başka güdüm fazı yoktur; bozuk-sonra-temizlenmiş GNSS **görev boyunca**
  kullanılır (sürekli yaklaşma + standoff'ta paceleme).

## 3) Hatalı ölçümlerin nasıl DEĞERLENDİRİLDİĞİ
Değerlendirme iki katmanlıdır: (a) **temizleme** (güdüme temiz veri ver), (b) **ölçme**
(temizlemenin gerçekten iyileştirdiğini kanıtla). Güdüme yalnız (a) girer.

**(a) Temizleme — `fusion/gnss_filtre.GNSSFiltre` (nedensel, yalnız geçmişe bakar):**
- **z-spike (v1, dikey):** ardışık değişim eşiği aşarsa spike; ölçümü atıp "son geçerli
  konum + son hız·dt" ile **sürdür** (dondurma değil → plato/sıçrama olmaz). `max_vz` ile
  hız kırpılır (uzun logda ıraksamayı önler).
- **x/y-spike (v2, yatay):** **iki kriter birlikte** aranır — (1) hız-tutarsızlık (adım
  hızı son-N hızdan çok saparsa) VE (2) konum sapması (beklenen konumdan uzaksa). İkisi de
  tetiklenirse spike → egimle devam. Gerçek dönüş konumda sapmaz → korunur; spike ikisinde
  de sapar → temizlenir. `max_hiz` ile egim kırpılır.
- **Gecikme telafisi:** sim bozuk GNSS'i ~`GECIKME_SN` (≈1 s) eski konum verir. Çıktı
  ileri-tahminle kapatılır (`pos + vel·gecikme_sn`); güdüme lead'li kestirim verilir.
- **Kayıp/boşluk yönetimi:** `dt > 5 s` felaket boşlukta ekstrapolasyon yapılmaz, ölçüm
  kabul edilir. Paket donması/dropout'ta (`_fresh=False`) son kestirim `HOLD_TICKS` (~6 s)
  tutulur; aşılırsa loiter (hover) — hatalı veriyle savrulma önlenir.

**(b) Ölçme/gösterge — `web/gps_server.py` + arayüz:**
- **Sapma (ham vs temiz):** her yeni pakette, ham ve temiz(anlık) kestirimin **gerçeğe**
  (truth) hatası ölçülür; son ~80 paketlik pencerede ortalama/std/max hesaplanır ("filtre
  iyi mi?" göstergesi). Arayüz: BOZUK GNSS GİRDİSİ → "Ham hata" vs "Temiz hata".
- **J düzeltme (anlık):** truth gerektirmeden, ham ↔ temiz(anlık) farkının büyüklüğü
  (filtrenin o an ne kadar düzelttiği).
- **GNSS kesinti izleyici:** paket yaşı `GNSS_KESINTI_S`'i aşarsa **KESİNTİ** olayı/rozeti;
  paket geri gelince "kesinti bitti". Gerçek yarışmada truth olmadan da çalışır.
- Ayrıca `veri/gps_takip_sapma.json` (bozuk+gerçek konum) ve `gps_takip_*.csv` uçuş logu
  offline analiz için yazılır.

## 4) Görsel takip başladıktan sonra GNSS bağımlılığının azaltılması / sonlandırılması
- **Bu sistemde görsel takip YOKTUR ve asla başlatılmaz** (kilitleme/handoff kaldırıldı).
  Dolayısıyla görsel faza devir ve "GNSS bağımlılığını azaltma/sonlandırma" adımı **kapsam
  dışıdır.** GPS takip görev boyunca temizlenmiş GNSS ile **sürekli yaklaşma** yapar.
- Yaklaşma sonu davranışı: hedefi geçmez; `APPROACH_STANDOFF` mesafesinde önünde pace eder
  (kilit/terminal vuruş/görsel devir yok).
- Görsel faz (kamera-tabanlı takip) ileride eklenirse, GNSS bağımlılığının azaltılması bu
  belgeye ayrı bir madde olarak eklenecektir; mevcut mimaride tanımlı değildir.

---

## DEĞİŞMEZ İLKE
Bozuk GNSS zincirinin her parçası (okuma, temizleme, değerlendirme) **bizim temiz,
açıklanabilir implementasyonumuzdur** (yarışma kuralı: her bileşeni açıklayabilmeliyiz).
Hazır güdüm/filtre yazılımı doğrudan kullanılmaz; senaryoya aşırı-uydurulmuş sabitler
konmaz. Temizleme eşikleri gerçek loglardan kalibre edilmiştir ve takımca açıklanabilir.
