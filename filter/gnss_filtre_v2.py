# ============================================================
# GNSS DUZELTICI v2 — POZISYON-TABANLI + ADAPTIF SUREC GURULTUSU
# ------------------------------------------------------------
# Hedefin jammer'la bozulmus GPS'ini (konum gurultusu, ani sicrama,
# veri kesintisi, gecikme) temizler. YALNIZCA bozuk GPS kullanir:
# SDK'dan get_target_location() -> (x, y, z). Hedef yaw/attitude
# KULLANMAZ (Bilgilendirme Dok. Bolum 2: hedef telemetrisi lat/lon/
# alt/hiz; attitude yok -> finalle birebir ortusur).
#
# MIMARI:
#  - CT-EKF cekirdek (durum: x, y, vx, vy, omega) -> manevra ongorusu
#    (coordinated-turn EKF: hedefin sabit donus hiziyla dondugunu
#     varsayip donusu ongorebilen genisletilmis Kalman filtresi)
#  - Fiziksel zarf (w_max/speed_max/vz_max): kestirim, ucagin kinematik
#    sinirlari disina cikamaz
#  - Mahalanobis kapilari (gate_xy/gate_z): jammer sicramalarini
#    istatistiksel olarak reddeder (innovation'in beklenen belirsizlige
#    orani; ki-kare testi)
#  - Kacis mekanizmasi: kapi ust uste reddederse P sisirilir -> jammer
#    yeni rejime gecerse filtre ~2-3 s'de yeniden kilitlenir (divergence
#    onleyici)
#  - ADAPTIF dt: iki taze paket arasi GERCEK sure perf_counter ile
#    olculur -> cagri/dongu hizindan bagimsiz
#  - DEAD RECKONING: kesikte son hiz+donusle ileri ekstrapolasyon
#    (dr_max_s ile sinirli)
#  - LEAD (lead_s): cikti, GPS gecikmesini kapatmak icin ileri
#    tasinir; olculen gecikme ~1.13 s oldugundan varsayilan 1.0.
#
# YENI: adaptive_q -> son innovation'lar (olcum-tahmin farki) buyudugunde
# omega surec gurultusu Qw gecici yukselir; boylece omega manevrada hizli
# doner, duz ucusta sakin kalir (IMM'in hafif muadili). Dropout spike'ini
# COZMEZ (o anlarda olcum yok). Duz+veri-olan manevrada ~%5-15 iyilesme.
# AYAR NOTU: Qw=1e-2 (omega surec gurultusu; 1e-3 yerine, omega'nin
# manevrada biraz daha hizli donmesine izin verir -> ~%38 daha iyi).
# Birimler: cm, cm/s, s.  Kullanim: GNSSFilterV2().update(x, y, z)
# ============================================================
import numpy as np


