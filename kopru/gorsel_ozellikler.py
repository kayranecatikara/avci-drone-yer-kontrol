# -*- coding: utf-8 -*-
"""
kopru/gorsel_ozellikler.py — GORSEL/HIBRIT YASA OZELLIK ANAHTARLARI (panel).

NEDEN VAR (kaynak CLAUDE.md §5, kullanici kurali 2026-08-10):
    "her defasinda tum sistemi bastan farkli ayarlarla calistirmam gerekmesin;
     anlik acip kapayarak farki daha iyi gozlemleyeyim"
    -> sisteme eklenen HER davranis anahtarinin panelde ac/kapa dugmesi olacak.

NASIL CALISIR
    bbox_ibvs.Cfg ve supervisor.SupCfg birer SINIF; gudum dongusu her karede
    cfg.<ALAN> okuyor. Sinif niteligini degistirmek BIR SONRAKI kareden itibaren
    gecerli -> yeniden baslatma GEREKMEZ. (supervisor.IbvsCfg is bbox_ibvs.Cfg
    dogrulandi -> tek nesne, tek yerden degisir.)

⛔ YASA DOSYALARINA DOKUNULMAZ. Burasi yalnizca calisma aninda sinif niteligi
   yazar — yasa_senkron.py ile dosyalar her zaman dalin HEAD'iyle birebir kalir.

YENI OZELLIK EKLEMEK: asagidaki OZELLIKLER listesine TEK SATIR ekle.
Sunucu ve arayuz listeyi buradan cekiyor; HTML/JS'e dokunmak GEREKMEZ.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_YASA = os.path.join(_HERE, "gazebo_kaynak")

# (anahtar, modul, tur, alt, ust, etiket, aciklama)
#   modul: "ibvs" = bbox_ibvs.Cfg | "sup" = supervisor.SupCfg
#   tur  : "bool" | "float" | "int"
# Durumlar kaynagin UYGULANACAK.md kampanyalarindan; "?" = DoW'da HIC olculmedi.
OZELLIKLER = [
    ("KP_VH", "kopru", "float", 0.010, 0.090, "★ Kopru yatay hiz kazanci",
     "⚠ KOPRU DENETIMI (2026-08-16) EN BUYUK KUSUR OLARAK ISARETLEDI. "
     "Acik dongu basamak testi: K=91 (m/s)/stick, tau=2.28 s. Kapali dongu "
     "tau = 2.28/(1+91*KP). KP=0.024 -> 0.72 s; arac 0.31 s'yi (KP=0.070) "
     "kaldiriyor -> UC KAT yavas. Canli olcum: |yaw hizi|>120 °/s iken yanal "
     "hiz hatasi 8.25 m/s ama uretilen roll cubugu 0.277 (tavan 0.75) -- "
     "yetki TAVANDA degil KAZANCTA kaybediliyor. Simulasyon: 45 °/s donuste "
     "yon hatasi 29.8 -> 13.0°, 90 °/s'de 46.6 -> 25.0°. "
     "⚠ 0.09'da asma buyumeye basliyor, 0.20 kullanilamaz. Tezgah 0.07'nin "
     "UCUSTA kararli oldugunu KANITLAYAMAZ (oyunun ic donguleri modellenmiyor) "
     "-> KADEMELI artir, salinim gorursen geri al."),

    ("V_MAX", "gg", "float", 16.0, 32.0, "GPS fazi yatay hiz tavani (m/s)",
     "⚠ OLCULDU 2026-08-16: komut hizi p50=p90=max=22.0, yani tavan %100 "
     "DOYMUS. Gerceklesen 21.1, hedef 18.8 -> kapanma payi sadece +2.3 m/s. "
     "GPS fazi 9 m istasyona bu yuzden gec variyor ve devir 15.7 m'de oluyor. "
     "Devir menzili ile iska neredeyse deterministik (rho +0.994): <10 m'de "
     "iska 4.91 m ve %10 vurus, 13-16 m'de 10.94 m ve %1.8. Zarf 34.6 m/s. "
     "⚠ Hizli gitmek hedefin yayinda kalmayi zorlastirir (a = V²/51): "
     "V=26 -> 13.3, V=30 -> 17.6 m/s² gerekir."),

    ("RANGE_SET", "gg", "float", 6.0, 30.0, "GPS istasyon slant menzili (m)",
     "Istasyon = RANGE_SET*cos(ELEV) arka + RANGE_SET*sin(ELEV) alt. "
     "25 -> 22.66 arka + 10.57 alt idi; devir kapisi (14 px = 22.2 m) "
     "dolmuyordu ve dikeyde 25° altta kaliyorduk (yasanin nisan dengesi 5°). "
     "18'e cekildi -> 17.7 arka + 3.1 alt. Bu alan HER TIK okunur, canli."),

    # ── ZARF CLAMP'LERI (2026-08-16) — ucusta olculdu, YAZILIM bogazliyor.
    #    Aracin FIZIKSEL zarfi (kumanda cubugu dogrudan surulerek olculdu):
    #        yanal ivme 39.22 m/s²   max hiz 34.6 m/s   tirmanma 33.7 m/s
    #    Bizim clamp'lerimiz: 12 / 24 / 3  -> sirasiyla 3.3x, 1.4x, 11x dusuk.
    #    OLCULEN SONUC: gorsel fazda kapanma hizi sadece +3.4 m/s (hiz orani
    #    1.2:1), faz 1.8 s yasiyor, 20 m'yi kapatmak icin gereken sure yok.
    #    Bu yuzden HANGI GUDUM YASASI konursa konsun fark etmiyor (4 ayar A/B:
    #    hepsi ~19.5 m). Once kapanma hizi, sonra yasa.
    ("V_TOPLAM_MAX", "ibvs", "float", 12.0, 33.0, "Azami toplam hiz (m/s)",
     "Hedef 17.98 m/s SABIT. 24 -> kapanma payi 6 m/s (tavan). Zarf 34.6."),
    ("MAX_ACCEL", "ibvs", "float", 4.0, 38.0, "Azami ivme / donus yetkisi (m/s²)",
     "a = V*omega: 12 m/s² ve 21.6 m/s'de donus tavani 31.8 °/s. Olculen LOS "
     "donus hizinin ust yuzdelikleri bunu ASIYOR -> arac komut duzeyinde "
     "donemiyor. Zarf 39.22."),
    ("VZ_MAX", "ibvs", "float", 1.0, 30.0, "Azami dikey hiz (m/s)",
     "Olculdu: hedefin 8-10 m ALTINDA duruyoruz, dikey komut faz boyunca "
     "3 m/s tavanina yapisik ve aciyi hic kapatamiyor. Zarf 33.7 (tirmanma)."),

    # ── PN / DEVIR (2026-08-16) — ucus sirasinda ayarlanabilsin diye burada.
    #    Bunlar acilmadan once her deney bir sunucu yeniden baslatmasi
    #    gerektiriyordu ve o da ucusu kesiyordu.
    ("YAW_HIZALA_S", "ibvs", "float", 0.0, 0.15, "λ̇ icin yaw zaman hizalamasi (s)",
     "los_az = iris_yaw(SIMDI) + piksel(D once) idi; fark yaw_ivmesi*D kadar "
     "SAHTE LOS hizi uretiyordu. Olculdu: yasanin lam'i truth'un 7.1 KATI. "
     "Bu deger dedektor gecikmesi (det_ms p50 29.7 ms + yakalama). 0 = kapali. "
     "Supurup lam_sisme'yi en kucuk yapan degeri sec — o gercek gecikmedir."),

    ("KUTU_MAX_KAPANMA", "ibvs", "float", 0.0, 30.0, "★ Kutu buyume hizi siniri (m/s)",
     "⚠ GORSEL FAZIN BIZI ATMASININ SEBEBI: menzil 8 m'de SABITken kutu "
     "20 -> 44 px firliyordu (hedef kadraj KENARINA kayinca gorunur boyut "
     "sisiyor). Hiz yasasi 'cok yakinim' deyip komutu 18.6 -> 9.8 m/s'ye "
     "dusuruyor, hedef 18 m/s gidiyor -> saniyede 8 m aciliyoruz. "
     "10 gorsel fazin 10'u bizi ortalama +21 m UZAKLASTIRIYORDU. "
     "Kutu ∝ 1/menzil oldugu icin buyume hizi kapanma hiziyla SINIRLI: "
     "sinir = boyut² * bu_deger / MENZIL_PX_M. Kuculme serbest. 0 = kapali."),

    ("KOR_KOPRU_ATALET_S", "ibvs", "float", 0.0, 1.5, "★ Kor kopru ATALET (KAZANAN)",
     "Kor karede hedefin ATALET KERTERIZI korunur ve GUNCEL yaw ile piksele "
     "cevrilir: eps = los_son - iris_yaw(simdi). Kendi donusumuz acikca "
     "cikarildigi icin parazitik dongu YAPISAL OLARAK kurulamaz. "
     "⚠ Piksel surumu (KOR_KOPRU_S) ucusta ZARARLI cikti: TUM 42.9->70.9°, "
     "tespitli kareler dahil bozuldu (8.2->25.7°). Bu onun dogru hali. "
     "⚠ Hedefin kerterizinin SABIT kaldigini varsayar -> sure KISA tut. 0 = kapali."),

    ("KOR_KOPRU_S", "ibvs", "float", 0.0, 1.5, "Kor kopru — PIKSEL (ZARARLI)",
     "⚠ OLCULEN EN BUYUK ACIK: gorsel fazin %60'inda kutu YOK ve son komut "
     "aynen tekrarlaniyor. Tespit varken hiz yonu hedefe 8.3° yakin, faz "
     "genelinde 56.4° ve %24'u >90° -- yani kor karelerde savruluyoruz. "
     "Bu ayar kutuyu son iki tespitin piksel hiziyla ileri tasiyip komutu "
     "TAZELER. Kopru karesi tespit SAYILMAZ (kayip sayaci isler). 0 = kapali."),

    ("BURUN_KD", "ibvs", "float", 0.0, 1.0, "⚠ Burun ongoruleme (FAYDASIZ)",
     "yaw_cmd += KD * (kutunun kadraj ici kayma hizi). Kutu sola kaymaya "
     "basladiysa burun ONCEDEN o tarafa doner. ⚠ Atalet LOS hizi DEGIL, saf "
     "piksel gozlemi -- lam 4-7 kat sisik oldugu icin ona baglanmadi. "
     "Oransal kazanci artirmak salinim yapar (46 ms olu zaman + 211 ms "
     "gecikme); TUREV faz ondelemesi katip kararliligi artirir. 0 = kapali. "
     "⚠ KARSI-SINAMA: gerekce TUTMADI -- omur her ayarda KISALIYOR "
     "(3.65 -> 2.76 s), iska 10.48 -> 11.07, vurus 18 -> 12/240. Jitter 3-5 px "
     "ile salinim CIKMADI (0.30 s pencere gurultuyu yutuyor) -> zararsiz ama "
     "faydasiz. Kalici yapmayin."),
    ("KADRAJ_ESIK_DEG", "ibvs", "float", 0.0, 61.0, "⚠ Kadraj oncelik esigi (ETKISIZ)",
     "|eps| bu esige yaklastikca KAPANMA kisilir, hiz hedefinkine doner: "
     "hedef kenara giderken ustune gitmeyi birakip once nisani toparlar. "
     "Olculen: kayip orani merkezde 0.036, >39°'de 0.609; olum aninda |eps| "
     "medyani 52°, kadraj siniri 61°. 0 = kapali. "
     "⚠ KUSURLU: kismanin tabani hiz_I ve I_MAX=24=V_TOPLAM_MAX. Integral "
     "doydugunda terim TAMAMEN OLU (olculdu: hiz_I=24, esik 45 -> v_los 24.00, "
     "hic kisma yok). Menzil aciliyorken integral doydugu icin tam ihtiyac "
     "duyulan rejimde kendini kapatiyor. Karsi-sinama: iska 10.48 -> 11.63."),

    ("K_YAW", "ibvs", "float", 0.1, 1.5, "⚠ BURUN + HIZ YONU kazanci (1.0 = tam)",
     "⚠ ISIM YANILTICI, DUZELTILDI: K_YAW yalniz burnu DEGIL, HIZ YONUNU de "
     "carpiyor -- bbox_ibvs.py:903 (hiz_yonu) ve :915 (PN tabani _taban). "
     "Yani 1.0 -> 0.3 direksiyon yetkisini %70 KISAR. PN acikken psi_v ilk "
     "karede o yanli yonden tohumlaniyor ve bir daha LOS'a baglanmiyor -> "
     "kalici ~20° yanlilik. "
     "⚠ KARSI-SINAMA: 'sessiz burun kazanir' onerisi KIRILDI -- vurus "
     "18 -> 7/240 (-%61); cok yakin devirde 15/120 -> 3/120. KISMAYIN."),

    ("PN_N", "ibvs", "float", 0.0, 4.0, "Oransal seyrusefer kazanci N",
     "Hiz yonunu LOS'a esitleme, LOS hizinin N katiyla dondur (psi_v += N*lam*dt). "
     "0 = kapali (eski saf takip). Simulator 510 angajman: saf takip 37/480, "
     "PN 357/480. Yayla N=1.4-1.6; N<=1.2 yakinsamiyor, N>=3 iraksiyor."),
    ("PN_PENCERE_S", "ibvs", "float", 0.0, 0.60, "lam kestirim penceresi (s)",
     "LOS hizi ardisik farkla degil EN KUCUK KARELER egimiyle kestirilir. "
     "Ardisik fark gurultusu sigma_px/(F*dt); 1 px ve 62 Hz'de 21 deg/s sahte "
     "LOS hizi uretir ve PN onu N katlar. 0 = eski EMA turevi."),
    ("BURUN_LOS", "ibvs", "bool", 0, 1, "Burun = LOS (arayici/govde ayrismasi)",
     "yaw_cmd'den '- sonum + lead_az' cikar. Bunlar DIREKSIYON terimleri, "
     "kameranin isi degil; lead tavani 9 derece iken kamera hedefi bilerek "
     "yanlis gosterip lam kestirimini de yanliyordu. Tek basina yetmez (0/40), "
     "PN ile birlikte 29/40 — ikisi AYRILMAZ."),
    ("DEVIR_BOYUT_PX", "sup", "float", 0.0, 40.0, "Devir icin asgari kutu (px)",
     "Kutu bundan kucukse tespit SAYILMAZ -> faz devretmez. Olculen bagıntı "
     "R*max(w,h)=310 px·m: 14 px = 22 m, 24 px = 13 m. Simulator 30 m ustunde "
     "cokuyor. 0 = kapali."),

    # ── Ucusta DOGRULANMIS, varsayilan ACIK ──
    ("ROLL_TELAFI", "ibvs", "bool", 0, 1, "T1a yatay roll/pitch telafisi",
     "Gazebo M1: 6/6 olcutte iyi (yatay hata 66->50 px, salinim 0.104->0.000). "
     "DoW'da roll isareti 2026-08-13'te duzeltildi — bundan once TERS calisirdi."),
    ("KAPANMA", "ibvs", "bool", 0, 1, "Dikey komut kapanma hiziyla olceklenir",
     "'Son anda ustten gecme'nin kok nedeni icin eklendi (Gazebo b42c30e)."),
    ("LEAD_SONUM", "ibvs", "bool", 0, 1, "Lead menzille soner",
     "Uzakta lead az, yakinda tam."),

    # ── Kodlandi ama NOTR/KAPALI (Gazebo'da olculdu, DoW'da olculmedi) ──
    ("LEAD_ERKEN", "ibvs", "bool", 0, 1, "M3 · erken lead (terminal kapisi yok)",
     "Gazebo 3'e 3 donusumlu kampanya: NOTR. Zarar vermedi, fayda da olcelemedi."),
    ("KACIS_KD", "ibvs", "float", 0.0, 3.0, "O1 · kacis telafisi (kapanma hizi)",
     "v_los'a -K_D*rdot ekler: hedef kacmaya baslayinca hiz ANINDA artar, "
     "integralin 5 saniyesini beklemez. 0 = kapali. Gazebo: olcut celiskisi."),
    ("YANAL_K", "ibvs", "float", 0.0, 6.0, "O8 · yanal komut (kacirma mesafesi)",
     "Gazebo 18 ucus: SALINIMI COZDU, menzili cozmedi. 0 = kapali, acik ~3.0."),
    ("SONUM_T", "ibvs", "float", 0.0, 1.0, "O9 · yatay sonumleme (D terimi)",
     "Gazebo 12 ucus: sakinlestirdi, yaklastirmadi. 0 = kapali, acik ~0.30."),
    ("DONUS_A", "ibvs", "float", 0.0, 15.0, "O5 · donus-farkinda hiz tavani",
     "Sert donuste hizi kisar (yaricap kucultur). Gazebo 10 ucus: GIRMEDI. "
     "0 = kapali, acik ~9.0."),
    # ── UCUSTA A/B KAZANDI, VARSAYILAN ACIK (2026-08-17) ──
    ("DIKEY_UFUK", "ibvs", "bool", 0, 1, "★ D1 · dikey nisan UFKA bagli",
     "Gorsel TUTUS yasasi nisani govdeye sabit pikselde (CY_NISAN=301) "
     "tutuyordu; bunun DUNYA yukselisi 4.888°+pitch oldugu icin dikey denge "
     "noktasi R=14 m'de hedefin 1.4 m USTUNDE kaliyordu ve hizlanirken burun "
     "asagi gidince denge daha da YUKARI kaciyordu (yatay kanal dikeye sahte "
     "'tirman' enjekte ediyor). Acikken nisanin DUNYA yukselisi sabitlenir -> "
     "denge her menzilde ES IRTIFA, pitch kuplaji YOK. "
     "UCUS A/B (recete_gecis.json, kol basina 12 dk): |dz| 1.39 -> 0.84 m, "
     "<2 m gecis %25 -> %41, temas 2 -> 5. Olumsuz kontrol (dikey kazanci "
     "TEK BASINA artirmak) 5/5 olcude KOTULESTI -> teshis kanitlandi. "
     "Kapatmak: AVCI_IBVS_DIKEY_UFUK=0 (bit-ayni eski davranis)."),
    ("UFUK_ELEV_DEG", "ibvs", "float", 0.0, 6.0, "D1 · ufuk nisan ofseti (°)",
     "+ = hedefin bu kadar derece ALTINDA kal (gokyuzu arka plani payi). "
     "⚠ 2.0 DENENDI VE KAYBETTI: CPA 2.84 -> 5.53 m, <2 m %41 -> %12. "
     "Yani 'alttan bakinca tespit daha iyi' beklentisi UCUSTA DOGRULANMADI. "
     "0 = tam es irtifa (varsayilan, kazanan)."),
    ("HIZ_SICAK_PAY", "ibvs", "float", -1.0, 4.0, "★ Y1 · hiz sicak baslangic payi",
     "Gorsel faz hiz integralini GPS'in hedef-hiz kestiriminden (ff) aliyordu; "
     "o kestirim RMS 4.63 m/s hatali ve %62'si hedefin hizinin ALTINDA -> "
     "devirlerin %28'inde komut edilen hiz hedefinkinden dusuk, yani kapanma "
     "MATEMATIKSEL OLARAK IMKANSIZ. Acikken taban = KENDI hizimiz - pay "
     "(araci kendi sensoru; canli GPS DEGIL, D0 uyumlu) ve YALNIZ YUKARI ceker. "
     "Saha: ff kotuyken en yakin menzil 11.85 m, iyiyken 3.95 m. "
     "⚠ SEYREK BAGLAR (fazlarin ~%8'i) -- ortalamayi degil, kapanmanin "
     "imkansiz oldugu fazlari kurtarir. <0 = KAPALI. Kapatmak: -1."),

    ("DIKEY_ROLL", "ibvs", "bool", 0, 1, "T1b · dikey roll telafisi",
     "⚠ KODLANDI ama HIC UCULMADI. Gazebo mekanizma kapisi eledi: terminalde "
     "gercek duzeltme medyan -0.06 deg. Hedef kadraj KENARINDA + sert yatista "
     "anlamli olabilir."),

    # ── MANEVRA KANALI (2026-08-17, ayna sonrasi olcum) ──
    # Olculdu: donuste CPA 2.69 -> 6.43 m ve iska YANAL DEGIL BOYUNA
    # (hedefin 4.42 m ARKASINDA kaliniyor, kapanma -0.84 m/s).
    # Sebep: hiz vektoru LOS'un 42.8 derece gerisinde -> sigma -18.2 +
    # arac gecikmesi -16.4. Donus komutu karelerin %54.1'inde DOYUYOR.
    ("DONUS_BUTCE", "ibvs", "float", 0.0, 1.0, "M1 · donus butcesi hiz kapisi",
     "V <= PAY * MAX_ACCEL / |istenen donus hizi|. Tavan (a/V) talebin "
     "altindaysa hizi kisip TAVANI BUYUTUR. Yalniz seyirde, yalniz kisar, "
     "duz segmentte baglamaz. 0 = kapali, onerilen 0.9."),
    ("DONUS_BUTCE_VTABAN", "ibvs", "float", 10.0, 22.0,
     "M1 · donus kapisi hiz tabani (m/s)",
     "Hedef 18 m/s; kapi tabansiz birakilirsa lam sicramasinda hiz cok duser "
     "ve hedef kacar. Varsayilan 15.0."),
    ("ARAC_TAU", "ibvs", "float", 0.0, 1.0, "M2 · arac gecikme telafisi (s)",
     "Gercek hiz yonu, komut edilen psi_v'nin 16.4 derece gerisinde kaliyor "
     "(29 deg/s'de tau=0.57 s). CIKISA tau*w kadar ongoru eklenir; GIRDI "
     "kerterizine DOKUNULMAZ (kerteriz ileri sarmasi olcumle curutuldu). "
     "0 = kapali, onerilen 0.35."),
    ("TERM_LAM_MAX_DEG", "ibvs", "float", 0.0, 40.0,
     "⛔ terminal lam kapisi (CURUTULDU)",
     "Ayna duzeldikten sonra yasanin lam'i hedefin DUZ/DONUS halini AYIRT "
     "EDEMIYOR (DUZ med 18.0 vs DONUS 28.5 deg/s). Esik 12 ile gerceklesen "
     "18 terminal taahhudun 15'i bloklanirdi ve bloklananlar CPA_med 2.66 m "
     "ile IYI olanlardi. 0 KALSIN."),

    # ── Dedektor esigi — DoW'da MUTLAKA olculmeli ──
    ("CONF_MIN", "ibvs", "float", 0.05, 0.60, "M2 · gorsel yasa guven esigi",
     "⚠ 0.35 GAZEBO dedektorune gore. Gazebo M2 olcumu: 0.15'te takip 3x iyi, "
     "temas 2x uzun. Bizim best.pt farkli dagilimda (medyan 0.468, p10 0.069) "
     "-> DoW'da AYRICA olculmeli."),

    # ── Faz yoneticisi (supervisor) ──
    ("KILIT_SURE_S", "sup", "float", 0.0, 10.0, "★ Devir icin KILIT SURESI (s)",
     "GPS, kilit bu sureyi doldurana kadar KESILMEZ. 0 = kapali (yalniz "
     "10-kare olcutu). ⚠ OLCULDU: 10-kare olcutuyle devredince gorsel faz "
     "10/10 fazda bizi 11.7 m'den 32.1 m'ye ATIYORDU ve kilit hic birikemiyordu. "
     "Supervisor'in okudugu sayac faz fark etmeksizin sayar (ana_kontrol.py:1000), "
     "yani GPS fazinda da birikir -- istenen sira budur: GPS tutar, kilit dolar, "
     "sonra devredilir."),

    ("KILIT_N", "sup", "int", 3, 30, "D0 · devir icin tespit sayisi",
     "Gorsel faza gecmek icin gereken tespit. Gazebo 2b8d68c ile 'ardisik 10' "
     "oldu -> ilk devir menzili 16.8-18.8 m (iki kat uzak, kural uyumu temiz)."),
    ("KILIT_ARDISIK", "sup", "bool", 0, 1, "D0 · ARDISIK mi, kayan pencere mi",
     "Acik = ardisik N tespit (yeni, sade). Kapali = son KILIT_PENCERE karede N."),
    ("KAYIP_M", "sup", "int", 5, 150, "Gorsel faz kayip esigi (kare)",
     "Bu kadar ardisik tespitsiz kare -> GPS'e don. Yasanin kendi degeri 20 "
     "(30 Hz varsayimi = 0.66 s). Bizim dedektor ~15 FPS ve 0.5-1 s delik "
     "aciyor -> 20 kare 1.3 s'de fazi OLDURUYOR. Olcum (11 Agu): hibrit acik "
     "130 gecis / istasyonda kalma %32. 60 kare ~4 s tipik deligi yutar."),
]

_INDEKS = {o[0]: o for o in OZELLIKLER}


def _moduller():
    """bbox_ibvs + supervisor modullerini getir (yasa yolunu gerekirse ekler).
    Yasa import edilemiyorsa (None, None) doner — panel sessizce bos kalir."""
    if _YASA not in sys.path:
        sys.path.insert(0, _YASA)
    try:
        import control.guidance.bbox_ibvs as bi
        import control.guidance.supervisor as sup
        return bi, sup
    except Exception:
        return None, None


def _cfg_nesnesi(modul_ad):
    bi, sup = _moduller()
    if bi is None:
        return None
    if modul_ad == "kopru":
        # dow_kopru.Cfg — cubuk cevirici. ⚠ YALNIZ dongude HER TIK okunan
        # alanlar buraya konabilir. KP_VH oyle (dow_kopru.py:592-593).
        try:
            from kopru import dow_kopru as dk
            return dk.Cfg
        except Exception:
            try:
                import dow_kopru as dk
                return dk.Cfg
            except Exception:
                return None
    if modul_ad == "gg":
        # GPS yasasi (istasyon geometrisi). ⚠ YALNIZ dongu icinde HER TIK
        # okunan alanlar buraya konabilir. RANGE_SET oyle (gps_guidance.py:567).
        # ISTASYON_ELEV_DEG DEGIL: dongu ONCESI bir kez cozuluyor (:391) ve
        # ELEV_DINAMIK kapali -> slider sessizce hicbir sey yapmaz, SAHTE A/B
        # uretir. Bu yuzden bilerek disarida birakildi.
        try:
            import control.guidance.gps_guidance as gg
            return gg.Cfg
        except Exception:
            return None
    return bi.Cfg if modul_ad == "ibvs" else sup.SupCfg


def _don(tur, ham):
    if tur == "bool":
        if isinstance(ham, str):
            return ham.strip().lower() in ("1", "true", "on", "evet", "acik")
        return bool(float(ham))
    return int(float(ham)) if tur == "int" else float(ham)


def hepsi():
    """Panel icin: [{anahtar, deger, tur, alt, ust, etiket, aciklama}, ...]"""
    out = []
    for anahtar, modul, tur, alt, ust, etiket, acik in OZELLIKLER:
        c = _cfg_nesnesi(modul)
        if c is None:
            continue
        d = getattr(c, anahtar, None)
        if d is None:
            continue
        out.append({"anahtar": anahtar, "modul": modul, "tur": tur,
                    "alt": alt, "ust": ust, "etiket": etiket,
                    "aciklama": acik,
                    "deger": bool(d) if tur == "bool" else
                             (int(d) if tur == "int" else round(float(d), 4))})
    return out


def ayarla(anahtar, deger):
    """Tek anahtari calisma aninda degistir. (yeni_deger, None) | (None, hata)"""
    o = _INDEKS.get(anahtar)
    if o is None:
        return None, "bilinmeyen anahtar: %s" % anahtar
    _, modul, tur, alt, ust, _, _ = o
    c = _cfg_nesnesi(modul)
    if c is None:
        return None, "yasa modulu yuklenemedi (kopru/gazebo_kaynak)"
    try:
        v = _don(tur, deger)
    except (TypeError, ValueError):
        return None, "gecersiz deger: %r" % (deger,)
    if tur != "bool":
        v = max(alt, min(ust, v))
    setattr(c, anahtar, v)
    return (bool(v) if tur == "bool" else v), None
