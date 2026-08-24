# -*- coding: utf-8 -*-
"""OMUR SUPURMESI: fazi yasatan ucuz kaldiraclar.

Olculen kisit: faz omru 1.28 s, 9 m'yi kapatmak 2.3 s istiyor.
Hiz yolu KAPALI (S9 kiyasi: hiz omru kisaltiyor, iskayi kotulestiriyor).
Geriye omru uzatan kaldiraclar kaliyor:

  1) conf kapisi 0.35 -> 0.28. Dedektor ZATEN 0.25 ile kosuyor
     (server.py:1461 predict esigi = min(0.25, VIS_CONF_MIN)); 0.25-0.35
     arasi tespitler hesaplaniyor ve server.py:1528 kapisinda ATILIYOR.
     Maliyet SIFIR ms. Olculen: kayiptan onceki son conf medyani 0.527,
     p10 0.383 -> dedektor esigin icinden asagi sizarken kesiliyor.
     Negatif-kare tavani 0.219 -> 0.28'de 0.06 marj var.
  2) KAYIP_M 20 -> 30. Olculen 21 Hz'de 20 kare = 0.95 s kor pencere
     (koddaki "0.66 s" yorumu 30 Hz varsayiyor, YANLIS). 30 -> 1.43 s.
     Taksonomi: 93/93 faz 19 karelik olum serisiyle bitiyor.
"""
import json, time, sys, urllib.request

KOK = 'http://127.0.0.1:8000'


