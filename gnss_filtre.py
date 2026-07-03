# ============================================================
# GNSS FILTRE — bozuk GNSS temizleme + gecikme telafisi
# ============================================================
# Sifirdan temiz implementasyon. Yontem ayni (CT-EKF), kod yeni.
#
# PROBLEM
#   Simulatorun verdigi hedef konumu bozuk: ~1 sn gecikme (FLAG_DELAY),
#   ani sicramalar, gurultu. Logda (gps_analiz/gps_log_canli.json) gecikme
#   iki bagimsiz yontemle olculdu: cross-correlation ve sapma~hiz
#   regresyonu, ikisi de tau = 0.9-1.1 sn, zamanla sabit. Gecikme tek
#   skalerdir (paketin tamami gecikir); eksen basina ayri tau overfit olur.
#
# COZUM (iki katman)
#   1) Kestirim: EKF gecikmeli olcumleri isler -> filtre durumu
#      "gecikme_sn once"nin en iyi kestirimidir.
#   2) Telafi: disari verilen kestirim, ayni hareket modeliyle gecikme_sn
#      ileri tasinir -> "SIMDI"nin kestirimi. Yeni sabit yok; filtrenin
#      kendi modeli kullanilir.
#
# MODEL
#   Yatay (x, y): sabit-donuslu (CT) model, durum [px, py, vx, vy, w].
#     Hedef ucak surekli manevrada; CT donusu dogal yakalar.
#   Dikey (z): lineer model, durum [z, vz]. Irtifa dinamigi basit.
#   Yatay/dikey ayri tutulur: birbirine sizinti yok, ayar bagimsiz.
#
# ZAMAN TABANI
#   guncelle()'ye taze paketler arasi gercek sure (dt) verilir. Verilmezse
#   dt_varsayilan kullanilir. Surec gurultusu dt ile oranlanir (surekli
#   zaman beyaz gurultu varsayimi) -> filtre 1 Hz'de de 5 Hz'de de ayni
#   "saniye basina" davranisi gosterir.
#
# BIRIMLER: SDK ham birimleri — cm, cm/s, rad/s. Sureler saniye.
# ============================================================
import numpy as np


