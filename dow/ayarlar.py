# -*- coding: utf-8 -*-
"""
================================================================================
MERKEZİ AYARLAR — panelden CANLI değiştirilebilir
================================================================================
Gazebo'daki `bbox_ibvs.Cfg` ile aynı desen: SINIF NİTELİKLERİ. Güdüm döngüsü
her karede `Ayar.<ALAN>` okur; panel sınıf niteliğini değiştirince bir sonraki
kareden itibaren geçerli olur — UÇUŞ SIRASINDA, yeniden başlatmadan.
(CLAUDE.md §6'nın DoW karşılığı.)
================================================================================
"""
import os


def _f(ad, v):  return float(os.environ.get(ad, v))
def _b(ad, v):  return os.environ.get(ad, str(int(v))).strip() not in ("0", "", "false", "False")


class _IbvsKopru:
    """Panelin IBVS ayarlarını canlı değiştirebilmesi için köprü:
    Ayar.<ALAN> okunduğunda/yazıldığında IbvsCfg'ye yansır."""
    pass


class Ayar:
    # ================= AŞAMA ANAHTARLARI =================
    # ⚠ GELİŞTİRME KİPİ (2026-08-22, kullanıcı kararı):
    #   Şimdilik BOZUK GPS + filtre yerine DOĞRUDAN TRUTH kullanılıyor.
    #   Amaç: GPS güdümünün kendisini (istasyon tutma) filtre gürültüsünden
    #   ARINDIRILMIŞ olarak düzeltmek. Bu iş bitince GPS_KAYNAK="filtre"
    #   yapılıp gnss_filtre.py yeniden devreye alınacak.
    #   ⛔ YARIŞMADA "truth" KULLANILAMAZ — orada bu kanal gelmez.
    GPS_KAYNAK   = os.environ.get("DOW_GPS_KAYNAK", "truth")   # "truth" | "filtre"

    # ⚠ Görsel faz ŞİMDİLİK KAPALI (kullanıcı kararı): önce GPS istasyon
    #   tutma düzelsin, sonra görsele geçilsin. Kapalıyken dedektör hiç
    #   koşmaz -> döngü 10 FPS yerine ~50 Hz olur, testler ÇOK hızlanır.
    # ================= GÜDÜM KİPİ (panelden CANLI seçilir) =================
    # Kullanıcı isteği (2026-08-22): "arayüze üç buton koy — hibrit, gps,
    # görsel. gps'e basınca sadece GPS güdümü, görsele basınca sadece görsel,
    # hibritte faz geçişiyle. Böylece sadece GPS'te uçurup detection modeli
    # aracı tam olarak nasıl tespit ediyor görebiliriz."
    #   "gps"    : YALNIZ istasyon tutma. Görsel faza ASLA geçilmez.
    #              Dedektör yine koşar (panel için) ama güdüme GİRMEZ.
    #   "gorsel" : kilit kurulunca görsele geçer ve GERİ DÖNMEZ.
    #              (İlk kilide kadar istasyon tutma yaklaştırır.)
    #   "hibrit" : 10 kare tespit -> görsel, 20 kare tespitsiz -> GPS.
    GUDUM_KIPI = os.environ.get("DOW_KIP", "hibrit").strip().lower()


    GORSEL_AKTIF = _b("DOW_GORSEL", False)

    # DEDEKTÖRÜ SADECE GÖSTER — güdüme GİRMEZ.
    # Kullanıcı panelde hedefin nasıl algılandığını görmek istiyor ama
    # güdüm GPS'te kalmalı. Bu anahtar dedektörü yalnız PANEL için koşturur;
    # çıktısı Beyin'e ASLA verilmez (GORSEL_AKTIF ayrı anahtardır).
    DEDEKTOR_GOSTER = _b("DOW_DET_GOSTER", True)
    DEDEKTOR_HZ     = _f("DOW_DET_HZ", 2.0)   # panel için çıkarım hızı

    # ================= PANEL MALİYET TAVANLARI =================
    # ⛔ ÖLÇÜLDÜ 2026-08-22 — arayüz UÇUŞU BOZUYORDU, yalnız yavaşlatmıyordu.
    #   izleyici.py ekranı SANİYEDE 180-330 KEZ kopyalıyordu (1920x1080 =
    #   8.3 MB/kare -> ~2 GB/s X11 trafiği) ve aynı GPU'da YOLO'yu imgsz
    #   1920'de tam hızda koşuyordu. Oyun (UE5/Vulkan) aynı GPU + aynı X
    #   sunucusunda olduğu için başarımı düştü. SONUÇ (GA04 vs GV11):
    #     istasyon hatası 5.3 m -> 25.3 m,  ≤15 m oranı %88 -> %2,
    #     v_istek 120 s boyunca 33 m/s TAVANINDA doyumda kaldı.
    #   Oyunun kendisi ~60-120 FPS basıyor; 30 Hz üstü kopyalama zaten AYNI
    #   kareyi tekrar okumak demek — bedava değil, bedelli hiçlik.
    #   ÖLÇÜLDÜ (oyun koşarken, 2026-08-22): tam kare X11 aktarımı
    #   13.3 ms + BGRA->RGB 1.25 ms = 14.6 ms. Yani 15 Hz ~ %22 çekirdek VE
    #   saniyede 15 GPU senkronu. Asıl bedel CPU değil: her XGetImage oyunun
    #   çizim boru hattını SENKRONA zorluyor. Eski sınırsız döngü bu yüzden
    #   oyunu aç bırakıyordu. Dedektör zaten 5 Hz'de kutu üretiyor.
    PANEL_YAKALA_HZ = _f("DOW_PANEL_YAKALA_HZ", 15.0)
    PANEL_DET_HZ    = _f("DOW_PANEL_DET_HZ", 5.0)
    # ⛔ GÖRSEL FAZDA DA TAVAN ŞART (ölçüldü 2026-08-22).
    #   Görsel fazda YOLO her kontrol tikinde koşunca (~19 Hz) oyun aç kaldı
    #   ve GPS istasyon tutma 4.96 m -> 17.76 m'ye BOZULDU; `v_istek`
    #   karelerin %59'unda 33 m/s tavanında doyuma girdi (GPS kipinde %12).
    #   Yani dedektörün hızı GÜDÜMÜ bozuyor. Güdüm zaten son kutuyu
    #   tutuyor; çıkarımı tavanlamak kontrol bant genişliğini de ARTIRIR.
    GORSEL_DET_HZ   = _f("DOW_GORSEL_DET_HZ", 10.0)
    PANEL_OLCEK     = _f("DOW_PANEL_OLCEK", 0.5)   # JPEG'e giden küçültme

    # ================= KALKIŞ =================
    KALKIS_ALT_M   = _f("DOW_KALKIS_ALT", 45.0)   # zemine göreli
    KALKIS_VZ      = _f("DOW_KALKIS_VZ", 12.0)
    KALKIS_TOL_M   = 3.0

    # ================= İSTASYON (GPS fazının HEDEFİ) =================
    # Gazebo'daki çözülmüş tasarım: hedefin KUYRUĞUNDA, biraz ALTINDA dur.
    # Kamera 26.5° YUKARI baktığı için "altında" olmak hedefi kadraja sokar.
    # ⭐ ÖLÇÜLDÜ (GA03 taraması + GA04 n=4 doğrulaması): 15 m EN İYİ NOKTA.
    #   35 m -> ist_hata 6.28 m, tespit %48, kutu 20 px
    #   25 m -> ist_hata 5.63 m, tespit %77, kutu 29 px
    #   15 m -> ist_hata 5.28 m, tespit %90, kutu 46 px   <- SEÇİLDİ
    #    8 m -> ist_hata 4.81 m, tespit %79 (hedef kadraja SIĞMIYOR)
    #
    # ⭐⭐ YENİDEN ÖLÇÜLDÜ 2026-08-22 (kampanya GK+GK2, 24 uçuş) — 8 m / 0.75.
    #   Kullanıcı isteği: "istasyonu hedef araca daha da yaklaştıralım, bir de
    #   biraz gerisine ve ALTINA alalım ki hedef kadraja girdiğinde arka planı
    #   gökyüzü olsun; detection modeli daha iyi algılayabilir."
    #   GK2 (3 kol x 4 koşu x 90 s, dönüşümlü) GERÇEK tespit oranı medyanı:
    #     15 m / 0.45  -> %66.9   kutu 47.7 px   yanlış-pozitif %11.4
    #      8 m / 0.45  -> %76.0   kutu 73.5 px   yanlış-pozitif  %4.0
    #      8 m / 0.75  -> %88.8   kutu 69.3 px   yanlış-pozitif  %3.7   <- SEÇİLDİ
    #   Kolların aralıkları HİÇ ÖRTÜŞMÜYOR (en kötü 8/0.75 = %82.9 >
    #   en iyi 8/0.45 = %79.4 > en iyi taban = %70.7).
    #   Geçerlilik eşleri geçti: hedef kadrajda %100, ist_hata/R = 0.63,
    #   kaza 0/12, en yakın 12.6 m, oturma 5.9 s (tabanla aynı).
    ISTASYON_MENZIL_M = _f("DOW_IST_MENZIL", 8.0)   # hedefin kaç m ARKASINDA
    ISTASYON_ALT_M    = _f("DOW_IST_ALT", 15.0)     # kaç m ALTINDA (oran 0 ise)
    # Alt ofseti menzile ORANTILI tut: h = R * ORAN. tan(26.5°)=0.499 ->
    # 0.45 seçildi (hedef kadraj merkezinin hafif ÜSTÜNDE dursun; gökyüzü
    # arka planı ve "alttan yaklaşma" Gazebo'da da tercih edilmişti).
    #
    # ⭐ İKİ DÜĞME BİRBİRİNDEN BAĞIMSIZ (2026-08-22 geometri hesabı):
    #   MENZİL yalnız KUTU BOYUTUNU değiştirir  (R 15->8 m: 61 -> 114 px)
    #   ORAN   yalnız GÖK PAYINI değiştirir     (0.45->0.75: 232 -> 362 px)
    #   Çünkü yükseliş açısı atan(oran) — menzilden BAĞIMSIZ.
    #   "gök payı" = hedefin kadrajda ufuk çizgisinin kaç piksel ÜSTÜNDE
    #   durduğu. Büyükse arka plan gökyüzü olur (dedektör için temiz zemin).
    ISTASYON_ALT_ORAN = _f("DOW_IST_ALT_ORAN", 0.75)
    # İleri besleme: hedefin hızı komuta DOĞRUDAN eklenir. Bu olmadan saf P
    # kontrolcü hareketli hedefi ASLA yakalayamaz (kalıcı gecikme hatası).
    ISTASYON_KP     = _f("DOW_IST_KP", 0.9)         # 1/s; konum hatası -> hız
    ISTASYON_KP_Z   = _f("DOW_IST_KPZ", 0.9)
    ISTASYON_ILERI  = _b("DOW_IST_ILERI", True)     # hedef hızı ileri besle
    # ⛔ ISTASYON_DONUS_ILERI ÇIKARILDI (2026-08-23) — ölçüldü, elendi.
    #    Ayrıntı ve sayılar: dow/gudum/gps.py başındaki not.
    V_MAX           = _f("DOW_V_MAX", 33.0)         # m/s (araç 34.6 yapabiliyor)
    VZ_MAX_TIRMAN   = 33.5
    VZ_MAX_ALCAL    = 6.95
    YAW_RATE_MAX    = _f("DOW_YAW_MAX", 120.0)      # °/s

    # ================= GÖRSEL DEVİR =================
    # ⛔⛔ YARIŞMA KURALI (kullanıcı 2026-08-22, DİSKALİFİYE SEBEBİ):
    #   "Görsel güdüm sırasında GPS verisini ASLA kullanma; mesafe verisini
    #    bile GPS'ten çekme. Görsel güdüm algoritmasına GPS verisini dahil
    #    etmek diskalifiye sebebi."
    #   Bu yüzden devir kapısı ARTIK GPS MENZİLİNE BAKMIYOR. Kapı tamamen
    #   KAMERA verisinden: ardışık N geçerli tespit.
    #   Yanlış-pozitife karşı koruma (eskiden GPS kapısı yapıyordu) şimdi:
    #     (a) ardışık 10 kare şartı — 10 kare üst üste aynı sahte kutu zor
    #     (b) ibvs.gecerli(): conf >= 0.40, kutu boyutu MENZIL_MIN..MAX
    #         aralığında (3-50 m). 140 m'de üretilen dev yanlış-pozitif
    #         (menzil 1.3 m) bu kapıdan GEÇEMEZ.
    DEVIR_KARE      = int(_f("DOW_DEVIR_KARE", 10))   # ardışık TESPİT -> görsel
    KAYIP_KARE      = int(_f("DOW_KAYIP_KARE", 20))   # ardışık TESPİTSİZ -> GPS

    # ================= ⛔ GELİŞTİRME DEVİR KAPISI — YARIŞMADA KULLANILAMAZ ==
    # Kullanıcı kararı (2026-08-22), gerekçesiyle:
    #   Dedektör MENZİLE şiddetle bağlı (GK2, n=2097 istasyon karesi):
    #     kuyruktan <10°, medyan 14.3 m -> ham tespit %88.2 (8/0.75'te %96.6)
    #     10-20°, medyan 20.2 m         -> %72.5
    #     20-35°, medyan 40.1 m         -> %50.0
    #     35-60°, medyan 69.5 m         -> %32.6
    #   Yani "ardışık 10 kare tespit" kapısı UZAKTA güvenilir sağlanamıyor ve
    #   görsel güdüm üzerinde çalışmayı fiilen bloke ediyor. Dedektörü ekip
    #   arkadaşı düzeltiyor; biz onu beklerken görsel yasayı geliştirebilelim.
    #
    # GEÇİCİ KURAL: drone istasyona OTURDUKTAN sonra ve hedefe ~15 m
    #   menzildeyken görsele devret. Bu, hedefe olan menzili GPS'ten okumayı
    #   gerektirir -> YALNIZ FAZ GEÇİŞİNDE, ayrı anahtarla.
    #
    # ⛔⛔ KULLANICININ ÜSTÜN KURALI DEĞİŞMEDİ: "görsel güdüm sırasında GPS
    #   verisini asla kullanma; görsel güdüm algoritmasına GPS verisini dahil
    #   etmek diskalifiye sebebi." Devir kapısının GPS'e bakması, görsel
    #   YASANIN GPS'e bakması DEĞİLDİR. Görsel faz başladıktan sonra güdüm
    #   hedefin GPS'ini okumaz bile (bekçiler B1/B18/B19 bunu sınar).
    #
    # ⚠ BU KAPI YARIŞMADA KULLANILAMAZ. `YARISMA_KIPI=1` yapısal olarak
    #   kapatır ve sistem kamera-tek kapıya (ardışık DEVIR_KARE tespit) döner.
    #   İyi dedektör gelince bu iskele SÖKÜLÜR (§5.12) ve devir daha uzak
    #   menzilden, yalnız kamerayla yapılır.
    YARISMA_KIPI       = _b("DOW_YARISMA", False)
    DEVIR_ISTASYONDAN  = _b("DOW_DEVIR_ISTASYON", True)
    DEVIR_IST_HATA_M   = _f("DOW_DEVIR_IST_HATA", 8.0)   # oturdu sayılma eşiği
    DEVIR_IST_KARE     = int(_f("DOW_DEVIR_IST_KARE", 25))  # ardışık (~0.5 s)
    DEVIR_MENZIL_M     = _f("DOW_DEVIR_MENZIL", 15.0)    # hedefe GPS menzili
    DEVIR_KARE_DEV     = int(_f("DOW_DEVIR_KARE_DEV", 3))  # görsel yasanın
    #   elinde bir kutu OLMASI için gereken asgari ardışık tespit. Bu bir GPS
    #   kapısı değil; kutusuz devretmek görsel fazı doğrudan "köprü" (kör)
    #   durumuna sokar.

    @classmethod
    def gelistirme_devri(cls):
        """Geliştirme devir kapısı ETKİN mi? Yarışma kipinde DAİMA False.
        ⚠ GPS'e bakan tek faz-geçiş kodu bu bayrağın ARKASINDADIR."""
        return bool(cls.DEVIR_ISTASYONDAN) and not bool(cls.YARISMA_KIPI)

    # ================= BEKÇİ (uçuş sağlık bandı) =================
    BEKCI_AKTIF        = _b("DOW_BEKCI", True)
    BEKCI_ALT_MAX_M    = _f("DOW_B_ALT", 300.0)   # zemine göreli tavan
    BEKCI_MENZIL_MAX_M = _f("DOW_B_MENZIL", 500.0)
    BEKCI_SPAWN_MAX_M  = _f("DOW_B_SPAWN", 1500.0)
    BEKCI_DONMA_S      = _f("DOW_B_DONMA", 4.0)   # telemetri bu kadar donarsa
    BEKCI_ESIK         = 3                        # ardışık ihlal -> iptal

    # ================= TEMAS SINIFLANDIRMASI =================
    # Kullanıcı isteği (2026-08-23): "drone hedefin pervanesine çarparsa bu
    # vuruş sayılmıyor, drone geriye itiliyor; sen bu pervaneye çarpmayı
    # anla ve bunu vuruş say."
    #
    # ⭐ EŞİK ÖLÇÜLDÜ (TEMAS kampanyası, 6 koşu, döngü hızında ~43 Hz):
    #     koşu  en_yakin  temas ivmesi  @menzil   normal uçuş p99
    #       1     0.78 m     536 m/s²    1.15 m        63
    #       2     0.95 m     879 m/s²    1.11 m        77
    #       3     0.69 m      14 m/s²    5.78 m        59   <- temas YOK
    #       4     0.71 m     359 m/s²    1.19 m        69
    #       5     0.86 m     813 m/s²    1.21 m        67
    #       6     0.93 m      99 m/s²    5.65 m        67   <- temas YOK
    #   Temas darbeleri 359-879, temassızlar 14-99, normal uçuş p99 ≈ 67.
    #   Boşluk ÇOK GENİŞ; eşik 200 (temassızın 2 katı, temasın yarısından az).
    #   Temas menzili 1.11-1.21 m'de KÜMELENİYOR — Talon kanat yarı açıklığı
    #   0.86 m + drone yarıçapı ile geometrik olarak da uyuşuyor.
    #
    # ⚠ BU BİR ÖLÇÜT DEĞİŞİKLİĞİDİR. Eski `isabet` yalnız "menzil < 4 m"
    #   diyordu ve TEMAS ile YAKIN GEÇİŞİ ayırmıyordu (aynı 6 koşuda altısını
    #   da isabet sayardı; gerçekte 4 temas, 2 yakın geçiş, 0 imha).
    #   Bu tarihten önceki kampanyaların `isabet` sayıları bu ölçütle
    #   DOĞRUDAN KIYASLANAMAZ.
    TEMAS_IVME_ESIK = _f("DOW_TEMAS_IVME", 200.0)   # m/s²
    TEMAS_MENZIL_M  = _f("DOW_TEMAS_MENZIL", 2.0)   # m

    # ================= KAYIT =================
    KAYIT_AKTIF   = _b("DOW_KAYIT", True)
    KAYIT_ARALIK  = _f("DOW_KAYIT_ARALIK", 0.5)   # s; kare + telemetri

    # ================= DÖNGÜ =================
    LOOP_HZ = _f("DOW_LOOP_HZ", 50.0)


