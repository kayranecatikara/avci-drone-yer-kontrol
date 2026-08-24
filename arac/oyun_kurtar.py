# -*- coding: utf-8 -*-
"""
================================================================================
  OYUN KURTAR  --  simulasyon cokerse kendi kendine geri getir
================================================================================
KULLANICININ TARIF ETTIGI AKIS (2026-08-16 gece):
    fatal hata -> oyunu tekrar ac -> ilk once ARAYUZ cikar -> ENTER
    -> baska bir ekran acilir -> BASLAT'a bas -> LOADING -> 'E' ile respawn

⚠ BU AKIS KOR YAZILDI. Oyun cokmeden UI'yi goremedigim icin tus dizisi
   VARSAYIMDIR, olculmus degil. Bu yuzden:
     * her adimin ONCESINDE ve SONRASINDA ekran goruntusu alinir
       -> veri/gece/kurtarma/<damga>/adim_NN_*.png
     * dizinin kendisi JSON'dan okunur (arac/kurtarma_dizisi.json)
       -> ekran goruntulerine bakip diziyi duzeltmek KOD DEGISTIRMEDEN olur
     * her adim sonrasi "oyun ayaga kalkti mi" diye telemetriye bakilir;
       kalktiysa kalan adimlar ATLANIR (fazla tusa basip menuye dusmeyelim)

GUVENLIK
    * Oyun SAGLIKLIYKEN bu modul HICBIR SEY yapmaz (kurtarma_gerekli() False).
    * Ust uste kurtarma denemesi arasinda bekleme suresi KATLANARAK artar.
    * MAKS_DENEME asilirsa durur ve gunluge yazar -- sonsuz dongu YOK.
================================================================================
"""
import os
import json
import time
import subprocess

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIK = os.path.join(KOK, "veri", "gece", "kurtarma")
DIZI_YOL = os.path.join(KOK, "arac", "kurtarma_dizisi.json")
OYUN_BAT = os.path.join(KOK, "1_Oyunu_Baslat.bat")

VARSAYILAN_DIZI = [
    {"ad": "oyun_acilis_bekle", "bekle_s": 45.0, "tus": None},
    {"ad": "arayuz_enter",      "bekle_s": 3.0,  "tus": "enter"},
    {"ad": "baslat_enter",      "bekle_s": 4.0,  "tus": "enter"},
    {"ad": "loading_bekle",     "bekle_s": 25.0, "tus": None},
    {"ad": "respawn_e",         "bekle_s": 3.0,  "tus": "e"},
    {"ad": "oturma",            "bekle_s": 5.0,  "tus": None},
]

# ── Windows sanal tus kodlari (SendInput icin scancode) ──────────────────
SCAN = {"e": 0x12, "enter": 0x1C, "space": 0x39, "esc": 0x01, "r": 0x13,
        "f": 0x21, "1": 0x02, "2": 0x03}


def _u32():
    import ctypes
    return ctypes.WinDLL("user32", use_last_error=True)


def oyun_penceresi():
    """DronesOfWar penceresinin HWND'si | None."""
    try:
        import ctypes
        from ctypes import wintypes
        u = _u32()
        bulunan = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def gez(h, _):
            n = u.GetWindowTextLengthW(h)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(h, b, n + 1)
                if "DronesOfWar" in b.value and u.IsWindowVisible(h):
                    bulunan.append(h)
            return True

        u.EnumWindows(gez, 0)
        return bulunan[0] if bulunan else None
    except Exception:
        return None


