"""
bbox_ibvs.py — SAF görüntü tabanlı görsel güdüm (IBVS), yalnız bbox.

YARIŞMA KURALI (üstün kısıt, bkz. UYGULANACAK.md D0): görsel temas varken
hedefin GPS'i güdümde KULLANILAMAZ — canlı GPS akışı yasak.

Bu modül iki girdiyle çalışır:
  1. Tespit kutusu (cx, cy, w, h, conf) — her kare, tek canlı kaynak.
  2. Drone'un KENDİ durumu (yaw, kendi hızı) — kendi sensörü, kural serbest.
  3. DONDURULMUŞ TAŞIYICI (ff_hiz): devir ANINDA, yani görsel temas kurulmadan
     ÖNCEKİ son GPS kestiriminden alınan hedef hız vektörü. Görsel faz boyunca
     BİR DAHA OKUNMAZ.
     ⚠ YAPISAL GARANTİ: bu bir SAYI ÜÇLÜSÜ olarak geçilir, callback değil —
     döngünün canlı GPS'e erişimi FİZİKSEL OLARAK YOKTUR. Kural ihlali
     "yapmamayı seçmek"le değil, yapamamakla güvence altında.

Kontrol yasası — SAF TAKİP (pure pursuit) + PI HIZ:
  YAW     : yatay piksel hatası (cx − CX) → burun hedefe döner.
  DİKEY   : dikey piksel hatası (cy − CY_NISAN) → tırman/alçal.
  YATAY   : hız DAİMA LOS (burun) YÖNÜNDE; büyüklüğü kutu boyutu hatasına
            PI kontrol:  v = I + K_P·(REF − boyut),  İ += K_I·(REF − boyut)·dt
            İntegral, hedefin hızını GÖRÜNTÜDEN öğrenir — GPS gerekmez.
            ff_hiz yalnız İNTEGRALİN BAŞLANGIÇ DEĞERİ (sıcak start).

⚠ 2026-08-08 İKİ UÇUŞ DERSİ (ikisi de bu tasarımı zorunlu kıldı):

1) Saf kutu-boyutu (P-only, taşıyıcısız) 12 m'de 8 m/s üretiyordu; hedef
   15 m/s → drone geride kaldı, faz 3.5 s'de koptu. P-only'nin kalıcı hata
   sorunu: denge için hız hedefin hızına EŞİT olmalı ama P-only bunu ancak
   sıfır olmayan hatayla üretir.

2) DONDURULMUŞ NED TAŞIYICI + LOS kapanması: faz 160 s sürdü, mesafe medyanı
   7.2 m çıktı — ama GEOMETRİ BOZULDU. Ölçüldü (log 184748, aspect açısı):
       devir anı  7° (tam kuyrukta) → 72 s: 55° → 180 s: 70° → 216 s: kayıp
       mesafe 8.7 → 5.3 → 12.2 → 66.6 m
   Kök neden: taşıyıcı NED'de SABİT. Hedef 0.16°/s gibi ÇOK yavaş dönse bile
   168 s'de 27° birikiyor; hız uyuşmazlığı 2·V·sin(Δ/2) ≈ 6 m/s yana kayma
   üretiyor. LOS'taki 3.8 m/s kapanma bunu yenemiyor → drone yana savruluyor,
   hedefi yandan görüyor, sonra kaybediyor.
   DERS: taşıyıcı NED'de dondurulamaz. Yön DAİMA LOS olmalı (saf takip);
   böylece hedef döndükçe hız vektörü kendiliğinden döner ve kuyruk
   geometrisi korunur. Dondurulmuş GPS ancak İNTEGRAL BAŞLANGICI olarak
   kullanılabilir — o da sadece ilk saniyelerin gecikmesini kesmek için.

Arayüz (supervisor.run_hybrid ile uyumlu):
  run_bbox_ibvs(conn, get_iris, wait_pose, stop_event, cfg, kayip_kare_esik,
                ff_hiz=(vx,vy,vz))
    get_iris() -> {..., "yaw": rad, "vx","vy","vz": m/s}  (drone KENDİ durumu)
    wait_pose(son_seq, timeout) -> {"seq","pose",...}  (pose = bbox kaydı | None)
  Dönüş: 'durduruldu' (stop_event) | 'kayip' (kayip_kare_esik ardışık kutusuz).
"""

import csv
import math
import os
import time

from vision import geometry as geo
from control.guidance.guidance_core import Cfg as GeoCfg
# ── TAM DURUM KESTIRIMI KUTUPHANESI (bkz. Cfg.KESTIRIM) ────────────────────
# ⚠ bbox_geometri SAF bir kutuphanedir: yalniz `math` import eder, env/zaman/IO
#   okumaz (tests/test_bbox_geometri.py bunu AST ile kilitler). Bu yuzden
#   import etmek yasanin davranisina TEK BASINA hicbir sey yapmaz; fonksiyonlari
#   YALNIZ `AVCI_IBVS_KESTIRIM=1` kapisinin ardindaki gozlem blogu cagirir.
#   (Modulun kendi docstring'i bu bagi ongoruyor: "canli yasaya ancak env
#    kapili TEK bir blokla baglanir".)
from control.guidance import bbox_geometri as BG
from control.guidance.common import (
    clamp, normalize_angle, send_velocity, limit_acceleration,
    limit_acceleration_split,
)
from control.guidance.kurtarma import Kurtarma
# GERCEK "5 s KESINTISIZ kilit" kapisi + denetim kaydi (2026-08-17).
# Varsayilan AVCI_KILIT_S=0 -> kapi KAPALI, davranis bit-ayni.
from control.guidance.kesintisiz_kilit import (
    KesintisizKilit, KilitKapiCfg, denetim as kilit_denetim)


def _env_f(name, default):
    return float(os.environ.get(name, default))


