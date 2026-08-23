# -*- coding: utf-8 -*-
"""
================================================================================
  PERIYODIK KESTIRICI  --  bozuk hedef GPS'inden GERCEK konumu geri kazanir
================================================================================
SORUN (olculdu 2026-08-19, 1055 esli ornek, 240 s, YARISMA modu)
--------------------------------------------------------------------------------
Yarisma hedefin GPS'ini bozuyor. Olculen:
    HAM bozuk konum hatasi        : medyan 21.6 m | p90 39.5 | p99 55.7
    mevcut "j" filtresi cikisi    : medyan 14.9 m | p90 39.0
Butun angajman 10-30 m menzilde geciyor -> 15 m hatayla vurmak IMKANSIZ.
Olculen sonuc: yarisma modunda 10 dk'da <3 m gecis %0 (teshis modunda %58).

⭐ BOZULMANIN CINSI: GURULTU DEGIL, GECIKME
--------------------------------------------------------------------------------
Bozuk veriye periyodik model uydurulunca ARTIK yalniz ~5 m cikiyor: yani
bozuk sinyal KENDI ICINDE son derece duzenli. Gurultu olsaydi artik da
buyuk olurdu. Oyunun kendi bildirdigi `delay_s = 1.00 s` ve hedef 18 m/s
-> ~18 m konum farki; olculen 21.6 m ile birebir.
    ⚠ Bu yuzden ORTALAMA ALMAK ISE YARAMAZ (bias'i silemez) ve HAM VERIYI
      KAYDIRMAK da ise yaramaz (gurultuyu tasir). Once DUZLESTIR, sonra
      KAYDIR: modeli t+ILERI'de degerlendir.

COZUM VE OLCULEN KAZANC (NEDENSEL: her an yalniz gecmise uydurulur)
--------------------------------------------------------------------------------
    yontem                        medyan     p90     p99
    HAM bozuk GPS                  21.62   39.45   55.71
    j filtresi (mevcut)            14.90   39.05       -
    ** FOURIER + 1.2 s ileri **     5.70   10.04   13.59
-> mevcut filtreye gore **%62** daha iyi; kuyrukta (p90) **4 kat**.
Periyot bozuk veriden 29.60 s olarak DOGRU bulunuyor (gercek 29.60).

⚠⚠ KULLANIM KURALLARI
--------------------------------------------------------------------------------
1. Bir tur + ortusme (>=75 s) gozlem sart; oncesinde `hazir()` False doner
   ve cagiran HAM konuma duser. Uydurma kestirim URETILMEZ.
2. Hedef pistini degistirirse (8 oyun varyanti) artik buyur -> kapi kapanir.
   Periyot her kosuda YENIDEN kestirilir, ASLA sabit yazilmaz.
3. Bu bir DAVRANIS DEGISTIREN kapidir -> cevrimdisi replay ile
   degerlendirilemez; ucusta olcelim.
4. OLUMSUZ KONTROL: `ileri_s=0` ver -> kazancin gecikme telafisinden
   geldigi dogrulanir (0'da hata ~22 m'ye geri cikmali).

GIRDI: yalnizca hedefin (bozuk) gecmis konumlari — zaten elimizde olan
telemetri. Oyunun ic durumu ya da truth kanali KULLANILMAZ.
================================================================================
"""
import math
import threading
from collections import deque

import numpy as np

# ── olculmus varsayilanlar ──────────────────────────────────────────────
# ⚠ Tarandi (1055 ornek): 90/120/180/235 s x 6/8/12/16 harmonik.
#   En iyi 235 s + 6 harmonik -> 5.00 m (120/8 = 5.77 m). Uzun pencere
#   daha cok ortalar, AZ harmonik gurultuyu daha az ezberler.
PENCERE_S = 235.0        # s; uydurma penceresi (~8 tur)
MIN_GOZLEM_S = 75.0      # s; altinda kapi KAPALI (bir tur + ortusme)
MIN_ORNEK = 250          # tampon en az bu kadar ornek tasimali
HARMONIK = 6             # Fourier terim sayisi (tarandi: 6 en iyi)
ILERI_S = 1.2            # s; gecikme telafisi (oyunun bildirdigi 1.0 + filtre gecikmesi)
PERIYOT_MIN = 25.0       # s
PERIYOT_MAX = 35.0       # s
PERIYOT_ADIM = 0.05      # s
PERIYOT_HARMONIK = 6     # periyot taramasinda daha az terim (hizli + kararli)
YENIDEN_UYDUR_S = 0.5    # s; katsayilar bu araliktan sik yenilenmez
YENIDEN_PERIYOT_S = 4.0  # s; periyot taramasi daha seyrek (maliyetli)
KALITE_MAX_M = 12.0      # m; uydurma artigi bunu asarsa kapi KAPALI
#   ⚠ 3 m DEGIL: bozuk veride artik dogal olarak ~5 m. Temiz veri esigiyle
#     karistirmayin; bu esik BOZUK sinyal icindir (olculen artik 5.07 m).
# ⚠⚠ SICRAMA ESIGI HIZ DEGIL MUTLAK MESAFE OLMALI (olculdu 2026-08-19):
#   BOZUK sinyal ornekler arasi p99 = 40.1 m, maks 43.3 m ziplar (176 m/s).
#   Hiz esigi (55 m/s = 12.4 m/ornek) orneklerin %5.5'ini "isinlanma" sayip
#   tamponu SUREKLI sifirliyordu -> kapi HIC acilmadi (0/1055).
#   Bozulma ~64 m ile sinirli oldugu icin en buyuk mesru zipllama ~128 m;
#   gorev yeniden baslangicindaki isinlanma ise YUZLERCE metre.
SICRAMA_M = 150.0        # m; ustunde ISINLANMA -> tampon sifirlanir


