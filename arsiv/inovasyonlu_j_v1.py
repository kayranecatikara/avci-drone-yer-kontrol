# ============================================================
# INOVASYONLU J v1 — GNSSDuzeltici (online CT-EKF + fiziksel kisit)
# Avci Drone — GNSS bozulma duzeltme
# ============================================================
# NOT: Bu surum SADECE OLCUM/KIYAS icin tutuluyor (arayuzde sapma
#      gostermek icin). Guduum uretim filtresi v2'dir (inovasyonlu_j_v2.py).
#
# 5 GNSS bozulmasini tek sinifta cozer:
#   Gurultu     -> Kalman yumusatir
#   Sicrama     -> Innovation gating reddeder
#   Veri kaybi  -> Donma tespiti, None doner
#   Gecikme     -> 2 sn ileri tahmin
#   + Fiziksel  -> ileri tahmin Talon'un ucus zarfiyla sinirli
#                  (imkansiz hiz/donus tahmini engellenir)
# ============================================================
import numpy as np


class GNSSDuzeltici:

    def __init__(self, telafi_sn=2.0, dt=1.0,
                 R=100.0, Qp=2000.0, Qw=1e-5, Rz=100.0, Qz=10.0, gate=200.0,
                 w_max=0.4, hiz_max=3000.0):
        # filtre
        self.telafi_sn = telafi_sn
        self.dt   = dt
        self.gate = gate
        # fiziksel sinirlar (Talon ~22 m/s; guvenli ust sinir)
        self.w_max   = w_max         # rad/s  (max donus hizi)
        self.hiz_max = hiz_max       # cm/s   (max ucus hizi = 30 m/s)
        # sabitler
        self.Hxy  = np.array([[1,0,0,0,0],[0,1,0,0,0]], float)
        self.Rxy  = np.eye(2) * R**2
        self.Fz   = np.array([[1,dt],[0,1]])
        self.Hz   = np.array([[1,0]], float)
        self.Rz_m = np.array([[Rz]])
        self.Qz_m = np.eye(2) * Qz
        self.Qd   = np.diag([Qp, Qp, Qp, Qp, Qw])
        # durum
        self._x = self._P = self._z = self._Pz = None
        self._baslandi  = False
        self._ilk       = None
        self._son_bozuk = None
        self._adim      = 0

    # Coordinated-Turn hareket modeli
    def _ct(self, d, dt):
        px,py,vx,vy,w = d
        if abs(w) < 1e-6: w = 1e-6
        s,c = np.sin(w*dt), np.cos(w*dt)
        return np.array([px+(vx*s-vy*(1-c))/w,
                         py+(vx*(1-c)+vy*s)/w,
                         vx*c-vy*s, vx*s+vy*c, w])

    # sayisal Jacobian (EKF lineerizasyon)
    def _jac(self, x, dt, eps=1e-5):
        f0=self._ct(x,dt); F=np.eye(5)
        for j in range(5):
            xp=x.copy(); xp[j]+=eps
            F[:,j]=(self._ct(xp,dt)-f0)/eps
        return F

    # fiziksel kisit: durumu Talon'un ucus zarfina cek
    def _kisitla(self):
        if self.w_max is not None and abs(self._x[4]) > self.w_max:
            self._x[4] = float(np.clip(self._x[4], -self.w_max, self.w_max))
        if self.hiz_max is not None:
            hiz = np.hypot(self._x[2], self._x[3])
            if hiz > self.hiz_max:
                o = self.hiz_max / hiz
                self._x[2] *= o; self._x[3] *= o

    def guncelle(self, bozuk_x, bozuk_y, bozuk_z):
        bx,by,bz = float(bozuk_x), float(bozuk_y), float(bozuk_z)
        self._adim += 1

        # ilk paket
        if self._adim == 1:
            self._son_bozuk = np.array([bx,by,bz]); return None

        # donma tespiti (tekrar eden paket)
        if self._son_bozuk is not None and np.allclose([bx,by,bz], self._son_bozuk):
            self._son_bozuk = np.array([bx,by,bz]); return None
        self._son_bozuk = np.array([bx,by,bz])

        # baslangic: iki olcum bekle
        if not self._baslandi:
            if self._ilk is None:
                self._ilk = np.array([bx,by,bz]); return None
            self._x  = np.array([self._ilk[0], self._ilk[1],
                                  bx-self._ilk[0], by-self._ilk[1], 0.05])
            self._P  = np.eye(5)*1e6
            self._z  = np.array([self._ilk[2], 0.0])
            self._Pz = np.eye(2)*1e6
            self._baslandi = True

        # PREDICT
        xe = self._x.copy()
        self._x  = self._ct(xe, self.dt)
        F        = self._jac(xe, self.dt)
        self._P  = F @ self._P @ F.T + self.Qd
        self._z  = self.Fz @ self._z
        self._Pz = self.Fz @ self._Pz @ self.Fz.T + self.Qz_m

        # UPDATE XY (+ innovation gating)
        yk = np.array([bx,by]) - self.Hxy @ self._x
        Sx = self.Hxy @ self._P @ self.Hxy.T + self.Rxy
        if yk @ np.linalg.inv(Sx) @ yk < self.gate**2:
            K = self._P @ self.Hxy.T @ np.linalg.inv(Sx)
            self._x = self._x + K @ yk
            self._P = (np.eye(5) - K @ self.Hxy) @ self._P

        # UPDATE Z (irtifa, ayri lineer KF)
        yz = np.array([bz]) - self.Hz @ self._z
        Sz = self.Hz @ self._Pz @ self.Hz.T + self.Rz_m
        Kz = self._Pz @ self.Hz.T @ np.linalg.inv(Sz)
        self._z  = self._z  + Kz @ yz
        self._Pz = (np.eye(2) - Kz @ self.Hz) @ self._Pz

        # fiziksel kisit -> gecikme telafisi (2 sn ileri tahmin)
        self._kisitla()
        f = self._ct(self._x, self.telafi_sn)
        return float(f[0]), float(f[1]), float(self._z[0]+self._z[1]*self.telafi_sn)
