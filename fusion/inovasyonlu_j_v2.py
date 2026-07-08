# ============================================================
# INOVASYONLU J v2.1 — GNSSDuzeltici (CT-EKF + fiziksel kisit)
# ============================================================
# v2'den FARK: dropout_dt mekanizmasi TAMAMEN KALDIRILDI.
#
# NEDEN: Yarisma simulatoru (TalonGPSSpoof) gercek-zamanli ~50 Hz tiklarken
# GPS'i 1 Hz veriyor (bLimitUpdateRate). Yani filtre saniyede ~49 kez AYNI
# (rate-limit ile dondurulmus) paketi goruyor. v2'nin "donmus kareyi say"
# mantigi bu normal tekrarlari DROPOUT saniyordu -> her taze pakette
# dt_eff ~ 50s hesaplayip CT modelini 50 saniye ileri firlatip estimate'i
# yok ediyordu. (Onceki sentetik testim filtreyi dogrudan 1 Hz besledigi
# icin bu confound'u hic uretmemis ve hatayi gizlemisti.)
#
# KALAN (guvenli) v2 iyilestirmeleri:
#   [FIX-1] Rz birim tutarsizligi  -> Rz da std (Rz**2). Default 150cm.
#   [FIX-2] vz fiziksel kisit      -> SADECE imkansiz dikey hiz elenir. Tavan,
#                                    ucagin toplam hiz zarfina bagli: vz toplam
#                                    hizi gecemez, o yuzden 2500 cm/s (25 m/s) ~
#                                    hiz_max'a yakin. Gercek dik tirmanis/dalisi
#                                    KIRPMAZ; Rz-fix hayalet vz'yi zaten onler,
#                                    bu yalnizca son emniyet supabi. None=kapali.
#   [FIX-3] opsiyonel irtifa gate  -> default kapali.
#   [FIX-5] Joseph-form kovaryans  -> sayisal saglamlik (davranis ayni).
# Yatay tuning'de R,Qp,Qw,telafi DOKUNULMADI. dt 2026-07-08'de ADAPTIF: PREDICT
# sabit 1.0 yerine ardisik paketler arasi GERCEK zaman farkini ([0.05,0.5]s clamp,
# 5Hz'de ~0.2) kullanir; t verilmezse 1.0 fallback. gate ise 2026-07-08'de AMPIRIK
# olarak 200->35 dusuruldu (arac/j_gate_sweep.py: bu profilde normal innovation
# maha^2 bandi maks ~504; gate^2=1225 bu bandin ~2.4x ustu -> normali kabul eder,
# gercek >=35m SUREKSIZLIGI (jump) reddeder; gate<6 iraksama ucurumundan uzak).
# TEORIK ki-kare esigi (gate~3) burada CALISMAZ: S asiri-olcekli (maha^2 medyani
# 0.3 << 2DOF ~1.4) -> gate=3'te %99 red -> coast -> iraksama (~2400m). Donma
# tespiti v1'deki gibi: tekrar eden paket -> None (ZAMAN ILERLETILMEZ).
# ============================================================
import numpy as np


