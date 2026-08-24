# -*- coding: utf-8 -*-
"""
================================================================================
  HEDEF TEKRAR KESTIRICISI  --  hedefin KAPALI pistinden ileriyi okuma
================================================================================
NEDEN (olculdu 2026-08-18, 47 kesintisiz iz parcasi, n~4100/ufuk)
--------------------------------------------------------------------------------
KISA UFUKLU kinematik kestirim ZAYIF:
    ufuk      sabit HIZ      sabit DONUS
    1.0 s     2.47 m         1.59 m   (p90 4.45)
    2.0 s     6.42 m         3.80 m   (p90 12.69)
Yani 1-2 s'lik "ongorulu nisan" duzelttigi kadar hata sokar. Lead tavanini
9 -> 14/20 buyutmenin ucusta NEDEN KAYBETTIGININ aciklamasi budur.

AMA hedef KAPALI ve TEKRARLAYAN bir oval ucuyor. Olculen periyot
**29.60 s** (p10 = p90 = 29.60, n=40 parca). "Bir tur oncesine bak"
kestiricisi -- pos(t+h) ~= pos(t+h-P):
    ufuk       2 s    5 s   10 s   20 s   30 s
    medyan    1.06   0.72   0.62   0.65   0.66  m
    p90       2.33   2.01   1.86   1.88   2.31  m
**Hata UFUKTAN BAGIMSIZ.** 30 s sonrasi, 2 s sonrasindan 6 KAT daha dogru.

NE ISE YARAR
--------------------------------------------------------------------------------
Vurusu ureten sey KESME GEOMETRISIDIR (aspect 60-90 deg -> CPA<1.5 m %55;
saf kuyruk 150-180 deg -> %9). Bugun yaklasmalarin %54'u kuyrukta bitiyor
ve yalniz %4'u kesme bandinda -- cunku kesme KAZARA olusuyor (hedef kendi
ovalinde donup bize geliyor). Bu kestiriciyle bulusma noktasi ONCEDEN
hesaplanabilir: kovalamak yerine PUSU.

⚠⚠ KULLANIM KURALLARI (ihlal edilirse olcum gecersizdir)
--------------------------------------------------------------------------------
1. Bir TUR (~30 s) gozlem sart. Oncesinde `hazir()` False doner ve cagiran
   ESKI DAVRANISI surdurmelidir -- kestirim uydurmak YOK.
2. MEKANIZMA KAPISI: kestirilen periyot beklenen bandin disindaysa
   (`PERIYOT_BEKLENEN +- PERIYOT_TOLERANS`) kapi KAPALI kalir. 8 oyun
   varyanti var ve oval yonelim/irtifa/merkez olarak DEGISIYOR; periyot
   her kosuda YENIDEN kestirilir, ASLA sabit yazilmaz.
3. Kalite esigi: tur-uzeri artik medyani `KALITE_MAX_M`'yi asarsa kapi
   kapanir (hedef pistini degistirmis ya da veri bozuk demektir).
4. Bu bir DAVRANIS DEGISTIREN kapidir -> cevrimdisi replay ile
   degerlendirilemez (off-policy tuzagi). Ucusta olc.
5. Olumsuz kontrol ZORUNLU: periyodu kasten %20 yanlis ver; sonuc
   KOTULESMELI. Kotulesmiyorsa kazanc kestirimden GELMIYOR demektir.

SALT GIRDI: hedefin gecmis konumlari (zaten elimizde olan telemetri).
Canli GPS ya da oyun ic durumu KULLANILMAZ.
================================================================================
"""
import math
from collections import deque

