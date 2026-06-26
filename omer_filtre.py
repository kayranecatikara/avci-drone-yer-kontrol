# -*- coding: utf-8 -*-
"""
GNSS Online Switching Denoiser (v6)
====================================
v5 (nedensel switching-KF + fixed-lag RTS) + KAVIS-DOLDURMA + KALIBRE GECIKME.

v5'ten FARK (Kayra talimati)
----------------------------
Spike cikinca yumusak kapi degeri zaten KIRPIYOR (v5). v6'nin ekledigi:
reddedilen blok, son MANTIKLI deger ile BIR SONRAKI mantikli deger ARASINDA
bir KAVIS ile doldurulur -- ileri ekstrapolasyon DEGIL, INTERPOLASYON:

  cubic Hermite:  p(s) = h00 p0 + h10 H v0 + h01 p1 + h11 H v1,   s in [0,1]
    p0,v0 = blok ONCESI son kabul (konum + hiz=tegers/turev)
    p1,v1 = blok SONRASI ilk kabul (konum + hiz)
    Uc tegersleri (turev) + kubik egrilik (konkavlik) => "son mantikli
    degerlerin olusturdugu kavis". Iki uctan BAGLI oldugu icin PATLAMAZ.

Online'lik: fixed-lag tamponu (lag=6) blok SONRASI ilk kabul degerini verir;
blok <= lag oldugu surece kavis nedensel-gecikmeli kurulur. Blok lag'i asarsa
CV-RTS'e (duz) geri dusulur. Bu, v4 `_fill_spike_blocks`'unun online portu;
keskin U-donuste (tangent acisi >90) Hermite, yumusakta dogalda lineere yakin.

NEDEN BU SURUM KARARLI (v6-onceki deneme neden patladi)
-------------------------------------------------------
Ilk deneme kavisi ILERI EKSTRAPOLE ediyordu (konkavlik tahmini gurultuyu
buyutup tahmini gercek yoldan kacirir -> donen iyi olcum reddedilir ->
GATING DEATH SPIRAL -> iraksama). Olculdu: her ayarda v5-delay-on'dan KOTU.
INTERPOLASYON bunu yapisal olarak engeller: dolgu iki gecerli uca KILITLI,
asla kacamaz. Ic filtre (kapi/durum) DEGISMEZ -- tam Q, v5 ile ozdes, kararli;
kavis yalnizca CIKTI asamasinda kabul-capalari ARASINI doldurur.

GECIKME (VARSAYILAN ACIK, Kayra karari)
---------------------------------------
H_eff = H F(-Δ*dt) (in-loop). delay_samples KALIBRE (bu veri Δ≈4.0). CLAMP
[0, delay_max=6]: Δ>=7 ham'dan kotu, Δ=8 patlar. FALLBACK compensate_delay=
False. Δ tek ucustan kilitlenmez; tum ground-truth ucuslarinda kumeleniyorsa
sabitlenir.

ARTIK TABAN (durust)
--------------------
Δ acik + kavis ile bile racetrack donuslerinde bir taban hata kalir. GNSS
"bolge kilavuzu"; final kilit vision/PnP. Kavis tabani DUSURUR, sifirlamaz.
"""
import numpy as np
from collections import deque


def _hermite(p0, v0, p1, v1, s, h):
    """Cubic Hermite: s in [0,1], h = aralik suresi (sn). v'ler m/s tegers."""
    s2 = s * s; s3 = s2 * s
    h00 = 2*s3 - 3*s2 + 1
    h10 = s3 - 2*s2 + s
    h01 = -2*s3 + 3*s2
    h11 = s3 - s2
    return h00*p0 + h10*h*v0 + h01*p1 + h11*h*v1


