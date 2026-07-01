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
# Yatay tuning'e (R,Qp,Qw,gate,telafi,dt) DOKUNULMADI. Donma tespiti
# v1'deki gibi: tekrar eden paket -> None (ZAMAN ILERLETILMEZ).
# ============================================================
import numpy as np


class GNSSDuzeltici:

    def __init__(self, telafi_sn=2.0, dt=1.0,
                 R=100.0, Qp=2000.0, Qw=1e-5, Rz=150.0, Qz=10.0, gate=200.0,
                 w_max=0.4, hiz_max=3000.0,
                 vz_max=2500.0, gate_z=None, joseph=True):   # vz_max: 25 m/s (ucak zarfi). None=kapali.
        self.telafi_sn = telafi_sn
        self.dt   = dt
        self.gate = gate
        self.w_max   = w_max
        self.hiz_max = hiz_max
        self.vz_max  = vz_max
        self.gate_z  = gate_z
        self.joseph  = joseph
        self.Hxy  = np.array([[1,0,0,0,0],[0,1,0,0,0]], float)
        self.Rxy  = np.eye(2) * R**2
        self.Fz   = np.array([[1,dt],[0,1]])
        self.Hz   = np.array([[1,0]], float)
        self.Rz_m = np.array([[Rz**2]])          # [FIX-1]
        self.Qz_m = np.eye(2) * Qz
        self.Qd   = np.diag([Qp, Qp, Qp, Qp, Qw])
        self._I5  = np.eye(5)
        self._x = self._P = self._z = self._Pz = None
        self._baslandi  = False
        self._ilk       = None
        self._son_bozuk = None
        self._adim      = 0

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

    def guncelle(self, bozuk_x, bozuk_y, bozuk_z):
        bx,by,bz = float(bozuk_x), float(bozuk_y), float(bozuk_z)
        self._adim += 1

        if self._adim == 1:
            self._son_bozuk = np.array([bx,by,bz]); return None

        if self._son_bozuk is not None and np.allclose([bx,by,bz], self._son_bozuk):
            self._son_bozuk = np.array([bx,by,bz]); return None   # v1 gibi: None, zaman ILERLETME
        self._son_bozuk = np.array([bx,by,bz])

        if not self._baslandi:
            if self._ilk is None:
                self._ilk = np.array([bx,by,bz]); return None
            self._x  = np.array([self._ilk[0], self._ilk[1],
                                  bx-self._ilk[0], by-self._ilk[1], 0.05])
            self._P  = np.eye(5)*1e6
            self._z  = np.array([self._ilk[2], 0.0])
            self._Pz = np.eye(2)*1e6
            self._baslandi = True

        # PREDICT (sabit dt -- v1 ile ayni)
        xe = self._x.copy()
        self._x  = self._ct(xe, self.dt)
        F        = self._jac(xe, self.dt)
        self._P  = F @ self._P @ F.T + self.Qd
        self._z  = self.Fz @ self._z
        self._Pz = self.Fz @ self._Pz @ self.Fz.T + self.Qz_m

        # UPDATE XY (+ gating) -- yatay AYNEN
        yk = np.array([bx,by]) - self.Hxy @ self._x
        Sx = self.Hxy @ self._P @ self.Hxy.T + self.Rxy
        Sx_inv = np.linalg.inv(Sx)
        if yk @ Sx_inv @ yk < self.gate**2:
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
