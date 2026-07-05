# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME ARACI — teslim paketine GIRMEZ. (arac/paket_kontrol.py bu dosyayi
paketten dislar ve server.py/index.html'deki DEV-ONLY citli baglanti
noktalarini paketlerken otomatik siler.)
================================================================================
DEV HEDEF-KAYNAGI: sim'in debug/truth kanalini AvciKontrol'un HARICI hedef
kaynagi disine (set_hedef_kaynagi) baglar. Amac: gelistirme sirasinda
midcourse yaklasmayi (ARAMA/TAKIP) hedefin BOZULMAMIS konumuyla kosturmak
(filtre/gudum ayristirmasi: sorun filtrede mi gudumde mi?).

Bu bir GUDUM modu degil KAYNAK secicisidir:
  * OTO/GPS/GORSEL anahtarina dokunmaz.
  * GORSEL_TAKIP ve sonrasi ETKILENMEZ (o fazlarda hedef GNSS'i kullanilmiyor).
  * Ucus CSV'sine hedef_kaynak etiketi "gercek" yazilir (kayit ayirt edilir).

Truth'a dokunan TUM kod bu dosyadadir; ucus pipeline'inin geri kalani
(detection/guidance/fusion/web/main.py) truth kelimesi dahi icermez
(CLAUDE.md SERT AYRIM). Bu modul yoksa/yuklenemezse sunucu NORMAL baslar,
arayuzde DEV butonu hic gorunmez.
================================================================================
"""
import time

import numpy as np


class DevTruthKaynagi:
    """drone (sdk modulu) uzerinden truth okur; AvciKontrol.set_hedef_kaynagi
    sozlesmesine uygun fn saglar: fn() -> None | {"pos": cm, "vel": cm/s}."""

    def __init__(self, drone, saat=time.perf_counter):
        self.drone = drone
        self._saat = saat            # enjekte edilebilir saat (test icin)
        self.aktif = False
        self._v_prev_p = None        # hiz icin sonlu-fark durumu (truth temiz -> guvenli)
        self._v_prev_t = None
        self._v = np.zeros(3)

    # ------------------------------------------------------------------
    def mevcut(self):
        """Truth kanali su an AKIYOR mu? (oyun debug modunda mi?)"""
        try:
            return bool(self.drone.get_debug_truth().get("available"))
        except Exception:
            return False

    V_KELEPCE = 4000.0        # cm/s; hedef hizi eksen basina tavan (40 m/s > 120 km/h)

    def _hiz(self, p):
        """Truth konumundan sonlu-fark + EMA hedef hizi (cm/s, 3B).
        KELEPCE: tek karelik konum sicramasi (glitch/paket karismasi) sonlu farkta
        binlerce cm/s uretebilir; EMA'ya girse bile eksen basina V_KELEPCE'de kirpilir
        (yanlis dev hiz -> gudum lead/dikey feedforward patlamasina karsi supap)."""
        t = self._saat()
        if self._v_prev_p is None or self._v_prev_t is None:
            self._v_prev_p = p.copy()
            self._v_prev_t = t
            return self._v
        dt = t - self._v_prev_t
        if 1e-3 < dt < 0.5:
            ham = (p - self._v_prev_p) / dt
            self._v = 0.7 * self._v + 0.3 * ham
            self._v = np.clip(self._v, -self.V_KELEPCE, self.V_KELEPCE)
            self._v_prev_p = p.copy()
            self._v_prev_t = t
        elif dt >= 0.5:                                  # bayat -> resetle
            self._v_prev_p = p.copy()
            self._v_prev_t = t
        return self._v

    def _fn(self):
        """AvciKontrol harici-kaynak sozlesmesi. Truth akmiyorsa None (beyin
        hold/dropout mantigina duser — kor kalinmaz, son kestirim tasinir)."""
        try:
            dbg = self.drone.get_debug_truth()
        except Exception:
            return None
        if not dbg.get("available"):
            return None
        p = np.array(dbg["target"]["position"], float)
        v = self._hiz(p)
        return {"pos": (float(p[0]), float(p[1]), float(p[2])),
                "vel": (float(v[0]), float(v[1]), float(v[2]))}

    # ------------------------------------------------------------------
    # Gecis tutarlilik kapisi esikleri: truth/ham AYNI nesnenin AYNI birimdeki
    # konumu olmali. Bozuk GPS'in offset+spike'i ~100 m'yi gecmez; birim (cm/m),
    # indeks kaymasi (v0.0.5 telemetri format degisikligi) veya eksen/isaret
    # hatasi ise KILOMETRELERCE fark / ~100x oran uretir -> gecis REDDEDILIR.
    GECIS_ORAN_BAND = (0.5, 2.0)     # |truth|/|ham| kabul bandi
    GECIS_FARK_CM = 30000.0          # |truth-ham| tavani (300 m)

    def uygula(self, beyin, mod):
        """Kaynak gecisi: mod 'gercek' | 'filtre'. (ok, msg) doner.
        beyin_lock ALTINDA cagrilmali (server tarafinda cagiran tutar)."""
        m = str(mod).lower()
        if m == "gercek":
            if not self.mevcut():
                return False, "DEV kaynak ACILAMADI: truth kanali AKMIYOR (sim debug kapali?)"
            # (i) GECIS ANI TUTARLILIK KONTROLU: tek ornegi yan yana logla ve dogrula.
            ham = np.array(self.drone.get_target_location(), float)
            tp = np.array(self.drone.get_debug_truth()["target"]["position"], float)
            fil = None
            try:
                d = beyin.filtre.durum_guduum() if beyin.filtre is not None else None
                fil = None if d is None else np.array(d["pos"], float)
            except Exception:
                fil = None
            print("[DEV] gecis ornegi (cm):")
            print("      ham   =", np.round(ham, 1))
            print("      filtre=", (np.round(fil, 1) if fil is not None else "(isinmamis)"))
            print("      truth =", np.round(tp, 1))
            nh = float(np.linalg.norm(ham))
            nt = float(np.linalg.norm(tp))
            oran = nt / max(nh, 1e-9)
            fark = float(np.linalg.norm(tp - ham))
            print("      |truth|/|ham| = %.3f   |truth-ham| = %.1f m   dz = %.1f m"
                  % (oran, fark / 100.0, (tp[2] - ham[2]) / 100.0))
            if not (self.GECIS_ORAN_BAND[0] <= oran <= self.GECIS_ORAN_BAND[1]) \
                    or fark > self.GECIS_FARK_CM:
                return False, ("GECIS REDDEDILDI: truth/ham TUTARSIZ (oran %.2f, fark %.0f m)"
                               " - birim/indeks/eksen suphesi; konsoldaki ornege bak."
                               % (oran, fark / 100.0))
            self._v_prev_p = None                        # hiz kestirimi taze baslasin
            self._v_prev_t = None
            self._v = np.zeros(3)
            beyin.set_hedef_kaynagi(self._fn, "gercek")
            self.aktif = True
            return True, ("KAYNAK: GERCEK (DEV) — midcourse bozulmamis hedef konumuyla "
                          "gudulur. GELISTIRME MODU; yarisma/video kosusu DEGIL.")
        if m == "filtre":
            beyin.set_hedef_kaynagi(None, "filtre")
            self.aktif = False
            return True, "KAYNAK: FILTRE — uretim yolu (Inovasyonlu J) aktif."
        return False, "Gecersiz kaynak modu: %s" % mod

    def durum(self, beyin):
        """Arayuz icin ozet (telemetriye 'dev' alani olarak eklenir)."""
        return {"var": True,
                "aktif": bool(getattr(beyin, "hedef_kaynak_ad", "filtre") == "gercek"),
                "akiyor": self.mevcut()}