def patch_leading_invalid(gps, eps_zero=1e-6, n_fit=4, verbose=False):
    """Bastaki gecersiz ornekleri ONARIR (filtre ONCESI on-asama).

    Kaynak: Diklic & Markovic (2025), "Vehicle trajectory filtering...",
    Bolum II.A "Patching and Reconstruction", Denklem (5)-(6) lineer
    interpolasyon. Makale eksik ornegi iki komsu arasinda doldurur; bizim
    bastaki (0,0,0)/orijin spike'inin SOL komsusu yok (t=0'da onceki referans
    yok -> online kapi bunu reddedemez, ilk deger oldugu icin ayiklanamaz).
    Bu yuzden ayni lineer model GERIYE EKSTRAPOLASYON olarak uygulanir (k<i):
        G[k] = a + b*k,   a,b = ilk gecerli segmentin lineer uyumu
    Makale gecerliligi zaman-bosluguyla (Denk 3-4) saptar; burada ornek
    mevcut ama uzaysal olarak gecersiz (orijin), bu yuzden norm ile saptanir.
    Interpolasyon ozdes.
    """
    G = np.asarray(gps, float).copy(); N = len(G)
    valid = np.linalg.norm(G, axis=1) >= eps_zero
    if valid[0]:
        return G                                   # bastaki gecersiz yok
    f = int(np.argmax(valid))                      # ilk gecerli indeks; lead = [0..f-1]
    xs, ys, last = [], [], None
    for i in range(f, N):                          # ilk n_fit FARKLI gecerli nokta
        if valid[i] and (last is None or np.linalg.norm(G[i]-last) >= eps_zero):
            xs.append(i); ys.append(G[i]); last = G[i].copy()
            if len(xs) >= n_fit: break
    if len(xs) < 2:
        for k in range(f): G[k] = G[f]             # tek nokta -> kopyala
        return G
    xs = np.array(xs, float); Y = np.array(ys)     # (m,3)
    A = np.vstack([np.ones_like(xs), xs]).T        # lineer uyum: a + b*index
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)   # (2,3)
    for k in range(f):
        G[k] = coef[0] + coef[1] * k               # Denk (5)-(6), k<i (geriye)
    if verbose:
        print(f"[patch] bastaki {f} gecersiz ornek geriye-ekstrapolasyonla onarildi "
              f"(ilk {len(xs)} gecerli noktadan lineer uyum)")
    return G