# ⛔ `CANLI` SÖZLÜĞÜ SİLİNDİ (2026-08-23, §5.12).
#   Panelin kaydırıcıları kullanıcı isteğiyle kaldırılınca ("o slidebarları
#   kaldır, ayarları değiştirme işi sende") bu sözlüğü OKUYAN kod da gitti;
#   geriye 18 satırlık ölü tablo kaldı ve içinde ARTIK OLMAYAN alanlar vardı
#   (MERKEZ_FREN). Ölü kod tutmak arşiv değil borçtur.

# Panel ve kampanya AYRI SÜREÇLER; panelden seçilen kip bu dosyayla taşınır.
_KIP_DOSYA = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), ".gudum_kipi")
_kip_onbellek = {"t": 0.0, "v": None}


def kip_yaz(k):
    try:
        with open(_KIP_DOSYA, "w") as f:
            f.write(k)
    except Exception:
        pass


def kip_oku(ttl=0.25):
    """Panelden seçilen kipi oku (TTL ile önbellekli — her tik disk okumaz)."""
    import time as _t
    simdi = _t.time()
    if _kip_onbellek["v"] is not None and simdi - _kip_onbellek["t"] < ttl:
        return _kip_onbellek["v"]
    v = Ayar.GUDUM_KIPI
    try:
        with open(_KIP_DOSYA) as f:
            x = f.read().strip().lower()
        if x in ("hibrit", "gps", "gorsel"):
            v = x
    except Exception:
        pass
    _kip_onbellek.update({"t": simdi, "v": v})
    return v