class GNSSDuzeltici:

    def __init__(self, telafi_sn=1.0, dt=1.0, dt_min=0.05, dt_max=0.5,
                 R=100.0, Qp=2000.0, Qw=1e-5, Rz=150.0, Qz=10.0, gate=35.0,  # gate: ampirik (bkz. dosya basi)
                 w_max=0.4, hiz_max=3000.0,
                 vz_max=2500.0, gate_z=None, joseph=True):   # vz_max: 25 m/s (ucak zarfi). None=kapali.
        self.telafi_sn = telafi_sn
        self.dt   = dt
        self.dt_min = dt_min       # ADAPTIF dt clamp alt (paket kaybinda absurd sicramayi onler)
        self.dt_max = dt_max       # ADAPTIF dt clamp ust
        self.gate = gate
        self.w_max   = w_max
        self.hiz_max = hiz_max
        self.vz_max  = vz_max
        self.gate_z  = gate_z
        self.joseph  = joseph
        self.Hxy  = np.array([[1,0,0,0,0],[0,1,0,0,0]], float)
        self.Rxy  = np.eye(2) * R**2
        self.Hz   = np.array([[1,0]], float)
        self.Rz_m = np.array([[Rz**2]])          # [FIX-1]
        self.Qz_m = np.eye(2) * Qz
        self.Qd   = np.diag([Qp, Qp, Qp, Qp, Qw])
        self._I5  = np.eye(5)
        self._x = self._P = self._z = self._Pz = None
        self._baslandi  = False
        self._ilk       = None
        self._son_bozuk = None
        self._son_t     = None     # son ILERLETEN paketin zaman damgasi (adaptif dt icin)
        self._adim      = 0
        self._diag      = None     # TESHIS (gozlemsel): son guncelle innovation/gate/w kaydi

    def _ct(self, d, dt):
        px,py,vx,vy,w = d
        if abs(w) < 1e-6: w = 1e-6
        s,c = np.sin(w*dt), np.cos(w*dt)
        return np.array([px+(vx*s-vy*(1-c))/w,
                         py+(vx*(1-c)+vy*s)/w,
                         vx*c-vy*s, vx*s+vy*c, w])

    def _jac(self, x, dt, eps=1e-5):
        f0=self._ct(x,dt); F=np.eye(5)
        for j in range(5):
            xp=x.copy(); xp[j]+=eps
            F[:,j]=(self._ct(xp,dt)-f0)/eps
        return F

    def _kisitla(self):
        if self.w_max is not None and abs(self._x[4]) > self.w_max:
            self._x[4] = float(np.clip(self._x[4], -self.w_max, self.w_max))
        if self.hiz_max is not None:
            hiz = np.hypot(self._x[2], self._x[3])
            if hiz > self.hiz_max:
                o = self.hiz_max / hiz
                self._x[2] *= o; self._x[3] *= o

    def _kisitla_z(self):                          # [FIX-2]
        if self.vz_max is not None:
            self._z[1] = float(np.clip(self._z[1], -self.vz_max, self.vz_max))

    def guncelle(self, bozuk_x, bozuk_y, bozuk_z, t=None):
        bx,by,bz = float(bozuk_x), float(bozuk_y), float(bozuk_z)
        self._adim += 1

        if self._adim == 1:
            self._son_bozuk = np.array([bx,by,bz]); self._son_t = t; return None

        if self._son_bozuk is not None and np.allclose([bx,by,bz], self._son_bozuk):
            self._son_bozuk = np.array([bx,by,bz]); return None   # v1 gibi: None, zaman ILERLETME
        self._son_bozuk = np.array([bx,by,bz])

        # ADAPTIF dt: ardisik ILERLETEN paketler arasi GERCEK zaman farki (wall-clock),
        # [dt_min,dt_max] clamp'li (paket kaybinda absurd sicrama olmasin). t verilmezse
        # sabit self.dt fallback (geriye uyumlu). LEAD ufku (telafi_sn) BUNDAN BAGIMSIZ.
        if t is not None and self._son_t is not None:
            dt = float(np.clip(t - self._son_t, self.dt_min, self.dt_max))
        else:
            dt = self.dt
        if t is not None:
            self._son_t = t

        if not self._baslandi:
            if self._ilk is None:
                self._ilk = np.array([bx,by,bz]); return None
            self._x  = np.array([self._ilk[0], self._ilk[1],
                                  (bx-self._ilk[0])/dt, (by-self._ilk[1])/dt, 0.05])  # hiz seed /dt
            self._P  = np.eye(5)*1e6
            self._z  = np.array([self._ilk[2], 0.0])
            self._Pz = np.eye(2)*1e6
            self._baslandi = True

        # PREDICT (ADAPTIF dt -- gercek paket araligi; z gecisi de ayni dt ile)
        Fz = np.array([[1.0, dt],[0.0, 1.0]])
        xe = self._x.copy()
        self._x  = self._ct(xe, dt)
        F        = self._jac(xe, dt)
        self._P  = F @ self._P @ F.T + self.Qd
        self._z  = Fz @ self._z
        self._Pz = Fz @ self._Pz @ Fz.T + self.Qz_m

        # UPDATE XY (+ gating) -- yatay AYNEN
        yk = np.array([bx,by]) - self.Hxy @ self._x
        Sx = self.Hxy @ self._P @ self.Hxy.T + self.Rxy
        Sx_inv = np.linalg.inv(Sx)
        _maha2 = float(yk @ Sx_inv @ yk)                   # TESHIS (gozlemsel; MANTIK DEGISMEZ)
        self._diag = {"yk_cm": float(np.hypot(yk[0], yk[1])), "maha2": _maha2,
                      "gate2": float(self.gate ** 2), "gecti": bool(_maha2 < self.gate ** 2),
                      "w": float(self._x[4]), "dt": float(dt)}
        # GATING (innovation-tabanli): maha^2 < gate^2 ise ORTALA (update). ASILIRSA (>=) XY
        # update ATLANIR -> state PREDICT'te kalir, OLCUME ATLAMAZ; sonraki tutarli olcum
        # yeniden oranlar. gate 2026-07-08 ampirik 200->35 (dosya basi + arac/j_gate_sweep.py).
        if _maha2 < self.gate**2:
            K = self._P @ self.Hxy.T @ Sx_inv
            self._x = self._x + K @ yk
            if self.joseph:
                A = self._I5 - K @ self.Hxy
                self._P = A @ self._P @ A.T + K @ self.Rxy @ K.T
            else:
                self._P = (self._I5 - K @ self.Hxy) @ self._P

        # UPDATE Z (+ opsiyonel gate + Joseph)
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

        self._kisitla()
        self._kisitla_z()                           # [FIX-2]
        f = self._ct(self._x, self.telafi_sn)
        return float(f[0]), float(f[1]), float(self._z[0]+self._z[1]*self.telafi_sn)

    # --------------------------------------------------------------
    #  GUDUUM ICIN GUNCEL HEDEF DURUMU (konum + HIZ)
    #  guncelle() telafi_sn kadar ONE tasinmis konum dondurur; ongorulu
    #  (lead) guduum kendi ileri-tahminini urettiginden BURADA telafisiz
    #  GUNCEL kestirim verilir -> cift-lead olmaz. Birimler cm ve cm/s.
    #  Filtre daha isinmadiysa None.
    # --------------------------------------------------------------
    def durum_guduum(self):
        if not self._baslandi:
            return None
        return {"pos": (float(self._x[0]), float(self._x[1]), float(self._z[0])),
                "vel": (float(self._x[2]), float(self._x[3]), float(self._z[1])),
                "w": float(self._x[4])}