class OnlineGNSSDenoiserV6:
    """Streaming GPS denoiser: v5 switching-KF + Hermite kavis-dolgu + gecikme."""

    def __init__(self, dt=2.0, lag=6, d_gate=4.5,
                 sigma_gnss=None, sigma_cv=None,
                 p0_pos=300.0, p0_vel=150.0,
                 compensate_delay=True, delay_samples=4.0, delay_max=6.0,
                 curve_fill=True, hermite_turn_deg=60.0,
                 cv_floor_xy=100.0, cv_floor_z=20.0, eps_zero=1e-6):
        self.dt = float(dt); self.lag = int(lag); self.d_gate = float(d_gate)
        self.eps_zero = float(eps_zero)
        # gecikme: clamp + fallback
        self.compensate_delay = bool(compensate_delay)
        if delay_samples is None:
            self.compensate_delay = False; delay_samples = 0.0
        self.delay_samples = float(np.clip(delay_samples, 0.0, float(delay_max)))
        self.delay_max = float(delay_max)
        # kavis-dolgu
        self.curve_fill = bool(curve_fill)
        self.hermite_turn_deg = float(hermite_turn_deg)  # bu acidan keskin donuste Hermite, altinda yumusak
        self.cv_floor_xy = float(cv_floor_xy)            # X-Y surec gurultusu tabani
        self.cv_floor_z = float(cv_floor_z)              # Z tabani (dusuk -> Z spike yakalanir)

        self.sigma_gnss = sigma_gnss; self.sigma_cv = sigma_cv
        self._p0_pos = float(p0_pos); self._p0_vel = float(p0_vel)

        F = np.eye(6); F[0,3]=F[1,4]=F[2,5]=self.dt; self.F = F
        H = np.zeros((3,6)); H[0,0]=H[1,1]=H[2,2]=1.0; self.H = H
        Fback = np.eye(6)
        dly = self.delay_samples*self.dt if self.compensate_delay else 0.0
        Fback[0,3]=Fback[1,4]=Fback[2,5]=-dly
        self.H_eff = self.H @ Fback

        self._initialized=False; self.x=None; self.P=None
        self.z_prev_raw=None; self.k=0; self.buf=deque(); self._next_emit=0
        # son EMIT edilen kabul capasi (Hermite sol ucu icin): (t, p, v)
        self.prev_anchor=None
        self.log_beta=[]; self.log_d=[]; self.log_accept=[]; self.log_filled=[]

    def _build_Q(self):
        dt=self.dt
        scv=np.atleast_1d(np.asarray(self.sigma_cv,float))
        if scv.size==1: scv=np.repeat(scv,3)
        Q=np.zeros((6,6))
        for i in range(3):
            sa=max(scv[i],1e-6)/(dt*dt); q=sa*sa
            Q[i,i]=q*dt**4/4; Q[i,i+3]=q*dt**3/2; Q[i+3,i]=q*dt**3/2; Q[i+3,i+3]=q*dt**2
        return Q
    def _R(self): s=max(self.sigma_gnss,1e-6); return np.eye(3)*(s*s)

    def calibrate(self, points):
        U=np.asarray(points,float); keep=[]; last=None
        for i in range(len(U)):
            if np.linalg.norm(U[i])<self.eps_zero: continue
            if last is not None and np.linalg.norm(U[i]-last)<self.eps_zero: continue
            keep.append(U[i]); last=U[i]
        Uc=np.array(keep) if keep else U
        s_med=0.0; med_ax=np.zeros(3)
        if len(Uc)>=3:
            D2=np.diff(Uc,n=2,axis=0)
            med_ax=np.median(np.abs(D2),axis=0)             # eksene-ozel 2.fark
            sec=np.linalg.norm(D2,axis=1)
            s_med=float(np.median(sec)) if len(sec) else 0.0
        if self.sigma_gnss is None: self.sigma_gnss=max(80.0,0.20*s_med)
        if self.sigma_cv is None:
            # X-Y: v5 ile AYNI (norm-tabanli s_med) -> X-Y davranisi korunur.
            # Z: EKSENE-OZEL dusuk taban. Z gercekte ~16x daha sakin; izotropik Q
            # Z'yi sisirip Z spike'larini kapidan geciriyordu. Dusuk Z tabani ->
            # Z kapisi keskin -> Z spike reddedilir, X-Y degismez.
            base_xy=max(self.cv_floor_xy, 0.20*s_med)
            cv_z=max(self.cv_floor_z, 0.20*med_ax[2])
            self.sigma_cv=np.array([base_xy, base_xy, cv_z])
        self.sigma_cv=np.atleast_1d(np.asarray(self.sigma_cv,float))
        if self.sigma_cv.size==1: self.sigma_cv=np.repeat(self.sigma_cv,3)
        self.Q=self._build_Q()
        return self.sigma_gnss, self.sigma_cv

    def _ensure_ready(self):
        if self.sigma_gnss is None: self.sigma_gnss=100.0
        if self.sigma_cv is None: self.sigma_cv=np.array([120.0,120.0,self.cv_floor_z])
        self.sigma_cv=np.atleast_1d(np.asarray(self.sigma_cv,float))
        if self.sigma_cv.size==1: self.sigma_cv=np.repeat(self.sigma_cv,3)
        if not hasattr(self,"Q"): self.Q=self._build_Q()

    def _init_state(self,z):
        self.x=np.hstack([z,np.zeros(3)])
        self.P=np.diag([self._p0_pos**2]*3+[self._p0_vel**2]*3).astype(float)
        self._initialized=True

    def update(self, z):
        self._ensure_ready(); z=np.asarray(z,float)
        if not self._initialized:
            if np.linalg.norm(z)>=self.eps_zero:
                self._init_state(z); self.z_prev_raw=z.copy()
            self._push(self.x if self.x is not None else np.zeros(6),
                       self.P if self.P is not None else np.eye(6),
                       self.x if self.x is not None else np.zeros(6),
                       self.P if self.P is not None else np.eye(6), False)
            self.log_beta.append(0.0); self.log_d.append(np.inf)
            self.log_accept.append(False); self.log_filled.append(False)
            return self._maybe_emit()

        # PREDICT (duz CV, tam Q -> KARARLI; v5 ile ozdes ic dinamik)
        xp=self.F@self.x
        Pp=self.F@self.P@self.F.T+self.Q

        beta=0.0; d=np.inf; accepted=False
        is_null=np.linalg.norm(z)<self.eps_zero
        is_freeze=(self.z_prev_raw is not None and
                   np.linalg.norm(z-self.z_prev_raw)<self.eps_zero)
        if not is_null and not is_freeze:
            R=self._R(); nu=z-self.H_eff@xp
            S=self.H_eff@Pp@self.H_eff.T+R; S=0.5*(S+S.T)+1e-9*np.eye(3)
            Sinv=np.linalg.inv(S); d2=float(nu@Sinv@nu)
            if not np.isfinite(d2) or d2<0: d2=1e6
            d=np.sqrt(d2); d2c=min(d2,700.0)
            l_wo=np.exp(-0.5*d2c); l_fa=np.exp(-0.5*self.d_gate**2)
            beta=l_wo/(l_wo+l_fa+1e-300)
            K=Pp@self.H_eff.T@Sinv
            self.x=xp+beta*(K@nu); Kn=(K@nu).reshape(-1,1)
            self.P=Pp-beta*(K@S@K.T)+beta*(1-beta)*(Kn@Kn.T); self.P=0.5*(self.P+self.P.T)
            accepted=beta>0.5
        else:
            self.x=xp; self.P=Pp
        if not is_null: self.z_prev_raw=z.copy()

        self.log_beta.append(beta); self.log_d.append(d)
        self.log_accept.append(accepted); self.log_filled.append(False)
        self._push(self.x.copy(),self.P.copy(),xp.copy(),Pp.copy(),accepted)
        return self._maybe_emit()

    # ---- fixed-lag + Hermite kavis-dolgu ----
    def _push(self,xf,Pf,xp,Pp,acc):
        self.buf.append(dict(gidx=self.k,xf=xf,Pf=Pf,xp=xp,Pp=Pp,acc=acc)); self.k+=1

    def _rts(self):
        m=len(self.buf); recs=list(self.buf); xs=[None]*m
        xs[m-1]=recs[m-1]['xf'].copy()
        for i in range(m-2,-1,-1):
            Pf=recs[i]['Pf']; Pp_n=recs[i+1]['Pp']; xp_n=recs[i+1]['xp']
            A=Pf@self.F.T; Ct=np.linalg.solve(Pp_n+1e-9*np.eye(6),A.T)
            xs[i]=recs[i]['xf']+Ct.T@(xs[i+1]-xp_n)
        return recs,xs

    def _emit_oldest(self, recs, xs):
        """En eski kaydi cikar. Reddedilmis blok icindeyse ve hem sol (prev_anchor)
        hem sag (tamponda ilk kabul) uc varsa Hermite ile doldur; yoksa CV-RTS."""
        r0=recs[0]; gidx=r0['gidx']; filled=False
        if r0['acc'] or not self.curve_fill:
            pos=xs[0][:3].copy()
            if r0['acc']:
                self.prev_anchor=(gidx, xs[0][:3].copy(), xs[0][3:6].copy())
        else:
            # sag uc: tamponda ilk kabul edilen kayit
            jr=next((j for j in range(len(recs)) if recs[j]['acc']), None)
            if self.prev_anchor is not None and jr is not None:
                t0,p0,v0=self.prev_anchor
                t1=recs[jr]['gidx']; p1=xs[jr][:3]; v1=xs[jr][3:6]
                h=(t1-t0)*self.dt
                if h>1e-9:
                    s=(gidx-t0)/(t1-t0)
                    # keskin donus testi: uc hiz vektorleri arasi aci
                    n0=np.linalg.norm(v0); n1=np.linalg.norm(v1)
                    sharp=True
                    if n0>1e-6 and n1>1e-6:
                        cosang=float(np.clip(np.dot(v0,v1)/(n0*n1),-1,1))
                        sharp=np.degrees(np.arccos(cosang))>self.hermite_turn_deg
                    if sharp:
                        pos=_hermite(p0,v0,p1,v1,s,h); filled=True
                    else:
                        pos=(1-s)*p0+s*p1; filled=True   # yumusak -> lineer (kiris)
                else:
                    pos=xs[0][:3].copy()
            else:
                pos=xs[0][:3].copy()   # sag uc yok (blok > lag) -> CV-RTS
        self.buf.popleft(); self._next_emit=gidx+1
        if filled and gidx < len(self.log_filled): self.log_filled[gidx]=True
        return (gidx,pos)

    def _maybe_emit(self):
        if len(self.buf)<=self.lag: return None
        recs,xs=self._rts()
        return self._emit_oldest(recs,xs)

    def flush(self):
        outs=[]
        while self.buf:
            recs,xs=self._rts()
            outs.append(self._emit_oldest(recs,xs))
        return outs


