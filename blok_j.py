# ============================================================
# BLOCK J — GNSSDuzeltici (tek sinif, online, canliya hazir)
# Avci Drone — GNSS bozulma duzeltme gorevi
# ============================================================
# KULLANIM:
#   from blok_j import GNSSDuzeltici
#   filtre = GNSSDuzeltici()
#   for her_gelen_paket:
#       sonuc = filtre.guncelle(bozuk_x, bozuk_y, bozuk_z)
#       if sonuc:
#           x, y, z = sonuc   # duzeltilmis konum (cm)
#
# NOT: Donmus (tekrar eden) paketlerde None doner — normaldir.
# ============================================================
import numpy as np


class GNSSDuzeltici:
    """
    4 GNSS bozuklugunu tek sinifta halleder:
      Gurultu    -> Kalman yumusatir
      Sicrama    -> Innovation gating reddeder
      Veri kaybi -> Donma tespiti, None doner
      Gecikme    -> 2 sn ileri tahmin (Blok I)
    """

    def __init__(self, telafi_sn=2.0, dt=1.0,
                 R=100.0, Qp=2000.0, Qw=1e-5,
                 Rz=100.0, Qz=10.0, gate=200.0):

        self.telafi_sn = telafi_sn
        self.dt   = dt
        self.gate = gate

        self.Hxy  = np.array([[1,0,0,0,0],[0,1,0,0,0]], float)
        self.Rxy  = np.eye(2) * R**2
        self.Fz   = np.array([[1,dt],[0,1]])
        self.Hz   = np.array([[1,0]], float)
        self.Rz_m = np.array([[Rz]])
        self.Qz_m = np.eye(2) * Qz
        self.Qd   = np.diag([Qp, Qp, Qp, Qp, Qw])

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

    def guncelle(self, bozuk_x, bozuk_y, bozuk_z):
        """
        Yeni paket ver, duzeltilmis konum al.
        Doner: (x, y, z) cm  |  None
        """
        bx,by,bz = float(bozuk_x), float(bozuk_y), float(bozuk_z)
        self._adim += 1

        # Ilk paket (0,0,0): atla
        if self._adim == 1:
            self._son_bozuk = np.array([bx,by,bz])
            return None

        # Donma tespiti
        donmus = (self._son_bozuk is not None and
                  np.allclose([bx,by,bz], self._son_bozuk))
        self._son_bozuk = np.array([bx,by,bz])
        if donmus:
            return None

        # Baslangic: iki farkli olcum bekle
        if not self._baslandi:
            if self._ilk is None:
                self._ilk = np.array([bx,by,bz])
                return None
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

        # UPDATE XY
        yk = np.array([bx,by]) - self.Hxy @ self._x
        Sx = self.Hxy @ self._P @ self.Hxy.T + self.Rxy
        if yk @ np.linalg.inv(Sx) @ yk < self.gate**2:
            K = self._P @ self.Hxy.T @ np.linalg.inv(Sx)
            self._x = self._x + K @ yk
            self._P = (np.eye(5) - K @ self.Hxy) @ self._P

        # UPDATE Z
        yz  = np.array([bz]) - self.Hz @ self._z
        Sz  = self.Hz @ self._Pz @ self.Hz.T + self.Rz_m
        Kz  = self._Pz @ self.Hz.T @ np.linalg.inv(Sz)
        self._z  = self._z  + Kz @ yz
        self._Pz = (np.eye(2) - Kz @ self.Hz) @ self._Pz

        # BLOK I: gecikme telafisi
        f = self._ct(self._x, self.telafi_sn)
        return float(f[0]), float(f[1]), float(self._z[0]+self._z[1]*self.telafi_sn)


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    import re, pandas as pd

    DATA  = r"C:\Users\T3 Vakfı\Desktop\avci_drone\veri"
    DESEN = re.compile(r"X:(-?\d+\.?\d*)\s*\|\s*Y:(-?\d+\.?\d*)\s*\|\s*Z:(-?\d+\.?\d*)")

    def oku(yol):
        s=open(yol,encoding="utf-8").read().splitlines(); k=[]; i=0
        while i<len(s):
            if s[i].startswith("BİZE GELEN"):
                b=DESEN.search(s[i]); g=DESEN.search(s[i+1]) if i+1<len(s) else None
                if b and g:
                    k.append({"bx":float(b.group(1)),"by":float(b.group(2)),"bz":float(b.group(3)),
                               "gx":float(g.group(1)),"gy":float(g.group(2)),"gz":float(g.group(3))})
                i+=5
            else: i+=1
        df=pd.DataFrame(k)
        if abs(df.loc[0,"bx"])<1e-9 and abs(df.loc[0,"by"])<1e-9:
            df=df.iloc[1:].reset_index(drop=True)
        return df

    for ad,yol in [("GPS Verisi.txt",    f"{DATA}/GPS Verisi.txt"),
                   ("GPS Verisi (1).txt", f"{DATA}/GPS Verisi (1).txt")]:
        df=oku(yol)
        ham=np.sqrt(np.mean((df["bx"]-df["gx"])**2+
                             (df["by"]-df["gy"])**2+
                             (df["bz"]-df["gz"])**2))

        # Donmamis satirlarin gercek degerlerini al (eslesme icin)
        tekrar=(df["bx"].diff()==0)&(df["by"].diff()==0)&(df["bz"].diff()==0)
        u=df[~tekrar.fillna(False)].reset_index(drop=True)

        filtre=GNSSDuzeltici()
        tah=[]; u_idx=0
        for _,r in df.iterrows():
            s=filtre.guncelle(r["bx"],r["by"],r["bz"])
            if s is not None and u_idx < len(u):
                tah.append({"tx":s[0],"ty":s[1],"tz":s[2],
                            "gx":u.loc[u_idx,"gx"],
                            "gy":u.loc[u_idx,"gy"],
                            "gz":u.loc[u_idx,"gz"]})
                u_idx+=1

        res=pd.DataFrame(tah)
        rj=np.sqrt(np.mean((res["tx"]-res["gx"])**2+
                           (res["ty"]-res["gy"])**2+
                           (res["tz"]-res["gz"])**2))
        print(f"=== {ad} ===")
        print(f"  HAM RMSE    : {ham:6.0f} cm = {ham/100:.1f} m")
        print(f"  BLOK J RMSE : {rj:6.0f} cm = {rj/100:.1f} m"
              f"   <-- {100*(ham-rj)/ham:.0f}% iyilesme")
        print(f"  Saglam      : {np.all(np.isfinite(res[['tx','ty','tz']].values))}")
        print()

    print("Takim arkadasin icin:")
    print("  from blok_j import GNSSDuzeltici")
    print("  filtre = GNSSDuzeltici()")
    print("  x, y, z = filtre.guncelle(bozuk_x, bozuk_y, bozuk_z)")
