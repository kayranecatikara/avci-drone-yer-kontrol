# ============================================================
# GNSSDuzeltici v2.4 — v2.1 cekirdek (telafi=2) + uyarlamali lead
# ============================================================
# v2.2'ye gore tek yapisal ekleme: UYARLAMALI LEAD.
#
# TESHIS: Asil hata manevrada. Sabit-donus (CT) modeli + uzun ileri tahmin
# (telafi), sert donuste donus acisini (telafi*w) cok ileri firlatip asiyor.
# Ama duz ucusta uzun lead gecikmeyi kapatmak icin GEREKLI.
#
# COZUM: lead'i donus hizina gore otomatik kisalt. Ileri tahminde
# ekstrapole edilen donus acisini (telafi*|w|) bir tavanla (lead_aci_max)
# sinirla:  lead_eff = min(telafi_sn, lead_aci_max / |w|)
#   - duz ucus (w~0)  -> lead_eff = telafi_sn (tam lead, gecikme kapanir)
#   - sert donus      -> lead_eff = lead_aci_max/|w| (kisalir, asma onlenir)
# Boylece BASE telafi'yi gercek gecikmeye (3s) esitleyip duz ucus kazancini
# alirken, manevradaki asmayi tavan engelliyor. Ikisi cakismIyor.
#
# v2.2'den devralinanlar: Rz-fix, vz-clamp (25 m/s), Joseph, telafi=3.0.
# Arayuz/birim/numpy-only/donma-isinma AYNEN korundu.
# Yeni parametreler: adaptif_lead (toggle), lead_aci_max (rad).
# ============================================================
import numpy as np


class GNSSDuzeltici:

    def __init__(self, telafi_sn=2.0, dt=1.0,
                 R=100.0, Qp=2000.0, Qw=1e-5, Rz=150.0, Qz=10.0, gate=200.0,
                 w_max=0.4, hiz_max=3000.0,
                 vz_max=2500.0, gate_z=None, joseph=True,
                 adaptif_lead=True, lead_aci_max=0.45):
        # lead_aci_max (rad): ~0.45 = 26 derece tavan. 0.45 en guvenli (duz ucusta
        # sifir kayip); 0.30 manevrada biraz daha keser. None = uyarlamali lead kapali.
        self.telafi_sn = telafi_sn
        self.dt   = dt
        self.gate = gate
        self.w_max   = w_max
        self.hiz_max = hiz_max
        self.vz_max  = vz_max
        self.gate_z  = gate_z
        self.joseph  = joseph
        self.adaptif_lead = adaptif_lead
        self.lead_aci_max = lead_aci_max
        self.Hxy  = np.array([[1,0,0,0,0],[0,1,0,0,0]], float)
        self.Rxy  = np.eye(2) * R**2
        self.Fz   = np.array([[1,dt],[0,1]])
        self.Hz   = np.array([[1,0]], float)
        self.Rz_m = np.array([[Rz**2]])
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

    def _lead_eff(self):
        # UYARLAMALI LEAD: donus acisi tavani
        if not self.adaptif_lead or self.lead_aci_max is None:
            return self.telafi_sn
        w = abs(self._x[4])
        return min(self.telafi_sn, self.lead_aci_max / (w + 1e-6))

    def _kisitla(self):
        if self.w_max is not None and abs(self._x[4]) > self.w_max:
            self._x[4] = float(np.clip(self._x[4], -self.w_max, self.w_max))
        if self.hiz_max is not None:
            hiz = np.hypot(self._x[2], self._x[3])
            if hiz > self.hiz_max:
                o = self.hiz_max / hiz
                self._x[2] *= o; self._x[3] *= o

    def _kisitla_z(self):
        if self.vz_max is not None:
            self._z[1] = float(np.clip(self._z[1], -self.vz_max, self.vz_max))

    def guncelle(self, bx, by, bz):
        bx,by,bz = float(bx), float(by), float(bz)
        self._adim += 1
        if self._adim == 1:
            self._son_bozuk = np.array([bx,by,bz]); return None
        if self._son_bozuk is not None and np.allclose([bx,by,bz], self._son_bozuk):
            self._son_bozuk = np.array([bx,by,bz]); return None
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
        # PREDICT
        xe = self._x.copy()
        self._x  = self._ct(xe, self.dt)
        F        = self._jac(xe, self.dt)
        self._P  = F @ self._P @ F.T + self.Qd
        self._z  = self.Fz @ self._z
        self._Pz = self.Fz @ self._Pz @ self.Fz.T + self.Qz_m
        # UPDATE XY (+ gating)
        yk = np.array([bx,by]) - self.Hxy @ self._x
        Sx = self.Hxy @ self._P @ self.Hxy.T + self.Rxy
        Sxi = np.linalg.inv(Sx)
        if yk @ Sxi @ yk < self.gate**2:
            K = self._P @ self.Hxy.T @ Sxi
            self._x = self._x + K @ yk
            if self.joseph:
                A = self._I5 - K @ self.Hxy
                self._P = A @ self._P @ A.T + K @ self.Rxy @ K.T
            else:
                self._P = (self._I5 - K @ self.Hxy) @ self._P
        # UPDATE Z
        yz = np.array([bz]) - self.Hz @ self._z
        Sz = self.Hz @ self._Pz @ self.Hz.T + self.Rz_m
        Szi = np.linalg.inv(Sz)
        ok = True if self.gate_z is None else float(yz @ Szi @ yz) < self.gate_z**2
        if ok:
            Kz = self._Pz @ self.Hz.T @ Szi
            self._z = self._z + Kz @ yz
            if self.joseph:
                Az = np.eye(2) - Kz @ self.Hz
                self._Pz = Az @ self._Pz @ Az.T + Kz @ self.Rz_m @ Kz.T
            else:
                self._Pz = (np.eye(2) - Kz @ self.Hz) @ self._Pz
        self._kisitla(); self._kisitla_z()
        tau = self._lead_eff()                       # <-- uyarlamali lead
        f = self._ct(self._x, tau)
        return float(f[0]), float(f[1]), float(self._z[0] + self._z[1]*tau)