def ozellik(a, d):
    q = urllib.request.Request(KOK + '/api/gudum_ozellikleri',
                               data=json.dumps({"anahtar": a, "deger": d}).encode(),
                               headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(q, timeout=6) as r:
        return json.loads(r.read().decode('utf-8', 'replace')).get('ok')


def tune(p, v):
    q = urllib.request.Request(KOK + '/api/tune',
                               data=json.dumps({"param": p, "value": v}).encode(),
                               headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(q, timeout=6) as r:
        return json.loads(r.read().decode('utf-8', 'replace')).get('ok')


# ⚠ 2. TUR: conf SABIT 0.35. Ilk turda conf 0.28 ile KAYIP_M birlikte
# denendi ve etki cikmadi; simulator conf 0.28'in vurusu %5->%2 DUSURDUGUNU
# soyluyor -> ikisi birbirini goturmus olabilir. Simdi tek degisken.
# Simulator tahmini (Tezgah B, kalibre): K20 12.3m | K30 9.8m | K45 7.3m | K60 5.7m
# ⚠ 3. TUR: KAYIP_M 60 SABIT (ucusta dogrulandi: omur 1.91->3.06 s, iska
# 12.47->10.10 m, EN IYI 3.71 m). Pencere acildigi icin ARTIK yasa olculebilir.
# 2. ajanin sirasi: pencere acilinca siralama TERSINE donuyor -- PN kotulesiyor,
# saf takip + sessiz burun kazaniyor. Tahmin: PN kapali ve K_YAW 0.3 iyilestirir.
# ⚠ 4. TUR — GPS FAZI HIZ TAVANI. Bugunku en buyuk kaldirac bu olabilir:
# olculdu, komut hizi %100 DOYMUS (p50=p90=max=22.0), kapanma payi +2.3 m/s.
# Devir menzili ile iska neredeyse deterministik (rho +0.994):
#     <10 m -> 4.91 m (%10 vurus) | 13-16 m -> 10.94 m (%1.8) | simdi 15.7 m
# Yani devri yakinlastirmak tek basina bandi degistiriyor.
# ⚠ 5. TUR — KOR KOPRU. Olculen en buyuk acik:
#   gorsel fazin %60'inda kutu YOK ve son komut (yaw dahil) aynen tekrarlaniyor
#   tespit VARKEN  hiz yonu <-> hedefe yon : medyan  8.3°
#   faz GENELINDE                          : medyan 56.4°, %24'u >90°
# Kisir dongu: tespit kesildi -> burun DONDU -> kutu kenara gitti -> kor kaldi.
# Kopru kutuyu piksel hiziyla ileri tasiyip komutu VE burnu tazeler.
# Bosluk serisi p90 = 19 kare (~0.6 s @31 Hz) -> 0.6 s bosluklarin %90'ini yutar.
# ⚠ 6. TUR — ATALET KOPRUSU (piksel surumunun DOGRU hali).
# PIKSEL surumu ucusta ZARARLI cikti (TUM 42.9 -> 70.9°, tespitli kareler
# dahil bozuldu 8.2 -> 25.7°): piksel hizi icinde KENDI BURUN DONUSUMUZ var,
# onu "hedef gidiyor" sanip geri besliyordum -> parazitik dongu.
# ATALET surumu kendi yaw'imizi ACIKCA cikarir:
#     eps_kopru = los_son - iris_yaw(SIMDI)
# Burun kerterize dondukce eps KUCULUR -> geri besleme yapisal olarak yok.
# Olcut: KORKEN sutunu (su an 73.3°) dusmeli, GORURKEN (8.2°) BOZULMAMALI.
# ⚠ 7. TUR — ATALET KOPRUSU, DOGRU SURE. Onceki testim (0.30/0.60 s) UC
# sebeple gecersizdi:
#   1) SURE: simulator yaylayi 1.5-2.0 s buluyor; ben yaylanin ALTINDA test
#      ettim. Yapisal kapi: KOR_KOPRU > KAYIP_M/31 Hz olunca hukumsuz.
#   2) OLCUT: "sapma" tek basina EN KOTU stratejiyi seciyor -- piksel
#      koprusu sapmayi fazi ERKEN OLDUREREK dusuruyor (tespitli sure
#      2.13 -> 0.65 s). Dogru sira: once omur/tespit gerilemesin, sonra ISKA.
#   3) GUC: ayni ayar iki kosuda 25° fark verdi (B0 42.9° vs A0 68.3°).
# Simulator (9 kosulun 9'unda kazandi): iska 10.59 -> 6.08 m.
# ⚠ Ama tezgah olum anindaki |eps|'i 6° veriyor, saha 52° -- yani koprunun
# en buyuk iddiasi tezgahta OLCULEMIYOR. Saha karari sart.
# ⚠ 8. TUR — KOPRU YATAY HIZ KAZANCI. Kopru denetimi en buyuk kusur olarak
# isaretledi: KP_VH=0.024 -> kapali dongu tau 0.72 s, arac 0.31 s kaldiriyor.
# Canli: |yaw|>120 °/s'de yanal hata 8.25 m/s ama cubuk 0.277 (tavan 0.75).
# ⚠ KADEMELI: 0.09'da asma buyuyor. Salinim gorursen SUPURMEYI DURDUR.
# Atalet koprusu (1.5 s) ACIK kalir -- o zaten kalici yapildi.
# ⚠ 9. TUR — ATALET KOPRUSU TEKRAR TESTI (1.5 s).
# Ilk olcum guclu cikti: tekrarli referans 12.12 / 12.40 m, kopru 2.81 m,
# 13 fazin 8'i 3 m esiginde. AMA TEK PENCERE. Matris ajani uyariyor:
# "kerteriz sabit" varsayimi TAM MANEVRADA kiriliyor (donuste -8, giriste -12).
# ⚠ Ajan koprunun 0.3/0.6 s'sini test etmis (yaylanin ALTI); 1.5 s'i degil.
# Bu tur: ayni tasarim, FARKLI pencere. Tekrar ederse saglam.
# ⚠ 10. TUR — KOPRU YATAY HIZ KAZANCI, SARTNAMEYE UYGUN ayarla.
# KAYIP_M = 20 (SARTNAME: "ust uste 20 karede tespit edemezse GPS'e gec").
# Kopru denetimi: KP_VH=0.024 -> kapali dongu tau 0.72 s; acik dongu
# basamak testinden K=91 (m/s)/stick, tau_v=2.28 s -> arac 0.31 s kaldiriyor.
# Canli: |yaw|>120 °/s'de yanal hata 8.25 m/s ama roll cubugu 0.277 (tavan .75)
# -> yetki TAVANDA degil KAZANCTA kaybediliyor.
# ⚠ KADEMELI: 0.09'da asma buyumeye basliyor. Salinim gorursen DURDUR.
AYARLAR = [
    ("P024_temel", {"conf": 0.35, "KAYIP_M": 20, "KP_VH": 0.024}),
    ("P045",       {"conf": 0.35, "KAYIP_M": 20, "KP_VH": 0.045}),
    ("P070",       {"conf": 0.35, "KAYIP_M": 20, "KP_VH": 0.070}),
    ("P024_geri",  {"conf": 0.35, "KAYIP_M": 20, "KP_VH": 0.024}),
]


def main():
    sure = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
    while True:
        try:
            with urllib.request.urlopen(KOK + '/api/telemetry', timeout=4) as r:
                if json.loads(r.read().decode()).get('gorev_aktif'):
                    break
        except Exception:
            pass
        time.sleep(2.0)
    kayit = []
    for ad, kw in AYARLAR:
        tune("VIS_CONF_MIN", kw["conf"])
        for _k in ("KAYIP_M", "PN_N", "K_YAW", "V_MAX", "KOR_KOPRU_S", "KOR_KOPRU_ATALET_S", "KP_VH",
                   "BURUN_KD", "KADRAJ_ESIK_DEG"):
            if _k in kw:
                if not ozellik(_k, kw[_k]):
                    print("  !! %s yazilamadi (canli listede olmayabilir)" % _k, flush=True)
        print("  [%s] %s" % (ad, kw), flush=True)
        t0 = time.perf_counter()
        time.sleep(sure)
        kayit.append({"ad": ad, "ayar": dict(kw), "t0": t0, "t1": time.perf_counter()})
        print("  [%s] bitti" % ad, flush=True)
    with open("veri/ab_pn_pencereler.json", "w", encoding="utf-8") as f:
        json.dump(kayit, f, indent=1)
    print("  -> python arac/pn_kiyas.py", flush=True)


if __name__ == "__main__":
    main()