def one_al(h=None):
    """Oyun penceresini one al ve GERCEKTEN one geldigini DOGRULA.

    ⚠ 2026-08-17 gece, CANLI YAKALANDI: SetForegroundWindow Windows'ta cagiran
      surec on planda degilse SESSIZCE BASARISIZ olur (odak calma korumasi).
      Donus degerini kontrol etmedigim icin tuslar oyuna degil O ANDA ODAKTA
      OLAN PENCEREYE gitti -- kurtarma ekran goruntusu kullanicinin VS Code
      terminalini gosterdi. Enter/E tuslari oraya basildi.
      Bu YIKICI olabilirdi. Artik: one alamazsak TUS GONDERILMEZ.

    AttachThreadInput hilesi: hedef pencerenin girdi kuyruguna baglanmak
    SetForegroundWindow kisitini asmanin desteklenen yoludur.
    """
    h = h or oyun_penceresi()
    if not h:
        return False
    try:
        import ctypes
        u = _u32()
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if u.IsIconic(h):
            u.ShowWindow(h, 9)                       # SW_RESTORE
            time.sleep(0.3)
        # 1) duz deneme
        u.SetForegroundWindow(h)
        time.sleep(0.25)
        if u.GetForegroundWindow() == h:
            return True
        # 2) AttachThreadInput ile tekrar dene
        hedef_th = u.GetWindowThreadProcessId(h, None)
        benim_th = k32.GetCurrentThreadId()
        onplan = u.GetForegroundWindow()
        onplan_th = u.GetWindowThreadProcessId(onplan, None) if onplan else 0
        for th in {hedef_th, onplan_th} - {0, benim_th}:
            u.AttachThreadInput(benim_th, th, True)
        try:
            u.ShowWindow(h, 5)                       # SW_SHOW
            u.BringWindowToTop(h)
            u.SetForegroundWindow(h)
            time.sleep(0.3)
        finally:
            for th in {hedef_th, onplan_th} - {0, benim_th}:
                u.AttachThreadInput(benim_th, th, False)
        return u.GetForegroundWindow() == h
    except Exception:
        return False


def tus_bas(ad, tekrar=1, arada=0.08):
    """Oyun penceresine SendInput ile tus. Oyunlar RawInput okur -> PostMessage YETMEZ."""
    sc = SCAN.get(str(ad).lower())
    if sc is None:
        return False
    # ⚠ EMNIYET KAPISI: pencere one gelmediyse TUS GONDERME. SendInput odaktaki
    #   pencereye gider; oyun odakta degilse tuslar BASKA bir uygulamaya
    #   (ornegin bir terminale) basilir. Bu gece bir kez oldu.
    if not one_al():
        return False
    try:
        _h = oyun_penceresi()
        if _h is None or _u32().GetForegroundWindow() != _h:
            return False
    except Exception:
        return False
    # ⚠ 2026-08-17 CANLI OLCULDU: DoW SendInput'u YUTUYOR, eski keybd_event
    #   API'sini KABUL EDIYOR. Dort yontem denendi, tek calisan bu:
    #       VK+scancode SendInput -> port acilmadi
    #       yalniz VK   SendInput -> port acilmadi
    #       yalniz scancode SendInput -> port acilmadi
    #       keybd_event (VK + scancode) -> PORT ACILDI, drone dogdu
    #   Once keybd_event denenir; basarisiz olursa SendInput'a duselir.
    VK = {"e": 0x45, "enter": 0x0D, "space": 0x20, "esc": 0x1B, "r": 0x52,
          "f": 0x46, "1": 0x31, "2": 0x32}
    _vk = VK.get(str(ad).lower(), 0)
    if _vk:
        try:
            u0 = _u32()
            for _ in range(max(1, tekrar)):
                u0.keybd_event(_vk, sc, 0, 0)
                time.sleep(0.12)
                u0.keybd_event(_vk, sc, 0x0002, 0)
                time.sleep(arada)
            return True
        except Exception:
            pass
    try:
        import ctypes
        from ctypes import wintypes
        u = _u32()
        KEYEVENTF_SCANCODE, KEYEVENTF_KEYUP = 0x0008, 0x0002

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

        class INPUT(ctypes.Structure):
            class _U(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]
            _anonymous_ = ("u",)
            _fields_ = [("type", wintypes.DWORD), ("u", _U)]

        def gonder(yukari):
            i = INPUT()
            i.type = 1
            i.ki = KEYBDINPUT(0, sc,
                              KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if yukari else 0),
                              0, None)
            u.SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))

        for _ in range(max(1, tekrar)):
            gonder(False)
            time.sleep(0.06)
            gonder(True)
            time.sleep(arada)
        return True
    except Exception:
        return False


def ekran_goruntusu(yol):
    """Oyun penceresinin goruntusu. mss varsa onunla, yoksa PIL."""
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        try:
            import mss
            import mss.tools
            with mss.mss() as s:
                m = s.monitors[1]
                im = s.grab(m)
                mss.tools.to_png(im.rgb, im.size, output=yol)
            return True
        except Exception:
            from PIL import ImageGrab
            ImageGrab.grab().save(yol)
            return True
    except Exception:
        return False