class Cfg:
    LOOP_HZ = 20.0

    # ── KADRAJ NİŞAN NOKTASI ──
    # ⚠ GEOMETRİ (2026-08-08 uçuş dersi): kamera gövdeye 25° YUKARI tilt'li.
    # SEVİYE (co-altitude) bir hedef kadrajda merkezde DEĞİL, AŞAĞIDA görünür:
    #     cy_seviye = CY + FY·tan(25°) = 240 + 166.6·0.466 ≈ 318 px
    # İlk sürümde nişan 210 (üst) alınmıştı — bu "hedefin ~8 m ALTINA dal"
    # demekti: drone vz'yi tavana (+4) yapıştırıp sürekli alçaldı, hedef
    # kadrajın altından (cy→390→dışarı) kaçtı, faz 3.1 s'de koptu.
    # DÜZELTME: nişanı seviye-hedef konumunun hafif ÜSTÜNE al (drone hedefin
    # az altında kalsın — gökyüzü arka planı + terminal pop-up). tan(20°) ile
    # ~10° altı: cy ≈ 240 + FY·tan(20°) ≈ 300.
    _CY_SEVIYE = geo.CY + geo.FY * math.tan(math.radians(20.0))
    CY_NISAN = _env_f("AVCI_IBVS_CY", round(_CY_SEVIYE, 0))  # ≈300 px
    CX_NISAN = geo.CX                           # px; yatay merkez (320)

    # ── YAW ──
    # eps_yaw = atan((cx − CX)/FX); komut = iris_yaw + K_YAW·eps. K_YAW=1 tam
    # düzeltme (ArduPilot kendi yaw hızıyla slew eder). <1 yumuşatır.
    K_YAW = _env_f("AVCI_IBVS_KYAW", 1.0)
    YAW_ESIK = math.radians(1.0)   # bu açının altında yaw komutu güncellenmez

    # ── YAW HIZ SINIRI (2026-08-09, TAKLANIN KÖK NEDENİ) ──
    # Yaw komutu her kare "iris_yaw + eps_yaw" olarak YENİDEN kuruluyordu;
    # hız sınırı YOKTU. Hedefin yanından geçerken (terminal sonrası fly-past)
    # kutu kadrajı hızla tarıyor ve komut çılgınlaşıyor. ÖLÇÜLDÜ (5 görsel faz):
    #     medyan 12-38 °/s   p95 238-412 °/s   MAX 876 °/s
    # Aracın yapabildiği ~120 °/s. 876 °/s isteyince yaw doyuyor, motorlar
    # yaw torkuna gidiyor, roll/pitch yetkisi kalmıyor → TAKLA.
    # Taklanın maliyeti ölçüldü: takla yaşamayan koşular 2/2 vurdu, takla
    # yaşayanlar 1/3 — her kurtarma 13+ s sürüyor ve hedef kaçıyor.
    #
    # ÇÖZÜM: gps_guidance'ta zaten olan slew sınırı buraya da konur.
    # ⚠ NORMAL TAKİBİ KISITLAMAZ: medyan 12-38 °/s, sınır 120 °/s — yalnız
    # p95 üstü (fly-past) anlarda bağlar.
    # ⚠ HIZ YÖNÜ ETKİLENMEZ: hız hedefin GERÇEK LOS'u boyunca gider; yalnız
    # BURUN yavaş döner. Multirotor yan uçabilir, nişan bozulmaz.
    # ⚠ Ö7 ÖLÇÜMÜ (2026-08-10): bu sınır kaçamak senaryosunda BAĞLIYOR.
    # "normal takip medyanı 12-38 °/s, sınır bağlamaz" gerekçesiyle konmuştu;
    # 8 m'lik yanal kırılmada ölçülen medyan 53-100 °/s ve karelerin
    # %23-47'sinde komut 120 °/s tavanına yapışıyor. Doymuş bir hız
    # sınırlayıcı kontrol döngüsüne FAZ GECİKMESİ katar — salınımın klasik
    # sebebi. Kullanıcı gözlemi: "karşı tarafa daha çok gidiyor ve salınıyor."
    # Panelden canlı denenebilsin diye derece cinsinden tutulur.
    YAW_RATE_MAX_DEG = _env_f("AVCI_IBVS_YAWRATE", 120.0)   # °/s

    # ── DİKEY ──
    # eps_elev = atan((cy − CY_NISAN)/FY); v_z = K_VZ · V_NOM · eps_elev.
    # cy büyük (hedef kadrajda AŞAĞIDA) → hedef boresight'ın altında → ALÇAL
    # (vz>0, NED down+). Nominal hızla ölçekli: hızlı giderken dik açı daha çok
    # dikey hız ister (irtifayı korumak için).
    # K_VZ 1.2 → 0.5, VZ_MAX 4 → 3 (2026-08-08): ilk sürüm dikey hızı çok
    # agresifti (10° hata → 2.5 m/s) ve tavana yapışıp salındı. Nişan doğru
    # yere gelince (≈300) hata küçük kalır; yumuşak kazanç yeter.
    # ⚠ 0.9 DENENDI VE ALINMADI (2026-08-17 ucus A/B, arac/recete_gecis.json):
    #   G4 (ufuk+hiz+K_VZ0.9): |dz| 0.84 -> 0.69 m (dikey DAHA IYI) ama
    #   CPA medyani 2.84 -> 3.64 m ve <2 m gecis %41 -> %24 (YATAY DAHA KOTU).
    #   Yani artan dikey yetki 3B ivme butcesinden YATAYI yiyor. Dikey kazanc
    #   yatay kaybini karsilamiyor -> 0.5'te kalir.
    #   ⚠ AYRICA G5 (K_VZ=0.9 TEK BASINA, ufuk kapisi KAPALI) 5/5 olcude
    #   kotulesti: dikey yetki, denge noktasi yanlisken ZARARLIDIR.
    # ⭐ 0.5 -> 0.8 (2026-08-18, UCUSTA DOGRULANDI, serpistirilmis 4 kol)
    # Olcum (`arac/recete_kazanc.json`, kol basina ~14 dk):
    #     kol          yaklasma  CPA   <1.5m  <1m  |dz|@CPA  vurus
    #     taban_a           46   2.73   %22   %4     1.03      3
    #     taban_b           46   2.86   %15   %7     0.89      2
    #     kvz08_a           36   2.35   %25   %6     0.46      4
    #     kvz08_b           30   2.80   %30   %17    0.78      5
    # Hedef buyukluk |dz|@CPA: taban ort. 0.96 -> aday ort. 0.62 (-0.34).
    # ⚠ Gurultu tabani (10 taban cifti): medyan 0.144, p90 0.339
    #   -> fark p90'IN OTESINDE. Iki tekrar da iki tabandan iyi.
    # Toplam CPA anlamli oynamadi (2.58 vs 2.80, gurultu icinde); kazanc
    # DIKEY eksende. Vurus 4/5 vs 3/2 (ayni yon ama Poisson gurultusu).
    # ⚠ BAGIMSIZ IKINCI KANIT: 2026-08-18 gecesi K_VZ=0.9 tek olumlu kol
    #   cikmisti (kapatma %69 vs %60.5, 8 vurus). Iki ayri kampanya.
    # ⚠ NEDEN ISE YARIYOR (olculdu): asim CPA'dan +0.6..1.3 s SONRA oluyor,
    #   yani onemli olan asimi onlemek DEGIL, CPA'ya KADAR hatayi kapatmak.
    #   Kazanc CPA'ya varisi 2.45-2.92 s'den 2.20 s'ye cekiyor.
    #   Sonumleme (KVZD_SEYIR) asimi yariya indirdi ama |dz|@CPA'yi
    #   KOTULESTIRDI (1.03) -> varsayilan KAPALI kaldi.
    K_VZ = _env_f("AVCI_IBVS_KVZ", 0.8)
    # ⚠ 2026-08-15 OLCULDU: arac 33.7 m/s tirmanabiliyor -> bu clamp
    # gorsel fazda dikey yetkiyi 11.2 KAT kisiyor. Ucun en dar tavani bu.
    VZ_MAX = _env_f("AVCI_VZ_MAX_GORSEL", 3.0)   # m/s; dikey hiz tavani

    # ══ SEYIR DIKEY SONUMLEMESI (2026-08-18) ═════════════════════════════
    # ⚠ BESINCI "yazilmis ama baglanmamis" vaka. Terminal dalinda turev
    # sonumlemesi VAR (K_VZ_D, bkz. :1924) ama SEYIR/TUTUS dalinda YOK --
    # orada yasa saf oransaldir:  vz = K_VZ * V_NOM * eps_elev.
    #
    # NEDEN ONEMLI: devir menzili medyan 12.7 m (n=2307 devir), terminal
    # mandali bundan cok daha yakinda kalkiyor. Yani GPS->GORSEL devrinden
    # sonraki butun gecici davranis SONUMLEMESIZ dalda yasaniyor. Kullanici
    # tarifi birebir buydu: "faza gectiginde dikeyde sorunlar oluyor".
    #
    # OLCULDU (2026-08-18, 2306 devir, G3 sonrasi, 10 Hz iz kaydi):
    #     devir aninda dz            -1.46 m  (gecislerin %99'unda ALTTAYIZ)
    #     +2.5..3.0 s'de dz          +0.41 m  -> ASIM
    #     dogru irtifadan GECIP giden gecis        %69
    #     hatanin 1 m altina inmesi                ~1.5 s (faz omru ~5 s)
    # ⚠ Devir anindaki -1.46 m bir ARIZA DEGIL: GPS istasyonunun 1.553 m alt
    #   ofseti. Olculdu (kareler.csv, menzil bandi sabit): hedefin 1-2 m
    #   ALTINDA tespit %90-95, ES IRTIFADA %68-74, USTTE %22-70. Ofset
    #   hedefi GOKYUZU fonunda tutuyor ve devir olcutu 10 ardisik kare
    #   istiyor -> ofseti erken eritmek devrin KENDISINI bozar.
    #   Bu yuzden cozum ofseti kaldirmak DEGIL, gecisi SONUMLEMEK.
    #
    # SONUMLEME ORANI, asimdan geri hesap:
    #     Mp = 0.41/1.46 = 0.28 ;  Mp = exp(-pi*z/sqrt(1-z^2))
    #     -> z ~= 0.375   (az sonumlu; ideal ~0.7 -> asim ~%5)
    # Saf oransal denetleyici + tasima gecikmesi tam olarak bunu uretir.
    #
    # DUZELTME: terminaldeki AYNI terim, ayni yapi:
    #     vz = vz_nisan + KVZD_SEYIR * (vz_nisan - vz_gercek)
    # Girdi aracin KENDI dikey hizi (iris.vz); canli GPS yok, kural serbest.
    # ⚠ Terim yalnizca sonumleme DEGIL: acilimi (1+Kd)*vz_nisan - Kd*vz_ger,
    #   yani oransal kazanci da (1+Kd) kati buyutur. Bu yuzden deneyde
    #   "saf kazanc" olumsuz kontrolu SART (K_VZ'yi 1+Kd kati yapip
    #   sonumlemeyi kapali birakan kol) -- yoksa etkinin hangisinden
    #   geldigi ayirt edilemez.
    # 0 = KAPALI (varsayilan) -> bit-ayni eski davranis.
    KVZD_SEYIR = _env_f("AVCI_IBVS_KVZD_SEYIR", 0.0)
    V_NOM = 12.0                   # m/s; dikey ölçekleme için nominal ileri hız

    # ── HIZ: PI kontrol, kutu boyutu hatası üzerinden (menzil vekili) ──
    # boyut = sqrt(w·h). Büyük kutu = yakın. hata = REF − boyut (pozitif = uzak).
    #     v_los = I + K_FWD·hata      (LOS yönünde uygulanır — saf takip)
    #     I    += K_I·hata·dt         (hedefin hızını GÖRÜNTÜDEN öğrenir)
    # İntegralin işi tam da P-only'nin yapamadığı şey: denge hızını (hedefin
    # LOS üzerindeki hız bileşeni) kalıcı hatasız üretmek. Hedef hızlanır,
    # yavaşlar ya da DÖNERSE integral kendini yeniden ayarlar — GPS'siz.
    #
    # REF ölçümden (2026-08-08): 12 m'de kutu ≈ 12-14 px → boyut ≈ 1/menzil.
    # 6-7 m tutuş için REF ≈ 25 px.
    BOYUT_REF = _env_f("AVCI_IBVS_REF", 25.0)   # px; sqrt(w·h) denge boyutu
    K_FWD = _env_f("AVCI_IBVS_KFWD", 0.35)      # (m/s)/px; P kazancı
    K_I = _env_f("AVCI_IBVS_KI", 0.04)          # (m/s)/(px·s); İ kazancı
    I_MIN, I_MAX = 0.0, 24.0       # m/s; integral penceresi (windup koruması)

    # V_MIN 0 (2026-08-08, kullanıcı kararı): GERİ ÇEKİLME YOK. Eski −2 m/s
    # "fren"i, kutu REF'i aşınca drone'u geri itiyordu — kullanıcı düz uçuş
    # koşusunda bunu görüp "fren olmasa vururduk" dedi. Görev vuruş; tutuş
    # mesafesinde beklemek değil.
    V_MIN = 0.0                    # m/s; asla geri gitme
    # 18 → 24 (2026-08-08, kullanıcı kararı): görsel faz KUYRUK takibi yapıyor,
    # GPS fazındaki "hızlanınca çember büyür" tuzağı burada YOK. 18 tavanında
    # komut %83 doygundu → hedefe (15-16 m/s) pay kalmıyordu, mesafe 30 m'de
    # donuyordu. GPS fazının V_MAX'ı 18'de KALIR (orada çember riski gerçek).
    V_TOPLAM_MAX = _env_f("AVCI_IBVS_VMAX", 24.0)   # m/s; yatay hız tavanı

    # ── TERMİNAL HÜCUM (mandal) ──
    # Kutu bu boyutu aşınca (≈ birkaç metre) kontrol "tut" modundan çıkar ve
    # LOS boyunca TAM hızla taahhüt eder; bir kez girilince mandal kilitli
    # kalır (kutu titrese de geri dönmez). Kutu kaybolursa son komut sürer —
    # kör hücum: terminalde hedef kadrajdan çıkabilir, çarpışma tamamlanmalı.
    # 45 → 25 px (2026-08-08, kullanıcı kararı — "1. madde"): 45 px ≈ 3.6 m
    # demekti; 24 m/s'lik hücumla o mesafe 0.15 s'de kapanıyor ve kamera 30 Hz'de
    # yalnız 4-5 kare görüyordu — hedefin son anki kaçışını düzeltecek zaman yok,
    # 7 hücumun 7'si ıska (en yakın 1.5 m). 25 px ≈ 6.4 m'den taahhüt → düzeltmeye
    # ~20 kare kalır. Ölçüm: kutu ≈ 160/menzil (12 m'de 12-14 px, uçuş logu).
    # 25, BOYUT_REF ile aynı: "tutuş mesafesine varınca hücuma geç" demek.
    TERMINAL_BOYUT = _env_f("AVCI_IBVS_TERM", 25.0)  # px; ≈6.4 m
    # ⚠ KÖR HÜCUM SÜRE SINIRI (2026-08-08, pahalı hata): ilk sürümde kör
    # hücumun süresi YOKTU. Drone hedefi ıskalayıp geçti, kutu kayboldu ve
    # son komut 260 s boyunca basıldı — araç 1032 m uzağa düz uçtu, faz hiç
    # 'kayip' dönmedi. Kör hücum çarpışmayı TAMAMLAMAK içindir; bu süre
    # içinde temas gelmezse ıska sayılır ve GPS fazına dönülür.
    TERMINAL_SURE = _env_f("AVCI_IBVS_TERM_SURE", 2.0)   # s

    # ── NİŞAN KAPISI: KÖTÜ NİŞANLA KÖR TAAHHÜT ETME (2026-08-15) ──────────
    # ÖLÇÜLDÜ (4 angajman, geometri kapısı + erken lead açıkken): terminal
    # mandalı YALNIZ kutu boyutuna bakıyordu ve tam da nişanın EN KÖTÜ olduğu
    # anda — hedef kadraj kenarındayken — kapanıyordu:
    #     menzil 3.0 m, eps_yaw -54°  ->  yanal sapma  4.1 m
    #     menzil 5.1 m, eps_yaw +56°  ->  yanal sapma  7.7 m
    #     menzil 3.1 m, eps_yaw +56°  ->  yanal sapma  4.7 m
    #     menzil 7.1 m, eps_yaw +55°  ->  yanal sapma 10.1 m
    # Talon'un çarpışma gövdesi ~0.8 m. 4-10 m yanal sapmayla kör uçmak
    # matematiksel olarak ıskadır; üstelik 2 s boyunca araç hedeften UZAKLAŞA
    # uçuyor ve yeniden angaje olmak için zaman kaybediyor.
    #
    # Menzil kaynağı kodun kendi kalibrasyonu: kutu ≈ 160/menzil
    # (bkz. TERMINAL_BOYUT notu, "12 m'de 12-14 px, uçuş logu").
    #     yanal_sapma = (160/boyut) · tan(eps_yaw)
    # 0 vermek kapıyı KAPATIR (eski davranış, bit-aynı).
    TERM_NISAN_MAX_M = _env_f("AVCI_IBVS_TERM_NISAN", 2.0)  # m

    # ── TERMİNAL NİŞANI: KESİŞİM + LEAD (2026-08-08, kullanıcı "2. madde") ──
    #
    # ÖLÇÜM (term25 uçuşu, en yakın anlar; ıska hedef çerçevesinde ayrıştırıldı):
    #     mesafe 0.9 m → yanal +0.5, DİKEY +0.5
    #     mesafe 0.8 m → yanal  0.0, DİKEY −0.2
    #     mesafe 1.9 m → yanal −0.1, DİKEY −0.8
    # Talon'un çarpışma gövdesi KANATLAR DAHİL (fuselage+left_wing+right_wing),
    # yani 0.8 m'de değmeliydi. Iskanın baskın bileşeni DİKEY.
    #
    # KÖK NEDEN: terminalde bile dikey kanal "TUTUŞ" yasasıydı — hedefi
    # CY_NISAN'da (≈5° yukarıda) tutmaya çalışıyor, yani ALTINDAN geçiyoruz.
    # Kesişim için hız vektörünün hedefe DOĞRU bakması gerekir, hedefi sabit
    # bir açıda tutması değil.
    #
    # ÇÖZÜM (yalnız TERMİNALDE; tutuş davranışı değişmez):
    #   1) KESİŞİM: vz = −v_los·tan(elev_hedef). elev, pikselden ve gövde
    #      pitch'inden çıkar (kamera 25° yukarı tilt'li).
    #   2) LEAD: nişan, ATALET çerçevesindeki LOS DÖNÜŞ HIZIYLA öne alınır
    #      (klasik lead pursuit / PN mantığı):
    #          los_azimut = iris_yaw + eps_yaw      → türevi = LOS hızı
    #          nişan = los + LEAD_SURE · los_hızı
    #      ⚠ Piksel hızı DEĞİL atalet LOS hızı kullanılır: yaw kontrolcüsü
    #      kutuyu merkeze çektiği için piksel hızı kendi düzeltmemizi de
    #      içerir; ona lead vermek düzeltmeyle kavga etmek olurdu.
    #   Düz kuyruk takibinde LOS hızı ≈ 0 → lead ≈ 0, yalnız kesişim kalır.
    # ── TERMİNAL HÜCUM HIZI (2026-08-08, kullanıcı kararı) ──
    # Yaklaşmada tavan 24 m/s KALIR (hedefe yetişmek için gerekli), yalnız
    # HÜCUM hızı 18'e düşer. Gerekçe: 24 m/s'de hedefin yanından 0.06 s'de
    # geçiyoruz — kamera 30 Hz'de son metrede 2 kare görüyor ve temas
    # penceresinden çok hızlı geçiliyor. 18 m/s'de kapanma 3.5 m/s (hedef
    # 14.5) → hem düzeltmeye daha çok kare, hem pencerede daha uzun süre.
    # Hedef 14.5 m/s olduğu için 18 hâlâ yeterli pay bırakır.
    # ⚠⚠ 2026-08-19: BU GEREKCENIN DAYANDIGI HEDEF HIZI ARTIK GECERSIZ.
    #   Yukaridaki hesap "hedef 14.5 m/s" varsayiyor ve 18 ile 3.5 m/s
    #   kapanma payi biraktigini soyluyor. BUGUN OLCULEN hedef hizi:
    #       medyan 18.0 m/s  (3943 ornek, yarisma modu, donmus satirlar atildi)
    #   Yani hucum hizi hedefin hiziyla ESIT -> terminalde kapanma payi SIFIR.
    #   Canli izlemede gorulen desen birebir bu: menzil 3-4 m'ye iniyor,
    #   sonra dr/dt POZITIFE donuyor ve arac geri dusuyor (son 3 m kapanmiyor).
    #   Tasarimin ORIJINAL NIYETI (3.5 m/s pay) korunacaksa deger
    #   18.0 + 3.5 = 21.5 olmali (V_TOPLAM_MAX 24 icinde kaliyor).
    #   ⚠ GENELLEME NOTU: sabit sayi senaryoya bagimlidir. Kalici cozum,
    #     hucum hizini yasanin GORSEL hiz kestirimi `hiz_I` uzerine sabit
    #     PAY eklemektir (hedef GPS'i kullanilamaz -- yarisma kurali).
    V_TERMINAL = _env_f("AVCI_IBVS_VTERM", 18.0)   # m/s; hücum hızı
    # Dikey bütçe yetmediğinde yatay hız buraya kadar kısılabilir (bkz. komut()).
    V_TERM_MIN = _env_f("AVCI_IBVS_VTERM_MIN", 10.0)   # m/s; hücum hız tabanı

    # ── TERMINAL KAPANMA PAYI (2026-08-19, GENELLESTIRME) ────────────────
    # Sabit V_TERMINAL senaryoya bagimlidir: gerekcesi "hedef 14.5 m/s"
    # varsayimiyla yazilmis, bugun olculen GERCEK hedef hizi 17.93 m/s
    # (debug.target_real turevi, n=353, bagimsiz olcum) -> pay SIFIR.
    # Farkli senaryoda hedef 25 m/s olsa sabit 18 yine yetmezdi.
    #
    # `hiz_I` yasanin KENDI gorsel hiz kestirimidir (kutu boyutu hatasi
    # uzerinden integral; hedef GPS'i KULLANMAZ -- yarisma kuralina uygun).
    # Bu deger hedefin hizina yakinsar. Hucum hizini onun UZERINE sabit pay
    # olarak tanimlamak, hedef ne kadar hizli olursa olsun kapanma birakir.
    #
    #   v_los = clamp(max(V_TERMINAL, hiz_I + TERM_PAY), V_TERM_MIN, V_TOPLAM_MAX)
    #
    # ⚠ ASLA V_TERMINAL'in ALTINA inmez -> mevcut davranistan kotu olamaz.
    # 0 = KAPALI (eski davranis, bit-ayni).
    # ⚠ MEKANIZMA KAPISI: acikken `v_los` terminal karelerde V_TERMINAL'den
    #   BUYUK olmali; hep esitse pay devreye girmemistir.
    TERM_PAY = _env_f("AVCI_IBVS_TERM_PAY", 0.0)   # m/s; 0 = kapali

    # ── BURUN HIZ TAVANI (2026-08-19, OLCUMDEN) ──────────────────────────
    # GPS yasasinda yaw tavani vardi (YAW_RATE_MAX); GORSEL yasada YOKTU:
    # `yaw_cmd = iris_yaw + K_YAW*eps_yaw - sonum + lead_az` dogrudan
    # yaziliyor. Olculdu (canli, faza gore |w|>60 °/s orani):
    #     GPS %13.2  ·  VISUAL %20.1     <- savrulma en cok GORSEL fazda
    # GPS tarafina tavan konunca |w| medyani 13 -> 1 °/s, p90 87 -> 56
    # dustu ama MAKS hala 164 °/s kaldi -- artigi bu daldan geliyor.
    # Yaw doyunca motorlarin roll/pitch yetkisi azalir; olculdu: savrulurken
    # hiz 22.1 -> 16.3 m/s (kullanicinin gordugu "sacma sapan durdurmalar").
    # 0 = tavan YOK (eski davranis).
    # ⚠ DENENDI ve KAPATILDI (canli, 220 s): 90 °/s tavanla
    #     yavas zaman (<5 m/s)  %1.3 -> %8.4
    #     yaklasma sayisi        11  -> 6
    #   ve savrulma AZALMADI (|w| maks 175 °/s ayni kaldi).
    # ⭐ BUNUN OGRETTIGI: savrulma iki yasanin YAW KOMUTUNDAN gelmiyor.
    #   Oyun "ANGL AIR" modunda ucuyor; burun HIZ KOMUTUNUN YONUNU takip
    #   ediyor. Dolayisiyla cozum yaw'i kismak degil, KOMUT EDILEN HIZ
    #   VEKTORUNUN yon degisimini sinirlamak olmali (ivme sinirlayici
    #   `limit_acceleration_split` bu isin dogru yeri).
    # 0 = tavan YOK (varsayilan, eski davranis).
    YAW_TAVAN_DPS = _env_f("AVCI_IBVS_YAW_TAVAN", 0.0)   # °/s

    # ⚠ LEAD MENZİLLE SÖNER (2026-08-09, kullanıcı gözlemi: "çarpacakken
    # birden yukarı itki verip kaçırıyoruz").
    # SORUN: lead = LOS_hızı × sabit süre. Ama LOS dönüş hızı menzil→0 iken
    # PATLAR (1 m'de küçük bir göreli hareket bile devasa açısal hız üretir).
    # Sabit süreyle çarpılınca nişan yukarı savruluyor, drone hedefin ÜSTÜNE
    # çıkıyor, sonra dalmak zorunda kalıyor ve ıskalıyor.
    # Ölçüldü (3 uçuşun son terminal kareleri): dikey hata +13° → +45°
    # büyüyor, yatay hız 10 m/s tabanına yapışıyor, hedef 45° ALTTA kalıyor.
    # ÇÖZÜM: lead, kalan süreyle (≈menzille) ölçeklenir — güdüm literatüründe
    # lead daima t_go ile çarpılır. Menzil vekili kutu boyutu olduğu için
    # ölçek = BOYUT_REF/boyut: uzakta 1.0, temas anında ~0.2.
    LEAD_SURE = _env_f("AVCI_IBVS_LEAD", 0.4)    # s; uzaktaki lead süresi
    LEAD_SONUM = _env_f("AVCI_IBVS_LEAD_SON", 1.0) >= 0.5  # 0 = eski (sabit) yol
    LEAD_EMA = 0.25                              # LOS hızı yumuşatması

    # ── ORANSAL SEYRÜSEFER (PN) — 2026-08-16, simülatörde ölçüldü ──────────
    # SORUN: saf takip (hız yönü = LOS) DÖNEN bir hedefe karşı sıfır ıskaya
    # yakınsamaz. Hedef 20.1 °/s dönüyor; biz anlık konuma burun tutunca
    # sürekli geriden geliyoruz. Ölçüm (510 angajman, ölçülmüş tesis):
    #     saf takip : medyan ıska 3.7 m, 35/510 vuruş
    #     PN        : medyan ıska 0.15 m, 370/510 vuruş
    # ÇÖZÜM: hız yönünü LOS'a EŞİTLEME, LOS'un DÖNÜŞ HIZININ N katıyla
    # DÖNDÜR:  psi_v ← psi_v + N·λ̇·dt.  (Hız komutlu araçta PN'in tam hâli;
    # klasik a = N·Vc·λ̇ ile eşdeğer, a = V·ψ̇_v olduğundan.)
    # ⚠ N SEÇİMİ: 6×6 tarama yapıldı; N 1.4-1.6 × pencere 0.10-0.30 s
    # yaylasında 34-40/40. N≤1.2'de UÇURUM var (yakınsamıyor), N≥3'te
    # ıraksıyor. 1.6 yaylanın MERKEZİ — tepe noktası değil, bilerek.
    # ── λ̇ ICIN YAW ZAMAN HIZALAMASI (2026-08-16, OLCULDU) ────────────────
    # SORUN: los_az = iris_yaw(SIMDI) + piksel_acisi(D saniye ONCE).
    # Dedektor olculdu: det_ms p50 29.7, p95 44.7 ms (+ yakalama gecikmesi).
    #     los_az_olculen = LOS(t-D) + yaw_hizi*D
    #     turevi         = lam_dot  + yaw_IVMESI*D
    # Yani arac sert donerken dogrudan SAHTE LOS hizi enjekte oluyor.
    # OLCULDU (36/36 angajman): yasanin lam'i truth'un 7.1 KATI; faz basinda
    # LOS kestirimi truth ile +8.3° uyumlu, faz sonunda +59.2° kaciyor.
    # DUZELTME: piksel acisini, karenin cekildigi ana ait yaw ile esle.
    # ⚠ YALNIZ λ̇ YOLUNU etkiler. Komut yolu (yaw_cmd, hiz_yonu) SIMDIKI
    # yaw'i kullanmaya devam eder — komut simdi veriliyor.
    # 0 = kapali (eski davranis).
    YAW_HIZALA_S = _env_f("AVCI_IBVS_YAW_HIZALA", 0.045)

    # ══ KOMUT YOLU ZAMAN HIZALAMASI — Y2 (2026-08-17, OLCULDU) ════════════
    # ⛔ YUKARIDAKI YAW_HIZALA_S BU SORUNU COZMEZ. Kendi notu soyluyor:
    #    "YALNIZ λ̇ YOLUNU etkiler. Komut yolu SIMDIKI yaw'i kullanmaya
    #    devam eder." Iste bu yuzden duzeltme YARIM BAGLIYDI.
    #
    # SORUN (tek cumle): kutu t−D'de cekiliyor, `eps` O ANKI govdeye gore;
    # yasa mutlak yonu `iris_yaw(SIMDI) + eps` ile kuruyor -> komut tam
    #     dψ = yaw(t) − yaw(t−D)
    # kadar sapiyor. Bu bir GEOMETRI hatasi degil, ZAMAN hatasidir.
    #
    # OLCULDU (sim/yaw_menzil.py --yaw; n=58.668 gercek tespitli kare,
    # 393 log, hepsi AYNA SONRASI, truth = get_debug_truth):
    #     |dψ| medyan 4.36° | p90 13.71° | p95 18.32° | maks 33.7°
    #     dψ ≈ 0.2071 · yaw_hizi   (R² = 0.968)   <- carpani VERI verdi
    #   yatay |hata| medyani:
    #     K=0.00 (bugunku)                     4.45°   p90 16.86
    #     K=0.20                               1.74°   p90  5.68   ← −61%
    #     K=0.25                               1.85°   p90  5.56
    #     IDEAL dψ cikarilmis (ulasilamaz)     1.58°   p90  4.96
    #   ⇒ EMA'li yaw_hizi, ideal telafinin %93'unu yakaliyor.
    #   DONUS HIZINA GORE (K=0.20):
    #     |ω|  0-5 °/s : 0.95 -> 1.04  (+10% KOTU — EMA gurultusu)
    #     |ω|  5-15    : 2.19 -> 1.34  (−39%)
    #     |ω| 15-30    : 4.39 -> 1.86  (−58%)
    #     |ω| 30+      : 11.37 -> 2.48 (−78%)
    #     TERMINAL (kutu>=25 px, n=5916): 12.79 -> 3.65° (−71%)
    #
    # ⚠⚠ SIRA ZORUNLU — ROLL TELAFISI BUNDAN SONRA GELIR:
    #     hizalamasiz + roll telafisi : 4.45 -> 5.45°  (DAHA KOTU)
    #     K=0.20     + roll telafisi  : 1.74 -> 1.29°  (DAHA IYI)
    #   Yani ROLL_TELAFI'nin isareti bu kapiya BAGLI. Once hizalama.
    #
    # ⚠ NEREYE UYGULANIR: govde açisini ATALET yonune ceviren HER YERE --
    #   yaw_cmd (BURUN_LOS dali), PN tabani ve DPP'nin `_los_kert`'i.
    #   Tek kavram, tek kapi. YARIM baglamak (yalniz yaw_cmd) tam da
    #   YAW_HIZALA_S'in dustugu hataya geri donmektir.
    #   ⛔ `hiz_yonu`nun saf-takip dalina DOKUNULMAZ: orada zaten
    #      `− sonum` (SONUM_T=0.30) var, ayni telafinin kaba hali. Iki kez
    #      uygulanmasin. (DPP/PN acikken hiz_yonu zaten ustune yazilir.)
    #
    # MEKANIZMA KAPISI (logdan, tek kosuda):
    #   `hizala_deg` sutunu 0'dan AYRILMALI ve isareti `yaw_hizi_dps` ile
    #   TERS olmali; ayrica
    #       yaw_cmd_deg − (iris_yaw_deg + eps_yaw_deg) == −hizala_deg
    #   (K_YAW=1, BURUN_KD=0 iken). `hizala_deg` 0'a yapisiksa YAMA
    #   DEVREYE GIRMEMISTIR ve deney GECERSIZDIR.
    # 0 = kapali (BIT-AYNI eski davranis). Onerilen 0.20.
    KOMUT_HIZALA_S = _env_f("AVCI_IBVS_KOMUT_HIZALA", 0.0)
    # Patlama kalkani: yaw sarmasi / tek kare sicramasi komutu firlatmasin.
    # Olculen p95 |dψ| 18.3° oldugu icin 25° normal ucusta HIC baglamaz.
    KOMUT_HIZALA_MAX_DEG = _env_f("AVCI_IBVS_KOMUT_HIZALA_MAX", 25.0)

    # ── KADRAJ KORUYUCU (2026-08-16) ─────────────────────────────────────
    # ONCELIK TERSINE CEVRILIYOR. Su ana kadar yasa "hizli kapat" diyordu,
    # kadraj yan urundu. Olculen tablo bunun yanlis oldugunu soyluyor:
    #   faz omru <-> LOS hizi   rho = -0.657  (en guclu bagintili degisken)
    #   tespit kaybi: merkezde 0.036, kenarda (>39°) 0.609
    #   fazlarin %64.7'si hedef kadrajin ICINDEYKEN tespit olerek bitiyor
    #   olum aninda |eps| medyani 52° (kadraj siniri 61°)
    #   hizi acmak iskayi KOTULESTIRDI: 12.73 -> 15.25 m (omur 1.28 -> 1.06 s)
    # Faz omru TEK gercek kisit; kadraj da faz omrunu belirliyor.
    #
    # (a) BURUN_KD — burun, kutunun NEREDE oldugu kadar NEREYE GITTIGINE de
    #     bakar: yaw_cmd += KD * eps_hizi. Birim SANIYE (ongoruleme suresi).
    #     ⚠ eps_hizi kutunun KADRAJ ICI kayma hizidir, atalet LOS hizi DEGIL.
    #     Bilerek boyle: lam olculen sekilde 4-7 kat sisik, ona bagliyamayiz.
    #     Kutunun piksel kaymasi saf gozlem, yaw'a hic bagli degil.
    #     ⚠ Oransal kazanci ARTIRMAK salinim yapar (46 ms olu zaman + 211 ms
    #     gecikme); TUREV terimi faz ondelemesi katar, kararliligi ARTIRIR.
    #     Ikisi celismez: K_YAW'i kis, KD ekle.
    BURUN_KD = _env_f("AVCI_IBVS_BURUN_KD", 0.0)     # s; 0 = kapali

    # (b) KADRAJ_ESIK — |eps| bu esige yaklastikca KAPANMA kisilir ve hiz
    #     hedefin hizina (hiz_I) doner. Yani hedef kenara giderken ustune
    #     gitmeyi birakip once NISANI TOPARLARIZ. hiz_I sicak baslatilmis
    #     integral; hedef GPS'i KULLANILMIYOR (yarisma kurali).
    #     0 = kapali. Olculen kayip sicramasi 39°, kadraj siniri 61°.
    KADRAJ_ESIK_DEG = _env_f("AVCI_IBVS_KADRAJ_ESIK", 0.0)   # 0 = kapali

    # ── KOR KOPRU (2026-08-16, OLCULEN EN BUYUK ACIK) ────────────────────
    # OLCUM: gorsel faz boyunca yasa karelerin ancak %40'inda komut uretiyor.
    # Kalan %60'ta kutu yok ve SON KOMUT aynen tekrarlaniyor. Sonucu:
    #     tespit VARKEN  hiz yonu <-> hedefe yon : medyan  8.3°  (iyi)
    #     faz GENELINDE                          : medyan 56.4°, %24'u >90°
    # Yani "arac takibi birakip baska yere gidiyor" dedigimiz sey, kor
    # karelerde ESKI YONLE surukleniyor olmasi. Hedef donmeye devam ederken
    # 2 s eski komut buyuk sapma demek.
    # ⚠ KAYIP_M'i buyutmek bunu COZMEZ, KOR SUREYI UZATIR (olculdu: omur
    # 1.91 -> 3.06 s ama iska duzelmedi).
    # COZUM: kutuyu son iki tespitin PIKSEL HIZIYLA ileri tasi ve komutu
    # TAZELE. Olculdu: kurtarilan bosluklarin %69.5'i <=4 kare.
    # ⚠ DURUSTLUK: kopru karesi GERCEK TESPIT SAYILMAZ -- kayip sayaci
    # islemeye devam eder, faz yine zamaninda biter.
    # ⚠⚠ UCUSTA OLCULDU VE ZARARLI CIKTI (2026-08-16). Varsayilan 0 KALSIN.
    #     ayar        TUM     gorurken   korken   >90°
    #     kopru yok  42.9°      8.2°     73.3°    %17
    #     0.30 s     54.8°     15.0°     93.2°    %30
    #     0.60 s     70.9°     25.7°    110.6°    %40
    # HER SEY kotulesti, TESPITLI kareler DAHIL (8.2 -> 25.7°).
    # SEBEP: kutuyu PIKSEL HIZIYLA ilerlettim. Piksel hizi hedefin hareketi
    # DEGIL -- icinde BIZIM KENDI BURUN DONUSUMUZ de var. Burun donunce kutu
    # kayiyor, o kaymayi "hedef gidiyor" sanip ileri tasiyorum, burnu oraya
    # ceviriyorum, daha cok kayma... PARAZITIK DONGU. Burun donus hizinin
    # 13 -> 18 °/s cikmasi bunun izi.
    # DOGRU YOLU: hedefin ATALET LOS'unu tasi (kendi yaw'imizi cikararak),
    # sonra guncel yaw ile piksele geri cevir. iris_yaw TAZE oldugu icin
    # (gecikme taramasi: en iyi uyum 0.00 s, fark 0.0°) bu yapilabilir.
    # Bkz. KOR_KOPRU_ATALET.
    KOR_KOPRU_S = _env_f("AVCI_IBVS_KOR_KOPRU", 0.0)   # s; 0 = kapali (ZARARLI)

    # ── KOR KOPRU / ATALET SURUMU (yukaridaki hatanin DOGRU hali) ────────
    # Piksel yerine hedefin ATALET KERTERIZI korunur:
    #     los_son = iris_yaw(o an) + eps(o an)        <- tespit aninda saklanir
    #     kor karede:  eps_kopru = los_son - iris_yaw(SIMDI)
    #                  cx_kopru  = CX_NISAN + FX * tan(eps_kopru)
    # Kendi donusumuz iris_yaw ile ACIKCA CIKARILDIGI icin parazitik dongu
    # YAPISAL OLARAK kurulamaz: burun kerterize dondukce eps KUCULUR ve
    # komut yatisir. Piksel surumunde tam tersi oluyordu.
    # ⚠ Bu, hedefin ATALET KERTERIZININ SABIT kaldigini varsayar. Hedef
    # kor surede donerse kerteriz kayar; bu yuzden sure KISA tutulmali.
    # iris_yaw'in taze oldugu dogrulandi (gecikme taramasi: en iyi uyum
    # 0.00 s, medyan fark 0.0°) -- bu surumun on sarti oydu.
    # ⚠⚠ UCUSTA DOGRULANDI (2026-08-16). Tekrarli referansli test:
    #     ayar            faz  omur   iska_medyan  <5m  <3m
    #     kapali (C0)      14  1.97s     12.12 m     1    1
    #     ATALET 1.5 s     13  3.92s      2.81 m    12    8   <- 13'un 8'i esikte
    #     kapali (C2)      14  1.95s     12.40 m     0    0
    # Iki referans 0.28 m ile ortusuyor -> gurultu degil. Faz omru 2 KAT.
    # Mekanizma: LOS donus hizi 40 -> 6 °/s. Hedefin ETRAFINDA donmekten
    # UZERINE gitmeye gecisin imzasi.
    # ⚠ SURE KRITIK: 0.30/0.60 s'de ETKISIZ/ZARARLI cikti (yaylanin altinda).
    #   Yapisal kapi: KOR_KOPRU > KAYIP_M/31Hz olmali. K60 -> 1.9 s.
    # ⚠ YARISMA: hedef GPS'i KULLANILMIYOR. Girdi yalniz (a) son GERCEK
    #   tespitin kerterizi -- piksel + kendi yaw'imiz, (b) guncel yaw.
    #   Kopru karesi kilit sayacina SAYILMIYOR.
    KOR_KOPRU_ATALET_S = _env_f("AVCI_IBVS_KOPRU_ATALET", 1.5)   # s; 0 = kapali

    # ── KUTU BUYUME HIZI SINIRI (2026-08-16, UCUSTAN TESHIS) ─────────────
    # ⚠⚠ GORSEL FAZIN BIZI HEDEFTEN ATMASININ SEBEBI BUYDU.
    # Olculdu (10 gorsel fazin 10'unda): faz basinda menzil 11.7 m,
    # sonunda 32.1 m -- her faz bizi +21 m UZAKLASTIRIYOR.
    # Kare kare iz (194742): menzil 8 m'de SABITken kutu 20 -> 44 px firladi.
    #     t=0.00  menzil 8.2m  kutu 20  eps  3°  komut 18.6 m/s
    #     t=1.23  menzil 8.6m  kutu 44  eps 39°  komut 16.2
    #     t=3.09  menzil 45.8m kutu 20  eps  4°  komut  9.8   <- atildik
    # Hiz yasasi v = hiz_I + K_FWD*(BOYUT_REF - boyut). Kutu 44 olunca
    # "cok yakinim" deyip komutu 18.6 -> 9.8 m/s'ye dusuruyor; hedef 18 m/s
    # gidiyor -> saniyede 8 m aciliyoruz.
    # Kutu neden firliyor: hedef kadraj KENARINA kayiyor (eps 3° -> 39°) ve
    # orada gorunur boyut sisiyor (yandan bakinca dikey kuyruk kadraja girer;
    # ayrica kenar bozulmasi). Menzille ilgisi YOK.
    # ÇÖZÜM: kutu ∝ 1/menzil. Kapanma hizimiz en fazla ~6 m/s ise, R menzilde
    # kutu saniyede en fazla boyut*(6/R) buyuyebilir. R'yi kutudan kestiriyoruz
    # (R = MENZIL_PX_M/boyut), yani sinir = boyut^2 * KUTU_MAX_KAPANMA/MENZIL_PX_M.
    # 8 m'de 20 px icin ~13 px/s; olculen 60 px/s -> FIZIKEN IMKANSIZ, olcum
    # hatasidir ve reddedilir. KUCULME serbest (hedef gercekten uzaklasabilir).
    KUTU_HIZ_SINIRI = _env_f("AVCI_IBVS_KUTU_HIZ", 1.0) > 0.5   # 0 = kapali
    KUTU_MAX_KAPANMA = _env_f("AVCI_IBVS_KUTU_KAPANMA", 6.0)    # m/s

    # ── PN KAZANCI 1.6 -> 3.0 (2026-08-19, kullanici tarifi) ─────────────
    # Kullanici: "karsi arac hafifce donmeye baslarsa bizim arac da bbox ile
    # matematiksel hesapla ANINDA o kadar donsun; manevra hafif/orta/sert
    # ne olursa olsun ayni kadar donelim".
    # Bu davranisin kodda karsiligi TAM OLARAK bu terimdir:
    #     w_uygulanan = PN_N * los_hiz_az        (KIRPMA YOK)
    # `los_hiz_az` bbox'tan turetilen LOS acisal hizidir (rad/s, EMA'li).
    # OLCULDU (18777 satir): |los_hiz_az| medyan 0.3 rad/s = 17 °/s,
    #   p90 1.4 rad/s = 80 °/s -> sinyal SAGLAM, hedefin donusu gercekten
    #   goruluyor. Yani eksik olan sinyal degil, KAZANC.
    # Klasik PN literaturu N=3-5 kullanir; 1.6 bunun ALTINDA -> hedef
    # donerken sistematik olarak EKSIK donuyorduk.
    #
    # ⚠ DURUSTLUK NOTU — SONUC METRIGINDE USTUNLUK KANITLANAMADI:
    #     kosu 1 (4.7 dk): yaklasma  5 | CPA 3.36 | <5 m %80 | <3 m %40
    #     kosu 2 (5.7 dk): yaklasma 12 | CPA 7.57 | <5 m  %8 | <3 m  %0
    #   Ilk kosu tekrarlamadi; 5 dakikalik pencerelerde bu fark AYIRT
    #   EDILEMIYOR (PN 1.6 tabani da 6.5-9.5 arasi saliniyordu).
    #   Secim gerekcesi: (a) kullanicinin acik istegi, (b) PN teorisi,
    #   (c) iki kosuda da SAVRULMA DUSTU (%12.2 -> %4.7 ve %9.8), zarar yok.
    # Geri alma: AVCI_IBVS_PN=1.6
    PN_N = _env_f("AVCI_IBVS_PN", 3.0)           # 0 = kapat (eski saf takip)

    # ── DPP · BAKIS ACISI DONGUSU (2026-08-17, literatur turevi) ─────────
    # DPP_K_SIGMA > 0 -> PN yerine sapmali saf takip. Kararli dengesi KUYRUK
    # TAKIBIDIR (Lee/Ann/Kim ICAS 2018 eq.6-7). sigma STATIK olcum oldugu icin
    # gecikmede PN gibi cokmez.
    # Kazanc turetmesi: L(s) = k*e^{-tau s}/s icin PM = 90 - k*tau*(180/pi).
    #   olculen en kotu tau_eff = 0.375 s (250 ms hat + 4 FPS yarim ornek)
    #   k = 1.4 -> PM = 60 derece.  k = 2.0 -> PM = 47 (sinir).
    # Doygunluk: omega_max = MAX_ACCEL / V = 12/21.6 = 31.8 derece/s
    #   -> k=1.4 ile doyguna giren sigma hatasi 22.7 derece.
    # 0 = kapali.
    DPP_K_SIGMA = _env_f("AVCI_DPP_K", 0.0)        # 1/s; onerilen 1.4
    DPP_SIGMA_C_DEG = _env_f("AVCI_DPP_SIGMA_C", 0.0)   # 0 = tam kuyruk
    # lambda_nokta ILERI BESLEMESI (1.0 = tam). Kuyruk dengesinde olculen LOS
    # hizi = hedefin donus hizi; bu terim olmadan DONEN hedefte kalici sigma
    # hatasi kalir ve hedef kadrajdan cikar (tezgahta olculdu).
    DPP_FF_LAM = _env_f("AVCI_DPP_FF", 1.0)
    # Terminal taahhut icin AZAMI kerteriz hizi (derece/s). Hedefin duz
    # segmentini bekler. 0 = kapali. Onerilen 12-15 (olculen ayrim esigi 5-20).
    # ⛔ 2026-08-17 (AYNA DUZELTMESI SONRASI) OLCULDU -> KAPI ARTIK ZARARLI.
    #   Kapi yasanin OLCTUGU λ̇'ya bakiyor; ayna duzeldikten sonra bu buyukluk
    #   hedefin DUZ/DONUS halini AYIRT EDEMIYOR. B_ayna_DPP, 41 angajman,
    #   3467 tespitli kare, truth omega ile eslenerek:
    #       yasa |λ̇|  hedef DUZ iken  med 18.0 °/s   (p25 6.2  p75 43.1)
    #       yasa |λ̇|  hedef DONUS iken med 28.5 °/s  (p25 18.6 p75 47.2)
    #     esik 12 °/s -> DUZ karelerin yalniz %38.8'i gecer, DONUS'un %13.7'si
    #                    ZATEN gecer. Yani kapi duz segmenti de %61 blokluyor.
    #   Ve mandal anlarinda: gerceklesen 18 terminal taahhudunun yasa |λ̇|
    #   medyani 45.4 °/s (truth |omega| medyani 18.9 °/s) ->
    #       esik 12 ile 15/18, esik 15 ile 14/18 taahhut BLOKLANIRDI.
    #       bloklananlarin CPA medyani 2.66 m, gecenlerinki 4.83 m (n=3)
    #   yani kapi IYI taahhutleri kesip KOTULERI geciriyor (ters korelasyon).
    #   SEBEP: kapali menzilde λ̇ ~ V_dik/R; 6-11 m'de kucuk bir yanal ofset
    #   bile 40-70 °/s uretir. Bu, hedefin donusu DEGIL kendi geometrimizdir.
    #   VARSAYILAN 0 KALIR. Acmak icin once λ̇'dan BAGIMSIZ bir duz-segment
    #   gostergesi bulunmali (aday: kutu en-boy orani; DUZ med 12.9 px vs
    #   DONUS 15.0 px olculdu ama dogrulanmadi -> OLCULMEDI).
    TERM_LAM_MAX_DEG = _env_f("AVCI_TERM_LAM_MAX", 0.0)
    # Menzil dongusu: V = hiz_I + K_R * sat(r - R_SET, +-R_SAT), taban V_MIN.
    #   K_R = 0.7 -> PM ~ 55 derece (hiz kanali tau_v ~ 0.5 s + gecikme).
    #   R_SET = 8.5 m -> kutu 310/8.5 = 36 px, tespit tabaninin ustunde.
    #   ⚠ DPP_V_MIN ZORUNLU: yoksa yalniz kapatir, hic geri acamaz -> carpar.
    DPP_K_R = _env_f("AVCI_DPP_KR", 0.0)           # 1/s; onerilen 0.7
    # ⚠ 8.5 -> 6.0 (2026-08-17, CANLI OLCUMLE duzeltildi).
    #   Olculen: menzil x max(w,h) = 743 px*m (n=966 gercek tespit, 1920x1080).
    #   Sartname kilit sayaci (kilit_sayaci.py, LOCK_PCT=0.06) kutunun ekranin
    #   %6'si olmasini istiyor = 115 px  ->  menzil <= 6.45 m.
    #   8.5 m'de kutu 87 px = %4.6  ->  SAYAC HIC TIKLAMAZ.
    #   Yani 8.5 m'de kararli asili kalmak, kilidin SAYILAMAYACAGI menzilde
    #   asili kalmak demekti. 6.0 m payli tarafta.
    DPP_R_SET = _env_f("AVCI_DPP_RSET", 6.0)       # m
    DPP_R_SAT = _env_f("AVCI_DPP_RSAT", 10.0)      # m
    DPP_V_MIN = _env_f("AVCI_DPP_VMIN", 14.0)      # m/s
    PN_PENCERE_S = _env_f("AVCI_IBVS_PN_PENCERE", 0.25)   # λ̇ kestirim penceresi
    # PN hız yönünün LOS'tan azami sapmasi (emniyet freni, bkz. komut()).
    PN_SAPMA_MAX_DEG = _env_f("AVCI_IBVS_PN_SAPMA", 0.0)   # 0 = kapali

    # ══════════════════════════════════════════════════════════════════════
    #  MANEVRA ISKASI — 2026-08-17 AYNA SONRASI OLCUM (B_ayna_DPP, 41 angajman)
    # ══════════════════════════════════════════════════════════════════════
    # KULLANICI: "manevralarda kaciriyor." Ayrim ayna duzeltmesinden SONRA da
    # duruyor ama NEDENI degisti. Kampanya izi (truth) + bbox_ibvs kare logu
    # 1:1 eslenerek (|sure farki| medyan 0.13 s, 41/41) olculdu:
    #
    #   grup            n   CPA_med  hedef cercevesinde ARKADA / YANAL / DIKEY
    #   DUZ  (w<15)    26    2.69 m        0.87 /  0.36 / 1.31
    #   DONUS(w>=15)   15    6.43 m        4.42 /  1.29 / 0.95
    #
    # ⚠ MANEVRA ISKASI YANAL DEGIL BOYUNADIR: yanal 0.36 -> 1.29 m (+0.9),
    #   DIKEY IYILESIYOR (1.31 -> 0.95), ama ARKADA kalma 0.87 -> 4.42 m.
    #   Yani donuste MESAFE KAPANMIYOR. Dogrudan olculdu (menzil<25 m):
    #       kapanma hizi  DUZ +1.04 m/s   DONUS -0.84 m/s   (ACILIYOR)
    #
    # KOK NEDEN — hiz vektoru LOS'a yetisemiyor. delta (gercek hiz yonu ile
    # TRUTH LOS arasi) ISARETLI olarak ucе ayrildi (n=1390 donus karesi):
    #       kerteriz hatasi (yasa LOS - truth LOS) :  -0.8 deg   (%1.9)
    #       SIGMA           (psi_v  - yasa LOS)    : -18.2 deg   (%42.5)
    #       ARAC GECIKMESI  (gercek yon - psi_v)   : -16.4 deg   (%38.3)
    #       TOPLAM delta                            : -42.8 deg
    #   DUZ karelerde ayni ucu: -0.4 / -0.5 / -1.2 -> toplam -1.6 deg.
    #   delta yuzunden kaybedilen kapanma: DUZ 1.90 m/s, DONUS 6.06 m/s.
    #
    # NEDEN SIGMA BUYUYOR — DONUS KOMUTU DOYUYOR:
    #       istenen |w| = k*sigma + λ̇   med  39.4 °/s (p90 142)
    #       tavan  w_max = MAX_ACCEL/V   med  30.1 °/s
    #       DOYGUNLUK %54.1 (terminalde %42.5);  λ̇'nin talep payi %72
    #   ve limit_acceleration donuste karelerin %81.6'sinda tam doygun
    #   (|dv|/(a_max*dt) medyan 1.00).
    #   Yani tavan λ̇ ile zaten dolu; sigma duzeltmesine kalan pay
    #       (30.1 - 28.5)/k = 1.1 deg  ->  daha buyuk sigma DUZELTILEMIYOR.
    #
    # ⛔ BU OLCUM IKI POPULER YAMAYI CURUTUR:
    #   (1) APN / hedef ivme terimi: a_T = V_t*w_T = 19.5*0.375 = 7.3 m/s2,
    #       N/2*a_T -> +16.3 °/s EK TALEP. Talep zaten tavanin 9.3 °/s
    #       ustunde; TALEP EKLEMEK doygunlugu artirir, delta'yi azaltmaz.
    #       Ustelik DPP'de λ̇ ileri beslemesi kuyruk dengesinde ZATEN hedefin
    #       donus hizidir (λ̇ = gamma_nokta_hedef) -> APN ayni bilgiyi IKINCI
    #       KEZ sayar.
    #   (2) Kerterizi dedektor gecikmesi kadar ILERI SARMA: gecikme taramasi
    #       yapildi (yasa LOS'u truth LOS(t-D) ile kiyaslandi, D=-0.10..0.70):
    #           D=0.00 -> 2.50 deg   D=0.05 -> 2.32 deg (EN IYI)
    #           D=0.25 -> 5.42 deg   D=0.45 -> 10.63 deg
    #       Etkin bayatlik 0.05 s. Sebep yapisal: yasa iris_yaw(SIMDI) +
    #       eps(t-D) topluyor ve kuyruk takibinde yaw_hizi ~ λ̇ oldugu icin
    #       yaw terimi gecikmeyi KENDILIGINDEN kapatiyor. 0.225 s ileri
    #       sarmak medyan hatayi 2.3 -> ~5 dereceye CIKARIR. YAPILMADI.
    #
    # KALAN IKI GERCEK KALDIRAC (ikisi de asagida, VARSAYILAN KAPALI):
    #   M1 DONUS BUTCESI  -> tavani buyut  (w_max = a/V, V'yi kis)
    #   M2 ARAC TELAFISI  -> aracin 16.4 derecelik hiz-vektoru gecikmesini kapat
    # ══════════════════════════════════════════════════════════════════════

    # ── M1 · DONUS BUTCESI HIZ KAPISI ────────────────────────────────────
    # Aracin donebilecegi en yuksek hiz w_max = MAX_ACCEL / V. Talep bunu
    # asiyorsa TEK yapisal care hizi kismaktir (MAX_ACCEL'e dokunmadan):
    #       V_tavan = DONUS_BUTCE * MAX_ACCEL / |w_talep|
    # Olculen medyan talep 39.4 °/s -> V_tavan = 12/0.688 = 17.4 m/s
    # (su anki 20.65'ten %16 dusuk) ve o hizda w_max = 39.5 °/s = talep.
    # ⚠ YALNIZ KISAR, asla artirmaz. Talep tavanin altindaysa hic dokunmaz,
    #   yani DUZ segmentte (kullanicinin dogruladigi davranis) etkisizdir:
    #   duz karelerde sigma medyani 4.7 deg -> talep ~28 °/s < tavan 30.1.
    # ⚠ YALNIZ SEYIRDE. Terminal hucum hizi (V_TERMINAL=18, kullanici karari)
    #   DOKUNULMAZ -- olculen kapanma coku SEYIRDE (medyan menzil 11.15 m).
    # ⚠ TABAN ZORUNLU: hedef 19.5 m/s gidiyor; tavan tabansiz birakilirsa
    #   λ̇ sicramasinda (p99 133 °/s) V 5 m/s'ye duser ve hedef busbutun kacar.
    # ⚠ KAPI KENDI DE RAMPALI: kare kare zipladiginde limit_acceleration'i
    #   yeniden doyurur (tam kacinmak istedigimiz sey). Saniyede en fazla
    #   MAX_ACCEL kadar oynar.
    # MEKANIZMA KAPISI: acikken logda `donus_kapi_v` DOLU olmali ve donus
    #   karelerinde `w_talep_deg`in tavani asma orani %54.1'den DUSMELI.
    #   Dusmuyorsa yama devreye girmemistir, deney GECERSIZDIR.
    # 0 = kapali (bit-ayni eski davranis).
    DONUS_BUTCE = _env_f("AVCI_IBVS_DONUS_BUTCE", 0.0)     # 0=kapali; onerilen 0.9
    DONUS_BUTCE_VTABAN = _env_f("AVCI_IBVS_DONUS_VTABAN", 15.0)   # m/s; hiz tabani

    # ── M2 · ARAC GECIKME TELAFISI (hiz vektoru ongorusu) ────────────────
    # Olculdu: gercek hiz yonu, yasanin komut ettigi psi_v'nin ARKASINDA
    # kaliyor -- DUZ'de 1.2 deg, DONUS'ta 16.4 deg (|mutlak| med 16.9,
    # p90 27.7). Uygulanan donus hizi medyani 29.0 °/s ->
    #       tau_arac = 16.4 / 29.0 = 0.57 s   (birinci mertebe gecikme)
    # Rampa girdide birinci mertebe gecikmenin kalici hatasi tam olarak
    # w*tau'dur; referansi w*tau kadar ONE almak bunu BIREBIR kapatir.
    # ⚠ KERTERIZ ILERI SARMASI DEGIL: girdi tarafina dokunulmaz (o curutuldu,
    #   yukari bak). Telafi CIKIS tarafinda, yalnizca gonderilen hiz
    #   vektorunun acisinda. psi_v DURUMU ONCULEMESIZ kalir -- yoksa sigma
    #   kendi ongorusunu geri okur ve dongu pozitif geri beslemeye doner.
    # ⚠ TAVAN: doygunluk zaten %54; sinirsiz lead yalnizca daha cok doygunluk
    #   uretir. 25 deg tavan olculen p90'in (27.7) hemen altinda.
    # ⚠ DUZ UCUSTA ETKISIZ: duz segmentte uygulanan w ~ 0 -> lead ~ 0.
    # ⚠ KAPSAM M1'DEN FARKLI: M2 TERMINALDE DE calisir. Gerekce: arac
    #   gecikmesi terminalde de var (terminal karelerinin %42.5'i doygun) ve
    #   lead uygulanan donus hiziyla olceklendigi icin duz segmentte gelen
    #   temasta kendiliginden 0'dir. RISK: tau yanlissa 6 m'de 25 derecelik
    #   tavan 2.5 m yanal nisan hatasi demektir -> once M2'yi TEK BASINA
    #   olcup terminal CPA'sina bakmadan M1+M2 birlikte kosulmaz.
    # MEKANIZMA KAPISI: acikken logda `arac_lead_deg` medyani |tau*w_uyg|
    #   olmali (0.35 s ve 29 °/s ile ~10 deg). 0'a yapisikise DEVREYE
    #   GIRMEMISTIR (DPP/PN kapali demektir) ve deney GECERSIZDIR.
    # 0 = kapali (bit-ayni eski davranis).
    ARAC_TAU = _env_f("AVCI_IBVS_ARAC_TAU", 0.0)           # s; olculen 0.57
    ARAC_TAU_MAX_DEG = _env_f("AVCI_IBVS_ARAC_TAU_MAX", 25.0)   # °; lead tavani

    # ── BURUN = LOS (arayıcı/gövde ayrışması) ─────────────────────────────
    # yaw_cmd'ye "− sonum + lead_az" ekleniyordu: bunlar DİREKSİYON terimleri,
    # kameranın işi değil. lead tavanı 9° iken kamera hedefi bilerek 9° yanlış
    # gösteriyor; 12 px'lik kutuda bu hem hedefi kadraj kenarına itiyor hem
    # λ̇ kestirimini yanlıyor. Füzede arayıcı başlık hedefe bakar, gövde PN
    # uçar — iki ayrı iş. ÖLÇÜLDÜ: tek başına yetmiyor (0/40), PN ile birlikte
    # 29/40. İkisi AYRILMAZ.
    BURUN_LOS = _env_f("AVCI_IBVS_BURUN_LOS", 1.0) > 0.5
    LEAD_MAX_DEG = 25.0                          # °; lead açısı tavanı

    # ══ LEAD ERKEN BAŞLASIN — M3 (2026-08-09) ══
    # Yatay lead `if terminal:` kapısının ARKASINDAYDI. terminal mandalı
    # TERMINAL_BOYUT=25 px ≈ 6.4 m'de kapanır, yani lead ancak son 6 metrede
    # devreye giriyordu. `lead_olcek` de o noktaya kadar zaten 1.0 (sönüm
    # yalnız 6.4 m'nin İÇİNDE başlar) — yani sönüm kusurlu değildi, KAPI
    # kusurluydu.
    #
    # ÖLÇÜLDÜ — 4473 kutulu kare, kendi daire koşularım (2026-08-09):
    #   menzil    |λ̇| med   V med   gereken yanal ivme   tavanı aşan   lead
    #   20-35 m   0.46      19.4     9.0 m/s²             %43           0.0°
    #   13-20 m   0.59      19.6    12.0                  %62           0.0°
    #    8-13 m   1.21      18.3    21.9                  %88           0.0°
    #     5-8 m   1.56      15.9    22.4                  %75           0.0°
    #     0-5 m   0.79      18.0    14.1                  %54           8.4°
    # Tavan = g·tan(ANGLE_MAX 45°) = 9.81 m/s². Gereken ivme = V·λ̇.
    #
    # OKUMASI: 8 m'ye gelindiğinde karelerin %88'i aracın FİZİKSEL olarak
    # üretemeyeceği bir dönüş istiyor — o noktada hiçbir nişan düzeltmesi
    # kurtarmaz. Düzeltmenin ucuz olduğu yer 13-35 m bandı (9-12 m/s²,
    # tavana yakın ama erişilebilir) ve orada lead TAM SIFIR.
    #
    # DEĞİŞİKLİK: yatay lead artık kutu olan HER karede uygulanır. Ölçek,
    # tavan ve LOS hızı kaynağı AYNEN aynı — tek değişen, kapının kalkması.
    # ⚠ KAPSAM: yalnız YATAY. Dikey lead (lead_el) terminal tutuşunda kalıyor;
    # kullanıcının düz uçuşta doğruladığı dikey davranış tek değişken
    # kuralının dışında tutuluyor.
    # DÜZ UÇUŞ RİSKİ DÜŞÜK: lead = LEAD_SURE · λ̇ ve düz takipte λ̇ ≈ 0
    # (ölçüldü: 20-35 m'de bile medyan 0.46 rad/s DÖNÜŞTE; düz koşuda ~0).
    #
    # ⛔ UÇUŞTA ÖLÇÜLDÜ (2026-08-09, 2 koşu / 2038 kutulu kare) — VARSAYILAN
    # KAPALI. Kapı kalkınca kadrajda tutuş gerçekten düzeldi:
    #     yatay hata p90   173.5 → 97.5 px      temas süresi  90 → 143 s
    #     yatay hata med    46.0 → 34.0 px      boyut son/ilk 0.97 → 1.07
    # AMA asıl iş olan YAKLAŞMA bozuldu:
    #     8 m içine giriş   4 kez / 65 kare  →  2 kez / 15 kare
    #     en yakın menzil   2.1 m (isabet)   →  13.2 / 10.0 m
    #     tavanı aşan kare  8-13 m'de %88    →  %95
    # SEBEP: lead karelerin %27'sinde LEAD_MAX_DEG=25° tavanında, medyan 18.7°.
    # Terminal için ayarlanmış tavan sürekli uygulanınca kalıcı nişan sapması
    # oluyor; araç kesişmek yerine hedefi GÖLGE ediyor (paralel koşu).
    # YÖN doğru, GENLİK yanlış. Sıradaki deney: seyir fazına AYRI (küçük)
    # lead tavanı — ~8-10° — terminal tavanı 25°'de kalsın.
    # AVCI_IBVS_LEAD_ERKEN=0 → lead yine yalnız terminalde (2026-08-09 hali).
    #
    # ══ M4 (2026-08-15): ERKEN LEAD AÇILDI + SEYİR TAVANI AYRILDI ══════════
    # Yukarıdaki notun kendi reçetesi uygulanıyor: "YÖN doğru, GENLİK yanlış.
    # Sıradaki deney: seyir fazına AYRI (küçük) lead tavanı — ~8-10° —
    # terminal tavanı 25°'de kalsın."
    #
    # NEDEN ŞİMDİ: supervisor'a GEOMETRİ KAPISI eklendi (aspect ≤ 40°), yani
    # görsel faz artık YALNIZ kuyruk takibinde başlıyor. Ölçüldü (3 angajman,
    # 2026-08-15): devirler aspect 3-4°, terminal ω 12-14 °/s.
    # Bu yeni rejimde kalan tek kusur TAKİP GECİKMESİ:
    #     aracın döndüğü      ort 27-31 °/s
    #     hatanın büyüdüğü    ort 33-36 °/s      -> her tik biraz geride
    #     eps_yaw  +2° → +55..63°  (1.6 s'de kadraj kenarı)
    #     lead_az  karelerin %100'ünde 0.0        <- ileri-besleme YOK
    # Kapasite 95 °/s, gereken ~35 °/s: araç YAPABİLİR ama emredilmiyor.
    # Oransal kontrolcü RAMPA girdiyi (dönen hedefin kerterizi) daima geriden
    # takip eder; kalıcı hatayı ancak ileri-besleme kapatır.
    #
    # 2026-08-09'da erken lead'in yaklaşmayı bozmasının sebebi tavandı, yönü
    # değil: kadrajda tutuş DÜZELMİŞTİ (yatay hata p90 173.5 → 97.5 px).
    # Seyir tavanı 9° ile tutuş kazancı korunup gölgeleme sapması kesiliyor.
    LEAD_ERKEN = _env_f("AVCI_IBVS_LEAD_ERKEN", 1.0) >= 0.5
    # Seyir (terminal DIŞI) lead tavanı. 0 vermek erken lead'i etkisiz kılar.
    # M5 (2026-08-15): 9° -> 14° DENENDI ve GERI ALINDI.
    # Gerekçe 9°'nin bağlıyor görünmesiydi (lead_max tam 9.0°). Ama ölçüm
    # bunu çürüttü -- 14° ile YAKLAŞMA bozuldu:
    #                    en yakın (ort)   en iyi koşu   kutu_max
    #     lead yok             8.0 m         3.3 m        23 px
    #     lead  9°             7.1 m         2.2 m        31 px   <-- en iyi
    #     lead 14°             8.8 m         5.5 m        20 px   <-- geriledi
    # Yani 2026-08-09'un "gölgeleme" teşhisi 25°'ye özgü değil, sınır 9-14
    # arasında bir yerde: fazla lead verilince araç kesişmek yerine hedefin
    # yanında PARALEL uçuyor. 9° bu veri setindeki en iyi değer.
    LEAD_MAX_SEYIR_DEG = _env_f("AVCI_IBVS_LEAD_SEYIR_DEG", 9.0)
    VZ_MAX_TERM = _env_f("AVCI_IBVS_VZT", 5.0)   # m/s; terminalde dikey tavan

    # ── TERMİNAL DİKEY SÖNÜMLEME (2026-08-09, kullanıcı: "son anda üstten
    # geçtik") ──
    # SORUN: terminal dikey kanalı SAF NİŞANLAMA (vz = −v·tan(elev)) — türev/
    # sönümleme terimi YOK. Uzaktayken haklı olarak tırmanma emri veriliyor,
    # araç dikey momentum kazanıyor; hedefe varınca komut azalıyor ama momentum
    # geç sönüyor → hedefin ÜSTÜNDEN geçiliyor.
    # Kullanıcının manuel uçuş kaydından ölçüldü (log 081132, son kareler):
    #     hedef TAM nişanda (dikey hata −2.2°) iken vz komutu −4.2 m/s
    #     ardından kutu kadrajda 294 → 456 px kayıyor = üstünden geçildi
    # ⚠ Lead DEĞİLDİ: aynı karelerde lead 0.09-0.15 s'ye sönmüş ve AŞAĞI
    # yönlüydü (−3° … −13°). Lead sönümü çalışıyor, sebep bu değil.
    #
    # ÇÖZÜM: aracın KENDİ dikey hızıyla türev sönümlemesi.
    #     vz = vz_nişan + K_VZ_D · (vz_nişan − vz_gerçek)
    # Zaten gerekenden hızlı tırmanıyorsak komut azalır/ters döner.
    # Girdi drone'un KENDİ sensörü — yarışma kuralı serbest.
    K_VZ_D = _env_f("AVCI_IBVS_KVZD", 0.6)   # dikey sönümleme kazancı

    # ══ DİKEY KOMUT KAPANMA HIZIYLA ÖLÇEKLENİR (2026-08-09) ══
    # KULLANICI GÖZLEMİ (uçuş kaydı): "tam vuracağı sırada yukarı manevra
    # yapıp aracın üstünden geçiyoruz."
    #
    # KÖK NEDEN — tek bir çarpan. Terminal dikey yasası şuydu:
    #     vz = −v_los · tan(yükseliş)          v_los = DRONE'un hızı (18 m/s)
    # Oysa dikey farkı "varana kadar" kapatmak gerekir; "varana kadar"ki süreyi
    # belirleyen şey KAPANMA hızıdır, drone'un yer hızı değil. Hedef 15 m/s ile
    # kaçtığı için mesafe saniyede 18 m değil ~2 m kapanıyor. Doğrusu:
    #     vz = −ṙ · tan(yükseliş)              ṙ = kapanma hızı
    #
    # ÖLÇÜLDÜ (kullanıcının 4 hücumu, üçünde de aynı):
    #     menzil 3.67 m, dikey fark 0.89 m altta
    #     komut −5.00 m/s   ·   gereken −0.37 m/s   →  13.7 KAT fazla
    # Araç yukarı ivmeleniyor, komut sonra tersine dönüyor ama momentum
    # kalıyor → hedefin üstünden geçiliyor. Gün boyu kovaladığım dikey
    # salınımın açıklaması da bu: mimari değil, çarpan.
    #
    # ṙ GÖRÜNTÜDEN ölçülür (GPS YOK, yarışma kuralı temiz):
    #     R = MENZIL_PX_M / boyut   ⇒   ṙ = −dR/dt = R · (dboyut/dt) / boyut
    # Kutu boyutu titrer → EMA ile yumuşatılır; taban konur ki kapanma
    # durduğunda dikey düzeltme büsbütün ölmesin.
    # AVCI_IBVS_KAPANMA=0 → eski davranış (v_los ile ölçekleme) aynen geri.
    KAPANMA = _env_f("AVCI_IBVS_KAPANMA", 1.0) >= 0.5
    KAPANMA_MIN = _env_f("AVCI_IBVS_KAPANMA_MIN", 1.5)   # m/s; ölçek tabanı
    KAPANMA_EMA = _env_f("AVCI_IBVS_KAPANMA_EMA", 0.20)  # kare başına yumuşatma
    # Kutu boyutu → menzil ölçeği: TERMINAL_BOYUT 25 px ≈ 6.4 m (Cfg yorumu)
    # ⚠ 160.0 -> 202.6 (2026-08-16, OLCULDU: 1788 tespitli kare / 93 kosu,
    # truth menzille eslenerek). Eski sabit menzili sistematik %21 EKSIK
    # sayiyordu (15-20 m diliminde -%34). Dogru deger sqrt(w*h) icin 202.6.
    # Daha iyisi (medyan hata %21 -> %6.2): R = F*0.856/(w^0.15 * h^0.85);
    # hazir fonksiyon arac/menzil_model.py. Buraya tek sabit birakildi cunku
    # yasa tek carpanla calisiyor -- model gecisi ayri is.
    # ⚠ Bu veri TAMAMEN kuyruk takibi (aspect 138-166°). Bordadan gorulen
    # hedefte model menzili ~%25-30 EKSIK sayar.
    #
    # ══ M-KAL · YENIDEN OLCULDU, 2026-08-17 (sim/yaw_menzil.py --menzil) ══
    # n = 58.386 gercek tespitli kare / 393 log, truth = get_debug_truth,
    # kirpik kutular ve ayna-oncesi loglar ATILDI.
    #     OLCULEN CARPANLAR (medyan): R·√(w·h) = 153.0 | R·w = 241.8
    #     model                          medAPE   yanlilik   medAE
    #     202.6 / √(w·h)   (KOD)          33.1%    +32.4%     3.98 m   ⛔
    #     160.0 / √(w·h)   (IKIZ)         19.0%     +4.6%     2.29 m
    #     153.0 / √(w·h)   (olculen)      19.2%     +0.0%     2.24 m
    #     241.8 / w        (yalniz EN)    19.7%     +0.0%     2.38 m
    #     232.2 / (√(w·h)+4.11)           17.0%    +10.6%     2.19 m
    #   ⇒ 202.6 SISIK: menzili sistematik %32 BUYUK sayiyor.
    #   ⇒ MENZILE GORE 202.6'nin yanliligi (bu yuzden terminalde en kotu):
    #        3-6 m +53.8% | 6-10 +39.3% | 10-15 +34.2% | 15-30 +25.7% | 30-60 −8.4%
    #      Yani 202.6 YALNIZ 30-60 m'de dogru; TERMINALDE %40-54 sisik.
    #   ⚠ ONCEKI KALIBRASYON (2026-08-16, 1788 kare) 202.6 demisti; bu
    #     olcum 33 KAT daha buyuk veriyle onu CURUTUYOR. Sebep muhtemelen
    #     o kumenin uzak karelerle agirlikli olmasi.
    #   ⚠ "yalniz genislik" (K_w/w) BU KUMEDE sqrt modelinden DAHA IYI
    #     DEGIL (19.7% vs 19.2%). Kazanci nokta hatasinda degil, menzille
    #     KAYMANIN azalmasinda (+19/+4/−0/−4 vs +54/+39/+34/+26).
    #
    # ⛔⛔ VARSAYILAN DEGISMEDI: 202.6 aynen duruyor. Kampanya kosuyor,
    #    varsayilan degistirmek kosan olcumu sessizce kirletir. Kalibrasyon
    #    A/B kolu olarak, ENV ile denenir (arac/recete_yaw.json).
    # ⭐⭐ 2026-08-19: 202.6 -> 153.0 UYGULANDI.
    # Asagidaki M-KAL olcumu (n=58.386 gercek tespitli kare / 393 log,
    # truth = get_debug_truth) 202.6'nin menzili sistematik %32 BUYUK
    # saydigini gosteriyordu ve bu bulgu ZATEN YAZILIYDI ama koda
    # UYGULANMAMISTI. Yanlilik menzille buyuyor: 30-60 m -8.4% iken
    # 3-6 m'de +53.8% -- yani KUTU BUYUDUKCE (yaklastikca) daha cok sisiyor.
    #
    # NEDEN KRITIK: bu menzil dikey kanala besleniyor.
    #     R = MENZIL_PX_M / boyut
    #     r_nokta = R * (dboyut/dt) / boyut          (kapanma hizi)
    #     vz = -r_nokta * tan(yukselis)              (terminal dikey komut)
    # R %54 sisikse kapanma hizi ve dikey komut da o kadar sisik cikar ->
    # arac irtifada ASIYOR, hedefin ustunden geciyor. Kullanicinin
    # "irtifayi tutturamiyor / ustunden geciyor" gozlemi bunun imzasi.
    #
    # 153.0 olculen medyan carpandir: yanlilik %0.0, medAPE %19.2,
    # medAE 3.98 -> 2.24 m.
    # ⚠ TERMINAL_BOYUT=25 px'in ima ettigi menzil de duzelir: 8.1 -> 6.1 m.
    # Geri alma: AVCI_IBVS_MENZIL_PX=202.6
    # ⛔ 153.0 DENENDI ve GERI ALINDI (2026-08-19, ucusta 5.7 dk):
    #     yaklasma 0 | en yakin 34.60 m | hiz 21 -> 14.2 | <8 m/s %19.4
    #   Yani sabit OLCUM OLARAK dogru (yanlilik %0 vs %32) ama yasanin
    #   BUTUN esikleri sisik degere gore kalibre edilmis:
    #     TERMINAL_BOYUT (px->menzil imasi), KUTU_MAX_KAPANMA siniri
    #     (= boyut^2*K/MENZIL_PX_M), r_nokta ve dikey olcek, supervisor
    #     devir kapilari...
    #   Tek sabiti duzeltmek zinciri kopariyor. DOGRU IS: 153.0'a gecerken
    #   bagimli esikleri birlikte yeniden ayarlamak (ayri calisma).
    MENZIL_PX_M = _env_f("AVCI_IBVS_MENZIL_PX", 202.6)   # px·m; √(w·h) modeli
    # ⚠ TERMINAL NISAN KAPISININ IKIZI (eskiden bbox_ibvs icinde HARDCODED
    #   160.0 idi). Ayni fiziksel buyukluk IKI FARKLI sabitle hesaplaniyordu
    #   -> kapi ile yasa birbirinden %27 kopuktu. Artik tek fonksiyondan
    #   (menzil_kutudan) geciyor ve TEK ENV ile esitlenebiliyor.
    #   ⚠ Varsayilan 160.0'da BIRAKILDI (bit-ayni). Ve olcum sunu diyor:
    #     160.0 (+4.6% yanli) yasanin 202.6'sindan (+32.4%) DAHA DOGRU --
    #     yani "kapiyi yasaya esitle" demek kapiyi %27 GEVSETMEK olurdu.
    #     Dogru is IKISINI DE olculen 153.0'a cekmektir.
    MENZIL_TERM_PX_M = _env_f("AVCI_IBVS_MENZIL_TERM_PX", 160.0)   # px·m
    # >0 verilirse menzil YALNIZ KUTU GENISLIGINDEN hesaplanir: R = K_w / w.
    # Gerekce: std(log(R·h)) = 0.494, std(log(R·w)) = 0.365 -- kutu YUKSEKLIGI
    # genisliginden cok daha gurultulu, √(w·h) o gurultuyu iceri aliyor.
    # 0 = kapali. Olculen K_w = 241.8 px·m.
    MENZIL_KW = _env_f("AVCI_IBVS_MENZIL_KW", 0.0)       # px·m
    # DEDEKTORUN SABIT KUTU PAYI c: s_olculen = s_gercek + c olduğu icin
    # "R·boyut" carpani menzille DOGRUSAL kayiyor (bkz. bbox_geometri.
    # menzil_ofsetli). R = K / (boyut − OFS). OFS<0 -> paydaya EKLER.
    # 0 = kapali (bit-ayni). Olculen en iyi cift: PX=232.2, OFS=−4.11.
    MENZIL_OFS_PX = _env_f("AVCI_IBVS_MENZIL_OFS", 0.0)  # px
    # ── MAX_ACCEL: KOMUT HIZI DEGISIM SINIRI ─────────────────────────────
    # ⚠ 2026-08-15'te OLCULDU: ASIL BAGLAYAN LIMIT BU.
    # Bizim aracin GERCEK yanal ivmesi (24682 ornekli iz kaydi, hiz>8 m/s):
    #     %99  11.22   max 11.96 m/s²      -> esdeger yatis 49-51°
    # yani komut tam 12.0'a DAYANMIS. Aracin kendi fizigi degil, BU CLAMP
    # baglıyor. Hiz vektorunun donebilecegi en yuksek hiz dogrudan buradan:
    #     omega_max = MAX_ACCEL / V = 12 / 18.3 = 37.6 °/s
    # ve olculen %99 donus hizi 37.9 °/s -- birebir ayni.
    #
    # NEDEN ONEMLI: donen hedefi takip icin gereken 33-36 °/s. Tavana
    # dayaniyoruz, yani her 30°'lik duzeltme
    #     dv = 2·V·sin(15°) = 9.3 m/s  ->  9.3/12 = 0.78 s
    # suruyor ve o surede hedef 16° daha donuyor. Kalici takip gecikmesinin
    # kaynagi bu.
    #
    # ⚠ MEKANIZMA KAPISI (Gazebo ekibinin O6 dersi): bir ozelligi kiyaslamadan
    # ONCE gercekten devreye girdigini kanitla. Yukseltince OLCULEN yanal
    # ivmenin 12'yi ASTIGINI dogrula; asmiyorsa oyunun kendi ucus modeli
    # bagliyordur ve deney gecersizdir.
    MAX_ACCEL = _env_f("AVCI_MAX_ACCEL", 12.0)   # m/s²

    # ══ YATAY AÇI ROLL/PITCH TELAFİSİ — T1a (2026-08-09) ══
    # KULLANICI GÖZLEMİ: "düz uçuşta ıskalamıyor, hedef manevra yapınca görsel
    # güdüm sapıtıyor, yatayda çok salınım oluyor."
    #
    # KÖK NEDEN — bir çerçeve karışıklığı. Yatay hata şöyle okunuyordu:
    #     eps_yaw = atan((cx − CX)/FX)      ← KAMERA çerçevesi azimutu
    #     los_az  = iris_yaw + eps_yaw      ← "bu SEVİYE azimutudur" varsayımı
    # Bu varsayım YALNIZ roll=0'da doğru. Kamera gövdeye 25° YUKARI vidalı;
    # araç yattığında kamera da yatıyor ve hedefin görüntüdeki YATAY konumu
    # kayıyor. Kodda roll telafisi hiç yoktu (roll okunuyordu ama sadece
    # takla bekçisine gidiyordu).
    #
    # ÖLÇÜLDÜ — 5869 kare GERÇEK uçuş verisi (GPS logunda hedefin gerçek
    # konumu + aracın gerçek duruşu + piksel izdüşümü birlikte var; okunan
    # açı ile gerçek seviye azimutu doğrudan kıyaslandı):
    #     yatış  0-9°  (4450 kare) → yatay okuma hatası ort. 0.6°
    #     yatış 10-19° ( 821 kare) →                        2.4°
    #     yatış 20-29° ( 313 kare) →                       11.0°
    #     yatış 30-39° ( 210 kare) →                       13.9°
    #     yatış 40-49° (  75 kare) →                       10.8°
    # Teori (hedef boresight'ın 20° üstünde): 30°→9.9°, 45°→14.2° — UYUŞUYOR.
    # Araç manevrada gerçekten 43-45°'ye (ANGLE_MAX tavanı) dayanıyor.
    #
    # ⚠ HATANIN İŞARETİ DÖNÜŞE KARŞI: sağa dönerken (sağa yatarken) hedef
    # SOLA kaymış görünüyor → güdüm dönüşü kısıyor → geride kalıyor → sonra
    # aşırı düzeltiyor. Yatay salınımın kaynağı bu.
    #
    # ÇÖZÜM: piksel ışını aracın KENDİ duruşuyla SEVİYE çerçevesine döndürülür
    # (bkz. los_seviye). Girdi drone'un kendi IMU'su — canlı hedef GPS'i yok,
    # yarışma kuralı (D0) temiz.
    # ⚠ T1a KAPSAMI: YALNIZ YATAY kanal. Dikey kanal (piksel_elev + pitch ve
    # tutuştaki eps_elev) BİLEREK dokunulmadan bırakıldı — uçuşta doğrulanmış
    # dikey davranış tek değişkenli testin dışında tutuluyor.
    # ⚠ DÜZ UÇUŞU BOZMAZ: roll<10°'de fark 0.6° (ölçüldü), yani kullanıcının
    # "düz uçuşta ıskalamıyor" dediği davranış pratikte aynı kalır.
    # AVCI_IBVS_ROLL=0 → eski (telafisiz) yol aynen geri gelir.
    ROLL_TELAFI = _env_f("AVCI_IBVS_ROLL", 1.0) >= 0.5

    # ══ Ö1 · KAÇIŞ TELAFİSİ — hız yasasına kapanma hızı geri beslemesi ══
    # KULLANICI GÖZLEMİ (2026-08-10, kendi uçuşu + 16 kaçamak testi):
    # "hedef manevra yaptığı sırada mesafe kapatılamıyor, hedef çok uzağa
    # gidiyor; ne zaman düz gitmeye başlarsa o zaman vuruluyor."
    #
    # ÖLÇÜLDÜ — 10 kaçamak koşusunun İSTİSNASIZ HEPSİNDE, kaçamaktan sonraki
    # 15 s içinde:
    #     drone hızı  7.7-13.9 m/s'ye düşüyor   (hedef 15.4-16.3 m/s)
    #     açılan mesafe 48-147 m
    # Hedeften YAVAŞKEN mesafe matematiksel olarak kapanmaz.
    #
    # KÖK NEDEN: hız yasası saf bir MENZİL düzenleyicisi — "hedef şu an benden
    # uzaklaşıyor mu" girdisi YOK.
    #     hata  = BOYUT_REF − boyut ;  hiz_I += K_I·hata·dt ;  v = hiz_I+K_FWD·hata
    # Yakın geçişte kutu 88-102 px olunca hata = −63…−77 → integral saniyede
    # 3.1 m/s DÜŞÜYOR; normal hata ≈ +15'te ise saniyede 0.6 m/s toparlanıyor.
    # 5:1 asimetri = kullanıcının gördüğü uzun toparlanma. (Kullanıcının uçuş
    # logunda birebir: hiz_I 15.1 → 12.0 iki saniyede, geri çıkması ~5 s.)
    #
    # ÇÖZÜM: ṙ (kapanma hızı) zaten hesaplanıyor — dikey kanal için eklenmişti
    # (bkz. Cfg.KAPANMA). Hız yasasına da girsin:
    #     v_los = hiz_I + K_FWD·hata + KACIS_KD·max(0, −ṙ)
    # ⚠ YALNIZ HIZLANDIRMA YÖNÜ. ṙ>0 (yaklaşırken) terim sıfırdır — kullanıcı
    # freni bilerek kaldırttığı için (V_MIN=0, "geri çekilme yok") bu terim
    # asla yavaşlatma yapmaz.
    # ⚠ KAPSAM: yalnız SEYİR (IBVS). Terminal hücum yasası (v=V_TERMINAL)
    # ve dikey kanal DOKUNULMADI — tek değişken kuralı.
    # AVCI_IBVS_KD=0 → kapalı (varsayılan; açık değeri ölçüm belirleyecek).
    KACIS_KD = _env_f("AVCI_IBVS_KD", 0.0)      # (m/s)/(m/s); 0 = kapalı
    KACIS_MAX = _env_f("AVCI_IBVS_KDMAX", 10.0)  # m/s; terimin tavanı

    # ══ Ö8 · YANAL KOMUT: AÇI DEĞİL, KAÇIRMA MESAFESİ ══
    # KULLANICI GÖZLEMİ (2026-08-10): "araç tam çarpacakken hedef hafif sağa
    # manevra yaptı; bbox ekranın en sağına geldiği için bizim araç sağa öyle
    # bir manevra yapıyor ki sonra salınım oluyor. En azından hedefin sağa
    # gittiği kadar gitsek ve aynı doğrultuda kalsak."
    #
    # ÖLÇÜLDÜ (O7A, kaçamak yatay, tetik 8 m — temas öncesi son 0.4 s):
    #     t       cx    menzil   eps_yaw   yaw komut değişimi
    #   -0.25    336     1.8 m      5.0°        60 °/s
    #   -0.10    410     1.5 m     24.7°       120 °/s  ← DOYDU
    #    0.00    432     1.3 m     35.1°       120 °/s
    #   +0.05    548     1.5 m     58.3°       122 °/s
    #   +0.15    600     2.5 m     58.0°       118 °/s   (kadraj genişliği 640)
    #
    # KÖK NEDEN: eps_yaw = atan((cx−CX)/FX) geometrik olarak DOĞRU — hedef
    # gerçekten 58° yanda. Ama 1.5 m'de 58°, yalnızca 1.5·sin(58°) = 1.3 m
    # yanal kaçırma demek. Güdüm 58°'lik dönüş emri veriyor: 1.3 metre için.
    # Aynı 58° hata 30 m'de 25 metrelik kaçırmadır — güdüm ikisine AYNI
    # komutu veriyor. Yani AÇIYA tepki veriyor, oysa önemli olan MESAFE.
    # 18 m/s'lik vektörü 58° döndürmek 17.5 m/s'lik hız değişimi ister;
    # MAX_ACCEL=12 ile 1.45 s sürer, oysa geometri 0.08 s bırakıyor →
    # komut doyar, araç savrulur, sonra geri savrulur = SALINIM.
    #
    # ⚠ Ö7 (yaw hız tavanı) bu yüzden hiçbir şey yapmadı: yaw sınırı yalnız
    # BURNU yavaşlatıyor, hız vektörü zaten anında savruluyordu. Salınım
    # burun kanalında değil HIZ kanalındaydı.
    #
    # ÇÖZÜM: hız vektörünün yönü, kalan sürede yanal kaçırmayı kapatmak için
    # gereken yanal hızdan türetilir:
    #     y      = R·sin(eps_yaw)            yanal kaçırma (m)
    #     t_go   = R / ṙ                     kalan süre (s)
    #     v_y    = YANAL_K · y / t_go        gereken yanal hız
    #     eps_eff= asin(v_y / v_los)
    # ve YALNIZ KISAR: eps_hiz = min(|eps_yaw|, |eps_eff|).
    # BURUN tam eps_yaw'da kalır → kamera hedefi kaybetmez. Gövde hedefin
    # gittiği kadar yana kayar → savrulmaz. (Kullanıcının tarifi bu.)
    #
    # Yukarıdaki anda (1.5 m, y=1.3 m, ṙ≈3 m/s, K=3): 58° → ~26°,
    # gereken hız değişimi 17.5 → 8.1 m/s.
    # ⚠ RİSK: uzak menzilde de kısar (30 m'de 20° → ~10°). Uzak menzil şu an
    # çalışıyor (25 m tetikte 4/6 isabet) — gerileme olup olmadığı ÖNCE orada
    # ölçülür. AVCI_IBVS_YANAL=0 → tamamen kapalı (varsayılan).
    YANAL_K = _env_f("AVCI_IBVS_YANAL", 0.0)      # 0 = kapalı; açık ~3.0
    YANAL_RDOT_MIN = 1.5   # m/s; t_go patlamasın diye kapanma tabanı
    YANAL_TGO_MIN = 0.20   # s;   t_go tabanı (0'a bölme + aşırı agresiflik)
    # MENZİL KAPISI — birim testi B45 yakaladı: sınır kapısız haliyle 20 m'de
    # komutu %37'ye düşürüyordu. Uzak menzil ŞU AN ÇALIŞIYOR (25 m tetikte
    # 4/6 isabet); orayı bozmamak için sınır yalnız yakında bağlar ve
    # YUMUŞAK geçer (sert kapı kendi başına sıçrama yaratırdı):
    #   R ≥ MENZIL      → hiç kısmaz (eski davranış birebir)
    #   R ≤ MENZIL/2    → tam kısar
    #   arası           → doğrusal harman
    YANAL_MENZIL = _env_f("AVCI_IBVS_YANAL_M", 12.0)   # m

    # ══ Ö9 · YATAY KANALA SÖNÜMLEME (D terimi) ══
    # KULLANICI GÖZLEMİ (2026-08-11, kendi uçuşu ucus_20260811_185753):
    # "hedefin yaptığı ilk manevrada bizim araç o kadar sağa yönelmese, hafif
    # bir sağa yönelip hedefin direkt arkasında kalsa, salınımı sönümlesek."
    # Kare 5 (4.3 m): ufuk DÜZ, hedef tam ortada, kutu 0.92 — mükemmel.
    # Kare 7 (2 s sonra): ufuk 40° YATIK, drone hedefin ÖBÜR tarafına geçmiş.
    # Mesafe 6.1 → 7.6 → 5.8 → 7.7 → 15.3 → 25.4 m: iki kez gidip geldi,
    # sonra tamamen kaybetti. Tetikleyen manevra HAFİFTİ (aileron 1733).
    #
    # KÖK NEDEN — YAPISAL: yatay kanal SAF ORANSAL bir denetleyici.
    #     yaw_cmd = iris_yaw + K_YAW·eps_yaw        (K_YAW = 1.0, TAM düzeltme)
    # Türev/sönümleme terimi YOK. Gecikmeli bir sistemde saf-P denetleyici
    # ZORUNLU olarak salınır — bu bir ayar değil YAPI eksiği. Araç hedefe
    # doğru dönerken "yeterince döndüm, yavaşla" diyen hiçbir şey yok;
    # hatayı ancak sıfırı geçtikten SONRA fark ediyor.
    #
    # ÇÖZÜM: aracın KENDİ dönüş hızına karşı koyan bir terim (rate feedback):
    #     eps_sonumlu = eps_yaw − SONUM_T · yaw_hizi
    # SONUM_T saniye biriminde: araç ω rad/s dönüyorsa komut ω·SONUM_T kadar
    # geri çekilir. Klasik PD; P-only aşımının ders kitabı çaresi.
    # ⚠ Girdi aracın KENDİ IMU'su (yaw türevi) — canlı hedef GPS'i yok, D0 temiz.
    # ⚠ Düz uçuşta etkisiz: hedef düz giderken drone dönmüyor (ω≈0) → terim 0.
    # AVCI_IBVS_SONUM=0 → kapalı (varsayılan; açık değeri ölçüm belirleyecek).
    #
    # ── 2026-08-14: 0.0 → 0.30 AÇILDI (ölçümle) ────────────────────────────
    # Yukarıdaki "açık değeri ölçüm belirleyecek" notunun cevabı geldi.
    # DoW canlı koşusu, devir anındaki komut logu (bbox_ibvs_20260814_214026):
    #     t=0.00  yaw 42.3°   conf 0.891
    #     t=0.31  yaw 46.6°   conf 0.890
    #     t=0.58  yaw 68.3°   conf 0.882
    #     t=0.69  yaw 81.4°   conf 0.899
    # 0.7 saniyede 42° → 81°: klasik saf-P aşımı. Araç sert dönünce hedef
    # kadrajdan çıkıyor ve görsel faz 2.6-4.4 sn'de ölüyor:
    #     faz #1: kutu görülen 0/64 kare | #2: 1/100 | #4: 0/59
    # DİKKAT: o anda conf 0.88-0.90 idi — model hedefi GÖRMEYE DEVAM
    # ediyordu. Kaybeden algı değil, aracın kendi manevrası.
    # Bu, yukarıda "ayar değil YAPI eksiği" diye tarif edilen durumun ta
    # kendisi; çaresi de orada yazıyor. Tavsiye edilen 0.30 ile açıldı.
    # Geri kapatmak: AVCI_IBVS_SONUM=0 (yedek: bbox_ibvs.py.yedek_*).
    SONUM_T = _env_f("AVCI_IBVS_SONUM", 0.30)  # s; 0 = kapalı, açık ~0.30
    SONUM_MAX_DEG = 30.0    # °; sönümleme teriminin tavanı (ters yöne itmesin)

    # ══ Ö5 · DÖNÜŞ-FARKINDA HIZ TAVANI ══
    # KULLANICI ÖLÇÜTÜYLE BULUNDU (2026-08-11): salınım artık hedefin
    # çerçevesindeki YANAL konumdan ölçülüyor (tools/salinim.py). 12 koşuda
    # SAĞA AŞIM 8-47 m — yani drone hedefin arkasında kalıyor ama YANINA
    # 8-47 metre savruluyor. "önde %" ise ~0: sorun boyuna değil, YANAL.
    #
    # FİZİK: dönüş yarıçapı R = V²/a. Aracın a tavanı g·tan(ANGLE_MAX 45°)
    # = 9.81 m/s². 18 m/s'de R = 33 m; hedef (Talon, 15 m/s, 60° yatış)
    # R = 13 m çiziyor. Drone 2.5 kat geniş yay çizdiği için DIŞARI taşıyor.
    # Yatışı artırmak denendi (Ö6) — çalışmadı, kanal zaten doymuş.
    # Geriye tek kaldıraç: HIZI KISMAK. R hızın KARESİYLE düşer:
    #     18 m/s → 33.0 m       12 m/s → 14.7 m       9 m/s → 8.3 m
    #
    # YASA: gereken yanal ivme = V·λ̇ ; bu a_max'ı aşıyorsa hız kısılır.
    #     v_tavan = DONUS_A / λ̇        (λ̇ = LOS azimut oranı, zaten ölçülü)
    # Yalnız KISAR; hızı asla artırmaz. Düz uçuşta λ̇≈0 → tavan sonsuz →
    # etkisiz (kullanıcının doğruladığı düz uçuş davranışı korunur).
    # ⚠ Taban: DONUS_V_MIN altına inmez — hedeften tamamen kopmayalım.
    # AVCI_IBVS_DONUS=0 → kapalı (varsayılan).
    DONUS_A = _env_f("AVCI_IBVS_DONUS", 0.0)     # m/s²; 0 = kapalı, açık ~9.0
    DONUS_V_MIN = _env_f("AVCI_IBVS_DONUS_VMIN", 10.0)   # m/s; hız tabanı

    # ══ T1b · DİKEY KANALDA ROLL/PITCH TELAFİSİ ══
    # NEDEN ŞİMDİ (2026-08-11 gece ölçümü): kesişim artık 10-40 cm'ye kadar
    # çözülüyor. İki uzun kayıtlı koşunun temas anı bileşenlerine ayrıldı:
    #     R01  yatay 0.33 m   dikey +0.05 m  → İSABET
    #     R02  yatay 0.12 m   dikey −0.11 m  → ıska (zarf sınırında)
    # İsabet zarfı yatayda ±0.65 m ama DİKEYDE +0.29 / −0.13 m — 5 KAT DAR.
    # Yani isabetle ıska arasındaki fark artık SANTİMETRE ve DİKEY eksende.
    #
    # T1a (yatay telafi) uygulanıp uçuşta doğrulandı; DİKEY, tek-değişken
    # kuralı gereği bilerek dokunulmadan bırakılmıştı. Ölçülen okuma hatası
    # dikeyde YATAYDAKİNDEN BÜYÜK: kullanıcının uçuşunda (log 091554) araç
    # 30° yatıktayken ham dikey okuma −22.1° derken telafili okuma +4.8°
    # diyordu — İŞARET TERS, en büyük sapma 33.1°.
    #
    # ÇÖZÜM: eps_elev, ham piksel farkı yerine los_seviye()'nin SEVİYE
    # çerçevesindeki yükseliş çıktısından kurulur. Nişan noktası da aynı
    # çerçeveye taşınır (CY_NISAN'ın seviye karşılığı), böylece hata tanımı
    # değişmez — yalnız okuma düzelir.
    # ⚠ DÜZ UÇUŞTA ETKİSİZ: roll=pitch=0'da los_seviye = piksel_elev, fark 0.
    # AVCI_IBVS_DIKEY_ROLL=0 → eski (telafisiz) dikey yol aynen geri gelir.
    DIKEY_ROLL = _env_f("AVCI_IBVS_DIKEY_ROLL", 0.0) >= 0.5

    # ══ T1c · TERMINAL DIKEY KANALINDA ROLL TELAFISI (2026-08-18) ══════════
    # ⛔⛔ T1b YARIM BAGLIYDI -- ve tam da EN COK GEREKEN yerde bagli DEGILDI.
    #   DIKEY_ROLL yalniz TUTUS dalindaki `eps_elev`i duzeltir. TERMINAL dali
    #   dikey nisani BASKA bir buyuklukten kurar:
    #        elev_atalet = piksel_elev(cy) + iris_pitch        (ROLL YOK)
    #   ve `vz_nisan = -v_dikey * tan(elev_atalet + lead_el)`. Yani hucumun
    #   SON metrelerindeki dikey komut roll'u HIC cikarmiyordu.
    #
    # NEDEN ONEMLI -- ve BEKLENTIYI ONCEDEN KUCULTEN OLCUM:
    #   Roll telafisinin yukselis hatasina kazanci yatisla buyuyor
    #   (n=20.944, truth menzille):
    #        |roll|  0-10 deg :  0.72 -> 0.50   (kazanc 0.23 deg)
    #        |roll| 10-20     :  1.89 -> 0.56   (kazanc 1.33)
    #        |roll| 20-30     :  8.87 -> 3.03   (kazanc 5.84)  ★
    #
    # ⛔⛔ AMA "TERMINALDE YATIS 50.7 DERECEYE CIKIYOR" IDDIASI BU DEPODAKI
    #   GUNCEL LOGLARDA DOGRULANMADI -- ve bu, T1c'nin beklenen kazancini
    #   DOGRUDAN kuculten bir olcumdur. Olculdu (bbox_ibvs_*.csv, ham
    #   `iris_roll_deg`, 2026-08-18):
    #        son 120 log / n=18.232 satir:
    #            TUM      : medyan 4.8, p90 12.4, p99 21.3, MAKS 24.5 deg
    #            TERMINAL : medyan 3.4, p90 10.6, p99 12.6, MAKS 16.3 deg
    #        ★ DEPODAKI BUTUN LOGLAR: 6.590 dosya / n=317.927 satir
    #            MAKS |roll| = 30.5 deg (bbox_ibvs_20260815_210242.csv)
    #            |roll| > 30 deg olan kare: 1 TANE (%0.0003)
    #   Yani 50.7 derece HIC OLMADI; tavan 30.5 ve o da tek karede.
    #   Yani 5.84 derecelik "20-30 bandi" kazancinin yasadigi bant PRATIKTE
    #   YOK. Gercekte olusan bantlardaki kazanc (sim/bbox_durum.py --veri,
    #   40 log / n=18.383 gercek tespit, truth ile kor kiyas, dz METRESI):
    #        |roll|  0-5  deg : 0.500 -> 0.465 m   (+0.035)
    #        |roll|  5-10     : 0.408 -> 0.306     (+0.103)
    #        |roll| 10-20     : 0.648 -> 0.270     (+0.378)  ★
    #        TERMINAL kareler : 0.497 -> 0.406     (+0.091)
    #   ⇒ DURUST BEKLENTI: terminalde medyan ~0.09 m, yatisli karelerde
    #     0.38 m'ye kadar. Isabet zarfi DIKEYDE +0.29/-0.13 m oldugu icin
    #     bu hala anlamlidir, ama "5.84 derece" manseti DEGILDIR.
    #   ⚠ KAZANC YATISLA BUYUYOR (0.035 -> 0.103 -> 0.378): sebep GERCEKTEN
    #     roll'dur. Buyumeseydi gerekce cokerdi -- kendini curutme kolu
    #     tezgahta kalicidir (bbox_durum.veri, "A2" tablosu).
    #
    # ⚠ AYNI FARK BICIMI (T1b ile birebir): telafi, yukselisin YERINE
    #   konmaz, SAPMA olarak EKLENIR:
    #        elev_atalet += los_seviye(roll)[1] - los_seviye(0)[1]
    #   Boylece roll=0'da terim TAM SIFIRDIR (bit-ayni) ve duzlemsel-kuresel
    #   farki (cx != CX'te olusan ayri bir kavram) BILEREK degismeden kalir.
    #   Dogrudan yerine koymak, B58 birim testinin yakaladigi hatadir.
    #
    # ⚠ KAPSAM: bu kapi terminal dikey kanalinin IKI girdisini birden duzeltir
    #   -- `elev_atalet` (nisan) ve `los_el` (yukselis hizi -> lead_el). Ikisi
    #   TEK KAVRAMDIR; yalniz birini baglamak T1b'nin dustugu hatanin ta
    #   kendisidir (bkz. Cfg.KOMUT_HIZALA_S'in "YARIM baglamak" notu).
    #
    # ⚠⚠ SIRA ZORUNLU -- KOMUT_HIZALA'DAN SONRA GELIR: roll telafisi BAYAT
    #   tutumla uygulandiginda YATAY hatayi BUYUTUYOR (olculdu: ham 4.45 ->
    #   telafili 5.45 deg; hizalama acikken 1.74 -> 1.29). Dikey eksende ayni
    #   isaret riski OLCULMEDI, ama sirayi bozmak icin sebep yok.
    #
    # MEKANIZMA KAPISI (logdan, tek kosuda):
    #   `term_roll_deg` sutunu TERMINAL karelerinde 0'dan AYRILMALI ve
    #   |iris_roll_deg| ile birlikte buyumeli. 0'a yapisiksa yama DEVREYE
    #   GIRMEMISTIR ve deney GECERSIZDIR.
    #   ⚠ TUTUS karelerinde de dolar (los_el yolu her karede isler) --
    #     terminal ayrimini `durum` sutunuyla yapin.
    # 0 = kapali (BIT-AYNI eski davranis).
    TERM_ROLL = _env_f("AVCI_IBVS_TERM_ROLL", 0.0) >= 0.5

    # ══ TERMINAL DIKEY KAPANMA — GORSEL FAZ (2026-08-17) ═══════════════════
    # gps_guidance.Cfg.TERM_DIKEY_M'in GORSEL karsiligi. Neden gerekli:
    # yakin gecislerin %87'si VISUAL fazda oluyor (olculdu, 228 CPA), yani
    # GPS tarafindaki rampa fiilen hic calismiyor.
    #
    # ⚠ ISARET SURPRIZI — OLCULDU (2026-08-17, ayna duzeltmesi SONRASI 228 CPA;
    #   olcum betigi: arac/dikey_ayristir.py):
    #   TUTUS yasasi hedefi CY_NISAN=301 px'te tutar. Bu GOVDE cercevesinde
    #   +4.89 derece yukselistir; DUNYA cercevesindeki karsiligi
    #       W0 = piksel_elev(CY_NISAN) + iris_pitch
    #   ve olculen pitch medyani -17.6 derece oldugu icin W0 = -12.7 derece.
    #   NEGATIF yukselis = hedef ufkun ALTINDA tutuluyor = ARAC HEDEFIN
    #   USTUNDEN geciyor. Olcum bunu birebir dogruladi:
    #       VISUAL CPA (r<=3 m, n=61): |dz| medyan 1.19 m, dz medyan +0.96 m,
    #                                  yalniz %10'u ALTTA
    #       taahhut aninda (7.4 m): tasarim +1.37 m, gercek +0.58 m
    #   Yani gorsel fazdaki dikey iska bir KONTROL hatasi degil, TASARIM
    #   ofsetidir -- GPS tarafindaki 1.553 m'lik ALT ofsetinin AYNASIDIR.
    #   (Ayna duzeltmesinden ONCE isaret tersti: VISUAL dz medyan -1.11 m,
    #   %77'si ALTTA. Sebep, kacak yaw dongusunun gorsel fazi 1.91 s'de
    #   kesmesi ve yasanin kendi dengesine hic ulasamamasiydi; izleme hatasi
    #   -1.79 m idi, simdi -0.84 m. Bkz. gorsel-yasa-ayna-hatasi.)
    #   ⛔ BUNUN SONUCU: "dikeye daha cok yetki ver" (ivme split) TEK BASINA
    #   gorsel fazi KOTULESTIRIR -- arac yanlis dengeye daha HIZLI varir.
    #   Benzetim (arac/dikey_ayristir.py --sim): yalniz split |dz| 1.09->1.04
    #   ama medyan +0.21 -> +0.64. Once bu rampa, sonra split.
    #
    # RAMPA: nisanin DUNYA yukselisi W0, menzille birlikte 0'a surulur:
    #       k = clamp(menzil / TERM_DIKEY_M, 0, 1);  W_etkin = W0 * k
    #   ve W_etkin GOVDE cercevesine geri cevrilip nisan PIKSELI kaydirilir.
    #   menzil >= esik -> k=1 -> CY_NISAN aynen (BIT-AYNI eski davranis).
    #   menzil -> 0    -> k=0 -> nisan es-irtifa (dunya yukselisi 0).
    #
    # BOYUTLANDIRMA (arac/dikey_ayristir.py --sim):
    #   olculen kapanma 9.87 m/s, dikey kanal olu 0.08 s + tau 0.64 s = 0.72 s
    #   -> kanal cevabinin menzil karsiligi 0.72 * 9.87 = 7.1 m.
    #   Rampa omru bunun 3 katini gecmezse komut yolda yenir -> esik >= 21 m.
    #   Ama 21 m'de rampa TUM gorsel faz boyunca acik kalir ve gokyuzu arka
    #   plani kaybolur (ofsetin var olma sebebi). Benzetim uzlasmayi veriyor:
    #       esik  KAPALI  8 m    12 m   20 m
    #       |dz|  1.04    0.93   0.82   0.66   (5 devir durumu ortalamasi)
    #   12 m ~ 1.22 s omur = kanal cevabinin 1.7 kati; |dz| kazanci 0.22 m.
    # ⚠ MENZIL KAYNAGI kutu vekilidir (MENZIL_PX_M/boyut) ve VEKIL SISIRIYOR:
    #   olculdu (n=8151, truth ile eslesmis) vekil/truth medyan 1.41; yakinda
    #   daha kotu (3-6 m'de olculen px*m 95, kodda 202.6 -> 2.13 kat).
    #   Yani BURAYA YAZILAN DEGER VEKIL METRESIDIR: 17 ~ 12 gercek metre.
    #   MENZIL_PX_M'i duzeltmek terminal kapisini ve kapanma kestirimini de
    #   kaydirir -> tek-degisken kurali geregi AYRI bir is.
    # 0 = KAPALI (varsayilan, bit-ayni eski davranis).
    TERM_DIKEY_M = _env_f("AVCI_IBVS_TERM_DIKEY", 0.0)   # m (kutu vekili menzili)

    # ══ DIKEY IVME BUTCESI (2026-08-17) ══════════════════════════════════
    # gps_guidance.Cfg.ACCEL_SPLIT ile AYNI kapi, AYNI gerekce: tek 3B tavan
    # yatay ivmeye yenilip dikeye kirinti birakiyor. Olculen (bu dosyanin
    # kendi logu, CPA oncesi 0.72 s, n=1459 tik):
    #     tiklerin %84.5'i 12 m/s^2 tavaninda
    #     tavandaki tiklerde dikeye kalan |d(vz)/dt|: medyan 1.52, p90 5.97
    # ⚠ GPS FAZINDAN DAHA IYI: orada dikeye kalan medyan 0.21-0.79 m/s^2.
    #   Yani split'in GORSEL fazdaki beklenen kazanci GPS fazindakinden
    #   KUCUKTUR; gorsel fazin asil acigi yukaridaki TASARIM ofsetidir.
    #   Yine de tavan %84.5 doygun oldugu icin baglayici bir kisittir.
    # ⚠ VARSAYILAN KAPALI: split tek tavanla BIREBIR ayni davranisa
    #   ayarlanamaz (12/10 split = 15.6 m/s^2 bileske). Once A/B ile kanitla.
    ACCEL_SPLIT = _env_f("AVCI_ACCEL_SPLIT", 0.0) >= 0.5
    MAX_ACCEL_V = _env_f("AVCI_MAX_ACCEL_V", 10.0)   # m/s² — DIKEY (split acikken)

    # ══ D1 · DIKEY NISAN UFKA BAGLI  (2026-08-17, "faza gecince dikeyi
    #        tutmuyor") ══════════════════════════════════════════════════
    # KULLANICI SIKAYETI: devirden sonra irtifa tutulmuyor.
    #
    # OLCUM (arac/devir_sicrama.py; veri/hedef_iz truth x bu dosyanin logu,
    # ayni monotonic saat, n=295 devir, taze paket %100, ayna duzeltmesi
    # SONRASI). Devir aninda:  R=13.9 m, dz-hz = -1.48 m (%99 ALTTAYIZ),
    # govde pitch = -10.75 deg, eps_elev = -14.7 deg (yasa "TIRMAN" diyor).
    # Devirden SONRA truth dz-hz:
    #     -1.45 (t=0) -> -0.21 (1.25 s) -> +0.64 (1.75 s) -> +1.55 (2.5 s)
    # yani SIFIRDAN GECIP USTE CIKIYOR ve orada kaliyor. "Tutmuyor" TAM
    # OLARAK BU: hedefe gore isaret degistiren, hic oturmayan bir dikey.
    #
    # KOK NEDEN — YASANIN DENGE NOKTASI YANLIS YERDE, ve PITCH'E BAGLI:
    #   vz = K_VZ*V_NOM*eps_elev,  eps_elev = atan((cy - CY_NISAN)/FY)
    #   Denge cy = CY_NISAN. Bunun DUNYA yukselisi
    #       W0 = piksel_elev(CY_NISAN) + iris_pitch = 4.888 deg + pitch
    #   pitch = -10.75 -> W0 = -5.86 deg -> hedefi 5.86 derece ALTIMIZDA
    #   tutmak istiyoruz -> denge  D* = -R*tan(W0) = +R*0.1026, yani
    #   R=14 m'de HEDEFIN 1.4 m USTUNDE. Olculen +1.55 m ile birebir.
    #   Zaman sabiti tau = R/(K_VZ*V_NOM) = R/6 = 2.3 s; gorsel faz medyan
    #   omru ~3 s -> hata FAZ BOYUNCA OTURMUYOR.
    # ⚠ VE KENDINI BESLIYOR: yasa yatayda hizlanma emrederse arac burnunu
    #   asagi egiyor (olculdu: devirde -10.8 -> +0.75 s'de -16.1 deg), W0
    #   daha da negatif oluyor, denge YUKARI kaciyor. Yatay kanal dikey
    #   kanala SAHTE bir "tirman" komutu enjekte ediyor.
    #
    # DUZELTME: nisanin GOVDE pikselini degil, DUNYA yukselisini sabitle.
    #     cy_nisan = elev_piksel(UFUK_ELEV - iris_pitch)
    # UFUK_ELEV=0 -> her menzilde D* = 0 (ES IRTIFA) ve pitch kuplaji YOK.
    # >0 vermek "hedefin bu kadar derece ALTINDA kal" demektir (gokyuzu
    # arka plani payi); 0 tam es irtifa.
    #
    # TEZGAH (sim/devir.py, n=240, 4 senaryo, gercek komut() cagriliyor):
    #     aday                 |dz|@2s   |dz|@3s   en yakin
    #     T0 taban               0.55      0.75      5.82 m
    #     V1 ufuk0               0.62      0.24 (-68%)  5.84
    #     V6 ufuk+hiz+K_VZ0.9    0.19      0.09 (-88%)  4.70
    # ⚠ MEKANIZMA SINAMASI (bu kapinin ASIL kaniti): K_VZ'yi TEK BASINA
    #   0.5->0.9 yapmak |dz|@2s'i %155 KOTULESTIRDI (denge yanlisken daha
    #   cok yetki, aracı yanlis yere daha hizli goturur -- MEMORY'deki
    #   ACCEL_SPLIT dersinin AYNISI). Ayni degisiklik ufuk kapisi ACIKKEN
    #   %66 IYILESTIRDI. Isaretin donmesi teshisi dogruluyor.
    # ⚠ MEKANIZMA KAPISI: kapi ACIKKEN CSV'deki `cy_nisan` sutunu 301'den
    #   SAPMALI ve pitch ile DEGISMELI; KAPALIYKEN 301'de SABIT kalmali.
    #   Ikisi de saglanmiyorsa deney GECERSIZDIR.
    #
    # ══ UCUSTA A/B ILE KAZANDI (2026-08-17) -> VARSAYILAN ACIK ═══════════
    # arac/recete_gecis.json, her kol 12 dk, hukum arac/gecis_hukum.py:
    #     ayar            |dz|   dz(isaretli)  CPA med  <2 m  <3 m  temas
    #     G0 taban        1.39      +1.10       3.42    %25   %45     2
    #     G1 ufuk         1.05      -0.83       2.74    %33   %57     0
    #     G3 ufuk+hiz     0.84      -0.53       2.84    %41   %56     5   <- SECILEN
    #     G4 +K_VZ0.9     0.69      -0.24       3.64    %24   %35     3
    #     G5 K_VZ TEK     1.54      +1.47       4.69     %6   %19     0
    # ⭐ OLUMSUZ KONTROL (G5: dikey kazanci TEK BASINA artir, denge
    #   DUZELTILMEDEN) 5/5 olcude KOTULESTI ve dz isareti +1.47 m ile
    #   TABANDAN DA YUKARI cikti. Tezgahin ongorusu (|dz|@2s %155 kotu)
    #   ucusta dogrulandi -> "kok neden YANLIS DENGE NOKTASI, yetersiz
    #   yetki DEGIL" teshisi KANITLANDI.
    # ⚠ G4 ALINMADI: dikeyi daha da iyilestiriyor (|dz| 0.69) ama CPA 3.64 ve
    #   <2 m %24 ile TABANDAN KOTU -- K_VZ dikeyi YATAYA yediriyor. Bu yuzden
    #   K_VZ varsayilani 0.5'te BIRAKILDI (bkz. Cfg.K_VZ).
    # ⚠ G6 (UFUK_ELEV=2, gokyuzu arka plani payi) HER OLCUDE KAYBETTI
    #   (CPA 5.53, <2 m %12) -> UFUK_ELEV varsayilani 0 KALIR. Tezgahin
    #   "arka plan cezasi" endisesi ucusta DOGRULANMADI.
    # Kapatmak: AVCI_IBVS_DIKEY_UFUK=0 (kapaliyken cy_nisan bit-ayni CY_NISAN).
    # Yedek: yedek/G3_ONCESI_20260817_164045, yedek/g3_kalici_20260817_164956
    DIKEY_UFUK = _env_f("AVCI_IBVS_DIKEY_UFUK", 1.0) >= 0.5
    UFUK_ELEV_DEG = _env_f("AVCI_IBVS_UFUK_ELEV", 0.0)   # derece; + = altta kal

    # ══ Y1 · HIZ INTEGRALININ SICAK BASLANGICI  (2026-08-17, "yatayda da
    #        tutmuyor") ══════════════════════════════════════════════════
    # run_bbox_ibvs hiz_I'yi |ff_hiz| ile sicak baslatiyor; ff_hiz GPS
    # fazinin hedef HIZ KESTIRIMIDIR (supervisor.py:930 `tgt_vx/vy/vz`).
    #
    # OLCUM (n=299 devir, hedefin GERCEK hizi truth izden):
    #     ff_hiz - V_hedef :  p10 -8.56   medyan -0.50   p90 +1.17  m/s
    #     %62'si hedefin hizinin ALTINDA, %33'unde |hata| > 3 m/s
    #     RMS hata 4.63 m/s
    # SONUCU (v_los = hiz_I + DPP menzil terimi):
    #     devirlerin %28'inde v_los ILK KAREDE hedefin hizindan DUSUK
    #     -> kapanma MATEMATIKSEL OLARAK IMKANSIZ.
    # SAHA ETKISI: ff kestirimi kotu (|hata|>3) olan fazlarda EN YAKIN
    #     MENZIL 11.85 m, iyi olanlarda 3.95 m.
    # ⚠ CURUTME DENENDI, BASARISIZ: (a) hedefin donus hizi ile korelasyon
    #   +0.009 (yok) ve donus kusaklari ayri ayri sabitlendiginde etki
    #   KALIYOR (10.5/3.0, 13.0/4.0, 12.5/5.0 m); (b) devir menzili
    #   12-18 m'ye sabitlendiginde de KALIYOR (12.01 vs 3.04 m, n=173).
    #
    # DUZELTME: devir aninda ARACIN KENDI hizi da bir kestirimdir -- GPS
    # fazinda hedefi kovaladigimiz icin kendi hizimiz hedefin hizina
    # yakindir (olculdu: kendi hiz - V_hedef medyan +1.55 m/s). Taban olarak
    # kullanilir; ff daha buyukse ff kalir (YALNIZ YUKARI ceker).
    #     hiz_I = clamp(max(|ff|, |v_kendi| - HIZ_SICAK_PAY), I_MIN, I_MAX)
    # KESTIRIM KALITESI (ayni n=299, hedefin gercek hizina gore RMS):
    #     ff tek basina                 4.63 m/s   (%33'u >3 m/s)
    #     max(ff, kendi-1.0)            2.54       (%26)
    #     max(ff, kendi-1.5)            2.37       (%21)   <- secilen
    #     max(ff, kendi-2.0)            2.27       (%20)
    # ⚠ D0 UYUMLU: kullanilan sey ARACIN KENDI hiz sensorudur (get_iris),
    #   CANLI GPS DEGIL; zaten ivme sinirlayicinin baslangici icin ayni
    #   kare okunuyor (asagida vx_p/vy_p). Tek sayi, devirde BIR KEZ.
    # ⚠ MEKANIZMA KAPISI: kapi acikken baslangic ciktisindaki "integral
    #   sicak baslangic" satiri KAYNAK olarak 'kendi' yazmali ve CSV'nin
    #   ILK satirindaki hiz_I |ff|'ten BUYUK olmali.
    #
    # ══ UCUSTA A/B ILE KAZANDI (2026-08-17) -> VARSAYILAN ACIK ═══════════
    # G3 (ufuk + hiz sicak) tabana gore: |dz| 1.39 -> 0.84 m, <2 m gecis
    # %25 -> %41, temas 2 -> 5 (bkz. Cfg.DIKEY_UFUK'teki tam tablo).
    # G2 (hiz sicak TEK BASINA): CPA medyani 3.42 -> 2.61 m, <3 m %45 -> %57.
    # ⚠⚠ KAPI SEYREK BAGLIYOR VE BU BEKLENEN: yama YALNIZ YUKARI ceker
    #   (max(ff, kendi-pay)), yani ff zaten iyiyse HIC dokunmaz. Ucusta
    #   mekanizma kapisi ('kaynak=kendi') fazlarin YALNIZ %8'inde tetiklendi.
    #   Bu bir SIZINTI DEGIL, tasarim: olculen "ff kestirimi kotu" orani
    #   %33 iken bunun ancak bir kismi (kendi hiz - 1.5) esigini asiyor.
    #   ⚠ DOLAYISIYLA G2'nin CPA kazanci %8'lik bir alt kumeden geliyor ->
    #   KOL BASINA ETKI BUYUK, ORTALAMAYA ETKI KUCUK gorunur. Bu kapinin
    #   isi ORTALAMAYI oynatmak degil, kapanmanin IMKANSIZ oldugu fazlari
    #   kurtarmaktir. Ileride olculecek dogru olcut: 'kaynak=kendi' olan
    #   fazlarin CPA'si vs G0'daki esdeger (ff'i kotu) fazlarin CPA'si.
    # <0 = KAPALI; >=0 ise m/s cinsinden pay. Kapatmak: AVCI_IBVS_HIZ_SICAK=-1
    HIZ_SICAK_PAY = _env_f("AVCI_IBVS_HIZ_SICAK", 1.5)   # m/s

    # ══ KES · KUTUDAN TAM DURUM KESTIRIMI  (2026-08-18) ═══════════════════
    # ⛔ BU BLOK GUDUME HIC DOKUNMAZ -- SALT GOZLEM. Hicbir komut, hicbir
    #   kapi, hicbir esik bu kestirimden beslenmez. Tek yaptigi CSV'ye
    #   sutun yazmaktir. Sebebi acik: kestirimin SAHA dogrulugu HENUZ
    #   OLCULMEDI; olculmeden yasaya baglamak bu depodaki en pahali hata
    #   sinifidir (bkz. ayna hatasinin UC KEZ tekrarlamasi).
    #
    # NE HESAPLAR (kullanicinin istegi: "bbox'tan tam hesaplama --
    # irtifa, hiz, yon, aci kestirimi"):
    #     ACI    : az / el  (SEVIYE cercevesi, roll+pitch cikarilmis)
    #     MENZIL : yasanin o an kullandigi model (menzil_kutudan)
    #     IRTIFA : dz = R sin(el)   (+ = hedef YUKARIDA)
    #     KONUM  : (N, E, D) bagil ofset
    #     HIZ    : v_hedef = v_KENDI + d(ofset)/dt   <- pencere egimi
    #     YON    : hedefin ROTASI (kursu) ve YER HIZI
    #     ASPECT : hedefin burnu ile LOS arasindaki aci (L_etkin'in girdisi)
    #
    # ⚠ D0 (yarisma kurali) TEMIZ: girdiler yalniz tespit kutusu + aracin
    #   KENDI durus/hiz sensoru (get_iris). Hedefin GPS'i HIC okunmaz --
    #   dongunun ona erisimi zaten YOKTUR.
    #
    # ⚠⚠ HATA BUTCESI ONCEDEN SOYLENIYOR (turetme, bkz. bbox_geometri.
    #   egim_pencere docstring'i). Kestirim EKSENE GORE COK FARKLI:
    #       TEGET bilesen  (aciden)   : 1 deg aci hatasi, 10 m'de 0.17 m
    #                                   -> 0.4 s pencerede ~0.4 m/s
    #       RADYAL bilesen (menzilden): %19 menzil hatasi, 10 m'de 1.9 m
    #                                   -> 0.4 s pencerede ~5 m/s  ⛔ COP
    #   ⇒ `kest_rota_deg` (yon) kullanilabilir, `kest_vh_ms`in RADYAL
    #     bileseni GUVENILMEZ. Kim ki bunu bir kapiya baglar, once olcsun.
    # ⚠ VE MENZILDEKI SISTEMATIK YANLILIK TUREVDE AYNEN KALIR:
    #   R_kest = (1+b)R  ->  bagil hiz da (1+b) katidir. MENZIL_PX_M=202.6'nin
    #   olculen b=+%33'u kapanma hizini da %33 sisirir. Bu, menzil kolunun
    #   IKINCI (bagimsiz) mekanizma kapisidir.
    #
    # MEKANIZMA KAPISI: kapi acikken `kest_R_m`, `kest_dz_m`, `kest_az_deg`
    #   DOLU olmali; `kest_n` >= 3 olan karelerde `kest_vh_ms` ve
    #   `kest_rota_deg` de dolmali. Hepsi bossa yama DEVREYE GIRMEMISTIR.
    #   ⚠ CAPRAZ KILIT: `kest_dz_m` ile `eps_elev_deg` ayni kareye bakiyor;
    #     isaretleri TERS olmali (hedef yukarida -> eps_elev negatif).
    # 0 = kapali (varsayilan; tek satir bile calismaz).
    KESTIRIM = _env_f("AVCI_IBVS_KESTIRIM", 0.0) >= 0.5
    # Hiz penceresi (s). Kisa -> gurultulu; uzun -> hedefin manevrasi silinir.
    # Olculen hedef donus hizi medyan 6.55 deg/s: 0.40 s'de 2.6 derece kurs
    # bulanikligi -- kabul edilebilir. 1.0 s'de 6.5 derece -> fazla.
    KESTIRIM_PENCERE_S = _env_f("AVCI_IBVS_KESTIRIM_PENCERE", 0.40)   # s

    # ── KUTU GEÇERLİLİĞİ ──
    CONF_MIN = _env_f("AVCI_IBVS_CONF", 0.35)   # bunun altı kutu = yok sayılır
    BOYUT_MIN = 6.0                # px; bundan küçük kutu güvenilmez (gürültü)


_LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs")

_CSV_ALANLAR = [
    "t", "dt", "durum", "cx", "cy", "w", "h", "boyut", "conf",
    "eps_yaw_deg", "eps_yaw_ham_deg", "eps_elev_deg", "eps_elev_ham_deg",
    "iris_roll_deg", "iris_pitch_deg", "iris_yaw_deg",
    "boyut_hata", "hiz_I", "v_los", "kacis_ek", "gecikme_s", "eps_hiz_deg", "sonum_deg", "donus_tavan", "lead_az_deg", "los_hiz_az", "los_hiz_el",
    "pn_n", "psi_v_deg", "pn_sapma_deg", "pn_ornek", "eps_hizi_deg", "kopru",
    "vx_cmd", "vy_cmd", "vz_cmd", "yaw_cmd_deg", "kayip_sayac",
    # ⚠ SONA eklendi (2026-08-17): okuyucular DictReader/isimle aliyor, bozulmaz.
    # MEKANIZMA KAPISI: TERM_DIKEY rampasi devreye girdiyse bu sutun
    # CY_NISAN'dan (301) SAPMALI. Sapmiyorsa yama calismamistir.
    "cy_nisan",
    # ── MANEVRA TESHISI + M1/M2 MEKANIZMA KAPILARI (2026-08-17) ──────────
    # w_talep_deg : yasanin ISTEDIGI hiz-yonu donus hizi (kirpilmadan once)
    # w_tavan_deg : o karedeki tavan = MAX_ACCEL / v_los   (a/V)
    # w_uyg_deg   : UYGULANAN (kirpilmis) donus hizi
    #   -> |w_talep| > w_tavan olan kare orani DOYGUNLUKTUR. Taban olcum:
    #      B_ayna_DPP %54.1 (terminalde %42.5). M1 bunu DUSURMELI.
    # donus_kapi_v: M1'in koydugu hiz tavani (bos = kapali/baglamadi)
    # arac_lead_deg: M2'nin cikisa ekledigi ongoru acisi (0 = kapali)
    "w_talep_deg", "w_tavan_deg", "w_uyg_deg", "donus_kapi_v", "arac_lead_deg",
    # ── Y2 (yaw bayatligi) + M-KAL (menzil) MEKANIZMA KAPILARI (2026-08-17)
    # hizala_deg   : komuttan cikarilan bayatlik telafisi (bkz. KOMUT_HIZALA_S)
    #                ⚠ 0'a YAPISIKSA yama devreye girmemistir -> deney gecersiz.
    # yaw_hizi_dps : kapinin girdisi. hizala_deg ile ISARETI AYNI olmali
    #                (hizala = K*yaw_hizi) ve komuttan CIKARILDIGI icin
    #                yaw_cmd_deg − (iris_yaw_deg + eps_yaw_deg) = −hizala_deg.
    # menzil_m     : yasanin kullandigi menzil (MENZIL_PX_M/KW/OFS modeli)
    # menzil_term_m: TERMINAL nisan kapisinin kullandigi menzil.
    #                ⚠ IKISI FARKLIYSA "MENZIL IKIZI" hala acik demektir.
    #                Taban kosuda oran 202.6/160.0 = 1.2663 SABIT olmali.
    "hizala_deg", "yaw_hizi_dps", "menzil_m", "menzil_term_m",
    # ── T1c (terminal dikey roll) MEKANIZMA KAPISI (2026-08-18) ───────────
    # term_roll_deg: TERMINAL dikey kanalina EKLENEN roll sapmasi (derece).
    #   ⚠ 0'a YAPISIKSA AVCI_IBVS_TERM_ROLL devreye girmemistir -> gecersiz.
    #   |iris_roll_deg| ile birlikte buyumeli; roll=0'da TAM 0 olmali.
    "term_roll_deg",
    # ── KES · TAM DURUM KESTIRIMI (SALT GOZLEM, bkz. Cfg.KESTIRIM) ────────
    # kest_R_m     : yasanin menzil modeliyle kutudan menzil
    # kest_dz_m    : + = hedef YUKARIDA  (caprazi: eps_elev_deg ile TERS isaret)
    # kest_az_deg  : SEVIYE kerterizi (burna gore), roll+pitch cikarilmis
    # kest_el_deg  : SEVIYE yukselisi
    # kest_vh_ms   : hedefin YER hizi (v_kendi + d(ofset)/dt)
    #                ⚠ RADYAL bileseni menzil yanliligini AYNEN tasir
    # kest_vz_ms   : hedefin dikey hizi (+ = NED'de ASAGI)
    # kest_rota_deg: hedefin kursu (kuzeyden saat yonu)
    # kest_aspect_deg: 180 = tam kuyrugunda, 90 = borda, 0 = karsidan
    # kest_n       : hiz penceresindeki ornek sayisi (<3 -> hiz bos)
    "kest_R_m", "kest_dz_m", "kest_az_deg", "kest_el_deg",
    "kest_vh_ms", "kest_vz_ms", "kest_rota_deg", "kest_aspect_deg", "kest_n",
]


