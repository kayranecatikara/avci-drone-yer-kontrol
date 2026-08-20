# Avcı Drone — Proje Notları (CLAUDE.md)

## KAPSAM (2026-08-20 sadeleştirmesi)
Proje **yalnızca iki şeyden** ibarettir: **GPS takip** (bozuk GNSS ile yaklaşma)
ve **görsel takip** (kamera ile IBVS güdüm). Web arayüzü, poz/PnP kestirimi, tune
raporu, kilit sayacı, görüntü-düzlemi köprüsü, gyro-CMC, analiz araçları, testler
ve arşiv **kaldırıldı** (kullanıcı kararı; git geçmişinde `main` branch'inde durur).
Sistem terminalden çalışır: `python3 -m control.main`.

Simülasyon ortamı bir **Unreal Engine oyunudur** (Drones of War). Gazebo, MAVLink,
ArduPilot SITL gibi katmanlar bu projede **YOKTUR** ve eklenmez; araç I/O'su
`sdk/drone_sdk.py` (resmi yarışma SDK'sı, TCP) üzerinden gider.

## DOKUNULMAZ
- `Drones of War Teknofest/` — oyun paketi (gitignore'lu, repoya konmaz).
- `sdk/` — resmi yarışma SDK'sı. **Değiştirilmez.**

## MİMARİ (modül → görev)
```
control/main.py        → görev gözetmeni: 50 Hz döngü, GPS ↔ GÖRSEL faz devri
control/gps_approach.py→ GPSTakip: kalkış + bozuk GNSS ile yaklaşma (Faz 1)
control/gorsel_takip.py→ GorselTakip: basit IBVS görsel güdüm (Faz 2)
control/common.py      → skaler yardımcılar + KomutGonderici (TEK komut çıkışı)
fusion/gnss_filtre.py  → GNSSFiltre: spike temizleme + hız kestirimi + gecikme telafisi
perception/camera.py   → ekran yakalama (mss) → tespit → takip → detection_state
perception/detector.py → YOLO (models/best.pt) + pervane maskesi
perception/tracking.py → HybridSort (boxmot) kimlik sürekliliği
perception/detection_state.py → kamera thread'i ↔ güdüm döngüsü köprüsü
scripts/start_game.sh  → oyunu Wine ile başlatır (TEK başlatma scripti)
```

## ⛔ KATI KURAL — GÖRSEL FAZDA GPS/GNSS YASAK (diskalifiye sebebi)
Görsel temas **sağlandıktan sonra** hareket komutu **yalnızca görsel veriden**
türetilir. Kural **yapısal** sağlanır: `GorselTakip.hesapla(det, own_pitch_rad)`
imzasında hedefe ait tek veri **bbox pikselleri**dir — konum/hız/GNSS kestirimi
parametre olarak bile geçmez. `own_pitch_rad` **kendi IMU pitch'imizdir**
(ego-motion telafisi), hedef verisi değildir → kurala uygun.
`control/main.py` görsel fazda yalnızca `gps._hedef_temizle()` çağırır; bu
**hiçbir komuta girmez**, sadece faz geri dönerse filtre ısınmış olsun diyedir.
**Görsel güdüm için ASLA GPS/filtre tabanlı bir çözüm önerme.**

## GPS GÜDÜMÜNÜN ROLÜ (net sınır)
GPS fazı öldürücü faz değildir. Görevi: (1) bozuk GNSS'i temizle ve hedef hızını
kestir, (2) araca yönel, (3) hedefle kesintisiz görsel temas kur (kadrajda tut),
(4) görsel faza temiz devret. Terminal takip görsel fazın işidir.

## FAZ DEVİR KAPISI
İki koşul **birlikte**: (1) yakınlık — `Cfg.HANDOFF_RANGE` (40 m) altı ya da GNSS
bayat; (2) görsel kilit — ard arda `N_LOCK`(5) karede güdüme girebilecek kutu.
Kutu kapısı **tek yerde**: `control.gorsel_takip.nisan_kutusu`. Gözetmen ve görsel
faz **aynı kapıyı** kullanır — iki katmana ayrı eşik yazmak, görsel fazın aynı
karede reddettiği kutuyla devir yapılmasına ve fazın sürekli sekmesine yol açar.
Görsel fazda tespit `LOST_S`(0.8 s) gelmezse GPS'e dönülür (yeniden kilitlenme).

## ÇALIŞMA İLKELERİ (değişmez)
- **Sadece üzerinde çalıştığımız, açıklayabildiğimiz şeyi kullan** (yarışma kuralı 8:
  her bileşeni açıklayabilmeliyiz). Bakmadığımız yabancı modüller entegre EDİLMEZ.
  Bilinen istisna: `boxmot` HybridSort (kullanıcı riski bilerek onayladı).
- **Hazır güdüm yazılımı doğrudan kullanılmaz** (kural 6). Filtre ve IBVS yasası
  bizim temiz implementasyonumuzdur.
- Senaryoya aşırı-uydurulmuş sabitler (örn. "lock 5.2 sn") kullanılmaz.
- Yeni özellik eklerken **kapsamı büyütme**: proje bilinçli olarak sadeleştirildi.

## GÖRSEL YASA — KORUNAN DÜZELTMELER (uçuş verisinden; silme)
- **Dikey nişan (tilt-farkında):** `ey_ref = NISAN·tan(TILT)/tan(VFOV_yarı)`.
  `DIKEY_NISAN=-0.25` negatiftir: hedefi merkezin ÜSTÜNDE tut → araç hedefin
  ALTINDA kalır, hedef gökyüzü arka planında (zemin clutter'ında tespit ölmez).
- **Ego-pitch telafisi (`EGO_PITCH_GAIN=0.4`):** ileri itki gövdeyi öne yatırır,
  gövdeye sabit kamera düşer, hedef görüntüde sahte YUKARI zıplar → yasa "tırman"
  sanıyordu. 1.0 aşırıydı (kalıcı yatıklığı da siliyordu, sürekli alçalış); 0.4
  uçuş verisinden seçildi.
- **Alçalma freni (`ALCAL_FREN`) + yaklaşma-ağırlıklı bypass (`yak`):** iki fren
  çarpımsal binince ileri itki eziliyordu (hedefe hiç yaklaşılamıyordu). Frenler
  yalnız istasyon bandında devrede; uzakta baypas.
- **Yumuşak geçiş (`HANDOFF_S=1.0`):** devir tikinde ileri itki tavana doyup tam
  lunge veriyordu (gövde yatar, hedef kadrajın üstünden kaçar). İleri itki ve
  dikey nişan 1 sn'de 0'dan açılır; yaw + dikey ortalama ilk tikten tam güçte.
- **Pervane maskesi (`detector.PROP_MASKE`):** avcının KENDİ pervanesi kadrajda
  sabit konumda "uçak" olarak algılanıyordu; merkezi maskede olan kutular seçim
  ÖNCESİ elenir.

## CANLI DOĞRULAMA BEKLEYEN
- **İŞARET DOĞRULAMASI (ilk uçuşta İLK İŞ):** yaw ters tepki verirse
  `gorsel_takip.Cfg.SIGN_YAW=-1`, dikey ters tepkiyse `SIGN_DIKEY=-1`.
- `ILERI` (yaklaşma hızı), `K_YAW`/`K_DIKEY` (merkezleme), `MERKEZ_FREN` (taşma),
  `HANDOFF_S` (0.6–1.5 s) canlı tune edilir.
- `K_BOYUT=0` → sabit ileri itkiyle hedefe kapanır (takip/vuruş). İstasyon tutmak
  (kilitlenme isterini doldurmak) gerekirse `K_BOYUT>0` yapılır.
