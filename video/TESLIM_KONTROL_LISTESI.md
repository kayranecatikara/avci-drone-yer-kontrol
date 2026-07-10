# TESLİM KONTROL LİSTESİ — Video + Kaynak Kod (.zip)

> Kayıt ve teslim öncesi son kontrol. Her madde işaretlenmeden teslim edilmez.

## A) VİDEO TARAFI
- [ ] **Toplam süre ≤ 6 dk**, iki bölüm: A (algoritma/kod ~4 dk) + B (uçuş kanıtı ~3 dk).
      (Resmi doküman "3+3" der; A 3 dk'ya inecekse `KONUSMA_METNI.md`'deki `[OPSİYONEL]` bloklar çıkarılır.)
- [ ] **Tek parça, anlaşılır akış**; takım adı (Hamidiye), sistem mimarisi, kullanılan algoritmalar,
      simülasyon ekranı ve görev çıktıları net görünüyor.
- [ ] **Sesli anlatım var** (A bölümü boyunca); kod yalnızca görsel gösterilmiyor, teknik anlatılıyor.
- [ ] **A bölümünde hızlandırma YOK.**
- [ ] **B bölümünde kritik anlar gerçek zamanlı:** tespit, takip başlatma, kilitlenme, GNSS'in
      devreden çıkarılması, görüntüyle takip, angajman. Bunların hiçbiri hızlandırılmamış.
- [ ] **Hızlandırılan kesitler etiketli** ("Nx hızlandırılmıştır") ve yalnız görev-dışı bekleme kısımlarında.
- [ ] **Kod ekranları okunabilir** çözünürlükte (koyu tema, büyük font, ilgili fonksiyona zoom).
- [ ] **Yanıltıcı kurgu / kritik an atlama / otonomiyi şüpheye düşüren kesme YOK.**
- [ ] **Vuruş sahnesi gerçek ve kesintisiz** simülasyon kaydı (kurguyla oluşturulmamış). `[VURUŞ-BAĞIMLI]`
- [ ] **YouTube "liste dışı"** yüklendi; bağlantı erişilebilir; teslim formuna eklendi.
- [ ] **Video↔kod tutarlılığı:** videoda anlatılan her yetenek teslim edilen kodda var
      (pose/keypoint anlatılmadı — kodda kapalı; İnovasyonlu J anlatılmadı — kodda yok; GNSS Filtre +
      GPS Takip + IBVS + HybridSort anlatıldı — kodda var).
- [ ] **`[VURUŞ-BAĞIMLI]` cümle denetimi:** `KONUSMA_METNI.md`'deki §Terminal faz'ın 2 cümlesi son
      kayıttaki fiili durumla **birebir** uyumlu. Terminal faz/vuruş yetişmediyse o cümleler revize
      edildi ve B bölümü 8-10 buna göre anlatıldı (aşağıdaki "Terminal faz yetişmezse" bölümü).

## B) KAYNAK KOD (.zip içeriği) — şartname 7. bölüm
- [ ] **`sdk/drone_sdk.py`** (input.py muadili; sim I/O).
- [ ] **Hedef tespit kodları:** `detection/gorsel_tespit.py` (+ `detection/algi_hatti.py`).
- [ ] **Tracking kodları:** `detection/takip.py` (boxmot HybridSort adaptörü) + `detection/pencere_yakala.py`.
- [ ] **Sensör füzyonu / filtreleme:** `fusion/gnss_filtre.py` (GNSSFiltre).
- [ ] **Güdüm ve karar:** `guidance/gps_takip.py` + `guidance/ana_kontrol.py` + `guidance/ibvs_gorsel.py`.
- [ ] **Ana çalıştırma:** `main.py`.
- [ ] **Config:** `config.py` (+ modül içi Cfg/GPSCfg blokları).
- [ ] **Bağımlılıklar:** `requirements.txt` (ultralytics, torch, opencv, numpy, boxmot, mss,
      windows-capture, Pillow, pygetwindow, openpyxl).
- [ ] **README:** çalıştırma talimatı içeriyor (`python main.py`).
- [ ] **Eğitilmiş model (.pt):** `models/best.pt` (YOLO26s, tek sınıf talon). *(pose modeli kapalı;
      zip'e alınırsa da güdüme girmez — ISTEĞE bağlı.)*
- [ ] **Zip temiz bir makinede doğrudan çalıştırılabilir** (README adımlarıyla).
- [ ] **Başıboş model kopyaları zip'e GİRMEDİ** (`best (1).pt`, `best 6.pt`, `best7.pt`,
      `best_son.pt`, `eniyi_*.pt`, `models/talon_pose_eski_*.pt` — bkz. YAPILACAKLAR).
- [ ] **DEV/truth izi teslimde temiz:** `web/dev_truth.py` pakete girmez; server/index'te DEV-ONLY
      çitli bloklar sökülür → `python arac/paket_kontrol.py` ile denetle (bkz. YAPILACAKLAR — paketleme).

## C) SON TUTARLILIK KONTROLÜ
- [ ] Videoda gösterilen sistem = zip'teki kod. Modül adları, algoritma adları (GNSS Filtre,
      GPS Takip, IBVS, YOLO26s, HybridSort) videoda ve kodda **aynı**.
- [ ] Konuşma metnindeki rakamlar kodla eşleşiyor (imgsz 960, kilit 10/5 sn, handoff 40 m,
      ölü-hesap 30 sn, gecikme telafisi 1 sn). Kod değiştiyse metin güncellendi.

---

## "Terminal faz yetişmezse" — metin revizyon reçetesi (`[VURUŞ-BAĞIMLI]`)
Kayıt gününe kadar terminal faz/vuruş güvenilir çalışmazsa:
- **Konuşma metni §Terminal faz:** iki `[VURUŞ-BAĞIMLI]` cümle şununla değişir:
  *"Kilit sağlandıktan sonra sistem hedefi kadraj içinde tutmaya ve görsel güdümle yaklaşmaya
  devam eder; terminal angajman ve vuruş, bu kilit temeli üzerine kurulan son safhadır."*
  (Vuruş iddiası çıkarılır; kilit + yaklaşma anlatılır — bunlar kodda kanıtlı.)
- **B bölümü çekim planı 8-10:** kilit sayacının dolması + ANGAJMAN çipi 8. adımda kanıtlanır;
  9-10 (vuruş + başarı banner) o koşuda gösterilmez.
- Bu durumda video hâlâ **tespit → takip → GNSS devre dışı → görsel yaklaşma → kilit** zincirini
  eksiksiz kanıtlar (şartname minimum kanıt akışı).