def piksel_elev(cy, cfg=Cfg):
    """Kutunun dikey pikselinden GÖVDE çerçevesinde LOS yükselişi (rad, yukarı+).

    Kamera gövdeye KAMERA_TILT (25°) yukarı tilt'li. cy=CY (kadraj merkezi)
    → boresight → yükseliş = +25°. cy büyüdükçe (kadrajda aşağı) yükseliş azalır.
    Doğrulama: cy = CY + FY·tan(25°) ≈ 318 → yükseliş ≈ 0 (seviye hedef).
    """
    tilt = math.radians(GeoCfg.KAMERA_TILT_DEG)
    b = (cy - geo.CY) / geo.FY
    return math.atan2(math.sin(tilt) - math.cos(tilt) * b,
                      math.cos(tilt) + math.sin(tilt) * b)


NISAN_KAYMA_MAX = 120.0    # px; dikey nişan rampasının kaydırabileceği en çok


def elev_piksel(elev, cfg=Cfg):
    """piksel_elev'in TERSI: GÖVDE yükselişi (rad) → cy pikseli.

    Türetme (piksel_elev'i b için çözerek):
        tan(e) = (sin t − cos t·b) / (cos t + sin t·b)   ⇒   b = tan(t − e)
    yani  cy = CY + FY·tan(KAMERA_TILT − e).
    Doğrulama: e = piksel_elev(301) = +4.89° → cy = 301 (tur-dönüş).

    ⚠ tan patlamasına karşı (t − e) ±70° ile sınırlanır; oradan öteye nişan
    zaten kadrajın çok dışındadır ve hata terimi doygun demektir.
    """
    tilt = math.radians(GeoCfg.KAMERA_TILT_DEG)
    a = clamp(tilt - elev, -math.radians(70.0), math.radians(70.0))
    return geo.CY + geo.FY * math.tan(a)