class GNSSFiltre:
    """Bozuk GNSS'ten hedefin guncel konum + hizini kestirir.

    Kullanim:
        f = GNSSFiltre()
        f.guncelle(bx, by, bz, dt=0.2)   # her TAZE pakette
        d = f.durum()                     # gecikme telafili "simdi"
        p = f.ileri_tahmin(1.0)           # intercept icin ek lead
    """

    def __init__(self,
                 gecikme_sn=1.0,        # olcum kanali gecikmesi (logdan olculdu)
                 dt_varsayilan=1.0,     # dt verilmezse varsayilan adim suresi
                 # --- olcum gurultusu (std, cm) ---
                 olcum_std_xy=100.0,
                 olcum_std_z=150.0,
                 # --- surec gurultusu (1 sn basina) ---
                 surec_q_konum=2000.0,  # yatay konum/hiz belirsizligi
                 surec_q_donus=1e-5,    # donus hizi (w) belirsizligi
                 surec_q_z=10.0,        # dikey belirsizlik
                 # --- fiziksel kisitlar (hedef ucak zarfi) ---
                 max_hiz=3000.0,        # 30 m/s toplam yatay hiz
                 max_vz=2500.0,         # 25 m/s dikey hiz
                 max_donus=0.4):        # rad/s donus hizi
        self.gecikme_sn = gecikme_sn
        self.dt_varsayilan = dt_varsayilan
        self.max_hiz = max_hiz
        self.max_vz = max_vz
        self.max_donus = max_donus

        # olcum modelleri
        self.H_xy = np.array([[1., 0., 0., 0., 0.],
                              [0., 1., 0., 0., 0.]])
        self.R_xy = np.eye(2) * olcum_std_xy**2
        self.H_z = np.array([[1., 0.]])
        self.R_z = np.array([[olcum_std_z**2]])

        # surec gurultusu (1 sn basina; adimda dt ile olceklenir)
        self.Q_xy = np.diag([surec_q_konum]*4 + [surec_q_donus])
        self.Q_z = np.eye(2) * surec_q_z

        # durum: yatay [px, py, vx, vy, w], dikey [z, vz]
        self.x = None
        self.P = None
        self.z = None
        self.Pz = None

        self._ilk_olcum = None      # hiz ilklendirme icin ilk paket
        self._son_olcum = None      # donmus paket tespiti
        self.hazir = False          # ilk iki farkli paketten sonra True

    # ------------------------------------------------------------
    # Hareket modelleri
    # ------------------------------------------------------------
    @staticmethod
    def _ct_ilerle(d, sure):
        """CT (sabit donuslu) modelde durumu 'sure' kadar ilerlet."""
        px, py, vx, vy, w = d
        if abs(w) < 1e-6:
            w = 1e-6                        # duz ucus = cok buyuk yaricapli donus
        s, c = np.sin(w*sure), np.cos(w*sure)
        return np.array([px + (vx*s - vy*(1-c)) / w,
                         py + (vx*(1-c) + vy*s) / w,
                         vx*c - vy*s,
                         vx*s + vy*c,
                         w])

    def _ct_jacobian(self, d, sure, eps=1e-5):
        """CT modelin durum turevi (sayisal, 5x5)."""
        f0 = self._ct_ilerle(d, sure)
        F = np.eye(5)
        for j in range(5):
            dp = d.copy()
            dp[j] += eps
            F[:, j] = (self._ct_ilerle(dp, sure) - f0) / eps
        return F

    # ------------------------------------------------------------
    # EKF adimlari
    # ------------------------------------------------------------
    def _tahmin(self, dt):
        """Iki modeli de dt kadar ilerlet; belirsizligi buyut."""
        oran = dt / 1.0                     # Q tanimlari 1 sn basina
        onceki = self.x.copy()
        self.x = self._ct_ilerle(onceki, dt)
        F = self._ct_jacobian(onceki, dt)
        self.P = F @ self.P @ F.T + self.Q_xy * oran

        Fz = np.array([[1., dt], [0., 1.]])
        self.z = Fz @ self.z
        self.Pz = Fz @ self.Pz @ Fz.T + self.Q_z * oran

    def _duzelt_yatay(self, olcum_xy):
        """Yatay olcumu isle (standart EKF duzeltmesi)."""
        fark = olcum_xy - self.H_xy @ self.x
        S = self.H_xy @ self.P @ self.H_xy.T + self.R_xy
        K = self.P @ self.H_xy.T @ np.linalg.inv(S)
        self.x = self.x + K @ fark
        A = np.eye(5) - K @ self.H_xy       # Joseph formu: sayisal saglam
        self.P = A @ self.P @ A.T + K @ self.R_xy @ K.T

    def _duzelt_dikey(self, olcum_z):
        fark = np.array([olcum_z]) - self.H_z @ self.z
        S = self.H_z @ self.Pz @ self.H_z.T + self.R_z
        K = self.Pz @ self.H_z.T @ np.linalg.inv(S)
        self.z = self.z + K @ fark
        A = np.eye(2) - K @ self.H_z
        self.Pz = A @ self.Pz @ A.T + K @ self.R_z @ K.T

    def _kisitla(self):
        """Fiziksel olarak imkansiz kestirimleri zarfa kirp."""
        self.x[4] = float(np.clip(self.x[4], -self.max_donus, self.max_donus))
        yatay_hiz = float(np.hypot(self.x[2], self.x[3]))
        if yatay_hiz > self.max_hiz:
            self.x[2:4] *= self.max_hiz / yatay_hiz
        self.z[1] = float(np.clip(self.z[1], -self.max_vz, self.max_vz))

    # ------------------------------------------------------------
    # Disa acik API
    # ------------------------------------------------------------
    def guncelle(self, bx, by, bz, dt=None):
        """Yeni GNSS paketi isle.

        dt: bir onceki TAZE paketten bu yana gecen sure (sn). None ->
        dt_varsayilan. Donmus (tekrarlanan) paket zamani ILERLETMEZ.
        Donus: kestirim uretildiyse True, isinma/donmus pakette False.
        """
        olcum = np.array([float(bx), float(by), float(bz)])

        # donmus paket: yeni bilgi yok, filtreye dokunma
        if self._son_olcum is not None and np.allclose(olcum, self._son_olcum):
            return False
        self._son_olcum = olcum

        # isinma: ilk iki FARKLI paketten konum + kaba hiz ilklendir
        if not self.hazir:
            if self._ilk_olcum is None:
                self._ilk_olcum = olcum
                return False
            adim = dt if dt is not None else self.dt_varsayilan
            self.x = np.array([olcum[0], olcum[1],
                               (olcum[0] - self._ilk_olcum[0]) / adim,
                               (olcum[1] - self._ilk_olcum[1]) / adim,
                               0.05])
            self.P = np.eye(5) * 1e6
            self.z = np.array([olcum[2], 0.0])
            self.Pz = np.eye(2) * 1e6
            self.hazir = True
            return False

        self._tahmin(dt if dt is not None else self.dt_varsayilan)
        self._duzelt_yatay(olcum[:2])
        self._duzelt_dikey(olcum[2])
        self._kisitla()
        return True

    def durum(self):
        """Gecikme telafili GUNCEL hedef durumu (None = filtre hazir degil).

        Filtre durumu 'gecikme_sn once'yi anlatir; burada hareket modeliyle
        gecikme_sn ileri tasinir -> donen konum/hiz "simdi"nin kestirimi.
        """
        if not self.hazir:
            return None
        y = self._ct_ilerle(self.x, self.gecikme_sn)
        return {"konum": (float(y[0]), float(y[1]),
                          float(self.z[0] + self.z[1] * self.gecikme_sn)),
                "hiz": (float(y[2]), float(y[3]), float(self.z[1])),
                "donus_hizi": float(y[4])}

    def ileri_tahmin(self, sure):
        """'Simdi'den 'sure' sn sonrasinin konumu (intercept/lead icin).

        Toplam ileri tasima = gecikme_sn + sure; gecikme telafisi ile lead
        tek yerde, cift sayim olmadan birlesir.
        """
        if not self.hazir:
            return None
        toplam = self.gecikme_sn + float(sure)
        y = self._ct_ilerle(self.x, toplam)
        return (float(y[0]), float(y[1]),
                float(self.z[0] + self.z[1] * toplam))
