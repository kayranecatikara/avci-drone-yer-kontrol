# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Truth-tabanli dortgen dogrulama; teslim paketine girmez.)
================================================================================
KILIT DORTGENI TRUTH DOGRULAMASI (sartname tespit kurali — her asamada gecerli)
================================================================================
Kilit/video dortgeninin (= model bbox) GERCEK hedefi dogru sardigini TRUTH ile
dogrular. Uc kural (sartname):
  1) Dortgen hedefin >=%90'ini ICERMELI (IoU-benzeri: hedefin gorunur alaninin
     dortgen icinde kalan orani >= 0.90).
  2) Dortgen-hedef MERKEZ farki: yatayda hedef GENISLIGININ, dikeyde
     YUKSEKLIGININ yarisini asamaz.
  3) Cizgiler <=3 px (video kaydedici sabiti; kilit_kurali.KilitCfg.CIZGI_PX).

Truth gerektirir -> UCUS pipeline'inda YAPILAMAZ (SERT AYRIM). Pipeline
kadraj-ici proxy kullanir (kilit_kurali.dortgen_kadraj_orani); bu arac
hedef GERCEK sinirini (truth reproj + 3D model) kullanarak TAM dogrular.
kilit_kurali.dortgen_kadraj_orani ile ortak: ikisi de dortgen gecerligi olcer.

Kullanim: kosu_yonetici pnp-test / fsm-prova sirasinda cagrilir (truth reproj
hedef bbox'i ile model bbox'i kiyasla). Saf fonksiyon: sentetik unit test.
================================================================================
"""
import os
import sys

_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJ_ROOT)

from guidance.kilit_kurali import KilitCfg


def dortgen_dogrula(dortgen, hedef_gercek, cizgi_px=None, cfg=None):
    """dortgen: (cx,cy,w,h) model bbox. hedef_gercek: (cx,cy,w,h) TRUTH hedef bbox
    (reproj + 3D modelden). cizgi_px: video dortgen cizgi kalinligi.
    -> {gecerli, icerme_orani, merkez_dx_orani, merkez_dy_orani, cizgi_ok, sebep}."""
    c = cfg or KilitCfg()
    dcx, dcy, dw, dh = dortgen
    tcx, tcy, tw, th = hedef_gercek

    # 1) Dortgen hedefin >=%90'ini icerir mi (hedef alaninin dortgen icinde kalani)
    dx1, dy1, dx2, dy2 = dcx - dw / 2, dcy - dh / 2, dcx + dw / 2, dcy + dh / 2
    tx1, ty1, tx2, ty2 = tcx - tw / 2, tcy - th / 2, tcx + tw / 2, tcy + th / 2
    ix = max(0.0, min(dx2, tx2) - max(dx1, tx1))
    iy = max(0.0, min(dy2, ty2) - max(dy1, ty1))
    hedef_alan = max(tw * th, 1e-9)
    icerme = (ix * iy) / hedef_alan            # hedefin ne kadari dortgen icinde

    # 2) Merkez farki: yatayda hedef w/2, dikeyde h/2 asamaz
    mdx = abs(dcx - tcx) / max(tw / 2.0, 1e-9)  # 1.0 = tam yarim genislik
    mdy = abs(dcy - tcy) / max(th / 2.0, 1e-9)

    # 3) Cizgi kalinligi
    cizgi = c.CIZGI_PX if cizgi_px is None else cizgi_px
    cizgi_ok = cizgi <= c.CIZGI_PX

    sebepler = []
    if icerme < 0.90:
        sebepler.append("icerme<%%90 (%.2f)" % icerme)
    if mdx > 1.0:
        sebepler.append("merkez_yatay>w/2 (%.2f)" % mdx)
    if mdy > 1.0:
        sebepler.append("merkez_dikey>h/2 (%.2f)" % mdy)
    if not cizgi_ok:
        sebepler.append("cizgi>%dpx" % c.CIZGI_PX)
    return {"gecerli": not sebepler, "icerme_orani": icerme,
            "merkez_dx_orani": mdx, "merkez_dy_orani": mdy,
            "cizgi_ok": cizgi_ok, "sebep": ("; ".join(sebepler) or None)}