def denoise_stream_v6(gps, dt=2.0, lag=6, d_gate=4.5, sigma_gnss=None, sigma_cv=None,
                      n_warmup=24, compensate_delay=True, delay_samples=4.0,
                      delay_max=6.0, curve_fill=True, patch_leading=True, verbose=True):
    gps=np.asarray(gps,float); N=len(gps)
    # ON-ASAMA: bastaki gecersiz (0,0,0) ornegini onar (makale Denk 5-6)
    if patch_leading:
        gps=patch_leading_invalid(gps, verbose=verbose)
    f=OnlineGNSSDenoiserV6(dt=dt,lag=lag,d_gate=d_gate,sigma_gnss=sigma_gnss,
                           sigma_cv=sigma_cv,compensate_delay=compensate_delay,
                           delay_samples=delay_samples,delay_max=delay_max,curve_fill=curve_fill)
    f.calibrate(gps[:max(n_warmup,3)])
    out=np.zeros((N,3)); seen=np.zeros(N,bool)
    for i in range(N):
        em=f.update(gps[i])
        if em:
            g,p=em
            if 0<=g<N: out[g]=p; seen[g]=True
    for g,p in f.flush():
        if 0<=g<N: out[g]=p; seen[g]=True
    if not seen.all() and seen.any():
        fo=np.where(seen)[0][0]
        for j in np.where(~seen)[0]: out[j]=out[fo]
    acc=np.array(f.log_accept[:N]); fil=np.array(f.log_filled[:N])
    if verbose:
        print(f"[v6-online] N={N} lag={lag} d_gate={d_gate}")
        print(f"[parametre] sigma_gnss={f.sigma_gnss:.0f}m  sigma_cv(X,Y,Z)={np.round(np.atleast_1d(f.sigma_cv),0)}")
        print(f"[switching] reddedilen(beta<=0.5): {int((~acc).sum())}/{N} | "
              f"Hermite-dolgulu cikti: {int(fil.sum())}")
        print(f"[gecikme]   {'ACIK %.2f (clamp<=%.0f)'%(f.delay_samples,f.delay_max) if f.compensate_delay else 'KAPALI(fallback)'}")
    info=dict(accept=acc,filled=fil,sigma_gnss=f.sigma_gnss,sigma_cv=f.sigma_cv,
              lag=lag,delay=f.delay_samples)
    return out,info