class GNSSFilterV2:
    """Hedefin jammer'la bozulmus GNSS'ini temizleyen CT-EKF.

    DURUM VEKTORU (5 eleman, XY kanali):  [px, py, vx, vy, omega]
        px, py  cm      hedefin konumu
        vx, vy  cm/s    hedefin hizi   <- ISTASYON YASASININ ILERI BESLEDIGI TERIM
        omega   rad/s   donus hizi     <- manevrayi ONGORMEYI saglayan eleman
    Z kanali AYRI ve daha basit tutulur (2 eleman: [z, vz], cm ve cm/s):
    irtifa manevrasi yatay donus kadar yapili degildir, ayni modele sokmak
    gereksiz baglasim uretirdi.

    KOD ICINDEKI [D1]..[D5] ETIKETLERININ ANLAMI
        [D1] gercek Mahalanobis kapisi — sicramayi sabit esikle degil,
             filtrenin O ANKI belirsizligine gore reddeder
        [D2] kacis mekanizmasi — kapi ust uste reddederse P sisirilir, boylece
             jammer YENI bir rejime gecerse filtre orada kilitlenebilir
        [D3] ilk iki paket arasindaki GERCEK sureden hiz kestirimi (soguk baslangic)
        [D4] fiziksel zarf — kestirim ucagin kinematik sinirlari disina cikamaz
        [D5] olu-hesap (dropout) + adaptif surec gurultusu

    ⛔ CIKISI YALNIZ GPS FAZINDA GUDUME GIRER. Gorsel temas kurulduktan sonra
      hedefe ait hicbir GNSS turevi komuta giremez (yarisma kurali); o
      fazlarda filtre yalnizca SICAK KALSIN diye beslenir.
    """

    def __init__(self, lead_s=1.0, dt=0.2,
                 R=50.0, Qp=500.0, Qw=1e-2, Rz=150.0, Qz=10.0,
                 gate_xy=5.0, escape_thresh=12, escape_gain=100.0,  # [D1][D2]
                 w_max=1.0, speed_max=3000.0,                       # [D4]
                 vz_max=2500.0, gate_z=5.0, joseph=True,
                 dr_max_s=2.5,
                 adaptive_q=True, q_ref=2.0, q_boost_max=25.0, q_ema=0.85):  # [D5]
        """Filtre ayarlari. BIRIMLER: cm, cm/s, s, rad/s.

        ZAMANLAMA
          lead_s    s;   cikis bu kadar ILERI tasinir -> GNSS gecikmesini kapatir.
                         Olculen gecikme ~1.13 s; kapatilmazsa 18 m/s'de ~20 m
                         sabit hata kalir (hata = hiz x gecikme).
          dt        s;   nominal paket periyodu. Surec gurultusu bu periyoda gore
                         olceklenir ve ilk tikte gercek dt bilinmedigi icin
                         kullanilir. Gercek dt her adimda perf_counter ile OLCULUR.
          dr_max_s  s;   [D5] veri kesildiginde olu-hesapla en fazla bu kadar ileri
                         gidilir. Sonrasinda kestirim DONDURULUR: uzun kesintide
                         ekstrapolasyon hizla anlamsizlasir.

        OLCUM VE SUREC GURULTUSU (Kalman'in "kime ne kadar guveneyim" ayari)
          R    cm;      XY olcum gurultusunun standart sapmasi (Rxy = I*R^2).
                        BUYUTMEK = "GPS'e daha az guven, modele daha cok"
          Rz   cm;      Z olcum gurultusunun standart sapmasi
          Qp   varyans; [D5] konum/hiz surec gurultusu (cm^2 ve (cm/s)^2),
                        NOMINAL BIR ADIM basina. Buyutmek filtreyi cevikleştirir
                        ama gurultuyu de gecirir.
          Qw   varyans; omega surec gurultusu ((rad/s)^2), nominal adim basina.
                        1e-3 yerine 1e-2 secildi: omega'nin manevrada daha hizli
                        donmesine izin verir (~%38 iyilesme).
          Qz   varyans; Z kanalinin surec gurultusu

        KAPI VE KACIS
          gate_xy        sigma (birimsiz); [D1] Mahalanobis kapisi. Olcum,
                         beklenen belirsizligin bu kadar katindan uzaksa
                         REDDEDILIR (d^2 < gate_xy^2 testi = ki-kare).
          gate_z         sigma; Z kanali icin ayni kapi
          escape_thresh  adet; [D2] ust uste kac ret sonra kacis tetiklenir.
                         Tek bir jammer sicramasi 1-2 ret uretir ve bu SAGLIKLI
                         calismadir; esik o yuzden yuksektir.
          escape_gain    carpan (birimsiz); kacista P bu kadar sisirilir. Belirsizlik
                         buyuyunce kapi genisler ve filtre yeni rejime kilitlenir
                         (~2-3 s). Bu bir DIVERGENCE onleyicidir.
          joseph         bool; kovaryans guncellemesinin Joseph bicimi. Sayisal
                         olarak kararlidir: P'yi simetrik ve pozitif tutar.

        FIZIKSEL ZARF [D4] — kestirim ucagin yapabildiginden fazlasini soyleyemez
          w_max      rad/s; azami donus hizi
          speed_max  cm/s;  azami yatay hiz (3000 = 30 m/s)
          vz_max     cm/s;  azami dikey hiz (2500 = 25 m/s)

        ADAPTIF SUREC GURULTUSU [D5] — IMM'in hafif muadili
          adaptive_q   bool;      son innovation'lar buyudugunde Qw gecici olarak
                                  yukseltilsin mi? Boylece omega manevrada hizli
                                  doner, duz ucusta sakin kalir.
          q_ref        d^2;       "normal" sayilan Mahalanobis uzakligi. Artis
                                  carpani = d2_ema / q_ref.
          q_boost_max  carpan;    Qw'ye uygulanabilecek azami artis
          q_ema        0..1;      d^2 yumusatmasinin EMA katsayisi (buyuk = sakin)
        """
        self.lead_s = lead_s
        self.dt   = dt
        self.gate_xy = gate_xy
        self.escape_thresh   = escape_thresh
        self.escape_gain = escape_gain
        self.w_max   = w_max
        self.speed_max = speed_max
        self.vz_max  = vz_max
        self.gate_z  = gate_z
        self.joseph  = joseph
        self.dr_max_s = dr_max_s
        self.Hxy  = np.array([[1,0,0,0,0],[0,1,0,0,0]], float)
        self.Rxy  = np.eye(2) * R**2
        self.Hz   = np.array([[1,0]], float)
        self.Rz_m = np.array([[Rz**2]])
        self.Qz_m = np.eye(2) * Qz
        self.Qd   = np.diag([Qp, Qp, Qp, Qp, Qw])
        self._I5  = np.eye(5)
        self._x = self._P = self._z = self._Pz = None
        self._started  = False
        self._first       = None
        self._first_t     = None  # [D3]
        self._last_noisy = None
        self._steps      = 0
        self._last_time = None
        self._t_update  = None
        self._reject_count = 0  # adet; [D2] UST USTE ret sayaci (kabul gelince sifirlanir)
        # Teshis alanlari — istege bagli okunur, guduume GIRMEZ.
        self.last_d2 = None; self.last_accept = None
        self.adaptive_q = adaptive_q; self.q_ref = q_ref
        self.q_boost_max = q_boost_max; self.q_ema = q_ema
        self._d2_ema = q_ref

    def _ct(self, d, dt):
        """COORDINATED TURN gecis modeli: durumu dt saniye ileri tasir.

        d  : [px, py, vx, vy, omega] — cm, cm/s, rad/s
        dt : s; ileri gidilecek sure (negatif olamaz)
        -> ayni bicimde yeni durum

        Varsayim: hedef SABIT donus hiziyla (omega) daire yayi cizer. Duz
        ucus bu modelin omega -> 0 ozel halidir, o yuzden ayri bir model
        gerekmez. Sifira bolunmeyi onlemek icin omega taban degerle korunur.
        """
        px,py,vx,vy,w = d
        if abs(w) < 1e-6: w = 1e-6
        s,c = np.sin(w*dt), np.cos(w*dt)
        return np.array([px+(vx*s-vy*(1-c))/w,
                         py+(vx*(1-c)+vy*s)/w,
                         vx*c-vy*s, vx*s+vy*c, w])

    def _jac(self, x, dt, eps=1e-5):
        """_ct'nin Jacobian'i (5x5) — SAYISAL turevle, ileri fark.

        EKF kovaryansi dogrusal bir gecis matrisi ister; CT modeli dogrusal
        DEGILDIR (omega ile trigonometrik). Analitik turev yerine sayisal
        turev secildi: model degistirilirse bu satirin guncellenmesi gerekmez.
        eps : sayisal turevin adimi.
        """
        f0=self._ct(x,dt); F=np.eye(5)
        for j in range(5):
            xp=x.copy(); xp[j]+=eps
            F[:,j]=(self._ct(xp,dt)-f0)/eps
        return F

    def _constrain(self):
        """[D4] XY durumunu fiziksel zarfa kirpar (donus hizi ve yatay hiz).

        Kestirim, ucagin YAPABILDIGINDEN fazlasini soyleyemez. Bu kirpma
        jammer sicramasinin filtreye sizdirdigi anlamsiz hizlarin guduume
        gecmesini engelleyen SON savunmadir.
        """
        if self.w_max is not None and abs(self._x[4]) > self.w_max:
            self._x[4] = float(np.clip(self._x[4], -self.w_max, self.w_max))
        if self.speed_max is not None:
            speed = np.hypot(self._x[2], self._x[3])
            if speed > self.speed_max:
                o = self.speed_max / speed
                self._x[2] *= o; self._x[3] *= o

    def _constrain_z(self):
        """[D4] Z kanalinin dikey hizini fiziksel zarfa kirpar."""
        if self.vz_max is not None:
            self._z[1] = float(np.clip(self._z[1], -self.vz_max, self.vz_max))

    def update(self, noisy_x, noisy_y, noisy_z, now=None):
        """HAM (bozuk) GNSS olcumunu isler ve TEMIZ hedef konumunu dondurur.

        noisy_x/y/z : cm; SDK'nin get_target_location() ciktisi
        now         : s (perf_counter); verilmezse simdi. Gercek dt bundan olculur.
        -> (x, y, z) cm — GECIKMESI TELAFI EDILMIS (lead_s kadar ileri tasinmis)
           konum, ya da None (filtre henuz isinmadi: ilk iki paket gerekir)

        Adimlar: paket tekrari mi? -> olu-hesap [D5] | soguk baslangic [D3] |
        PREDICT (adaptif dt + adaptif Qw) | XY UPDATE (kapi [D1] + kacis [D2]) |
        Z UPDATE | zarf kirpmasi [D4] | lead.

        ⚠ AYNI PAKET TEKRAR GELIRSE olcum guncellemesi YAPILMAZ; bunun yerine
          son durumdan olu-hesapla ileri gidilir. Bu sayede filtre 50 Hz'de
          beslenebilir (`GPSCfg.FILTER_EVERY_TICK`) ve yasa 5 Hz'lik bir
          MERDIVEN yerine surekli bir hedef konumu gorur.
        """
        import time as _t
        if now is None: now = _t.perf_counter()
        bx,by,bz = float(noisy_x), float(noisy_y), float(noisy_z)
        self._steps += 1

        if self._steps == 1:
            self._last_noisy = np.array([bx,by,bz]); return None

        if self._last_noisy is not None and np.allclose([bx,by,bz], self._last_noisy):
            self._last_noisy = np.array([bx,by,bz])
            # DEAD RECKONING: son hiz+donusle ileri git; sure sinirli [D5]
            if getattr(self,'_started',False) and self._t_update is not None:
                elapsed  = min(self.dr_max_s, max(0.0, now - self._t_update))
                fr = self._ct(self._x, elapsed + self.lead_s)
                z_fwd = self._z[0] + self._z[1]*elapsed  # Z: lead yok [D5]
                return float(fr[0]), float(fr[1]), float(z_fwd)
            return None
        self._last_noisy = np.array([bx,by,bz])

        if not self._started:
            if self._first is None:
                self._first = np.array([bx,by,bz]); self._first_t = now; return None
            # [D3] ilk iki paket arasi GERCEK sureden hiz kestir
            dt0 = (max(0.05, min(1.0, now - self._first_t))
                   if self._first_t else self.dt)
            self._x  = np.array([self._first[0], self._first[1],
                                 (bx-self._first[0])/dt0,
                                 (by-self._first[1])/dt0, 0.05])
            self._P  = np.eye(5)*1e6
            self._z  = np.array([self._first[2], 0.0])
            self._Pz = np.eye(2)*1e6
            self._started = True

        # PREDICT (ADAPTIF dt)
        if self._last_time is None:
            dt_eff = self.dt
        else:
            dt_eff = min(3.0, max(0.02, now - self._last_time))
        self._last_time = now
        scale = dt_eff / self.dt
        Fz_eff = np.array([[1, dt_eff],[0, 1]])
        xe = self._x.copy()
        self._x  = self._ct(xe, dt_eff)
        F        = self._jac(xe, dt_eff)
        if self.adaptive_q:
            qboost = min(self.q_boost_max, max(1.0, self._d2_ema / self.q_ref))
            Qd_eff = self.Qd.copy(); Qd_eff[4,4] *= qboost
        else:
            Qd_eff = self.Qd
        self._P  = F @ self._P @ F.T + Qd_eff * scale
        self._z  = Fz_eff @ self._z
        self._Pz = Fz_eff @ self._Pz @ Fz_eff.T + self.Qz_m * scale

        # UPDATE XY: gercek Mahalanobis kapisi [D1] + kacis [D2]
        yk = np.array([bx,by]) - self.Hxy @ self._x
        Sx = self.Hxy @ self._P @ self.Hxy.T + self.Rxy
        Sx_inv = np.linalg.inv(Sx)
        d2 = float(yk @ Sx_inv @ yk)
        self.last_d2 = d2
        self._d2_ema = self.q_ema*self._d2_ema + (1.0-self.q_ema)*d2
        accept = (self.gate_xy is None) or (d2 < self.gate_xy**2)
        if not accept:
            self._reject_count += 1
            if self._reject_count >= self.escape_thresh:  # [D2] kacis:
                self._P = self._P * self.escape_gain      # belirsizligi sisir,
                self._reject_count = 0                    # yeni rejime kilitlen
                Sx = self.Hxy @ self._P @ self.Hxy.T + self.Rxy
                Sx_inv = np.linalg.inv(Sx)
                accept = True
        else:
            self._reject_count = 0
        self.last_accept = accept
        if accept:
            K = self._P @ self.Hxy.T @ Sx_inv
            self._x = self._x + K @ yk
            if self.joseph:
                A = self._I5 - K @ self.Hxy
                self._P = A @ self._P @ A.T + K @ self.Rxy @ K.T
            else:
                self._P = (self._I5 - K @ self.Hxy) @ self._P

        # UPDATE Z (+ gate + Joseph) — degismedi
        yz = np.array([bz]) - self.Hz @ self._z
        Sz = self.Hz @ self._Pz @ self.Hz.T + self.Rz_m
        Sz_inv = np.linalg.inv(Sz)
        z_ok = True
        if self.gate_z is not None:
            z_ok = float(yz @ Sz_inv @ yz) < self.gate_z**2
        if z_ok:
            Kz = self._Pz @ self.Hz.T @ Sz_inv
            self._z = self._z + Kz @ yz
            if self.joseph:
                Az = np.eye(2) - Kz @ self.Hz
                self._Pz = Az @ self._Pz @ Az.T + Kz @ self.Rz_m @ Kz.T
            else:
                self._Pz = (np.eye(2) - Kz @ self.Hz) @ self._Pz

        self._constrain()
        self._constrain_z()
        self._t_update = now
        f = self._ct(self._x, self.lead_s)
        return float(f[0]), float(f[1]), float(self._z[0])

    # ==================================================================
    #  PROJE ARAYUZU (control/gps_approach.py'nin bekledigi sozlesme)
    #  Algoritmaya dokunmaz; yalnizca mevcut EKF durumunu disari acar.
    # ==================================================================
    def guidance_state(self):
        """{"pos": (x,y,z) cm, "vel": (vx,vy,vz) cm/s} — isinmadiysa None.

        ⭐ ISTASYON YASASI HIZI BURADAN ALIR VE ILERI BESLER. Ileri besleme
          OLMADAN saf P kontrolcu hareketli hedefi ASLA yakalayamaz: denge
          e = V/Kp'de kurulur (Kp=0.9, V=18 m/s -> 20 m KALICI hata; olculdu,
          ileri beslemesiz surumde menzil 100-255 m salindi). Yani bu islev
          suslu bir tani kanali degil, GUDUMUN ZORUNLU girdisidir.

        Hiz dogrudan CT-EKF durumundan gelir (x[2], x[3] = vx, vy; z[1] = vz).
        Ustune AYRICA turev/EMA konmaz — filtre zaten yumusatiyor; ikinci bir
        yumusatma katmani hem gecikme ekler hem manevrayi korlestirir.

        ⚠ pos, telafi (lead) UYGULANMAMIS anlik kestirimdir. update()'nin
          dondurdugu konum ise lead_s kadar ILERI tasinmistir; ikisini
          karistirmayin (birini digerinin yerine kullanmak ~1 s x hedef hizi
          kadar, yani 18 m/s'de ~18 m sabit hata verir).
        """
        if not self._started or self._x is None or self._z is None:
            return None
        return {"pos": (float(self._x[0]), float(self._x[1]), float(self._z[0])),
                "vel": (float(self._x[2]), float(self._x[3]), float(self._z[1]))}

    def diag(self):
        """Kapi/kacis teshisi — YALNIZ gosterge, guduume GIRMEZ.

        d2            : son olcumun Mahalanobis uzakligi (KARE, birimsiz).
                        gate_xy^2 uzeri = jammer sicramasi sayilip REDDEDILDI.
        accept        : son olcum filtreye alindi mi (True/False)
        ret           : adet; UST USTE ret sayaci
        gate          : sigma; yururlukteki XY kapi esigi
        escape_thresh : adet; kacisin tetiklenecegi ret sayisi
        started       : filtre isindi mi (False iken update() None doner)

        ⭐ `GPSTracker._filter_lost()` bu ciktiyi okur: gorevler arasi SICAK
          tasinacak filtrenin kilidini gercekten kaybedip kaybetmedigine
          `ret` degeri uzerinden karar verir.
        """
        return {"d2": self.last_d2, "accept": self.last_accept,
                "ret": self._reject_count, "gate": self.gate_xy,
                "escape_thresh": self.escape_thresh, "started": bool(self._started)}
