# Avcı Drone — GPS Takip + Görsel Takip

Teknofest **Drones of War** simülasyonunda (Unreal Engine oyunu) hedef Talon
İHA'sını otonom takip eden yer kontrol yazılımı. Sistem **iki fazlıdır**:

1. **GPS yaklaşma** — hedefin **bozuk GNSS** telemetrisi filtrelenip temizlenir,
   araç hedefe yönelir ve hedefi kadrajda tutarak yaklaşır.
2. **Görsel takip** — görsel temas kurulunca komut **yalnızca kameradan** türer
   (YOLO bbox → basit IBVS). Bu fazda GPS/GNSS güdüme **girmez**.

Başka faz, arayüz veya yardımcı katman yoktur.

---

## Klasör yapısı

```
control/            güdüm ve karar
  main.py             görev gözetmeni + giriş noktası (faz devir kapısı)
  gps_approach.py     GPSTakip — kalkış + bozuk GNSS ile yaklaşma
  gorsel_takip.py     GorselTakip — basit IBVS görsel güdüm yasası
  common.py           paylaşılan yardımcılar + KomutGonderici (tek komut çıkışı)
fusion/             sensör füzyonu / filtreleme
  gnss_filtre.py      GNSSFiltre — spike temizleme + hız kestirimi + gecikme telafisi
perception/         hedef tespit + takip
  camera.py           ekran yakalama → tespit → takip → detection_state
  detector.py         YOLO tespiti (models/best.pt) + pervane maskesi
  tracking.py         HybridSort (boxmot) kimlik sürekliliği
  detection_state.py  kamera thread'i ↔ güdüm döngüsü köprüsü
  models/best.pt      eğitilmiş model (task=detect, sınıf: talon)
sdk/                simülasyon I/O (resmi yarışma SDK'sı — DEĞİŞTİRİLMEZ)
scripts/start_game.sh   oyunu Wine ile başlatır (tek başlatma scripti)
```

Veri akışı tek yönlüdür:

```
oyun ekranı ──► perception/camera ──► detection_state ──┐
                                                        ├──► control/main ──► sdk ──► oyun
oyun telemetrisi (bozuk GNSS) ──► fusion/gnss_filtre ───┘        (gözetmen)
```

---

## Kurulum

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # torch'u CUDA'lı kurmak için pytorch.org
```

Yarışma paketindeki oyunu depo köküne **`Drones of War Teknofest/`** klasörü
olacak şekilde çıkartın (bu klasör repoya konmaz, `.gitignore`'dadır).

## Çalıştırma

```bash
./scripts/start_game.sh                # 1) oyunu başlat, PLAY moduna geç
python3 -m control.main                # 2) ayrı terminalde görevi başlat (ENTER)
```

`Ctrl+C` görevi durdurur ve motorları keser.

> **Oyun penceresi görünür/önde kalmalıdır.** Kamera hattı `mss` ile **ekranı**
> yakalar; oyun başka bir pencerenin arkasında kalırsa dedektöre masaüstü
> pikseli gider ve hedef "kaybolur". Kenarlıksız pencere modu en sağlıklısıdır.

### Ortam değişkenleri

| Değişken | Etki |
|---|---|
| `AVCI_BOLGE="left,top,w,h"` | Tüm ekran yerine yalnız bu dikdörtgeni yakala |
| `AVCI_DEBUG_PENCERE=1` | Dedektörün **gördüğü** kareyi kutularla ayrı pencerede göster |
| `AVCI_FP16=0` | FP16 inference'i kapat |

---

## Faz devir kapısı (GPS → görsel)

İki koşul **birlikte** sağlanmalıdır:

1. **Yakınlık** — GPS yatay mesafesi `control.main.Cfg.HANDOFF_RANGE` (40 m)
   altında; ya da hedef GNSS'i bayat (o zaman menzil zaten bilinemez).
2. **Görsel kilit** — ard arda `N_LOCK` (5) karede güdüme girebilecek kutu.

Kutu kapısı tek yerde tanımlıdır (`control.gorsel_takip.nisan_kutusu`) ve hem
gözetmen hem görsel faz **aynısını** kullanır. İki katmana ayrı eşik yazmak,
görsel fazın aynı karede reddettiği bir kutuyla devir yapılmasına ve fazın
sürekli sekmesine yol açar.

Görsel fazda tespit `LOST_S` (0.8 s) boyunca gelmezse GPS yaklaşmaya dönülür
ve yeniden kilitlenmeye çalışılır.

## Görsel güdüm yasası (basit IBVS)

Görüntüdeki **nişan noktasından** bbox merkezine bir çizgi çekilir; çizginin
açısı düzeltmenin yönünü, büyüklüğü sapmayı verir. Güdüm bu çizgiyi sıfıra
sürer:

```
yaw   = SIGN_YAW   · K_YAW   · ex          hedef sağda → sağa dön
thr   = SIGN_DIKEY · K_DIKEY · (−eyy)      hedef nişanın üstünde → tırman
pitch = ILERI · fren                       nişandayken tam ileri
roll  = 0                                  çerçeveleme yaw'ın işi
```

- **Dikey nişan** kamera tilt'inden (+25°) türer; negatif `DIKEY_NISAN` hedefi
  merkezin üstünde tutar → araç hedefin **altında** kalır, hedef gökyüzü arka
  planında olur (zemin clutter'ında tespit ölmez).
- **Ego-pitch telafisi**: ileri itki gövdeyi öne yatırır, gövdeye sabit kamera
  düşer ve hedef görüntüde sahte yukarı zıplar; dikey hata kendi IMU pitch'imizden
  arındırılır (kendi tutumumuz = ego-motion, hedef verisi değil).
- **Yumuşak geçiş**: devir anında ileri itki ve dikey nişan `HANDOFF_S` (1 s)
  boyunca 0'dan açılır — aksi halde ilk tikte tam lunge gövdeyi yatırıp hedefi
  kadrajın üstünden kaçırır.

Ayar sabitleri `control/gorsel_takip.py :: Cfg` içindedir; **canlı uçuşta tune
edilir.** İlk uçuşta yapılacak ilk iş **işaret doğrulaması**: yaw ters tepki
verirse `SIGN_YAW = -1`, dikey ters tepki verirse `SIGN_DIKEY = -1`.

## Bozuk GNSS zinciri

`sdk.drone_sdk.get_target_location()` bozuk (gürültü/offset/sıçrama/kesinti/
gecikme içerebilir) hedef konumunu verir. `fusion/gnss_filtre.py` bunu nedensel
olarak temizler: z-spike ve x/y-spike kapıları, son-N nokta lineer hız kestirimi
ve gecikme telafili lead. `control/gps_approach.py` bu temiz kestirimle yatay
standoff (hedefin gerisinde pace), irtifa PID'i ve burun-hedefe yaw üretir.

## Kurala uyum (görsel fazda GPS yasağı)

Görsel temas kurulduktan sonra hareket komutunu GPS ile üretmek diskalifiye
sebebidir. Kural **yapısal** olarak sağlanır: `GorselTakip.hesapla(det,
own_pitch_rad)` imzasında hedefe ait tek veri **bbox**tır — konum, hız ya da
GNSS kestirimi parametre olarak bile geçmez. `own_pitch_rad` kendi IMU
pitch'imizdir (ego-motion telafisi), hedef verisi değildir.