def menzil_olcek(boyut, cfg=Cfg, w=None):
    """Menzil modelinin ETKIN BOYUTU (px) — R = K / menzil_olcek(...).

    Varsayilanda `boyut` = √(w·h)'yi AYNEN dondurur, yani bit-ayni.
    Kapilar acikken model degisir:
        MENZIL_KW  > 0 -> etkin boyut = w        (yalniz genislik)
        MENZIL_OFS != 0 -> etkin boyut = boyut − OFS   (sabit kutu payi)

    ⚠ NEDEN AYRI FONKSIYON: kapanma hizi ṙ = R·(ds/dt)/s formulunun `s`'i
    menzil modelinin `s`'iyle AYNI olmak zorunda. Aksi halde R'yi genislikten,
    turevi √(w·h)'den alan tutarsiz bir ṙ cikar (ve o ṙ dikey butceyi,
    terminal kapisini ve KACIS_KD'yi besliyor).
    """
    kw = float(getattr(cfg, "MENZIL_KW", 0.0) or 0.0)
    if kw > 0.0 and w is not None and w > 1e-6:
        return float(w)
    ofs = float(getattr(cfg, "MENZIL_OFS_PX", 0.0) or 0.0)
    return float(boyut) - ofs if ofs != 0.0 else float(boyut)


def menzil_kutudan(boyut, cfg=Cfg, w=None, terminal_kapi=False):
    """Kutu boyutundan menzil (m) — YASADAKI TEK KAYNAK.

    ⛔ 2026-08-17 ONCESI: bu hesap kodun IKI YERINDE, IKI FARKLI SABITLE
       yapiliyordu — yasa `Cfg.MENZIL_PX_M`=202.6, terminal nisan kapisi ise
       satir ici HARDCODED 160.0. Ayni kareye iki farkli menzil: kapi ile
       yasanin arasi %27. Artik ikisi de buradan gecer; tutarsizlik
       ANCAK bilerek (MENZIL_TERM_PX_M ile) kurulabilir.

    terminal_kapi=True -> MENZIL_TERM_PX_M (varsayilan 160.0) kullanilir.
    ⚠ MENZIL_KW acikken TERMINAL DE ayni modeli kullanir: tek model, tek
      menzil. Ikiz yapisal olarak kapanir.

    ⚠ KIRILGANLIK: MENZIL_OFS>0 iken kucuk kutuda payda 0'a yaklasip R
      patlar. bbox_geometri.menzil_ofsetli bunu yaziyor: `boyut > c + 3 px`
      kapisi koyun. Yasada BOYUT_MIN=6 px zaten var; OFS'i 3'ten buyuk
      POZITIF vermeyin (onerilen deger NEGATIF: −4.11).
    """
    s = menzil_olcek(boyut, cfg, w)
    if float(getattr(cfg, "MENZIL_KW", 0.0) or 0.0) > 0.0 and w is not None \
            and w > 1e-6:
        return float(cfg.MENZIL_KW) / max(s, 1e-6)
    k = (float(getattr(cfg, "MENZIL_TERM_PX_M", 160.0)) if terminal_kapi
         else float(cfg.MENZIL_PX_M))
    return k / max(s, 1e-6)


def nisan_cy(iris_pitch, boyut, cfg=Cfg, w=None):
    """Dikey nişan pikseli — menzille kapanan TERMİNAL rampası dahil.

    Bkz. Cfg.TERM_DIKEY_M (gerekçe, ölçüm ve boyutlandırma orada).
    Rampa kapalıyken (varsayılan) DÖNÜŞ TAM OLARAK cfg.CY_NISAN'dır — eski
    davranış bit-aynı korunur.
    """
    # ── D1: UFKA BAGLI NISAN (bkz. Cfg.DIKEY_UFUK) ───────────────────────
    # Kapali (varsayilan) -> taban nisan CY_NISAN, yani BIT-AYNI eski yol.
    # Acik -> nisanin DUNYA yukselisi UFUK_ELEV_DEG'e sabitlenir; govde
    # pikseli pitch ile birlikte kayar. Boylece dikey denge noktasi
    # D* = -R*tan(W0) menzilden VE pitch'ten bagimsiz olur.
    taban = cfg.CY_NISAN
    if getattr(cfg, "DIKEY_UFUK", False):
        _uf = math.radians(float(getattr(cfg, "UFUK_ELEV_DEG", 0.0) or 0.0))
        taban = clamp(elev_piksel(_uf - iris_pitch, cfg),
                      cfg.CY_NISAN - NISAN_KAYMA_MAX,
                      cfg.CY_NISAN + NISAN_KAYMA_MAX)

    td = float(getattr(cfg, "TERM_DIKEY_M", 0.0) or 0.0)
    if td <= 0.0 or boyut <= 1e-6:
        return taban
    menzil = menzil_kutudan(boyut, cfg, w)    # ⚠ VEKIL (bkz. Cfg.TERM_DIKEY_M)
    k = clamp(menzil / td, 0.0, 1.0)
    if k >= 1.0:
        return taban                          # uzakta: hiç dokunma
    # nişanın DÜNYA yükselişi k ile 0'a sürülür, sonra gövdeye geri çevrilir
    # ⚠ RAMPA TABANDAN baslar: ufuk kapisi acikken w0 zaten ~0 oldugu icin
    #   rampa dogal olarak etkisizlesir (iki kapi CAKISMAZ).
    w0 = piksel_elev(taban, cfg) + iris_pitch
    cy = elev_piksel(w0 * k - iris_pitch, cfg)
    # ⚠ PATLAMA SINIRI: nişanı CY_NISAN'dan en çok ±NISAN_KAYMA_MAX px kaydır.
    # Ölçülen pitch bandında (p10 −21.2° … p90 0°) kayma yalnız 35-45 px, yani
    # sınır normal uçuşta HİÇ bağlamaz; yalnız kurtarma gibi aşırı duruşlarda
    # nişanın kadrajdan büsbütün kaçmasını engeller.
    return clamp(cy, cfg.CY_NISAN - NISAN_KAYMA_MAX,
                 cfg.CY_NISAN + NISAN_KAYMA_MAX)