def _tasarim(t, P, K):
    """Fourier tasarim matrisi: [1, cos(kwt), sin(kwt) ...]"""
    w = 2.0 * math.pi / P
    M = [np.ones_like(t)]
    for k in range(1, K + 1):
        M.append(np.cos(k * w * t))
        M.append(np.sin(k * w * t))
    return np.vstack(M).T


def _uydur(t, x, P, K):
    c, *_ = np.linalg.lstsq(_tasarim(t, P, K), x, rcond=None)
    return c


def _degerlendir(t, c, P, K):
    return _tasarim(np.atleast_1d(np.asarray(t, dtype=float)), P, K) @ c


class PeriyodikKestirici:
    """Bozuk hedef konumundan gecikme-telafili temiz konum.

        pk = PeriyodikKestirici()
        pk.ekle(t, x, y, z)          # her HAM telemetri ornegi
        p = pk.kestir(t)             # (x, y, z) ya da None -> cagiran HAM'a duser
    """

    def __init__(self, ileri_s=ILERI_S, harmonik=HARMONIK,
                 pencere_s=PENCERE_S, min_gozlem_s=MIN_GOZLEM_S,
                 kalite_max=KALITE_MAX_M):
        self._buf = deque()
        self.ileri_s = float(ileri_s)
        self.K = int(harmonik)
        self.pencere_s = float(pencere_s)
        self.min_gozlem_s = float(min_gozlem_s)
        self.kalite_max = float(kalite_max)
        self._P = None
        self._c = None          # (cx, cy, cz)
        self._kalite = None
        self._son_uydur = None
        self._son_periyot = None

    # ── veri ────────────────────────────────────────────────────────────
    def ekle(self, t, x, y, z=0.0):
        if t is None or x is None or y is None:
            return
        k = getattr(self, "_kilit", None)
        if k is not None:
            with k:
                return self._ekle(t, x, y, z)
        return self._ekle(t, x, y, z)

    def _ekle(self, t, x, y, z=0.0):
        if self._buf:
            t0, x0, y0, _z0 = self._buf[-1]
            if t <= t0:
                self.sifirla()                      # saat geriye gitti
            elif math.hypot(x - x0, y - y0) > SICRAMA_M:
                self.sifirla()                      # isinlanma (bkz. SICRAMA_M)
        self._buf.append((float(t), float(x), float(y), float(z or 0.0)))
        son = self._buf[-1][0]
        while self._buf and son - self._buf[0][0] > self.pencere_s:
            self._buf.popleft()

    def sifirla(self):
        self._buf.clear()
        self._P = self._c = self._kalite = None
        self._son_uydur = self._son_periyot = None

    # ── ic ──────────────────────────────────────────────────────────────
    def _diziler(self):
        B = self._buf
        t = np.fromiter((b[0] for b in B), dtype=float, count=len(B))
        x = np.fromiter((b[1] for b in B), dtype=float, count=len(B))
        y = np.fromiter((b[2] for b in B), dtype=float, count=len(B))
        z = np.fromiter((b[3] for b in B), dtype=float, count=len(B))
        return t, x, y, z

    def _periyot_bul(self, t, x, y):
        """Periyot taramasi.

        ⚠ MALIYET: genis tarama 200 aday x 2 lstsq -> olculdu 7.6 ms/ornek,
        20 Hz dongude tik butcesinin %15'i. Periyot bir kez KILITLENINCE
        (29.65 s, kosudan kosuya kararli) yalnizca +-0.5 s dar tarama yeter
        -> 20 aday. Kilit kaybolursa (kalite bozulur) genis taramaya doner.
        """
        en = None
        if self._P is not None and self._kalite is not None                 and self._kalite <= self.kalite_max:
            alt = max(PERIYOT_MIN, self._P - 0.5)
            ust = min(PERIYOT_MAX, self._P + 0.5)
        else:
            alt, ust = PERIYOT_MIN, PERIYOT_MAX
        P = alt
        while P <= ust:
            try:
                cx = _uydur(t, x, P, PERIYOT_HARMONIK)
                cy = _uydur(t, y, P, PERIYOT_HARMONIK)
                r = float(np.median(np.hypot(
                    x - _degerlendir(t, cx, P, PERIYOT_HARMONIK),
                    y - _degerlendir(t, cy, P, PERIYOT_HARMONIK))))
            except np.linalg.LinAlgError:
                r = None
            if r is not None and (en is None or r < en[1]):
                en = (P, r)
            P += PERIYOT_ADIM
        return en

    def guncelle(self, simdi=None):
        """Gerekiyorsa periyodu ve katsayilari yenile. Her tik cagrilabilir."""
        B = self._buf
        if len(B) < MIN_ORNEK:
            return
        t_son = B[-1][0] if simdi is None else float(simdi)
        if B[-1][0] - B[0][0] < self.min_gozlem_s:
            return
        if self._son_uydur is not None and t_son - self._son_uydur < YENIDEN_UYDUR_S:
            return
        self._son_uydur = t_son
        t, x, y, z = self._diziler()
        if (self._P is None or self._son_periyot is None
                or t_son - self._son_periyot >= YENIDEN_PERIYOT_S):
            en = self._periyot_bul(t, x, y)
            if en is None:
                self._P = self._c = self._kalite = None
                return
            self._P = en[0]
            self._son_periyot = t_son
        P = self._P
        try:
            cx = _uydur(t, x, P, self.K)
            cy = _uydur(t, y, P, self.K)
            cz = _uydur(t, z, P, self.K)
        except np.linalg.LinAlgError:
            self._c = self._kalite = None
            return
        self._c = (cx, cy, cz)
        self._kalite = float(np.median(np.hypot(
            x - _degerlendir(t, cx, P, self.K),
            y - _degerlendir(t, cy, P, self.K))))

    # ── disari ──────────────────────────────────────────────────────────
    @property
    def periyot(self):
        return self._P

    @property
    def kalite(self):
        return self._kalite

    def hazir(self):
        if self._c is None or self._P is None or self._kalite is None:
            return False
        if self._kalite > self.kalite_max:
            return False
        if not self._buf or self._buf[-1][0] - self._buf[0][0] < self.min_gozlem_s:
            return False
        return True

    def kestir(self, t=None):
        """t (varsayilan: son ornek) anindaki GERCEK konum kestirimi.

        Model t + `ileri_s`'te degerlendirilir -> oyunun gecikmesi telafi
        edilir. Kapi kapaliysa DAIMA None (cagiran HAM konuma duser).
        """
        if not self.hazir():
            return None
        tt = (self._buf[-1][0] if t is None else float(t)) + self.ileri_s
        cx, cy, cz = self._c
        P, K = self._P, self.K
        return (float(_degerlendir(tt, cx, P, K)[0]),
                float(_degerlendir(tt, cy, P, K)[0]),
                float(_degerlendir(tt, cz, P, K)[0]))

    # ── ARKAPLAN ISCISI ────────────────────────────────────────────────
    # ⚠ NEDEN SART: `guncelle()` olculdu -> medyan 0.0 ms ama p99 18.7 ms,
    #   MAKS 121.8 ms (ilk genis tarama). Kontrol dongusu 20 Hz = 50 ms tik;
    #   121 ms'lik bir takilma IKI TIK dusurur. 2026-08-17'de benzer bir
    #   tikanma (nobetci SDK portunu yokluyordu) `connected`i %7.6'ya
    #   dusurup araci 900 m'ye tirmandirmisti. Uydurma kontrol dongusunde
    #   YAPILMAZ: `ekle()` ucuz (sadece append), uydurma AYRI IS PARCACIGINDA.
    def isci_baslat(self, arali_s=0.5):
        """Arkaplanda periyodik uydurma baslat (idempotent)."""
        if getattr(self, "_isci", None) is not None:
            return
        self._dur = threading.Event()
        self._kilit = threading.Lock()

        def _dongu():
            import time as _t
            while not self._dur.is_set():
                try:
                    with self._kilit:
                        self.guncelle()
                except Exception:
                    pass
                self._dur.wait(arali_s)

        self._isci = threading.Thread(target=_dongu, daemon=True,
                                      name="periyodik_kestirici")
        self._isci.start()

    def isci_durdur(self):
        d = getattr(self, "_dur", None)
        if d is not None:
            d.set()
        self._isci = None

    def tani(self):
        return {
            "pk_periyot_s": self._P,
            "pk_kalite_m": self._kalite,
            "pk_hazir": self.hazir(),
            "pk_ornek": len(self._buf),
            "pk_sure_s": (self._buf[-1][0] - self._buf[0][0]) if self._buf else 0.0,
            "pk_ileri_s": self.ileri_s,
        }