# Bizim oyunumuzu BASKA kurulumlardan ayiran yol parcasi.
# ⚠⚠ 2026-08-19 -- BULUNAN TEHLIKE: `oyun_calisiyor()` yalnizca SUREC ADINA
#   bakiyordu ("DronesOfWar-Win64-Shipping.exe"). Makinede Steam'den kurulu
#   IKINCI bir Drones of War kopyasi acik kaldiginda, bizim Teknofest yapimiz
#   FATAL verip OLSE BILE bu kontrol True donuyordu -> nobetci "oyun ayakta"
#   sanip yeniden acmiyor, ekran koordinatlarina bos yere tikliyordu.
#   Oyun sik FATAL verdigi icin bu, tam da en kritik anda bozulan bir kor
#   nokta. Artik CALISTIRILABILIR YOLU eslestiriyoruz.
OYUN_YOL_IMZA = "Drones of War Teknofest"


def oyun_calisiyor():
    """BIZIM Teknofest yapimiz ayakta mi (yalniz surec adi YETMEZ)."""
    try:
        c = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='DronesOfWar-Win64-Shipping.exe'\""
             " | Select-Object -ExpandProperty ExecutablePath"],
            capture_output=True, text=True, timeout=20)
        cikti = (c.stdout or "")
        if cikti.strip():
            return OYUN_YOL_IMZA.lower() in cikti.lower()
        # Hic surec yok -> gercekten kapali
        if c.returncode == 0:
            return False
    except Exception:
        pass
    # PowerShell kullanilamadiysa ESKI davranisa dus (emin degilsek mudahale etme)
    try:
        c = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq DronesOfWar-Win64-Shipping.exe", "/NH"],
            capture_output=True, text=True, timeout=15)
        return "DronesOfWar" in (c.stdout or "")
    except Exception:
        return True                                   # emin degilsek MUDAHALE ETME


def dizi_oku():
    try:
        if os.path.exists(DIZI_YOL):
            with open(DIZI_YOL, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, list) and d:
                return d
    except Exception:
        pass
    return VARSAYILAN_DIZI


def dizi_yaz_varsayilan():
    """Ilk calistirmada JSON'u diske dok ki elle duzeltilebilsin."""
    if not os.path.exists(DIZI_YOL):
        try:
            with open(DIZI_YOL, "w", encoding="utf-8") as f:
                json.dump(VARSAYILAN_DIZI, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def oyunu_baslat(gunluk=print):
    """1_Oyunu_Baslat.bat'i ayri bir konsolda calistir."""
    if not os.path.exists(OYUN_BAT):
        gunluk("[KURTAR] oyun .bat bulunamadi: %s" % OYUN_BAT)
        return False
    try:
        subprocess.Popen(["cmd", "/c", "start", "", OYUN_BAT],
                         cwd=KOK, shell=False,
                         creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
        gunluk("[KURTAR] oyun baslatildi: %s" % os.path.basename(OYUN_BAT))
        return True
    except Exception as e:
        gunluk("[KURTAR] oyun baslatilamadi: %r" % (e,))
        return False


# ═══════════════════════════════════════════════════════════════════════
#  OYUNU SIFIRDAN AC  --  kullanicinin KAYDEDILEN dizisinden ogrenildi
# ═══════════════════════════════════════════════════════════════════════
# 2026-08-17 sabahi, kullanici bir kez yapti ve kaydedildi
# (arac/giris_kaydet.py -> veri/gece/giris/baslangic.json, 93.5 s):
#     78.9 s  sol tik  pencerenin %49, %80'i   <- "PRESS FOR START"
#     85.2 s  sol tik  pencerenin  %9, %43'u   <- harita/gorev secimi
#     93.4 s  E                                <- drone dogar, port 12345 acilir
# ⚠ Gece bu noktaya KOR tahminle ulasamadim: ayni koordinata tikladim ama
#   olmadi (oyun saatlerce attract modunda kalmisti). Simdi sabit zamanlama
#   yerine UYARLANABILIR: her adimdan sonra sonuc kontrol edilir, gerekirse
#   tekrarlanir.
BASLIK_TIK = (0.49, 0.80)     # "PRESS FOR START"
HARITA_TIK = (0.09, 0.43)     # gorev secimi
# ⚠ 2026-08-17 KESFEDILDI: gorev BASARIYLA bitince oyun "MISSION COMPLETED"
#   ekranina gecer ve SDK portu kapanir. Kayitli dizi BASLIK ekranindan
#   basladigi icin 6 tur boyunca bosa tikladi (172 s) ve BASARISIZ dedi.
#   Bu ekranda iki dugme var: "RETURN TO MENU" (sol) ve "PLAY AGAIN" (sag).
#   PLAY AGAIN dogrudan gorevi yeniden baslatir -> OLCULDU: port 14 s'de acildi.
TEKRAR_OYNA_TIK = (0.786, 0.845)     # "PLAY AGAIN"
MENUYE_DON_TIK = (0.226, 0.845)      # "RETURN TO MENU" (yedek)
YUKLEME_BEKLE_S = 6.0     # PLAY AGAIN sonrasi loading payi, sonra E




def _tikla_oran(ox, oy):
    """Pencereye GORE oranli konuma sol tik. Pencere tasinsa da calisir."""
    import ctypes
    h = oyun_penceresi()
    if not h or not one_al(h):
        return False
    u = _u32()

    class _R(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                    ("r", ctypes.c_long), ("b", ctypes.c_long)]
    r = _R()
    u.GetWindowRect(h, ctypes.byref(r))
    x = int(r.l + ox * (r.r - r.l))
    y = int(r.t + oy * (r.b - r.t))
    u.SetCursorPos(x, y)
    time.sleep(0.15)
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.07)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    return True


def port_acik(port=12345, zaman=0.6):
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=zaman)
        s.close()
        return True
    except Exception:
        return False