def los_seviye(cx, cy, roll, pitch, cfg=Cfg):
    """Piksel + aracın KENDİ duruşu → SEVİYE çerçevesinde (azimut, yükseliş).

    Neden gerekli: bkz. Cfg.ROLL_TELAFI. atan((cx−CX)/FX) KAMERA çerçevesinin
    azimutudur; araç yattığında bu, seviye çerçevesindeki gerçek azimut DEĞİLDİR
    (30-40° yatışta 11-14° sapma ölçüldü).

    Zincir — üç adım, hepsi drone'un kendi sensörüyle (canlı GPS YOK):
      1) piksel → kamera ışını      [sağ, aşağı, ileri] = (x, y, 1)
      2) kamera → GÖVDE (FRD)       kamera KAMERA_TILT° yukarı vidalı: Ry(−tilt)
      3) gövde → SEVİYE (yaw hariç) Ry(pitch)·Rx(roll) ile duruş çıkarılır

    Dönüş: (azimut, yükseliş) rad — azimut BURNA GÖRE sağ+, yükseliş yukarı+.
    Yani çağıran seviye çerçevesindeki mutlak yönü `iris_yaw + azimut` ile alır.

    Doğrulama (roll=pitch=0, cx=CX): azimut=0 ve yükseliş = piksel_elev(cy).
    """
    x = (cx - geo.CX) / geo.FX          # kamera sağ  (CX = ana nokta)
    y = (cy - geo.CY) / geo.FY          # kamera aşağı
    t = math.radians(GeoCfg.KAMERA_TILT_DEG)
    ct, st = math.cos(t), math.sin(t)
    # 2) kamera ışını → gövde FRD
    bx = ct + st * y                    # ileri
    by = x                              # sağ
    bz = ct * y - st                    # aşağı
    # 3) gövde → seviye: önce roll, sonra pitch geri alınır
    cr, sr = math.cos(roll), math.sin(roll)
    y1 = by * cr - bz * sr
    z1 = by * sr + bz * cr
    cp, sp = math.cos(pitch), math.sin(pitch)
    x2 = bx * cp + z1 * sp
    z2 = -bx * sp + z1 * cp
    return math.atan2(y1, x2), math.atan2(-z2, math.hypot(x2, y1))


def komut(cx, cy, w, h, iris_yaw, hiz_I, dt, cfg=Cfg, terminal=False,
          los_hiz=(0.0, 0.0), iris_pitch=0.0, iris_vz=0.0,
          kapanma=None, iris_roll=0.0, yaw_hizi=0.0, psi_v=None,
          eps_hizi=0.0, v_kapi=None):
    """IBVS kontrol yasası — SAF TAKİP + PI hız (MAVLink yok, CANLI GPS yok).

    Girdi:
      (cx,cy,w,h) : tespit kutusu — TEK canlı kaynak
      iris_yaw    : drone kendi yaw'ı (rad) — kendi sensörü
      hiz_I       : hız integralinin o anki değeri (m/s) — çağıran taşır
      dt          : adım süresi (s)
    Çıktı: (vx_ned, vy_ned, vz, yaw_cmd, hiz_I_yeni, tani)

    Hız DAİMA LOS (burun) yönünde: hedef dönünce hız vektörü de döner —
    dondurulmuş NED taşıyıcının yana savurma hatası yapısal olarak imkânsız.
    """
    boyut = math.sqrt(max(w, 0.0) * max(h, 0.0))

    # YAW: yatay açı hatası → burun hedefe
    # ROLL/PITCH TELAFİSİ (bkz. Cfg.ROLL_TELAFI): araç yattığında kamera
    # azimutu seviye azimutu DEĞİLDİR. Telafili yol pikseli aracın kendi
    # duruşuyla seviye çerçevesine döndürür; hız vektörü de bu yöne gider.
    eps_yaw_ham = math.atan((cx - cfg.CX_NISAN) / geo.FX)
    if cfg.ROLL_TELAFI:
        eps_yaw, _ = los_seviye(cx, cy, iris_roll, iris_pitch, cfg)
    else:
        eps_yaw = eps_yaw_ham
    # LEAD ÖLÇEĞİ: kalan süreyle (≈menzille) söner — bkz. Cfg.LEAD_SONUM.
    # boyut ∝ 1/menzil olduğu için REF/boyut ≈ menzil/menzil_REF.
    lead_olcek = 1.0
    if cfg.LEAD_SONUM and boyut > 1e-6:
        lead_olcek = clamp(cfg.BOYUT_REF / boyut, 0.0, 1.0)
    lead_sure = cfg.LEAD_SURE * lead_olcek
    lead_az = 0.0
    # LEAD: nişanı atalet LOS dönüş hızıyla öne al (bkz. Cfg.LEAD_SURE).
    # M3: kapı kalktı — artık kutu olan her karede (bkz. Cfg.LEAD_ERKEN).
    # M4 (2026-08-15): SEYİR fazına AYRI, KÜÇÜK tavan. Gerekçe LEAD_ERKEN
    # bloğundaki ölçümün kendi reçetesi: "YÖN doğru, GENLİK yanlış".
    # Terminal için ayarlanmış 25° tavan seyirde sürekli uygulanınca kalıcı
    # nişan sapması yapıyordu (karelerin %27'si tavanda, medyan 18.7°) ve
    # araç kesişmek yerine hedefi GÖLGE ediyordu (paralel koşu).
    # Terminal tavanı 25°'de AYNEN kalır; yalnız seyir fazı kısılır.
    if terminal or cfg.LEAD_ERKEN:
        _tavan = (cfg.LEAD_MAX_DEG if terminal else cfg.LEAD_MAX_SEYIR_DEG)
        lead_az = clamp(lead_sure * los_hiz[0],
                        -math.radians(_tavan), math.radians(_tavan))
    # Ö9 SÖNÜMLEME: aracın kendi dönüş hızı komutu geri çeker (bkz. SONUM_T)
    sonum = 0.0
    if cfg.SONUM_T > 0.0:
        sonum = clamp(cfg.SONUM_T * yaw_hizi,
                      -math.radians(cfg.SONUM_MAX_DEG),
                      math.radians(cfg.SONUM_MAX_DEG))
    # ══ Y2 · KOMUT YOLU ZAMAN HIZALAMASI (bkz. Cfg.KOMUT_HIZALA_S) ═══════
    # `eps` t−D anindaki GOVDEYE goredir; onu ATALET yonune cevirirken
    # kullanilmasi gereken yaw da t−D anininkidir, SIMDIKI degil.
    # `iyaw_hiz` = govde yaw'inin KARENIN anina geri sarilmis hali.
    # ⛔ VARSAYILAN 0 -> hizala=0 -> iyaw_hiz == iris_yaw -> BIT-AYNI.
    # ⛔ KAPI KOSULU `> 0` DEGIL `!= 0`: NEGATIF DEGER SESSIZCE YUTULUYORDU.
    #   Bu, OLUMSUZ KONTROL kolunu (AVCI_IBVS_KOMUT_HIZALA=-0.20, telafiyi
    #   TERS uygulayip mekanizmanin gercek olup olmadigini sinar) FIILEN
    #   TABANLA AYNI hale getiriyordu -- yani deney "fark yok" der ve biz
    #   YANLIS hukum veririz. Depodaki en pahali hata sinifi tam da budur:
    #   ayari yazdik saniyoruz, kod onu yok sayiyor.
    #   ⚠ VARSAYILAN ETKILENMEZ: 0.0 iken `!= 0` da False -> hizala = 0 ->
    #     BIT-AYNI. Pozitif degerlerde de davranis birebir ayni. Yalnizca
    #     NEGATIF degerin anlami degisir: "yok sayilir" -> "ters uygulanir".
    _kh = float(getattr(cfg, "KOMUT_HIZALA_S", 0.0) or 0.0)
    hizala = 0.0
    if _kh != 0.0:
        hizala = clamp(_kh * float(yaw_hizi or 0.0),
                       -math.radians(cfg.KOMUT_HIZALA_MAX_DEG),
                       math.radians(cfg.KOMUT_HIZALA_MAX_DEG))
    iyaw_hiz = iris_yaw - hizala
    # BURUN: kamera hedefe bakar. Direksiyon terimleri (sonum/lead) BURADA
    # DEĞİL, hız yönünde. Bkz. Cfg.BURUN_LOS.
    if getattr(cfg, "BURUN_LOS", False):
        # KADRAJ KORUYUCU (a): kutunun kayma hizini ONCELE (bkz. Cfg.BURUN_KD)
        _kd = float(getattr(cfg, "BURUN_KD", 0.0) or 0.0)
        yaw_cmd = normalize_angle(iyaw_hiz + cfg.K_YAW * eps_yaw
                                  + _kd * float(eps_hizi or 0.0))
    else:
        yaw_cmd = normalize_angle(iris_yaw + cfg.K_YAW * eps_yaw - sonum + lead_az)
        # BURUN HIZ TAVANI (bkz. Cfg.YAW_TAVAN_DPS): komut, aracin mevcut
        # yaw'indan en fazla tavan*dt kadar uzaklasabilir -> govde savrulmaz.
        _yt = float(getattr(cfg, "YAW_TAVAN_DPS", 0.0) or 0.0)
        if _yt > 0.0 and dt > 0.0:
            _adim = math.radians(_yt) * dt
            _fark = normalize_angle(yaw_cmd - iris_yaw)
            if abs(_fark) > _adim:
                yaw_cmd = normalize_angle(
                    iris_yaw + (_adim if _fark > 0 else -_adim))

    # HIZ: kutu boyutu hatası üzerinden PI (terminalde TAM taahhüt)
    hata = cfg.BOYUT_REF - boyut               # px; + = uzak
    hiz_I = clamp(hiz_I + cfg.K_I * hata * dt, cfg.I_MIN, cfg.I_MAX)
    kacis_ek = 0.0
    if terminal:
        v_los = cfg.V_TERMINAL                 # hücum: fren yok, sabit hız
        # TERMINAL KAPANMA PAYI (bkz. Cfg.TERM_PAY): hedefin GORSEL hiz
        # kestirimi uzerine sabit pay -> her hedef hizinda kapanma garanti.
        _tp = float(getattr(cfg, "TERM_PAY", 0.0) or 0.0)
        if _tp > 0.0:
            v_los = clamp(max(v_los, hiz_I + _tp),
                          cfg.V_TERM_MIN, cfg.V_TOPLAM_MAX)
    else:
        # Ö1 KAÇIŞ TELAFİSİ (bkz. Cfg.KACIS_KD): hedef uzaklaşıyorsa (ṙ<0)
        # hızı ANINDA artır — integralin 5 saniyesini bekleme.
        # ⚠ YALNIZ hızlandırma yönü: ṙ>0 iken (yaklaşırken) terim SIFIR.
        if cfg.KACIS_KD > 0.0 and kapanma is not None and kapanma < 0.0:
            kacis_ek = min(cfg.KACIS_KD * (-kapanma), cfg.KACIS_MAX)
        v_los = clamp(hiz_I + cfg.K_FWD * hata + kacis_ek,
                      cfg.V_MIN, cfg.V_TOPLAM_MAX)
        # KADRAJ KORUYUCU (b): |eps| esige yaklastikca KAPANMAYI kis.
        # Hedef kadraj kenarina giderken ustune gitmek fazi olduruyor;
        # once nisani toparla. Pay 1 -> tam kapanma, 0 -> hedefin hizinda kal.
        _ke = float(getattr(cfg, "KADRAJ_ESIK_DEG", 0.0) or 0.0)
        if _ke > 0.0:
            _pay = clamp((_ke - abs(math.degrees(eps_yaw))) / _ke, 0.0, 1.0)
            v_los = clamp(hiz_I + (v_los - hiz_I) * _pay,
                          cfg.V_MIN, cfg.V_TOPLAM_MAX)

    # Ö5 DÖNÜŞ TAVANI (bkz. Cfg.DONUS_A): gereken yanal ivme V·λ̇ aracın
    # tavanını aşıyorsa hızı kıs — yarıçap V² ile düştüğü için dönüş sıkışır.
    # ⚠ YALNIZ KISAR. Düz uçuşta λ̇≈0 → tavan çok büyük → etkisiz.
    donus_tavan = None
    if cfg.DONUS_A > 0.0:
        _lam = abs(los_hiz[0])
        if _lam > 1e-3:
            donus_tavan = max(cfg.DONUS_V_MIN, cfg.DONUS_A / _lam)
            if donus_tavan < v_los:
                v_los = donus_tavan

    # ══ Ö8 · YANAL KOMUT AÇIYLA DEĞİL, KAÇIRMA MESAFESİYLE ══
    # Hız vektörünün yönü artık ayrı hesaplanır (bkz. Cfg.YANAL_K).
    # BURUN (yaw_cmd) tam eps_yaw'da kalır — kamera hedefi izlemeye devam eder.
    eps_hiz = eps_yaw
    if cfg.YANAL_K > 0.0 and boyut > 1e-6 and v_los > 0.1:
        _R = menzil_kutudan(boyut, cfg, w)            # menzil (m)
        _y = _R * math.sin(eps_yaw)                   # YANAL KAÇIRMA (m)
        _rdot = max(abs(kapanma) if kapanma is not None else 0.0,
                    cfg.YANAL_RDOT_MIN)
        _tgo = max(_R / _rdot, cfg.YANAL_TGO_MIN)     # kalan süre (s)
        _vy = cfg.YANAL_K * _y / _tgo                 # gereken yanal hız
        _eps_eff = math.asin(clamp(_vy / v_los, -1.0, 1.0))
        if abs(_eps_eff) < abs(eps_yaw):              # YALNIZ KISAR, büyütmez
            # menzil harmanı: uzakta hiç, yakında tam (bkz. YANAL_MENZIL)
            _w = clamp((cfg.YANAL_MENZIL - _R) / (0.5 * cfg.YANAL_MENZIL),
                       0.0, 1.0)
            eps_hiz = eps_yaw + _w * (_eps_eff - eps_yaw)

    # SAF TAKİP: hız LOS yönünde — ama yönü eps_hiz belirler
    hiz_yonu = normalize_angle(iris_yaw + cfg.K_YAW * eps_hiz - sonum + lead_az)

    # ── PN: hız yönünü LOS'a eşitleme, λ̇'nın N katıyla DÖNDÜR ────────────
    # psi_v durum taşır (hiz_I gibi): çağıran tani["psi_v"]'yi geri besler.
    # Beslemezse saf takip yönünden başlar — yumuşak bozulma, çökme yok.
    # M1/M2 teshis degiskenleri (bkz. Cfg "MANEVRA ISKASI" blogu).
    # _w_ham = yasanin KIRPILMADAN once istedigi hiz-yonu donus hizi (rad/s)
    # _w_uyg = gercekten uygulanan (kirpilmis) donus hizi
    # Saf takipte (PN=0, DPP=0) donus hizi ACIK bir buyuklук degildir -> None
    # kalir ve M1/M2 dogal olarak devre disi olur.
    _w_ham = None
    _w_uyg = None
    _w_tavan = None      # kirpmada GERCEKTEN kullanilan tavan (a/V, o andaki V)
    _pn = float(getattr(cfg, "PN_N", 0.0) or 0.0)
    if _pn > 0.0:
        # ⚠ PN AÇIKKEN lead_az ve sonum HIZ YÖNÜNDEN ÇIKAR:
        #   lead_az = lead_sure · λ̇  — bu zaten LOS hızına orantılı bir
        #   öngörü, yani KABA BİR PN. PN ile birlikte ÇİFT SAYILIR.
        #   sonum ise aracın kendi dönüşünü geri çeker; PN'in integratörü
        #   bunu kendi yapar.
        # Y2: govde -> ATALET cevirimi burada da t−D'ye hizalanir.
        _taban = normalize_angle(iyaw_hiz + cfg.K_YAW * eps_hiz)
        if psi_v is None:
            _p = _taban                       # ilk kare: saf takipten başla
        else:
            _w_ham = _w_uyg = _pn * los_hiz[0]     # PN'de kirpma yok
            _p = normalize_angle(float(psi_v) + _pn * los_hiz[0] * dt)
        # ⚠ SAPMA TAVANI VARSAYILAN KAPALI (0). Denendi ve ZARARLI çıktı:
        # 45° tavanda 0/40, 90°'de 31/40, tavansız 37/40. Sebep: PN'in LOS'tan
        # belirgin sapması ÖNGÖRÜ AÇISININ KENDİSİ; onu kısmak yasayı öldürür.
        # >0 verilirse yalnız gerçek kaçışa karşı kaba bir fren olur.
        _tav_d = float(getattr(cfg, "PN_SAPMA_MAX_DEG", 0.0) or 0.0)
        if _tav_d > 0.0:
            _tav = math.radians(_tav_d)
            _sap = normalize_angle(_p - _taban)
            if _sap > _tav:
                _p = normalize_angle(_taban + _tav)
            elif _sap < -_tav:
                _p = normalize_angle(_taban - _tav)
        hiz_yonu = _p
        _pn_taban = _taban
    else:
        _pn_taban = hiz_yonu

    # ══ DPP · SAPMALI SAF TAKIP, BAKIS ACISI DONGUSU (2026-08-17) ═══════════
    # Literatur (Lee/Ann/Kim ICAS 2018 eq.6-7; Ghose NPTEL M6/L18 eq.7.47-48):
    #   sabit bakis acisi komutu sigma_c ile ucan sapmali takibin kerteriz
    #   kinematiginde IKI denge vardir ve KARARLI olani KUYRUK TAKIBIDIR.
    #   sigma_c = 0 secilirse denge lambda* = gamma_hedef, yani tam olarak
    #   hedefin saat 6 yonu, bakis acisi 0, kerteriz hizi 0.
    # Yasa:  a = V*lambda_nokta + k*V*(sigma_c - sigma)   ->  kapali cevrimde
    #        sigma_nokta = -k*(sigma_c - sigma)
    # yani "bakis acisini 1/k zaman sabitiyle sigma_c'ye sur"den ibarettir.
    #
    # ⚠ BUNU NEDEN PN YERINE ISTIYORUZ: sigma STATIK bir olcumdur -- piksel
    #   acisidir, TUREV icermez, iris_yaw'a ihtiyac duymaz, dolayisiyla
    #   strapdown govde kuplaji ve "yaw_ivmesi x gecikme" sahte LOS hizi
    #   terimi YAPISAL OLARAK olusmaz. Olculen boru hatti gecikmesi 130-250 ms
    #   iken lambda_nokta tabanli hicbir yasa (PN dahil) calismaz; sigma
    #   tabanli yasa calisir.
    # ⚠ Ayrica kuyruk dengesinde lambda_nokta ~ 0 oldugu icin hedef kadrajda
    #   neredeyse hic kaymaz -> 61 derecelik yari-HFOV'un tamami serbest kalir
    #   ve dusuk kare hizi (4-16 FPS) yeterli hale gelir.
    # 0 = kapali (PN / saf takip yolu aynen calisir).
    _ks = float(getattr(cfg, "DPP_K_SIGMA", 0.0) or 0.0)
    if _ks > 0.0:
        # ⚠⚠ Y2 BURASI EN KRITIK KULLANIM. DPP'nin docstring'i "sigma
        #   iris_yaw'a ihtiyac duymaz" diyor ama KOD DUYUYOR: sigma =
        #   _los_kert − psi_v ve _los_kert govde acisini iris_yaw ile
        #   ataletlestiriyor. Yani yaw BAYATLIGI dogrudan sigma'ya, oradan
        #   da geri beslemeye biniyor (olculen |dψ| p90 13.7°, terminalde
        #   12.8° medyan). KOMUT_HIZALA kapali (0) iken BIT-AYNI.
        _los_kert = normalize_angle(iyaw_hiz + cfg.K_YAW * eps_hiz)
        if psi_v is None:
            _pd = _los_kert                      # ilk kare: LOS'a otur
        else:
            _sig_c = math.radians(float(getattr(cfg, "DPP_SIGMA_C_DEG", 0.0) or 0.0))
            _sig = normalize_angle(_los_kert - float(psi_v))     # bakis acisi
            # ── λ̇ ILERI BESLEMESI (Ghose eq.7.47/7.48'deki V_M*theta_nokta) ──
            # ⚠ BUNU ILK YAZIMDA ATLAMISTIM ve tezgahta bedeli goruldu:
            #   DONEN hedefte kalici sigma hatasi kaliyordu (tip-1 sistemin
            #   rampa izleme hatasi). 15 derece/s donen hedefte sigma_p95 41
            #   dereceye ciciyor, 35 derece/s'de hedef kadrajdan CIKIYORDU.
            #   Kuyruk dengesinde lambda_nokta = gamma_nokta_hedef oldugu icin
            #   olculen LOS hizi dogrudan hedefin donus hizidir.
            # ⚠ GERI BESLEME DEGIL ILERI BESLEME: gurultusu kararliligi bozmaz,
            #   yalnizca izleme hatasini kapatir. PN'de ayni terim N ile
            #   carpilip GERI BESLEMEYE giriyordu -- fark budur.
            _ff = float(getattr(cfg, "DPP_FF_LAM", 1.0) or 0.0) * los_hiz[0]
            # yaw hizi doygunlugu: a = V*omega -> omega_max = a_max / V
            # ⚠ M1 ACIKKEN TAVAN, KISILMIS HIZLA hesaplanmali: yoksa yasa
            #   15 m/s ucarken hala 23 m/s'nin tavanini kullanir ve M1'in
            #   ACTIGI donus yetkisini HIC KULLANMAZ (yama bosa gider).
            #   v_kapi cagirandan gelen ONCEKI karenin kapisidir -> bir kare
            #   gecikme; kalici rejimde tam dogru.
            _v_wm = v_los
            if (float(getattr(cfg, "DONUS_BUTCE", 0.0) or 0.0) > 0.0
                    and v_kapi is not None and not terminal):
                _v_wm = min(_v_wm, float(v_kapi))
            _wmax = float(getattr(cfg, "MAX_ACCEL", 12.0)) / max(_v_wm, 1.0)
            _w_ham = _ks * (_sig - _sig_c) + _ff       # KIRPILMAMIS talep
            _w = clamp(_w_ham, -_wmax, _wmax)
            _w_uyg = _w
            _w_tavan = _wmax          # ⚠ kirpmanin kullandigi TAM deger
            _pd = normalize_angle(float(psi_v) + _w * dt)
        hiz_yonu = _pd
        _pn_taban = _los_kert

        # ── MENZIL DONGUSU: V = V_hedef_kestirim + K_r * sat(r - r_set) ──
        # hiz_I zaten hedefin hizina yakinsayan integraldir (K_I * boyut hatasi).
        # Uzerine ACIK menzil hatasi terimi koyariz; boylece hiz kararı kutunun
        # ANLIK boyutundan degil, MENZILDEN gelir -- kutu kadraj kenarinda
        # sistigunde (olculdu: 8 m'de 20 -> 44 px) sahte fren yapilmaz.
        _kr = float(getattr(cfg, "DPP_K_R", 0.0) or 0.0)
        if _kr > 0.0 and boyut > 1e-6 and not terminal:
            _Rm = menzil_kutudan(boyut, cfg, w)
            _rset = float(getattr(cfg, "DPP_R_SET", 8.5))
            _sat = float(getattr(cfg, "DPP_R_SAT", 10.0))
            _vmin = float(getattr(cfg, "DPP_V_MIN", 14.0))
            v_los = clamp(hiz_I + _kr * clamp(_Rm - _rset, -_sat, _sat),
                          _vmin, cfg.V_TOPLAM_MAX)

    # ══ M1 · DONUS BUTCESI HIZ KAPISI (bkz. Cfg.DONUS_BUTCE) ═══════════════
    # w_max = MAX_ACCEL / V. Talep tavani asiyorsa V'yi kisip TAVANI BUYUT.
    # ⚠ YALNIZ SEYIRDE (terminal hucum hizi kullanici karari, dokunulmaz).
    # ⚠ YALNIZ KISAR; talep tavanin altindaysa hic dokunmaz (duz segment).
    donus_kapi = None
    _db = float(getattr(cfg, "DONUS_BUTCE", 0.0) or 0.0)
    if (_db > 0.0 and not terminal and _w_ham is not None
            and abs(_w_ham) > 1e-3):
        _tab = float(getattr(cfg, "DONUS_BUTCE_VTABAN", 15.0))
        _kap = max(_tab, _db * float(getattr(cfg, "MAX_ACCEL", 12.0))
                   / abs(_w_ham))
        # Kapinin KENDISI rampali: kare kare ziplarsa limit_acceleration'i
        # yeniden doyurur -- tam kacinmak istedigimiz sey. Saniyede en fazla
        # MAX_ACCEL kadar oynar (cagiran v_kapi'yi tasir).
        if v_kapi is not None:
            _d = float(getattr(cfg, "MAX_ACCEL", 12.0)) * dt
            _kap = clamp(_kap, float(v_kapi) - _d, float(v_kapi) + _d)
        donus_kapi = _kap
        if _kap < v_los:
            v_los = _kap
    # kapi durumu: baglamasa da tasinir ki rampa surekli olsun
    v_kapi_yeni = donus_kapi if donus_kapi is not None else v_los

    # ⚠ DURUM ONCULEMESIZ: sigma bir sonraki karede psi_v'den olculur; M2'nin
    # ongorusu duruma girerse dongu kendi lead'ini geri okur (pozitif geri
    # besleme). Bu yuzden psi_v_yeni CIKIS ongorusunden ONCE sabitlenir.
    psi_v_yeni = hiz_yonu

    # ══ M2 · ARAC GECIKME TELAFISI (bkz. Cfg.ARAC_TAU) ═════════════════════
    # Gercek hiz yonu psi_v'nin ARKASINDA kaliyor (donuste -16.4 deg olculdu).
    # Rampa girdide birinci mertebe gecikmenin kalici hatasi w*tau'dur;
    # referansi w*tau kadar ONE alarak birebir kapatilir.
    arac_lead = 0.0
    _at = float(getattr(cfg, "ARAC_TAU", 0.0) or 0.0)
    if _at > 0.0 and _w_uyg is not None:
        _lt = math.radians(float(getattr(cfg, "ARAC_TAU_MAX_DEG", 25.0)))
        arac_lead = clamp(_at * _w_uyg, -_lt, _lt)
        hiz_yonu = normalize_angle(hiz_yonu + arac_lead)

    vx_ned = v_los * math.cos(hiz_yonu)
    vy_ned = v_los * math.sin(hiz_yonu)

    # ── DİKEY NİŞAN: TERMİNAL RAMPASI (bkz. Cfg.TERM_DIKEY_M) ────────────
    # Rampa kapalıyken cy_nisan == cfg.CY_NISAN (bit-aynı eski davranış).
    # Açıkken nişanın DÜNYA yükselişi menzille 0'a sürülür → son metrelerde
    # eş irtifa. GPS yasasındaki TERM_DIKEY_M ile AYNI mantık, aynı isim.
    cy_nisan = nisan_cy(iris_pitch, boyut, cfg, w)

    # T1b (bkz. Cfg.DIKEY_ROLL): ham piksel farkı KAMERA çerçevesindedir;
    # araç yattığında bu SEVİYE çerçevesindeki yükseliş DEĞİLDİR.
    eps_elev_ham = math.atan((cy - cy_nisan) / geo.FY)      # cy büyük → altta
    eps_elev = eps_elev_ham
    # ── T1b/T1c ORTAK TERIM: durusun YALNIZ ROLL'den gelen yukselis sapmasi.
    # el_roll = gercek SEVIYE yukselisi; el_norm = roll'u 0 sayan hali.
    # Fark, "roll yuzunden yukselisi ne kadar yanlis okuyoruz"dur.
    # ⚠ roll = 0 -> los_seviye(...,0,...) ile birebir ayni cagri -> TAM 0.
    #   Yani iki kapi da kapaliyken bu blok HIC calismaz (koşul aşağıda).
    _roll_sapma = 0.0
    if cfg.DIKEY_ROLL or getattr(cfg, "TERM_ROLL", False):
        _, _el_roll = los_seviye(cx, cy, iris_roll, iris_pitch, cfg)
        _, _el_norm = los_seviye(cx, cy, 0.0, iris_pitch, cfg)
        _roll_sapma = _el_roll - _el_norm
    if cfg.DIKEY_ROLL:
        # ⚠ TELAFİ, FARK OLARAK uygulanır — hata TANIMI değişmez.
        # Birim testi B58 şunu yakaladı: seviye yükselişini doğrudan hata
        # yerine koymak, roll=pitch=0'da BİLE komutu 0.51 m/s değiştiriyordu
        # (25° tilt yüzünden piksel farkı ile açı farkı aynı fonksiyon değil).
        # Doğrusu: duruşun getirdiği SAPMAYI çıkarmak.
        # ⚠ YALNIZ ROLL izole edilir; pitch İKİ terimde de aynı bırakılır.
        # Sebep: nişan noktası CY_NISAN, aracın seyir pitch'i (18 m/s'de
        # burun ~28° aşağı) ile BİRLİKTE uçuşta ayarlanmıştı. Pitch'i de
        # telafi etmek nişan noktasını kaydırır — bu ayrı bir değişkendir,
        # bu adımın konusu değil. (İlk sürüm pitch'i de içeriyordu ve
        # terminalde +5.9° kayma üretiyordu; tek-değişken kuralına aykırı.)
        _, _el_roll = los_seviye(cx, cy, iris_roll, iris_pitch, cfg)
        _, _el_norm = los_seviye(cx, cy, 0.0, iris_pitch, cfg)
        # el_roll > el_norm ⇒ hedef sandığımızdan YUKARIDA ⇒ daha çok tırman
        eps_elev = eps_elev_ham - (_el_roll - _el_norm)
    # T1c (bkz. Cfg.TERM_ROLL): TERMINAL dikey kanalina uygulanan roll
    # sapmasi. Kapali (varsayilan) -> 0.0 -> asagisi BIT-AYNI.
    term_roll = _roll_sapma if getattr(cfg, "TERM_ROLL", False) else 0.0
    if terminal:
        # KESİŞİM: hız vektörü hedefe DOĞRU baksın (tutuş ofseti değil).
        # elev_atalet = gövde LOS yükselişi + gövde pitch; lead ile öne alınır.
        # ⚠ T1c: `piksel_elev` ROLL'u HIC cikarmaz. Yatis 50.7 dereceye
        #   ciktigi TERMINALDE bu, olculen en buyuk dikey okuma hatasidir
        #   (|roll| 20-30 deg bandinda 8.87 -> 3.03 deg). Telafi FARK olarak
        #   eklenir; roll=0'da terim TAM SIFIR -> eski davranis birebir.
        elev_atalet = piksel_elev(cy, cfg) + iris_pitch + term_roll
        lead_el = clamp(lead_sure * los_hiz[1],
                        -math.radians(cfg.LEAD_MAX_DEG),
                        math.radians(cfg.LEAD_MAX_DEG))
        nisan_elev = clamp(elev_atalet + lead_el,
                           -math.radians(60.0), math.radians(60.0))

        # ── DİKEY BÜTÇE KISITI (2026-08-09, kullanıcı gözlemi: "dikeyde çok
        # kaçırıyor") ──
        # Hız vektörünün gösterebileceği en dik açı atan(VZ_MAX_TERM/v_los).
        # 18 ve 5 ile bu YALNIZCA 15.5° — hedef daha yukarıdaysa kesişim
        # MATEMATİKSEL OLARAK İMKÂNSIZ, drone altından geçer. Ölçüldü: terminal
        # karelerinin %22-49'unda vz tavana dayanmıştı (yani "daha çok
        # tırmanmam lazım" deyip yapamıyordu).
        # ÇÖZÜM: dikey tavan yetmiyorsa YATAYI KIS — böylece vektör hedefe
        # bakabilir. Yavaşlamak yaklaşmayı geciktirir ama ıskalamaktan iyidir;
        # V_TERM_MIN altına inilmez (hedefi büsbütün kaçırmamak için).
        # AÇIYI DİKEY HIZA ÇEVİREN ÖLÇEK (bkz. Cfg.KAPANMA): kapanma hızı.
        # ⚠ Dikey bütçe kısıtı da AYNI ölçeği kullanmalı — yoksa yatayı,
        # artık var olmayan bir dikey talep yüzünden kısar (yani boşuna
        # frene basar). İki yer tek kavram.
        v_dikey = v_los
        if cfg.KAPANMA and kapanma is not None:
            v_dikey = clamp(kapanma, cfg.KAPANMA_MIN, max(cfg.KAPANMA_MIN, v_los))
        t_ = abs(math.tan(nisan_elev))
        if t_ > 1e-6 and v_dikey * t_ > cfg.VZ_MAX_TERM:
            v_los = max(cfg.V_TERM_MIN, cfg.VZ_MAX_TERM / t_)
            vx_ned = v_los * math.cos(hiz_yonu)
            vy_ned = v_los * math.sin(hiz_yonu)
        vz_nisan = -v_dikey * math.tan(nisan_elev)
        # TÜREV SÖNÜMLEMESİ: aracın kendi dikey hızı nişanın ötesine geçtiyse
        # komut geri çekilir → hedefin üstünden geçme biter (bkz. Cfg.K_VZ_D).
        vz = clamp(vz_nisan + cfg.K_VZ_D * (vz_nisan - iris_vz),
                   -cfg.VZ_MAX_TERM, cfg.VZ_MAX_TERM)
    else:
        # TUTUŞ: hedefi nişan pikselinde tut. Nişan, rampa KAPALIYKEN
        # CY_NISAN'dır (eski davranış); açıkken menzille eş irtifaya kayar
        # (bkz. Cfg.TERM_DIKEY_M ve nisan_cy).
        vz_nisan_seyir = cfg.K_VZ * cfg.V_NOM * eps_elev
        # TÜREV SÖNÜMLEMESİ — terminal dalının (bkz. Cfg.K_VZ_D) SEYİR
        # karşılığı. Gerekçe, ölçüm ve boyutlandırma: Cfg.KVZD_SEYIR.
        # 0 = KAPALI → aşağısı bit-aynı eski davranış.
        _kd_seyir = float(getattr(cfg, "KVZD_SEYIR", 0.0) or 0.0)
        if _kd_seyir > 0.0:
            vz_nisan_seyir += _kd_seyir * (vz_nisan_seyir - iris_vz)
        vz = clamp(vz_nisan_seyir, -cfg.VZ_MAX, cfg.VZ_MAX)

    tani = {"psi_v": psi_v_yeni, "pn_taban": _pn_taban,
            "cy_nisan": cy_nisan,
            "eps_hizi": float(eps_hizi or 0.0),
            "boyut": boyut, "eps_yaw": eps_yaw, "eps_elev": eps_elev,
            "eps_elev_ham": eps_elev_ham,
            "hata": hata, "v_los": v_los, "terminal": terminal,
            "eps_hiz": eps_hiz, "sonum": sonum,
            "donus_tavan": donus_tavan,
            "kacis_ek": kacis_ek,
            "lead_az": lead_az, "lead_olcek": lead_olcek,
            "eps_yaw_ham": eps_yaw_ham,
            # ── MANEVRA TESHISI / M1-M2 MEKANIZMA KAPILARI ──
            "w_ham": _w_ham, "w_uyg": _w_uyg,
            # ⚠ DPP'de kirpmanin GERCEKTEN kullandigi tavan yazilir (o andaki
            #   v_los ile); menzil dongusu v_los'u sonra degistirdigi icin
            #   sonradan yeniden hesaplamak doygunluk oranini yanlis olcerdi.
            "w_tavan": (_w_tavan if _w_tavan is not None
                        else float(getattr(cfg, "MAX_ACCEL", 12.0))
                        / max(v_los, 1.0)),
            "donus_kapi": donus_kapi, "v_kapi": v_kapi_yeni,
            "arac_lead": arac_lead,
            # ── Y2 / M-KAL MEKANIZMA KAPILARI ──
            # hizala : komuttan cikarilan yaw bayatligi (rad). 0'a yapisiksa
            #          KOMUT_HIZALA devreye GIRMEMISTIR -> deney gecersiz.
            # yaw_hizi: kapinin girdisi; isaretleri TERS olmali.
            # menzil / menzil_term: yasanin ve terminal nisan kapisinin ayni
            #          kareye verdigi menziller. Esit degillerse IKIZ var.
            # term_roll: T1c'nin TERMINAL dikey kanalina ekledigi sapma (rad).
            #   0'a yapisiksa TERM_ROLL devreye GIRMEMISTIR.
            "term_roll": term_roll,
            "hizala": hizala, "yaw_hizi": float(yaw_hizi or 0.0),
            "menzil": menzil_kutudan(boyut, cfg, w) if boyut > 1e-6 else None,
            "menzil_term": (menzil_kutudan(boyut, cfg, w, terminal_kapi=True)
                            if boyut > 1e-6 else None)}
    return vx_ned, vy_ned, vz, yaw_cmd, hiz_I, tani