PERIYOT_BEKLENEN = 29.6      # s; olculen (p10 = p90 = 29.60)
# ⚠ TOLERANS VARSAYILAN OLARAK GENIS (=sert kapi DEGIL). Sebep: 8 oyun
#   varyanti var ve oval yonelim/irtifa/MERKEZ olarak degisiyor; periyodu
#   29.6'ya baglamak baska varyantta kapiyi bosuna kapatir. ASIL KAPI
#   KALITE'dir (tur-uzeri artik medyani) -- o, periyodun gercekten
#   tekrar uretip uretmedigini dogrudan olcer.
#   ⚠ Ayrica GERCEK periyodun HARMONIGI de gecerli bir kestiricidir
#     (15 s'lik pist icin 30 s kusursuz calisir) -- bandi daraltmak bunu
#     da bosuna reddeder. Testle dogrulandi.
PERIYOT_TOLERANS = 99.0      # s; sert bant istenirse kucult (or. 1.5)
PERIYOT_MIN = 20.0           # s; tarama alt siniri
PERIYOT_MAX = 42.0           # s; tarama ust siniri
PERIYOT_ADIM = 0.1           # s; tarama cozunurlugu
KALITE_MAX_M = 3.0           # m; tur-uzeri artik medyani bunu asarsa kapi kapali
# ⚠ Tampon periyottan COK daha uzun olmali: `_artik` yalniz (sure - P)
#   kadarlik bolumde ortusme bulabilir. 46 s'de P=29.6 icin ortusme 16 s
#   kalir ve kestirim gurultulenir. 75 s -> ~45 s ortusme.
PENCERE_S = 75.0             # s; halka tampon omru
MIN_GOZLEM_S = 45.0          # s; en az bir tam tur + saglam ORTUSME payi
# ⚠ 40 s veriyle periyot 28.5 cikip kalite 9.32'ye firliyor (olculdu):
#   P=29.6 icin `t-P` ancak son ~10 s'de tampona dusuyor -> ortusme az,
#   kestirim gurultulu. 44 s'de kalite 1e-12. Kapi zaten kaliteden
#   kapaniyordu; bu esik bosuna hesaplamayi da onler.
MIN_ORTUSME = 12             # _artik icin gereken en az ornek cifti
YENIDEN_HESAP_S = 2.0        # s; periyot bu araliktan sik hesaplanmaz (maliyet)
MIN_ORNEK = 120              # tampon en az bu kadar ornek tasimali
# ⚠ Hedef 17.95 m/s (olculdu, sigma 0.45). Bunun 3 kati bir sicrama ancak
#   ISINLANMA olabilir (gorev yeniden baslangici) -> tampon sifirlanir.
SICRAMA_HIZ = 55.0           # m/s  (ARTIK KULLANILMIYOR, bkz. SICRAMA_M)
# ⚠⚠ 2026-08-19: HIZ ESIGI BU MODULU YARISMA MODUNDA TAMAMEN CALISMAZ YAPTI.
# 20 Hz kontrol dongusunde dt=0.05 s -> esik ornek basina 55*0.05 = 2.75 m.
# Bozuk GPS ise ornekler arasi 40+ m ziplar (olculen p99 40.1, maks 43.3).
# Sonuc: hemen her ornek "isinlanma" sayilip tampon SIFIRLANIYOR.
# UCUSTA OLCULDU (tani satirlari): tampon uzunlugu 2, 4, 7, 11, 33, 2 ...
# MIN_ORNEK=120'ye HIC ulasamiyor -> periyot None -> PUSU hic atesmiyor
# (5166 satirda `pusu_tgo_s` 0 kez doldu).
# ⚠ AYNI TUZAK `fusion/periyodik_kestirici.py`'de de vardi ve orada
#   MUTLAK MESAFE esigine (150 m) cevrilerek cozulmustu; oradaki regresyon
#   testi: `test_BOZULMA_SICRAMASI_tamponu_SIFIRLAMAZ`.
# GERCEK isinlanma (gorev yeniden dogusu) YUZLERCE metredir; 150 m onu
# yakalar, bozulma sicramasini (43 m) yakalamaz.
SICRAMA_M = 150.0            # m; MUTLAK mesafe (HIZ DEGIL)