def oyunu_ac_ve_goreve_sok(gunluk=print, toplam_s=300.0):
    """Oyunu sifirdan acip GOREVE sokar. Basari olcutu: port 12345 acilir.

    Adimlar uyarlanabilir: her birinden sonra port kontrol edilir; acildiysa
    kalan adimlar atlanir, acilmadiysa adim TEKRARLANIR.
    """
    t0 = time.time()
    if port_acik():
        gunluk("[AC] port zaten acik -> oyun gorevde, yapacak bir sey yok")
        return True

    if not oyun_calisiyor():
        if not oyunu_baslat(gunluk):
            return False
        gunluk("[AC] oyun acilisini bekliyorum (pencere)...")
        while time.time() - t0 < 120:
            if oyun_penceresi():
                gunluk("[AC]   pencere geldi (%.0f s)" % (time.time() - t0))
                break
            time.sleep(3)
        time.sleep(25)                      # motorun oturmasi

    for tur in range(1, 7):
        if port_acik():
            gunluk("[AC] ✓ GOREVDE (port acik, %.0f s)" % (time.time() - t0))
            return True
        if time.time() - t0 > toplam_s:
            break
        # ⚠⚠ 2026-08-19: OYUN SURECI HER TURDA YENIDEN KONTROL EDILIR.
        # `oyun_calisiyor()` yukarida YALNIZ BIR KEZ bakiliyordu. Oyun
        # dizinin ORTASINDA olurse bu dongu 300 s boyunca MASAUSTUNE
        # tikliyordu. Sahada yasandi (2026-08-19 20:58-21:00): log "tur 4,
        # tur 5, tur 6 PLAY AGAIN tiki" diye akarken oyun sureci YOKTU ve
        # sistem 2+ dakika bos bekledi; kullanici "sunucu kapali" dedi.
        if not oyun_calisiyor():
            gunluk("[AC] ⚠ oyun sureci OLMUS -> yeniden baslatiliyor")
            if not oyunu_baslat(gunluk):
                return False
            _b = time.time()
            while time.time() - _b < 120:
                if oyun_penceresi():
                    gunluk("[AC]   pencere geldi (%.0f s)" % (time.time() - _b))
                    break
                time.sleep(3)
            time.sleep(25)                  # motorun oturmasi
            continue
        # 1) "MISSION COMPLETED" ekraninda miyiz? PLAY AGAIN en kisa yol.
        #    Baslik ekraninda bu nokta bos alan -> zararsiz.
        gunluk("[AC] tur %d: PLAY AGAIN tiki (%%%.0f,%%%.0f)"
               % (tur, TEKRAR_OYNA_TIK[0] * 100, TEKRAR_OYNA_TIK[1] * 100))
        _tikla_oran(*TEKRAR_OYNA_TIK)
        # ⚠ 2026-08-17 -- KULLANICININ TARIF ETTIGI AKIS:
        #   "play again butonuna bas -> BIRKAC SANIYE SONRA E bas".
        #   E'yi portun acilmasina BAGLAMA: port = gorev yuklendi demek,
        #   arac hala DOGMAMIS olabilir. Onceki surumde port acilmazsa E hic
        #   basilmiyor, baslik ekrani dizisine dusuluyordu (yanlis ekran).
        time.sleep(YUKLEME_BEKLE_S)          # loading
        gunluk("[AC]   PLAY AGAIN sonrasi E (drone dogur)")
        for _ in range(4):
            tus_bas("e")
            time.sleep(2.5)
            if port_acik():
                break
        if port_acik():
            gunluk("[AC]   ✓ PLAY AGAIN + E tuttu")
            continue
        gunluk("[AC]   baslik tiki (%%%.0f,%%%.0f)"
               % (BASLIK_TIK[0] * 100, BASLIK_TIK[1] * 100))
        _tikla_oran(*BASLIK_TIK)
        time.sleep(6)
        if port_acik():
            continue
        gunluk("[AC]   harita tiki (%%%.0f,%%%.0f)"
               % (HARITA_TIK[0] * 100, HARITA_TIK[1] * 100))
        _tikla_oran(*HARITA_TIK)
        time.sleep(8)
        gunluk("[AC]   E (drone dogur)")
        for _ in range(3):
            tus_bas("e")
            time.sleep(2.0)
            if port_acik():
                break
        time.sleep(3)

    ok = port_acik()
    gunluk("[AC] %s (%.0f s)" % ("✓ GOREVDE" if ok else "⚠ BASARISIZ",
                                 time.time() - t0))
    if not ok:
        ekran_goruntusu(os.path.join(CIK, "ac_basarisiz_%s.png"
                                     % time.strftime("%Y%m%d_%H%M%S")))
    return ok


