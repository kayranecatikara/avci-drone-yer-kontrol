# -*- coding: utf-8 -*-
"""
================================================================================
HAKEM ISTEMCI — kilit paketi + telemetri gonderimi (YARISMA PIPELINE FAZ 3 stub)
================================================================================
Sim'de canli bir hakem sunucusu YOK -> dosyaya/loga yazar. Amac: FSM'deki
kilit -> bildir -> angajman SIRALAMASINI kodda somutlastirmak; yarisma gunu
sahadaki istemci AYNI arayuze takilir (kod degismez).

Sozlesme (yarisma sunucusu bunlari bekler; buradaki imza sabit tutulur):
  kilit_paketi_gonder(t, konum, kilit_durumu) -> +400 garanti altina alinir
  telemetri_gonder(...)  -> 1-5 Hz, sistem saati timestamp

Guvenlik: gonderimler idempotent DEGIL; FSM kilit_paketi'ni BIR KEZ gonderir
(kenar-tetik). Bu stub yalniz kaydeder; cift-gonderim FSM sorumlulugu.
================================================================================
"""
import json
import os
import time


class HakemIstemci:
    def __init__(self, log_yolu=None):
        _proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _veri = os.path.join(_proj, "veri")
        os.makedirs(_veri, exist_ok=True)
        self.log_yolu = log_yolu or os.path.join(_veri, "hakem_log.jsonl")
        self._f = None
        self.kilit_gonderildi = False
        self._son_telemetri_t = 0.0

    def _yaz(self, kayit):
        try:
            if self._f is None:
                self._f = open(self.log_yolu, "a", encoding="utf-8")
            self._f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
            self._f.flush()
        except Exception:
            pass

    def kilit_paketi_gonder(self, t, konum, kilit_durumu):
        """Kilit bildirimi (+400). konum: (x,y,z) cm; kilit_durumu: dict.
        Bir kez gonderilir (kilit_gonderildi bayragi); tekrar cagri kaydedilir
        ama 'tekrar' isaretlenir (FSM hatasi teshisi)."""
        tekrar = self.kilit_gonderildi
        self.kilit_gonderildi = True
        kayit = {"tip": "KILIT_PAKETI", "t_perf": t, "t_wall": time.time(),
                 "konum": list(konum) if konum is not None else None,
                 "kilit_durumu": kilit_durumu, "tekrar": tekrar}
        self._yaz(kayit)
        print("[HAKEM] KILIT PAKETI gonderildi%s (kumulatif=%.1fs surekli=%.1fs)"
              % (" [TEKRAR!]" if tekrar else "",
                 kilit_durumu.get("kumulatif_kilit_sn", 0),
                 kilit_durumu.get("surekli_kilit_sn", 0)))
        return not tekrar

    def telemetri_gonder(self, t, konum, durum, ekstra=None, hz=5.0):
        """Periyodik telemetri (1-5 Hz; sistem saati). hz'e gore hizlar."""
        now = time.time()
        if now - self._son_telemetri_t < (1.0 / max(hz, 0.1)):
            return False
        self._son_telemetri_t = now
        kayit = {"tip": "TELEMETRI", "t_perf": t, "t_wall": now,
                 "konum": list(konum) if konum is not None else None,
                 "durum": durum, "ekstra": ekstra or {}}
        self._yaz(kayit)
        return True

    def sifirla(self):
        """Yeni gorev: kilit bayragini sifirla (log dosyasi korunur)."""
        self.kilit_gonderildi = False
        self._son_telemetri_t = 0.0

    def kapat(self):
        if self._f is not None:
            try:
                self._f.close()
            except Exception:
                pass
            self._f = None