class HedefTekrar:
    """Hedefin kapali pistinden ileri konum okur.

    Kullanim:
        tk = HedefTekrar()
        tk.ekle(t, x, y, z)              # her telemetri ornegi
        if tk.hazir():
            p = tk.kestir(t + 12.0)      # 12 s sonraki konum, ya da None
    """

    def __init__(self, beklenen=PERIYOT_BEKLENEN, tolerans=PERIYOT_TOLERANS,
                 pencere_s=PENCERE_S, min_gozlem_s=MIN_GOZLEM_S,
                 kalite_max=KALITE_MAX_M, periyot_carpan=1.0):
        self._buf = deque()                  # (t, x, y, z), t ARTAN
        self._P = None                       # kestirilen periyot (s)
        self._kalite = None                  # tur-uzeri artik medyani (m)
        self._son_hesap = None
        self.beklenen = float(beklenen)
        self.tolerans = float(tolerans)
        self.pencere_s = float(pencere_s)
        self.min_gozlem_s = float(min_gozlem_s)
        self.kalite_max = float(kalite_max)
        # ⚠ OLUMSUZ KONTROL ICIN: periyodu kasten bozmak (1.2 -> %20 yanlis).
        #   1.0 = normal. Bunu 1.0 disinda birakip uretime almak HATADIR.
        self.periyot_carpan = float(periyot_carpan)

    # ── veri ────────────────────────────────────────────────────────────
    def ekle(self, t, x, y, z=0.0):
        """Bir telemetri ornegi. t monotonik ARTAN olmali."""
        if t is None or x is None or y is None:
            return
        if self._buf and t <= self._buf[-1][0]:
            # saat geriye gitti (sunucu yeniden basladi) -> tampon GECERSIZ
            self.sifirla()
        elif self._buf:
            # ⚠ SICRAMA KORUMASI: gorev yeniden baslayinca hedef ISINLANIR.
            #   Tampon fazlar arasi yasadigi icin bu sicrama iceri sizar ve
            #   periyot kestirimini bozar. Fiziksel ust sinir: hedef 18 m/s
            #   ucuyor; 1 s'de 18 m'den fazla yer degistiremez. Genis pay
            #   birakip 3 kat aliyoruz (gecikmeli ornek de olabilir).
            _t0, _x0, _y0, _z0 = self._buf[-1]
            _dt = max(t - _t0, 1e-3)
            if math.hypot(x - _x0, y - _y0) > SICRAMA_M:
                self.sifirla()
        self._buf.append((float(t), float(x), float(y), float(z or 0.0)))
        son = self._buf[-1][0]
        while self._buf and son - self._buf[0][0] > self.pencere_s:
            self._buf.popleft()

    def sifirla(self):
        self._buf.clear()
        self._P = None
        self._kalite = None
        self._son_hesap = None

    # ── ic yardimcilar ──────────────────────────────────────────────────
    def _konum(self, t):
        """Tampondan t anindaki konum (dogrusal ara deger) ya da None."""
        B = self._buf
        if not B or t < B[0][0] or t > B[-1][0]:
            return None
        lo, hi = 0, len(B) - 1
        while hi - lo > 1:
            orta = (lo + hi) // 2
            if B[orta][0] <= t:
                lo = orta
            else:
                hi = orta
        t0, x0, y0, z0 = B[lo]
        t1, x1, y1, z1 = B[hi]
        if t1 - t0 < 1e-9:
            return (x0, y0, z0)
        a = (t - t0) / (t1 - t0)
        return (x0 + a * (x1 - x0), y0 + a * (y1 - y0), z0 + a * (z1 - z0))

    def _artik(self, P, adim=None):
        """|pos(t) - pos(t-P)| medyani; kucukse P gercek periyottur."""
        B = self._buf
        if adim is None:                      # ~60 ornek noktasi hedefle
            adim = max(1, len(B) // 60)
        d = []
        for i in range(0, len(B), adim):
            t, x, y, _z = B[i]
            g = self._konum(t - P)
            if g is None:
                continue
            d.append(math.hypot(x - g[0], y - g[1]))
        if len(d) < MIN_ORTUSME:
            return None
        d.sort()
        n = len(d)
        return d[n // 2] if n % 2 else 0.5 * (d[n // 2 - 1] + d[n // 2])

    def _hesapla(self):
        """Periyodu tara. Maliyetli -> YENIDEN_HESAP_S'den sik cagrilmaz."""
        B = self._buf
        if len(B) < MIN_ORNEK:
            return
        sure = B[-1][0] - B[0][0]
        if sure < self.min_gozlem_s:
            return
        ust = min(PERIYOT_MAX, sure - 2.0)
        if ust <= PERIYOT_MIN:
            return
        en = None
        P = PERIYOT_MIN
        while P <= ust:
            a = self._artik(P)
            if a is not None and (en is None or a < en[1]):
                en = (P, a)
            P += PERIYOT_ADIM
        if en is None:
            self._P, self._kalite = None, None
            return
        self._P, self._kalite = en

    def guncelle(self, t_simdi=None):
        """Gerekiyorsa periyodu yeniden kestir. Her tik cagrilabilir."""
        if not self._buf:
            return
        t = self._buf[-1][0] if t_simdi is None else float(t_simdi)
        if self._son_hesap is not None and t - self._son_hesap < YENIDEN_HESAP_S:
            return
        self._son_hesap = t
        self._hesapla()

    # ── disari acilan ───────────────────────────────────────────────────
    @property
    def periyot(self):
        return self._P

    @property
    def kalite(self):
        return self._kalite

    def hazir(self):
        """MEKANIZMA KAPISI: kestirim guvenilir mi?

        Uc kosul da saglanmali; biri bile bozuksa cagiran ESKI davranisa
        duser. "Yaklasik dogru" kestirimle ucmak YOK.
        """
        if self._P is None or self._kalite is None:
            return False
        if self._kalite > self.kalite_max:
            return False
        if abs(self._P - self.beklenen) > self.tolerans:
            return False
        if not self._buf:
            return False
        if self._buf[-1][0] - self._buf[0][0] < self.min_gozlem_s:
            return False
        return True

    def kestir(self, t_hedef):
        """t_hedef anindaki hedef konumu (x, y, z) ya da None.

        Bir tur geriye bakar; gerekirse birden cok tur geri sarar.
        Kapi kapaliysa DAIMA None doner -- uydurma kestirim uretmez.
        """
        if not self.hazir():
            return None
        P = self._P * self.periyot_carpan
        if P <= 1e-6:
            return None
        t = float(t_hedef)
        son = self._buf[-1][0]
        # tamponun icine dusene kadar tur tur geri sar
        kacinci = 0
        while t > son and kacinci < 8:
            t -= P
            kacinci += 1
        if t > son:
            return None
        return self._konum(t)

    def ufuk_ile(self, t_simdi, ufuk_s):
        """Kolaylik: `kestir(t_simdi + ufuk_s)`."""
        return self.kestir(float(t_simdi) + float(ufuk_s))

    def tani(self):
        """Log/denetim icin durum ozeti."""
        return {
            "tekrar_periyot_s": self._P,
            "tekrar_kalite_m": self._kalite,
            "tekrar_hazir": self.hazir(),
            "tekrar_ornek": len(self._buf),
            "tekrar_sure_s": (self._buf[-1][0] - self._buf[0][0]) if self._buf else 0.0,
            "tekrar_carpan": self.periyot_carpan,
        }


def bulusma_sec(tk, simdi, ix, iy, aspect_hedef=75.0, tgo_min=2.0, tgo_max=30.0,
                tgo_adim=0.5, v_kabul=20.0, ulasim_pay=0.95,
                sapma_max=40.0, hx=None, hy=None):
    """ULASILABILIR bulusma noktalari arasindan aspect'i hedefe en yakin olani.

    Donus: (x, y, z, ux, uy, tgo, aspect_deg)  ya da  None.
      (ux, uy) = hedefin O BULUSMA ANINDAKI birim kurs vektoru; cagiran
      istasyonun "arka" yonunu bundan kurmalidir (simdiki kurstan DEGIL).

    ⚠ NEDEN SECIM: vurusu KESME GEOMETRISI uretir (aspect 60-90 deg ->
      CPA<1.5 m %55; saf kuyruk %9). Hedefin kapali pisti bilindiginde
      bulusma noktasi secilebilir. Saf kinematik tarama (n=1557):
          en iyi bant  mevcut ~%4 · basit kesisme %12 · SECILI %99
    ⚠ ULASILABILIRLIK sarti: mesafe <= v_kabul * tgo * ulasim_pay.
      Bu, DONUS dinamigini icermez -> ust sinirdir.

    ⚠⚠ SAPMA SINIRI (`sapma_max`, hx/hy verilirse) -- HAYATI:
      Sinirsiz secim istasyonu hedefin SIMDIKI yerinden medyan **130.6 m**
      (p90 217 m) uzaga koyuyor. Hedefi medyan 29 m'den goruyoruz ve
      tespit 40 m otesinde dusuyor -> arac hedefi KAYBEDER, devir olcutu
      (10 ardisik kare) hic dolmaz, SISTEM COKER. Uçmadan once olculdu.
      Tarama (n=1557), sinir -> (60-90 bandi, gercek sapma medyani):
          25 m -> %33, 19.5 m      60 m -> %65, 27.9 m
          40 m -> %55, 21.2 m     sinirsiz -> %99, 130.6 m  ⛔
      40 m faydanin cogunu verip istasyonu gorus menzilinde tutar.
      (Mevcut sistem kiyas: kesme %6, aspect medyan 150 deg.)
    ⚠ tk.hazir() False ise DAIMA None -> cagiran eski davranisi surdurur.
    """
    if not tk.hazir():
        return None
    V = max(6.0, float(v_kabul))
    en = None
    tg = float(tgo_min)
    while tg <= float(tgo_max):
        p = tk.kestir(simdi + tg)
        q = tk.kestir(simdi + tg + 0.5)
        if p is not None and q is not None:
            ux = q[0] - p[0]
            uy = q[1] - p[1]
            un = math.hypot(ux, uy)
            if un >= 0.3:
                ux /= un
                uy /= un
                rx = ix - p[0]
                ry = iy - p[1]
                rn = math.hypot(rx, ry)
                sapma_ok = True
                if sapma_max and hx is not None and hy is not None:
                    sapma_ok = math.hypot(p[0] - hx, p[1] - hy) <= float(sapma_max)
                if sapma_ok and 0.5 <= rn <= V * tg * float(ulasim_pay):
                    c = max(-1.0, min(1.0, (rx * ux + ry * uy) / rn))
                    a = math.degrees(math.acos(c))
                    sk = abs(a - float(aspect_hedef))
                    if en is None or sk < en[0]:
                        en = (sk, p, ux, uy, tg, a)
        tg += float(tgo_adim)
    if en is None:
        return None
    return (en[1][0], en[1][1], en[1][2], en[2], en[3], en[4], en[5])
