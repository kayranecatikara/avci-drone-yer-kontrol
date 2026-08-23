# -*- coding: utf-8 -*-
"""
================================================================================
 KILITLENME ISTERI SAYACI — sartname 6.1.2 / 6.1.4 kaniti (SALT GOZLEM)
================================================================================
NEDEN AYRI MODUL (2026-08-11)
  Bu sayac eskiden `guidance/ana_kontrol.py` icindeki ESKI gorsel yasanin
  (`_gorsel_guduum`) icine gomuluydu. Hibrit hatta gecince (guduum artik
  Kayran'in `supervisor` + `bbox_ibvs` yasasi) o blok devre disi kaldi ve
  sayac SESSIZCE OLDU: `kilit_ok` hic True olmadi, `web/server.py`'deki
  ANGAJMAN cipi / VURUS / BASARI mandallari hic tetiklenmedi.
  Eski yasa SILINECEGI icin sayac buraya tasindi: guduumden BAGIMSIZ, yalnizca
  tespit + faz bilgisiyle beslenen bir GOZLEMCI.

⛔ KOMUTA GIRMEZ. Hicbir cikti guduume donmez; yalnizca arayuz/olay gunlugu
   ve sartname kanit zinciri icin durum uretir.

SARTNAME KURALI (degistirilmez sabitler)
  * Hedef merkezi Angajman Volumu (AV) icinde: yatay %25-75, dikey %10-90
  * Bbox EN AZ BIR eksende ekranin >= %5'i (biz %6 marjla sayiyoruz)
  * 10 sn'lik kayan pencerede KUMULATIF >= 5 sn -> kilit isteri SAGLANDI (latch)

KULLANIM
    say = KilitSayaci()
    say.guncelle(tespit, t, gorsel_faz=True)   # her gorsel tikte
    say.ok        -> bool  (kalici latch)
    say.durum()   -> telemetri sozlugu
================================================================================
"""
from collections import deque


class KilitCfg:
    """Sartname sabitleri — DEGISTIRILMEZ."""
    LOCK_PCT = 0.06      # bbox eksen orani esigi (sartname >=0.05, marjli)
    AV_X = 0.25          # AV yatay kenar payi (%25-%75 bandi)
    AV_Y = 0.10          # AV dikey kenar payi (%10-%90 bandi)
    WIN_S = 10.0         # degerlendirme penceresi (s)
    WIN_NEED_S = 5.0     # pencerede gereken kumulatif kilit (s)
    # Iki ornek arasi bu sureden buyuk bosluk KUMULATIFE SAYILMAZ (gorsel faz
    # disinda gecen zaman kilit suresi gibi gorunmesin).
    BOSLUK_MAX_S = 0.5


class KilitSayaci:
    def __init__(self, cfg=KilitCfg):
        self.cfg = cfg
        self.win = deque()          # (t, kilit_anlik)
        self.anlik = False
        self.sure = 0.0
        self.ok = False             # kalici latch (gorev boyunca)
        self.boyut = None           # son tikte bbox eksen orani (telemetri)
        self._ilan = False

    def sifirla(self):
        """Yeni gorev: pencere + latch dahil bastan."""
        self.win.clear()
        self.anlik = False
        self.sure = 0.0
        self.ok = False
        self.boyut = None
        self._ilan = False

    def guncelle(self, tespit, t, gorsel_faz=True):
        """Bir tik ilerlet.

        tespit: {"cx","cy","w","h","W","H"} | None  (TAM-KARE piksel)
        t     : monoton zaman (s)
        gorsel_faz: supervisor GORSEL fazda mi. False ise ornek "kilit yok"
                    olarak eklenir — GPS fazinda gecen zaman kilit sayilmaz.
        """
        kilit = False
        self.boyut = None
        if gorsel_faz and tespit is not None:
            try:
                W = float(tespit.get("W", 0) or 0)
                H = float(tespit.get("H", 0) or 0)
                if W > 1 and H > 1:
                    cxn = float(tespit["cx"]) / W
                    cyn = float(tespit["cy"]) / H
                    boyut = max(float(tespit["w"]) / W, float(tespit["h"]) / H)
                    self.boyut = boyut
                    c = self.cfg
                    kilit = (c.AV_X <= cxn <= 1.0 - c.AV_X
                             and c.AV_Y <= cyn <= 1.0 - c.AV_Y
                             and boyut >= c.LOCK_PCT)
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                kilit = False               # bozuk tespit = kilit yok
        self.anlik = kilit

        win = self.win
        win.append((t, kilit))
        while win and (t - win[0][0]) > float(self.cfg.WIN_S):
            win.popleft()

        sure = 0.0
        for i in range(1, len(win)):
            dt = win[i][0] - win[i - 1][0]
            if win[i - 1][1] and 0.0 < dt < float(self.cfg.BOSLUK_MAX_S):
                sure += dt
        self.sure = sure

        if (not self.ok) and sure >= float(self.cfg.WIN_NEED_S):
            self.ok = True
            if not self._ilan:
                self._ilan = True
                print("[KILIT] %.0f sn pencerede %.1f sn kumulatif kilit -> "
                      "KILIT ISTERI SAGLANDI (sartname 6.1.4: >= %.0f sn)."
                      % (self.cfg.WIN_S, sure, self.cfg.WIN_NEED_S))
        return kilit

    def durum(self):
        """Arayuz/telemetri sozlugu (salt okuma)."""
        return {"anlik": bool(self.anlik),
                "sure": round(float(self.sure), 2),
                "ok": bool(self.ok),
                "boyut_pct": (round(self.boyut * 100.0, 1)
                              if self.boyut is not None else None),
                "esik_pct": round(float(self.cfg.LOCK_PCT) * 100.0, 1),
                "pencere_s": float(self.cfg.WIN_S),
                "gereken_s": float(self.cfg.WIN_NEED_S)}