def kurtar(saglikli_mi, gunluk=print, sadece_tus=False):
    """Kurtarma dizisini yurut.

    saglikli_mi : cagiran taraftan gelen fonksiyon -> True ise dizi ERKEN BITER
    sadece_tus  : oyun surecin ayakta ama menude takili -> .bat'i CALISTIRMA
    """
    damga = time.strftime("%Y%m%d_%H%M%S")
    klasor = os.path.join(CIK, damga)
    dizi_yaz_varsayilan()
    adimlar = dizi_oku()
    gunluk("[KURTAR] ==== kurtarma basladi (%s) sadece_tus=%s ====" % (damga, sadece_tus))

    if not sadece_tus:
        if not oyunu_baslat(gunluk):
            return False

    for i, ad in enumerate(adimlar):
        if sadece_tus and ad["ad"] == "oyun_acilis_bekle":
            continue
        bekle = float(ad.get("bekle_s", 2.0))
        gunluk("[KURTAR] adim %d/%d '%s' -> %.0f s bekle, tus=%s"
               % (i + 1, len(adimlar), ad["ad"], bekle, ad.get("tus")))
        t0 = time.time()
        while time.time() - t0 < bekle:
            time.sleep(1.0)
            try:
                if saglikli_mi():
                    gunluk("[KURTAR] oyun ayaga kalkti (adim %d) -> kalan adimlar ATLANDI" % (i + 1))
                    ekran_goruntusu(os.path.join(klasor, "adim_%02d_saglikli.png" % i))
                    return True
            except Exception:
                pass
        ekran_goruntusu(os.path.join(klasor, "adim_%02d_%s_once.png" % (i, ad["ad"])))
        t = ad.get("tus")
        if t:
            ok = tus_bas(t)
            gunluk("[KURTAR]   tus '%s' gonderildi: %s" % (t, ok))
            time.sleep(1.5)
            ekran_goruntusu(os.path.join(klasor, "adim_%02d_%s_sonra.png" % (i, ad["ad"])))

    try:
        son = saglikli_mi()
    except Exception:
        son = False
    ekran_goruntusu(os.path.join(klasor, "adim_99_bitis.png"))
    gunluk("[KURTAR] dizi bitti. saglikli=%s  (goruntuler: %s)" % (son, klasor))
    return son


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tus", help="tek tus gonder ve cik (e/enter/space...)")
    ap.add_argument("--goruntu", help="ekran goruntusu al ve bu yola yaz")
    ap.add_argument("--durum", action="store_true", help="oyun/pencere durumu")
    a = ap.parse_args()
    if a.durum:
        h = oyun_penceresi()
        print("oyun sureci calisiyor :", oyun_calisiyor())
        print("pencere HWND          :", h)
        dizi_yaz_varsayilan()
        print("kurtarma dizisi       :", DIZI_YOL)
    if a.goruntu:
        print("goruntu:", ekran_goruntusu(a.goruntu), "->", a.goruntu)
    if a.tus:
        print("tus '%s' :" % a.tus, tus_bas(a.tus))