def _kutu_gecerli(pose, cfg):
    """pose kaydından geçerli kutu çıkar → (cx,cy,w,h,conf) veya None."""
    if pose is None:
        return None
    conf = pose.get("conf", 0.0)
    if conf < cfg.CONF_MIN:
        return None
    bbox = pose.get("bbox")
    if bbox is not None:
        x1, y1, x2, y2 = bbox
        w, h = (x2 - x1), (y2 - y1)
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    elif pose.get("cx") is not None:
        cx, cy = pose["cx"], pose["cy"]
        w = pose.get("w", 0.0)
        h = pose.get("h", 0.0)
    else:
        return None
    if math.sqrt(max(w, 0.0) * max(h, 0.0)) < cfg.BOYUT_MIN:
        return None
    return cx, cy, w, h, conf


def run_bbox_ibvs(conn, get_iris, wait_pose, stop_event, cfg=Cfg,
                  kayip_kare_esik=20, ff_hiz=(0.0, 0.0, 0.0), get_temas=None,
                  kilit_t0=None):
    """bbox IBVS görsel güdüm döngüsü. Kutu akışına kilitli (wait_pose).

    kilit_t0: devir anında SÜREN kesintisiz kilidin başlangıcı (monoton) veya
    None. Terminal mandalının "5 s kesintisiz kilit" kapısı bunu DEVRALIR —
    yoksa devirden sonra sayaç sıfırdan başlar ve toplam şart 10 s'ye çıkar.
    None (varsayılan) → sayaç sıfırdan; AVCI_KILIT_S=0 iken zaten etkisiz.

    ff_hiz: devir anındaki son GPS hız kestirimi — YALNIZ hız integralinin
    SICAK BAŞLANGIÇ değeri olarak kullanılır (|ff| skaler). ⚠ SAYI ÜÇLÜSÜ,
    callback DEĞİL: döngünün canlı GPS'e erişimi yoktur (D0 yapısal garanti).
    Yön hiçbir zaman ff'ten gelmez — hız daima LOS yönündedir (2026-08-08
    dersi: dondurulmuş NED yönü hedef döndükçe drone'u yana savuruyordu).

    get_temas: Talon'un ÇARPMA SENSÖRÜ (sim_truth.temas) — True dönerse
    'vuruldu' ile biter. ⚠ Bu bir SONUÇ sinyalidir, güdüm girdisi DEĞİL:
    hedefin yerini/hızını taşımaz, yalnız "çarpışma oldu mu" der. Güdüm
    yasası (komut) onu hiç görmez.

    kayip_kare_esik ardışık geçersiz-kutu karesi → 'kayip' döner (görsel temas
    kesildi; supervisor GPS fazına döner). stop_event → 'durduruldu'.
    """
    loop_period = 1.0 / cfg.LOOP_HZ
    son_seq = 0
    kayip_sayac = 0
    # SICAK BAŞLANGIÇ: integral hedefin bilinen seyir hızıyla başlar; böylece
    # ilk saniyelerde "hızı sıfırdan öğrenme" gecikmesi yaşanmaz. Bundan sonra
    # integrali YALNIZ görüntü hatası sürer.
    hiz_I = clamp(math.hypot(float(ff_hiz[0]), float(ff_hiz[1])),
                  cfg.I_MIN, cfg.I_MAX)
    # İvme sınırlayıcı drone'un GERÇEK hızından başlar (kendi sensörü).
    # Sıfırdan başlarsa devir anında 15 m/s'lik seyir "frenlenmiş" gibi
    # rampalanır (12 m/s² ile 1.25 s) — hedef o sırada kaçar.
    _i0 = get_iris()
    vx_p = float(_i0.get("vx", 0.0) or 0.0)
    vy_p = float(_i0.get("vy", 0.0) or 0.0)
    vz_p = float(_i0.get("vz", 0.0) or 0.0)
    # ── Y1: SICAK BASLANGIC TABANI = KENDI HIZIMIZ (bkz. Cfg.HIZ_SICAK_PAY)
    # Kapali (varsayilan, pay<0) -> hiz_I bit-ayni |ff_hiz|'dir.
    # ⚠ D0: get_iris ARACIN KENDI hiz sensorudur, canli GPS DEGIL. Devirde
    #   BIR KEZ okunur (zaten yukarida okundu), gorsel faz boyunca bir daha
    #   bakilmaz — dondurulmus tasiyici garantisi bozulmaz.
    _hiz_kaynak = "ff"
    _hs_pay = float(getattr(cfg, "HIZ_SICAK_PAY", -1.0))
    _oz_hiz = math.hypot(vx_p, vy_p)
    if _hs_pay >= 0.0:
        _taban = clamp(_oz_hiz - _hs_pay, cfg.I_MIN, cfg.I_MAX)
        if _taban > hiz_I:
            hiz_I = _taban
            _hiz_kaynak = "kendi"
    son_v_cmd = None       # kutu boşluğunda sürdürülecek son komut
    terminal_mandal = False   # terminal hücum kilidi (bir kez girilince kalır)
    nisan_uyari = False       # nişan kapısı uyarısı bir kez bassın
    kor_baslangic = None      # kör hücumun başladığı duvar anı (süre sınırı)
    prev_time = None
    cmd_yaw = None
    kurt = Kurtarma()         # duruş bekçisi (normal uçuşta hiç tetiklenmez)
    # LOS (atalet) açıları ve hızları — lead nişanı için
    los_az_onceki = los_el_onceki = None
    psi_v = None                    # PN hız yönü durumu (bkz. Cfg.PN_N)
    v_kapi = None                   # M1 dönüş bütçesi hız kapısı (rampa durumu)
    yaw_gecmis = []                 # (t, iris_yaw) — λ̇ zaman hizalamasi icin
    eps_gecmis = []                 # (t, eps) — KADRAJ ICI kayma hizi (saf piksel)
    kopru_gecmis = []               # (t, cx, cy, w, h) — kor kopru icin son tespitler
    son_tespit = None               # (t, los_atalet, cy, w, h) — atalet koprusu icin
    kutu_son = None                 # (t, boyut, w) — kutu buyume hizi siniri icin
    # ── KES · tam durum kestirimi penceresi (bkz. Cfg.KESTIRIM) ────────────
    # (t, ofset_N, ofset_E, ofset_D) — YALNIZ GERCEK tespitli kareler.
    # ⚠ HAYALET (kopru) kareler DISARIDA: onlarin cx/cy'si son gercek
    #   tespitten ILERI TASINMIS bir vekildir; pencereye girerse hedefe
    #   ait olmayan sahte bir hiz uretir (olculen kopru kerteriz hatasi
    #   medyan 141.6 derece -- oradan hiz cikarmak sacmadir).
    kest_gecmis = []
    kutu_kirp = 0
    los_gecmis = []                 # (t, los_az_açılmış) — en küçük kareler penceresi
    los_hiz = [0.0, 0.0]      # [azimut, yükseliş] rad/s, EMA'lı
    boyut_onceki = None       # kapanma hızı için (bkz. Cfg.KAPANMA)
    kapanma = None            # m/s; görüntüden ölçülen kapanma hızı, EMA'lı
    iyaw_onceki = None        # Ö9 sönümlemesi için yaw türevi (bkz. Cfg.SONUM_T)
    yaw_hizi = 0.0            # rad/s; aracın KENDİ dönüş hızı, EMA'lı
    # ── KESİNTİSİZ KİLİT SAYACI (2026-08-17) ───────────────────────────────
    # ÖLÇÜLDÜ: terminal mandalı (aşağıda) kilit süresine HİÇ bakmıyordu;
    # mandal anında kesintisiz gerçek tespit medyanı 0.16 s (2026-08-17, n=81),
    # yalnız %3.7'si ≥5 s. Bu sayaç o boşluğu kapatır. Kapı AVCI_KILIT_S ile
    # açılır; 0 (varsayılan) iken gecti() hep True → davranış BİT-AYNI.
    kk = KesintisizKilit(t0=kilit_t0)
    _kilit_uyari = False      # terminal kapısı uyarısı bir kez bassın

    def _vuruldu():
        if get_temas is None:
            return False
        return get_temas() is True

    os.makedirs(_LOG_DIR, exist_ok=True)
    csv_yol = os.path.join(_LOG_DIR, time.strftime("bbox_ibvs_%Y%m%d_%H%M%S.csv"))
    f = open(csv_yol, "w", newline="")
    w_csv = csv.DictWriter(f, fieldnames=_CSV_ALANLAR, extrasaction="ignore")
    w_csv.writeheader()
    print(f"[IBVS] bbox görsel güdüm başladı — SAF TAKİP + PI hız "
          f"(CANLI GPS YOK, yarışma kuralı). İntegral sıcak başlangıç: "
          f"{hiz_I:.1f} m/s [kaynak={_hiz_kaynak}, ff={math.hypot(float(ff_hiz[0]), float(ff_hiz[1])):.1f}, "
          f"kendi={_oz_hiz:.1f}], REF={cfg.BOYUT_REF:.0f}px, tavan "
          f"{cfg.V_TOPLAM_MAX:.0f} m/s, terminal hücum >{cfg.TERMINAL_BOYUT:.0f}px, "
          f"CY_nişan={cfg.CY_NISAN:.0f}, kayıp eşiği={kayip_kare_esik} kare, "
          f"yatay roll/pitch telafisi={'AÇIK' if cfg.ROLL_TELAFI else 'kapalı'}, "
          f"temas sensörü={'VAR' if get_temas is not None else 'yok'} "
          f"— log: {csv_yol}")
    # ⚠ ETKIN AYARI YAZ (kampanyanin "bayat sunucu" dersi): bir ayarin
    #   gercekten kosuldugu, env'e ne yazildigina degil, surecin ne BASTIGINA
    #   bakilarak dogrulanir. Iki yeni kapi da burada gorunur olsun.
    _td_v = float(getattr(cfg, "TERM_DIKEY_M", 0.0) or 0.0)
    # ⚠ DEVIR KAPILARI (2026-08-17): ikisi de VARSAYILAN KAPALI.
    #   D1 acikken `cy_nisan` sutunu 301'den SAPMALI ve pitch ile OYNAMALI;
    #   Y1 acikken yukaridaki satirda kaynak=kendi yazmali.
    print(f"[IBVS] devir kapıları: D1 dikey nişan ufka bağlı="
          f"{('AÇIK (ufuk elev %.1f°)' % getattr(cfg, 'UFUK_ELEV_DEG', 0.0)) if getattr(cfg, 'DIKEY_UFUK', False) else 'KAPALI'}"
          f" | Y1 hız sıcak başlangıç tabanı="
          f"{('AÇIK (pay %.1f m/s)' % cfg.HIZ_SICAK_PAY) if float(getattr(cfg, 'HIZ_SICAK_PAY', -1.0)) >= 0.0 else 'KAPALI'}")
    print(f"[IBVS] dikey: nişan {cfg.CY_NISAN:.0f} px, terminal dikey rampası="
          f"{('%.1f m (vekil)' % _td_v) if _td_v > 0 else 'KAPALI'}, "
          f"ivme tavanı="
          f"{('AYRIK %.1f yatay / %.1f dikey' % (cfg.MAX_ACCEL, getattr(cfg, 'MAX_ACCEL_V', 10.0))) if getattr(cfg, 'ACCEL_SPLIT', False) else ('TEK 3B %.1f' % cfg.MAX_ACCEL)}"
          f" m/s²")
    # ⚠ MANEVRA KAPILARI (2026-08-17): ikisi de VARSAYILAN KAPALI. Acikken
    #   log sutunlari `donus_kapi_v` / `arac_lead_deg` DOLMALI; dolmuyorsa
    #   yama devreye girmemistir ve deney GECERSIZDIR.
    _db_v = float(getattr(cfg, "DONUS_BUTCE", 0.0) or 0.0)
    _at_v = float(getattr(cfg, "ARAC_TAU", 0.0) or 0.0)
    print(f"[IBVS] manevra: M1 dönüş bütçesi="
          f"{('%.2f x a/|w| , taban %.1f m/s' % (_db_v, getattr(cfg, 'DONUS_BUTCE_VTABAN', 15.0))) if _db_v > 0 else 'KAPALI'}"
          f" | M2 araç gecikme telafisi="
          f"{('tau %.2f s, tavan %.0f°' % (_at_v, getattr(cfg, 'ARAC_TAU_MAX_DEG', 25.0))) if _at_v > 0 else 'KAPALI'}"
          f" | terminal λ̇ kapısı="
          f"{('%.0f °/s' % cfg.TERM_LAM_MAX_DEG) if cfg.TERM_LAM_MAX_DEG > 0 else 'KAPALI (ölçümle çürütüldü)'}")
    # ⚠ BBOX GEOMETRI KAPILARI (2026-08-18): DORDU DE VARSAYILAN KAPALI.
    #   Acikken log sutunlari DOLMALI (hizala_deg / term_roll_deg / kest_*);
    #   dolmuyorsa yama devreye girmemistir ve deney GECERSIZDIR.
    _khz = float(getattr(cfg, "KOMUT_HIZALA_S", 0.0) or 0.0)
    print(f"[IBVS] bbox geometri: Y2 komut yolu yaw hizalama="
          f"{('AÇIK (%.2f s, tavan %.0f°)' % (_khz, getattr(cfg, 'KOMUT_HIZALA_MAX_DEG', 25.0))) if _khz > 0 else 'KAPALI'}"
          f" | T1b tutuş dikey roll={'AÇIK' if cfg.DIKEY_ROLL else 'KAPALI'}"
          f" | T1c terminal dikey roll="
          f"{'AÇIK' if getattr(cfg, 'TERM_ROLL', False) else 'KAPALI'}"
          f" | menzil: yasa {cfg.MENZIL_PX_M:.1f} / terminal {getattr(cfg, 'MENZIL_TERM_PX_M', 160.0):.1f} px·m"
          f"{(' / K_w %.1f' % cfg.MENZIL_KW) if float(getattr(cfg, 'MENZIL_KW', 0.0) or 0.0) > 0 else ''}"
          f"{(' / pay %.2f px' % cfg.MENZIL_OFS_PX) if float(getattr(cfg, 'MENZIL_OFS_PX', 0.0) or 0.0) != 0 else ''}"
          f" | KES durum kestirimi="
          f"{('AÇIK (%.2f s pencere)' % getattr(cfg, 'KESTIRIM_PENCERE_S', 0.40)) if getattr(cfg, 'KESTIRIM', False) else 'KAPALI'}")

    try:
        while not stop_event.is_set():
            kayit = wait_pose(son_seq, timeout=0.5)
            if kayit is None:
                # kare akışı durdu — temas kesildi say (akış yoksa ilerleme yok)
                kayip_sayac += 1
                if kayip_sayac >= kayip_kare_esik:
                    print("[IBVS] kare akışı/temas kesildi → 'kayip'")
                    return "kayip"
                continue
            son_seq = kayit["seq"]
            # ÖLÇÜM (davranışa etkisi YOK): karenin gcs'e gelişinden
            # komut anına kadar geçen süre. Lead süresinin doğru
            # değeri bu gecikmeden çıkar — tahminle konmamalı.
            _wr = kayit.get("wall_recv")
            gecikme_s = (time.time() - _wr) if _wr else None

            if _vuruldu():
                print("[IBVS] ✓✓ VURULDU (Talon çarpma sensörü)")
                send_velocity(conn, 0.0, 0.0, 0.0, cmd_yaw or 0.0)
                return "vuruldu"

            now = time.monotonic()
            dt = (now - prev_time) if prev_time is not None else loop_period
            dt = clamp(dt, 0.001, 0.5)
            prev_time = now

            iris = get_iris()
            iyaw = iris.get("yaw", 0.0)
            # Ö9 için aracın KENDİ dönüş hızı (rad/s) — kendi IMU'su, D0 temiz.
            # EMA: yaw gürültüsü sönümleme terimini titretmesin.
            if iyaw_onceki is not None and 1e-3 < dt < 0.5:
                _yr = normalize_angle(iyaw - iyaw_onceki) / dt
                yaw_hizi = 0.3 * _yr + 0.7 * yaw_hizi
            iyaw_onceki = iyaw

            # ── KURTARMA BEKÇİSİ (bkz. kurtarma.py) — takla/kaçak dönmede
            # güdüm komutu kesilir. Terminal kör hücumdan da ÖNCE gelir:
            # kontrolü kaybetmiş araçla hücumu sürdürmek uçuşu bitiriyor.
            # Kayıp sayacı işlemeye devam eder → uzun sürerse GPS'e dönülür.
            if kurt.guncelle(iris.get("roll", 0.0), iris.get("pitch", 0.0),
                             iyaw, now):
                send_velocity(conn, 0.0, 0.0, 0.0, iyaw)
                vx_p = vy_p = vz_p = 0.0
                son_v_cmd = None
                cmd_yaw = iyaw
                kayip_sayac += 1
                if kayip_sayac >= kayip_kare_esik:
                    print("[IBVS] kurtarma sırasında temas koptu → 'kayip'")
                    return "kayip"
                w_csv.writerow({"t": round(now, 3), "dt": round(dt, 4),
                                "durum": "KURTARMA",
                                "kayip_sayac": kayip_sayac,
                                "iris_yaw_deg": round(math.degrees(iyaw), 1)})
                f.flush()
                continue

            kutu = _kutu_gecerli(kayit["pose"], cfg)

            # ── KOR KOPRU: kutu yoksa son iki tespitten ILERI TASI ────────
            kopru_kare = False
            _kks = float(getattr(cfg, "KOR_KOPRU_S", 0.0) or 0.0)
            if kutu is not None:
                kopru_gecmis.append((now, kutu[0], kutu[1], kutu[2], kutu[3]))
                while len(kopru_gecmis) > 6:
                    kopru_gecmis.pop(0)
            elif (float(getattr(cfg, "KOR_KOPRU_ATALET_S", 0.0) or 0.0) > 0.0
                  and son_tespit is not None):
                # ── ATALET KOPRUSU: kerterizi koru, guncel yaw ile cevir ──
                _kka = float(cfg.KOR_KOPRU_ATALET_S)
                _yas = now - son_tespit[0]
                if 0.0 < _yas <= _kka:
                    _eps_b = normalize_angle(son_tespit[1] - iyaw)
                    _eps_b = clamp(_eps_b, -1.15, 1.15)     # ~66°, kadraj disi olmasin
                    kutu = (cfg.CX_NISAN + geo.FX * math.tan(_eps_b),
                            son_tespit[2], son_tespit[3], son_tespit[4], 0.0)
                    kopru_kare = True
            elif _kks > 0.0 and len(kopru_gecmis) >= 2:
                _a, _b = kopru_gecmis[-2], kopru_gecmis[-1]
                _yas = now - _b[0]
                _dt = _b[0] - _a[0]
                if 1e-3 < _dt < 0.6 and 0.0 < _yas <= _kks:
                    _vx = (_b[1] - _a[1]) / _dt          # px/s yatay
                    _vy = (_b[2] - _a[2]) / _dt
                    # ⚠ piksel hizini SINIRLA: tek kotu kare kopruyu savurmasin
                    _vx = clamp(_vx, -900.0, 900.0)
                    _vy = clamp(_vy, -900.0, 900.0)
                    kutu = (_b[1] + _vx * _yas, _b[2] + _vy * _yas,
                            _b[3], _b[4], 0.0)
                    kopru_kare = True

            # ── KESİNTİSİZ KİLİT SAYACI: HAM tespit beslenir ───────────────
            # kayit["pose"] = dedektörün GERÇEK kutusu (yasa çerçevesi px) ya
            # da None. Köprü/hayalet karesi `hayalet=True` ile geçer → kilide
            # SAYILMAZ (kullanıcı şartı: "gerçek tespit, hayalet DEĞİL").
            # SALT ÖLÇÜM: AVCI_KILIT_S=0 iken hiçbir karar buna bakmaz.
            kk.guncelle(None if kopru_kare else kayit.get("pose"), now,
                        hayalet=kopru_kare)

            if kutu is None:
                kayip_sayac += 1
                # TERMİNAL: kör hücum — kutu kaybolsa da son komutla devam,
                # AMA SÜRE SINIRLI. Terminalde hedef kadrajdan çıkması NORMAL
                # (çok yakın); GPS'e hemen dönmek çarpışmayı iptal eder. Süre
                # dolarsa ıska sayılır — sınırsız bırakmak aracı kaçırıyor.
                if terminal_mandal:
                    if kor_baslangic is None:
                        kor_baslangic = time.time()
                        print(f"[IBVS] kör hücum başladı — {cfg.TERMINAL_SURE:.1f} s "
                              f"içinde temas gelmezse ıska")
                    gecen = time.time() - kor_baslangic
                    if gecen >= cfg.TERMINAL_SURE:
                        print(f"[IBVS] kör hücum {gecen:.1f} s sürdü, temas yok "
                              f"→ ISKA, 'kayip' (GPS'e dönülüyor)")
                        return "kayip"
                    if son_v_cmd is not None:
                        send_velocity(conn, *son_v_cmd)
                    w_csv.writerow({"t": round(now, 3), "dt": round(dt, 4),
                                    "durum": "TERM_KOR",
                                    "kayip_sayac": kayip_sayac,
                                    "iris_yaw_deg": round(math.degrees(iyaw), 1)})
                    f.flush()
                    continue
                if kayip_sayac >= kayip_kare_esik:
                    print(f"[IBVS] {kayip_kare_esik} ardışık kutusuz kare → 'kayip'")
                    return "kayip"
                # Kutu yok: SON KOMUT sürdürülür (hedefin seyri bir karede
                # değişmez). Sıfır komut vermek kısa bir tespit boşluğunu
                # kalıcı kayba çevirir. İntegral dokunulmaz (bozulmasın).
                if son_v_cmd is not None:
                    send_velocity(conn, *son_v_cmd)
                else:
                    send_velocity(conn, vx_p, vy_p, vz_p, cmd_yaw or iyaw)
                w_csv.writerow({"t": round(now, 3), "dt": round(dt, 4),
                                "durum": "KUTU_YOK", "kayip_sayac": kayip_sayac,
                                "iris_yaw_deg": round(math.degrees(iyaw), 1)})
                f.flush()
                continue

            # ⚠ KOPRU karesi tespit SAYILMAZ: sayac islemeye devam eder,
            # faz yine zamaninda biter. Yalniz komut TAZELENIR.
            if kopru_kare:
                kayip_sayac += 1
                if kayip_sayac >= kayip_kare_esik:
                    print(f"[IBVS] {kayip_kare_esik} ardışık kutusuz kare → 'kayip'")
                    return "kayip"
            else:
                kayip_sayac = 0
                kor_baslangic = None   # kutu geri geldi → kör sayaç sıfırlanır
            cx, cy, bw, bh, conf = kutu

            # ── ATALET LOS AÇILARI + HIZLARI (lead nişanı girdisi) ──
            # Piksel hızı DEĞİL: yaw kontrolcüsü kutuyu merkeze çektiği için
            # piksel hızı kendi düzeltmemizi içerir. Atalet açısı = gövde
            # açısı + aracın kendi duruşu → gerçek LOS dönüşü kalır.
            ipitch = iris.get("pitch", 0.0)
            iroll = iris.get("roll", 0.0)
            # ⚠ Bu açı LEAD nişanının girdisi (los_hiz). Telafisiz halinde
            # aracın YATIŞI sahte LOS dönüş hızı üretiyordu — manevrada lead
            # de bozuluyordu. Aynı telafi burada da uygulanır.
            # ── λ̇ ICIN YAW'I KARENIN ANINA HIZALA (bkz. Cfg.YAW_HIZALA_S) ──
            # Komut yolu iyaw'i (SIMDIKI) kullanmaya devam eder; burada
            # hesaplanan los_az YALNIZ los_hiz (λ̇) icin.
            _tnow = time.perf_counter()
            yaw_gecmis.append((_tnow, iyaw))
            while len(yaw_gecmis) > 240:
                yaw_gecmis.pop(0)
            _iyaw_lam = iyaw
            _D = float(getattr(cfg, "YAW_HIZALA_S", 0.0) or 0.0)
            if _D > 0.0 and len(yaw_gecmis) >= 2:
                _tk = (kayit.get("t") or _tnow) - _D      # karenin cekildigi an
                if _tk <= yaw_gecmis[0][0]:
                    _iyaw_lam = yaw_gecmis[0][1]
                else:
                    for _i in range(len(yaw_gecmis) - 1, 0, -1):
                        _ta, _ya = yaw_gecmis[_i - 1]
                        _tb, _yb = yaw_gecmis[_i]
                        if _ta <= _tk <= _tb:
                            _w = (_tk - _ta) / max(_tb - _ta, 1e-9)
                            # aci interpolasyonu (sarma korunur)
                            _iyaw_lam = normalize_angle(
                                _ya + _w * normalize_angle(_yb - _ya))
                            break
            if cfg.ROLL_TELAFI:
                _az_s, _ = los_seviye(cx, cy, iroll, ipitch, cfg)
                los_az = normalize_angle(_iyaw_lam + _az_s)
            else:
                _az_s = math.atan((cx - cfg.CX_NISAN) / geo.FX)
                los_az = normalize_angle(_iyaw_lam + _az_s)

            # ── KADRAJ ICI KAYMA HIZI (bkz. Cfg.BURUN_KD) ────────────────
            # "Kutu sola/saga kaymaya basladiysa burnu o tarafa hizlandir."
            # ⚠ Bu ATALET LOS HIZI DEGIL: yaw'a hic bagli degil, saf piksel
            # gozlemi. lam olculen sekilde 4-7 kat sisik oldugu icin buruna
            # ONU baglamiyoruz. 0.30 s pencerede en kucuk kareler egimi
            # (ardisik fark 1 px jitter'da 21 °/s sahte hiz uretiyordu).
            eps_gecmis.append((_tnow, _az_s))
            while eps_gecmis and _tnow - eps_gecmis[0][0] > 0.30:
                eps_gecmis.pop(0)
            eps_hizi = 0.0
            if len(eps_gecmis) >= 3:
                _k = len(eps_gecmis)
                _tm = sum(g[0] for g in eps_gecmis) / _k
                _em = sum(g[1] for g in eps_gecmis) / _k
                _sxx = sum((g[0] - _tm) ** 2 for g in eps_gecmis)
                if _sxx > 1e-12:
                    eps_hizi = clamp(
                        sum((g[0] - _tm) * (g[1] - _em) for g in eps_gecmis) / _sxx,
                        -6.0, 6.0)
            # ⚠ T1a: DİKEY BİLEREK DOKUNULMADI (tek değişkenli test).
            # ⚠ T1c (bkz. Cfg.TERM_ROLL): `los_el` yukselis HIZININ girdisidir
            #   ve o hiz terminalde `lead_el` olarak dikey nisana biner. Yani
            #   nisani duzeltip bu girdiyi duzeltmemek, ayni kavrami YARIM
            #   baglamaktir. Ayni FARK bicimi; TERM_ROLL kapaliyken TAM 0.
            los_el = piksel_elev(cy, cfg) + ipitch
            if getattr(cfg, "TERM_ROLL", False):
                _, _elr = los_seviye(cx, cy, iroll, ipitch, cfg)
                _, _eln = los_seviye(cx, cy, 0.0, ipitch, cfg)
                los_el += (_elr - _eln)
            if los_az_onceki is not None and 1e-3 < dt < 0.5:
                a_ = cfg.LEAD_EMA
                los_hiz[0] = (a_ * (normalize_angle(los_az - los_az_onceki) / dt)
                              + (1 - a_) * los_hiz[0])
                los_hiz[1] = (a_ * ((los_el - los_el_onceki) / dt)
                              + (1 - a_) * los_hiz[1])
            los_az_onceki, los_el_onceki = los_az, los_el

            # ── KUTU BUYUME HIZI SINIRI (bkz. Cfg.KUTU_HIZ_SINIRI) ────────
            # ⚠ Yalniz BUYUMEYI sinirlar; kuculme serbest.
            if getattr(cfg, "KUTU_HIZ_SINIRI", False) and kutu_son is not None:
                _dt_k = now - kutu_son[0]
                if 1e-3 < _dt_k < 1.0:
                    _b0 = kutu_son[1]
                    # ⚠ M-KAL TUTARLILIK: bu tavan ṙ = R·(ds/dt)/s'den gelir,
                    # yani R'yi UREten sabitle AYNI olmak zorunda. Menzil
                    # kapilari (KW / OFS) acikken R artik 202.6/boyut DEGIL;
                    # eski ifade orada YANLIS bir tavan uretir.
                    # ⛔ VARSAYILANDA IFADE HIC DEGISMEZ (tek ulp bile):
                    #    kapilar kapaliyken eski satir aynen calisir.
                    if (float(getattr(cfg, "MENZIL_KW", 0.0) or 0.0) > 0.0
                            or float(getattr(cfg, "MENZIL_OFS_PX", 0.0) or 0.0) != 0.0):
                        _R0 = menzil_kutudan(_b0, cfg, kutu_son[2])
                        _tavan = (_b0 * float(cfg.KUTU_MAX_KAPANMA)
                                  / max(_R0, 1e-6))
                    else:
                        _tavan = (_b0 * _b0 * float(cfg.KUTU_MAX_KAPANMA)
                                  / max(cfg.MENZIL_PX_M, 1e-6))
                    _izin = _b0 + _tavan * _dt_k
                    _b_ham = math.sqrt(max(bw * bh, 1e-9))
                    if _b_ham > _izin and _izin > 1.0:
                        _olcek = _izin / _b_ham
                        bw *= _olcek
                        bh *= _olcek
                        kutu_kirp += 1
                        if kutu_kirp in (1, 50) or kutu_kirp % 500 == 0:
                            print("[IBVS] KUTU HIZ SINIRI: %.0f -> %.0f px "
                                  "(fiziken imkansiz buyume) [toplam %d]"
                                  % (_b_ham, _izin, kutu_kirp))
            # ⚠ `w` de saklanir: menzil modeli MENZIL_KW acikken GENISLIGI
            #   kullanir, tavan da o modelden cikmali (yukari bak).
            kutu_son = (now, math.sqrt(max(bw * bh, 1e-9)), bw)

            # atalet koprusu icin son GERCEK tespitin kerterizini sakla
            if not kopru_kare:
                son_tespit = (now, los_az, cy, bw, bh)

            # ── λ̇ KESTİRİMİ: EN KÜÇÜK KARELER PENCERESİ (PN açıkken) ──────
            # ⚠ NEDEN: ardışık-fark türevi piksel gürültüsünü σ_px/(FX·dt) ile
            # büyütür. 1 px jitter ve dt=1/62 s → 21 °/s SAHTE LOS hızı; PN
            # bunu N katına çıkarır. Pencere üzerinden eğim, gürültüyü
            # ~√örnek kadar bastırır ve dt'ye duyarsızdır (tespit kesintili
            # geldiği için dt zaten düzensiz).
            # ÖLÇÜLDÜ: gürültüsüz koşuda EMA türevi 9/30, pencere 27/30.
            if cfg.PN_N > 0.0 and cfg.PN_PENCERE_S > 0.0:
                _tn = time.perf_counter()
                if los_gecmis:
                    _onc = los_gecmis[-1][1]
                    _acik = _onc + normalize_angle(los_az - _onc)
                else:
                    _acik = los_az
                los_gecmis.append((_tn, _acik))
                while los_gecmis and _tn - los_gecmis[0][0] > cfg.PN_PENCERE_S:
                    los_gecmis.pop(0)
                if len(los_gecmis) >= 3:
                    _k = len(los_gecmis)
                    _tm = sum(g[0] for g in los_gecmis) / _k
                    _lm = sum(g[1] for g in los_gecmis) / _k
                    _sxx = sum((g[0] - _tm) ** 2 for g in los_gecmis)
                    if _sxx > 1e-12:
                        los_hiz[0] = clamp(
                            sum((g[0] - _tm) * (g[1] - _lm) for g in los_gecmis) / _sxx,
                            -6.0, 6.0)

            # ── KAPANMA HIZI, GÖRÜNTÜDEN (bkz. Cfg.KAPANMA) ──
            # R = MENZIL_PX_M/boyut  ⇒  ṙ = −dR/dt = R·(dboyut/dt)/boyut
            # GPS YOK: yalnız kutu boyutunun büyüme hızı. Kutu titrediği için
            # EMA'lanır; ilk karede geçmiş yok, None kalır (komut o turda
            # eski davranışa düşer — güvenli taraf).
            boyut_simdi = math.sqrt(bw * bh)
            # ⚠ M-KAL: ṙ'nin `s`'i menzil modelinin `s`'i OLMAK ZORUNDA
            # (bkz. menzil_olcek). Varsayilanda _s_simdi == boyut_simdi ->
            # BIT-AYNI; kapi acildiginda R ve turevi AYNI modelden gelir.
            _s_simdi = menzil_olcek(boyut_simdi, cfg, bw)
            if (boyut_onceki is not None and boyut_simdi > 1e-6
                    and 1e-3 < dt < 0.5):
                _R = menzil_kutudan(boyut_simdi, cfg, bw)
                _rdot = _R * ((_s_simdi - boyut_onceki) / dt) / max(_s_simdi, 1e-6)
                _rdot = clamp(_rdot, -30.0, 30.0)      # gürültü kalkanı
                kapanma = (_rdot if kapanma is None else
                           cfg.KAPANMA_EMA * _rdot
                           + (1.0 - cfg.KAPANMA_EMA) * kapanma)
            boyut_onceki = _s_simdi
            # TERMİNAL MANDALI: kutu eşiği aşınca hücuma taahhüt, geri dönüş yok
            # + NİŞAN KAPISI: kötü nişanla taahhüt etme (bkz. TERM_NISAN_MAX_M)
            # ⚠ 2026-08-16 GECE — HAYALET TERMINAL KAPATILDI.
            #   OLCULDU (1318 s, 6 angajman): TERMINAL ilan edilen karelerin
            #   TAMAMI kopru (hayalet) karesiydi. Mekanizma:
            #     * boyut_simdi hayalet karede son_tespit[3..4]'ten geliyor,
            #       yani SON GERCEK tespitin boyutu her hayalet karede YENIDEN
            #       sinaniyor -> bir kez >=25 px olduysa kapi her karede deneniyor.
            #     * cx hayalette CX_NISAN + FX*tan(los_son - iris_yaw); biz
            #       kerterize DONDUKCE eps->0, dolayisiyla _yanal->0 -> nisan
            #       kapisi KENDILIGINDEN aciliyor.
            #   Sonuc: gercek karede "nisan kotu, taahhut etme" denen an, birkac
            #   hayalet kare sonra "nisan mukemmel" diye mandallaniyordu ve
            #   v_los V_TERMINAL'e sabitlenip conf=0 bir hayaletin ustune
            #   daliniyordu. Kopru karesinde kerteriz hatasi medyan 141.6°.
            # ── DUZ SEGMENT KAPISI (2026-08-17, arkeoloji bulgusundan) ──
            # OLCULDU (869 angajman, 16-17 Agustos): CPA aninda hedef
            #   DUZ kesimde  (|omega| < 5 deg/s)  -> P(<3 m) = 0.161
            #   gecis        (5-20 deg/s)         -> P(<3 m) = 0.054
            #   keskin donus (>20 deg/s)          -> P(<3 m) = 0.037
            # Yani duz segmentte vurus olasiligi 4.3 KAT. Ve hedef sabit bir
            # ovalde uctugu icin duz segment MUTLAKA geliyor: 29.63 s turun
            # ~12.7 saniyesi duz. Terminal hucumu 8 m'den ~1.3 s suruyor --
            # duz segmente RAHAT sigar.
            # Bu kapi: kerteriz donuyorken taahhut ETME, duz segmenti bekle.
            # 0 = kapali (eski davranis).
            _lam_esik = float(getattr(cfg, "TERM_LAM_MAX_DEG", 0.0) or 0.0)
            _lam_ok = (_lam_esik <= 0.0
                       or abs(math.degrees(los_hiz[0])) <= _lam_esik)
            # ── KESİNTİSİZ KİLİT KAPISI (2026-08-17, kullanıcı şartı) ──────
            # ÖLÇÜLDÜ: bu mandal kilit süresini HİÇ kontrol etmiyordu —
            # koşullar yalnız kutu boyutu + nişan kapısıydı. 217 mandal
            # açılışında kesintisiz gerçek tespit medyanı 0.00 s (tümü),
            # 2026-08-17'de 0.16 s; yalnız %1.4'ü ≥5 s. Yani araç 5 s kilit
            # OLMADAN terminale taahhüt ediyordu. Kapı AVCI_KILIT_S ile açılır.
            _kilit_ok = kk.gecti()
            if (not terminal_mandal and not kopru_kare and conf > 0.0
                    and _lam_ok and boyut_simdi >= cfg.TERMINAL_BOYUT
                    and not _kilit_ok and not _kilit_uyari):
                _kilit_uyari = True
                print(f"[IBVS] ⏱ KESİNTİSİZ KİLİT KAPISI: {kk.sure:.2f} s < "
                      f"{KilitKapiCfg.ESIK_S:.1f} s — kutu eşiği aşıldı ama "
                      f"TERMİNALE TAAHHÜT YOK, kilit dolana kadar takip")
            if (not terminal_mandal and not kopru_kare and conf > 0.0
                    and _lam_ok and _kilit_ok
                    and boyut_simdi >= cfg.TERMINAL_BOYUT):
                # ⛔ 2026-08-17 ONCESI BURADA `160.0` HARDCODED IDI ve yasa
                #   ayni kareye `Cfg.MENZIL_PX_M`=202.6 ile bakiyordu -> ayni
                #   fiziksel menzil icin IKI FARKLI SAYI (%27 kopukluk).
                #   Artik tek fonksiyondan gecer; sabit `MENZIL_TERM_PX_M`
                #   (varsayilan 160.0, yani BIT-AYNI) ile ayarlanir.
                #   ⚠ OLCUM (n=5722 terminal karesi): gercek medyan 5.85 m,
                #     160.0 -> 5.13 m (−12%), 202.6 -> 6.50 m (+11%).
                #     Yani IKIZ, yasanin sabitinden DAHA DOGRU. "Kapiyi
                #     202.6'ya esitle" demek kapiyi %27 GEVSETMEKTIR.
                _men = menzil_kutudan(boyut_simdi, cfg, bw, terminal_kapi=True)
                _eps = math.atan((cx - cfg.CX_NISAN) / geo.FX)
                _yanal = _men * abs(math.tan(_eps))
                if cfg.TERM_NISAN_MAX_M <= 0.0 or _yanal <= cfg.TERM_NISAN_MAX_M:
                    terminal_mandal = True
                    print(f"[IBVS] ⚡ TERMİNAL HÜCUM (kutu {boyut_simdi:.0f}px "
                          f"≥ {cfg.TERMINAL_BOYUT:.0f}, ~{_men:.1f} m, yanal "
                          f"sapma {_yanal:.1f} m, KESİNTİSİZ KİLİT "
                          f"{kk.sure:.2f} s) — fren yok, tam taahhüt")
                    kilit_denetim.yaz(
                        "TERMINAL", kk,
                        "kutu>=%.0fpx & nisan<=%.1fm%s"
                        % (cfg.TERMINAL_BOYUT, cfg.TERM_NISAN_MAX_M,
                           (" & kesintisiz>=%.1fs" % KilitKapiCfg.ESIK_S)
                           if KilitKapiCfg.acik() else ""),
                        {"menzil_m": _men, "boyut_px": boyut_simdi,
                         "not": "yanal_m=%.2f conf=%.2f" % (_yanal, conf)})
                elif not nisan_uyari:
                    nisan_uyari = True
                    print(f"[IBVS] NİŞAN KAPISI: yanal sapma {_yanal:.1f} m > "
                          f"{cfg.TERM_NISAN_MAX_M:.1f} m (~{_men:.1f} m menzilde, "
                          f"eps {math.degrees(_eps):+.0f}°) -> kör taahhüt YOK, "
                          f"takibe devam")
            vx, vy, vz, yaw_hedef, hiz_I, tani = komut(cx, cy, bw, bh, iyaw,
                                                       hiz_I, dt, cfg,
                                                       terminal_mandal,
                                                       tuple(los_hiz), ipitch,
                                                       float(iris.get("vz", 0.0) or 0.0),
                                                       kapanma, iroll,
                                                       yaw_hizi, psi_v,
                                                       eps_hizi, v_kapi)
            psi_v = tani.get("psi_v", psi_v)      # PN durumu taşınır
            v_kapi = tani.get("v_kapi", v_kapi)   # M1 kapı rampası taşınır

            # ══ KES · KUTUDAN TAM DURUM KESTIRIMI (bkz. Cfg.KESTIRIM) ══════
            # ⛔ SALT GOZLEM: asagidaki hicbir sayi komuta, kapiya ya da esige
            #   girmez. Yalnizca `kest_*` sutunlarini doldurur.
            # ⚠ KAPI KAPALIYSA (varsayilan) blok HIC calismaz -> CPU maliyeti
            #   de sifir, davranis bit-ayni.
            kest = None
            kest_v = None
            if getattr(cfg, "KESTIRIM", False) and not kopru_kare:
                _Rk = tani.get("menzil")
                if _Rk is not None and math.isfinite(_Rk) and _Rk > 0.0:
                    # ⚠ AYNI BAYATLIK TELAFISI: yasa komutu `iyaw − hizala`
                    #   ile kurduysa kestirim de oyle kurmali; yoksa iki ayri
                    #   "mutlak yon" tanimi olusur (tam da menzil ikizinin
                    #   yaptigi hata). hizala=0 iken fark yok.
                    kest = BG.durum_kestir(cx, cy, bw, bh, iroll, ipitch, iyaw,
                                           _Rk, dpsi=tani.get("hizala", 0.0))
                    _o = kest["ofset_ned"]
                    kest_gecmis.append((now, _o[0], _o[1], _o[2]))
                    _pw = float(getattr(cfg, "KESTIRIM_PENCERE_S", 0.40) or 0.40)
                    while kest_gecmis and now - kest_gecmis[0][0] > _pw:
                        kest_gecmis.pop(0)
                    if len(kest_gecmis) >= 3:
                        # ⚠ D0: v_kendi ARACIN KENDI hiz sensorudur (get_iris),
                        #   hedefin GPS'i DEGIL. Bagil turevden mutlak hiza
                        #   gecmenin TEK yolu budur (bkz. bbox_geometri.
                        #   hedef_hiz_ned: "kutu buyuyor demek hedef
                        #   yaklasiyor" ancak BIZ dururken dogrudur).
                        _vk = (float(iris.get("vx", 0.0) or 0.0),
                               float(iris.get("vy", 0.0) or 0.0),
                               float(iris.get("vz", 0.0) or 0.0))
                        kest_v = BG.hedef_hiz_ned(
                            [g[0] for g in kest_gecmis],
                            [(g[1], g[2], g[3]) for g in kest_gecmis], _vk)
                else:
                    kest_gecmis.clear()   # menzil yok -> pencere bozulmasin
            # ── YAW SLEW SINIRI (bkz. Cfg.YAW_RATE_MAX) ──
            # HIZ (vx, vy) yaw_hedef'ten hesaplandı ve DEĞİŞMEZ: nişan hedefin
            # gerçek yönünde kalır. Sınırlanan yalnız BURUNUN dönme hızı.
            if cmd_yaw is None:
                cmd_yaw = iyaw
            yaw_err = normalize_angle(yaw_hedef - cmd_yaw)
            adim = clamp(yaw_err, -math.radians(cfg.YAW_RATE_MAX_DEG) * dt,
                         math.radians(cfg.YAW_RATE_MAX_DEG) * dt)
            cmd_yaw = normalize_angle(cmd_yaw + adim)
            yaw_cmd = cmd_yaw

            # ── IVME SINIRI (komut hizi sicramasin) ──────────────────────
            # AYRIK TAVAN (bkz. Cfg.ACCEL_SPLIT): yatay tavan kamerayi korur
            # (burun egimi = atan(a/g), gokyuzu arka plani kaybolur), dikey
            # tavani ise yalniz itki butcesi baglar -- kamera acisi degismez.
            # Tek 3B tavanda kameranin YATAY kisiti dikeye de dayatiliyordu.
            # ⚠ MEKANIZMA KAPISI: split acilinca bu logda |d(v_cmd)/dt| ust
            #   siniri 12.0'dan sqrt(12^2+10^2)=15.6'ya cikmali. Olculdu:
            #   split KAPALIYKEN >12.25 olan tik orani %0.0 (n=10823, sert
            #   kenar). Acinca >12.5 orani belirgin sekilde 0'dan buyuk
            #   olmazsa yama devreye GIRMEMISTIR ve deney gecersizdir.
            if getattr(cfg, "ACCEL_SPLIT", False):
                vx, vy, vz = limit_acceleration_split(
                    vx, vy, vz, vx_p, vy_p, vz_p,
                    cfg.MAX_ACCEL, float(getattr(cfg, "MAX_ACCEL_V", 10.0)), dt)
            else:
                vx, vy, vz = limit_acceleration(vx, vy, vz, vx_p, vy_p, vz_p,
                                                cfg.MAX_ACCEL, dt)
            vx_p, vy_p, vz_p = vx, vy, vz
            son_v_cmd = (vx, vy, vz, yaw_cmd)
            send_velocity(conn, vx, vy, vz, yaw_cmd)

            w_csv.writerow({
                "t": round(now, 3), "dt": round(dt, 4),
                "durum": "TERMINAL" if terminal_mandal else "IBVS",
                "cx": round(cx, 1), "cy": round(cy, 1),
                "w": round(bw, 1), "h": round(bh, 1),
                "boyut": round(tani["boyut"], 1), "conf": round(conf, 3),
                "eps_yaw_deg": round(math.degrees(tani["eps_yaw"]), 1),
                # ÖLÇÜM SÜTUNU: telafisiz okuma. Farkı (ham − telafili) roll'e
                # karşı çizince T1a'nın uçuşta ne kadar bağladığı doğrudan
                # görülür. Yalnız log — güdüm bunu kullanmaz.
                "eps_yaw_ham_deg": round(math.degrees(tani["eps_yaw_ham"]), 1),
                "eps_elev_deg": round(math.degrees(tani["eps_elev"]), 1),
                "eps_elev_ham_deg": round(math.degrees(tani["eps_elev_ham"]), 1),
                "iris_roll_deg": round(math.degrees(iroll), 1),
                "iris_pitch_deg": round(math.degrees(ipitch), 1),
                "iris_yaw_deg": round(math.degrees(iyaw), 1),
                "boyut_hata": round(tani["hata"], 1),
                "hiz_I": round(hiz_I, 2), "v_los": round(tani["v_los"], 2),
                "kacis_ek": round(tani["kacis_ek"], 2),
                "gecikme_s": (round(gecikme_s, 4)
                              if gecikme_s is not None else ""),
                "eps_hiz_deg": round(math.degrees(tani["eps_hiz"]), 1),
                "sonum_deg": round(math.degrees(tani["sonum"]), 2),
                "donus_tavan": ("" if tani["donus_tavan"] is None
                                else round(tani["donus_tavan"], 2)),
                "lead_az_deg": round(math.degrees(tani["lead_az"]), 2),
                "los_hiz_az": round(los_hiz[0], 3), "los_hiz_el": round(los_hiz[1], 3),
                # ── PN TESHISI: sapma = PN'in saf takip yonunden ne kadar
                # ayrildigi (ONGORU ACISI). 0'a yapisiyorsa PN calismiyor
                # demektir; +-60 dereceyi asiyorsa lam kestirimi bozuktur.
                "pn_n": cfg.PN_N,
                "psi_v_deg": round(math.degrees(tani["psi_v"]), 1),
                "pn_sapma_deg": round(math.degrees(
                    normalize_angle(tani["psi_v"] - tani["pn_taban"])), 2),
                "pn_ornek": len(los_gecmis),
                "kopru": 1 if kopru_kare else 0,
                # kadraj ici kayma hizi (buruna giren turev terimi)
                "eps_hizi_deg": round(math.degrees(tani.get("eps_hizi", 0.0)), 1),
                "vx_cmd": round(vx, 2), "vy_cmd": round(vy, 2),
                "vz_cmd": round(vz, 2),
                "yaw_cmd_deg": round(math.degrees(yaw_cmd), 1),
                # ⚠ 2026-08-16: burada SABIT 0 yaziliyordu -> hayalet karede
                #   sayac az once artmis olsa bile log 0 gosteriyordu, yani
                #   koprunun izini bu sutun SILIYORDU. Gercek degeri yaz.
                "kayip_sayac": kayip_sayac,
                "cy_nisan": round(tani["cy_nisan"], 1),
                # ── MANEVRA TESHISI + M1/M2 MEKANIZMA KAPILARI ──────────
                # DOYGUNLUK = |w_talep| > w_tavan olan kare orani.
                # Taban olcum (B_ayna_DPP, 3467 kare): %54.1.
                "w_talep_deg": ("" if tani["w_ham"] is None
                                else round(math.degrees(tani["w_ham"]), 1)),
                "w_tavan_deg": round(math.degrees(tani["w_tavan"]), 1),
                "w_uyg_deg": ("" if tani["w_uyg"] is None
                              else round(math.degrees(tani["w_uyg"]), 1)),
                "donus_kapi_v": ("" if tani["donus_kapi"] is None
                                 else round(tani["donus_kapi"], 2)),
                "arac_lead_deg": round(math.degrees(tani["arac_lead"]), 2),
                # ── Y2 / M-KAL MEKANIZMA KAPILARI ──
                "hizala_deg": round(math.degrees(tani["hizala"]), 3),
                "yaw_hizi_dps": round(math.degrees(tani["yaw_hizi"]), 2),
                "menzil_m": ("" if tani["menzil"] is None
                             else round(tani["menzil"], 2)),
                "menzil_term_m": ("" if tani["menzil_term"] is None
                                  else round(tani["menzil_term"], 2)),
                # ── T1c MEKANIZMA KAPISI ──
                "term_roll_deg": round(math.degrees(tani["term_roll"]), 3),
                # ── KES · TAM DURUM KESTIRIMI (salt gozlem) ──
                "kest_R_m": ("" if kest is None else round(kest["menzil_m"], 2)),
                "kest_dz_m": ("" if kest is None else round(kest["dz_m"], 2)),
                "kest_az_deg": ("" if kest is None
                                else round(math.degrees(kest["az"]), 2)),
                "kest_el_deg": ("" if kest is None
                                else round(math.degrees(kest["el"]), 2)),
                "kest_vh_ms": ("" if kest_v is None
                               else round(math.hypot(kest_v[0], kest_v[1]), 2)),
                "kest_vz_ms": ("" if kest_v is None else round(kest_v[2], 2)),
                "kest_rota_deg": (
                    "" if kest_v is None
                    else round(math.degrees(
                        BG.rota_ve_yer_hizi(kest_v[0], kest_v[1])[0]), 1)),
                "kest_aspect_deg": (
                    "" if (kest is None or kest_v is None
                           or BG.aspect_hizdan(kest["ofset_ned"], kest_v) is None)
                    else round(math.degrees(
                        BG.aspect_hizdan(kest["ofset_ned"], kest_v)), 1)),
                "kest_n": len(kest_gecmis),
            })
            f.flush()

            _elapsed = time.monotonic() - now
            if _elapsed < loop_period:
                time.sleep(loop_period - _elapsed)

        send_velocity(conn, 0.0, 0.0, 0.0, cmd_yaw or 0.0)
        return "durduruldu"
    finally:
        f.close()
        print(f"[IBVS] log kapatıldı: {csv_yol}")
